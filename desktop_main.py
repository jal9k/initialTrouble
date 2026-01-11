"""
TechTim(e) Desktop Application Entry Point

This script:
1. Configures logging
2. Starts the Ollama sidecar
3. Ensures the required model is downloaded
4. Creates the PyWebView window with the frontend
5. Handles graceful shutdown on exit

Usage:
    python desktop_main.py          # Normal mode
    python desktop_main.py --dev    # Development mode (uses Next.js dev server)
"""
import sys
import asyncio
import logging
import argparse
import threading
from pathlib import Path

import webview

from backend.config import get_settings
from backend.logging_config import setup_logging
from backend.preferences import get_preferences
from desktop.ollama_manager import OllamaManager
from desktop.api import TechTimApi
from desktop.exceptions import OllamaNotFoundError, OllamaStartupError
from desktop.process_guard import cleanup_orphaned_ollama, ProcessGuard

logger = logging.getLogger("techtime.desktop")


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='TechTim(e) Desktop Application')
    parser.add_argument(
        '--dev',
        action='store_true',
        help='Development mode: use Next.js dev server instead of static files'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug mode with verbose logging'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=3000,
        help='Port for Next.js dev server (default: 3000)'
    )
    return parser.parse_args()


def get_frontend_url(dev_mode: bool, port: int = 3000) -> str:
    """
    Get the URL or path to load in the webview.
    
    Args:
        dev_mode: If True, use Next.js dev server
        port: Port for Next.js dev server
    
    Returns:
        URL string or file path
    """
    settings = get_settings()
    
    if dev_mode:
        # Development: connect to Next.js dev server
        return f'http://localhost:{port}'
    
    # Production: load static files
    if settings.bundled_mode:
        # PyInstaller bundle
        frontend_path = settings.base_path / 'frontend' / 'out' / 'index.html'
    else:
        # Development with static build
        frontend_path = Path(__file__).parent / 'frontend' / 'techtime' / 'out' / 'index.html'
    
    if not frontend_path.exists():
        raise FileNotFoundError(
            f"Frontend not found at {frontend_path}\n\n"
            f"To fix this, either:\n"
            f"  1. Run in dev mode: python desktop_main.py --dev\n"
            f"  2. Build the frontend: cd frontend/techtime && npm run build\n"
        )
    
    return str(frontend_path)


async def initialize_app(
    api: TechTimApi,
    window: webview.Window,
) -> bool:
    """
    Initialize the application after window is created.
    
    This runs asynchronously while a loading screen is shown.
    
    Args:
        api: The API bridge instance
        window: The PyWebView window
    
    Returns:
        True if initialization succeeded, False otherwise
    """
    settings = get_settings()
    
    def update_status(message: str):
        """Update the loading status in the frontend."""
        logger.info(f"Status: {message}")
        window.evaluate_js(f'window.setLoadingStatus && window.setLoadingStatus("{message}")')
    
    def update_progress(percent: int, message: str):
        """Update the loading progress bar."""
        window.evaluate_js(
            f'window.setLoadingProgress && window.setLoadingProgress({percent}, "{message}")'
        )
    
    try:
        # Step 1: Start Ollama
        update_status("Starting AI engine...")
        await api.ollama.start(timeout=30)
        
        # Step 2: Check for model
        update_status("Checking AI model...")
        has_model = await api.ollama.has_model(settings.ollama_model)
        
        # Step 3: Download model if needed
        if not has_model:
            update_status(f"Downloading AI model ({settings.ollama_model})...")
            
            def on_progress(progress: dict):
                status = progress.get('status', '')
                completed = progress.get('completed', 0)
                total = progress.get('total', 1)
                
                if total > 0:
                    pct = int(completed / total * 100)
                    update_progress(pct, status)
            
            await api.ollama.pull_model(settings.ollama_model, on_progress)
        
        # Step 4: Initialize chat service
        update_status("Initializing...")
        await api._initialize()
        
        # Step 5: Signal ready
        update_status("Ready!")
        window.evaluate_js('window.onAppReady && window.onAppReady()')
        
        logger.info("Application initialized successfully")
        return True
        
    except OllamaNotFoundError as e:
        logger.error(f"Ollama not found: {e}")
        error_message = str(e).replace('"', '\\"').replace('\n', '\\n')
        window.evaluate_js(f'window.onAppError && window.onAppError("{error_message}")')
        return False
        
    except OllamaStartupError as e:
        logger.error(f"Ollama startup failed: {e}")
        error_message = str(e).replace('"', '\\"').replace('\n', '\\n')
        window.evaluate_js(f'window.onAppError && window.onAppError("{error_message}")')
        return False
        
    except Exception as e:
        logger.exception("Failed to initialize application")
        error_message = str(e).replace('"', '\\"').replace('\n', '\\n')
        window.evaluate_js(f'window.onAppError && window.onAppError("{error_message}")')
        return False


