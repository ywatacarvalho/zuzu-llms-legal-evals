import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class RubricCriterion(BaseModel):
    id: str
    name: str
    description: str
    weight: float = Field(gt=0, le=1)
    module_id: int | None = None
    # Karthic row-card enrichment fields. These are optional so legacy RRD
    # criteria remain valid until the enrichment pass is enabled.
    row_code: str | None = None
    na_guidance: str | None = None
    golden_target_summary: str | None = None
    golden_contains: list[str] | None = None
    allowed_omissions: list[str] | str | None = None
    contradiction_flags: list[str] | None = None
    comparison_guidance: str | None = None
    scoring_anchors: dict[str, str] | None = None
    primary_failure_labels: list[str] | None = None
    row_status: Literal["anchor", "provisional"] | None = None


class RubricCreate(BaseModel):
    case_id: uuid.UUID
    question: str = Field(min_length=10)


class RubricOut(BaseModel):
    id: uuid.UUID
    evaluation_id: uuid.UUID | None = None
    case_id: uuid.UUID | None = None
    question: str | None = None
    status: str = "building"
    criteria: list[RubricCriterion] | None = None
    raw_response: str | None = None
    is_frozen: bool = False
    conditioning_sample: list[str] | None = None
    decomposition_tree: dict | None = None
    refinement_passes: list | None = None
    stopping_metadata: dict | None = None
    setup_responses: list | None = None
    strong_reference_text: str | None = None
    weak_reference_text: str | None = None
    # FrankInstructions pipeline data
    screening_result: dict | None = None
    source_extraction: dict | None = None
    gold_packet_mapping: dict | None = None
    doctrine_pack: str | None = None
    routing_metadata: dict | None = None
    predicted_failure_modes: list | None = None
    gold_answer: str | None = None
    generated_question: str | None = None
    self_audit_result: dict | None = None
    question_analysis: dict | None = None
    # FrankInstructions HITL gate
    fi_status: str | None = None
    fi_stream_id: str | None = None
    review_notes: str | None = None
    # Locked controller card (Step 2A)
    controller_card: dict[str, Any] | None = None
    controller_card_version: str | None = None
    # Variation / dual-rubric fields
    selected_lane_code: str | None = None
    dual_rubric_mode: bool = False
    base_question: str | None = None
    base_gold_answer: str | None = None
    variation_question: str | None = None
    variation_criteria: list[RubricCriterion] | dict | None = None
    # Citation verification
    workflow_source_case_name: str | None = None
    workflow_source_case_citation: str | None = None
    case_citation_verification_mode: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RubricApproveRequest(BaseModel):
    action: Literal["approve", "reject", "reroute"]
    reroute_pack: str | None = None
    notes: str | None = None


class CompareDraftRequest(BaseModel):
    draft_text: str = Field(min_length=10)


class VariationMenuRequest(BaseModel):
    pass


class SelectVariationRequest(BaseModel):
    selected_lane_code: str | None
