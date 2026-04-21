export interface InternalModelInfo {
  id: string;
  name: string;
  provider: string;
  roleKey: string;
  styleKey: string;
}

export const INTERNAL_MODELS: InternalModelInfo[] = [
  {
    id: "deepseek-ai/DeepSeek-V3",
    name: "DeepSeek V3",
    provider: "DeepSeek",
    roleKey: "description.modelRegistry.roles.controlSetup",
    styleKey: "description.modelRegistry.styles.instruction",
  },
  {
    id: "deepseek-ai/DeepSeek-R1",
    name: "DeepSeek R1",
    provider: "DeepSeek",
    roleKey: "description.modelRegistry.roles.strongSetup",
    styleKey: "description.modelRegistry.styles.chainOfThought",
  },
  {
    id: "Qwen/Qwen2.5-7B-Instruct-Turbo",
    name: "Qwen 2.5 7B",
    provider: "Alibaba",
    roleKey: "description.modelRegistry.roles.weakSetup",
    styleKey: "description.modelRegistry.styles.instruction",
  },
  {
    id: "meta-llama/Llama-3.3-70B-Instruct-Turbo",
    name: "Llama 3.3 70B",
    provider: "Meta",
    roleKey: "description.modelRegistry.roles.setup",
    styleKey: "description.modelRegistry.styles.instruction",
  },
];
