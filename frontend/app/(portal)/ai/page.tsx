import AIChat from "@/components/ai-chat";

export default function AIPage() {
  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 flex flex-col max-w-3xl mx-auto w-full px-6 py-6">
        <AIChat />
      </div>
    </div>
  );
}
