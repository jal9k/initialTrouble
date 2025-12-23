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
from .tools import ToolRegistry, get_registry, ToolResult
from .prompts import AgentType, load_prompt, get_prompt_for_context
from .logging_config import setup_logging, get_logger

# Import analytics
from analytics import AnalyticsCollector, AnalyticsStorage
from analytics.models import SessionOutcome, IssueCategory

# #region debug
from datetime import datetime
from .logging_config import debug_log, ResponseDiagnostics
# #endregion

# Initialize logging
logger = get_logger("network_diag.cli")

# =============================================================================
# CONSTANTS
# =============================================================================

# Maximum tool call iterations to prevent infinite loops
MAX_TOOL_ITERATIONS = 7

# Tools that modify system state and require verification after execution
ACTION_TOOLS = {"enable_wifi", "disable_wifi", "reset_network"}

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


# =============================================================================
# TOOL EXECUTION LOOP
# =============================================================================

async def execute_tool_loop(
    llm_router: LLMRouter,
    tool_registry: ToolRegistry,
    messages: list[ChatMessage],
    tools: list,
    diagnostics: "ResponseDiagnostics | None" = None,
    max_iterations: int = MAX_TOOL_ITERATIONS,
) -> tuple[ChatMessage, bool]:
    """
    Execute tools in a loop until the model stops requesting them.
    
    This implements the core agentic loop:
    1. Send messages to LLM (forcing tool call on first iteration)
    2. If LLM returns tool calls, execute them
    3. Add tool results to messages
    4. Repeat until no more tool calls or max iterations reached
    
    Args:
        llm_router: The LLM router instance
        tool_registry: The tool registry with registered diagnostics
        messages: Current conversation messages (modified in place)
        tools: List of available tool definitions
        diagnostics: Optional ResponseDiagnostics for debug tracking
        max_iterations: Maximum number of tool call iterations
    
    Returns:
        tuple of (final_message, action_tool_was_called)
    """
    action_tool_called = False
    
    for iteration in range(max_iterations):
        # Force tool call on first iteration, allow auto on subsequent
        tool_choice = "required" if iteration == 0 else "auto"
        
        # #region debug
        debug_log("AgentExecutor", f"Tool loop iteration {iteration + 1}/{max_iterations}", {
            "tool_choice": tool_choice,
            "message_count": len(messages),
        })
        if diagnostics:
            diagnostics.add_thought(f"Tool loop iteration {iteration + 1}, tool_choice={tool_choice}")
        # #endregion
        
        logger.info(f"Tool loop iteration {iteration + 1}/{max_iterations}, tool_choice={tool_choice}")
        
        # Get LLM response
        response = await llm_router.chat(
            messages=messages,
            tools=tools,
            temperature=0.3,
            tool_choice=tool_choice,
        )
        
        # If no tool calls, we're done
        if not response.has_tool_calls or not response.message.tool_calls:
            # #region debug
            debug_log("AgentExecutor", "No tool calls, ending loop", {
                "iteration": iteration + 1,
                "has_content": bool(response.content),
            })
            if diagnostics:
                diagnostics.add_thought(f"No tool calls in iteration {iteration + 1}, ending loop")
            # #endregion
            logger.info(f"No tool calls in iteration {iteration + 1}, ending loop")
            return response.message, action_tool_called
        
        # Add assistant message with tool calls to history
        messages.append(response.message)
        logger.info(f"LLM requested {len(response.message.tool_calls)} tool call(s)")
        
        # Execute each tool call
        for tool_call in response.message.tool_calls:
            logger.info(f"Executing tool: {tool_call.name} with args: {tool_call.arguments}")
            
            # Display to user
            args_str = ", ".join(f"{k}={v}" for k, v in tool_call.arguments.items())
            console.print(f"\n[yellow]Running:[/yellow] {tool_call.name}({args_str})")
            
            # Execute the tool with error handling
            try:
                result = await tool_registry.execute(tool_call)
            except Exception as e:
                logger.exception(f"Tool execution failed: {e}")
                result = ToolResult(
                    tool_call_id=tool_call.id,
                    name=tool_call.name,
                    content=f"Tool execution failed: {e}",
                    success=False,
                )
            
            logger.debug(f"Tool result success: {result.success}")
            
            # Display condensed result
            preview = result.content[:300] + "..." if len(result.content) > 300 else result.content
            console.print(Panel(preview, title=f"{tool_call.name} result", border_style="dim"))
            
            # #region debug
            debug_log("AgentExecutor", f"Tool {tool_call.name} completed", {
                "success": result.success,
                "content_length": len(result.content),
            })
            if diagnostics:
                diagnostics.add_tool_result(tool_call.name, {
                    "success": result.success,
                    "content_preview": result.content[:100],
                })
                diagnostics.add_thought(f"Tool '{tool_call.name}' returned success={result.success}")
            # #endregion
            
            # Add tool result to messages
            messages.append(
                ChatMessage(
                    role="tool",
                    content=result.content,
                    tool_call_id=tool_call.id,
                    name=tool_call.name,
                )
            )
            
            # Track if an action tool was called
            if tool_call.name in ACTION_TOOLS:
                action_tool_called = True
    
    # Max iterations reached - get final response without tool forcing
    logger.warning(f"Reached max iterations ({max_iterations}), getting final response")
    
    # #region debug
    debug_log("AgentExecutor", "Max iterations reached", {"max": max_iterations})
    if diagnostics:
        diagnostics.add_thought(f"Reached max iterations ({max_iterations})")
    # #endregion
    
    response = await llm_router.chat(
        messages=messages,
        tools=tools,
        temperature=0.3,
        tool_choice="none",  # Prevent further tool calls
    )
    
    return response.message, action_tool_called


