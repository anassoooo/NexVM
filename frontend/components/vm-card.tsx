"use client";

import { VM } from "@/types";

const STATUS_COLOR: Record<VM["status"], string> = {
  running:  "var(--success)",
  stopped:  "var(--text-muted)",
  starting: "var(--accent)",
  stopping: "var(--warning)",
  error:    "var(--warning)",
};

interface VMCardProps {
  vm: VM;
  onStart: () => void;
  onStop: () => void;
  onDelete: () => void;
  onSync: () => void;
  onForceReset?: () => void;
  loading: boolean;
  showOwner?: boolean;
}

function formatDisk(mb: number): string {
  return mb >= 1024 ? `${Math.round(mb / 1024)} GB` : `${mb} MB`;
}

function formatRam(mb: number): string {
  return mb >= 1024 ? `${mb / 1024} GB` : `${mb} MB`;
}

export default function VMCard({
  vm, onStart, onStop, onDelete, onSync, onForceReset, loading, showOwner,
}: VMCardProps) {
  const transitional = vm.status === "starting" || vm.status === "stopping";
  const showForceReset = showOwner && onForceReset && (transitional || vm.status === "error");

  return (
    <div
      className="glass transition-shadow duration-300"
      style={{ padding: "1.25rem" }}
      onMouseEnter={(e) => { (e.currentTarget as HTMLDivElement).style.boxShadow = "0 0 40px rgba(0,230,118,0.15)"; }}
      onMouseLeave={(e) => { (e.currentTarget as HTMLDivElement).style.boxShadow = "none"; }}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <span className="font-bold text-base truncate mr-2" style={{ color: "var(--text)" }}>
          {vm.name}
        </span>
        <span className="text-xs font-semibold shrink-0" style={{ color: STATUS_COLOR[vm.status] }}>
          {vm.status}
        </span>
      </div>

      {/* OS */}
      <p className="text-sm mb-2" style={{ color: "var(--text)" }}>{vm.os}</p>

      {/* Hardware specs */}
      <div className="flex gap-3 text-xs mb-3" style={{ color: "var(--text-muted)" }}>
        <span>{vm.cpu} vCPU</span>
        <span>·</span>
        <span>{formatRam(vm.ram)} RAM</span>
        <span>·</span>
        <span>{formatDisk(vm.disk_size)} Disk</span>
      </div>

      {showOwner && (
        <p className="text-xs mb-2 truncate" style={{ color: "rgba(122,158,138,0.5)" }}>
          {vm.user_id}
        </p>
      )}

      {vm.status === "error" && vm.error_message && (
        <p className="text-xs mb-3 p-2 rounded" style={{ color: "var(--warning)", background: "rgba(255,109,0,0.08)" }}>
          {vm.error_message}
        </p>
      )}

      {/* Actions */}
      <div className="flex gap-2 flex-wrap mt-1">
        <button
          onClick={onStart}
          disabled={loading || transitional || (vm.status !== "stopped" && vm.status !== "error")}
          className="text-xs font-semibold px-3 py-1 rounded-full transition-all"
          style={{ background: "rgba(0,200,83,0.12)", color: "var(--success)", border: "1px solid rgba(0,200,83,0.25)" }}
          onMouseEnter={(e) => { if (!e.currentTarget.disabled) (e.currentTarget as HTMLButtonElement).style.background = "rgba(0,200,83,0.22)"; }}
          onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.background = "rgba(0,200,83,0.12)"; }}
        >
          Start
        </button>

        <button
          onClick={onStop}
          disabled={loading || transitional || vm.status !== "running"}
          className="text-xs font-semibold px-3 py-1 rounded-full transition-all"
          style={{ background: "rgba(255,109,0,0.12)", color: "var(--warning)", border: "1px solid rgba(255,109,0,0.25)" }}
          onMouseEnter={(e) => { if (!e.currentTarget.disabled) (e.currentTarget as HTMLButtonElement).style.background = "rgba(255,109,0,0.22)"; }}
          onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.background = "rgba(255,109,0,0.12)"; }}
        >
          Stop
        </button>

        <button
          onClick={onSync}
          disabled={loading}
          className="text-xs font-semibold px-3 py-1 rounded-full transition-all"
          style={{ background: "rgba(0,150,230,0.12)", color: "var(--accent)", border: "1px solid rgba(0,150,230,0.25)" }}
          onMouseEnter={(e) => { if (!e.currentTarget.disabled) (e.currentTarget as HTMLButtonElement).style.background = "rgba(0,150,230,0.22)"; }}
          onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.background = "rgba(0,150,230,0.12)"; }}
        >
          Sync
        </button>

        <button
          onClick={onDelete}
          disabled={loading || transitional || (vm.status !== "stopped" && vm.status !== "error")}
          className="text-xs font-semibold px-3 py-1 rounded-full transition-all"
          style={{ background: "rgba(255,109,0,0.08)", color: "rgba(255,109,0,0.7)", border: "1px solid rgba(255,109,0,0.15)" }}
          onMouseEnter={(e) => { if (!e.currentTarget.disabled) (e.currentTarget as HTMLButtonElement).style.background = "rgba(255,109,0,0.18)"; }}
          onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.background = "rgba(255,109,0,0.08)"; }}
        >
          Delete
        </button>

        {showForceReset && (
          <button
            onClick={onForceReset}
            disabled={loading}
            className="text-xs font-semibold px-3 py-1 rounded-full transition-all"
            style={{ background: "rgba(255,50,50,0.12)", color: "#ff4444", border: "1px solid rgba(255,50,50,0.3)" }}
            onMouseEnter={(e) => { if (!e.currentTarget.disabled) (e.currentTarget as HTMLButtonElement).style.background = "rgba(255,50,50,0.22)"; }}
            onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.background = "rgba(255,50,50,0.12)"; }}
          >
            Force Reset
          </button>
        )}
      </div>
    </div>
  );
}
