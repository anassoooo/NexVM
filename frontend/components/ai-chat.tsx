"use client";

import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { AICommandResponse } from "@/types";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  action?: string;
  error?: boolean;
}

const MAX_PROMPT_LENGTH = 500;

export default function AIChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages, loading]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || loading) return;

    const userMsg: Message = {
      id: `${Date.now()}-user`,
      role: "user",
      content: trimmed,
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const res = await api.post<AICommandResponse>("/api/v1/ai/command", {
        prompt: trimmed,
      });
      setMessages((prev) => [
        ...prev,
        {
          id: `${Date.now()}-assistant`,
          role: "assistant",
          content: res.result,
          action: res.action,
        },
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
    <div className="border rounded-lg flex flex-col h-[600px] bg-white">
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.length === 0 && (
          <div className="text-center text-gray-400 text-sm mt-10">
            Try: &quot;create an Ubuntu VM with 2GB RAM&quot;, &quot;start my Ubuntu VM&quot;,
            &quot;stop my VM&quot;, or &quot;delete my VM&quot;.
          </div>
        )}

        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[75%] rounded-lg px-3 py-2 text-sm ${
                msg.role === "user"
                  ? "bg-blue-600 text-white"
                  : msg.error
                    ? "bg-red-50 text-red-700 border border-red-200"
                    : "bg-gray-100 text-gray-900"
              }`}
            >
              {msg.action && (
                <div className="text-xs font-medium mb-1 opacity-70">
                  {msg.action}
                </div>
              )}
              <div className="whitespace-pre-wrap break-words">{msg.content}</div>
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex justify-start">
            <div className="bg-gray-100 text-gray-500 rounded-lg px-3 py-2 text-sm">
              Thinking...
            </div>
          </div>
        )}
      </div>

      <form onSubmit={handleSubmit} className="border-t p-3 flex gap-2 items-end">
        <div className="flex-1">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            maxLength={MAX_PROMPT_LENGTH}
            disabled={loading}
            placeholder="Describe what you want to do..."
            className="w-full border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-50"
          />
          <div className="text-xs text-gray-400 mt-1">
            {input.length}/{MAX_PROMPT_LENGTH}
          </div>
        </div>
        <button
          type="submit"
          disabled={loading || !input.trim()}
          className="px-4 py-2 bg-blue-600 text-white rounded text-sm font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Send
        </button>
      </form>
    </div>
  );
}
