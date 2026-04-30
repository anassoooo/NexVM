# Contract — AI Command API (updated)

**Route**: `POST /api/v1/ai/command`

## `create_vm` action — updated schema

```json
{
  "action": "create_vm",
  "name": "<string, 1-50 chars>",
  "os": "<string>",
  "ram": "<integer, 512-16384>",
  "cpu": "<integer, 1-32, optional, default 2>",
  "disk_size": "<integer MB, 5120-512000, optional, default 20480>"
}
```

`cpu` and `disk_size` are optional. If omitted by the AI, defaults apply.

## No other contract changes

`list_vms`, `start_vm`, `stop_vm`, `delete_vm`, `query_analytics`, `chat` —
schemas unchanged. The bugs fixed here are implementation errors, not contract violations.
