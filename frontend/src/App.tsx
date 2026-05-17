import { Sparkles, Trash2 } from "lucide-react";
import { ChatInput } from "./components/ChatInput";
import { ChatWindow } from "./components/ChatWindow";
import { DocumentList } from "./components/DocumentList";
import { EvalPanel } from "./components/EvalPanel";
import { UploadZone } from "./components/UploadZone";
import { useChat } from "./hooks/useChat";
import { useUpload } from "./hooks/useUpload";

export default function App() {
  const upload = useUpload();
  const chat = useChat();

  return (
    <div className="flex h-screen w-screen flex-col bg-ink-950 text-zinc-100">
      {/* Top bar */}
      <header className="flex items-center justify-between border-b border-zinc-900 bg-ink-950/95 px-5 py-3 backdrop-blur">
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-violet-500/15 text-violet-300">
            <Sparkles size={16} />
          </div>
          <div>
            <div className="text-sm font-semibold">Conversational RAG</div>
            <div className="text-[11px] text-zinc-500">
              LangGraph · Pinecone · BGE · GPT-4o · RAGAS
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2 text-xs text-zinc-400">
          <span className="hidden md:inline font-mono">
            session: {chat.sessionId.slice(0, 8)}
          </span>
          <button
            type="button"
            onClick={chat.reset}
            className="btn-ghost"
            disabled={chat.messages.length === 0}
            title="Start a new chat session"
          >
            <Trash2 size={14} /> reset chat
          </button>
        </div>
      </header>

      {/* Main two-column layout */}
      <main className="flex flex-1 min-h-0 gap-4 px-4 py-4">
        {/* Sidebar */}
        <aside className="hidden w-80 shrink-0 flex-col gap-4 lg:flex">
          <section className="card p-4 space-y-3">
            <header className="flex items-center justify-between">
              <h2 className="text-sm font-semibold text-zinc-100">
                Documents
              </h2>
              {upload.currentNamespace && (
                <span className="rounded-full bg-emerald-500/10 px-2 py-0.5 text-[10px] uppercase tracking-wide text-emerald-300">
                  active
                </span>
              )}
            </header>
            <UploadZone
              onFile={async (f) => {
                try {
                  await upload.uploadFile(f);
                } catch {
                  /* surfaced via hook state */
                }
              }}
              isUploading={upload.isUploading}
              progress={upload.progress}
              error={upload.error}
            />
            <DocumentList
              docs={upload.uploadedDocs}
              currentNamespace={upload.currentNamespace}
              onSelect={upload.selectNamespace}
            />
          </section>
        </aside>

        {/* Chat column */}
        <section className="flex flex-1 min-w-0 flex-col gap-4">
          <div className="card flex flex-1 min-h-0 flex-col p-4">
            <ChatWindow
              messages={chat.messages}
              namespace={upload.currentNamespace}
            />
          </div>
          <ChatInput
            onSend={(t) => chat.sendMessage(t, upload.currentNamespace)}
            disabled={!upload.currentNamespace}
            isLoading={chat.isLoading}
            placeholder={
              upload.currentNamespace
                ? "Ask a question about your documents…"
                : "Upload a document first"
            }
          />
          <EvalPanel activeNamespace={upload.currentNamespace} />
        </section>
      </main>
    </div>
  );
}
