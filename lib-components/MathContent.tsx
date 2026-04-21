import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import rehypeRaw from 'rehype-raw';

/**
 * MathContent — renders Markdown with full LaTeX math support via KaTeX.
 *
 * Inline math:   $E = mc^2$
 * Display math:  $$\hat{\beta} = (X^TX)^{-1}X^Ty$$
 */
export interface MathContentProps {
  children: string;
  className?: string;
}

export function MathContent({ children, className = '' }: MathContentProps) {
  return (
    <div
      className={[
        'prose max-w-none dark:prose-invert',
        'prose-h2:mt-10 prose-h2:text-2xl prose-h2:font-bold prose-h2:text-foreground',
        'prose-h3:mt-6 prose-h3:text-xl prose-h3:font-semibold prose-h3:text-foreground',
        'prose-p:leading-relaxed prose-p:text-muted-foreground',
        'prose-li:text-muted-foreground',
        'prose-strong:text-foreground',
        'prose-blockquote:border-l-primary prose-blockquote:bg-primary/10',
        'prose-blockquote:py-1 prose-blockquote:px-4 prose-blockquote:rounded-r-lg prose-blockquote:not-italic',
        'prose-code:bg-secondary prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:text-sm prose-code:text-secondary-foreground prose-code:before:content-none prose-code:after:content-none',
        'prose-pre:bg-muted prose-pre:border prose-pre:border-border prose-pre:rounded-xl',
        'prose-table:border-collapse prose-th:border prose-th:border-border prose-th:px-4 prose-th:py-2 prose-th:bg-muted/50',
        'prose-td:border prose-td:border-border prose-td:px-4 prose-td:py-2',
        className,
      ].join(' ')}
    >
      <ReactMarkdown
        remarkPlugins={[remarkMath]}
        rehypePlugins={[rehypeKatex, rehypeRaw]}
      >
        {children}
      </ReactMarkdown>
    </div>
  );
}
