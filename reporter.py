from collections import defaultdict
from datetime import datetime


class Reporter:
    def __init__(self, total_runs: int = 1, url: str = "", mode: str = ""):
        self._total_runs = total_runs
        self._url = url
        self._mode = mode
        self._results: list[dict] = []
        self._hurdle_order: list[str] = []
        self._started_at = datetime.now()

    def record(self, name: str, passed: bool, reason: str, status: int,
               body_snippet: str | None, run: int = 1):
        if name not in self._hurdle_order:
            self._hurdle_order.append(name)
        self._results.append({
            "name": name,
            "passed": passed,
            "reason": reason,
            "status": status,
            "snippet": body_snippet or "",
            "run": run,
        })

    def _build_stats(self):
        hurdle_runs: dict[str, int] = defaultdict(int)
        hurdle_fails: dict[str, int] = defaultdict(int)
        hurdle_reasons: dict[str, list[str]] = defaultdict(list)
        hurdle_snippets: dict[str, str] = {}

        for r in self._results:
            n = r["name"]
            hurdle_runs[n] += 1
            if not r["passed"]:
                hurdle_fails[n] += 1
                hurdle_reasons[n].append(r["reason"])
                if not hurdle_snippets.get(n) and r["snippet"]:
                    hurdle_snippets[n] = r["snippet"]

        return hurdle_runs, hurdle_fails, hurdle_reasons, hurdle_snippets

    def _verdict(self, failed_count: int, total: int) -> str:
        if failed_count == 0:
            return "All tests passed."
        elif failed_count <= total * 0.25:
            return f"{failed_count} failure(s) — minor issues detected."
        else:
            return f"{failed_count} failure(s) — significant issues detected."

    def _verdict_emoji(self, failed_count: int, total: int) -> str:
        if failed_count == 0:
            return "✅  All tests passed."
        elif failed_count <= total * 0.25:
            return f"⚠️   {failed_count} failure(s) — minor issues detected."
        else:
            return f"❌  {failed_count} failure(s) — significant issues detected."

    def summary(self, output_path: str | None = None):
        total = len(self._results)
        passed_count = sum(1 for r in self._results if r["passed"])
        failed_count = total - passed_count

        hurdle_runs, hurdle_fails, hurdle_reasons, hurdle_snippets = self._build_stats()

        sorted_hurdles = sorted(
            self._hurdle_order,
            key=lambda n: hurdle_fails[n],
            reverse=True,
        )

        # --- terminal output ---
        print()
        print("=" * 70)
        print(f"  SUMMARY")
        print("=" * 70)

        if self._total_runs > 1:
            print(f"\n  Total runs completed : {self._total_runs}")
            print(f"  Overall score        : {passed_count}/{total} passed\n")

            for name in sorted_hurdles:
                fails = hurdle_fails[name]
                runs = hurdle_runs[name]

                if fails == runs:
                    label, marker = "CONSISTENT FAIL", "!"
                elif fails > 0:
                    label, marker = "FLAKY", "~"
                else:
                    label, marker = "OK", "+"

                rate = f"{fails}/{runs} runs failed"
                print(f"  {marker}  {name:<32}  {rate:<20}  {label}")

                if fails > 0:
                    for reason in list(dict.fromkeys(hurdle_reasons[name]))[:2]:
                        print(f"       reason : {reason}")
                    if hurdle_snippets.get(name):
                        print(f"       snippet: {hurdle_snippets[name]}")

            print()
        else:
            print(f"\n  Score : {passed_count}/{total} passed\n")
            for r in self._results:
                if not r["passed"]:
                    print(f"  !  {r['name']:<32}  {r['reason']}")
                    if r["snippet"]:
                        print(f"       snippet: {r['snippet']}")
            print()

        print("=" * 70)
        print(f"  {self._verdict_emoji(failed_count, total)}")
        print("=" * 70)
        print()

        # --- file output ---
        if output_path:
            self._write_file(output_path, total, passed_count, failed_count,
                             sorted_hurdles, hurdle_runs, hurdle_fails,
                             hurdle_reasons, hurdle_snippets)

    def _write_file(self, path: str, total: int, passed_count: int, failed_count: int,
                    sorted_hurdles: list[str], hurdle_runs: dict, hurdle_fails: dict,
                    hurdle_reasons: dict, hurdle_snippets: dict):
        lines = []

        lines.append("Orangutan — AI Endpoint Stress Test Report")
        lines.append("=" * 70)
        lines.append(f"Timestamp : {self._started_at.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"URL       : {self._url}")
        lines.append(f"Mode      : {self._mode}")
        lines.append(f"Runs      : {self._total_runs}")
        lines.append(f"Score     : {passed_count}/{total} passed")
        lines.append("")

        lines.append("=" * 70)
        lines.append("ALL HURDLE RESULTS")
        lines.append("=" * 70)
        lines.append("")

        if self._total_runs > 1:
            for name in sorted_hurdles:
                fails = hurdle_fails[name]
                runs = hurdle_runs[name]
                if fails == runs:
                    label = "CONSISTENT FAIL"
                elif fails > 0:
                    label = "FLAKY"
                else:
                    label = "OK"
                lines.append(f"  {name:<34}  {fails}/{runs} runs failed  {label}")
            lines.append("")
        else:
            for r in self._results:
                result_str = "PASS" if r["passed"] else "FAIL"
                lines.append(f"  {r['name']:<34}  {result_str}  [{r['status']}]  {r['reason']}")
            lines.append("")

        failures = [r for r in self._results if not r["passed"]]
        if failures:
            lines.append("=" * 70)
            lines.append("FAILURE DETAILS")
            lines.append("=" * 70)
            lines.append("")

            seen: set[str] = set()
            for name in sorted_hurdles:
                if hurdle_fails[name] == 0:
                    continue
                if name in seen:
                    continue
                seen.add(name)

                fails = hurdle_fails[name]
                runs = hurdle_runs[name]
                lines.append(f"  Hurdle  : {name}")
                lines.append(f"  Rate    : {fails}/{runs} runs failed")

                for reason in list(dict.fromkeys(hurdle_reasons[name]))[:2]:
                    lines.append(f"  Reason  : {reason}")

                if hurdle_snippets.get(name):
                    lines.append(f"  Snippet : {hurdle_snippets[name]}")

                for r in self._results:
                    if r["name"] == name and not r["passed"]:
                        lines.append(f"    run {r['run']:>2}  [{r['status']}]  {r['reason']}")

                lines.append("")

        lines.append("=" * 70)
        lines.append("VERDICT")
        lines.append("=" * 70)
        lines.append(self._verdict(failed_count, total))
        lines.append("")

        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        print(f"  Report saved to {path}")
