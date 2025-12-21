"""CLI interface for Network Diagnostics."""

import asyncio
import re
from pathlib import Path

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt, Confirm

from .config import get_settings
from .llm import ChatMessage, LLMRouter
from .tools import ToolRegistry, get_registry
from .prompts import AgentType, load_prompt, get_prompt_for_context

# Import analytics
from analytics import AnalyticsCollector, AnalyticsStorage
from analytics.models import SessionOutcome, IssueCategory

# Initialize CLI app and console
app = typer.Typer(
    name="network-diag",
    help="AI-powered network diagnostics CLI",
)
console = Console()

# Resolution detection patterns
RESOLUTION_PATTERNS = [
    r"\b(thank(?:s|you)?|works?|working|fixed|resolved|perfect|great|awesome)\b",
    r"\b(it'?s?\s+(?:working|fixed|good|fine))\b",
    r"\b(problem\s+solved)\b",
    r"\b(all\s+good)\b",
    r"\b(yes|yep|yeah|yup)\b",
]

def detect_resolution_signal(text: str) -> bool:
    """Detect if user message indicates resolution."""
    text_lower = text.lower()
    for pattern in RESOLUTION_PATTERNS:
        if re.search(pattern, text_lower):
            return True
    return False


def prompt_for_feedback(collector: AnalyticsCollector) -> None:
    """Prompt user for feedback after session."""
    console.print("\n" + "-" * 50)
    console.print("[bold blue]Session Feedback[/bold blue]")
    
    try:
        resolved = Prompt.ask(
            "Was your issue resolved?",
            choices=["y", "n", "s"],
            default="s",
        )
        
        if resolved == "s":
            # User skipped - mark as abandoned
            collector.end_session(outcome=SessionOutcome.ABANDONED)
            return
        
        outcome = SessionOutcome.RESOLVED if resolved == "y" else SessionOutcome.UNRESOLVED
        
        # Ask for rating
        score_str = Prompt.ask(
            "Rate your experience (1-5, or skip)",
            default="s",
        )
        
        if score_str != "s" and score_str.isdigit():
            score = int(score_str)
            if 1 <= score <= 5:
                collector.record_feedback(
                    score=score,
                    source="cli",
                )
        
        # End session with outcome
        collector.end_session(outcome=outcome)
        console.print("[dim]Thank you for your feedback![/dim]")
        
    except (KeyboardInterrupt, EOFError):
        collector.end_session(outcome=SessionOutcome.ABANDONED)
        console.print("\n[dim]Feedback skipped.[/dim]")


