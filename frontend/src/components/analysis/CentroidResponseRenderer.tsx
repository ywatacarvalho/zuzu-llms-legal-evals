import type { ReactNode } from "react";

interface CentroidResponseRendererProps {
  text: string;
}

type TableBlock = {
  headers: string[];
  rows: string[][];
};

function renderInline(text: string, keyPrefix: string): ReactNode[] {
  const parts: ReactNode[] = [];
  const pattern = /\*\*([^*]+)\*\*/g;
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = pattern.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push(text.slice(lastIndex, match.index));
    }
    parts.push(
      <strong key={`${keyPrefix}-${match.index}`} className="font-semibold text-foreground">
        {match[1]}
      </strong>
    );
    lastIndex = match.index + match[0].length;
  }

  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex));
  }

  return parts.length > 0 ? parts : [text];
}

function isTableSeparator(line: string) {
  return /^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$/.test(line);
}

function isPipeRow(line: string) {
  const trimmed = line.trim();
  return trimmed.startsWith("|") && trimmed.slice(1).includes("|");
}

function parsePipeRow(line: string) {
  const trimmed = line.trim().replace(/^\|/, "");
  const withoutOptionalTrailingPipe = trimmed.endsWith("|") ? trimmed.slice(0, -1) : trimmed;
  return withoutOptionalTrailingPipe.split("|").map((cell) => cell.trim());
}

function parseTable(
  lines: string[],
  startIndex: number
): { block: TableBlock; nextIndex: number } | null {
  if (!isPipeRow(lines[startIndex]) || !isTableSeparator(lines[startIndex + 1] ?? "")) {
    return null;
  }

  const headers = parsePipeRow(lines[startIndex]);
  const rows: string[][] = [];
  let index = startIndex + 2;

  while (index < lines.length && isPipeRow(lines[index])) {
    rows.push(parsePipeRow(lines[index]));
    index += 1;
  }

  return { block: { headers, rows }, nextIndex: index };
}

function isShortSectionHeading(line: string) {
  if (line.length > 140) return false;
  if (/^part\s+\d+\s*:/i.test(line)) return true;
  if (/^#{1,3}\s+/.test(line)) return false;
  return /^[A-Z][^.!?]{2,100}:$/.test(line);
}

function isSingleNumberedSection(lines: string[], index: number) {
  const line = lines[index].trim();
  if (!/^\d+\.\s+[A-Z].{5,120}$/.test(line)) return false;

  const prev = lines[index - 1]?.trim() ?? "";
  const next = lines[index + 1]?.trim() ?? "";
  const prevIsNumbered = /^\d+\.\s+/.test(prev);
  const nextIsNumbered = /^\d+\.\s+/.test(next);

  return !prevIsNumbered && !nextIsNumbered;
}

function renderParagraph(text: string, key: string) {
  const colonLead = /^([^:]{3,80}):\s+(.+)$/.exec(text);
  if (colonLead && /^[A-Z]/.test(colonLead[1])) {
    return (
      <p key={key} className="text-xs leading-relaxed">
        <strong className="font-semibold text-foreground">{colonLead[1]}:</strong>{" "}
        {renderInline(colonLead[2], `${key}-body`)}
      </p>
    );
  }

  const transitionLead =
    /^(To address (?:the )?(?:first|second) question|In this case|Considering the evidence(?: presented)?(?: in this case)?|In conclusion|Therefore|Moreover),?\s+(.+)$/i.exec(
      text
    );
  if (transitionLead) {
    return (
      <p key={key} className="text-xs leading-relaxed">
        <strong className="font-semibold text-foreground">{transitionLead[1]}</strong>{" "}
        {renderInline(transitionLead[2], `${key}-body`)}
      </p>
    );
  }

  return (
    <p key={key} className="text-xs leading-relaxed">
      {renderInline(text, key)}
    </p>
  );
}

export function CentroidResponseRenderer({ text }: CentroidResponseRendererProps) {
  const lines = text.replace(/\r\n/g, "\n").split("\n");
  const blocks: ReactNode[] = [];
  let index = 0;

  while (index < lines.length) {
    const rawLine = lines[index];
    const line = rawLine.trim();

    if (!line) {
      index += 1;
      continue;
    }

    const table = parseTable(lines, index);
    if (table) {
      blocks.push(
        <div key={`table-${index}`} className="overflow-x-auto rounded-md border border-border">
          <table className="w-full text-[10px]">
            <thead>
              <tr className="border-b border-border bg-background/70">
                {table.block.headers.map((header, headerIndex) => (
                  <th
                    key={headerIndex}
                    className="px-3 py-2 text-left font-semibold text-foreground"
                  >
                    {renderInline(header, `table-${index}-h-${headerIndex}`)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {table.block.rows.map((row, rowIndex) => (
                <tr key={rowIndex} className="border-b border-border last:border-0">
                  {table.block.headers.map((_, cellIndex) => (
                    <td key={cellIndex} className="px-3 py-2 align-top text-muted-foreground">
                      {renderInline(
                        row[cellIndex] ?? "",
                        `table-${index}-${rowIndex}-${cellIndex}`
                      )}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
      index = table.nextIndex;
      continue;
    }

    const heading = /^(#{1,3})\s+(.+)$/.exec(line);
    if (heading) {
      blocks.push(
        <h3 key={`heading-${index}`} className="text-xs font-semibold text-foreground">
          {renderInline(heading[2], `heading-${index}`)}
        </h3>
      );
      index += 1;
      continue;
    }

    if (isShortSectionHeading(line) || isSingleNumberedSection(lines, index)) {
      blocks.push(
        <h3 key={`inferred-heading-${index}`} className="text-xs font-semibold text-foreground">
          {renderInline(line, `inferred-heading-${index}`)}
        </h3>
      );
      index += 1;
      continue;
    }

    if (line === "---") {
      blocks.push(<hr key={`hr-${index}`} className="border-border" />);
      index += 1;
      continue;
    }

    const listMatch = /^([-*]|\d+\.)\s+(.+)$/.exec(line);
    if (listMatch) {
      const ordered = /^\d+\.$/.test(listMatch[1]);
      const items: string[] = [];

      while (index < lines.length) {
        const itemMatch = /^([-*]|\d+\.)\s+(.+)$/.exec(lines[index].trim());
        if (!itemMatch || /^\d+\.$/.test(itemMatch[1]) !== ordered) break;
        items.push(itemMatch[2]);
        index += 1;
      }

      const ListTag = ordered ? "ol" : "ul";
      blocks.push(
        <ListTag
          key={`list-${index}`}
          className={`${ordered ? "list-decimal" : "list-disc"} ml-4 space-y-1 text-xs leading-relaxed`}
        >
          {items.map((item, itemIndex) => (
            <li key={itemIndex}>{renderInline(item, `list-${index}-${itemIndex}`)}</li>
          ))}
        </ListTag>
      );
      continue;
    }

    const paragraphLines: string[] = [];
    while (index < lines.length) {
      const nextLine = lines[index].trim();
      if (
        !nextLine ||
        /^(#{1,3})\s+/.test(nextLine) ||
        isShortSectionHeading(nextLine) ||
        isSingleNumberedSection(lines, index) ||
        nextLine === "---" ||
        /^([-*]|\d+\.)\s+/.test(nextLine) ||
        parseTable(lines, index)
      ) {
        break;
      }
      paragraphLines.push(nextLine);
      index += 1;
    }

    blocks.push(renderParagraph(paragraphLines.join(" "), `paragraph-${index}`));
  }

  return <div className="space-y-3 text-xs leading-relaxed text-foreground">{blocks}</div>;
}
