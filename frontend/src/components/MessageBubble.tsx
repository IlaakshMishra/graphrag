import { useState } from "react";
import { Bot, ChevronDown, ChevronRight, FileText, User } from "lucide-react";
import type { ChatMessage } from "../types";

interface Props {
  message: ChatMessage;
}

function TypingDots() {
  return (
    <div className="flex items-center gap-1 py-1">
      <span className="h-1.5 w-1.5 rounded-full bg-violet-300 animate-bounce-dot [animation-delay:-0.32s]" />
      <span className="h-1.5 w-1.5 rounded-full bg-violet-300 animate-bounce-dot [animation-delay:-0.16s]" />
      <span className="h-1.5 w-1.5 rounded-full bg-violet-300 animate-bounce-dot" />
    </div>
  );
}

export function MessageBubble({ message }: Props) {
  const [openSources, setOpenSources] = useState(false);
  const isUser = message.role === "user";

  return (
    <div
      className={`flex w-full gap-3 animate-fade-in ${
        isUser ? "justify-end" : "justify-start"
      }`}
    >
      {!isUser && (
        <div className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-violet-500/15 text-violet-300">
          <Bot size={16} />
        </div>
      )}

      <div
        className={`max-w-[78%] rounded-2xl px-4 py-3 text-sm leading-relaxed shadow-sm ${
          isUser
            ? "bg-violet-500 text-white rounded-br-md"
            : "bg-ink-800/80 text-zinc-100 border border-zinc-800/80 rounded-bl-md"
        }`}
      >
        {message.pending ? (
          <TypingDots />
        ) : (
          <div className="whitespace-pre-wrap break-words">
            {message.content || (
              <span className="text-zinc-500 italic">empty response</span>
            )}
          </div>
        )}

        {!isUser && message.sources && message.sources.length > 0 && (
          <div className="mt-3 border-t border-zinc-800/80 pt-2">
            <button
              type="button"
              className="flex items-center gap-1 text-xs text-zinc-400 hover:text-zinc-200 transition"
              onClick={() => setOpenSources((v) => !v)}
            >
              {openSources ? (
                <ChevronDown size={14} />
              ) : (
                <ChevronRight size={14} />
              )}
              {message.sources.length} source
              {message.sources.length === 1 ? "" : "s"}
            </button>
            {openSources && (
              <ul className="mt-2 space-y-1.5">
                {message.sources.map((src, i) => (
                  <li
                    key={`${src.source}-${src.chunk_index ?? i}`}
                    className="flex items-start gap-2 rounded-md border border-zinc-800/70 bg-ink-900/60 px-2.5 py-1.5 text-xs text-zinc-300"
                  >
                    <FileText size={12} className="mt-0.5 shrink-0 text-violet-300" />
                    <div className="min-w-0">
                      <div className="font-medium text-zinc-200 truncate">
                        {src.source}
                        {src.page ? (
                          <span className="text-zinc-500"> · p.{src.page}</span>
                        ) : null}
                        {typeof src.score === "number" ? (
                          <span className="ml-2 text-violet-300/80">
                            {src.score.toFixed(3)}
                          </span>
                        ) : null}
                      </div>
                      {src.snippet ? (
                        <div className="mt-0.5 text-zinc-500 line-clamp-2">
                          {src.snippet}
                        </div>
                      ) : null}
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </div>

      {isUser && (
        <div className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-zinc-800 text-zinc-300">
          <User size={16} />
        </div>
      )}
    </div>
  );
}
