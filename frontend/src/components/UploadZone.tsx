import { ChangeEvent, DragEvent, useRef, useState } from "react";
import { CloudUpload, Loader2 } from "lucide-react";

interface Props {
  onFile: (file: File) => Promise<void> | void;
  isUploading: boolean;
  progress: number;
  error: string | null;
}

const ACCEPT =
  ".pdf,.txt,.md,.docx,.xlsx,.xls,.png,.jpg,.jpeg,.webp,.gif";

export function UploadZone({ onFile, isUploading, progress, error }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [hover, setHover] = useState(false);

  const handle = async (file: File | undefined | null) => {
    if (!file) return;
    await onFile(file);
  };

  const onChange = (e: ChangeEvent<HTMLInputElement>) =>
    handle(e.target.files?.[0]);

  const onDrop = (e: DragEvent<HTMLLabelElement>) => {
    e.preventDefault();
    setHover(false);
    handle(e.dataTransfer.files?.[0]);
  };

  return (
    <div className="space-y-2">
      <label
        htmlFor="file-upload-input"
        onDragOver={(e) => {
          e.preventDefault();
          setHover(true);
        }}
        onDragLeave={() => setHover(false)}
        onDrop={onDrop}
        className={`flex flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed px-4 py-8 text-center transition cursor-pointer ${
          hover
            ? "border-violet-400 bg-violet-500/5"
            : "border-zinc-800 hover:border-zinc-700 bg-ink-900/40"
        } ${isUploading ? "opacity-70 cursor-progress" : ""}`}
      >
        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-violet-500/15 text-violet-300">
          {isUploading ? (
            <Loader2 size={18} className="animate-spin" />
          ) : (
            <CloudUpload size={18} />
          )}
        </div>
        <div className="text-sm font-medium text-zinc-100">
          {isUploading ? "Indexing…" : "Drop file or click to upload"}
        </div>
        <div className="text-xs text-zinc-500">
          PDF · DOCX · Excel · Images · TXT · MD · 25 MB max
        </div>
        <input
          id="file-upload-input"
          ref={inputRef}
          type="file"
          accept={ACCEPT}
          className="hidden"
          onChange={onChange}
          disabled={isUploading}
        />
      </label>

      {isUploading && (
        <div className="h-1.5 w-full overflow-hidden rounded-full bg-ink-700">
          <div
            className="h-full bg-violet-500 transition-[width] duration-150"
            style={{ width: `${Math.max(progress, 6)}%` }}
          />
        </div>
      )}

      {error && (
        <div className="rounded-md border border-red-500/30 bg-red-500/10 px-3 py-2 text-xs text-red-300">
          {error}
        </div>
      )}
    </div>
  );
}
