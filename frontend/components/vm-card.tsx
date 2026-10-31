"use client";

import { useEffect, useState } from "react";
import { PortFwdRule, Snapshot, VM, VMMetrics, VMSchedule } from "@/types";
import { api } from "@/lib/api";
import { Modal } from "@/components/modal";

const STATUS_COLOR: Record<VM["status"], string> = {
  running:  "var(--success)",
  stopped:  "var(--text-muted)",
  starting: "var(--accent)",
  stopping: "var(--warning)",
  paused:   "var(--info)",
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
  onPause: () => void;
  onResume: () => void;
  onSaveState: () => void;
  onModify: (ram: number | null, cpu: number | null) => void;
  onAddPortRule: (name: string, proto: "tcp" | "udp", hp: number, gp: number) => void;
  onRemovePortRule: (name: string) => void;
  onTakeSnapshot: (name: string, desc: string) => void;
  onRestoreSnapshot: (name: string) => void;
  onDeleteSnapshot: (name: string) => void;
  onClone: (newName: string) => void;
  onExport: (outputPath: string) => void;
  onCreateSchedule: (action: "start" | "stop", cronExpr: string) => void;
  onDeleteSchedule: (scheduleId: string) => void;
  onToggleSchedule: (scheduleId: string) => void;
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
  onPause, onResume, onSaveState, onModify,
  onAddPortRule, onRemovePortRule,
  onTakeSnapshot, onRestoreSnapshot, onDeleteSnapshot,
  onClone, onExport,
  onCreateSchedule, onDeleteSchedule, onToggleSchedule,
  loading, showOwner,
}: VMCardProps) {
  const [isoInputVisible, setIsoInputVisible]   = useState(false);
  const [isoInputValue, setIsoInputValue]       = useState("");
  const [vrdeInputVisible, setVrdeInputVisible] = useState(false);
  const [vrdePortValue, setVrdePortValue]       = useState("");

  const [modifyVisible, setModifyVisible]   = useState(false);
  const [modifyRam, setModifyRam]           = useState("");
  const [modifyCpu, setModifyCpu]           = useState("");

  const [portFwdVisible, setPortFwdVisible] = useState(false);
  const [pfName, setPfName]                 = useState("");
  const [pfProto, setPfProto]               = useState<"tcp" | "udp">("tcp");
  const [pfHostPort, setPfHostPort]         = useState("");
  const [pfGuestPort, setPfGuestPort]       = useState("");

  const [snapVisible, setSnapVisible]       = useState(false);
  const [snapName, setSnapName]             = useState("");
  const [snapDesc, setSnapDesc]             = useState("");
  const [snapshots, setSnapshots]           = useState<Snapshot[] | null>(null);
  const [snapLoading, setSnapLoading]       = useState(false);

  const [cloneVisible, setCloneVisible]     = useState(false);
  const [cloneName, setCloneName]           = useState("");
  const [exportVisible, setExportVisible]   = useState(false);
  const [exportPath, setExportPath]         = useState("");

  const [metricsVisible, setMetricsVisible] = useState(false);
  const [metrics, setMetrics]               = useState<VMMetrics | null>(null);
  const [metricsLoading, setMetricsLoading] = useState(false);

  const [stopConfirm, setStopConfirm]       = useState(false);

  const [schedVisible, setSchedVisible]     = useState(false);
  const [schedAction, setSchedAction]       = useState<"start" | "stop">("start");
  const [schedCron, setSchedCron]           = useState("");
  const [schedules, setSchedules]           = useState<VMSchedule[] | null>(null);
  const [schedLoading, setSchedLoading]     = useState(false);

  const transitional = vm.status === "starting" || vm.status === "stopping";
  const isStopped    = vm.status === "stopped";
  const isRunning    = vm.status === "running";
  const isPaused     = vm.status === "paused";
  const showForceReset = showOwner && onForceReset && (transitional || vm.status === "error");

  useEffect(() => {
    if (!snapVisible) return;
    setSnapLoading(true);
    api.get<Snapshot[]>(`/api/v1/vm/snapshots?vm_id=${vm.id}`)
      .then(setSnapshots)
      .catch(() => setSnapshots([]))
      .finally(() => setSnapLoading(false));
  }, [snapVisible, vm.id]);

  useEffect(() => {
    if (!schedVisible) return;
    setSchedLoading(true);
    api.get<VMSchedule[]>(`/api/v1/schedules/${vm.id}`)
      .then(setSchedules)
      .catch(() => setSchedules([]))
      .finally(() => setSchedLoading(false));
  }, [schedVisible, vm.id]);

  function handleCreateSchedule() {
    if (!schedCron.trim()) return;
    onCreateSchedule(schedAction, schedCron.trim());
    setSchedCron("");
    setSchedules(null);
  }

  function handleAttachISO() {
    const p = isoInputValue.trim();
    if (!p) return;
    onAttachISO(p);
    setIsoInputVisible(false); setIsoInputValue("");
  }

  function handleEnableVRDE() {
    const port = parseInt(vrdePortValue, 10);
    if (!port || port < 1024 || port > 65535) return;
    onEnableVRDE(port);
    setVrdeInputVisible(false); setVrdePortValue("");
  }

  function handleModify() {
    const r = modifyRam ? parseInt(modifyRam, 10) : null;
    const c = modifyCpu ? parseInt(modifyCpu, 10) : null;
    if (!r && !c) return;
    onModify(r, c);
    setModifyVisible(false); setModifyRam(""); setModifyCpu("");
  }

  function handleAddPortRule() {
    const hp = parseInt(pfHostPort, 10);
    const gp = parseInt(pfGuestPort, 10);
    if (!pfName || !hp || !gp) return;
    onAddPortRule(pfName, pfProto, hp, gp);
    setPfName(""); setPfHostPort(""); setPfGuestPort("");
  }

  function handleTakeSnapshot() {
    if (!snapName.trim()) return;
    onTakeSnapshot(snapName.trim(), snapDesc.trim());
    setSnapName(""); setSnapDesc("");
    setSnapshots(null);
  }

  function fetchMetrics() {
    setMetricsLoading(true);
    api.get<VMMetrics>(`/api/v1/vm/metrics?vm_id=${vm.id}`)
      .then(setMetrics)
      .catch(() => setMetrics(null))
      .finally(() => setMetricsLoading(false));
  }

  function handleClone() {
    const n = cloneName.trim();
    if (!n) return;
    onClone(n);
    setCloneVisible(false); setCloneName("");
  }

  function handleExport() {
    const p = exportPath.trim();
    if (!p) return;
    onExport(p);
    setExportVisible(false); setExportPath("");
  }

  const inputStyle: React.CSSProperties = {
    background: "color-mix(in srgb, var(--ink) 6%, transparent)",
    color: "var(--text)",
    border: "1px solid color-mix(in srgb, var(--accent) 20%, transparent)",
    outline: "none",
    borderRadius: "4px",
    padding: "2px 6px",
    fontSize: "12px",
  };

  return (
    <div
      className="glass transition-shadow duration-300"
      style={{ padding: "1.25rem" }}
      onMouseEnter={(e) => { (e.currentTarget as HTMLDivElement).style.boxShadow = "var(--glow)"; }}
      onMouseLeave={(e) => { (e.currentTarget as HTMLDivElement).style.boxShadow = ""; }}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <span className="font-bold text-base truncate mr-2" style={{ color: "var(--text)" }}>{vm.name}</span>
        <span className="text-xs font-semibold shrink-0" style={{ color: STATUS_COLOR[vm.status] }}>{vm.status}</span>
      </div>

      <p className="text-sm mb-2" style={{ color: "var(--text)" }}>{vm.os}</p>

      <div className="flex gap-3 text-xs mb-3" style={{ color: "var(--text-muted)" }}>
        <span>{vm.cpu} vCPU</span><span>·</span>
        <span>{formatRam(vm.ram)} RAM</span><span>·</span>
        <span>{formatDisk(vm.disk_size)} Disk</span>
      </div>

      {/* Badges */}
      {(vm.iso_path || vm.vrde_enabled) && (
        <div className="flex flex-wrap gap-2 mb-3">
          {vm.iso_path && (
            <span className="text-xs px-2 py-0.5 rounded-full" style={{ background: "color-mix(in srgb, var(--accent) 8%, transparent)", color: "var(--accent)", border: "1px solid color-mix(in srgb, var(--accent) 20%, transparent)" }}>
              ISO: {basename(vm.iso_path)}
            </span>
          )}
          {vm.vrde_enabled && vm.vrde_port && (
            <span className="text-xs px-2 py-0.5 rounded-full" style={{ background: "color-mix(in srgb, var(--info) 8%, transparent)", color: "var(--info)", border: "1px solid color-mix(in srgb, var(--info) 20%, transparent)" }}>
              RDP :{vm.vrde_port}
            </span>
          )}
        </div>
      )}

      {showOwner && <p className="text-xs mb-2 truncate" style={{ color: "var(--text-muted)" }}>{vm.user_id}</p>}

      {vm.status === "error" && vm.error_message && (
        <p className="text-xs mb-3 p-2 rounded" style={{ color: "var(--warning)", background: "color-mix(in srgb, var(--warning) 8%, transparent)" }}>{vm.error_message}</p>
      )}

      {/* ISO inline input */}
      {isoInputVisible && (
        <div className="flex gap-2 mb-2">
          <input type="text" value={isoInputValue} onChange={(e) => setIsoInputValue(e.target.value)} placeholder="…\isos\ubuntu.iso (server ISO folder)" className="flex-1" style={inputStyle}
            onKeyDown={(e) => { if (e.key === "Enter") handleAttachISO(); if (e.key === "Escape") setIsoInputVisible(false); }} autoFocus />
          <Btn onClick={handleAttachISO} disabled={!isoInputValue.trim() || loading} color="green">OK</Btn>
          <Btn onClick={() => setIsoInputVisible(false)} color="muted">✕</Btn>
        </div>
      )}

      {/* VRDE inline input */}
      {vrdeInputVisible && (
        <div className="flex gap-2 mb-2">
          <input type="number" value={vrdePortValue} onChange={(e) => setVrdePortValue(e.target.value)} placeholder="3389" min={1024} max={65535} className="flex-1" style={{ ...inputStyle, border: "1px solid color-mix(in srgb, var(--info) 20%, transparent)" }}
            onKeyDown={(e) => { if (e.key === "Enter") handleEnableVRDE(); if (e.key === "Escape") setVrdeInputVisible(false); }} autoFocus />
          <Btn onClick={handleEnableVRDE} disabled={!vrdePortValue || loading} color="blue">OK</Btn>
          <Btn onClick={() => setVrdeInputVisible(false)} color="muted">✕</Btn>
        </div>
      )}

      {/* Modify inline form */}
      {modifyVisible && (
        <div className="flex gap-2 mb-2 flex-wrap">
          <input type="number" value={modifyRam} onChange={(e) => setModifyRam(e.target.value)} placeholder={`RAM (${vm.ram})`} min={512} max={16384} style={{ ...inputStyle, width: "90px" }} />
          <input type="number" value={modifyCpu} onChange={(e) => setModifyCpu(e.target.value)} placeholder={`CPU (${vm.cpu})`} min={1} max={32} style={{ ...inputStyle, width: "70px" }} />
          <Btn onClick={handleModify} disabled={(!modifyRam && !modifyCpu) || loading} color="green">Apply</Btn>
          <Btn onClick={() => { setModifyVisible(false); setModifyRam(""); setModifyCpu(""); }} color="muted">✕</Btn>
        </div>
      )}

      {/* ISO boot indicator — shown while VM is on and an ISO is attached */}
      {vm.iso_path && (isRunning || transitional) && (
        <div style={{
          background: "color-mix(in srgb, var(--caution) 6%, transparent)",
          border: "1px solid color-mix(in srgb, var(--caution) 22%, transparent)",
          borderRadius: "8px",
          padding: "0.55rem 0.8rem",
          marginBottom: "0.7rem",
          display: "flex",
          alignItems: "center",
          gap: "8px",
        }}>
          <span className="animate-pulse" style={{ color: "var(--caution)", fontSize: "13px", flexShrink: 0 }}>◉</span>
          <div>
            <p style={{ color: "var(--caution)", fontSize: "11px", fontWeight: 700, marginBottom: "1px" }}>
              Booting from ISO
            </p>
            <p style={{ color: "var(--text-muted)", fontSize: "10px", lineHeight: 1.4 }}>
              {vm.status === "starting"
                ? "Starting the virtual machine…"
                : "OS is loading — this can take several minutes. Watch VirtualBox for progress."}
            </p>
          </div>
        </div>
      )}

      {stopConfirm && (
        <Modal
          title="Stop VM — RDP Warning"
          message="An RDP session may still be open on this VM. Make sure you have closed your Remote Desktop window before stopping. This will forcibly power it off."
          confirmLabel="Yes, stop it"
          onConfirm={() => { setStopConfirm(false); onStop(); }}
          onCancel={() => setStopConfirm(false)}
          loading={loading}
        />
      )}

      {/* Primary action buttons */}
      <div className="flex gap-2 flex-wrap mt-1">
        <ActionBtn onClick={onStart} disabled={loading || transitional || (vm.status !== "stopped" && vm.status !== "error")} color="green">Start</ActionBtn>
        <ActionBtn onClick={() => {
          if (vm.vrde_enabled) { setStopConfirm(true); } else { onStop(); }
        }} disabled={loading || transitional || vm.status !== "running"} color="orange">Stop</ActionBtn>
        <ActionBtn onClick={onPause} disabled={loading || !isRunning} color="blue">Pause</ActionBtn>
        <ActionBtn onClick={onResume} disabled={loading || !isPaused} color="green">Resume</ActionBtn>
        <ActionBtn onClick={onSaveState} disabled={loading || !isRunning} color="blue">Save State</ActionBtn>
        <ActionBtn onClick={onSync} disabled={loading} color="cyan">Sync</ActionBtn>
        <ActionBtn onClick={onDelete} disabled={loading || transitional || (vm.status !== "stopped" && vm.status !== "error")} color="red-soft">Delete</ActionBtn>
        {showForceReset && <ActionBtn onClick={onForceReset!} disabled={loading} color="red">Force Reset</ActionBtn>}
      </div>

      {/* ISO / VRDE / Modify secondary buttons */}
      <div className="flex gap-2 flex-wrap mt-2">
        {!vm.iso_path && !isoInputVisible && (
          <ActionBtn onClick={() => { setVrdeInputVisible(false); setModifyVisible(false); setIsoInputVisible(true); }} disabled={loading || !isStopped} color="green-soft">Attach ISO</ActionBtn>
        )}
        {vm.iso_path && (
          <ActionBtn onClick={onDetachISO} disabled={loading || !isStopped} color="muted-soft">Detach ISO</ActionBtn>
        )}
        {!vm.vrde_enabled && !vrdeInputVisible && (
          <ActionBtn onClick={() => { setIsoInputVisible(false); setModifyVisible(false); setVrdeInputVisible(true); }} disabled={loading || !isStopped} color="blue-soft">Enable RDP</ActionBtn>
        )}
        {vm.vrde_enabled && (
          <ActionBtn onClick={onDisableVRDE} disabled={loading || !isStopped} color="muted-soft">Disable RDP</ActionBtn>
        )}
        {!modifyVisible && (
          <ActionBtn onClick={() => { setIsoInputVisible(false); setVrdeInputVisible(false); setModifyVisible(true); }} disabled={loading || !isStopped} color="muted-soft">Modify</ActionBtn>
        )}
      </div>

      {/* Port-forwarding section */}
      <div className="mt-3">
        <button onClick={() => setPortFwdVisible((v) => !v)} className="text-xs" style={{ color: "var(--text-muted)" }}>
          {portFwdVisible ? "▾" : "▸"} Port Rules ({vm.nat_rules.length})
        </button>
        {portFwdVisible && (
          <div className="mt-2">
            {vm.nat_rules.length > 0 && (
              <div className="mb-2 space-y-1">
                {vm.nat_rules.map((r: PortFwdRule) => (
                  <div key={r.name} className="flex items-center justify-between text-xs" style={{ color: "var(--text-muted)" }}>
                    <span>{r.name} {r.protocol.toUpperCase()} :{r.host_port}→:{r.guest_port}</span>
                    <button onClick={() => onRemovePortRule(r.name)} disabled={loading || !isStopped} className="ml-2" style={{ color: "var(--warning)", opacity: (!isStopped || loading) ? 0.3 : 1 }}>✕</button>
                  </div>
                ))}
              </div>
            )}
            {isStopped && (
              <div className="flex gap-1 flex-wrap mt-1">
                <input value={pfName} onChange={(e) => setPfName(e.target.value)} placeholder="name" style={{ ...inputStyle, width: "70px" }} />
                <select value={pfProto} onChange={(e) => setPfProto(e.target.value as "tcp" | "udp")} style={{ ...inputStyle, width: "55px" }}>
                  <option value="tcp">tcp</option>
                  <option value="udp">udp</option>
                </select>
                <input value={pfHostPort} onChange={(e) => setPfHostPort(e.target.value)} placeholder="host" type="number" style={{ ...inputStyle, width: "60px" }} />
                <input value={pfGuestPort} onChange={(e) => setPfGuestPort(e.target.value)} placeholder="guest" type="number" style={{ ...inputStyle, width: "60px" }} />
                <Btn onClick={handleAddPortRule} disabled={!pfName || !pfHostPort || !pfGuestPort || loading} color="green">Add</Btn>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Snapshots section */}
      <div className="mt-2">
        <button onClick={() => setSnapVisible((v) => !v)} className="text-xs" style={{ color: "var(--text-muted)" }}>
          {snapVisible ? "▾" : "▸"} Snapshots
        </button>
        {snapVisible && (
          <div className="mt-2">
            {snapLoading && <p className="text-xs" style={{ color: "var(--text-muted)" }}>Loading…</p>}
            {!snapLoading && snapshots && snapshots.length === 0 && (
              <p className="text-xs" style={{ color: "var(--text-muted)" }}>No snapshots</p>
            )}
            {!snapLoading && snapshots && snapshots.map((s: Snapshot) => (
              <div key={s.id} className="flex items-center justify-between text-xs mb-1" style={{ color: "var(--text-muted)" }}>
                <span>{s.name}{s.description ? ` — ${s.description}` : ""}</span>
                <div className="flex gap-2 ml-2">
                  <button onClick={() => { onRestoreSnapshot(s.name); setSnapshots(null); }} disabled={loading || !isStopped} style={{ color: "var(--accent)", opacity: (!isStopped || loading) ? 0.3 : 1 }}>↩</button>
                  <button onClick={() => { onDeleteSnapshot(s.name); setSnapshots(null); }} disabled={loading || !isStopped} style={{ color: "var(--warning)", opacity: (!isStopped || loading) ? 0.3 : 1 }}>✕</button>
                </div>
              </div>
            ))}
            {isStopped && (
              <div className="flex gap-1 flex-wrap mt-2">
                <input value={snapName} onChange={(e) => setSnapName(e.target.value)} placeholder="snapshot name" style={{ ...inputStyle, flex: "1", minWidth: "100px" }} />
                <input value={snapDesc} onChange={(e) => setSnapDesc(e.target.value)} placeholder="description (opt)" style={{ ...inputStyle, flex: "1", minWidth: "100px" }} />
                <Btn onClick={handleTakeSnapshot} disabled={!snapName.trim() || loading} color="green">Take</Btn>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Metrics section — running VMs only */}
      {isRunning && (
        <div className="mt-2">
          <div className="flex items-center gap-2">
            <button
              onClick={() => { setMetricsVisible((v) => !v); if (!metricsVisible) fetchMetrics(); }}
              className="text-xs"
              style={{ color: "var(--text-muted)" }}
            >
              {metricsVisible ? "▾" : "▸"} Metrics
            </button>
            {metricsVisible && (
              <button
                onClick={fetchMetrics}
                disabled={metricsLoading}
                className="text-xs"
                style={{ color: "var(--accent)", opacity: metricsLoading ? 0.5 : 1 }}
              >
                ↻
              </button>
            )}
          </div>
          {metricsVisible && (
            <div className="mt-1 text-xs" style={{ color: "var(--text-muted)" }}>
              {metricsLoading ? (
                <span>Loading…</span>
              ) : metrics ? (
                <span>
                  CPU Load: {metrics.cpu_percent !== null ? `${metrics.cpu_percent}%` : "N/A"}
                  {" · "}
                  RAM Allocated: {metrics.ram_used_mb !== null ? `${metrics.ram_used_mb >= 1024 ? `${(metrics.ram_used_mb / 1024).toFixed(1)} GB` : `${metrics.ram_used_mb} MB`}` : "N/A"}
                </span>
              ) : (
                <span>Unavailable</span>
              )}
            </div>
          )}
        </div>
      )}

      {/* Clone / Export section */}
      <div className="mt-2">
        {cloneVisible && (
          <div className="flex gap-2 mb-2">
            <input type="text" value={cloneName} onChange={(e) => setCloneName(e.target.value)} placeholder="New VM name" className="flex-1" style={inputStyle}
              onKeyDown={(e) => { if (e.key === "Enter") handleClone(); if (e.key === "Escape") setCloneVisible(false); }} autoFocus />
            <Btn onClick={handleClone} disabled={!cloneName.trim() || loading} color="green">Clone</Btn>
            <Btn onClick={() => { setCloneVisible(false); setCloneName(""); }} color="muted">✕</Btn>
          </div>
        )}
        {exportVisible && (
          <div className="flex gap-2 mb-2">
            <input type="text" value={exportPath} onChange={(e) => setExportPath(e.target.value)} placeholder="my-vm.ova" className="flex-1" style={inputStyle}
              onKeyDown={(e) => { if (e.key === "Enter") handleExport(); if (e.key === "Escape") setExportVisible(false); }} autoFocus />
            <Btn onClick={handleExport} disabled={!exportPath.trim() || loading} color="blue">Export</Btn>
            <Btn onClick={() => { setExportVisible(false); setExportPath(""); }} color="muted">✕</Btn>
          </div>
        )}
        {!cloneVisible && (vm.status === "stopped" || vm.status === "error") && (
          <ActionBtn onClick={() => { setExportVisible(false); setCloneVisible(true); }} disabled={loading} color="green-soft">Clone</ActionBtn>
        )}
        {" "}
        {!exportVisible && vm.status === "stopped" && (
          <ActionBtn onClick={() => { setCloneVisible(false); setExportVisible(true); }} disabled={loading} color="blue-soft">Export OVA</ActionBtn>
        )}
      </div>

      {/* Schedule section */}
      <div className="mt-2">
        <button onClick={() => setSchedVisible((v) => !v)} className="text-xs" style={{ color: "var(--text-muted)" }}>
          {schedVisible ? "▾" : "▸"} Schedules
        </button>
        {schedVisible && (
          <div className="mt-2">
            {schedLoading && <p className="text-xs" style={{ color: "var(--text-muted)" }}>Loading…</p>}
            {!schedLoading && schedules && schedules.length === 0 && (
              <p className="text-xs mb-2" style={{ color: "var(--text-muted)" }}>No schedules</p>
            )}
            {!schedLoading && schedules && schedules.map((s: VMSchedule) => (
              <div key={s.id} className="flex items-center justify-between text-xs mb-1" style={{ color: s.enabled ? "var(--accent)" : "var(--text-muted)" }}>
                <span>
                  <span className="font-semibold">{s.action}</span> {s.cron_expr}
                  {s.last_run && <span style={{ color: "var(--text-muted)", fontSize: "10px" }}> (last: {new Date(s.last_run).toLocaleString()})</span>}
                </span>
                <div className="flex gap-2 ml-2">
                  <button onClick={() => onToggleSchedule(s.id)} style={{ color: s.enabled ? "var(--warning)" : "var(--success)", opacity: loading ? 0.3 : 1 }}>
                    {s.enabled ? "⏸" : "▶"}
                  </button>
                  <button onClick={() => { onDeleteSchedule(s.id); setSchedules(null); }} style={{ color: "var(--warning)", opacity: loading ? 0.3 : 1 }}>✕</button>
                </div>
              </div>
            ))}
            <div className="flex gap-1 flex-wrap mt-2">
              <select value={schedAction} onChange={(e) => setSchedAction(e.target.value as "start" | "stop")} style={{ ...inputStyle, width: "70px" }}>
                <option value="start">start</option>
                <option value="stop">stop</option>
              </select>
              <input value={schedCron} onChange={(e) => setSchedCron(e.target.value)} placeholder="*/30 * * * * (cron)" style={{ ...inputStyle, flex: 1, minWidth: "140px" }}
                onKeyDown={(e) => { if (e.key === "Enter") handleCreateSchedule(); }} />
              <Btn onClick={handleCreateSchedule} disabled={!schedCron.trim() || loading} color="green">Add</Btn>
            </div>
            <p className="text-xs mt-1" style={{ color: "var(--text-muted)", fontSize: "10px" }}>
              Format: minute hour day month weekday — e.g. &apos;0 8 * * *&apos; = daily at 8:00, &apos;*/30 * * * *&apos; = every 30 min
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

/* ── Tiny reusable button components ── */

type BtnColor = "green" | "blue" | "muted" | "red";

function Btn({ onClick, disabled, color, children }: {
  onClick: () => void; disabled?: boolean; color: BtnColor; children: React.ReactNode;
}) {
  const colors: Record<BtnColor, [string, string]> = {
    green: ["color-mix(in srgb, var(--accent) 15%, transparent)", "var(--accent)"],
    blue:  ["color-mix(in srgb, var(--info) 15%, transparent)", "var(--info)"],
    muted: ["transparent", "var(--text-muted)"],
    red:   ["color-mix(in srgb, var(--danger) 15%, transparent)", "var(--danger)"],
  };
  const [bg, fg] = colors[color];
  return (
    <button onClick={onClick} disabled={disabled}
      className="text-xs font-semibold px-2 py-1 rounded"
      style={{ background: bg, color: fg, opacity: disabled ? 0.4 : 1 }}>
      {children}
    </button>
  );
}

type ActionColor = "green" | "orange" | "blue" | "cyan" | "red" | "red-soft" | "green-soft" | "blue-soft" | "muted-soft";

function ActionBtn({ onClick, disabled, color, children }: {
  onClick: () => void; disabled?: boolean; color: ActionColor; children: React.ReactNode;
}) {
  const styles: Record<ActionColor, { bg: string; fg: string; border: string }> = {
    green:      { bg: "color-mix(in srgb, var(--success) 12%, transparent)",    fg: "var(--success)",          border: "color-mix(in srgb, var(--success) 25%, transparent)" },
    orange:     { bg: "color-mix(in srgb, var(--warning) 12%, transparent)",   fg: "var(--warning)",          border: "color-mix(in srgb, var(--warning) 25%, transparent)" },
    blue:       { bg: "color-mix(in srgb, var(--info) 12%, transparent)", fg: "var(--info)",                 border: "color-mix(in srgb, var(--info) 25%, transparent)" },
    cyan:       { bg: "color-mix(in srgb, var(--info) 12%, transparent)",   fg: "var(--accent)",           border: "color-mix(in srgb, var(--info) 25%, transparent)" },
    red:        { bg: "color-mix(in srgb, var(--danger) 12%, transparent)",   fg: "var(--danger)",                 border: "color-mix(in srgb, var(--danger) 30%, transparent)" },
    "red-soft": { bg: "color-mix(in srgb, var(--warning) 8%, transparent)",   fg: "var(--warning)",                                         border: "color-mix(in srgb, var(--warning) 15%, transparent)" },
    "green-soft":{ bg: "color-mix(in srgb, var(--accent) 7%, transparent)",  fg: "var(--accent)",           border: "color-mix(in srgb, var(--accent) 15%, transparent)" },
    "blue-soft": { bg: "color-mix(in srgb, var(--info) 7%, transparent)",fg: "var(--info)",                 border: "color-mix(in srgb, var(--info) 15%, transparent)" },
    "muted-soft":{ bg: "color-mix(in srgb, var(--accent) 7%, transparent)",  fg: "var(--text-muted)",       border: "color-mix(in srgb, var(--accent) 15%, transparent)" },
  };
  const s = styles[color];
  return (
    <button onClick={onClick} disabled={disabled}
      className="text-xs font-semibold px-3 py-1 rounded-full transition-all"
      style={{ background: s.bg, color: s.fg, border: `1px solid ${s.border}`, opacity: disabled ? 0.4 : 1 }}>
      {children}
    </button>
  );
}
