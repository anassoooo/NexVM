"use client";

import { useEffect, useState } from "react";
import { UserAnalytics, VM } from "@/types";
import { api } from "@/lib/api";
import VMList from "@/components/vm-list";
import VMCreateForm from "@/components/vm-create-form";

export default function VMsClient({
  initialVms,
  initialAnalytics,
}: {
  initialVms: VM[];
  initialAnalytics: UserAnalytics | null;
}) {
  const [vms, setVms] = useState<VM[]>(initialVms);
  const [loading, setLoading] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showImport, setShowImport] = useState(false);
  const [importPath, setImportPath] = useState("");
  const [importName, setImportName] = useState("");
  const [importRam, setImportRam] = useState("1024");
  const [importCpu, setImportCpu] = useState("2");

  async function refetch() {
    setLoading(true);
    setError(null);
    try {
      const data = await api.get<VM[]>("/api/v1/vm");
      setVms(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to fetch VMs");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    const hasTransitional = vms.some(
      (v) => v.status === "starting" || v.status === "stopping"
    );
    if (!hasTransitional) return;
    const id = setInterval(() => void refetch(), 5000);
    return () => clearInterval(id);
  }, [vms]);

  async function withLoading(fn: () => Promise<void>) {
    setLoading(true);
    setError(null);
    try {
      await fn();
      await refetch();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Operation failed");
      setLoading(false);
    }
  }

  const handleStart        = (id: string) => withLoading(() => api.post("/api/v1/vm/start",  { vm_id: id }));
  const handleStop         = (id: string) => withLoading(() => api.post("/api/v1/vm/stop",   { vm_id: id }));
  const handleDelete       = (id: string) => withLoading(() => api.post("/api/v1/vm/delete", { vm_id: id }));
  const handleSync         = (id: string) => withLoading(async () => {
    const updated = await api.post<VM>("/api/v1/vm/sync", { vm_id: id });
    setVms((prev) => prev.map((v) => (v.id === id ? updated : v)));
  });
  const handleAttachISO    = (id: string, isoPath: string) => withLoading(() => api.post("/api/v1/vm/iso",  { vm_id: id, iso_path: isoPath }));
  const handleDetachISO    = (id: string) => withLoading(() => api.delete("/api/v1/vm/iso",  { vm_id: id }));
  const handleEnableVRDE   = (id: string, port: number) => withLoading(() => api.post("/api/v1/vm/vrde", { vm_id: id, port }));
  const handleDisableVRDE  = (id: string) => withLoading(() => api.delete("/api/v1/vm/vrde", { vm_id: id }));
  const handlePause        = (id: string) => withLoading(() => api.post("/api/v1/vm/pause",     { vm_id: id }));
  const handleResume       = (id: string) => withLoading(() => api.post("/api/v1/vm/resume",    { vm_id: id }));
  const handleSaveState    = (id: string) => withLoading(() => api.post("/api/v1/vm/savestate", { vm_id: id }));
  const handleModify       = (id: string, ram: number | null, cpu: number | null) =>
    withLoading(() => api.post("/api/v1/vm/modify", { vm_id: id, ram, cpu }));
  const handleAddPortRule  = (id: string, name: string, proto: "tcp" | "udp", hp: number, gp: number) =>
    withLoading(() => api.post("/api/v1/vm/portfwd", { vm_id: id, name, protocol: proto, host_port: hp, guest_port: gp }));
  const handleRemovePortRule = (id: string, name: string) =>
    withLoading(() => api.delete("/api/v1/vm/portfwd", { vm_id: id, name }));
  const handleTakeSnapshot   = (id: string, name: string, desc: string) =>
    withLoading(() => api.post("/api/v1/vm/snapshot", { vm_id: id, name, description: desc }));
  const handleRestoreSnapshot = (id: string, name: string) =>
    withLoading(() => api.post("/api/v1/vm/snapshot/restore", { vm_id: id, name }));
  const handleDeleteSnapshot  = (id: string, name: string) =>
    withLoading(() => api.delete("/api/v1/vm/snapshot", { vm_id: id, name }));
  const handleClone           = (id: string, newName: string) =>
    withLoading(() => api.post("/api/v1/vm/clone", { vm_id: id, new_name: newName }));
  const handleExport          = (id: string, outputPath: string) =>
    withLoading(() => api.post("/api/v1/vm/export", { vm_id: id, output_path: outputPath }));
  const handleImport          = () => {
    if (!importPath.trim() || !importName.trim()) return;
    withLoading(() => api.post("/api/v1/vm/import", {
      source_path: importPath.trim(),
      name: importName.trim(),
      ram: parseInt(importRam, 10) || 1024,
      cpu: parseInt(importCpu, 10) || 2,
    }));
    setShowImport(false); setImportPath(""); setImportName(""); setImportRam("1024"); setImportCpu("2");
  };

  const quotaBar = (() => {
    if (!initialAnalytics) return null;
    const { total_disk_used_mb: used, disk_quota_mb: quota } = initialAnalytics;
    const pct      = quota > 0 ? Math.min(100, (used / quota) * 100) : 0;
    const usedGb   = (used  / 1024).toFixed(1);
    const quotaGb  = (quota / 1024).toFixed(1);
    const barColor = pct > 90 ? "var(--warning)" : "var(--accent)";
    return (
      <div className="glass mb-6" style={{ padding: "1rem 1.25rem" }}>
        <div className="flex justify-between text-xs mb-2" style={{ color: "var(--text-muted)" }}>
          <span>Disk usage</span>
          <span style={{ color: barColor }}>{usedGb} GB / {quotaGb} GB ({pct.toFixed(1)}%)</span>
        </div>
        <div style={{ background: "rgba(255,255,255,0.06)", borderRadius: "4px", overflow: "hidden", height: "6px" }}>
          <div style={{ width: `${pct.toFixed(1)}%`, height: "100%", background: barColor, transition: "width 0.3s" }} />
        </div>
      </div>
    );
  })();

  return (
    <div>
      {quotaBar}
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold" style={{ color: "var(--text)" }}>
          Virtual Machines
        </h1>
        <div className="flex gap-2">
          <button onClick={() => setShowImport(true)} className="btn-primary" style={{ padding: "8px 20px", background: "rgba(100,180,255,0.12)", color: "#64b4ff", border: "1px solid rgba(100,180,255,0.25)" }}>
            Import OVA
          </button>
          <button onClick={() => setShowForm(true)} className="btn-primary" style={{ padding: "8px 20px" }}>
            Create VM
          </button>
        </div>
      </div>

      {showImport && (
        <div className="glass mb-4" style={{ padding: "1rem" }}>
          <p className="text-sm font-semibold mb-3" style={{ color: "var(--text)" }}>Import OVA / OVF</p>
          <div className="flex gap-2 flex-wrap">
            <input type="text" value={importPath} onChange={(e) => setImportPath(e.target.value)} placeholder="/path/to/file.ova" className="flex-1" style={{ background: "rgba(255,255,255,0.06)", color: "var(--text)", border: "1px solid rgba(0,230,118,0.2)", outline: "none", borderRadius: "4px", padding: "6px 10px", fontSize: "13px", minWidth: "200px" }} />
            <input type="text" value={importName} onChange={(e) => setImportName(e.target.value)} placeholder="VM name" className="flex-1" style={{ background: "rgba(255,255,255,0.06)", color: "var(--text)", border: "1px solid rgba(0,230,118,0.2)", outline: "none", borderRadius: "4px", padding: "6px 10px", fontSize: "13px", minWidth: "120px" }} />
            <input type="number" value={importRam} onChange={(e) => setImportRam(e.target.value)} placeholder="RAM (MB)" min={512} max={16384} style={{ background: "rgba(255,255,255,0.06)", color: "var(--text)", border: "1px solid rgba(0,230,118,0.2)", outline: "none", borderRadius: "4px", padding: "6px 10px", fontSize: "13px", width: "90px" }} />
            <input type="number" value={importCpu} onChange={(e) => setImportCpu(e.target.value)} placeholder="CPU" min={1} max={32} style={{ background: "rgba(255,255,255,0.06)", color: "var(--text)", border: "1px solid rgba(0,230,118,0.2)", outline: "none", borderRadius: "4px", padding: "6px 10px", fontSize: "13px", width: "70px" }} />
            <button onClick={handleImport} disabled={!importPath.trim() || !importName.trim() || loading} className="btn-primary" style={{ padding: "6px 16px" }}>Import</button>
            <button onClick={() => { setShowImport(false); setImportPath(""); setImportName(""); }} className="btn-primary" style={{ padding: "6px 16px", background: "transparent", color: "var(--text-muted)" }}>Cancel</button>
          </div>
        </div>
      )}

      {error && (
        <div
          className="mb-4 p-3 rounded text-sm"
          style={{ background: "rgba(255,109,0,0.1)", color: "var(--warning)", border: "1px solid rgba(255,109,0,0.2)" }}
        >
          {error}
        </div>
      )}

      {showForm && (
        <VMCreateForm
          onSuccess={async () => { setShowForm(false); await refetch(); }}
          onCancel={() => setShowForm(false)}
        />
      )}

      <VMList
        vms={vms}
        loading={loading}
        onStart={handleStart}
        onStop={handleStop}
        onDelete={handleDelete}
        onSync={handleSync}
        onAttachISO={handleAttachISO}
        onDetachISO={handleDetachISO}
        onEnableVRDE={handleEnableVRDE}
        onDisableVRDE={handleDisableVRDE}
        onPause={handlePause}
        onResume={handleResume}
        onSaveState={handleSaveState}
        onModify={handleModify}
        onAddPortRule={handleAddPortRule}
        onRemovePortRule={handleRemovePortRule}
        onTakeSnapshot={handleTakeSnapshot}
        onRestoreSnapshot={handleRestoreSnapshot}
        onDeleteSnapshot={handleDeleteSnapshot}
        onClone={handleClone}
        onExport={handleExport}
      />
    </div>
  );
}
