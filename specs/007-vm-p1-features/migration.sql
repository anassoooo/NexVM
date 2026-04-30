-- Migration: Spec 007 — VM P1 Features
-- Apply via Supabase SQL editor

ALTER TABLE public.vms
  ADD COLUMN IF NOT EXISTS iso_path     text,
  ADD COLUMN IF NOT EXISTS vrde_enabled boolean NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS vrde_port    integer;

ALTER TABLE public.vms
  ADD CONSTRAINT vms_vrde_port_check
    CHECK (vrde_port IS NULL OR (vrde_port >= 1024 AND vrde_port <= 65535));
