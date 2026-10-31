"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { AgentRun, UserAnalytics } from "@/types";
import Findings from "./findings";
import PlanCard from "./plan-card";
import { Button } from "@/components/ui";

type Message =
  | { id: string; kind: "user"; text: string }
  | { id: string; kind: "bot"; text: string; error?: boolean }
  | { id: string; kind: "run"; run: AgentRun };

const MAX_PROMPT_LENGTH = 2000;
const SUGGESTIONS = [
  "Set up a 3-node Kubernetes lab with 4 GB RAM each",
  "Why is my VM slow?",
  "Snapshot every stopped VM",
];

export default function AutopilotChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [input, setInput] = useState("");
  const [thinking, setThinking] = useState(false);
  const [busyRun, setBusyRun] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api.get<UserAnalytics>("/api/v1/analytics")
      .then((d) => setMessages([{ id: "greeting", kind: "bot", text:
        `You have ${d.total_vms} VM${d.total_vms !== 1 ? "s" : ""} — ${d.running_vms} running, ${d.stopped_vms} stopped` +
        (d.error_vms ? `, ${d.error_vms} with errors` : "") +
        ". Tell me what you need; I'll plan it and you approve before anything changes." }]))
      .catch(() => setMessages([{ id: "greeting", kind: "bot", text: "Tell me what you need; I'll plan it and you approve before anything changes." }]));
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, thinking]);

  const runningIds = messages.flatMap((m) => (m.kind === "run" && m.run.status === "running" ? [m.run.id] : []));
  const runningKey = runningIds.join(",");

  // Poll runs that are executing so step progress shows live.
  useEffect(() => {
    if (!runningKey) return;
    const timer = setInterval(async () => {
      for (const id of runningKey.split(",")) {
        try {
          replaceRun(await api.get<AgentRun>(`/api/v1/agent/runs/${id}`));
        } catch {
          /* keep polling; transient errors are fine */
        }
      }
    }, 1000);
    return () => clearInterval(timer);
  }, [runningKey]);

  function replaceRun(run: AgentRun) {
    setMessages((prev) => prev.map((m) => (m.kind === "run" && m.run.id === run.id ? { ...m, run } : m)));
  }

  async function send(text: string) {
    const prompt = text.trim();
    if (!prompt || thinking) return;
    setMessages((prev) => [...prev, { id: `${Date.now()}-u`, kind: "user", text: prompt }]);
    setInput("");
    setThinking(true);
    try {
      const run = await api.post<AgentRun>("/api/v1/agent/runs", { prompt, conversation_id: conversationId });
      setConversationId(run.conversation_id);
      // A new message supersedes an earlier plan that was still waiting.
      setMessages((prev) => [
        ...prev.map((m) => (m.kind === "run" && m.run.status === "needs_approval"
          ? { ...m, run: { ...m.run, status: "cancelled" as const, error: "Superseded by a newer message" } } : m)),
        { id: run.id, kind: "run", run },
      ]);
    } catch (err) {
      setMessages((prev) => [...prev, { id: `${Date.now()}-e`, kind: "bot", text: err instanceof Error ? err.message : "Something went wrong", error: true }]);
    } finally {
      setThinking(false);
    }
  }

  async function act(run: AgentRun, action: "approve" | "cancel") {
    setBusyRun(run.id);
    try {
      const body = action === "approve" ? { plan_version: run.plan_version } : {};
      replaceRun(await api.post<AgentRun>(`/api/v1/agent/runs/${run.id}/${action}`, body));
    } catch (err) {
      setMessages((prev) => [...prev, { id: `${Date.now()}-e`, kind: "bot", text: err instanceof Error ? err.message : "Request failed", error: true }]);
    } finally {
      setBusyRun(null);
    }
  }

  return (
    <div className="flex flex-col" style={{ height: "calc(100vh - 120px)", minHeight: 400 }}>
      <div className="flex items-center justify-between pb-3" style={{ borderBottom: "1px solid var(--border)" }}>
        <div>
          <h1 className="text-xl font-semibold tracking-tight" style={{ color: "var(--text)" }}>Autopilot</h1>
          <p className="text-sm" style={{ color: "var(--text-muted)" }}>Describe a change. You approve the plan before anything runs.</p>
        </div>
        <Link href="/ai/runs" className="text-sm nav-link">Run history</Link>
      </div>

      <div ref={scrollRef} className="flex-1 overflow-y-auto py-4 space-y-4" style={{ scrollbarColor: "var(--border) transparent" }}>
        {messages.map((m) =>
          m.kind === "user" ? (
            <div key={m.id} className="flex justify-end">
              <div className="max-w-[72%] text-sm font-medium" style={{ background: "var(--accent)", color: "var(--on-accent)", borderRadius: "12px 12px 4px 12px", padding: "10px 14px", wordBreak: "break-word" }}>
                {m.text}
              </div>
            </div>
          ) : (
            <div key={m.id} className="flex justify-start">
              <div className="max-w-[88%] w-full card text-sm" style={{ padding: "14px 16px", lineHeight: 1.65, color: m.kind === "bot" && m.error ? "var(--warning)" : "var(--text)" }}>
                {m.kind === "bot" ? (
                  <div className="whitespace-pre-wrap">{m.text}</div>
                ) : (
                  <>
                    <div className="whitespace-pre-wrap">{m.run.answer}</div>
                    <Findings findings={m.run.findings} />
                    <PlanCard run={m.run} busy={busyRun === m.run.id}
                      onApprove={() => act(m.run, "approve")} onCancel={() => act(m.run, "cancel")} />
                    <div className="mt-2 text-xs flex gap-3" style={{ color: "var(--text-muted)" }}>
                      <span>Planned in {(m.run.latency_ms / 1000).toFixed(1)} s with {m.run.total_tokens.toLocaleString()} tokens</span>
                      <Link href={`/ai/runs/${m.run.id}`} className="nav-link underline underline-offset-2">View trace</Link>
                    </div>
                  </>
                )}
              </div>
            </div>
          ),
        )}
        {thinking && (
          <div className="flex justify-start">
            <div className="card text-sm" style={{ color: "var(--text-muted)", padding: "14px 16px" }}>Planning…</div>
          </div>
        )}
        {messages.length <= 1 && !thinking && (
          <div className="flex flex-wrap gap-2">
            {SUGGESTIONS.map((s) => (
              <Button key={s} variant="secondary" size="sm" onClick={() => send(s)} style={{ fontWeight: 500 }}>
                {s}
              </Button>
            ))}
          </div>
        )}
      </div>

      <div className="pt-3" style={{ borderTop: "1px solid var(--border)" }}>
        <form onSubmit={(e) => { e.preventDefault(); send(input); }} className="flex gap-3 items-end">
          <div className="flex-1">
            <input type="text" value={input} onChange={(e) => setInput(e.target.value)} maxLength={MAX_PROMPT_LENGTH}
              disabled={thinking} placeholder="Ask Autopilot to set up, fix or explain your VMs…" className="field" />
            <div className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>{input.length}/{MAX_PROMPT_LENGTH}</div>
          </div>
          <Button type="submit" variant="primary" disabled={thinking || !input.trim()} style={{ marginBottom: "1.25rem", height: 40 }}>
            Send
          </Button>
        </form>
      </div>
    </div>
  );
}
