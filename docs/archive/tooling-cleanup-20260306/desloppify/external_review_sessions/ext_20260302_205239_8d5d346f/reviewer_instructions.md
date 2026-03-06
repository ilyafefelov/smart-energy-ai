# External Blind Review Session

Session id: ext_20260302_205239_8d5d346f
Session token: 3461e22de7c0a93520823ae23228e4ef
Blind packet: D:\OpenClaw-Backup\clawd\projects\smart-energy-ai\.desloppify\review_packet_blind.json
Template output: D:\OpenClaw-Backup\clawd\projects\smart-energy-ai\.desloppify\external_review_sessions\ext_20260302_205239_8d5d346f\review_result.template.json
Claude launch prompt: D:\OpenClaw-Backup\clawd\projects\smart-energy-ai\.desloppify\external_review_sessions\ext_20260302_205239_8d5d346f\claude_launch_prompt.md
Expected reviewer output: D:\OpenClaw-Backup\clawd\projects\smart-energy-ai\.desloppify\external_review_sessions\ext_20260302_205239_8d5d346f\review_result.json

Happy path:
1. Open the Claude launch prompt file and paste it into a context-isolated subagent task.
2. Reviewer writes JSON output to the expected reviewer output path.
3. Submit with the printed --external-submit command.

Reviewer output requirements:
1. Return JSON with top-level keys: session, assessments, findings.
2. session.id must be `ext_20260302_205239_8d5d346f`.
3. session.token must be `3461e22de7c0a93520823ae23228e4ef`.
4. Include findings with required schema fields (dimension/identifier/summary/related_files/evidence/suggestion/confidence).
5. Use the blind packet only (no score targets or prior context).
