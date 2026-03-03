# External Blind Review Session

Session id: ext_20260302_232715_1da62dda
Session token: 8ead0e111ea1308c7f0c9cdc5462d358
Blind packet: D:\OpenClaw-Backup\clawd\projects\smart-energy-ai\.desloppify\review_packet_blind.json
Template output: D:\OpenClaw-Backup\clawd\projects\smart-energy-ai\.desloppify\external_review_sessions\ext_20260302_232715_1da62dda\review_result.template.json
Claude launch prompt: D:\OpenClaw-Backup\clawd\projects\smart-energy-ai\.desloppify\external_review_sessions\ext_20260302_232715_1da62dda\claude_launch_prompt.md
Expected reviewer output: D:\OpenClaw-Backup\clawd\projects\smart-energy-ai\.desloppify\external_review_sessions\ext_20260302_232715_1da62dda\review_result.json

Happy path:
1. Open the Claude launch prompt file and paste it into a context-isolated subagent task.
2. Reviewer writes JSON output to the expected reviewer output path.
3. Submit with the printed --external-submit command.

Reviewer output requirements:
1. Return JSON with top-level keys: session, assessments, findings.
2. session.id must be `ext_20260302_232715_1da62dda`.
3. session.token must be `8ead0e111ea1308c7f0c9cdc5462d358`.
4. Include findings with required schema fields (dimension/identifier/summary/related_files/evidence/suggestion/confidence).
5. Use the blind packet only (no score targets or prior context).
