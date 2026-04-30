"use client";

import { useEffect, useState } from "react";
import { VM } from "@/types";
import { api } from "@/lib/api";
import VMList from "@/components/vm-list";
import VMCreateForm from "@/components/vm-create-form";

export default function VMsClient({ initialVms }: { initialVms: VM[] }) {
  const [vms, setVms] = useState<VM[]>(initialVms);
  const [loading, setLoading] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [error, setError] = useState<string | null>(null);

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

  const handleStart     = (id: string) => withLoading(() => api.post("/api/v1/vm/start",  { vm_id: id }));
  const handleStop      = (id: string) => withLoading(() => api.post("/api/v1/vm/stop",   { vm_id: id }));
  const handleDelete    = (id: string) => withLoading(() => api.post("/api/v1/vm/delete", { vm_id: id }));
  const handleSync      = (id: string) => withLoading(async () => {
    const updated = await api.post<VM>("/api/v1/vm/sync", { vm_id: id });
    setVms((prev) => prev.map((v) => (v.id === id ? updated : v)));
  });
  const handleAttachISO  = (id: string, isoPath: string) => withLoading(() => api.post("/api/v1/vm/iso",  { vm_id: id, iso_path: isoPath }));
  const handleDetachISO  = (id: string) => withLoading(() => api.delete("/api/v1/vm/iso",  { vm_id: id }));
  const handleEnableVRDE = (id: string, port: number) => withLoading(() => api.post("/api/v1/vm/vrde", { vm_id: id, port }));
  const handleDisableVRDE = (id: string) => withLoading(() => api.delete("/api/v1/vm/vrde", { vm_id: id }));

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold" style={{ color: "var(--text)" }}>
          Virtual Machines
        </h1>
        <button onClick={() => setShowForm(true)} className="btn-primary" style={{ padding: "8px 20px" }}>
          Create VM
        </button>
      </div>

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
      />
    </div>
  );
}
