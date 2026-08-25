"""One-off: re-run two cases whose answers were affected by the 1000-char
span-output truncation, then splice fresh samples into samples_full.json."""

import io
import json
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "evals"))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")

from application.agents.agent import StockAgent  # noqa: E402
from infrastructure.observability.tracing import init_tracing  # noqa: E402
from run_ragas_eval import load_cases, run_case  # noqa: E402

REFRESH = {"price_002", "price_004"}
FULL = Path(
    ROOT / "evals/reports/benchmark-resume-20260825-043846/samples_full.json"
)

data = json.loads(FULL.read_text(encoding="utf-8"))
cases = {c["id"]: c for c in load_cases(ROOT / "evals/golden/golden_dataset.jsonl", None, None)}

init_tracing()
agent = StockAgent()
if agent.llm_provider is None:
    raise SystemExit("LLM unavailable")

for s in data["samples"]:
    cid = s["meta"]["id"]
    if cid not in REFRESH:
        continue
    print("re-running", cid)
    fresh = run_case(agent, cases[cid])
    s["response"] = fresh["response"]
    s["retrieved_contexts"] = fresh["retrieved_contexts"]
    s["meta"] = fresh["meta"]

FULL.write_text(json.dumps(data, ensure_ascii=False, default=str), encoding="utf-8")
print("spliced ->", FULL)
