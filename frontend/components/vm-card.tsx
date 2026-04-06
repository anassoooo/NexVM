"use client";

import { VM } from "@/types";

const STATUS_STYLES: Record<VM["status"], string> = {
  running: "bg-green-100 text-green-800",
  stopped: "bg-gray-100 text-gray-800",
  starting: "bg-amber-100 text-amber-800",
  stopping: "bg-amber-100 text-amber-800",
  error: "bg-red-100 text-red-800",
};

interface VMCardProps {
  vm: VM;
  onStart: () => void;
  onStop: () => void;
  onDelete: () => void;
  loading: boolean;
}

export default function VMCard({ vm, onStart, onStop, onDelete, loading }: VMCardProps) {
  const transitional = vm.status === "starting" || vm.status === "stopping";

  return (
    <div className="border rounded-lg p-4 shadow-sm">
      <div className="flex items-center justify-between mb-2">
        <span className="font-bold text-lg">{vm.name}</span>
        <span className={`text-xs font-medium px-2 py-1 rounded-full ${STATUS_STYLES[vm.status]}`}>
          {vm.status}
        </span>
      </div>

      <div className="text-sm text-gray-600 space-y-1">
        <p>OS: {vm.os}</p>
        <p>RAM: {vm.ram} MB</p>
      </div>

      {vm.status === "error" && vm.error_message && (
        <p className="text-sm text-red-600 mt-2">{vm.error_message}</p>
      )}

      <div className="flex gap-2 mt-4">
        <button
          onClick={onStart}
          disabled={loading || transitional || (vm.status !== "stopped" && vm.status !== "error")}
          className="px-3 py-1 text-sm bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Start
        </button>
        <button
          onClick={onStop}
          disabled={loading || transitional || vm.status !== "running"}
          className="px-3 py-1 text-sm bg-amber-600 text-white rounded hover:bg-amber-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Stop
        </button>
        <button
          onClick={onDelete}
          disabled={loading || transitional || vm.status !== "stopped"}
          className="px-3 py-1 text-sm bg-red-600 text-white rounded hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Delete
        </button>
      </div>
    </div>
  );
}