def on_window_loaded(window: webview.Window, api: TechTimApi):
    """
    Called when the webview finishes loading.
    
    Starts the async initialization process in a background thread.
    """
    api.set_window(window)
    
    def run_init():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(initialize_app(api, window))
        except Exception as e:
            logger.exception("Initialization thread error")
        finally:
            loop.close()
    
    # Run initialization in background thread
    init_thread = threading.Thread(target=run_init, daemon=True)
    init_thread.start()


def main():
    """Application entry point."""
    args = parse_args()
    settings = get_settings()
    
    # Setup logging
    log_level = "DEBUG" if args.debug else "INFO"
    setup_logging(level=log_level, log_to_file=True)
    
    logger.info("=" * 60)
    logger.info("TechTim(e) Desktop Application Starting")
    logger.info("=" * 60)
    logger.info(f"Bundled mode: {settings.bundled_mode}")
    logger.info(f"Development mode: {args.dev}")
    logger.info(f"User data path: {settings.user_data_path}")
    logger.info(f"Database path: {settings.database_path}")
    
    # Clean up any orphaned Ollama processes from previous crashes
    if cleanup_orphaned_ollama():
        logger.info("Cleaned up orphaned Ollama process from previous session")
    
    # Ensure directories exist
    settings.log_path.mkdir(parents=True, exist_ok=True)
    settings.models_path.mkdir(parents=True, exist_ok=True)
    
    # Load user preferences
    prefs = get_preferences()
    
    # Create managers
    ollama_manager = OllamaManager()
    process_guard = ProcessGuard("ollama")
    api = TechTimApi(ollama_manager)
    
    # Store process guard reference for Ollama PID tracking
    original_start = ollama_manager.start
    
    async def tracked_start(timeout: float = 30.0) -> None:
        """Wrapper to track Ollama PID after startup."""
        await original_start(timeout=timeout)
        if ollama_manager.process:
            process_guard.register_pid(ollama_manager.process.pid)
    
    ollama_manager.start = tracked_start
    
    try:
        # Get frontend URL
        frontend_url = get_frontend_url(args.dev, args.port)
        logger.info(f"Loading frontend from: {frontend_url}")
        
        # Get window state from preferences
        window_prefs = prefs.all.window
        
        # Create window with saved position/size (dev mode ignores saved position)
        window = webview.create_window(
            title='TechTim(e)',
            url=frontend_url,
            js_api=api,
            x=window_prefs.x if not args.dev else None,
            y=window_prefs.y if not args.dev else None,
            width=window_prefs.width,
            height=window_prefs.height,
            min_size=(800, 600),
            confirm_close=True,
        )
        
        # Start webview event loop
        # debug=True enables Chrome DevTools (right-click -> Inspect)
        webview.start(
            func=lambda: on_window_loaded(window, api),
            debug=args.debug or args.dev,
        )
        
    except FileNotFoundError as e:
        logger.error(str(e))
        
        # Show error dialog
        webview.create_window(
            title='TechTim(e) - Error',
            html=f'''
                <!DOCTYPE html>
                <html>
                <head>
                    <style>
                        body {{
                            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                            padding: 40px;
                            text-align: center;
                            background: #1a1a2e;
                            color: #eee;
                        }}
                        h1 {{ color: #ff6b6b; }}
                        pre {{
                            text-align: left;
                            background: #16213e;
                            padding: 20px;
                            border-radius: 8px;
                            overflow-x: auto;
                        }}
                        button {{
                            background: #4a69bd;
                            color: white;
                            border: none;
                            padding: 12px 24px;
                            border-radius: 6px;
                            cursor: pointer;
                            font-size: 16px;
                        }}
                        button:hover {{ background: #1e3799; }}
                    </style>
                </head>
                <body>
                    <h1>Failed to Start</h1>
                    <pre>{str(e)}</pre>
                    <button onclick="window.close()">Close</button>
                </body>
                </html>
            ''',
            width=600,
            height=400,
        )
        webview.start()
        sys.exit(1)
        
    except Exception as e:
        logger.exception("Unexpected error during startup")
        sys.exit(1)
    
    finally:
        # Clean shutdown
        logger.info("Shutting down...")
        
        # Stop Ollama
        if ollama_manager.is_running():
            ollama_manager.stop()
        
        # Clean up PID file
        process_guard.unregister()
        
        logger.info("Shutdown complete")


if __name__ == '__main__':
    main()

