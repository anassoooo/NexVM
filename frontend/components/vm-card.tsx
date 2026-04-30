"use client";

import { useState } from "react";
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
  onAttachISO: (isoPath: string) => void;
  onDetachISO: () => void;
  onEnableVRDE: (port: number) => void;
  onDisableVRDE: () => void;
  loading: boolean;
  showOwner?: boolean;
}

function formatDisk(mb: number): string {
  return mb >= 1024 ? `${Math.round(mb / 1024)} GB` : `${mb} MB`;
}

function formatRam(mb: number): string {
  return mb >= 1024 ? `${mb / 1024} GB` : `${mb} MB`;
}

function basename(path: string): string {
  return path.replace(/\\/g, "/").split("/").pop() ?? path;
}

export default function VMCard({
  vm, onStart, onStop, onDelete, onSync, onForceReset,
  onAttachISO, onDetachISO, onEnableVRDE, onDisableVRDE,
  loading, showOwner,
}: VMCardProps) {
  const [isoInputVisible, setIsoInputVisible] = useState(false);
  const [isoInputValue, setIsoInputValue] = useState("");
  const [vrdeInputVisible, setVrdeInputVisible] = useState(false);
  const [vrdePortValue, setVrdePortValue] = useState("");

  const transitional = vm.status === "starting" || vm.status === "stopping";
  const isStopped = vm.status === "stopped";
  const showForceReset = showOwner && onForceReset && (transitional || vm.status === "error");

  function handleAttachISO() {
    const path = isoInputValue.trim();
    if (!path) return;
    onAttachISO(path);
    setIsoInputVisible(false);
    setIsoInputValue("");
  }

  function handleEnableVRDE() {
    const port = parseInt(vrdePortValue, 10);
    if (!port || port < 1024 || port > 65535) return;
    onEnableVRDE(port);
    setVrdeInputVisible(false);
    setVrdePortValue("");
  }

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

      {/* ISO & VRDE badges */}
      {(vm.iso_path || vm.vrde_enabled) && (
        <div className="flex flex-wrap gap-2 mb-3">
          {vm.iso_path && (
            <span className="text-xs px-2 py-0.5 rounded-full" style={{ background: "rgba(0,230,118,0.08)", color: "var(--accent)", border: "1px solid rgba(0,230,118,0.2)" }}>
              ISO: {basename(vm.iso_path)}
            </span>
          )}
          {vm.vrde_enabled && vm.vrde_port && (
            <span className="text-xs px-2 py-0.5 rounded-full" style={{ background: "rgba(100,180,255,0.08)", color: "#64b4ff", border: "1px solid rgba(100,180,255,0.2)" }}>
              RDP :{vm.vrde_port}
            </span>
          )}
        </div>
      )}

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

      {/* ISO attach inline input */}
      {isoInputVisible && (
        <div className="flex gap-2 mb-2">
          <input
            type="text"
            value={isoInputValue}
            onChange={(e) => setIsoInputValue(e.target.value)}
            placeholder="C:\ISOs\ubuntu.iso"
            className="flex-1 text-xs px-2 py-1 rounded"
            style={{ background: "rgba(255,255,255,0.06)", color: "var(--text)", border: "1px solid rgba(0,230,118,0.2)", outline: "none" }}
            onKeyDown={(e) => { if (e.key === "Enter") handleAttachISO(); if (e.key === "Escape") setIsoInputVisible(false); }}
            autoFocus
          />
          <button onClick={handleAttachISO} disabled={!isoInputValue.trim() || loading} className="text-xs font-semibold px-2 py-1 rounded" style={{ background: "rgba(0,230,118,0.15)", color: "var(--accent)" }}>
            OK
          </button>
          <button onClick={() => setIsoInputVisible(false)} className="text-xs px-2 py-1 rounded" style={{ color: "var(--text-muted)" }}>
            ✕
          </button>
        </div>
      )}

      {/* VRDE port inline input */}
      {vrdeInputVisible && (
        <div className="flex gap-2 mb-2">
          <input
            type="number"
            value={vrdePortValue}
            onChange={(e) => setVrdePortValue(e.target.value)}
            placeholder="3389"
            min={1024}
            max={65535}
            className="flex-1 text-xs px-2 py-1 rounded"
            style={{ background: "rgba(255,255,255,0.06)", color: "var(--text)", border: "1px solid rgba(100,180,255,0.2)", outline: "none" }}
            onKeyDown={(e) => { if (e.key === "Enter") handleEnableVRDE(); if (e.key === "Escape") setVrdeInputVisible(false); }}
            autoFocus
          />
          <button onClick={handleEnableVRDE} disabled={!vrdePortValue || loading} className="text-xs font-semibold px-2 py-1 rounded" style={{ background: "rgba(100,180,255,0.15)", color: "#64b4ff" }}>
            OK
          </button>
          <button onClick={() => setVrdeInputVisible(false)} className="text-xs px-2 py-1 rounded" style={{ color: "var(--text-muted)" }}>
            ✕
          </button>
        </div>
      )}

      {/* Primary actions */}
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

      {/* ISO & VRDE actions */}
      <div className="flex gap-2 flex-wrap mt-2">
        {!vm.iso_path && !isoInputVisible && (
          <button
            onClick={() => { setVrdeInputVisible(false); setIsoInputVisible(true); }}
            disabled={loading || !isStopped}
            className="text-xs font-semibold px-3 py-1 rounded-full transition-all"
            style={{ background: "rgba(0,230,118,0.07)", color: "var(--accent)", border: "1px solid rgba(0,230,118,0.15)" }}
            onMouseEnter={(e) => { if (!e.currentTarget.disabled) (e.currentTarget as HTMLButtonElement).style.background = "rgba(0,230,118,0.14)"; }}
            onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.background = "rgba(0,230,118,0.07)"; }}
          >
            Attach ISO
          </button>
        )}

        {vm.iso_path && (
          <button
            onClick={onDetachISO}
            disabled={loading || !isStopped}
            className="text-xs font-semibold px-3 py-1 rounded-full transition-all"
            style={{ background: "rgba(0,230,118,0.07)", color: "var(--text-muted)", border: "1px solid rgba(0,230,118,0.15)" }}
            onMouseEnter={(e) => { if (!e.currentTarget.disabled) (e.currentTarget as HTMLButtonElement).style.background = "rgba(0,230,118,0.14)"; }}
            onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.background = "rgba(0,230,118,0.07)"; }}
          >
            Detach ISO
          </button>
        )}

        {!vm.vrde_enabled && !vrdeInputVisible && (
          <button
            onClick={() => { setIsoInputVisible(false); setVrdeInputVisible(true); }}
            disabled={loading || !isStopped}
            className="text-xs font-semibold px-3 py-1 rounded-full transition-all"
            style={{ background: "rgba(100,180,255,0.07)", color: "#64b4ff", border: "1px solid rgba(100,180,255,0.15)" }}
            onMouseEnter={(e) => { if (!e.currentTarget.disabled) (e.currentTarget as HTMLButtonElement).style.background = "rgba(100,180,255,0.14)"; }}
            onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.background = "rgba(100,180,255,0.07)"; }}
          >
            Enable RDP
          </button>
        )}

        {vm.vrde_enabled && (
          <button
            onClick={onDisableVRDE}
            disabled={loading || !isStopped}
            className="text-xs font-semibold px-3 py-1 rounded-full transition-all"
            style={{ background: "rgba(100,180,255,0.07)", color: "rgba(100,180,255,0.6)", border: "1px solid rgba(100,180,255,0.15)" }}
            onMouseEnter={(e) => { if (!e.currentTarget.disabled) (e.currentTarget as HTMLButtonElement).style.background = "rgba(100,180,255,0.14)"; }}
            onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.background = "rgba(100,180,255,0.07)"; }}
          >
            Disable RDP
          </button>
        )}
      </div>
    </div>
  );
}
