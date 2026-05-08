"""agent-replay show — Show session details."""

from __future__ import annotations

import typer

app = typer.Typer()


@app.callback(invoke_without_command=True)
def show_session(
    session_id: str = typer.Argument(..., help="Session ID to show"),
    steps: bool = typer.Option(False, "--steps", "-s", help="Show individual steps"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
    db: str | None = typer.Option(None, "--db", help="Database path"),
) -> None:
    """Show full detail for a session."""
    import json as json_mod

    from rich.console import Console
    from rich.panel import Panel
    from rich.syntax import Syntax
    from rich.table import Table

    from agent_replay.store import Store

    store = Store(db_path=db)
    try:
        session = store.get_session(session_id, include_steps=True)
        if session is None:
            typer.echo(f"Error: session not found: {session_id}", err=True)
            raise typer.Exit(code=1)

        if json_output:
            data = {
                "id": session.id,
                "name": session.name,
                "framework": session.framework,
                "model": session.model,
                "status": session.status,
                "started_at": session.started_at.isoformat(),
                "ended_at": session.ended_at.isoformat() if session.ended_at else None,
                "tags": session.tags,
                "metadata": session.metadata,
                "total_input_tokens": session.total_input_tokens,
                "total_output_tokens": session.total_output_tokens,
                "total_cost_usd": session.total_cost_usd,
                "steps": [
                    {
                        "id": s.id,
                        "sequence": s.sequence,
                        "type": s.type,
                        "started_at": s.started_at.isoformat(),
                        "ended_at": s.ended_at.isoformat() if s.ended_at else None,
                        "latency_ms": s.latency_ms,
                        "input": s.input,
                        "output": s.output,
                        "input_tokens": s.input_tokens,
                        "output_tokens": s.output_tokens,
                        "cost_usd": s.cost_usd,
                        "error": s.error,
                        "annotation": s.annotation,
                        "verdict": s.verdict,
                    }
                    for s in session.steps
                ],
            }
            typer.echo(json_mod.dumps(data, indent=2, default=str))
            return

        console = Console()

        # Session summary panel
        total_tokens = session.total_input_tokens + session.total_output_tokens
        ended = session.ended_at.strftime("%Y-%m-%d %H:%M:%S") if session.ended_at else "—"
        summary = (
            f"[bold cyan]ID:[/]         {session.id}\n"
            f"[bold cyan]Name:[/]       {session.name or '—'}\n"
            f"[bold cyan]Framework:[/]  {session.framework}\n"
            f"[bold cyan]Model:[/]      {session.model}\n"
            f"[bold cyan]Status:[/]     {session.status}\n"
            f"[bold cyan]Started:[/]    {session.started_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"[bold cyan]Ended:[/]      {ended}\n"
            f"[bold cyan]Tags:[/]       {', '.join(session.tags) or '—'}\n"
            f"[bold cyan]Steps:[/]      {len(session.steps)}\n"
            f"[bold cyan]Tokens:[/]     {total_tokens:,}"
            f" ({session.total_input_tokens:,} in"
            f" / {session.total_output_tokens:,} out)\n"
            f"[bold cyan]Cost:[/]       ${session.total_cost_usd:.4f}"
        )
        console.print(Panel(summary, title="Session", border_style="cyan"))

        if steps and session.steps:
            table = Table(title="Steps", show_lines=True)
            table.add_column("#", style="cyan", justify="right")
            table.add_column("Type", style="magenta")
            table.add_column("Latency", justify="right")
            table.add_column("Tokens", justify="right")
            table.add_column("Cost", justify="right", style="green")
            table.add_column("Error", style="red", max_width=30)
            table.add_column("Verdict", style="bold")

            for s in session.steps:
                tokens = f"{s.input_tokens} / {s.output_tokens}"
                latency = f"{s.latency_ms}ms" if s.latency_ms else "—"
                error = s.error[:30] + "…" if s.error and len(s.error) > 30 else (s.error or "—")
                verdict = s.verdict or "—"
                table.add_row(
                    str(s.sequence),
                    s.type,
                    latency,
                    tokens,
                    f"${s.cost_usd:.4f}",
                    error,
                    verdict,
                )

            console.print(table)

            # Print step details
            for s in session.steps:
                input_json = json_mod.dumps(s.input, indent=2, default=str)
                output_json = json_mod.dumps(s.output, indent=2, default=str)
                console.print(f"\n[bold cyan]Step #{s.sequence}[/] — {s.type}")
                console.print(Panel(Syntax(input_json, "json", theme="monokai"), title="Input"))
                console.print(Panel(Syntax(output_json, "json", theme="monokai"), title="Output"))
                if s.annotation:
                    console.print(f"  📝 [yellow]{s.annotation}[/]")
    finally:
        store.close()
