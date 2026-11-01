"""CSV → SQLite."""

from emporio_agent.data_loader import ingest_csvs


def main() -> None:
    path = ingest_csvs()
    print(f"Banco criado em: {path}")


if __name__ == "__main__":
    main()
