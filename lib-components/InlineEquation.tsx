import React from 'react';
import katex from 'katex';

/**
 * InlineEquation — renders a single LaTeX formula using KaTeX directly.
 * Use for standalone formula blocks in UI (e.g., course cards).
 *
 * For full Markdown+math document rendering, use <MathContent> instead.
 *
 * @param {string}  latex       LaTeX source string
 * @param {boolean} displayMode true = centred display, false = inline
 */
export interface InlineEquationProps {
  latex: string;
  displayMode?: boolean;
}

export function InlineEquation({ latex, displayMode = false }: InlineEquationProps) {
  let html = '';
  try {
    html = katex.renderToString(latex, {
      throwOnError: false,
      displayMode,
      output: 'html',
    });
  } catch {
    html = `<span class="text-destructive text-xs pr-1">[equation error]</span>`;
  }

  return (
    <span
      className={displayMode ? 'block overflow-x-auto py-2 text-foreground' : 'inline text-foreground'}
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}
