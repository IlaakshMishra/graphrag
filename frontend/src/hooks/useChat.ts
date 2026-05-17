import { useCallback, useMemo, useRef, useState } from "react";
import { postChat } from "../api/client";
import type { ChatMessage } from "../types";

function uuid(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return Math.random().toString(36).slice(2) + Date.now().toString(36);
}

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const sessionIdRef = useRef<string>(uuid());

  const reset = useCallback(() => {
    setMessages([]);
    sessionIdRef.current = uuid();
  }, []);

  const sendMessage = useCallback(
    async (text: string, namespace: string | null) => {
      const trimmed = text.trim();
      if (!trimmed || isLoading) return;
      if (!namespace) {
        setMessages((m) => [
          ...m,
          {
            id: uuid(),
            role: "assistant",
            content: "Upload at least one document before asking questions.",
            error: "no_namespace",
          },
        ]);
        return;
      }

      const userMsg: ChatMessage = {
        id: uuid(),
        role: "user",
        content: trimmed,
      };
      const placeholderId = uuid();
      const placeholder: ChatMessage = {
        id: placeholderId,
        role: "assistant",
        content: "",
        pending: true,
      };

      setMessages((m) => [...m, userMsg, placeholder]);
      setIsLoading(true);

      const history = messages.map((m) => ({
        role: m.role,
        content: m.content,
      }));

      try {
        const res = await postChat({
          question: trimmed,
          namespace,
          session_id: sessionIdRef.current,
          chat_history: history,
        });
        setMessages((m) =>
          m.map((msg) =>
            msg.id === placeholderId
              ? {
                  ...msg,
                  pending: false,
                  content: res.answer,
                  sources: res.sources,
                }
              : msg
          )
        );
      } catch (err: unknown) {
        const detail =
          err instanceof Error ? err.message : "request failed";
        setMessages((m) =>
          m.map((msg) =>
            msg.id === placeholderId
              ? {
                  ...msg,
                  pending: false,
                  content: `Error: ${detail}`,
                  error: detail,
                }
              : msg
          )
        );
      } finally {
        setIsLoading(false);
      }
    },
    [isLoading, messages]
  );

  return useMemo(
    () => ({
      messages,
      isLoading,
      sessionId: sessionIdRef.current,
      sendMessage,
      reset,
    }),
    [messages, isLoading, sendMessage, reset]
  );
}
