"""agent-replay stats — Aggregate cost and token usage."""

from __future__ import annotations

from datetime import datetime, timedelta

import typer

app = typer.Typer()


@app.callback(invoke_without_command=True)
def stats_command(
    days: int = typer.Option(7, "--days", "-d", help="Number of days to aggregate"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
    db: str | None = typer.Option(None, "--db", help="Database path"),
) -> None:
    """Aggregate cost and token usage across recent sessions."""
    import json as json_mod

    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table

    from agent_replay.store import Store

    store = Store(db_path=db)
    try:
        sessions = store.list_sessions(limit=10000)
        cutoff = datetime.now() - timedelta(days=days)
        recent = [s for s in sessions if s.started_at >= cutoff]

        total_sessions = len(recent)
        total_input_tokens = sum(s.total_input_tokens for s in recent)
        total_output_tokens = sum(s.total_output_tokens for s in recent)
        total_cost = sum(s.total_cost_usd for s in recent)
        total_steps = sum(len(store.get_steps(s.id)) for s in recent)

        # Group by framework
        by_framework: dict[str, dict[str, float | int]] = {}
        for s in recent:
            fw = s.framework
            if fw not in by_framework:
                by_framework[fw] = {"sessions": 0, "tokens": 0, "cost": 0.0}
            by_framework[fw]["sessions"] = int(by_framework[fw]["sessions"]) + 1
            by_framework[fw]["tokens"] = (
                int(by_framework[fw]["tokens"]) + s.total_input_tokens + s.total_output_tokens
            )
            by_framework[fw]["cost"] = float(by_framework[fw]["cost"]) + s.total_cost_usd

        if json_output:
            data = {
                "period_days": days,
                "total_sessions": total_sessions,
                "total_steps": total_steps,
                "total_input_tokens": total_input_tokens,
                "total_output_tokens": total_output_tokens,
                "total_tokens": total_input_tokens + total_output_tokens,
                "total_cost_usd": total_cost,
                "by_framework": by_framework,
            }
            typer.echo(json_mod.dumps(data, indent=2))
            return

        console = Console()

        summary = (
            f"[bold cyan]Period:[/]        Last {days} days\n"
            f"[bold cyan]Sessions:[/]      {total_sessions}\n"
            f"[bold cyan]Steps:[/]         {total_steps}\n"
            f"[bold cyan]Input tokens:[/]  {total_input_tokens:,}\n"
            f"[bold cyan]Output tokens:[/] {total_output_tokens:,}\n"
            f"[bold cyan]Total tokens:[/]  {total_input_tokens + total_output_tokens:,}\n"
            f"[bold cyan]Total cost:[/]    ${total_cost:.4f}"
        )
        console.print(Panel(summary, title="Usage Statistics", border_style="cyan"))

        if by_framework:
            table = Table(title="By Framework")
            table.add_column("Framework", style="magenta")
            table.add_column("Sessions", justify="right")
            table.add_column("Tokens", justify="right")
            table.add_column("Cost", justify="right", style="green")
            for fw, data_dict in sorted(by_framework.items()):
                table.add_row(
                    fw,
                    str(int(data_dict["sessions"])),
                    f"{int(data_dict['tokens']):,}",
                    f"${float(data_dict['cost']):.4f}",
                )
            console.print(table)

    finally:
        store.close()
