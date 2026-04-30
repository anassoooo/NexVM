"use client";

import { useState } from "react";
import { api } from "@/lib/api";

const OS_OPTIONS = [
  "Ubuntu 22.04",
  "Ubuntu 20.04",
  "Debian 12",
  "Debian 11",
  "Kali Linux",
  "Fedora",
  "Arch Linux",
  "CentOS Stream",
  "Rocky Linux",
  "AlmaLinux",
  "Windows 10",
  "Windows 11",
];

const RAM_OPTIONS = [512, 1024, 2048, 4096, 8192, 16384];
const CPU_OPTIONS = [1, 2, 4, 8, 16, 32];
const DISK_OPTIONS = [
  { label: "5 GB",   value: 5120 },
  { label: "10 GB",  value: 10240 },
  { label: "20 GB",  value: 20480 },
  { label: "40 GB",  value: 40960 },
  { label: "80 GB",  value: 81920 },
  { label: "100 GB", value: 102400 },
];

interface VMCreateFormProps {
  onSuccess: () => void;
  onCancel: () => void;
}

export default function VMCreateForm({ onSuccess, onCancel }: VMCreateFormProps) {
  const [name, setName]         = useState("");
  const [os, setOs]             = useState(OS_OPTIONS[0]);
  const [ram, setRam]           = useState(1024);
  const [cpu, setCpu]           = useState(2);
  const [diskSize, setDiskSize] = useState(20480);
  const [error, setError]       = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    if (!/^[a-zA-Z0-9][a-zA-Z0-9 \-]{0,49}$/.test(name)) {
      setError("Name: 1–50 chars, alphanumeric, hyphens, spaces only");
      return;
    }

    setSubmitting(true);
    try {
      await api.post("/api/v1/vm/create", { name, os, ram, cpu, disk_size: diskSize });
      onSuccess();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create VM");
    } finally {
      setSubmitting(false);
    }
  }

  const selectClass = "input-dark";

  return (
    <div className="glass mb-6" style={{ padding: "1.5rem" }}>
      <h2 className="font-bold mb-5 text-base" style={{ color: "var(--text)" }}>
        Create Virtual Machine
      </h2>

      {error && (
        <div
          className="mb-4 p-3 rounded text-sm"
          style={{ background: "rgba(255,109,0,0.1)", color: "var(--warning)", border: "1px solid rgba(255,109,0,0.2)" }}
        >
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Name */}
        <div>
          <label className="block text-xs font-medium mb-2 uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>
            Name
          </label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            maxLength={50}
            required
            className="input-dark"
            placeholder="my-vm-01"
          />
        </div>

        {/* OS */}
        <div>
          <label className="block text-xs font-medium mb-2 uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>
            Operating System
          </label>
          <select value={os} onChange={(e) => setOs(e.target.value)} className={selectClass}>
            {OS_OPTIONS.map((o) => (
              <option key={o} value={o}>{o}</option>
            ))}
          </select>
        </div>

        {/* CPU + RAM — side by side */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium mb-2 uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>
              CPU (vCores)
            </label>
            <select value={cpu} onChange={(e) => setCpu(Number(e.target.value))} className={selectClass}>
              {CPU_OPTIONS.map((c) => (
                <option key={c} value={c}>{c} {c === 1 ? "core" : "cores"}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium mb-2 uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>
              RAM (MB)
            </label>
            <select value={ram} onChange={(e) => setRam(Number(e.target.value))} className={selectClass}>
              {RAM_OPTIONS.map((r) => (
                <option key={r} value={r}>{r >= 1024 ? `${r / 1024} GB` : `${r} MB`}</option>
              ))}
            </select>
          </div>
        </div>

        {/* Disk */}
        <div>
          <label className="block text-xs font-medium mb-2 uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>
            Disk Size
          </label>
          <select value={diskSize} onChange={(e) => setDiskSize(Number(e.target.value))} className={selectClass}>
            {DISK_OPTIONS.map(({ label, value }) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </select>
        </div>

        {/* Summary */}
        <div
          className="text-xs p-3 rounded"
          style={{ background: "rgba(0,230,118,0.05)", color: "var(--text-muted)", border: "1px solid var(--border)" }}
        >
          {cpu} vCPU · {ram >= 1024 ? `${ram / 1024} GB` : `${ram} MB`} RAM ·{" "}
          {DISK_OPTIONS.find(d => d.value === diskSize)?.label} Disk · {os}
        </div>

        <div className="flex gap-3 pt-1">
          <button type="submit" disabled={submitting} className="btn-primary">
            {submitting ? "Creating..." : "Create VM"}
          </button>
          <button
            type="button"
            onClick={onCancel}
            className="text-sm px-5 py-2 rounded-full font-medium transition-colors"
            style={{ background: "rgba(255,255,255,0.04)", color: "var(--text-muted)", border: "1px solid var(--border)" }}
          >
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}
