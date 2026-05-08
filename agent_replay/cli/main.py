"""agent-replay CLI — Typer entry point.

All subcommands accept --db to override the database location.
"""

from __future__ import annotations

import typer

app = typer.Typer(
    name="agent-replay",
    help="Dead-simple, local-first agent observability.",
    no_args_is_help=True,
)


@app.command("list")
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


@app.command("show")
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
                tokens_str = f"{s.input_tokens} / {s.output_tokens}"
                latency = f"{s.latency_ms}ms" if s.latency_ms else "—"
                error = (
                    s.error[:30] + "…"
                    if s.error and len(s.error) > 30
                    else (s.error or "—")
                )
                verdict = s.verdict or "—"
                table.add_row(
                    str(s.sequence), s.type, latency, tokens_str,
                    f"${s.cost_usd:.4f}", error, verdict,
                )

            console.print(table)

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


@app.command("diff")
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
        console.print(Panel(
            f"[bold]{result.summary}[/]",
            title=f"Diff: {session_a[:12]} ↔ {session_b[:12]}",
            border_style="cyan",
        ))
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
                    str(a_step.sequence), a_step.type, b_step.type,
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


@app.command("replay")
def replay(
    session_id: str = typer.Argument(..., help="Session ID to replay"),
    model: str | None = typer.Option(None, "--model", help="Override the model"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print plan without executing"),
    db: str | None = typer.Option(None, "--db", help="Database path"),
) -> None:
    """Re-execute a recorded session against a (possibly different) model."""
    from agent_replay.replay import replay_session
    from agent_replay.store import Store

    store = Store(db_path=db)
    try:
        result = replay_session(
            session_id, model_override=model, dry_run=dry_run, store=store
        )
        if result:
            typer.echo(f"✅ Replay complete. New session: {result.id}")
            typer.echo(
                f"   {result.total_input_tokens + result.total_output_tokens} tokens, "
                f"${result.total_cost_usd:.4f}"
            )
    except ValueError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1) from e
    finally:
        store.close()


@app.command("annotate")
def annotate(
    session_id: str = typer.Argument(..., help="Session ID to annotate"),
    note: str = typer.Option(..., "--note", "-n", help="Annotation text"),
    step: str | None = typer.Option(None, "--step", help="Step ID (annotate specific step)"),
    verdict: str | None = typer.Option(None, "--verdict", "-v", help="Verdict: pass or fail"),
    db: str | None = typer.Option(None, "--db", help="Database path"),
) -> None:
    """Attach a human note and optional verdict to a session or step."""
    from agent_replay.store import Store

    if verdict and verdict not in ("pass", "fail"):
        typer.echo("Error: --verdict must be 'pass' or 'fail'", err=True)
        raise typer.Exit(code=1)

    store = Store(db_path=db)
    try:
        session = store.get_session(session_id, include_steps=False)
        if session is None:
            typer.echo(f"Error: session not found: {session_id}", err=True)
            raise typer.Exit(code=1)

        store.update_annotation(
            session_id=session_id, step_id=step, note=note, verdict=verdict,
        )

        target = f"step {step}" if step else f"session {session_id[:12]}"
        typer.echo(f"✅ Annotated {target}")
        if verdict:
            typer.echo(f"   Verdict: {verdict}")
    finally:
        store.close()


@app.command("export")
def export_command(
    session_id: str = typer.Argument(..., help="Session ID to export"),
    fmt: str = typer.Option("jsonl", "--format", "-f", help="Export format: jsonl or html"),
    out: str | None = typer.Option(None, "--out", "-o", help="Output file path"),
    db: str | None = typer.Option(None, "--db", help="Database path"),
) -> None:
    """Export a session as JSONL or HTML."""
    from agent_replay.export import export_html, export_jsonl
    from agent_replay.store import Store

    if fmt not in ("jsonl", "html"):
        typer.echo("Error: --format must be 'jsonl' or 'html'", err=True)
        raise typer.Exit(code=1)

    store = Store(db_path=db)
    try:
        session = store.get_session(session_id, include_steps=True)
        if session is None:
            typer.echo(f"Error: session not found: {session_id}", err=True)
            raise typer.Exit(code=1)

        if fmt == "jsonl":
            content = export_jsonl(session)
        else:
            content = export_html(session)

        if out:
            with open(out, "w") as f:
                f.write(content)
            typer.echo(f"✅ Exported to {out}")
        else:
            typer.echo(content)
    finally:
        store.close()


@app.command("stats")
def stats_command(
    days: int = typer.Option(7, "--days", "-d", help="Number of days to aggregate"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
    db: str | None = typer.Option(None, "--db", help="Database path"),
) -> None:
    """Aggregate cost and token usage across recent sessions."""
    import json as json_mod
    from datetime import datetime, timedelta

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
            for fw, fw_data in sorted(by_framework.items()):
                table.add_row(
                    fw,
                    str(int(fw_data["sessions"])),
                    f"{int(fw_data['tokens']):,}",
                    f"${float(fw_data['cost']):.4f}",
                )
            console.print(table)
    finally:
        store.close()


if __name__ == "__main__":
    app()
