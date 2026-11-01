from __future__ import annotations

from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from emporio_agent.agent import EmporioAgent
from emporio_agent.config import PROJECT_ROOT
from emporio_agent.data_loader import ingest_csvs
from emporio_agent.policies_rag import ensure_policy_index

console = Console()


def _bootstrap() -> None:
    console.print("[dim]Preparando dados e índice de políticas...[/dim]")
    ingest_csvs()
    ensure_policy_index()


def main() -> None:
    _bootstrap()
    try:
        agent = EmporioAgent()
    except RuntimeError as e:
        console.print(f"[red]{e}[/red]")
        raise SystemExit(1) from e

    console.print(
        Panel(
            "Empório da Música — Assistente virtual\n"
            "Comandos: /sair  /limpar  /export [nome.md]",
            title="Bem-vindo",
        )
    )

    while True:
        try:
            user_input = console.input("[bold cyan]Você:[/bold cyan] ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\nAté logo!")
            break

        if not user_input:
            continue
        if user_input.lower() in {"/sair", "/exit", "sair"}:
            console.print("Até logo!")
            break
        if user_input.lower() == "/limpar":
            agent.reset()
            console.print("[dim]Histórico da sessão limpo.[/dim]")
            continue
        if user_input.lower().startswith("/export"):
            parts = user_input.split(maxsplit=1)
            name = parts[1] if len(parts) > 1 else f"conversa_{datetime.now():%Y%m%d_%H%M%S}.md"
            if not name.endswith(".md"):
                name += ".md"
            out_dir = PROJECT_ROOT / "examples" / "conversations"
            out_dir.mkdir(parents=True, exist_ok=True)
            path = out_dir / name
            path.write_text(agent.export_transcript(), encoding="utf-8")
            console.print(f"[green]Exportado:[/green] {path}")
            continue

        with console.status("[dim]Pensando...[/dim]"):
            reply = agent.chat(user_input)
        console.print(Panel(Markdown(reply), title="Assistente", border_style="green"))


if __name__ == "__main__":
    main()
