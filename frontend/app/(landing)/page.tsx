import Link from "next/link";
import PlanPreview from "@/components/landing/plan-preview";
import { Badge, buttonClass } from "@/components/ui";

const STAGES = [
  {
    name: "Plan",
    text: "The model picks from 18 typed tools. Calling a tool only queues a step; nothing touches the host.",
    sample: <code>create_vm(name=&quot;demo-web&quot;, ram=1024)</code>,
  },
  {
    name: "Simulate",
    text: "Each step is applied to a copy of your VMs. Invalid states, quotas, host ports and name clashes are rejected, and the model gets the reason.",
    sample: <code>&apos;demo-web&apos; will exist (stopped)</code>,
  },
  {
    name: "Approve",
    text: "You see every step, its effect and its cost. Destructive steps are marked and need their own approval.",
    sample: <Badge tone="warning">destructive</Badge>,
  },
  {
    name: "Execute",
    text: "Code, not the model, runs the approved plan and checks each step against the live host first.",
    sample: <code>created &apos;demo-web&apos; (1.7 s)</code>,
  },
  {
    name: "Trace",
    text: "Every model call, tool call and step is recorded with its timing and token count.",
    sample: <code>3 model calls, 2 tool calls</code>,
  },
];

const GUARANTEES = [
  ["The model can't run commands", "It can only propose steps from a fixed set of tools, and their arguments are validated."],
  ["Your login decides what a plan can touch", "Plans only see your own VMs. The model never chooses whose VMs it works on."],
  ["Nothing destructive without you", "Powering off, deleting a VM or restoring a snapshot is marked destructive and needs an explicit approval."],
  ["A failed step stops the plan", "The rest is skipped and Autopilot proposes a revised plan, which needs a new approval."],
];

const EVALS: [string, number, string][] = [
  ["Single step", 13, "Create, start, resize, snapshot and the other tools on their own"],
  ["Multi-step", 10, "Several steps in the right order, such as a three-node lab"],
  ["Safety", 10, "Prompt injection, requests outside its scope, destructive asks"],
  ["Follow-ups", 6, "References like “start it” that depend on the conversation"],
  ["Clarification", 6, "Ambiguous requests answered with a question instead of a guess"],
  ["Diagnostics", 6, "“Why is web slow?” answered from rule-based checks"],
  ["Other languages", 6, "The same requests in French, Spanish, German and Arabic"],
  ["Questions", 5, "Answers that must not change anything"],
  ["Repair", 3, "A revised plan after a step fails on the host"],
];

const CONSOLE = [
  ["Lifecycle", "Start, stop, pause, resume and save state"],
  ["Snapshots and clones", "Take, restore and delete snapshots; clone stopped VMs"],
  ["Media and access", "Attach ISOs and turn on remote desktop (RDP)"],
  ["Networking", "Port-forwarding rules from the host to the guest"],
  ["Schedules", "Start or stop VMs on a cron schedule"],
  ["Import and export", "Move VMs in and out as OVA files"],
  ["Analytics and logs", "VM counts over time, AI usage and a full activity log"],
];

function Section({ title, lede, children }: { title: string; lede?: string; children: React.ReactNode }) {
  return (
    <section className="py-16 sm:py-20" style={{ borderTop: "1px solid var(--border)" }}>
      <h2 className="text-2xl sm:text-3xl font-semibold tracking-tight" style={{ color: "var(--text)" }}>{title}</h2>
      {lede && <p className="mt-3 max-w-2xl text-base leading-relaxed" style={{ color: "var(--text-muted)" }}>{lede}</p>}
      <div className="mt-10">{children}</div>
    </section>
  );
}

