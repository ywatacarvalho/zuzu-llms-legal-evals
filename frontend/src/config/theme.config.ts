export type ThemeId = "light" | "dark" | "clean";

export interface ThemeOption {
  id: ThemeId;
  label: string;
}

export const themes: ThemeOption[] = [
  { id: "light", label: "Light" },
  { id: "dark", label: "Dark" },
  { id: "clean", label: "Clean" },
];
