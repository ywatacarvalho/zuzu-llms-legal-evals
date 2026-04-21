import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rubric import Rubric


class RubricRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_standalone(
        self,
        case_id: uuid.UUID,
        question: str,
    ) -> Rubric:
        rubric = Rubric(
            case_id=case_id,
            question=question,
            status="building",
            is_frozen=False,
        )
        self.db.add(rubric)
        await self.db.commit()
        await self.db.refresh(rubric)
        return rubric

    async def create(
        self,
        evaluation_id: uuid.UUID | None = None,
        criteria: list[dict] | None = None,
        raw_response: str | None = None,
        decomposition_tree: dict | None = None,
        refinement_passes: list | None = None,
        stopping_metadata: dict | None = None,
        conditioning_sample: list | None = None,
        is_frozen: bool = False,
        setup_responses: list | None = None,
        strong_reference_text: str | None = None,
        weak_reference_text: str | None = None,
    ) -> Rubric:
        rubric = Rubric(
            evaluation_id=evaluation_id,
            criteria=criteria,
            raw_response=raw_response,
            decomposition_tree=decomposition_tree,
            refinement_passes=refinement_passes,
            stopping_metadata=stopping_metadata,
            conditioning_sample=conditioning_sample,
            is_frozen=is_frozen,
            setup_responses=setup_responses,
            strong_reference_text=strong_reference_text,
            weak_reference_text=weak_reference_text,
        )
        self.db.add(rubric)
        await self.db.commit()
        await self.db.refresh(rubric)
        return rubric

    async def get_by_id(self, rubric_id: uuid.UUID) -> Rubric | None:
        result = await self.db.execute(select(Rubric).where(Rubric.id == rubric_id))
        return result.scalar_one_or_none()

    async def get_by_evaluation_id(self, evaluation_id: uuid.UUID) -> Rubric | None:
        result = await self.db.execute(select(Rubric).where(Rubric.evaluation_id == evaluation_id))
        return result.scalar_one_or_none()

    async def list_all(
        self,
        case_id: uuid.UUID | None = None,
        status: str | None = None,
    ) -> list[Rubric]:
        stmt = select(Rubric)
        if case_id is not None:
            stmt = stmt.where(Rubric.case_id == case_id)
        if status is not None:
            stmt = stmt.where(Rubric.status == status)
        stmt = stmt.order_by(Rubric.created_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def list_frozen(self) -> list[Rubric]:
        return await self.list_all(status="frozen")

    async def set_status(self, rubric_id: uuid.UUID, status: str) -> None:
        rubric = await self.get_by_id(rubric_id)
        if rubric:
            rubric.status = status
            if status == "frozen":
                rubric.is_frozen = True
            await self.db.commit()

    async def reset_for_rerun(self, rubric_id: uuid.UUID) -> None:
        """Wipe build artifacts and reset status to building for a re-run."""
        rubric = await self.get_by_id(rubric_id)
        if not rubric:
            return
        rubric.status = "building"
        rubric.is_frozen = False
        rubric.criteria = None
        rubric.decomposition_tree = None
        rubric.refinement_passes = None
        rubric.stopping_metadata = None
        rubric.conditioning_sample = None
        rubric.setup_responses = None
        rubric.strong_reference_text = None
        rubric.weak_reference_text = None
        rubric.screening_result = None
        rubric.source_extraction = None
        rubric.gold_packet_mapping = None
        rubric.doctrine_pack = None
        rubric.routing_metadata = None
        rubric.predicted_failure_modes = None
        rubric.gold_answer = None
        rubric.generated_question = None
        rubric.self_audit_result = None
        rubric.question_analysis = None
        rubric.fi_status = None
        rubric.fi_stream_id = None
        rubric.review_notes = None
        rubric.controller_card = None
        rubric.controller_card_version = None
        rubric.selected_lane_code = None
        rubric.dual_rubric_mode = False
        rubric.base_question = None
        rubric.base_gold_answer = None
        rubric.variation_question = None
        rubric.variation_criteria = None
        rubric.workflow_source_case_name = None
        rubric.workflow_source_case_citation = None
        rubric.case_citation_verification_mode = False
        await self.db.commit()

    async def freeze(self, rubric_id: uuid.UUID) -> Rubric | None:
        rubric = await self.get_by_id(rubric_id)
        if rubric:
            rubric.is_frozen = True
            rubric.status = "frozen"
            await self.db.commit()
            await self.db.refresh(rubric)
        return rubric

    async def update_rubric_data(
        self,
        rubric_id: uuid.UUID,
        criteria: list[dict],
        decomposition_tree: dict | None = None,
        refinement_passes: list | None = None,
        stopping_metadata: dict | None = None,
        conditioning_sample: list | None = None,
        setup_responses: list | None = None,
        strong_reference_text: str | None = None,
        weak_reference_text: str | None = None,
        screening_result: dict | None = None,
        source_extraction: dict | None = None,
        gold_packet_mapping: dict | None = None,
        doctrine_pack: str | None = None,
        routing_metadata: dict | None = None,
        predicted_failure_modes: list | None = None,
        gold_answer: str | None = None,
        generated_question: str | None = None,
        self_audit_result: dict | None = None,
        question_analysis: dict | None = None,
        controller_card: dict | None = None,
        controller_card_version: str | None = None,
        selected_lane_code: str | None = None,
        dual_rubric_mode: bool | None = None,
        base_question: str | None = None,
        base_gold_answer: str | None = None,
        variation_question: str | None = None,
        variation_criteria: dict | list | None = None,
        workflow_source_case_name: str | None = None,
        workflow_source_case_citation: str | None = None,
        case_citation_verification_mode: bool | None = None,
    ) -> Rubric | None:
        rubric = await self.get_by_id(rubric_id)
        if not rubric:
            return None
        rubric.criteria = criteria
        rubric.decomposition_tree = decomposition_tree
        rubric.refinement_passes = refinement_passes
        rubric.stopping_metadata = stopping_metadata
        rubric.conditioning_sample = conditioning_sample
        rubric.setup_responses = setup_responses
        rubric.strong_reference_text = strong_reference_text
        rubric.weak_reference_text = weak_reference_text
        rubric.screening_result = screening_result
        rubric.source_extraction = source_extraction
        rubric.gold_packet_mapping = gold_packet_mapping
        rubric.doctrine_pack = doctrine_pack
        rubric.routing_metadata = routing_metadata
        rubric.predicted_failure_modes = predicted_failure_modes
        rubric.gold_answer = gold_answer
        rubric.generated_question = generated_question
        rubric.self_audit_result = self_audit_result
        rubric.question_analysis = question_analysis
        rubric.controller_card = controller_card
        rubric.controller_card_version = controller_card_version
        rubric.selected_lane_code = selected_lane_code
        if dual_rubric_mode is not None:
            rubric.dual_rubric_mode = dual_rubric_mode
        rubric.base_question = base_question
        rubric.base_gold_answer = base_gold_answer
        rubric.variation_question = variation_question
        rubric.variation_criteria = variation_criteria
        rubric.workflow_source_case_name = workflow_source_case_name
        rubric.workflow_source_case_citation = workflow_source_case_citation
        if case_citation_verification_mode is not None:
            rubric.case_citation_verification_mode = case_citation_verification_mode
        rubric.is_frozen = True
        rubric.status = "frozen"
        await self.db.commit()
        await self.db.refresh(rubric)
        return rubric

    async def save_fi_intermediate(
        self,
        rubric_id: uuid.UUID,
        fi_status: str,
        fi_stream_id: str | None = None,
        gold_answer: str | None = None,
        weak_reference_text: str | None = None,
        self_audit_result: dict | None = None,
        screening_result: dict | None = None,
        source_extraction: dict | None = None,
        routing_metadata: dict | None = None,
        doctrine_pack: str | None = None,
        gold_packet_mapping: dict | None = None,
        predicted_failure_modes: list | None = None,
        question_analysis: dict | None = None,
        controller_card: dict | None = None,
        controller_card_version: str | None = None,
        selected_lane_code: str | None = None,
        dual_rubric_mode: bool | None = None,
        base_question: str | None = None,
        base_gold_answer: str | None = None,
        variation_question: str | None = None,
        variation_criteria: dict | list | None = None,
        workflow_source_case_name: str | None = None,
        workflow_source_case_citation: str | None = None,
        case_citation_verification_mode: bool | None = None,
    ) -> Rubric | None:
        """Persist Phase A FI results without freezing the rubric.

        Sets the provided fi_status and saves all intermediate FI fields.
        The rubric remains in 'building' status (not frozen) until Phase B completes.
        """
        rubric = await self.get_by_id(rubric_id)
        if not rubric:
            return None
        rubric.fi_status = fi_status
        rubric.fi_stream_id = fi_stream_id
        rubric.gold_answer = gold_answer
        rubric.weak_reference_text = weak_reference_text
        rubric.self_audit_result = self_audit_result
        rubric.screening_result = screening_result
        rubric.source_extraction = source_extraction
        rubric.routing_metadata = routing_metadata
        rubric.doctrine_pack = doctrine_pack
        rubric.gold_packet_mapping = gold_packet_mapping
        rubric.predicted_failure_modes = predicted_failure_modes
        rubric.question_analysis = question_analysis
        rubric.controller_card = controller_card
        rubric.controller_card_version = controller_card_version
        rubric.selected_lane_code = selected_lane_code
        if dual_rubric_mode is not None:
            rubric.dual_rubric_mode = dual_rubric_mode
        rubric.base_question = base_question
        rubric.base_gold_answer = base_gold_answer
        rubric.variation_question = variation_question
        rubric.variation_criteria = variation_criteria
        rubric.workflow_source_case_name = workflow_source_case_name
        rubric.workflow_source_case_citation = workflow_source_case_citation
        if case_citation_verification_mode is not None:
            rubric.case_citation_verification_mode = case_citation_verification_mode
        await self.db.commit()
        await self.db.refresh(rubric)
        return rubric

    async def save_controller_card(
        self,
        rubric_id: uuid.UUID,
        controller_card: dict,
        controller_card_version: str | None = None,
        workflow_source_case_name: str | None = None,
        workflow_source_case_citation: str | None = None,
        case_citation_verification_mode: bool = False,
    ) -> Rubric | None:
        """Persist the locked controller card and source-case monitoring fields."""
        rubric = await self.get_by_id(rubric_id)
        if not rubric:
            return None
        rubric.controller_card = controller_card
        rubric.controller_card_version = controller_card_version
        rubric.workflow_source_case_name = workflow_source_case_name
        rubric.workflow_source_case_citation = workflow_source_case_citation
        rubric.case_citation_verification_mode = case_citation_verification_mode
        await self.db.commit()
        await self.db.refresh(rubric)
        return rubric

    async def approve_fi(
        self,
        rubric_id: uuid.UUID,
        fi_status: str | None,
        review_notes: str | None = None,
    ) -> Rubric | None:
        """Record a human review decision on a rubric awaiting HITL approval."""
        rubric = await self.get_by_id(rubric_id)
        if not rubric:
            return None
        rubric.fi_status = fi_status
        if review_notes is not None:
            rubric.review_notes = review_notes
        await self.db.commit()
        await self.db.refresh(rubric)
        return rubric
