"use client";

import { useState } from "react";
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

  async function handleStart(vmId: string) {
    setLoading(true);
    setError(null);
    try {
      await api.post("/api/v1/vm/start", { vm_id: vmId });
      await refetch();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to start VM");
      setLoading(false);
    }
  }

  async function handleStop(vmId: string) {
    setLoading(true);
    setError(null);
    try {
      await api.post("/api/v1/vm/stop", { vm_id: vmId });
      await refetch();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to stop VM");
      setLoading(false);
    }
  }

  async function handleDelete(vmId: string) {
    setLoading(true);
    setError(null);
    try {
      await api.post("/api/v1/vm/delete", { vm_id: vmId });
      await refetch();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to delete VM");
      setLoading(false);
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Virtual Machines</h1>
        <button
          onClick={() => setShowForm(true)}
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 text-sm font-medium"
        >
          Create VM
        </button>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 text-red-700 rounded text-sm">{error}</div>
      )}

      {showForm && (
        <VMCreateForm
          onSuccess={async () => {
            setShowForm(false);
            await refetch();
          }}
          onCancel={() => setShowForm(false)}
        />
      )}

      <VMList
        vms={vms}
        loading={loading}
        onStart={handleStart}
        onStop={handleStop}
        onDelete={handleDelete}
      />
    </div>
  );
}
