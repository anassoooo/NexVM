import BackgroundLayer from "@/components/background-layer";
import LogsClient from "@/components/logs-client";

export default function LogsPage() {
  return (
    <div
      className="relative"
      style={{ minHeight: "calc(100vh - 56px)", background: "var(--bg)" }}
    >
      <BackgroundLayer />
      <div className="relative z-10 max-w-5xl mx-auto px-4 py-8">
        <LogsClient />
      </div>
    </div>
  );
}
