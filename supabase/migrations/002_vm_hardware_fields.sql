-- ============================================================
-- myVMS — VM hardware fields
-- Date: 2026-04-21
-- Adds cpu, disk_size, vbox_id to the vms table
-- ============================================================

ALTER TABLE public.vms
  ADD COLUMN IF NOT EXISTS cpu       integer NOT NULL DEFAULT 2,
  ADD COLUMN IF NOT EXISTS disk_size integer NOT NULL DEFAULT 20480,
  ADD COLUMN IF NOT EXISTS vbox_id   text;

ALTER TABLE public.vms
  ADD CONSTRAINT vms_cpu_check       CHECK (cpu >= 1 AND cpu <= 32),
  ADD CONSTRAINT vms_disk_size_check CHECK (disk_size >= 5120 AND disk_size <= 512000);
