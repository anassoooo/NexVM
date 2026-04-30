import AIChat from "@/components/ai-chat";
import BackgroundLayer from "@/components/background-layer";

export default function AIPage() {
  return (
    <div
      className="relative flex flex-col"
      style={{ minHeight: "calc(100vh - 56px)", background: "var(--bg)" }}
    >
      <BackgroundLayer />
      <div className="relative z-10 flex-1 flex flex-col max-w-3xl mx-auto w-full px-4 py-6">
        <AIChat />
      </div>
    </div>
  );
}