async def run_chat_loop():
    """Main chat loop."""
    settings = get_settings()
    
    # Initialize analytics
    db_path = Path("data/analytics.db")
    db_path.parent.mkdir(parents=True, exist_ok=True)
    storage = AnalyticsStorage(db_path)
    collector = AnalyticsCollector(storage=storage)
    
    # Initialize LLM router with analytics
    llm_router = LLMRouter(settings, analytics_collector=collector)
    tool_registry = get_registry()
    
    # Connect analytics to tool registry
    tool_registry.set_analytics(collector)

    # Register diagnostics
    from .diagnostics import register_all_diagnostics

    register_all_diagnostics(tool_registry)

    # Check LLM availability
    console.print("\n[bold blue]Network Diagnostics Assistant[/bold blue]")
    console.print("Checking LLM backends...\n")

    availability = await llm_router.is_available()
    for backend, available in availability.items():
        status = "[green]✓[/green]" if available else "[red]✗[/red]"
        console.print(f"  {status} {backend}")

    if not any(availability.values()):
        console.print(
            "\n[red]Error:[/red] No LLM backend available. "
            "Please start Ollama or set OPENAI_API_KEY."
        )
        return

    console.print(f"\nUsing model: [cyan]{llm_router.active_model or 'auto'}[/cyan]")
    console.print("Type your network problem or 'quit' to exit.")
    console.print("[dim]Commands: /feedback (rate session), /stats (show analytics)[/dim]\n")
    console.print("-" * 50)

    # Load diagnostic agent prompt (follows OSI ladder properly)
    system_prompt = load_prompt(AgentType.DIAGNOSTIC)
    
    # Conversation history
    messages: list[ChatMessage] = [
        ChatMessage(role="system", content=system_prompt)
    ]
    
    # Start analytics session
    session = collector.start_session()
    console.print(f"[dim]Session: {session.session_id[:8]}...[/dim]")
    
    # Track if we should prompt for feedback
    resolution_detected = False
    first_message = True

    # Chat loop
    while True:
        try:
            # Get user input
            user_input = Prompt.ask("\n[bold green]You[/bold green]")

            if user_input.lower() in ("quit", "exit", "q"):
                console.print("\n[dim]Goodbye![/dim]")
                # Prompt for feedback before exiting
                prompt_for_feedback(collector)
                break
            
            # Handle special commands
            if user_input.strip() == "/feedback":
                prompt_for_feedback(collector)
                # Start a new session after feedback
                session = collector.start_session()
                console.print(f"\n[dim]New session: {session.session_id[:8]}...[/dim]")
                messages = [ChatMessage(role="system", content=system_prompt)]
                resolution_detected = False
                first_message = True
                continue
            
            if user_input.strip() == "/stats":
                summary = storage.get_session_summary()
                console.print("\n[bold]Analytics Summary[/bold]")
                console.print(f"  Total sessions: {summary.total_sessions}")
                console.print(f"  Resolved: {summary.resolved_count} ({summary.success_rate:.1f}%)")
                console.print(f"  Avg tokens/session: {summary.avg_tokens_per_session:.0f}")
                console.print(f"  Avg time to resolution: {summary.avg_time_to_resolution_seconds:.1f}s")
                if summary.total_cost_usd > 0:
                    console.print(f"  Total OpenAI cost: ${summary.total_cost_usd:.4f}")
                continue

            if not user_input.strip():
                continue
            
            # Record user message
            collector.record_user_message(user_input)
            
            # Check for resolution signal
            if detect_resolution_signal(user_input):
                resolution_detected = True

            # Add user message
            messages.append(ChatMessage(role="user", content=user_input))

            # Get response with tools
            console.print("\n[dim]Thinking...[/dim]")

            tools = tool_registry.get_all_definitions()
            response = await llm_router.chat(
                messages=messages,
                tools=tools,
                temperature=0.3,
            )
            
            # Set backend info after first LLM call
            if first_message and llm_router.active_backend:
                collector.set_session_backend(
                    backend=llm_router.active_backend,
                    model_name=llm_router.active_model or "unknown",
                    had_fallback=llm_router.had_fallback,
                )
                first_message = False

            # Handle tool calls
            if response.has_tool_calls and response.message.tool_calls:
                messages.append(response.message)

                for tool_call in response.message.tool_calls:
                    console.print(
                        f"\n[yellow]Running:[/yellow] {tool_call.name}"
                        f"({', '.join(f'{k}={v}' for k, v in tool_call.arguments.items())})"
                    )

                    result = await tool_registry.execute(tool_call)

                    # Show condensed result
                    if len(result.content) > 200:
                        preview = result.content[:200] + "..."
                    else:
                        preview = result.content
                    console.print(Panel(preview, title=f"{tool_call.name} result", border_style="dim"))

                    # Add tool response to conversation
                    messages.append(
                        ChatMessage(
                            role="tool",
                            content=result.content,
                            tool_call_id=tool_call.id,
                            name=tool_call.name,
                        )
                    )

                # Get final response
                response = await llm_router.chat(
                    messages=messages,
                    tools=tools,
                    temperature=0.3,
                )

            # Add assistant response
            messages.append(response.message)

            # Display response
            console.print("\n[bold blue]Assistant[/bold blue]")
            md = Markdown(response.content)
            console.print(md)
            
            # If resolution was detected, prompt for feedback
            if resolution_detected:
                console.print("\n[dim]It looks like your issue may be resolved![/dim]")
                want_feedback = Prompt.ask(
                    "Would you like to provide feedback?",
                    choices=["y", "n"],
                    default="n",
                )
                if want_feedback == "y":
                    prompt_for_feedback(collector)
                    # Start new session
                    session = collector.start_session()
                    console.print(f"\n[dim]New session: {session.session_id[:8]}...[/dim]")
                    messages = [ChatMessage(role="system", content=system_prompt)]
                    first_message = True
                resolution_detected = False

        except KeyboardInterrupt:
            console.print("\n\n[dim]Interrupted. Goodbye![/dim]")
            collector.end_session(outcome=SessionOutcome.ABANDONED)
            break

        except Exception as e:
            console.print(f"\n[red]Error:[/red] {e}")
            if settings.debug:
                console.print_exception()

    # Cleanup
    await llm_router.close()


