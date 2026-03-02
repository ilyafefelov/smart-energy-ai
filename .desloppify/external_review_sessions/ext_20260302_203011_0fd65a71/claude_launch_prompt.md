# Claude Blind Reviewer Launch Prompt

You are an isolated blind reviewer. Do not use prior chat context, prior score history, or target-score anchoring.

Blind packet: D:\OpenClaw-Backup\clawd\projects\smart-energy-ai\.desloppify\review_packet_blind.json
Template JSON: D:\OpenClaw-Backup\clawd\projects\smart-energy-ai\.desloppify\external_review_sessions\ext_20260302_203011_0fd65a71\review_result.template.json
Output JSON path: D:\OpenClaw-Backup\clawd\projects\smart-energy-ai\.desloppify\external_review_sessions\ext_20260302_203011_0fd65a71\review_result.json

Requirements:
1. Read ONLY the blind packet and repository code.
2. Start from the template JSON so `session.id` and `session.token` are preserved.
3. Keep `session.id` exactly `ext_20260302_203011_0fd65a71`.
4. Keep `session.token` exactly `40041a1d69fc6a30446098d0ee5b7aa9`.
5. Output must be valid JSON with top-level keys: session, assessments, findings.
6. Every finding must include: dimension, identifier, summary, related_files, evidence, suggestion, confidence.
7. Do not include provenance metadata (CLI injects canonical provenance).
8. Return JSON only (no markdown fences).
