import { Check, FileText } from "lucide-react";
import type { UploadedDoc } from "../types";

interface Props {
  docs: UploadedDoc[];
  currentNamespace: string | null;
  onSelect: (ns: string) => void;
}

function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / 1024 / 1024).toFixed(1)} MB`;
}

export function DocumentList({ docs, currentNamespace, onSelect }: Props) {
  if (docs.length === 0) {
    return (
      <div className="text-xs text-zinc-500 italic px-1">
        No documents yet.
      </div>
    );
  }

  return (
    <ul className="space-y-1.5">
      {docs.map((d) => {
        const active = d.namespace === currentNamespace;
        return (
          <li key={d.namespace}>
            <button
              type="button"
              onClick={() => onSelect(d.namespace)}
              className={`group w-full text-left rounded-lg border px-3 py-2 text-xs transition ${
                active
                  ? "border-violet-400/40 bg-violet-500/10"
                  : "border-zinc-800 bg-ink-800/40 hover:border-zinc-700"
              }`}
            >
              <div className="flex items-start gap-2">
                <FileText
                  size={14}
                  className={`mt-0.5 shrink-0 ${
                    active ? "text-violet-300" : "text-zinc-400"
                  }`}
                />
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-1.5">
                    <span className="truncate font-medium text-zinc-100">
                      {d.filename}
                    </span>
                    {active && (
                      <Check size={12} className="text-violet-300 shrink-0" />
                    )}
                  </div>
                  <div className="mt-0.5 flex items-center gap-2 text-zinc-500">
                    <span>{d.chunks_indexed} chunks</span>
                    <span>·</span>
                    <span>{formatBytes(d.bytes_processed)}</span>
                  </div>
                  <div className="mt-0.5 truncate font-mono text-[10px] text-zinc-600">
                    {d.namespace}
                  </div>
                </div>
              </div>
            </button>
          </li>
        );
      })}
    </ul>
  );
}