@app.command()
def chat():
    """Start interactive chat session."""
    asyncio.run(run_chat_loop())


@app.command()
def check(
    diagnostic: str = typer.Argument(
        ...,
        help="Diagnostic to run: adapter, ip, gateway, dns-ping, dns-resolve",
    ),
):
    """Run a single diagnostic check."""

    async def run_diagnostic():
        tool_registry = get_registry()

        from .diagnostics import register_all_diagnostics

        register_all_diagnostics(tool_registry)

        # Map short names to tool names
        name_map = {
            "adapter": "check_adapter_status",
            "ip": "get_ip_config",
            "gateway": "ping_gateway",
            "dns-ping": "ping_dns",
            "dns-resolve": "test_dns_resolution",
        }

        tool_name = name_map.get(diagnostic, diagnostic)
        tool = tool_registry.get_tool(tool_name)

        if not tool:
            console.print(f"[red]Unknown diagnostic:[/red] {diagnostic}")
            console.print(f"Available: {', '.join(name_map.keys())}")
            return

        console.print(f"\n[bold]Running {tool_name}...[/bold]\n")

        result = await tool()

        # Display result
        if hasattr(result, "to_llm_response"):
            md = Markdown(result.to_llm_response())
            console.print(md)
        else:
            console.print(result)

    asyncio.run(run_diagnostic())


@app.command()
def ladder():
    """Run full diagnostic ladder (all checks in sequence)."""

    async def run_ladder():
        tool_registry = get_registry()

        from .diagnostics import register_all_diagnostics

        register_all_diagnostics(tool_registry)

        checks = [
            ("check_adapter_status", "Checking network adapters..."),
            ("get_ip_config", "Checking IP configuration..."),
            ("ping_gateway", "Testing gateway connectivity..."),
            ("ping_dns", "Testing external connectivity..."),
            ("test_dns_resolution", "Testing DNS resolution..."),
        ]

        console.print("\n[bold blue]Running Diagnostic Ladder[/bold blue]\n")

        all_passed = True
        for tool_name, message in checks:
            console.print(f"[yellow]→[/yellow] {message}")

            tool = tool_registry.get_tool(tool_name)
            if not tool:
                console.print(f"  [red]✗[/red] Tool not found: {tool_name}")
                all_passed = False
                continue

            try:
                result = await tool()

                if result.success and result.data.get("reachable", True):
                    console.print(f"  [green]✓[/green] Passed")
                else:
                    console.print(f"  [red]✗[/red] Failed")
                    if result.suggestions:
                        for suggestion in result.suggestions[:2]:
                            console.print(f"    → {suggestion}")
                    all_passed = False

            except Exception as e:
                console.print(f"  [red]✗[/red] Error: {e}")
                all_passed = False

        console.print()
        if all_passed:
            console.print("[bold green]All checks passed![/bold green]")
        else:
            console.print(
                "[bold yellow]Some checks failed.[/bold yellow] "
                "Run 'network-diag chat' for AI-assisted troubleshooting."
            )

    asyncio.run(run_ladder())


def main():
    """Entry point."""
    app()


if __name__ == "__main__":
    main()