async def run_verification(
    llm_router: LLMRouter,
    tool_registry: ToolRegistry,
    messages: list[ChatMessage],
    tools: list,
) -> tuple[bool, ChatMessage | None]:
    """
    Run verification diagnostics after an action tool was executed.
    
    Ensures that fixes like enable_wifi actually worked by running
    connectivity tests.
    
    Args:
        llm_router: The LLM router instance
        tool_registry: The tool registry
        messages: Conversation messages
        tools: Available tools
    
    Returns:
        Tuple of (verification_passed, verification_message)
    """
    console.print("\n[dim]Verifying fix...[/dim]")
    
    # #region debug
    debug_log("AgentExecutor", "Running verification after action tool", {})
    # #endregion
    
    # Inject a verification instruction
    messages.append(ChatMessage(
        role="user",
        content=(
            "[SYSTEM: A fix was just applied. Run check_adapter_status and ping_dns "
            "to verify the network is now working. Then report the results.]"
        ),
    ))
    
    # Run verification loop with limited iterations
    final_msg, _ = await execute_tool_loop(
        llm_router=llm_router,
        tool_registry=tool_registry,
        messages=messages,
        tools=tools,
        max_iterations=3,  # Verification should be quick
    )
    
    messages.append(final_msg)
    
    # Check if verification passed - must handle negations properly
    content_lower = (final_msg.content or "").lower()
    
    # Negative indicators take precedence - if found, verification failed
    negative_patterns = [
        r"\bnot\s+working\b",
        r"\bnot\s+connected\b",
        r"\bno\s+connection\b",
        r"\bno\s+internet\b",
        r"\bunreachable\b",
        r"\bfailed\b",
        r"\bcannot\s+reach\b",
        r"\bcan't\s+reach\b",
        r"\bstill\s+down\b",
        r"\bnot\s+reachable\b",
        r"\bno\s+network\b",
        r"\bdisconnected\b",
    ]
    
    has_negative = any(re.search(pattern, content_lower) for pattern in negative_patterns)
    
    if has_negative:
        verification_passed = False
    else:
        # Only check positive indicators if no negations found
        positive_phrases = [
            "working",
            "connected",
            "successful",
            "verified",
            "internet is accessible",
            "network is healthy",
            "reachable",
            "connection restored",
            "now online",
        ]
        verification_passed = any(phrase in content_lower for phrase in positive_phrases)
    
    # #region debug
    debug_log("AgentExecutor", "Verification completed", {
        "passed": verification_passed,
        "has_negative": has_negative,
    })
    # #endregion
    
    return verification_passed, final_msg


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
    
    # Setup logging
    log_level = "DEBUG" if settings.debug else "INFO"
    setup_logging(level=log_level)
    logger.info("Starting chat loop")
    
    # Initialize analytics
    db_path = Path("data/analytics.db")
    db_path.parent.mkdir(parents=True, exist_ok=True)
    storage = AnalyticsStorage(db_path)
    collector = AnalyticsCollector(storage=storage)
    
    # Initialize LLM router with analytics
    llm_router = LLMRouter(settings, analytics_collector=collector)
    tool_registry = get_registry()
    logger.info(f"Using LLM backend preference: {settings.llm_backend}")
    
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
            logger.info(f"User message: {user_input[:100]}...")
            
            # #region debug
            debug_log("AgentExecutor", "Executing agent call", {
                "user_query": user_input[:100],
                "message_count": len(messages),
            })
            diagnostics = ResponseDiagnostics()
            diagnostics.add_thought(f"User input: {len(user_input)} chars")
            # #endregion
            
            # Check for resolution signal
            if detect_resolution_signal(user_input):
                resolution_detected = True
                # #region debug
                diagnostics.add_thought("Resolution signal detected in user input")
                # #endregion

            # Add user message
            messages.append(ChatMessage(role="user", content=user_input))

            # Get response with tools
            console.print("\n[dim]Thinking...[/dim]")

            tools = tool_registry.get_all_definitions()
            logger.debug(f"Available tools: {[t.name for t in tools]}")
            
            # Set backend info after first LLM call
            if first_message and llm_router.active_backend:
                collector.set_session_backend(
                    backend=llm_router.active_backend,
                    model_name=llm_router.active_model or "unknown",
                    had_fallback=llm_router.had_fallback,
                )
                first_message = False
            
            # #region debug
            diagnostics.add_thought(f"Available tools: {len(tools)}")
            # #endregion
            
            # =================================================================
            # MULTI-TURN TOOL EXECUTION LOOP
            # =================================================================
            final_message, action_tool_called = await execute_tool_loop(
                llm_router=llm_router,
                tool_registry=tool_registry,
                messages=messages,
                tools=tools,
                diagnostics=diagnostics,
            )
            
            # Add final response to messages
            messages.append(final_message)
            
            # Display initial response with timestamp
            # #region debug
            ts = datetime.now().strftime("%H:%M:%S")
            console.print(f"\n[bold blue]Assistant [{ts}][/bold blue]")
            # #endregion
            # If not in debug mode, this line handles display:
            if final_message.content:
                md = Markdown(final_message.content)
                console.print(md)
            else:
                console.print("[dim]No response content[/dim]")
            
            # Run verification if an action tool was called
            if action_tool_called:
                # #region debug
                diagnostics.add_thought("Action tool called - running verification")
                # #endregion
                verification_passed, verification_msg = await run_verification(
                    llm_router=llm_router,
                    tool_registry=tool_registry,
                    messages=messages,
                    tools=tools,
                )
                
                # Display verification result to user
                if verification_msg and verification_msg.content:
                    console.print(f"\n[bold blue]Verification Result[/bold blue]")
                    md = Markdown(verification_msg.content)
                    console.print(md)
                
                if verification_passed:
                    console.print("\n[green]✓ Verified: Connection is working[/green]")
                    # #region debug
                    diagnostics.add_thought("Verification passed")
                    diagnostics.set_confidence(0.9)
                    # #endregion
                else:
                    console.print("\n[yellow]⚠ Verification: Connection may still have issues[/yellow]")
                    # #region debug
                    diagnostics.add_thought("Verification failed - issues detected")
                    diagnostics.set_confidence(0.4)
                    # #endregion
            
            # #region debug
            # Display Response Diagnostics panel
            console.print(Panel(
                diagnostics.to_panel_content(),
                title="Response Diagnostics",
                border_style="dim",
            ))
            debug_log("AgentExecutor", "Turn completed", {
                "confidence": diagnostics.confidence_score,
                "tools_used": len(diagnostics.tools_used),
            })
            # #endregion
            
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
            logger.exception(f"Error in chat loop: {e}")
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


