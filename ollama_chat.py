#!/usr/bin/env python3
"""Terminal chat client for a local Ollama server using ollama-python."""

from __future__ import annotations

import argparse
import json
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

try:
    from ollama import Client, ResponseError, list as ollama_list
except ImportError:  # pragma: no cover - depends on local environment
    print(
        "The 'ollama' Python package is not installed.\n"
        "Install it with: pip install ollama",
        file=sys.stderr,
    )
    raise SystemExit(1)


DEFAULT_HOST = "http://localhost:11434"
DEFAULT_MODEL = "qwen2.5-coder:3b"
EXIT_COMMANDS = {"/exit", "/quit", "/bye"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Terminal chat client for a local Ollama server."
    )
    parser.add_argument("--model", help="Model name to use, for example llama3.2")
    parser.add_argument(
        "-d",
        "--default-model",
        action="store_true",
        help=f"Use the default model ({DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--host",
        default=DEFAULT_HOST,
        help=f"Ollama host URL (default: {DEFAULT_HOST})",
    )
    parser.add_argument("--system", help="Optional system prompt")
    parser.add_argument(
        "--log-dir",
        default="chat_logs",
        help="Directory where chat transcripts will be saved",
    )
    return parser.parse_args()


def list_models() -> list[str]:
    try:
        response = ollama_list()
    except Exception:
        return []

    models = []
    for model in response.get("models", []):
        name = model.get("name")
        if name:
            models.append(name)
    return models


def choose_model() -> str:
    models = list_models()
    if models:
        print("Available Ollama models:")
        for name in models:
            print(f"  - {name}")
        print()

    while True:
        model = input("Enter the model name to use: ").strip()
        if model:
            return model
        print("Please enter a model name.")


def stream_reply(client: Client, model: str, messages: list[dict]) -> str:
    stream = client.chat(model=model, messages=messages, stream=True)
    parts: list[str] = []
    stop_animation = threading.Event()

    def animate_waiting() -> None:
        frames = [".  ", ".. ", "..."]
        index = 0
        while not stop_animation.is_set():
            frame = frames[index % len(frames)]
            print(f"\rOllama: {frame}", end="", flush=True)
            index += 1
            time.sleep(0.35)

    animation_thread = threading.Thread(target=animate_waiting, daemon=True)
    animation_thread.start()
    started_reply = False

    try:
        for chunk in stream:
            content = chunk["message"]["content"]
            if content:
                if not started_reply:
                    stop_animation.set()
                    animation_thread.join()
                    print("\rOllama: ", end="", flush=True)
                    started_reply = True
                print(content, end="", flush=True)
                parts.append(content)
    finally:
        stop_animation.set()
        animation_thread.join()

    print()
    return "".join(parts)


def save_conversation(
    log_dir: Path,
    model: str,
    host: str,
    messages: list[dict],
    started_at: datetime,
) -> Path:
    log_dir.mkdir(parents=True, exist_ok=True)
    ended_at = datetime.now()
    filename = f"chat_{started_at.strftime('%Y%m%d_%H%M%S')}.json"
    path = log_dir / filename

    payload = {
        "model": model,
        "host": host,
        "started_at": started_at.isoformat(),
        "ended_at": ended_at.isoformat(),
        "messages": messages,
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def main() -> int:
    args = parse_args()
    started_at = datetime.now()
    model = args.model or (DEFAULT_MODEL if args.default_model else choose_model())
    client = Client(host=args.host)

    messages: list[dict] = []
    if args.system:
        messages.append({"role": "system", "content": args.system})

    print(f"Connected host: {args.host}")
    print(f"Starting chat with model: {model}")
    print("Type your message and press Enter.")
    print("Use /exit, /quit, or /bye to end the session.")
    print()

    try:
        while True:
            try:
                user_input = input("You: ").strip()
            except EOFError:
                print()
                break

            if not user_input:
                continue

            if user_input.lower() in EXIT_COMMANDS:
                break

            messages.append({"role": "user", "content": user_input})
            reply = stream_reply(client, model, messages)
            messages.append({"role": "assistant", "content": reply})

    except KeyboardInterrupt:
        print("\nEnding chat session...")
    except ResponseError as exc:
        print(f"\nOllama API error: {exc.error}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(
            f"\nCould not reach Ollama at {args.host}: {exc}",
            file=sys.stderr,
        )
        return 1

    log_path = save_conversation(
        Path(args.log_dir), model, args.host, messages, started_at
    )
    print(f"Conversation saved to: {log_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
