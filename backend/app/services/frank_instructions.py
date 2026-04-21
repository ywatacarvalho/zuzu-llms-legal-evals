"""FrankInstructions content store.

Core workflow constants are embedded here for prompt construction. The active
doctrine taxonomy is the six-pack B-series model sourced from the current
`documents/FrankInstructions` files by the public accessors at module runtime.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Module skeleton (07_SHARED_MODULE_SKELETON.txt)
# ---------------------------------------------------------------------------

MODULE_SKELETON: dict = {
    "modules": {
        0: {
            "name": "Metadata tags (not scored)",
            "weight": 0,
            "criteria_ids": [],
            "description": (
                "Non-scored metadata fields: bottom-line outcome, outcome correctness, "
                "reasoning alignment, jurisdiction assumption, controlling doctrine named by model."
            ),
        },
        1: {
            "name": "Structural gatekeeping",
            "weight": 28,
            "criteria_ids": ["A", "K", "J"],
            "description": (
                "Checks whether the answer follows the right legal path, identifies the "
                "dispositive issue early, and keeps independent barriers separate."
            ),
        },
        2: {
            "name": "Primary doctrine gates",
            "weight": 40,
            "criteria_ids": ["B", "C", "D", "E"],
            "description": (
                "Holds the core doctrinal analysis for the pack. The main legal module "
                "containing the controlling gate plus the most important secondary gates."
            ),
        },
        3: {
            "name": "Fallback doctrines and defenses",
            "weight": 19,
            "criteria_ids": ["F", "G", "H"],
            "description": (
                "Fallback theories, competing doctrines, and defenses addressed only "
                "after the main gates."
            ),
        },
        4: {
            "name": "Cross-cutting answer discipline",
            "weight": 13,
            "criteria_ids": ["I", "L", "M"],
            "description": (
                "Factual fidelity, scope calibration, claim discipline, and prompt "
                "adherence across all modules."
            ),
        },
    },
    "default_weight_rationale": (
        "Module 1=28, Module 2=40, Module 3=19, Module 4=13. Starting defaults from "
        "07_SHARED_MODULE_SKELETON.txt. A later pack may adjust with explicit changelog note."
    ),
    "scoring_anchors": {
        0: "Absent or materially wrong; would mislead the outcome.",
        1: (
            "Mentioned but incorrect or superficial; wrong test, wrong trigger,"
            " or no real application."
        ),
        2: (
            "Partially correct; right general idea but missing a key element,"
            " exception, or application step."
        ),
        3: "Mostly correct; minor gaps but still usable.",
        4: (
            "Strong; correct rule, prioritized path, fact-specific application,"
            " and addresses key counterpoints."
        ),
    },
}

MODULE_0_METADATA_TAGS: list[str] = [
    "Bottom-line outcome",
    "Outcome correctness",
    "Reasoning alignment",
    "Jurisdiction assumption",
    "Controlling doctrine named by model",
]

# ---------------------------------------------------------------------------
# Output shape (03_CORE_OUTPUT_SHAPE_AND_PROMPT_STRUCTURE.txt)
# ---------------------------------------------------------------------------

OUTPUT_SHELL_HEADINGS: list[str] = [
    "Jurisdiction assumption",
    "Bottom-line outcome",
    "Controlling doctrine",
    "Transaction / formation characterization",
    "Writing requirement and trigger",
    "Compliance / substitute / exception analysis",
    "Other defenses or competing doctrines",
    "Strongest counterargument",
]

CORE_PROMPT_BLOCK: str = (
    "You are analyzing a legal question for evaluation or benchmarking purposes. "
    "Do not use generic IRAC. Use the exact section headings below. Keep the analysis "
    "concise, fact-specific, doctrinally ordered, neutral, and black-letter-law in style. "
    "Name the likely controlling doctrine early. Keep independent barriers separate. "
    "Address fallback theories only after the main writing or formality analysis. "
    "Use full doctrine names. Do not invent facts, writings, signatures, parties, or "
    "jurisdiction-specific rules. If uncertainty remains, identify the specific source of "
    'uncertainty rather than saying only "it depends." Do not cite outside authority '
    "unless the task specifically asks for it.\n\n"
    "Return your answer in exactly this format:\n"
    "Jurisdiction assumption:\n"
    "Bottom-line outcome:\n"
    "Controlling doctrine:\n"
    "Transaction / formation characterization:\n"
    "Writing requirement and trigger:\n"
    "Compliance / substitute / exception analysis:\n"
    "Other defenses or competing doctrines:\n"
    "Strongest counterargument:"
)

# ---------------------------------------------------------------------------
# Source intake checklist (02_CORE_SOURCE_INTAKE_CHECKLIST.txt)
# ---------------------------------------------------------------------------

SOURCE_INTAKE_CHECKLIST: dict = {
    "purpose": (
        "Screens whether a case, statute, Restatement section, or doctrine source is a "
        "strong candidate for use in a gold packet. Use before full source extraction."
    ),
    "stop_rule_triggers": [
        "Mostly headnotes, synopsis, syllabus, or editorial material rather than source text",
        "No clear doctrinal holding on the target issue",
        "Too procedural to support a stable benchmark answer",
        "Too fact-bound to generalize without distortion",
        "Too jurisdiction-split to support a clean benchmark answer without added authority",
        "No clear path to a narrow reverse-engineered question",
        "No clean doctrinal center or no stable routing path to a single doctrine family / pack",
    ],
    "rating_scale": [
        "Strong lead source",
        "Moderate; usable with supporting authority",
        "Weak; support/contrast source only",
        "Not a strong gold-source candidate without additional authority",
    ],
    "output_headings": [
        "1. Candidate source",
        "2. Source type / authority level",
        "3. Target doctrine family / likely pack",
        "4. Clean legal issue",
        "5. Black-letter rule extractable",
        "6. Trigger facts identifiable",
        "7. Holding usable for benchmark drafting",
        "8. Limits / boundaries identifiable",
        "9. Procedural noise level",
        "10. Jurisdiction sensitivity / split risk",
        "11. Benchmark-answer suitability",
        "12. Reverse-engineering suitability",
        "13. Benchmark posture (choose one): (a) Narrow source-grounded benchmark only; "
        "(b) Generalizable only with supporting authority; "
        "(c) Portable benchmark under stated assumptions",
        "14. Failure-mode yield",
        "15. JD review burden",
        "16. Final intake rating",
        "17. Recommendation",
    ],
}

# ---------------------------------------------------------------------------
# Source extraction headings (01_CORE_WORKFLOW_TEMPLATE.txt Step 1)
# ---------------------------------------------------------------------------

SOURCE_EXTRACTION_HEADINGS: list[str] = [
    "1. Selected doctrine pack",
    "2. Candidate source",
    "3. Source type / authority level",
    "4. Jurisdiction / forum",
    "5. Procedural posture",
    "6. Clean legal issue",
    "7. Black-letter rule",
    "8. Trigger facts",
    "9. Holding or best-supported answer path",
    "10. Why that result follows",
    "11. Limits / boundaries",
    "12. What the source does not decide",
    "13. Jurisdiction sensitivity / split risk",
    "14. Benchmark-use confidence",
    "15. JD Review Needed",
]

# ---------------------------------------------------------------------------
# Gold packet mapping headings (01_CORE_WORKFLOW_TEMPLATE.txt Step 2)
# ---------------------------------------------------------------------------

GOLD_PACKET_MAPPING_HEADINGS: list[str] = [
    "1. Doctrine family",
    "2. Controlling trigger",
    "3. Required gate order",
    "4. What makes the doctrine apply",
    "5. What does NOT satisfy it",
    "6. Independent competing barriers",
    "7. Possible substitutes / exceptions",
    "8. Limits on substitutes / exceptions",
    "9. Likely jurisdiction-sensitive points",
    "10. Likely model mistakes",
    "11. Candidate fact-pattern ingredients",
    "12. Reverse-engineering suitability",
    "13. Benchmark posture",
]

BENCHMARK_POSTURE_VALUES: list[str] = [
    "(a) Pack-specific benchmark only",
    "(b) Generalizable only with supporting authority",
    "(c) Portable benchmark within the selected pack",
]

# ---------------------------------------------------------------------------
# Traceability tags (01_CORE_WORKFLOW_TEMPLATE.txt Step 1 rules)
# ---------------------------------------------------------------------------

TRACEABILITY_TAGS: list[str] = [
    "Supported by source",
    "Inference from source",
    "Background generalization",
]

# ---------------------------------------------------------------------------
# Provenance-banned words (01_CORE_WORKFLOW_TEMPLATE.txt Step 4 rules)
# ---------------------------------------------------------------------------

PROVENANCE_BANNED_WORDS: list[str] = [
    "source",
    "case",
    "opinion",
    "court",
    "holding",
    "record",
    "authority",
    "supported by source",
    "inference from source",
    "background generalization",
    "source-grounded",
    "audit-tagged",
]

# ---------------------------------------------------------------------------
# Mode C comparison headings (01_CORE_WORKFLOW_TEMPLATE.txt)
# ---------------------------------------------------------------------------

MODE_C_COMPARISON_HEADINGS: list[str] = [
    "1. Source / benchmark alignment",
    "2. Controlling doctrine match",
    "3. Gate order correctness",
    "4. Trigger test accuracy",
    "5. Exception / substitute mapping",
    "6. Fallback doctrine treatment",
    "7. Factual fidelity",
    "8. Provenance discipline",
]

# ---------------------------------------------------------------------------
# Question writing checklist (04_CORE_QUESTION_WRITING_CHECKLIST.txt)
# ---------------------------------------------------------------------------

QUESTION_CHECKLIST: dict = {
    "design_goals": [
        "Test the controlling doctrine or controlling legal issue first",
        "Stay neutral in the call of the question",
        "Preserve only the facts needed to trigger the target legal path and one or two "
        "realistic distractors",
        "Avoid answer leakage",
        "Stay realistic, concise, and exam-style",
        "Be easy to compare across outputs and later cluster by legal reasoning",
        "Preserve explicit jurisdiction or governing-law cues when the benchmark depends on them",
    ],
    "neutral_call_examples": [
        "Is the agreement enforceable? Analyze.",
        "Is the promise enforceable against the promisor? Analyze.",
        "Who has the better claim? Analyze.",
        "Does the claimant have the better argument for enforcement? Analyze.",
        "Is the writing sufficient to make the agreement enforceable? Analyze.",
    ],
    "body_checks": [
        "Neutral call of the question (no doctrine named in the call)",
        "Source-fidelity preservation (holding-driving facts kept)",
        "Distractor facts limited to one or two realistic options",
        "No invented documents, signatures, or party roles",
        "Jurisdiction stated when benchmark depends on it",
        "Timing or sequence preserved when legally important",
        "No answer leakage in phrasing",
    ],
    "release_checks": [
        "Call of the question is neutral",
        "Controlling doctrine not named or pre-answered",
        "Holding-driving facts preserved",
        "Only one or two realistic distractors",
        "No invented writings, signatures, or party-role changes",
        "Jurisdiction / governing-law cues stated when required",
        "Timing and sequence accurate",
        "Benchmark posture preserved",
        "Question can support stable model-output clustering",
        "Question matches the benchmark answer path",
    ],
}

# ---------------------------------------------------------------------------
# Routing matrix (05_SOF_ROUTING_MATRIX.txt)
# ---------------------------------------------------------------------------

ROUTING_MATRIX: dict = {
    "packs": {
        "pack_10": {
            "name": "Common law oral promises",
            "scope": "Marriage consideration, one-year, and suretyship issues.",
            "use_when": [
                "The source centers common law oral-promise categories",
                "The main issue is marriage consideration, one-year, or suretyship",
                "The enforceability question turns on an oral promise that does not belong "
                "in the land, executor, or UCC packs",
            ],
            "common_cues": [
                "promise in consideration of marriage",
                "oral contract not performable within one year",
                "guaranty",
                "suretyship",
                "promise to answer for the debt of another",
                "promise to indemnify a surety",
                "promise to a proposed surety to see the debt paid if the surety signs",
            ],
            "do_not_use_when": [
                "The actual issue is land-contract writing compliance",
                "The actual issue is executor or administrator personal liability",
                "The actual issue is UCC 2-201 goods writing compliance",
                "Another pack fits the controlling issue better",
            ],
        },
        "pack_20": {
            "name": "Land contracts",
            "scope": "Contracts for the transfer of land or a land interest.",
            "use_when": [
                "The source centers a transfer of land or a land interest",
                "The issue is whether that land transaction requires or satisfies a writing",
                "The enforceability question turns on land-transaction characterization or "
                "land-writing compliance",
            ],
            "common_cues": [
                "sale of land",
                "real estate purchase",
                "option to buy land",
                "easement",
                "mortgage or deed-related transfer",
                "lease of land or other land-interest transfer",
            ],
            "do_not_use_when": [
                "The real issue is a separate surety or guaranty promise",
                "The land reference is incidental and another Statute of Frauds category "
                "is doing the real work",
                "The source is not actually analyzing the land transaction's writing requirement",
            ],
        },
        "pack_30": {
            "name": "Executor or administrator personal promise",
            "scope": (
                "Whether a personal representative undertook personal liability for estate debt."
            ),
            "use_when": [
                "The source centers whether an executor or administrator undertook personal "
                "liability for estate debt",
                "The issue is personal versus representative capacity",
                "The enforceability question turns on a promise by a personal representative "
                "to answer estate debt personally",
            ],
            "common_cues": [
                "executor",
                "administrator",
                "personal representative",
                "estate debt",
                "probate context",
                "decedent's debt",
                "promise to pay estate obligations from personal funds",
            ],
            "do_not_use_when": [
                "The representative is acting only in a representative capacity and the actual "
                "Statute of Frauds issue is land or goods",
                "Estate facts are background only",
                "The source is not testing a personal promise by the representative",
            ],
        },
        "pack_40": {
            "name": "Sale of goods (UCC 2-201)",
            "scope": "Writing issues for contracts for the sale of goods.",
            "use_when": [
                "The source centers whether a contract for the sale of goods satisfies UCC 2-201",
                (
                    "The enforceability question turns on goods characterization"
                    " or UCC writing compliance"
                ),
                (
                    "The source is analyzing merchant confirmation, quantity,"
                    " signature, or UCC exceptions"
                ),
            ],
            "common_cues": [
                "goods",
                "merchants",
                "confirmatory memo",
                "signed writing",
                "quantity term",
                "specially manufactured goods",
                "admission in pleading or testimony",
                "payment",
                "receipt and acceptance",
            ],
            "do_not_use_when": [
                "The actual issue is a separate promise to answer for another's debt",
                "Goods are only background and the source is not analyzing UCC 2-201",
                "The litigated promise is collateral rather than the goods contract itself",
            ],
        },
    },
    "core_routing_rule": (
        "Route by the controlling enforceability issue, not by surface facts alone. "
        "Ask: What legal question is the source actually resolving?"
    ),
    "stepwise_routing": [
        "Identify the promise or transaction whose enforceability is being tested.",
        "Identify whether the source is testing the contract itself, a separate collateral "
        "promise, personal representative liability, or a UCC goods writing issue.",
        "Select one primary pack.",
        "Preserve any secondary issues for later sections.",
        "If no clean fit emerges, stop at source extraction and JD review flags.",
    ],
    "special_priority_rules": [
        "A promise is not Pack 10 just because it is oral.",
        "A goods transaction is not Pack 40 if the litigated promise is a separate guaranty.",
        "A land reference is not Pack 20 if the litigated promise is collateral suretyship.",
        "Estate facts do not trigger Pack 30 unless the source is testing a personal promise "
        "by the representative.",
        "Route by the issue the source is resolving, not by the broad factual setting.",
    ],
    "default_fallback": (
        "If fit is mixed or unclear, do source extraction first. Then state: tentative pack, "
        "one-sentence reason, confidence level: strong, moderate, or weak. "
        "If confidence remains weak, stop at source extraction plus JD review flags."
    ),
    "required_routing_output": "Selected pack:\nReason:",
}

# ---------------------------------------------------------------------------
# Self-audit (06_CORE_SELF_AUDIT.txt)
# ---------------------------------------------------------------------------

SELF_AUDIT_FAST_TRIAGE: list[dict] = [
    {
        "id": 1,
        "name": "Bottom line + controller",
        "checks": [
            (
                "Does the draft clearly state who wins or whether the agreement/promise"
                " is enforceable?"
            ),
            "Does it explicitly name the likely controlling doctrine?",
            "Is the conclusion supported by the analysis?",
            "Is any uncertainty specific rather than generic?",
        ],
    },
    {
        "id": 2,
        "name": "Controlling trigger + ordered path",
        "checks": [
            "Does the draft identify the controlling gate, rule, or trigger first?",
            "Does it use the correct test rather than a loose paraphrase?",
            "Are secondary issues kept secondary?",
            (
                "If a writing doctrine is relevant, does the draft distinguish"
                " enforceability from proof?"
            ),
        ],
    },
    {
        "id": 3,
        "name": "Exception mapping",
        "checks": [
            "Do fallback doctrines or substitutes appear only after the main gates?",
            "Does the draft explain what each workaround can and cannot cure?",
            "Does it avoid one-exception-cures-all reasoning?",
        ],
    },
    {
        "id": 4,
        "name": "Routing / pack fit",
        "checks": [
            "Does the selected doctrine pack actually match the controlling issue?",
            "Is the draft borrowing doctrine, examples, or trigger tests from a different pack?",
            "If fit is mixed or weak, does the draft stop at source extraction + JD review flags "
            "instead of forcing a final benchmark answer?",
        ],
    },
]

SELF_AUDIT_RED_FLAGS: list[str] = [
    "Controlling doctrine omitted",
    "Wrong doctrine pack appears to be driving the answer",
    "Material rule or trigger test misstatement",
    "Material fact, timing, quantity, role, or sequence error",
    "Exception bleed-over",
    (
        "Invented writing, signature, assent, confirmation, admission, payment,"
        " or other compliance fact"
    ),
    "Irrelevant doctrine used as a major driver",
    "Excessive hedging in place of analysis",
    "Source too weak or split-dependent for a stable benchmark answer, but the draft is written "
    "as settled",
    "Jurisdiction-specific rule imported without stating the jurisdictional assumption",
]

SELF_AUDIT_RELEASE_CHECK: list[str] = [
    "A clear bottom-line outcome appears early",
    "The likely controlling doctrine is named",
    "The selected pack still fits the issue",
    "The draft follows the ordered path",
    "The controlling trigger is analyzed before fallback doctrines",
    "Independent barriers remain separate",
    "Substitutes or exceptions are mapped only to the barriers they can actually address",
    "Non-triggered secondary issues are brief",
    "No invented facts or unsupported jurisdictional rules remain",
    "The strongest counterargument is real",
    "Any uncertainty is specific and bounded",
    "If the output is a question, the call remains neutral and does not leak the answer",
]

SELF_AUDIT_CLASSIFICATIONS: list[str] = [
    "Ready",
    "Needs targeted revision",
    "Needs major rewrite",
    "Needs rerouting",
]

# ---------------------------------------------------------------------------
# Doctrine pack content (per-pack)
# ---------------------------------------------------------------------------

_PACK_10_CONTENT: dict = {
    "id": "pack_10",
    "name": "Common-Law Oral Promises",
    "categories": ["marriage-consideration", "one-year", "suretyship"],
    "must_separate_subissues": [
        "Formation versus reliance: Do not collapse bargain formation into reliance.",
        "Enforceability versus proof: The Statute of Frauds is an enforceability screen.",
        "Controlling gate versus secondary gates: Identify likely controlling SoF category first.",
        "Marriage-consideration versus incidental marriage: Distinguish marriage as real "
        "consideration from background context.",
        "One-year possibility-at-formation versus actual duration: Use formation-time possibility.",
        "Promise direction in suretyship: promise to creditor vs. debtor vs. proposed surety.",
        "Primary versus secondary liability: Separate collateral guaranty from true assumption.",
        "Main purpose doctrine versus general personal motive: Use main purpose only if "
        "suretyship is actually triggered.",
        "Motive versus condition precedent: A hoped-for benefit is not an express condition.",
        "Fallback doctrine versus universal cure: Map each fallback to the barrier it can address.",
    ],
    "benchmark_headings": [
        "Jurisdiction assumption",
        "Bottom-line outcome",
        "Controlling doctrine",
        "Formation",
        "Statute of Frauds Gates",
        "Exceptions/Promissory Estoppel",
        "Defenses/Mistake",
        "Strongest counterargument",
    ],
    "note": (
        "Pack 10 uses legacy headings for backward compatibility with current oral-promise runs. "
        "See 10_DOCTRINE_PACK_ORAL_PROMISE.txt section OUTPUT-SHAPE REMINDER."
    ),
}

_PACK_20_CONTENT: dict = {
    "id": "pack_20",
    "name": "Land Contracts",
    "categories": ["land-sale", "option", "lease", "easement", "part-performance"],
    "must_separate_subissues": [
        "Transaction characterization: characterize the transaction type before writing analysis.",
        "Writing compliance vs. equitable workaround: keep analytically separate.",
        "Missing writing vs. defective or partial writing: different problems.",
        "Legal remedies vs. equitable remedies when a substitute doctrine is raised.",
    ],
    "benchmark_headings": OUTPUT_SHELL_HEADINGS,
}

_PACK_30_CONTENT: dict = {
    "id": "pack_30",
    "name": "Executor or Administrator Personal Promise",
    "categories": ["personal-vs-representative-capacity", "preexisting-estate-debt"],
    "must_separate_subissues": [
        "Personal vs. representative capacity: separate from writing compliance.",
        "Preexisting decedent obligation vs. new post-death contract.",
        "Payment from estate assets vs. payment from representative's own funds.",
        "Executor-category vs. ordinary suretyship.",
    ],
    "benchmark_headings": OUTPUT_SHELL_HEADINGS,
}

_PACK_40_CONTENT: dict = {
    "id": "pack_40",
    "name": "Sale of Goods (UCC § 2-201)",
    "categories": [
        "goods-characterization",
        "merchant-confirmation",
        "quantity-term",
        "specially-manufactured",
        "admission",
        "payment-receipt-acceptance",
    ],
    "must_separate_subissues": [
        "Goods characterization: distinguish goods contract from services contract.",
        "Merchant status: required for merchant-confirmation rule.",
        "Writing sufficiency: keep quantity cap visible.",
        "Direct compliance vs. exception-based enforcement.",
        "Sale contract vs. separate collateral promise.",
    ],
    "quantity_cap_rule": (
        "Under the standard UCC § 2-201 formulation, the contract is enforceable only up "
        "to the quantity supported by the qualifying writing, admission, or conduct."
    ),
    "benchmark_headings": OUTPUT_SHELL_HEADINGS,
}

# Failure bank skeletons (label families only -- full text in .txt files)
_FAILURE_BANK_10: dict = {
    "pack_id": "pack_10",
    "label_families": {
        "SG": "Structural gatekeeping",
        "FR": "Formation / exchange framing",
        "SC": "Statute of Frauds core / gate selection",
        "MC": "Marriage-consideration",
        "OY": "One-year provision",
        "SU": "Suretyship",
        "FD": "Fallback doctrines and defenses",
        "XD": "Cross-cutting answer discipline",
        "OUT": "Outside current oral-promise bank scope",
    },
    "metadata_tags": {
        "outcome": ["Enforceable", "Not enforceable", "Mixed / depends", "No clear conclusion"],
        "outcome_correctness": [
            "Correct",
            "Arguably correct / jurisdiction-dependent",
            "Incorrect",
            "Indeterminate",
        ],
        "reasoning_alignment": [
            "Right result / right reason",
            "Right result / wrong or incomplete reason",
            "Wrong result / plausible reasoning",
            "Wrong result / poor reasoning",
        ],
        "jurisdiction_assumption": [
            "U.S. common law / Restatement-style",
            "Other stated jurisdiction",
            "No jurisdiction stated",
        ],
        "controlling_doctrine_named": [
            "Marriage-consideration Statute of Frauds",
            "One-year provision",
            "Suretyship",
            "Main purpose doctrine",
            "Promissory estoppel",
            "Formation / consideration",
            "Mistake / condition",
            "Mixed / multiple",
            "None named",
            "Other",
        ],
    },
    "assignment_rule": (
        "Assign metadata tags first. Then assign one primary doctrinal failure label. "
        "Add up to two secondary modifiers if needed. "
        "Prefer the earliest doctrinal gate that goes materially wrong."
    ),
}

_FAILURE_BANK_20: dict = {
    "pack_id": "pack_20",
    "label_families": {
        "SG": "Structural gatekeeping",
        "TC": "Transaction characterization",
        "WR": "Writing requirement",
        "WC": "Writing compliance",
        "EP": "Equitable workarounds (part performance, estoppel, restitution)",
        "XD": "Cross-cutting answer discipline",
        "OUT": "Outside current land pack scope",
    },
}

_FAILURE_BANK_30: dict = {
    "pack_id": "pack_30",
    "label_families": {
        "SG": "Structural gatekeeping",
        "CP": "Capacity / role characterization",
        "PR": "Preexisting obligation determination",
        "WR": "Writing requirement and compliance",
        "FD": "Fallback and original-undertaking theories",
        "XD": "Cross-cutting answer discipline",
        "OUT": "Outside current executor pack scope",
    },
}

_FAILURE_BANK_40: dict = {
    "pack_id": "pack_40",
    "label_families": {
        "SG": "Structural gatekeeping",
        "GC": "Goods characterization",
        "MS": "Merchant status",
        "WS": "Writing sufficiency",
        "MC": "Merchant-confirmation rule",
        "EX": "Exceptions (special manufacture, admission, payment / receipt-acceptance)",
        "QC": "Quantity cap",
        "XD": "Cross-cutting answer discipline",
        "OUT": "Outside current UCC 2-201 pack scope",
    },
}

# B-series pack maps. The old four-pack constants above remain as historical
# source material for tests/docs, but the public accessors below expose the
# six-pack B-series taxonomy.


def _read_fi_file(filename: str) -> str:  # noqa: ANN001
    """Read a FrankInstructions .txt file relative to this file's location.

    This is the only place file I/O occurs, and only during module import.
    """
    import pathlib

    fi_dir = pathlib.Path(__file__).parent.parent.parent.parent / "documents" / "FrankInstructions"
    path = fi_dir / filename
    if not path.exists():
        return f"[File not found: {filename}]"
    return path.read_text(encoding="utf-8")


_PACK_FILE_MAP: dict[str, str] = {
    "pack_marriage": "B11_Marriage_Provision_Pack.txt",
    "pack_suretyship": "B12_Suretyship_Provision_Pack.txt",
    "pack_one_year": "B13_One_Year_Provision_Pack.txt",
    "pack_land": "B14_Land_Provision_Pack.txt",
    "pack_ucc_2201": "B15_UCC_2_201_Provision_Pack.txt",
    "pack_executor": "B16_Executor_Provision_Pack.txt",
}

_WORKED_EXAMPLE_FILE_MAP: dict[str, str] = {
    "pack_marriage": "B21_Marriage_Worked_Benchmark_Example.txt",
    "pack_suretyship": "B22_Suretyship_Worked_Benchmark_Example.txt",
    "pack_one_year": "B23_One_Year_Worked_Benchmark_Example.txt",
    "pack_land": "B24_Land_Worked_Benchmark_Example.txt",
    "pack_ucc_2201": "B25_UCC_2_201_Worked_Benchmark_Example.txt",
    "pack_executor": "B26_Executor_Worked_Benchmark_Example.txt",
}

_DOCTRINE_PACKS: dict[str, dict] = {
    "pack_marriage": {
        "id": "pack_marriage",
        "name": "Marriage provision",
        "categories": ["marriage-consideration", "premarital-promise", "writing-trigger"],
        "source_file": _PACK_FILE_MAP["pack_marriage"],
        "worked_example_file": _WORKED_EXAMPLE_FILE_MAP["pack_marriage"],
        "must_separate_subissues": [
            "Marriage as bargained-for consideration versus relationship background.",
            "Promise timing and party direction.",
            "Writing requirement and any source-supported substitute.",
        ],
        "benchmark_headings": OUTPUT_SHELL_HEADINGS,
    },
    "pack_suretyship": {
        "id": "pack_suretyship",
        "name": "Suretyship provision",
        "categories": ["collateral-promise", "original-undertaking", "main-purpose"],
        "source_file": _PACK_FILE_MAP["pack_suretyship"],
        "worked_example_file": _WORKED_EXAMPLE_FILE_MAP["pack_suretyship"],
        "must_separate_subissues": [
            "Creditor, debtor, and promisor role direction.",
            "Collateral liability versus original undertaking.",
            "Writing trigger and any self-benefit or substitute route.",
        ],
        "benchmark_headings": OUTPUT_SHELL_HEADINGS,
    },
    "pack_one_year": {
        "id": "pack_one_year",
        "name": "One-year provision",
        "categories": ["formation-time-possibility", "duration", "termination"],
        "source_file": _PACK_FILE_MAP["pack_one_year"],
        "worked_example_file": _WORKED_EXAMPLE_FILE_MAP["pack_one_year"],
        "must_separate_subissues": [
            "Formation date and earliest possible full performance.",
            "Impossibility within one year versus unlikely performance.",
            "Termination, contingency, and writing-status distinctions.",
        ],
        "benchmark_headings": OUTPUT_SHELL_HEADINGS,
    },
    "pack_land": {
        "id": "pack_land",
        "name": "Land sale / interest in land provision",
        "categories": ["land-interest", "writing-sufficiency", "part-performance"],
        "source_file": _PACK_FILE_MAP["pack_land"],
        "worked_example_file": _WORKED_EXAMPLE_FILE_MAP["pack_land"],
        "must_separate_subissues": [
            "Transaction characterization and land-interest type.",
            "Writing trigger, essential terms, and direct compliance.",
            "Part performance, estoppel, and remedy-sensitive substitute limits.",
        ],
        "benchmark_headings": OUTPUT_SHELL_HEADINGS,
    },
    "pack_ucc_2201": {
        "id": "pack_ucc_2201",
        "name": "UCC 2-201 sale-of-goods provision",
        "categories": ["goods", "merchant-confirmation", "quantity", "ucc-exceptions"],
        "source_file": _PACK_FILE_MAP["pack_ucc_2201"],
        "worked_example_file": _WORKED_EXAMPLE_FILE_MAP["pack_ucc_2201"],
        "must_separate_subissues": [
            "Article 2 goods classification and threshold.",
            "Writing, authentication, and quantity-term sufficiency.",
            "Merchant confirmation and UCC exception routes.",
        ],
        "benchmark_headings": OUTPUT_SHELL_HEADINGS,
        "quantity_cap_rule": (
            "The contract is enforceable only up to the quantity supported by the "
            "qualifying writing, admission, or conduct."
        ),
    },
    "pack_executor": {
        "id": "pack_executor",
        "name": "Executor / administrator personal-promise provision",
        "categories": ["fiduciary-capacity", "estate-obligation", "personal-promise"],
        "source_file": _PACK_FILE_MAP["pack_executor"],
        "worked_example_file": _WORKED_EXAMPLE_FILE_MAP["pack_executor"],
        "must_separate_subissues": [
            "Fiduciary role and underlying estate obligation.",
            "Personal versus representative capacity.",
            "Writing trigger and source-supported substitute route.",
        ],
        "benchmark_headings": OUTPUT_SHELL_HEADINGS,
    },
}

_FAILURE_BANKS: dict[str, dict] = {
    "pack_marriage": {
        "pack_id": "pack_marriage",
        "label_families": {
            "SG": "Structural gatekeeping",
            "MC": "Marriage-consideration trigger",
            "WR": "Writing requirement",
            "FD": "Fallback doctrines and defenses",
            "XD": "Cross-cutting answer discipline",
            "OUT": "Outside current marriage provision scope",
        },
    },
    "pack_suretyship": {
        "pack_id": "pack_suretyship",
        "label_families": {
            "SG": "Structural gatekeeping",
            "RL": "Role direction",
            "CO": "Collateral versus original obligation",
            "MP": "Main-purpose / self-benefit route",
            "WR": "Writing requirement",
            "XD": "Cross-cutting answer discipline",
            "OUT": "Outside current suretyship provision scope",
        },
    },
    "pack_one_year": {
        "pack_id": "pack_one_year",
        "label_families": {
            "SG": "Structural gatekeeping",
            "TM": "Timing and formation-date measurement",
            "PF": "Possibility of full performance within one year",
            "TR": "Termination or contingency confusion",
            "WR": "Writing requirement",
            "XD": "Cross-cutting answer discipline",
            "OUT": "Outside current one-year provision scope",
        },
    },
    "pack_land": {
        "pack_id": "pack_land",
        "label_families": {
            "SG": "Structural gatekeeping",
            "TC": "Land transaction characterization",
            "WR": "Writing requirement",
            "WC": "Writing compliance",
            "EP": "Equitable workarounds",
            "XD": "Cross-cutting answer discipline",
            "OUT": "Outside current land provision scope",
        },
    },
    "pack_ucc_2201": {
        "pack_id": "pack_ucc_2201",
        "label_families": {
            "SG": "Structural gatekeeping",
            "GC": "Goods characterization",
            "MS": "Merchant status",
            "WS": "Writing sufficiency",
            "MC": "Merchant-confirmation rule",
            "EX": "UCC exceptions",
            "QC": "Quantity cap",
            "XD": "Cross-cutting answer discipline",
            "OUT": "Outside current UCC 2-201 provision scope",
        },
    },
    "pack_executor": {
        "pack_id": "pack_executor",
        "label_families": {
            "SG": "Structural gatekeeping",
            "CP": "Capacity / role characterization",
            "PR": "Preexisting estate obligation",
            "WR": "Writing requirement",
            "FD": "Fallback and original-undertaking theories",
            "XD": "Cross-cutting answer discipline",
            "OUT": "Outside current executor provision scope",
        },
    },
}

ROUTING_MATRIX = {
    "packs": {
        pack_id: {
            "name": pack["name"],
            "categories": pack["categories"],
            "source_file": pack["source_file"],
        }
        for pack_id, pack in _DOCTRINE_PACKS.items()
    },
    "core_routing_rule": (
        "Route by the controlling Statute of Frauds provision and gate order before "
        "offering variations."
    ),
    "routing_status_values": [
        "Stable route",
        "Multiple plausible routes",
        "Needs classification first",
        "Not primarily a Statute of Frauds problem",
    ],
}

VARIATION_LANE_CODES: dict[str, dict[str, str]] = {
    "A1": {
        "label": "Variable swap",
        "description": "Swap names, places, or labels while preserving legal role and path.",
    },
    "A2": {
        "label": "Threshold-preserving numeric shift",
        "description": (
            "Change numbers only when they stay on the same side of the legal threshold."
        ),
    },
    "A3": {
        "label": "Specificity shift",
        "description": "Move between general and specific labels without changing legal function.",
    },
    "A4": {
        "label": "Non-controlling salience injection",
        "description": "Add vivid but legally non-controlling detail to test overreaction.",
    },
    "B1": {
        "label": "Fact omission / ambiguity test",
        "description": "Remove or blur a fact needed to resolve a gate.",
    },
    "B2": {
        "label": "Controlled generalization",
        "description": "Generalize a precise fact to test bounded uncertainty and branching.",
    },
}

B_SERIES_ROUTING_GATES: dict[str, dict[str, str]] = {
    "G1": {
        "label": "Governing law family",
        "description": (
            "Classify whether the transaction is governed primarily by Article 2, "
            "common law, real-property doctrine, probate/executor doctrine, or a mixed framework."
        ),
    },
    "G2": {
        "label": "Statute of Frauds trigger",
        "description": (
            "Decide whether the selected provision is actually triggered rather than assuming "
            "the Statute of Frauds applies because a promise is oral."
        ),
    },
    "G3": {
        "label": "Variation readiness",
        "description": (
            "If classification depends on an unresolved fact, mark the route unstable before "
            "offering a normal Lane A menu."
        ),
    },
}

PENALTY_CODES: list[str] = [
    "P_ControllingDoctrineOmitted",
    "P_WrongPackDriver",
    "P_MaterialRuleMisstatement",
    "P_MaterialFactOrRoleOrTimelineError",
    "P_InventedComplianceFact",
    "P_ExceptionBleedOver",
    "P_IrrelevantDoctrine",
    "P_ExcessiveHedging",
    "P_RelianceByPerformance",
    "P_JurisdictionDrift",
    "P_HallucinatedCaseCitation",
]

CAP_CODES: list[str] = [
    "CAP_60_ControllingDoctrineOmitted",
    "CAP_60_WrongPackDriver",
    "CAP_70_NoClearConclusion",
    "CAP_75_InventedCoreCompliance",
    "CAP_75_HallucinatedCoreAuthority",
]

JUDGE_MODELS: list[str] = [
    "deepseek-ai/DeepSeek-V3",
    "deepseek-ai/DeepSeek-R1",
    "Qwen/Qwen2.5-7B-Instruct-Turbo",
    "meta-llama/Llama-3.3-70B-Instruct-Turbo",
]

_CONFUSION_SET_FILE_MAP: dict[frozenset[str], str] = {
    frozenset(["pack_marriage", "pack_land"]): (
        "B31_Marriage_and_Land_Dual_Trigger_Confusion_Set.txt"
    ),
    frozenset(["pack_executor", "pack_suretyship"]): (
        "B32_Executor_and_Suretyship_Overlap_Confusion_Set.txt"
    ),
    frozenset(["pack_ucc_2201", "pack_one_year"]): (
        "B33_UCC_and_One_Year_Priority_Confusion_Set.txt"
    ),
    frozenset(["pack_land", "pack_one_year"]): ("B34_Land_and_One_Year_Lease_Confusion_Set.txt"),
    frozenset(["pack_ucc_2201", "pack_suretyship"]): (
        "B35_UCC_and_Suretyship_Split_Transaction_Confusion_Set.txt"
    ),
    frozenset(["pack_ucc_2201", "pack_land"]): (
        "B36_UCC_and_Land_Fixtures_or_Severance_Confusion_Set.txt"
    ),
}

_WORKED_EXAMPLES: dict[str, list[str]] = {}
_CLEAN_BENCHMARKS: dict[str, list[str]] = {}

# ---------------------------------------------------------------------------
# Public accessors
# ---------------------------------------------------------------------------

_VALID_PACKS = frozenset(_DOCTRINE_PACKS.keys())


def get_doctrine_pack(pack_id: str) -> dict:
    """Return the doctrine pack dict for the given pack_id.

    Returns a dict with at least: id, name, categories, must_separate_subissues,
    benchmark_headings. Also includes raw doctrine text under key 'raw_text' if
    the source file can be read.
    """
    if pack_id not in _VALID_PACKS:
        raise ValueError(f"Unknown pack_id: {pack_id!r}. Valid: {sorted(_VALID_PACKS)}")
    pack = dict(_DOCTRINE_PACKS[pack_id])
    pack["raw_text"] = _read_fi_file(pack["source_file"])
    pack["worked_example_text"] = _read_fi_file(pack["worked_example_file"])
    return pack


def get_failure_bank(pack_id: str) -> dict:
    """Return the failure bank dict for the given pack_id.

    Includes label families, metadata tags (where defined), and assignment rules.
    Also includes raw bank text under key 'raw_text'.
    """
    if pack_id not in _VALID_PACKS:
        raise ValueError(f"Unknown pack_id: {pack_id!r}. Valid: {sorted(_VALID_PACKS)}")
    bank = dict(_FAILURE_BANKS[pack_id])
    bank["raw_text"] = _read_fi_file(_PACK_FILE_MAP[pack_id])
    return bank


def get_worked_examples(pack_id: str) -> list[str]:
    """Return worked benchmark examples for the given B-series pack_id."""
    if pack_id not in _VALID_PACKS:
        raise ValueError(f"Unknown pack_id: {pack_id!r}. Valid: {sorted(_VALID_PACKS)}")
    if pack_id not in _WORKED_EXAMPLES:
        _WORKED_EXAMPLES[pack_id] = [_read_fi_file(_WORKED_EXAMPLE_FILE_MAP[pack_id])]
    return _WORKED_EXAMPLES[pack_id]


def get_clean_benchmarks(pack_id: str) -> list[str]:
    """Return clean benchmark examples for the given B-series pack_id.

    The B-series supplies worked benchmark examples rather than separate clean
    benchmark files, so the same pack-specific B21-B26 source is exposed here
    for downstream prompt compatibility.
    """
    if pack_id not in _VALID_PACKS:
        raise ValueError(f"Unknown pack_id: {pack_id!r}. Valid: {sorted(_VALID_PACKS)}")
    if pack_id not in _CLEAN_BENCHMARKS:
        _CLEAN_BENCHMARKS[pack_id] = [_read_fi_file(_WORKED_EXAMPLE_FILE_MAP[pack_id])]
    return _CLEAN_BENCHMARKS[pack_id]


def get_confusion_set(pack_a: str, pack_b: str) -> dict:
    """Return a B-series cross-pack confusion set for an unordered pack pair."""
    if pack_a not in _VALID_PACKS:
        raise ValueError(f"Unknown pack_id: {pack_a!r}. Valid: {sorted(_VALID_PACKS)}")
    if pack_b not in _VALID_PACKS:
        raise ValueError(f"Unknown pack_id: {pack_b!r}. Valid: {sorted(_VALID_PACKS)}")
    key = frozenset([pack_a, pack_b])
    filename = _CONFUSION_SET_FILE_MAP.get(key)
    if not filename:
        raise ValueError(f"No confusion set registered for pack pair: {pack_a}, {pack_b}")
    return {
        "pack_a": pack_a,
        "pack_b": pack_b,
        "source_file": filename,
        "raw_text": _read_fi_file(filename),
    }
