"""agent-replay export — Export sessions to JSONL or HTML."""

from __future__ import annotations

import typer

app = typer.Typer()


@app.callback(invoke_without_command=True)
def export_command(
    session_id: str = typer.Argument(..., help="Session ID to export"),
    format: str = typer.Option(  # noqa: A002
        "jsonl", "--format", "-f", help="Export format: jsonl or html"
    ),
    out: str | None = typer.Option(None, "--out", "-o", help="Output file path"),
    db: str | None = typer.Option(None, "--db", help="Database path"),
) -> None:
    """Export a session as JSONL or HTML."""
    from agent_replay.export import export_html, export_jsonl
    from agent_replay.store import Store

    if format not in ("jsonl", "html"):
        typer.echo("Error: --format must be 'jsonl' or 'html'", err=True)
        raise typer.Exit(code=1)

    store = Store(db_path=db)
    try:
        session = store.get_session(session_id, include_steps=True)
        if session is None:
            typer.echo(f"Error: session not found: {session_id}", err=True)
            raise typer.Exit(code=1)

        if format == "jsonl":
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
