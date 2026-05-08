"""agent-replay diff — Side-by-side diff of two sessions."""

from __future__ import annotations

import typer

app = typer.Typer()


@app.callback(invoke_without_command=True)
def diff_command(
    session_a: str = typer.Argument(..., help="First session ID (baseline)"),
    session_b: str = typer.Argument(..., help="Second session ID (comparison)"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
    db: str | None = typer.Option(None, "--db", help="Database path"),
) -> None:
    """Side-by-side diff of two runs."""
    import json as json_mod

    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table

    from agent_replay.diff import diff_sessions
    from agent_replay.store import Store

    store = Store(db_path=db)
    try:
        result = diff_sessions(session_a, session_b, store=store)

        if json_output:
            data = {
                "session_a": result.session_a,
                "session_b": result.session_b,
                "steps_added": len(result.steps_added),
                "steps_removed": len(result.steps_removed),
                "steps_changed": len(result.steps_changed),
                "cost_delta_usd": result.cost_delta_usd,
                "token_delta": result.token_delta,
                "summary": result.summary,
            }
            typer.echo(json_mod.dumps(data, indent=2))
            return

        console = Console()

        # Summary panel
        console.print(Panel(
            f"[bold]{result.summary}[/]",
            title=f"Diff: {session_a[:12]} ↔ {session_b[:12]}",
            border_style="cyan",
        ))

        # Stats
        console.print(f"  Token delta: [yellow]{result.token_delta:+,}[/]")
        console.print(f"  Cost delta:  [green]${result.cost_delta_usd:+.4f}[/]")
        console.print()

        if result.steps_added:
            table = Table(title=f"Added Steps ({len(result.steps_added)})", style="green")
            table.add_column("#", justify="right")
            table.add_column("Type")
            table.add_column("Tokens", justify="right")
            for s in result.steps_added:
                table.add_row(str(s.sequence), s.type, f"{s.input_tokens + s.output_tokens}")
            console.print(table)

        if result.steps_removed:
            table = Table(title=f"Removed Steps ({len(result.steps_removed)})", style="red")
            table.add_column("#", justify="right")
            table.add_column("Type")
            table.add_column("Tokens", justify="right")
            for s in result.steps_removed:
                table.add_row(str(s.sequence), s.type, f"{s.input_tokens + s.output_tokens}")
            console.print(table)

        if result.steps_changed:
            table = Table(title=f"Changed Steps ({len(result.steps_changed)})", style="yellow")
            table.add_column("#", justify="right")
            table.add_column("Type A")
            table.add_column("Type B")
            table.add_column("Tokens A", justify="right")
            table.add_column("Tokens B", justify="right")
            for a_step, b_step in result.steps_changed:
                table.add_row(
                    str(a_step.sequence),
                    a_step.type,
                    b_step.type,
                    str(a_step.input_tokens + a_step.output_tokens),
                    str(b_step.input_tokens + b_step.output_tokens),
                )
            console.print(table)

        if not (result.steps_added or result.steps_removed or result.steps_changed):
            console.print("[dim]Sessions are identical.[/dim]")

    except ValueError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1) from e
    finally:
        store.close()
