export interface VM {
  id: string;
  user_id: string;
  name: string;
  os: string;
  ram: number;
  status: "stopped" | "starting" | "running" | "stopping" | "error";
  error_message: string | null;
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
