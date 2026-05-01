import Image from "next/image";
import Link from "next/link";
import BackgroundLayer from "@/components/background-layer";

export default function LandingPage() {
  return (
    <div className="relative" style={{ background: "var(--bg)" }}>
      <BackgroundLayer />

      {/* Hero */}
      <section className="relative z-10 flex flex-col items-center justify-center text-center px-6" style={{ minHeight: "calc(100vh - 56px)" }}>
        <div
          className="mb-6"
          style={{ width: 88, height: 88, borderRadius: "22px", overflow: "hidden", border: "1px solid rgba(0,230,118,0.2)" }}
        >
          <Image src="/logo.png" alt="NexVM" width={88} height={88} style={{ objectFit: "cover", width: "100%", height: "100%" }} priority />
        </div>

        <h1 className="text-5xl md:text-6xl font-bold mb-4 text-balance" style={{ color: "var(--text)" }}>
          Manage Your VMs<br />
          <span style={{ color: "var(--accent)" }}>From Your Browser</span>
        </h1>

        <p className="text-lg md:text-xl max-w-2xl mb-10" style={{ color: "var(--text-muted)" }}>
          Create, control, and monitor VirtualBox virtual machines through a modern
          web interface — powered by AI.
        </p>

        <div className="flex gap-4">
          <Link
            href="/signup"
            className="btn-primary"
            style={{ padding: "14px 36px", fontSize: "1rem" }}
          >
            Get Started
          </Link>
          <a
            href="#features"
            className="btn-primary"
            style={{
              padding: "14px 36px",
              fontSize: "1rem",
              background: "transparent",
              border: "1px solid var(--border)",
              color: "var(--text)",
            }}
          >
            Learn More
          </a>
        </div>

        <div className="mt-16 animate-bounce" style={{ color: "var(--text-muted)", opacity: 0.4 }}>
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M12 5v14M19 12l-7 7-7-7" />
          </svg>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="relative z-10 max-w-6xl mx-auto px-6 py-24">
        <h2 className="text-3xl font-bold text-center mb-4" style={{ color: "var(--text)" }}>
          Everything You Need
        </h2>
        <p className="text-center mb-16 max-w-xl mx-auto" style={{ color: "var(--text-muted)" }}>
          A complete VM management platform with modern tooling and an intuitive interface.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <FeatureCard
            icon={
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><rect x="2" y="3" width="20" height="14" rx="2" /><line x1="8" y1="21" x2="16" y2="21" /><line x1="12" y1="17" x2="12" y2="21" /></svg>
            }
            title="Full VM Lifecycle"
            description="Create, start, stop, pause, snapshot, clone, export and delete VMs — all from your browser."
          />
          <FeatureCard
            icon={
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M12 2a10 10 0 1 0 10 10A10 10 0 0 0 12 2z" /><path d="M12 6v6l4 2" /></svg>
            }
            title="Scheduling"
            description="Automate start/stop with cron-like scheduling. Set it once, let the platform handle the rest."
          />
          <FeatureCard
            icon={
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" /></svg>
            }
            title="AI Assistant"
            description="Manage VMs using natural language. Just type &quot;create an Ubuntu VM with 4GB RAM&quot; and it happens."
          />
          <FeatureCard
            icon={
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><circle cx="12" cy="12" r="10" /><path d="M12 6v6l4 2" /></svg>
            }
            title="Real-Time Metrics"
            description="Monitor CPU load and RAM allocation for running VMs in real time."
          />
          <FeatureCard
            icon={
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" /></svg>
            }
            title="Secure & Isolated"
            description="Row-Level Security in Supabase ensures each user only accesses their own VMs and data."
          />
          <FeatureCard
            icon={
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M18 20V10" /><path d="M12 20V4" /><path d="M6 20v-6" /></svg>
            }
            title="Analytics Dashboard"
            description="Track VM usage, AI command history, and disk consumption with time-series charts."
          />
        </div>
      </section>

      {/* How It Works */}
      <section className="relative z-10 max-w-5xl mx-auto px-6 py-24">
        <h2 className="text-3xl font-bold text-center mb-4" style={{ color: "var(--text)" }}>
          How It Works
        </h2>
        <p className="text-center mb-16 max-w-xl mx-auto" style={{ color: "var(--text-muted)" }}>
          Get from zero to a running VM in under a minute.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          <StepCard step={1} title="Sign Up" description="Create your account in seconds. No credit card needed — just an email and password." />
          <StepCard step={2} title="Create a VM" description="Choose an OS, set RAM and CPU, and click Create. Or just ask the AI assistant to do it for you." />
          <StepCard step={3} title="Manage & Monitor" description="Start, stop, attach ISOs, enable RDP, take snapshots, schedule tasks — all from the dashboard." />
        </div>
      </section>

      {/* Platform */}
      <section className="relative z-10 max-w-5xl mx-auto px-6 py-24">
        <h2 className="text-3xl font-bold text-center mb-4" style={{ color: "var(--text)" }}>
          Built On
        </h2>
        <p className="text-center mb-16 max-w-xl mx-auto" style={{ color: "var(--text-muted)" }}>
          Powered by proven, open-source technologies.
        </p>

        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
          <TechBadge name="VirtualBox" sub="Hypervisor" />
          <TechBadge name="FastAPI" sub="Backend" />
          <TechBadge name="Next.js" sub="Frontend" />
          <TechBadge name="Supabase" sub="Auth & DB" />
          <TechBadge name="Groq" sub="AI Engine" />
          <TechBadge name="Python" sub="Language" />
        </div>
      </section>

      {/* What Can You Do */}
      <section className="relative z-10 max-w-5xl mx-auto px-6 py-24">
        <h2 className="text-3xl font-bold text-center mb-4" style={{ color: "var(--text)" }}>
          What Can You Do?
        </h2>
        <p className="text-center mb-12 max-w-xl mx-auto" style={{ color: "var(--text-muted)" }}>
          NexVM gives you full control over your VirtualBox infrastructure.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Capability text="Create VMs with custom OS, RAM, CPU, and disk size" />
          <Capability text="Start, stop, pause, resume, and save VM state" />
          <Capability text="Attach ISO images to install any operating system" />
          <Capability text="Enable RDP (VRDE) for remote desktop access" />
          <Capability text="Take, restore, and delete VM snapshots" />
          <Capability text="Clone existing VMs or export/import as OVA" />
          <Capability text="Add NAT port forwarding rules (SSH, HTTP, etc.)" />
          <Capability text="Schedule automatic start/stop with cron expressions" />
          <Capability text="Monitor CPU load and RAM in real time" />
          <Capability text="Manage everything via AI natural language commands" />
          <Capability text="Track activity with detailed logs and analytics" />
          <Capability text="Admin panel for managing all users and VMs" />
        </div>
      </section>

      {/* CTA */}
      <section className="relative z-10 py-24">
        <div className="max-w-2xl mx-auto text-center px-6">
          <h2 className="text-3xl font-bold mb-4" style={{ color: "var(--text)" }}>
            Ready to Get Started?
          </h2>
          <p className="mb-8" style={{ color: "var(--text-muted)" }}>
            Create your free account and launch your first VM in minutes.
          </p>
          <Link
            href="/signup"
            className="btn-primary inline-block"
            style={{ padding: "14px 48px", fontSize: "1rem" }}
          >
            Create Account
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer
        className="relative z-10 py-8 text-center"
        style={{ borderTop: "1px solid var(--border)" }}
      >
        <p className="text-sm" style={{ color: "var(--text-muted)" }}>
          NexVM — Virtual Machine Management Platform
        </p>
      </footer>
    </div>
  );
}

