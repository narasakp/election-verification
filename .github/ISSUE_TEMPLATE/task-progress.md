---
name: Task Progress
about: Track progress of the six high-priority workstreams for election-verification.
title: "[Task] ..."
labels: [task, priority]
assignees: []
---

## High-level plan
- [ ] Data integrity + cross-ref
- [ ] Postprocess + validation
- [ ] Review throughput
- [ ] CI/CD/ops
- [ ] Roadmap/docs
- [ ] Cost/perf metrics

## Data integrity + cross-ref
- [ ] verify `drive_index_*` vs `ocr_multimodel_*`
- [ ] rerun cross-reference script
- [ ] generate missing coverage report

## Postprocess + validation
- [ ] run postprocess pipeline (R0..R9)
- [ ] run validation rules (V1..V11)
- [ ] create regression tests

## Review throughput
- [ ] build priority queue feature
- [ ] implement auto-approve low-risk
- [ ] monitor backlog metrics

## CI/CD/ops
- [ ] add workflows, lint, tests
- [ ] add nightly smoke test
- [ ] add environment/key checks

## Cost/perf metrics
- [ ] add cost report script
- [ ] add performance report, global summary
- [ ] present key metrics in docs

## Done: notes / blockers

