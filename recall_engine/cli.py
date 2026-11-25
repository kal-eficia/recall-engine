"""recall-engine command line.

  recall-engine starter  --bank bank.csv --log attempts.csv --student Amir
  recall-engine class    --bank bank.csv --log attempts.csv          (one starter per student)
  recall-engine review   --bank bank.csv --log attempts.csv --student Amir
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date

from . import __version__
from .engine import build_starter, load_bank, load_log, six_week_review, students


def _pct(x):
    return "  –  " if x is None else f"{round(x * 100):>3}%"


def render_starter(student, picks, today, show_answers):
    lines = [f"## Starter for {student} · {today:%a %d %b %Y}", ""]
    for i, p in enumerate(picks, 1):
        lines.append(f"{i}. {p.question.question}  _({p.question.topic})_")
        if show_answers and p.question.answer:
            lines.append(f"   - Answer: {p.question.answer}")
    lines += ["", "<details><summary>Why these questions</summary>", ""]
    lines += [f"- Q{i}: {p.reason}" for i, p in enumerate(picks, 1)]
    lines += ["", "</details>", ""]
    return "\n".join(lines)


def render_review(student, trends):
    lines = [f"## Six-week review · {student}", "", "| Topic | Baseline | Last 2 weeks | Change |", "|---|---:|---:|---:|"]
    for t in sorted(trends, key=lambda t: (t.change is None, -(t.change or 0))):
        ch = "" if t.change is None else f"{'+' if t.change >= 0 else ''}{round(t.change * 100)} pts"
        lines.append(f"| {t.topic} | {_pct(t.baseline)} ({t.asked_baseline}) | {_pct(t.recent)} ({t.asked_recent}) | {ch} |")
    gains = [t for t in trends if (t.change or 0) >= 0.2]
    slips = [t for t in trends if (t.change or 0) <= -0.1]
    lines.append("")
    if gains:
        lines.append("**Strongest gains:** " + ", ".join(t.topic for t in gains))
    if slips:
        lines.append("**Needs another pass:** " + ", ".join(t.topic for t in slips))
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="recall-engine", description="Spaced-retrieval starters for recall-first lessons.")
    p.add_argument("--version", action="version", version=f"recall-engine {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("starter", "class", "review"):
        s = sub.add_parser(name)
        s.add_argument("--bank", required=True)
        s.add_argument("--log", required=True)
        s.add_argument("--date", type=date.fromisoformat, default=date.today())
        s.add_argument("--json", action="store_true")
        if name != "class":
            s.add_argument("--student", required=True)
        if name != "review":
            s.add_argument("--size", type=int, default=8)
            s.add_argument("--topics", help="comma-separated topics taught so far (default: any topic already asked)")
            s.add_argument("--answers", action="store_true", help="include answers (teacher copy)")
            s.add_argument("--seed", type=int)
    a = p.parse_args(argv)

    bank, log = load_bank(a.bank), load_log(a.log)
    if a.cmd == "review":
        trends = six_week_review(bank, log, a.student, a.date)
        if a.json:
            print(json.dumps([t.__dict__ | {"change": t.change} for t in trends], indent=2))
        else:
            sys.stdout.write(render_review(a.student, trends))
        return 0

    topics = [t.strip() for t in a.topics.split(",")] if a.topics else None
    who = students(log) if a.cmd == "class" else [a.student]
    out = {}
    for s in who:
        picks = build_starter(bank, log, s, a.date, a.size, topics, seed=a.seed)
        out[s] = picks
        if not a.json:
            sys.stdout.write(render_starter(s, picks, a.date, a.answers) + "\n")
    if a.json:
        print(json.dumps({s: [{"id": p.question.id, "topic": p.question.topic, "question": p.question.question,
                               "reason": p.reason} for p in ps] for s, ps in out.items()}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
