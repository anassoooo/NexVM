export interface PortFwdRule {
  name: string;
  protocol: "tcp" | "udp";
  host_port: number;
  guest_port: number;
}

export interface Snapshot {
  id: string;
  vm_id: string;
  name: string;
  description: string | null;
  created_at: string;
}

export interface VM {
  id: string;
  user_id: string;
  name: string;
  os: string;
  ram: number;
  cpu: number;
  disk_size: number;
  vbox_id: string | null;
  status: "stopped" | "starting" | "running" | "stopping" | "paused" | "error";
  error_message: string | null;
  iso_path: string | null;
  vrde_enabled: boolean;
  vrde_port: number | null;
  nat_rules: PortFwdRule[];
  created_at: string;
  updated_at: string;
}

export interface Log {
  id: string;
  user_id: string | null;
  action:
    | "create_vm"
    | "start_vm"
    | "stop_vm"
    | "delete_vm"
    | "login"
    | "ai_command";
  target: string;
  status: "success" | "failure";
  message: string;
  created_at: string;
}

export interface AIUsage {
  id: string;
  user_id: string | null;
  prompt: string;
  response: string;
  tokens: number;
  created_at: string;
}

export interface UserProfile {
  id: string;
  is_admin: boolean;
  created_at: string;
}

export interface UserInfo {
  id: string;
  email: string;
  is_admin: boolean;
}

export interface PendingAction {
  action: "delete_vm";
  vm_id: string;
  vm_name: string;
}

export interface AICommandResponse {
  action: string;
  result: string;
  ai_response: Record<string, unknown>;
  pending_action?: PendingAction | null;
}

export interface VMMetrics {
  cpu_percent: number | null;
  ram_used_mb: number | null;
}

export interface UserAnalytics {
  total_vms: number;
  running_vms: number;
  stopped_vms: number;
  error_vms: number;
  total_ai_commands: number;
  total_disk_used_mb: number;
  disk_quota_mb: number;
}

export interface AdminAnalytics {
  total_users: number;
  total_vms: number;
  running_vms: number;
  stopped_vms: number;
  error_vms: number;
  total_ai_commands: number;
  total_disk_used_mb: number;
  disk_quota_mb: number;
}

export interface TimeSeriesPoint {
  date: string;
  count: number;
}

export interface AnalyticsTimeSeries {
  vms_created: TimeSeriesPoint[];
  vms_by_day: TimeSeriesPoint[];
  ai_commands_by_day: TimeSeriesPoint[];
}

export interface VMSchedule {
  id: string;
  user_id: string;
  vm_id: string;
  action: "start" | "stop";
  cron_expr: string;
  enabled: boolean;
  last_run: string | null;
  created_at: string;
}

// ─── Autopilot (spec 013) ─────────────────────────────────────────────────

export type RunStatus = "answered" | "needs_approval" | "running" | "completed" | "failed" | "cancelled";
export type StepStatus = "pending" | "running" | "done" | "failed" | "skipped";
export type Risk = "low" | "costly" | "destructive";

export interface PlanStep {
  index: number;
  tool: string;
  args: Record<string, unknown>;
  risk: Risk;
  description: string;
  effect: string;
  status: StepStatus;
  result: string;
  duration_ms: number;
}

export interface Finding {
  vm: string;
  severity: "info" | "warning" | "critical";
  code: string;
  message: string;
  suggestion: string;
}

export interface TraceSpan {
  kind: "llm" | "tool" | "step";
  name: string;
  start_ms: number;
  duration_ms: number;
  ok: boolean;
  tokens_in: number;
  tokens_out: number;
  detail: string;
}

export interface AgentRun {
  id: string;
  conversation_id: string;
  prompt: string;
  status: RunStatus;
  answer: string | null;
  plan: PlanStep[];
  plan_version: number;
  findings: Finding[];
  trace: TraceSpan[];
  model: string | null;
  total_tokens: number;
  latency_ms: number;
  repairs: number;
  error: string | null;
  created_at: string;
  risk: Partial<Record<Risk, number>>;
  resources: { new_vms: number; ram_mb: number; cpu: number; disk_mb: number };
}

export type AgentRunSummary = Pick<
  AgentRun,
  "id" | "conversation_id" | "prompt" | "status" | "answer" | "plan_version" | "model" | "total_tokens" | "latency_ms" | "created_at"
>;
