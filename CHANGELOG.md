# Changelog

## P0 Stable Baseline — 2026-09-16

Commit: `ca5f3adb184575501c27746aee62aac68c12c3a3`

Baseline ổn định trước P1:

- Khắc phục xung đột corpus/audit với safe-action fallback.
- Hoàn thiện nhận diện DKX10/sang tên xe với dữ liệu tiếng Việt không dấu.
- Sửa precedence của clarification để không che demo/form hợp lệ.
- Khắc phục form-link secret/fallback production.
- Giữ nguyên Artifact Core 19 nguồn, memory, form generation, safe fallback và Zalo flow.

Validation:

- 164 tests PASS; 1 test skipped có chủ đích.
- 100.000 routing stress PASS.
- 10.000 retrieval/stress PASS.
- 10.000 audit PASS.
- AI Core CI #187 PASS.
- production-smoke PASS.
- Official Go-Live Gate #32 PASS.
