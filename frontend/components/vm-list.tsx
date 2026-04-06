"use client";

import { VM } from "@/types";
import VMCard from "./vm-card";

interface VMListProps {
  vms: VM[];
  loading: boolean;
  onStart: (vmId: string) => void;
  onStop: (vmId: string) => void;
  onDelete: (vmId: string) => void;
}

export default function VMList({ vms, loading, onStart, onStop, onDelete }: VMListProps) {
  if (loading && vms.length === 0) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {[1, 2, 3].map((i) => (
          <div key={i} className="border rounded-lg p-4 h-40 animate-pulse bg-gray-100" />
        ))}
      </div>
    );
  }

  if (vms.length === 0) {
    return (
      <p className="text-gray-500 text-center py-12">
        No VMs yet — create your first one
      </p>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {vms.map((vm) => (
        <VMCard
          key={vm.id}
          vm={vm}
          loading={loading}
          onStart={() => onStart(vm.id)}
          onStop={() => onStop(vm.id)}
          onDelete={() => onDelete(vm.id)}
        />
      ))}
    </div>
  );
}