function FeatureCard({ icon, title, description }: { icon: React.ReactNode; title: string; description: string }) {
  return (
    <div className="glass" style={{ padding: "1.5rem" }}>
      <div className="mb-3" style={{ color: "var(--accent)" }}>{icon}</div>
      <h3 className="text-base font-semibold mb-2" style={{ color: "var(--text)" }}>{title}</h3>
      <p className="text-sm leading-relaxed" style={{ color: "var(--text-muted)" }}>{description}</p>
    </div>
  );
}

function StepCard({ step, title, description }: { step: number; title: string; description: string }) {
  return (
    <div className="text-center">
      <div
        className="mx-auto mb-4 font-bold text-2xl"
        style={{
          width: 48,
          height: 48,
          borderRadius: "50%",
          background: "rgba(0,230,118,0.1)",
          border: "1px solid rgba(0,230,118,0.25)",
          color: "var(--accent)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        {step}
      </div>
      <h3 className="text-lg font-semibold mb-2" style={{ color: "var(--text)" }}>{title}</h3>
      <p className="text-sm" style={{ color: "var(--text-muted)" }}>{description}</p>
    </div>
  );
}

function TechBadge({ name, sub }: { name: string; sub: string }) {
  return (
    <div className="glass text-center" style={{ padding: "1rem" }}>
      <p className="font-semibold text-sm" style={{ color: "var(--text)" }}>{name}</p>
      <p className="text-xs mt-0.5" style={{ color: "var(--text-muted)" }}>{sub}</p>
    </div>
  );
}

function Capability({ text }: { text: string }) {
  return (
    <div className="flex items-start gap-3" style={{ padding: "0.75rem 0" }}>
      <svg
        width="18"
        height="18"
        viewBox="0 0 24 24"
        fill="none"
        stroke="var(--accent)"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        style={{ flexShrink: 0, marginTop: 2 }}
      >
        <polyline points="20 6 9 17 4 12" />
      </svg>
      <span className="text-sm" style={{ color: "var(--text)" }}>{text}</span>
    </div>
  );
}
