import { useEffect, useRef } from "react";
import { Sparkles } from "lucide-react";
import { MessageBubble } from "./MessageBubble";
import type { ChatMessage } from "../types";

interface Props {
  messages: ChatMessage[];
  namespace: string | null;
}

function EmptyState({ namespace }: { namespace: string | null }) {
  return (
    <div className="flex h-full w-full flex-col items-center justify-center gap-3 px-6 text-center">
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-violet-500/15 text-violet-300">
        <Sparkles size={20} />
      </div>
      <h2 className="text-lg font-semibold text-zinc-100">
        Conversational RAG
      </h2>
      <p className="max-w-md text-sm text-zinc-400">
        {namespace
          ? "Documents indexed. Ask anything — answers are grounded in your uploads with source citations."
          : "Upload a PDF, DOCX, TXT, or Markdown file on the left to get started. Each upload becomes its own isolated namespace."}
      </p>
    </div>
  );
}

export function ChatWindow({ messages, namespace }: Props) {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages]);

  if (messages.length === 0) {
    return <EmptyState namespace={namespace} />;
  }

  return (
    <div className="flex h-full flex-col gap-4 overflow-y-auto px-1 py-2">
      {messages.map((m) => (
        <MessageBubble key={m.id} message={m} />
      ))}
      <div ref={endRef} />
    </div>
  );
}
