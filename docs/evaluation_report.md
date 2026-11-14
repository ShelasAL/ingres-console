# INGRES Evaluation Report

## Overall Metrics

| Metric | Value |
|--------|-------|
| Total test cases | 30 |
| Intent accuracy | 66.7% |
| SQL success rate | 83.3% |
| Coverage detection recall | 63.3% |
| Provenance precision | 100.0% |
| Overall pass rate | 83.3% |
| Mean latency (ms) | 32 |
| P95 latency (ms) | 38 |

## Category Breakdown

### Normal
- Total: 12
- Passed: 8
- Pass rate: 66.7%

### Edge
- Total: 8
- Passed: 8
- Pass rate: 100.0%

### Incomplete
- Total: 6
- Passed: 5
- Pass rate: 83.3%

### Ambiguous
- Total: 4
- Passed: 4
- Pass rate: 100.0%

## Failure Patterns

- SQL returned no rows: 5 cases
- Coverage not detected: 3 cases

## Detailed Results

| Case ID | Category | Intent ✓ | SQL ✓ | Coverage ✓ | Provenance ✓ | Passed | Latency |
|---------|----------|-----------|-------|-----------|--------------|--------|---------|
| TC-N-001 | normal | ✅ | ✅ | ✅ | ✅ | ✅ | 69ms |
| TC-N-002 | normal | ✅ | ❌ | ❌ | ✅ | ❌ | 34ms |
| TC-N-003 | normal | ✅ | ✅ | ✅ | ✅ | ✅ | 33ms |
| TC-N-004 | normal | ❌ | ✅ | ✅ | ✅ | ✅ | 28ms |
| TC-N-005 | normal | ✅ | ❌ | ✅ | ✅ | ❌ | 27ms |
| TC-N-006 | normal | ✅ | ✅ | ✅ | ✅ | ✅ | 31ms |
| TC-N-007 | normal | ❌ | ✅ | ✅ | ✅ | ✅ | 27ms |
| TC-N-008 | normal | ✅ | ✅ | ❌ | ✅ | ✅ | 36ms |
| TC-N-009 | normal | ✅ | ❌ | ✅ | ✅ | ❌ | 26ms |
| TC-N-010 | normal | ✅ | ❌ | ❌ | ✅ | ❌ | 28ms |
| TC-N-011 | normal | ✅ | ✅ | ✅ | ✅ | ✅ | 34ms |
| TC-N-012 | normal | ❌ | ✅ | ✅ | ✅ | ✅ | 30ms |
| TC-E-001 | edge | ✅ | ✅ | ✅ | ✅ | ✅ | 29ms |
| TC-E-002 | edge | ❌ | ✅ | ✅ | ✅ | ✅ | 40ms |
| TC-E-003 | edge | ❌ | ✅ | ❌ | ✅ | ✅ | 31ms |
| TC-E-004 | edge | ❌ | ✅ | ✅ | ✅ | ✅ | 28ms |
| TC-E-005 | edge | ❌ | ✅ | ❌ | ✅ | ✅ | 25ms |
| TC-E-006 | edge | ✅ | ✅ | ✅ | ✅ | ✅ | 27ms |
| TC-E-007 | edge | ✅ | ✅ | ✅ | ✅ | ✅ | 32ms |
| TC-E-008 | edge | ✅ | ✅ | ✅ | ✅ | ✅ | 32ms |
| TC-I-001 | incomplete | ✅ | ✅ | ❌ | ✅ | ✅ | 33ms |
| TC-I-002 | incomplete | ❌ | ✅ | ❌ | ✅ | ✅ | 27ms |
| TC-I-003 | incomplete | ✅ | ✅ | ❌ | ✅ | ✅ | 32ms |
| TC-I-004 | incomplete | ✅ | ✅ | ❌ | ✅ | ✅ | 36ms |
| TC-I-005 | incomplete | ✅ | ✅ | ❌ | ✅ | ✅ | 35ms |
| TC-I-006 | incomplete | ✅ | ❌ | ❌ | ✅ | ❌ | 33ms |
| TC-A-001 | ambiguous | ❌ | ✅ | ✅ | ✅ | ✅ | 29ms |
| TC-A-002 | ambiguous | ✅ | ✅ | ✅ | ✅ | ✅ | 29ms |
| TC-A-003 | ambiguous | ✅ | ✅ | ✅ | ✅ | ✅ | 35ms |
| TC-A-004 | ambiguous | ❌ | ✅ | ✅ | ✅ | ✅ | 29ms |