# Architecture Improvement Plans

Implementation plans for the outstanding recommendations from `docs/ARCHITECTURE_REVIEW.md`.

---

## Quick Reference

| # | Plan | Priority | Effort | Status |
|---|------|----------|--------|--------|
| 1 | [Split Prompts for Cloud/Local](./plan_01_split_prompts.md) | 🔴 High | Medium | Not Started |
| 2 | [Input Validation Layer](./plan_02_input_validation.md) | 🔴 High | Low | Not Started |
| 3 | [Retry Logic with Backoff](./plan_03_retry_logic.md) | 🔴 High | Low | Not Started |
| 4 | [Reasoning Context Preservation](./plan_04_reasoning_context.md) | 🟡 Medium | Medium | Not Started |
| 5 | [Tool Description Examples](./plan_05_tool_examples.md) | 🟡 Medium | Low | Not Started |
| 6 | [Response Validation](./plan_06_response_validation.md) | 🟡 Medium | Medium | Not Started |

---

## Recommended Implementation Order

### Phase 1: Foundation (Do First)

These are **high priority, low effort** - quick wins that significantly improve robustness:

1. **Plan 02: Input Validation** - Prevents security issues, ~1 hour
2. **Plan 03: Retry Logic** - Prevents single-point failures, ~1 hour

### Phase 2: Core Improvements

These require more changes but have significant impact:

3. **Plan 01: Split Prompts** - Better model-specific behavior, ~2-3 hours
4. **Plan 05: Tool Examples** - Better tool selection accuracy, ~1-2 hours

### Phase 3: Advanced Features

These add polish and efficiency:

5. **Plan 04: Reasoning Context** - Multi-turn coherence, ~3-4 hours
6. **Plan 06: Response Validation** - Catch hallucinations, ~2-3 hours

---

## Dependencies

```
Plan 02 (Input Validation)    ──────┐
                                    ├──► Can implement in any order
Plan 03 (Retry Logic)         ──────┘

Plan 01 (Split Prompts)       ──────┐
                                    ├──► Plan 04 can use provider-specific prompts
Plan 04 (Reasoning Context)   ◄─────┘

Plan 05 (Tool Examples)       ──────┐
                                    ├──► Plan 06 validates against tool schemas
Plan 06 (Response Validation) ◄─────┘
```

---

## Total Estimated Effort

| Category | Hours |
|----------|-------|
| High Priority (Plans 1-3) | 4-6 hours |
| Medium Priority (Plans 4-6) | 6-9 hours |
| **Total** | **10-15 hours** |

---

## Files Created/Modified Summary

### New Files

| File | Plan | Purpose |
|------|------|---------|
| `backend/security/__init__.py` | 02 | Security module init |
| `backend/security/guardrails.py` | 02 | Input validation |
| `backend/llm/reasoning_cache.py` | 04 | Reasoning preservation |
| `backend/llm/response_validator.py` | 06 | Response validation |
| `backend/tools/example_templates.py` | 05 | Tool example helpers |
| `prompts/cloud/openai.md` | 01 | Cloud reasoning prompt |
| `prompts/cloud/anthropic.md` | 01 | XML-tagged prompt for Claude |
| `prompts/local/ollama.md` | 01 | Condensed local prompt |

### Modified Files

| File | Plans | Changes |
|------|-------|---------|
| `backend/config.py` | 01, 02, 03, 04 | New config options |
| `backend/prompts.py` | 01 | Provider-aware loading |
| `backend/chat_service.py` | 02, 04 | Guardrails + session ID |
| `backend/llm/gluellm_wrapper.py` | 03, 04, 06 | Retry, reasoning, validation |
| `backend/llm/tool_adapter.py` | 05 | Include examples in docstrings |
| `backend/tools/schemas.py` | 05 | Add ToolExample class |
| `backend/diagnostics/__init__.py` | 05 | Add examples to tools |
| `pyproject.toml` | 03 | Add tenacity dependency |

---

## Tracking Progress

Update this section as plans are completed:

```
[ ] Plan 01: Split Prompts
[ ] Plan 02: Input Validation  
[ ] Plan 03: Retry Logic
[ ] Plan 04: Reasoning Context
[ ] Plan 05: Tool Examples
[ ] Plan 06: Response Validation
```

---

## Notes

- All plans include unit tests and integration test requirements
- Plans are designed to be implemented independently where possible
- Each plan has success criteria to verify completion
- Plans reference the original architecture review for context

---

*Generated from `docs/ARCHITECTURE_REVIEW.md` assessment on 2026-01-19*
