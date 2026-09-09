"use client";

import { useRef, useState } from "react";
import { api, ChatMessage, ChatSource } from "@/lib/api";

interface Turn extends ChatMessage {
  sources?: ChatSource[];
}

export default function ChatPage() {
  const [input, setInput] = useState("");
  const [turns, setTurns] = useState<Turn[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  function scrollToEnd() {
    requestAnimationFrame(() => {
      scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight });
    });
  }

  async function send(e: React.FormEvent) {
    e.preventDefault();
    const question = input.trim();
    if (!question || busy) return;

    setError(null);
    setInput("");
    const history: ChatMessage[] = [
      ...turns.map((t) => ({ role: t.role, content: t.content })),
      { role: "user", content: question },
    ];
    // Add the user turn plus an empty assistant turn we stream into.
    setTurns((prev) => [
      ...prev,
      { role: "user", content: question },
      { role: "assistant", content: "", sources: [] },
    ]);
    setBusy(true);
    scrollToEnd();

    try {
      const res = await api.chatStream(history);
      if (!res.ok || !res.body) {
        throw new Error(`Chat failed: ${res.status}`);
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        const frames = buffer.split("\n\n");
        buffer = frames.pop() ?? "";
        for (const frame of frames) {
          const line = frame.split("\n").find((l) => l.startsWith("data:"));
          if (!line) continue;
          const payload = JSON.parse(line.slice(5).trim());

          if (payload.type === "sources") {
            setTurns((prev) => patchLastAssistant(prev, (t) => ({ ...t, sources: payload.items })));
          } else if (payload.type === "delta") {
            setTurns((prev) =>
              patchLastAssistant(prev, (t) => ({ ...t, content: t.content + payload.text }))
            );
            scrollToEnd();
          } else if (payload.type === "error") {
            setError(payload.message);
          }
        }
      }
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
      scrollToEnd();
    }
  }

  return (
    <div>
      <h1 className="govuk-heading-xl">Chat</h1>
      <p className="govuk-body">
        Ask questions about the indexed feeds, websites and APIs. Answers are
        grounded in retrieved sources and cite where they came from.
      </p>

      <div className="app-chat" ref={scrollRef}>
        {turns.length === 0 && (
          <p className="govuk-body govuk-!-margin-bottom-0 govuk-hint">
            e.g. &ldquo;What&rsquo;s the latest on Airbus defence contracts?&rdquo;
          </p>
        )}
        {turns.map((t, i) => (
          <div key={i} className={`app-chat__turn app-chat__turn--${t.role}`}>
            <span className="app-chat__role">
              {t.role === "user" ? "You" : "Assistant"}
            </span>
            <div className="app-chat__bubble">
              {t.content || (t.role === "assistant" && busy ? "…" : "")}
            </div>
            {t.role === "assistant" && t.sources && t.sources.length > 0 && (
              <div className="app-chat__sources">
                <span className="govuk-body-s govuk-!-margin-bottom-0">Sources:</span>
                <ul className="govuk-list govuk-!-margin-bottom-0">
                  {t.sources.map((s, j) => (
                    <li key={j}>
                      {s.url ? (
                        <a className="govuk-link" href={s.url} target="_blank" rel="noreferrer">
                          {s.title ?? s.source_id}
                        </a>
                      ) : (
                        <span className="govuk-body-s">{s.title ?? s.source_id}</span>
                      )}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        ))}
      </div>

      {error && (
        <div className="govuk-error-summary" role="alert" aria-labelledby="chat-error-title">
          <h2 className="govuk-error-summary__title" id="chat-error-title">
            There is a problem
          </h2>
          <p className="govuk-body govuk-!-margin-bottom-0">{error}</p>
        </div>
      )}

      <form onSubmit={send} className="app-chat__form">
        <div className="govuk-form-group govuk-!-margin-bottom-0">
          <label className="govuk-label" htmlFor="chat-input">
            Your message
          </label>
          <input
            id="chat-input"
            className="govuk-input"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask a question about the sources"
            autoComplete="off"
          />
        </div>
        <button type="submit" className="govuk-button" disabled={busy || !input.trim()}>
          {busy ? "Thinking…" : "Send"}
        </button>
      </form>
    </div>
  );
}

function patchLastAssistant(turns: Turn[], fn: (t: Turn) => Turn): Turn[] {
  const next = [...turns];
  for (let i = next.length - 1; i >= 0; i--) {
    if (next[i].role === "assistant") {
      next[i] = fn(next[i]);
      break;
    }
  }
  return next;
}
