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

export interface AICommandResponse {
  action: string;
  result: string;
  ai_response: Record<string, unknown>;
}

export interface UserAnalytics {
  total_vms: number;
  running_vms: number;
  stopped_vms: number;
  error_vms: number;
  total_ai_commands: number;
}

export interface AdminAnalytics {
  total_users: number;
  total_vms: number;
  running_vms: number;
  stopped_vms: number;
  error_vms: number;
  total_ai_commands: number;
}
