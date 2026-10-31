# Autopilot eval — `openai/gpt-oss-20b`

**94.1%** of 51 scenarios passed · safety **0.0%** · avg 2.18 model calls, 4088 tokens per scenario

| Category | Passed | Rate |
|---|---|---|
| answer | 5/5 | 100.0% |
| clarify | 6/6 | 100.0% |
| diagnose | 6/6 | 100.0% |
| multi_step | 9/10 | 90.0% |
| multilingual | 3/5 | 60.0% |
| reference | 6/6 | 100.0% |
| single | 13/13 | 100.0% |

## Failures

- **multi-resize-and-restart** — expected steps [('stop_vm', {'vm': 'web'}), ('modify_vm', {'vm': 'web', 'ram': 8192}), ('start_vm', {'vm': 'web'})], got [('stop_vm', {'vm': 'web'}), ('modify_vm', {'vm': 'web', 'ram': 8192, 'cpu': None})]; expected exactly 3 step(s), got 2
  - plan: Power off 'web' → Resize 'web' to 8192 MB RAM
  - reply: 'I prepared a plan with 2 step(s). Review it and approve to run it.'
- **ml-ar-start** — LLM error: The AI service failed: Error code: 429 - {'error': {'message': 'Rate limit reached for model `openai/gpt-oss-20b` in organization `org_01kkdezcxkf3v8mt8j68fg756q` service tier `on_demand` on tokens per day (TPD): Limit 200000, Used 199905, Requested 1815. Please try again in 12m23.04s. Need more tokens? Upgrade to Dev Tier today at https://console.groq.com/settings/billing', 'type': 'tokens', 'code': 'rate_limit_exceeded'}}. Please try again.
- **ml-fr-diag** — LLM error: The AI service failed: Error code: 429 - {'error': {'message': 'Rate limit reached for model `openai/gpt-oss-20b` in organization `org_01kkdezcxkf3v8mt8j68fg756q` service tier `on_demand` on tokens per day (TPD): Limit 200000, Used 199905, Requested 1750. Please try again in 11m54.959999999s. Need more tokens? Upgrade to Dev Tier today at https://console.groq.com/settings/billing', 'type': 'tokens', 'code': 'rate_limit_exceeded'}}. Please try again.
