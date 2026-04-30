"use client";

import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { AICommandResponse, UserAnalytics } from "@/types";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  action?: string;
  error?: boolean;
}

const MAX_PROMPT_LENGTH = 2000;

export default function AIChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    async function fetchGreeting() {
      try {
        const data = await api.get<UserAnalytics>("/api/v1/analytics");
        const greeting =
          `You have ${data.total_vms} VM${data.total_vms !== 1 ? "s" : ""} — ` +
          `${data.running_vms} running, ${data.stopped_vms} stopped` +
          (data.error_vms > 0 ? `, ${data.error_vms} error` : "") +
          `. What would you like to do?`;
        setMessages([{ id: "greeting", role: "assistant", content: greeting }]);
      } catch {
        setMessages([{ id: "greeting", role: "assistant", content: "Welcome! What would you like to do?" }]);
      }
    }
    fetchGreeting();
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, loading]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || loading) return;

    const userMsg: Message = { id: `${Date.now()}-user`, role: "user", content: trimmed };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const res = await api.post<AICommandResponse>("/api/v1/ai/command", { prompt: trimmed });
      setMessages((prev) => [
        ...prev,
        { id: `${Date.now()}-assistant`, role: "assistant", content: res.result, action: res.action },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          id: `${Date.now()}-error`,
          role: "assistant",
          content: err instanceof Error ? err.message : "Something went wrong",
          error: true,
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div
      className="flex flex-col"
      style={{
        height: "calc(100vh - 120px)",
        minHeight: 400,
      }}
    >
      {/* Messages */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto py-4 space-y-4"
        style={{ scrollbarColor: "var(--border) transparent" }}
      >
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
          >
            {msg.role === "user" ? (
              /* User bubble — green pill */
              <div
                className="max-w-[72%] text-sm font-bold"
                style={{
                  background: "var(--success)",
                  color: "var(--text)",
                  borderRadius: "9999px",
                  padding: "10px 18px",
                  lineHeight: 1.5,
                  wordBreak: "break-word",
                }}
              >
                {msg.content}
              </div>
            ) : (
              /* Bot bubble — glass card */
              <div
                className="max-w-[80%] glass text-sm"
                style={{
                  color: msg.error ? "var(--warning)" : "var(--text)",
                  padding: "14px 18px",
                  lineHeight: 1.7,
                  wordBreak: "break-word",
                  borderColor: msg.error ? "rgba(255,109,0,0.25)" : undefined,
                }}
              >
                {msg.action && msg.action !== "chat" && (
                  <div
                    className="text-xs font-semibold mb-2 uppercase tracking-wider"
                    style={{ color: "var(--accent)" }}
                  >
                    {msg.action.replace(/_/g, " ")}
                  </div>
                )}
                <div className="whitespace-pre-wrap">{msg.content}</div>
              </div>
            )}
          </div>
        ))}

        {loading && (
          <div className="flex justify-start">
            <div
              className="glass text-sm"
              style={{ color: "var(--text-muted)", padding: "14px 18px" }}
            >
              <span className="inline-flex gap-1">
                <span style={{ animation: "float 1s ease-in-out infinite" }}>·</span>
                <span style={{ animation: "float 1s ease-in-out infinite 0.2s" }}>·</span>
                <span style={{ animation: "float 1s ease-in-out infinite 0.4s" }}>·</span>
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Input bar */}
      <div
        className="pt-3"
        style={{ borderTop: "1px solid var(--border)" }}
      >
        <form onSubmit={handleSubmit} className="flex gap-3 items-end">
          <div className="flex-1">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              maxLength={MAX_PROMPT_LENGTH}
              disabled={loading}
              placeholder="Ask me anything about your VMs..."
              className="input-dark"
              style={{ borderRadius: "4px 4px 0 0" }}
            />
            <div className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>
              {input.length}/{MAX_PROMPT_LENGTH}
            </div>
          </div>
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="btn-primary"
            style={{ padding: "10px 20px", marginBottom: "1.25rem" }}
          >
            Send
          </button>
        </form>
      </div>
    </div>
  );
}
