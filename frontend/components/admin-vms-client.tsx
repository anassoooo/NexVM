"use client";

import { useEffect, useState } from "react";
import { VM } from "@/types";
import { api } from "@/lib/api";
import VMList from "@/components/vm-list";

export default function AdminVMsClient({ initialVms }: { initialVms: VM[] }) {
  const [vms, setVms] = useState<VM[]>(initialVms);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function refetch() {
    setLoading(true);
    setError(null);
    try {
      const data = await api.get<VM[]>("/api/v1/admin/vm");
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

  const handleStart        = (id: string) => withLoading(() => api.post("/api/v1/admin/vm/start",       { vm_id: id }));
  const handleStop         = (id: string) => withLoading(() => api.post("/api/v1/admin/vm/stop",        { vm_id: id }));
  const handleDelete       = (id: string) => withLoading(() => api.post("/api/v1/admin/vm/delete",      { vm_id: id }));
  const handleForceReset   = (id: string) => withLoading(() => api.post("/api/v1/admin/vm/force-reset", { vm_id: id }));
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

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold" style={{ color: "var(--text)" }}>
          All Virtual Machines
        </h1>
      </div>

      {error && (
        <div
          className="mb-4 p-3 rounded text-sm"
          style={{ background: "rgba(255,109,0,0.1)", color: "var(--warning)", border: "1px solid rgba(255,109,0,0.2)" }}
        >
          {error}
        </div>
      )}

      <VMList
        vms={vms}
        loading={loading}
        onStart={handleStart}
        onStop={handleStop}
        onDelete={handleDelete}
        onSync={handleSync}
        onForceReset={handleForceReset}
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
        showOwner={true}
      />
    </div>
  );
}
