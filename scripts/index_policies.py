"""Indexa PDF de políticas no Chroma."""

import sys

from emporio_agent.policies_rag import ensure_policy_index


def main() -> None:
    force = "--force" in sys.argv
    ensure_policy_index(force=force)
    print("Índice de políticas atualizado.")


if __name__ == "__main__":
    main()
