"""agent-replay annotate — Attach notes and verdicts."""

from __future__ import annotations

import typer

app = typer.Typer()


@app.callback(invoke_without_command=True)
def annotate(
    session_id: str = typer.Argument(..., help="Session ID to annotate"),
    step: str | None = typer.Option(None, "--step", help="Step ID (annotate specific step)"),
    note: str = typer.Option(..., "--note", "-n", help="Annotation text"),
    verdict: str | None = typer.Option(
        None, "--verdict", "-v", help="Verdict: pass or fail"
    ),
    db: str | None = typer.Option(None, "--db", help="Database path"),
) -> None:
    """Attach a human note and optional verdict to a session or step."""
    from agent_replay.store import Store

    if verdict and verdict not in ("pass", "fail"):
        typer.echo("Error: --verdict must be 'pass' or 'fail'", err=True)
        raise typer.Exit(code=1)

    store = Store(db_path=db)
    try:
        # Verify session exists
        session = store.get_session(session_id, include_steps=False)
        if session is None:
            typer.echo(f"Error: session not found: {session_id}", err=True)
            raise typer.Exit(code=1)

        store.update_annotation(
            session_id=session_id,
            step_id=step,
            note=note,
            verdict=verdict,
        )

        target = f"step {step}" if step else f"session {session_id[:12]}"
        typer.echo(f"✅ Annotated {target}")
        if verdict:
            typer.echo(f"   Verdict: {verdict}")
    finally:
        store.close()
