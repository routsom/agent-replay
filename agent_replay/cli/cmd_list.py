"""agent-replay list — List recent sessions."""

from __future__ import annotations

import typer

app = typer.Typer()


@app.callback(invoke_without_command=True)
def list_sessions(
    limit: int = typer.Option(20, "--limit", "-n", help="Max sessions to display"),
    tag: str | None = typer.Option(None, "--tag", "-t", help="Filter by tag"),
    framework: str | None = typer.Option(None, "--framework", "-f", help="Filter by framework"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
    db: str | None = typer.Option(None, "--db", help="Database path"),
) -> None:
    """List recent sessions in a table."""
    import json as json_mod

    from rich.console import Console
    from rich.table import Table

    from agent_replay.store import Store

    store = Store(db_path=db)
    try:
        sessions = store.list_sessions(limit=limit, tag=tag, framework=framework)

        if json_output:
            data = [
                {
                    "id": s.id,
                    "name": s.name,
                    "framework": s.framework,
                    "model": s.model,
                    "status": s.status,
                    "started_at": s.started_at.isoformat(),
                    "total_cost_usd": s.total_cost_usd,
                    "total_input_tokens": s.total_input_tokens,
                    "total_output_tokens": s.total_output_tokens,
                    "tags": s.tags,
                }
                for s in sessions
            ]
            typer.echo(json_mod.dumps(data, indent=2))
            return

        console = Console()
        if not sessions:
            console.print("[dim]No sessions found.[/dim]")
            return

        table = Table(title="Agent Sessions", show_lines=False)
        table.add_column("ID", style="cyan", max_width=12)
        table.add_column("Name", style="white")
        table.add_column("Framework", style="magenta")
        table.add_column("Model", style="yellow")
        table.add_column("Steps", justify="right")
        table.add_column("Tokens", justify="right")
        table.add_column("Cost", justify="right", style="green")
        table.add_column("Status", style="blue")
        table.add_column("Started", style="dim")

        for s in sessions:
            steps = store.get_steps(s.id)
            tokens = s.total_input_tokens + s.total_output_tokens
            table.add_row(
                s.id[:12],
                s.name or "—",
                s.framework,
                s.model,
                str(len(steps)),
                f"{tokens:,}",
                f"${s.total_cost_usd:.4f}",
                s.status,
                s.started_at.strftime("%Y-%m-%d %H:%M"),
            )

        console.print(table)
    finally:
        store.close()
