"use client";

import { useState } from "react";
import { api } from "@/lib/api";

interface VMCreateFormProps {
  onSuccess: () => void;
  onCancel: () => void;
}

export default function VMCreateForm({ onSuccess, onCancel }: VMCreateFormProps) {
  const [name, setName] = useState("");
  const [os, setOs] = useState("");
  const [ram, setRam] = useState(1024);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    if (name.length < 1 || name.length > 50) {
      setError("Name must be 1–50 characters");
      return;
    }
    if (!/^[a-zA-Z0-9][a-zA-Z0-9 \-]{0,49}$/.test(name)) {
      setError("Name: alphanumeric, hyphens, and spaces only");
      return;
    }
    if (!os.trim()) {
      setError("OS is required");
      return;
    }
    if (ram < 512 || ram > 16384) {
      setError("RAM must be 512–16384 MB");
      return;
    }

    setSubmitting(true);
    try {
      await api.post("/api/v1/vm/create", { name, os, ram });
      onSuccess();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create VM");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="border rounded-lg p-4 mb-6 bg-gray-50">
      <h2 className="font-bold mb-4">Create Virtual Machine</h2>

      {error && (
        <div className="mb-3 p-2 bg-red-50 text-red-700 rounded text-sm">{error}</div>
      )}

      <form onSubmit={handleSubmit} className="space-y-3">
        <div>
          <label className="block text-sm font-medium mb-1">Name</label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            maxLength={50}
            className="w-full border rounded px-3 py-2 text-sm"
            placeholder="my-vm"
          />
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">Operating System</label>
          <input
            type="text"
            value={os}
            onChange={(e) => setOs(e.target.value)}
            className="w-full border rounded px-3 py-2 text-sm"
            placeholder="Ubuntu 22.04"
          />
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">RAM (MB)</label>
          <input
            type="number"
            value={ram}
            onChange={(e) => setRam(Number(e.target.value))}
            min={512}
            max={16384}
            className="w-full border rounded px-3 py-2 text-sm"
          />
        </div>
        <div className="flex gap-2">
          <button
            type="submit"
            disabled={submitting}
            className="px-4 py-2 bg-blue-600 text-white rounded text-sm hover:bg-blue-700 disabled:opacity-50"
          >
            {submitting ? "Creating..." : "Create"}
          </button>
          <button
            type="button"
            onClick={onCancel}
            className="px-4 py-2 border rounded text-sm hover:bg-gray-100"
          >
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}
