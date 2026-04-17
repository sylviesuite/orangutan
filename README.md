# Orangutan

Stress-test AI chat endpoints by firing adversarial inputs and reporting failures.

```bash
python orangutan.py --url https://your-api/chat
```

---

## Install

```bash
pip install httpx
```

---

## Usage

```bash
python orangutan.py [options]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--url` | **required** | POST endpoint to test |
| `--header` | — | Request header as `KEY:VALUE` (repeatable) |
| `--field` | `message` | JSON field name for the input |
| `--timeout` | `10.0` | Seconds before a request is killed |
| `--delay` | `0.0` | Pause in seconds between requests |
| `--mode` | `standard` | `standard` \| `security` \| `edge` \| `chaos` |
| `--runs` | `1` | Number of times to repeat the full hurdle set |
| `--output` | — | Save the report to a file path |

---

## Modes

**standard** — Runs a baseline set of inputs covering common failure patterns: empty strings, very long inputs, repeated characters, and benign but unusual phrasing. Use this for a quick sanity check against any endpoint.

**security** — Fires prompt injection attempts, jailbreak phrases, role-override instructions, and inputs designed to leak system prompts. Useful for validating that a model or API wrapper has guardrails in place.

**edge** — Targets boundary conditions: Unicode edge cases, null-like strings, whitespace-only inputs, control characters, and inputs that stress tokenization. Catches crashes and malformed responses that normal testing misses.

**chaos** — Sends random, malformed, and structurally unexpected payloads. Inputs may be truncated mid-sentence, contain mixed encodings, or be syntactically valid but semantically incoherent. Surfaces instability under unpredictable load.

---

## What it detects

- Empty or null responses from the endpoint
- Slow responses that exceed the configured timeout threshold
- Disallowed phrases present in the response body
- Contradictions across multiple runs for the same input
- HTTP errors (4xx, 5xx)

---

## Example commands

```bash
# Run the security hurdle set against a local endpoint with an auth header
python orangutan.py \
  --url http://localhost:8080/chat \
  --header "Authorization:Bearer mytoken" \
  --mode security

# Run the full standard suite 5 times and save the report
python orangutan.py \
  --url https://api.example.com/v1/chat \
  --runs 5 \
  --output results.txt

# Test a custom message field with a 30-second timeout and 1-second delay between requests
python orangutan.py \
  --url https://api.example.com/chat \
  --field prompt \
  --timeout 30.0 \
  --delay 1.0 \
  --mode edge
```

---

## File structure

- `orangutan.py` — CLI entry point; parses arguments and orchestrates test runs
- `hurdles.py` — Input sets for each mode (standard, security, edge, chaos)
- `detector.py` — Response analysis logic; identifies failures and anomalies
- `reporter.py` — Formats and outputs results to stdout or file
- `mock_server.py` — Local test server for validating Orangutan itself

---

## License

MIT
