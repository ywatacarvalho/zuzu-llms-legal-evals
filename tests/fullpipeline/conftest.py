"""Shared configuration for the full-pipeline benchmark tests."""

from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCUMENTS_DIR = REPO_ROOT / "documents"
RESULTS_DIR = Path(__file__).resolve().parent / "results"


@dataclass(frozen=True)
class BenchmarkCase:
    name: str
    pdf_filename: str
    question: str
    testing_focus: str


BENCHMARK_CASES: list[BenchmarkCase] = [
    BenchmarkCase(
        name="anglemire",
        pdf_filename="_Anglemire v Policemens Benev Assn of Chicago_Marriage.pdf",
        question=(
            "Under the Illinois statute of frauds, was the insured's oral promise to "
            "name the plaintiff as beneficiary in his benefit association certificate, "
            "made in consideration of marriage, enforceable after the marriage was "
            "performed? Analyze whether the subsequent marriage and the insured's act "
            "of changing the beneficiary constituted part performance sufficient to "
            "remove the agreement from the statute of frauds, and whether the insured "
            "was estopped from later changing the beneficiary to other parties."
        ),
        testing_focus="Decomposition quality and beneficiary/marriage-related issue separation",
    ),
    BenchmarkCase(
        name="demeritt",
        pdf_filename="_Demeritt v Bickford_Surety.pdf",
        question=(
            "Was the defendant's oral promise to indemnify the plaintiff for becoming "
            "surety on a note to a third party -- where the plaintiff acted solely in "
            "reliance on the defendant's promise -- an original undertaking outside the "
            "statute of frauds, or a collateral promise to answer for the debt of "
            "another that required a writing to be enforceable?"
        ),
        testing_focus="Surety/indemnity reasoning and overlap reduction",
    ),
    BenchmarkCase(
        name="westside",
        pdf_filename="_Westside Wrecker Service Inc v Skafi_OneYear.pdf",
        question=(
            "Was the oral agreement between Westside and the subcontractor towing "
            "companies, which was intended to run for the five-year term of a government "
            "towing contract, barred by the one-year provision of the Texas statute of "
            "frauds even though the agreement could have been terminated early by the "
            "city's cancellation of the program? Additionally, was the evidence legally "
            "sufficient to establish that the parties had formed a partnership under the "
            "Texas Revised Partnership Act, considering the totality of the statutory "
            "factors?"
        ),
        testing_focus=(
            "One-year/statute-of-frauds reasoning and ranking stability under weighting changes"
        ),
    ),
]

COMPARISON_MODELS: list[str] = [
    "Qwen/Qwen3-235B-A22B-Instruct-2507-tput",  # Alibaba  235B MoE  $0.20/M  3.0s
    "openai/gpt-oss-120b",  # OpenAI   120B      $0.15/M  5.6s
    "openai/gpt-oss-20b",  # OpenAI    20B      $0.05/M  3.5s
    "LiquidAI/LFM2-24B-A2B",  # LiquidAI  24B      $0.03/M  2.2s
    "meta-llama/Meta-Llama-3-8B-Instruct-Lite",  # Meta       8B      $0.10/M  3.0s
]

RESPONSES_PER_MODEL = 40
