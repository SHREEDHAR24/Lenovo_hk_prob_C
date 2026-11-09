"""Smoke test: retrieval, refusal, the checker, a version diff, and one CUDA forward pass."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sourcedesk.answer import Quote, checked_stitch  # noqa: E402
from sourcedesk.dense import cuda_forward  # noqa: E402
from sourcedesk.ingest import load_dir  # noqa: E402
from sourcedesk.privacy import log_event, open_seal, seal  # noqa: E402
from sourcedesk.tiers import classify, probe, serving_mode  # noqa: E402
from sourcedesk.verify import unsupported  # noqa: E402
from sourcedesk.workbench import Workbench, compare_texts  # noqa: E402


def check(name: str, cond: bool, detail: str = "") -> None:
    if not cond:
        raise SystemExit(f"FAIL {name} {detail}")
    print(f"ok  {name}")


def main() -> int:
    samples = ROOT / "samples"
    if not (samples / "fy25_payroll.xlsx").exists():
        subprocess.check_call([sys.executable, str(samples / "make_samples.py")])
    log_path = ROOT / ".sourcedesk" / "smoke.log"
    if log_path.exists():
        log_path.unlink()

    bench = Workbench(samples, log_path=log_path)
    tier = probe()
    print(f"tier {tier.name}  ram-rule stitcher={bench.tier.stitcher}  live={tier.name}")

    bonus = bench.ask("What is Rahul Verma's bonus?")
    check("bonus status", bonus.status == "answer", bonus.text)
    check("bonus figure", "1,50,000" in bonus.text, bonus.text)
    check("neighbour dropped", "1,80,000" not in bonus.text, bonus.text)
    check("quote is substring", bonus.quotes and bonus.quotes[0].text in _source_text(samples, bonus.quotes[0].doc_id))
    check("quote names the cell", "D14" in bonus.quotes[0].text, bonus.quotes[0].text)

    missing = bench.ask("What is the CEO home address?")
    check("refusal", missing.status == "refuse", missing.text)
    check("refusal words", "do not say" in missing.text.lower(), missing.text)

    notice = bench.ask("What notice period does the Northwind contract require?")
    check("conflict", notice.status == "conflict", notice.text)
    check("both periods", "30" in notice.text and "60" in notice.text, notice.text)

    papers = bench.ask("What is the retention period for board papers?")
    check("pdf answer", papers.status == "answer" and "7" in papers.text, papers.text)

    summary = bench.summarize("What is the retention period for board papers?")
    check("summary cites", summary.status == "summary" and "7" in summary.text, summary.text)
    check(
        "summary quote is source",
        summary.quotes and summary.quotes[0].text in _source_text(samples, summary.quotes[0].doc_id),
    )
    leave_summary = bench.summarize("How many days of leave may an employee take?")
    check("summary skips a weak scan", "18" not in leave_summary.text, leave_summary.text)

    note = bench.draft("What is Rahul Verma's bonus?")
    check("draft from the cell", note.status == "draft" and "1,50,000" in note.text and "1,80,000" not in note.text, note.text)
    notice_note = bench.draft("What notice period does the Northwind contract require?")
    check("draft does not pick a side", notice_note.status == "conflict", notice_note.text)

    import shutil
    import tempfile

    scratch = Path(tempfile.mkdtemp())
    copied = scratch / "set"
    shutil.copytree(samples, copied)
    fresh = Workbench(copied, log_path=scratch / "events.log")
    before = fresh.manifest
    check("refresh is quiet", fresh.refresh() is False)
    scan = copied / "leave_policy.scan.txt"
    scan.write_text(scan.read_text(encoding="utf-8") + "\nRevised scan line without a pay figure.\n", encoding="utf-8")
    check("refresh sees the edit", fresh.refresh() is True)
    check("manifest moved", fresh.manifest != before)
    again = fresh.ask("What is Rahul Verma's bonus?")
    check("bonus survives refresh", "1,50,000" in again.text, again.text)

    leave = bench.ask("How many days of leave may an employee take?")
    check("scan refused", leave.status == "refuse", leave.text)
    check("scan hides the figure", "18" not in leave.text, leave.text)

    planted = unsupported("The bonus is 1,80,000.", "Payroll!D14=Bonus 1,50,000")
    check("planted number rejected", "1,80,000" in planted, str(planted))
    quote = Quote("Payroll!D14=Bonus 1,50,000", "fy25_payroll.xlsx", "Payroll", None)
    sentence, missing_bits = checked_stitch(quote)
    check("honest stitch kept", sentence is not None and not missing_bits, str(sentence))

    reduced = bench.ask("What is Rahul Verma's bonus?", battery_pct=10)
    check("reduced mode", reduced.mode == "reduced" and reduced.stitcher == "none", reduced.text)
    check("reduced still quotes", "1,50,000" in reduced.text, reduced.text)

    check("tier floor", classify(8, True).name == "refuse")
    check("tier C", classify(16, True).name == "C")
    check("tier B", classify(16, False, has_npu=True).name == "B")
    check("tier A", classify(32, False).name == "A")
    check("degrade", serving_mode(gpu_busy=True) == "reduced")
    check("full mode", serving_mode() == "full")

    corpus = load_dir(samples)
    by_name = {}
    for page in corpus.pages:
        by_name.setdefault(page.doc_id, [])
        by_name[page.doc_id].append(page.text)
    diff = compare_texts("\n".join(by_name["northwind_v1.docx"]), "\n".join(by_name["northwind_v2.docx"]))
    joined = " ".join(diff["only_left"] + diff["only_right"])
    check("version diff", "30" in joined and "60" in joined, joined)

    blob = seal(b"index-bytes-not-a-document")
    check("seal roundtrip", open_seal(blob) == b"index-bytes-not-a-document")
    log_text = log_path.read_text(encoding="utf-8")
    check("log has no figure", "1,50,000" not in log_text and "Rahul" not in log_text, log_text[:200])

    device = cuda_forward()
    check("cuda forward", device == "cuda", device)

    proc = subprocess.run([sys.executable, str(ROOT / "train_later.py"), "--train"], capture_output=True, text=True)
    check("no training", proc.returncode == 0 and "not training" in proc.stdout and "steps=0" in proc.stdout, proc.stdout)
    print("smoke passed")
    return 0


def _source_text(folder: Path, doc_id: str) -> str:
    corpus = load_dir(folder)
    return "\n".join(page.text for page in corpus.pages if page.doc_id == doc_id)


if __name__ == "__main__":
    raise SystemExit(main())
