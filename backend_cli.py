#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

import httpx


API_URL = "http://127.0.0.1:8000/api/generate-sql"
DB_DIR = Path(__file__).resolve().parent / "backend" / "db"
EXIT_COMMANDS = {"q", "quit", "exit"}


def list_databases() -> list[str]:
    return sorted(path.name for path in DB_DIR.iterdir() if path.is_file())


def choose_database(databases: list[str]) -> str:
    print("Available databases:")
    for index, name in enumerate(databases, start=1):
        print(f"  {index}. {name}")
    print()

    while True:
        choice = input("Choose a database by number: ").strip()
        if not choice.isdigit():
            print("Please enter a number.")
            continue

        selected_index = int(choice) - 1
        if 0 <= selected_index < len(databases):
            return databases[selected_index]

        print("Choice out of range.")


def ask_question(client: httpx.Client, db_filename: str, question: str) -> dict:
    response = client.post(
        API_URL,
        json={"db_filename": db_filename, "question": question},
        timeout=120.0,
    )
    response.raise_for_status()
    return response.json()


def main() -> int:
    if not DB_DIR.exists():
        print(f"Database directory not found: {DB_DIR}", file=sys.stderr)
        return 1

    databases = list_databases()
    if not databases:
        print(f"No database files found in {DB_DIR}", file=sys.stderr)
        return 1

    db_filename = choose_database(databases)
    print(f"\nUsing database: {db_filename}")
    print("Ask a question about the data. Type 'quit' to exit.\n")

    with httpx.Client() as client:
        while True:
            try:
                question = input("Question: ").strip()
            except EOFError:
                print()
                break
            except KeyboardInterrupt:
                print()
                break

            if not question:
                continue

            if question.lower() in EXIT_COMMANDS:
                break

            try:
                result = ask_question(client, db_filename, question)
            except httpx.HTTPStatusError as exc:
                print(f"Request failed: {exc.response.status_code}")
                print(exc.response.text)
                print()
                continue
            except httpx.HTTPError as exc:
                print(f"Could not reach backend at {API_URL}: {exc}")
                print()
                continue

            print(json.dumps(result, indent=2, ensure_ascii=False))
            print()

    print("Goodbye.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
