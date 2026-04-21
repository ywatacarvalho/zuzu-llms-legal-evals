from dataclasses import dataclass


@dataclass(frozen=True)
class ModelInfo:
    id: str
    name: str
    provider: str


# Models used internally for rubric assembly (sample-response generation) and final judging.
# These are excluded from the user-facing comparison pool to avoid methodological conflicts.
CONTROL_MODEL = "deepseek-ai/DeepSeek-V3"

# Reference pair for misalignment filtering (positive-edge proxy, per RRD paper §2.3).
# A criterion is misaligned if it prefers the weak response over the strong one.
STRONG_REF_MODEL = "deepseek-ai/DeepSeek-R1"
WEAK_REF_MODEL = "Qwen/Qwen2.5-7B-Instruct-Turbo"

SETUP_MODELS: list[ModelInfo] = [
    ModelInfo("deepseek-ai/DeepSeek-V3", "DeepSeek V3", "DeepSeek"),
    ModelInfo("deepseek-ai/DeepSeek-R1", "DeepSeek R1", "DeepSeek"),
    ModelInfo("Qwen/Qwen2.5-7B-Instruct-Turbo", "Qwen 2.5 7B", "Alibaba"),
    ModelInfo("meta-llama/Llama-3.3-70B-Instruct-Turbo", "Llama 3.3 70B", "Meta"),
]

SETUP_MODEL_IDS: set[str] = {m.id for m in SETUP_MODELS}

# Models available for user selection in the comparison stage.
# Must not overlap with SETUP_MODELS or the control/judge model.
# Sourced from Together AI serverless catalog (price <= $2/M, latency < 30s).
AVAILABLE_MODELS: list[ModelInfo] = [
    ModelInfo("LiquidAI/LFM2-24B-A2B", "LFM2 24B", "LiquidAI"),
    ModelInfo("openai/gpt-oss-20b", "GPT OSS 20B", "OpenAI"),
    ModelInfo("arize-ai/qwen-2-1.5b-instruct", "Qwen 2 1.5B", "Arize/Alibaba"),
    ModelInfo("meta-llama/Meta-Llama-3-8B-Instruct-Lite", "Llama 3 8B Lite", "Meta"),
    ModelInfo("essentialai/rnj-1-instruct", "RNJ-1", "EssentialAI"),
    ModelInfo("openai/gpt-oss-120b", "GPT OSS 120B", "OpenAI"),
    ModelInfo("Qwen/Qwen3-235B-A22B-Instruct-2507-tput", "Qwen3 235B", "Alibaba"),
    ModelInfo("MiniMaxAI/MiniMax-M2.5", "MiniMax M2.5", "MiniMaxAI"),
    ModelInfo("deepseek-ai/DeepSeek-V3.1", "DeepSeek V3.1", "DeepSeek"),
    ModelInfo("Qwen/Qwen3.5-397B-A17B", "Qwen3.5 397B", "Alibaba"),
    ModelInfo("zai-org/GLM-5", "GLM-5", "ZhipuAI"),
    ModelInfo("deepcogito/cogito-v2-1-671b", "Cogito V2.1 671B", "DeepCogito"),
    ModelInfo("MiniMaxAI/MiniMax-M2.7", "MiniMax M2.7", "MiniMaxAI"),
    ModelInfo("zai-org/GLM-5.1", "GLM-5.1", "ZhipuAI"),
]

AVAILABLE_MODEL_IDS: set[str] = {m.id for m in AVAILABLE_MODELS}
