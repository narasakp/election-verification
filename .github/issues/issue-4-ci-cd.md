# Issue 4: CI/CD/ops

## Description
Set up comprehensive CI/CD pipeline with automated testing and deployment.

## Tasks
- [ ] Update `.github/workflows/ci.yml` with full test suite
- [ ] Add `npm test`, `pytest`, `lint`, `typecheck` to CI
- [ ] Add nightly smoke test (OCR sample → postprocess → validation)
- [ ] Add environment/key rotation checks
- [ ] Configure deployment health checks
- [ ] Add performance regression detection

## Acceptance Criteria
- CI passes on all PRs
- Nightly smoke tests run successfully
- Deployment includes health checks
- Performance regressions caught automatically

## Labels
infrastructure, ci-cd, devops, medium-priority