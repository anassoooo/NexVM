"use client";

import { useState } from "react";
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

  const handleStart       = (id: string) => withLoading(() => api.post("/api/v1/admin/vm/start",       { vm_id: id }));
  const handleStop        = (id: string) => withLoading(() => api.post("/api/v1/admin/vm/stop",        { vm_id: id }));
  const handleDelete      = (id: string) => withLoading(() => api.post("/api/v1/admin/vm/delete",      { vm_id: id }));
  const handleForceReset  = (id: string) => withLoading(() => api.post("/api/v1/admin/vm/force-reset", { vm_id: id }));
  const handleSync        = (id: string) => withLoading(async () => {
    const updated = await api.post<VM>("/api/v1/vm/sync", { vm_id: id });
    setVms((prev) => prev.map((v) => (v.id === id ? updated : v)));
  });

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
        showOwner={true}
      />
    </div>
  );
}
