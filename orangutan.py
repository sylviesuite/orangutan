#!/usr/bin/env python3
import argparse
import io
import sys
import time

import httpx

from hurdles import HURDLES
from detector import evaluate
from reporter import Reporter

# Force UTF-8 output on Windows terminals
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="orangutan",
        description="Stress-test AI chat endpoints with adversarial inputs.",
    )
    p.add_argument("--url",       required=True,               help="Target endpoint URL")
    p.add_argument("--header",    action="append", default=[], metavar="KEY:VALUE",
                   help="HTTP header (repeatable, e.g. --header Authorization:Bearer token)")
    p.add_argument("--field",     default="message",           help="JSON body field for the input (default: message)")
    p.add_argument("--model",     default=None,
                   help="Anthropic model ID — wraps payload as messages API body (e.g. claude-sonnet-4-6)")
    p.add_argument("--max-tokens", type=int, default=1024,     help="max_tokens for Anthropic mode (default: 1024)")
    p.add_argument("--timeout",   type=float, default=10.0,    help="Request timeout in seconds (default: 10.0)")
    p.add_argument("--delay",     type=float, default=0.0,     help="Delay between requests in seconds (default: 0.0)")
    p.add_argument("--mode",      default="standard",
                   choices=["standard", "security", "edge", "chaos"],
                   help="Hurdle set to run (default: standard)")
    p.add_argument("--runs",      type=int, default=1,
                   help="Number of times to repeat the full hurdle set (default: 1)")
    p.add_argument("--output",    type=str, default=None,
                   help="Save report to file path (e.g. report.txt)")
    return p


def parse_headers(raw: list[str]) -> dict[str, str]:
    headers = {}
    for item in raw:
        if ":" not in item:
            print(f"[warn] skipping malformed header (no colon): {item!r}", file=sys.stderr)
            continue
        key, _, value = item.partition(":")
        headers[key.strip()] = value.strip()
    return headers


def build_body(field: str, payload, model: str | None, max_tokens: int) -> dict:
    if model:
        content = str(payload) if not isinstance(payload, str) else payload
        return {
            "model": model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": content}],
        }
    return {field: payload}


def extract_text(body: str, model: str | None) -> str:
    if not model or not body:
        return body
    try:
        import json
        data = json.loads(body)
        # Anthropic response: {"content": [{"type": "text", "text": "..."}], ...}
        blocks = data.get("content", [])
        if isinstance(blocks, list):
            return " ".join(b.get("text", "") for b in blocks if b.get("type") == "text")
    except Exception:
        pass
    return body


def send(url: str, headers: dict[str, str], field: str, payload, timeout: float,
         model: str | None, max_tokens: int) -> tuple[int, str, float]:
    body = build_body(field, payload, model, max_tokens)
    start = time.perf_counter()
    try:
        resp = httpx.post(url, json=body, headers=headers, timeout=timeout)
        elapsed = time.perf_counter() - start
        text = extract_text(resp.text, model)
        return resp.status_code, text, elapsed
    except httpx.TimeoutException:
        elapsed = time.perf_counter() - start
        return 0, "", elapsed
    except httpx.RequestError as exc:
        elapsed = time.perf_counter() - start
        return -1, str(exc), elapsed


def run(args: argparse.Namespace):
    headers = parse_headers(args.header)
    hurdle_list = HURDLES.get(args.mode, [])
    reporter = Reporter(total_runs=args.runs, url=args.url, mode=args.mode)

    mode_info = f"model: {args.model}" if args.model else f"field: {args.field}"
    runs_info = f"runs: {args.runs}" if args.runs > 1 else ""
    meta = "  |  ".join(filter(None, [f"mode: {args.mode}", f"hurdles: {len(hurdle_list)}", mode_info, runs_info]))
    print(f"\n  Orangutan  ->  {args.url}")
    print(f"  {meta}\n")

    for run_num in range(1, args.runs + 1):
        previous_answers: list[str] = []

        if args.runs > 1:
            print(f"  -- run {run_num}/{args.runs} " + "-" * 48)

        print(f"  {'name':<32}  {'status':>6}  {'time':>7}  reason")
        print("  " + "-" * 66)

        for hurdle in hurdle_list:
            name = hurdle["name"]

            if args.delay > 0:
                time.sleep(args.delay)

            status, body, elapsed = send(
                args.url, headers, args.field, hurdle["input"],
                args.timeout, args.model, args.max_tokens,
            )
            passed, reason, snip = evaluate(status, body, elapsed, hurdle, previous_answers)

            if body and body.strip():
                previous_answers.append(body)

            reporter.record(name, passed, reason, status, snip, run=run_num)

            mark = "+" if passed else "!"
            status_str = str(status) if status > 0 else "ERR"
            print(f"  {mark}  {name:<32}  [{status_str:>3}]  {elapsed:>6.2f}s  {reason}")

        print()

    reporter.summary(output_path=args.output)


def main():
    parser = build_parser()
    args = parser.parse_args()

    try:
        run(args)
    except KeyboardInterrupt:
        print("\n[interrupted]", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
