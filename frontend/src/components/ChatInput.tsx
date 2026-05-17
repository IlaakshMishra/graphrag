import { KeyboardEvent, useRef, useState } from "react";
import { Loader2, SendHorizonal } from "lucide-react";

interface Props {
  onSend: (text: string) => void | Promise<void>;
  disabled?: boolean;
  isLoading?: boolean;
  placeholder?: string;
}

export function ChatInput({
  onSend,
  disabled,
  isLoading,
  placeholder = "Ask a question about your documents…",
}: Props) {
  const [value, setValue] = useState("");
  const taRef = useRef<HTMLTextAreaElement>(null);

  const submit = async () => {
    const text = value.trim();
    if (!text || disabled || isLoading) return;
    setValue("");
    if (taRef.current) taRef.current.style.height = "auto";
    await onSend(text);
  };

  const handleKey = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  const autoResize = (el: HTMLTextAreaElement) => {
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 200) + "px";
  };

  return (
    <div className="card p-2 flex items-end gap-2">
      <textarea
        ref={taRef}
        value={value}
        onChange={(e) => {
          setValue(e.target.value);
          autoResize(e.currentTarget);
        }}
        onKeyDown={handleKey}
        placeholder={placeholder}
        rows={1}
        disabled={disabled}
        className="input resize-none border-none bg-transparent focus:ring-0 focus:border-transparent max-h-[200px] py-2.5"
      />
      <button
        type="button"
        onClick={submit}
        disabled={disabled || isLoading || !value.trim()}
        className="btn-primary h-10 w-10 shrink-0 p-0"
        aria-label="Send"
      >
        {isLoading ? (
          <Loader2 size={16} className="animate-spin" />
        ) : (
          <SendHorizonal size={16} />
        )}
      </button>
    </div>
  );
}