export default function LandingPage() {
  return (
    <main className="max-w-6xl mx-auto px-5 sm:px-8">
      {/* Hero: the product itself, a real plan waiting for approval */}
      <section className="grid gap-12 lg:gap-16 items-center py-14 sm:py-20 lg:grid-cols-[minmax(0,6fr)_minmax(0,7fr)]">
        <div>
          <h1 className="text-4xl sm:text-5xl lg:text-[3.25rem] font-semibold tracking-tight text-balance" style={{ color: "var(--text)", lineHeight: 1.05 }}>
            Describe a VM change. Approve the plan before it runs.
          </h1>
          <p className="mt-6 text-lg leading-relaxed max-w-xl" style={{ color: "var(--text-muted)" }}>
            NexVM is a console for VirtualBox with Autopilot, an agent that turns a request into a plan, checks every
            step against a simulated copy of your VMs, and changes nothing until you approve.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link href="/signup" className={buttonClass({ variant: "primary" })} style={{ padding: "10px 18px" }}>Create an account</Link>
            <Link href="/login" className={buttonClass({ variant: "secondary" })} style={{ padding: "10px 18px" }}>Sign in</Link>
          </div>
          <p className="mt-6 text-sm" style={{ color: "var(--text-muted)" }}>
            Self-hosted. It drives the VirtualBox on the machine it runs on.
          </p>
        </div>
        <div>
          <PlanPreview />
          <p className="mt-3 text-xs" style={{ color: "var(--text-muted)" }}>
            A run recorded from the live app. Approve it to replay what happened on the host.
          </p>
        </div>
      </section>

      <Section title="What happens to a request" lede="Five stages, and the model only takes part in the first one.">
        <ol className="grid gap-8 sm:grid-cols-2 lg:grid-cols-5 lg:gap-6">
          {STAGES.map((s, i) => (
            <li key={s.name} className="pt-4" style={{ borderTop: `2px solid ${i === 2 ? "var(--accent)" : "var(--border-strong)"}` }}>
              <div className="flex items-baseline gap-2">
                <span className="mono text-sm tabular-nums" style={{ color: "var(--text-muted)" }}>{i + 1}</span>
                <h3 className="text-base font-semibold" style={{ color: "var(--text)" }}>{s.name}</h3>
              </div>
              <p className="mt-2 text-sm leading-relaxed" style={{ color: "var(--text-muted)" }}>{s.text}</p>
              <div className="mt-3 text-xs" style={{ color: "var(--text)" }}>{s.sample}</div>
            </li>
          ))}
        </ol>
      </Section>

      <Section title="What it won't do">
        <dl className="grid gap-x-12 sm:grid-cols-2">
          {GUARANTEES.map(([term, detail]) => (
            <div key={term} className="py-5" style={{ borderTop: "1px solid var(--border)" }}>
              <dt className="text-base font-semibold" style={{ color: "var(--text)" }}>{term}</dt>
              <dd className="mt-1.5 text-sm leading-relaxed" style={{ color: "var(--text-muted)" }}>{detail}</dd>
            </div>
          ))}
        </dl>
      </Section>

      <Section
        title="Tested on 65 scenarios"
        lede="Scoring is deterministic: each scenario checks the planned tools and arguments, not the wording. CI replays the recorded model responses on every push. On the 49 scenarios recorded so far, openai/gpt-oss-20b passed 48."
      >
        <div className="card overflow-x-auto">
          <table className="w-full text-sm" style={{ borderCollapse: "collapse" }}>
            <caption className="sr-only">Evaluation scenarios by category</caption>
            <thead>
              <tr style={{ color: "var(--text-muted)" }}>
                <th scope="col" className="text-left font-medium px-4 py-3">Category</th>
                <th scope="col" className="text-right font-medium px-4 py-3">Scenarios</th>
                <th scope="col" className="text-left font-medium px-4 py-3 hidden sm:table-cell">What it checks</th>
              </tr>
            </thead>
            <tbody>
              {EVALS.map(([name, count, what]) => (
                <tr key={name} style={{ borderTop: "1px solid var(--border)" }}>
                  <th scope="row" className="text-left font-medium px-4 py-3" style={{ color: "var(--text)" }}>{name}</th>
                  <td className="text-right px-4 py-3 tabular-nums mono" style={{ color: "var(--text)" }}>{count}</td>
                  <td className="px-4 py-3 hidden sm:table-cell" style={{ color: "var(--text-muted)" }}>{what}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Section>

      <Section title="And a full manual console" lede="Everything Autopilot can do is also a button, along with the things it doesn't do.">
        <dl className="grid gap-x-12 gap-y-6 sm:grid-cols-2 lg:grid-cols-3">
          {CONSOLE.map(([term, detail]) => (
            <div key={term}>
              <dt className="text-sm font-semibold" style={{ color: "var(--text)" }}>{term}</dt>
              <dd className="mt-1 text-sm" style={{ color: "var(--text-muted)" }}>{detail}</dd>
            </div>
          ))}
        </dl>
      </Section>

      <footer className="py-14 grid gap-6 sm:grid-cols-2 sm:items-end" style={{ borderTop: "1px solid var(--border)" }}>
        <div className="min-w-0">
          <h2 className="text-lg font-semibold" style={{ color: "var(--text)" }}>Run it yourself</h2>
          <p className="mt-2 text-sm max-w-md" style={{ color: "var(--text-muted)" }}>
            NexVM needs VirtualBox, a Supabase project and a Groq API key. The README covers the setup.
          </p>
          <pre className="mt-4 text-sm rounded-lg px-4 py-3 overflow-x-auto" style={{ background: "var(--surface-inset)", border: "1px solid var(--border)", color: "var(--text)" }}>
            <code>git clone https://github.com/anassoooo/NexVM</code>
          </pre>
        </div>
        <div className="sm:text-right">
          <a href="https://github.com/anassoooo/NexVM" className="text-sm nav-link underline underline-offset-4">Source and README on GitHub</a>
        </div>
      </footer>
    </main>
  );
}
