"use client";

import { VM } from "@/types";
import VMCard from "./vm-card";

interface VMListProps {
  vms: VM[];
  loading: boolean;
  onStart: (vmId: string) => void;
  onStop: (vmId: string) => void;
  onDelete: (vmId: string) => void;
  onSync: (vmId: string) => void;
  onForceReset?: (vmId: string) => void;
  onAttachISO: (vmId: string, isoPath: string) => void;
  onDetachISO: (vmId: string) => void;
  onEnableVRDE: (vmId: string, port: number) => void;
  onDisableVRDE: (vmId: string) => void;
  onPause: (vmId: string) => void;
  onResume: (vmId: string) => void;
  onSaveState: (vmId: string) => void;
  onModify: (vmId: string, ram: number | null, cpu: number | null) => void;
  onAddPortRule: (vmId: string, name: string, proto: "tcp" | "udp", hp: number, gp: number) => void;
  onRemovePortRule: (vmId: string, name: string) => void;
  onTakeSnapshot: (vmId: string, name: string, desc: string) => void;
  onRestoreSnapshot: (vmId: string, name: string) => void;
  onDeleteSnapshot: (vmId: string, name: string) => void;
  onClone: (vmId: string, newName: string) => void;
  onExport: (vmId: string, outputPath: string) => void;
  onCreateSchedule: (vmId: string, action: "start" | "stop", cronExpr: string) => void;
  onDeleteSchedule: (scheduleId: string) => void;
  onToggleSchedule: (scheduleId: string) => void;
  showOwner?: boolean;
}

export default function VMList({
  vms, loading, onStart, onStop, onDelete, onSync, onForceReset,
  onAttachISO, onDetachISO, onEnableVRDE, onDisableVRDE,
  onPause, onResume, onSaveState, onModify,
  onAddPortRule, onRemovePortRule,
  onTakeSnapshot, onRestoreSnapshot, onDeleteSnapshot,
  onClone, onExport,
  onCreateSchedule, onDeleteSchedule, onToggleSchedule,
  showOwner,
}: VMListProps) {
  if (loading && vms.length === 0) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {[1, 2, 3].map((i) => (
          <div key={i} className="glass animate-pulse h-40" style={{ opacity: 0.5 }} />
        ))}
      </div>
    );
  }

  if (vms.length === 0) {
    return (
      <p className="text-center py-16" style={{ color: "var(--text-muted)" }}>
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
          onSync={() => onSync(vm.id)}
          onForceReset={onForceReset ? () => onForceReset(vm.id) : undefined}
          onAttachISO={(isoPath) => onAttachISO(vm.id, isoPath)}
          onDetachISO={() => onDetachISO(vm.id)}
          onEnableVRDE={(port) => onEnableVRDE(vm.id, port)}
          onDisableVRDE={() => onDisableVRDE(vm.id)}
          onPause={() => onPause(vm.id)}
          onResume={() => onResume(vm.id)}
          onSaveState={() => onSaveState(vm.id)}
          onModify={(ram, cpu) => onModify(vm.id, ram, cpu)}
          onAddPortRule={(name, proto, hp, gp) => onAddPortRule(vm.id, name, proto, hp, gp)}
          onRemovePortRule={(name) => onRemovePortRule(vm.id, name)}
          onTakeSnapshot={(name, desc) => onTakeSnapshot(vm.id, name, desc)}
          onRestoreSnapshot={(name) => onRestoreSnapshot(vm.id, name)}
          onDeleteSnapshot={(name) => onDeleteSnapshot(vm.id, name)}
          onClone={(newName) => onClone(vm.id, newName)}
          onExport={(outputPath) => onExport(vm.id, outputPath)}
          onCreateSchedule={(action, cronExpr) => onCreateSchedule(vm.id, action, cronExpr)}
          onDeleteSchedule={(scheduleId) => onDeleteSchedule(scheduleId)}
          onToggleSchedule={(scheduleId) => onToggleSchedule(scheduleId)}
          showOwner={showOwner}
        />
      ))}
    </div>
  );
}
