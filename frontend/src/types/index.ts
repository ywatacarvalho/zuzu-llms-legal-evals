export interface ModelInfo {
  id: string;
  name: string;
  provider: string;
}

export interface User {
  id: string;
  email: string;
  created_at: string;
  updated_at: string;
}

export interface LegalCase {
  id: string;
  title: string;
  filename: string;
  raw_text: string | null;
  created_at: string;
  updated_at: string;
}

export interface RubricCriterion {
  id: string;
  name: string;
  description: string;
  weight: number;
  module_id?: number | null;
  row_code?: string | null;
  na_guidance?: string | null;
  golden_target_summary?: string | null;
  golden_contains?: string[] | null;
  allowed_omissions?: string[] | string | null;
  contradiction_flags?: string[] | null;
  comparison_guidance?: string | null;
  scoring_anchors?: Record<string, string> | null;
  primary_failure_labels?: string[] | null;
  row_status?: "anchor" | "provisional" | null;
}

export interface SetupResponse {
  model: string;
  text: string;
}

export type RubricStatus = "building" | "frozen" | "failed";

export type FIStatus =
  | "extracting"
  | "awaiting_review"
  | "approved"
  | "variation_pending"
  | "completed"
  | "rejected"
  | null;

export type VariationLaneCode = "A1" | "A2" | "A3" | "A4" | "B1" | "B2" | null;

export interface VariationOption {
  lane_code: VariationLaneCode;
  label: string;
  what_changes: string;
  why_it_fits: string;
  expected_answer_reuse: string;
  main_red_flag: string;
}

export interface ControllerCard {
  [key: string]: unknown;
}

export interface CentroidCompositionEntry {
  model_name: string;
  answer_count: number;
  answer_share: number;
}

export interface CentroidComposition {
  cluster_size_total: number;
  model_breakdown: CentroidCompositionEntry[];
  represented_model_count: number;
  dominant_model_name: string;
  dominant_model_count: number;
  dominant_model_share: number;
}

export interface OverlayResult {
  penalties_applied: Array<{ code: string; points: number; label: string }>;
  cap_status: { cap_code: string | null; applied: boolean };
  subtotal: number;
  post_penalty_score: number;
  final_score: number;
}

export interface JudgePanel {
  models: string[];
  mode: "single_model" | "multi_model_panel";
  aggregation_rule: string;
  homogeneity_status: string;
}

export interface ZakFlag {
  flag: "yes" | "no";
  reason: "no_majority" | null;
  disputed_centroids: number[];
}

export interface Module0Metadata {
  bottom_line_outcome: string;
  outcome_correctness: "correct" | "incorrect" | "partial" | "unclear";
  reasoning_alignment: "aligned" | "misaligned" | "partial";
  jurisdiction_assumption: string;
  controlling_doctrine_named: string;
}

export type FIApproveAction = "approve" | "reject" | "reroute";

export interface RubricApproveRequest {
  action: FIApproveAction;
  reroute_pack?: string;
  notes?: string;
}

export interface Rubric {
  id: string;
  evaluation_id: string | null;
  case_id: string | null;
  question: string | null;
  status: RubricStatus;
  criteria: RubricCriterion[] | null;
  raw_response: string | null;
  is_frozen: boolean;
  conditioning_sample: string[] | null;
  decomposition_tree: Record<string, string[]> | null;
  refinement_passes: RefinementPass[] | null;
  stopping_metadata: StoppingMetadata | null;
  setup_responses: SetupResponse[] | null;
  strong_reference_text: string | null;
  weak_reference_text: string | null;
  // FrankInstructions pipeline data
  screening_result: Record<string, unknown> | null;
  source_extraction: Record<string, unknown> | null;
  gold_packet_mapping: Record<string, unknown> | null;
  doctrine_pack: string | null;
  routing_metadata: Record<string, unknown> | null;
  predicted_failure_modes: Record<string, unknown>[] | null;
  gold_answer: string | null;
  generated_question: string | null;
  self_audit_result: Record<string, unknown> | null;
  question_analysis: Record<string, unknown> | null;
  // FrankInstructions HITL gate
  fi_status: FIStatus;
  fi_stream_id: string | null;
  review_notes: string | null;
  // Locked controller card and variation metadata
  controller_card: ControllerCard | null;
  controller_card_version: string | null;
  selected_lane_code: VariationLaneCode;
  dual_rubric_mode: boolean;
  base_question: string | null;
  base_gold_answer: string | null;
  variation_question: string | null;
  variation_criteria: RubricCriterion[] | Record<string, unknown> | null;
  // Citation verification
  workflow_source_case_name: string | null;
  workflow_source_case_citation: string | null;
  case_citation_verification_mode: boolean;
  created_at: string;
  updated_at: string;
}

export interface RefinementPass {
  pass_number: number;
  accepted: number;
  rejected_misalignment: number;
  rejected_redundancy: number;
  decomposition_empty: number;
}

export interface StoppingMetadata {
  reason: string;
  total_rejected: number;
  passes_completed: number;
}

export enum EvaluationStatus {
  Pending = "pending",
  RubricBuilding = "rubric_building",
  RubricFrozen = "rubric_frozen",
  Running = "running",
  Done = "done",
  Failed = "failed",
}

export interface Evaluation {
  id: string;
  case_id: string | null;
  rubric_id: string | null;
  question: string;
  model_names: string[] | null;
  status: EvaluationStatus;
  response_count: number;
  created_at: string;
  updated_at: string;
}

export interface ModelResponse {
  id: string;
  evaluation_id: string;
  model_name: string;
  response_text: string | null;
  run_index: number;
  question_version: string;
  created_at: string;
  updated_at: string;
}

export interface ClusterResult {
  cluster_id: number;
  response_indices: number[];
  centroid_index: number;
  centroid_response_text: string | null;
  model_counts: Record<string, number> | null;
  composition?: CentroidComposition | null;
  overlay?: OverlayResult | null;
}

export interface DashboardStats {
  total_cases: number;
  evaluations_run: number;
  models_evaluated: number;
  avg_clusters: number;
}

export interface WeightingModeResult {
  scores: Record<string, number>;
  winning_cluster: number;
  model_shares: Record<string, number>;
}

export interface Analysis {
  id: string;
  evaluation_id: string;
  k: number;
  clusters: ClusterResult[] | null;
  centroid_indices: number[] | null;
  scores: Record<string, number> | null;
  winning_cluster: number | null;
  model_shares: Record<string, number> | null;
  weighting_mode: string | null;
  baseline_scores: Record<string, Record<string, number>> | null;
  weighting_comparison: Record<string, WeightingModeResult> | null;
  silhouette_scores_by_k: Record<string, number> | null;
  failure_tags: Record<string, unknown> | null;
  centroid_composition: Record<string, CentroidComposition> | null;
  penalties_applied: Record<string, unknown> | null;
  cap_status: Record<string, unknown> | null;
  final_scores: Record<string, number> | Record<string, unknown>[] | null;
  case_citation_metadata: Record<string, unknown> | null;
  judge_panel: JudgePanel | Record<string, unknown> | null;
  judge_votes: Record<string, unknown> | null;
  zak_review_flag: ZakFlag | Record<string, unknown> | null;
  variation_scores: Record<string, unknown> | Record<string, unknown>[] | null;
  created_at: string;
  updated_at: string;
}

export type AnalysisResult = Analysis;
