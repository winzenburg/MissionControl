# Cost Governance Framework

**Last Updated:** February 25, 2026  
**Status:** ACTIVE & ENFORCED  
**Priority:** CRITICAL (non-negotiable)

---

## Golden Rule

> **If the local model can do it, the local model does it. No exceptions.**

Every escalation to cloud APIs is a cost. Local Ollama models are free. The only reason to escalate is gate failure—not speed, not "safety feelings", not convenience.

---

## Seven Hard Rules (Non-Negotiable)

### Rule 1: Default to Local (Zero Cost)
- **Every task STARTS with Ollama** (qwen2.5:7b, llama3.1:8b, deepseek-coder:6.7b)
- Extract, classify, summarize, code review, planning, writing, refactoring → LOCAL FIRST
- "Try local first" is not a suggestion; it's the rule

**Cost impact:** $0 per task

### Rule 2: Escalation Only on Gate Failure
- If the local model produces a **VALID output** (schema correct, no contradictions, complete): STOP. Use it.
- If and **ONLY IF** gate check fails → escalate to Tier B
- If Tier B gate fails → escalate to Tier C
- **DO NOT escalate for speed, convenience, or "just to be safe"**

**Gate checks that matter:**
- ✅ schema_valid: output parses + contains required fields
- ✅ constraints_met: respects user constraints
- ✅ contradictions: no self-contradictions or misalignment
- ✅ tests_present: code changes include tests
- ✅ citations_if_web: web sources cited, no fabricated citations

### Rule 3: Every Escalation Requires Justification
- In ROUTE JSON, the `reason` field MUST explain why local was insufficient
- Examples of **VALID reasons**:
  - "Gate check failed: JSON schema violated"
  - "Output contradicts itself; needs human-level resolution"
  - "High-stakes financial decision requires Opus-level reasoning"
- Examples of **INVALID reasons**:
  - "Would be faster"
  - "Cloud model is 'safer'"
  - "Just to double-check"
  - "Might be better"

**Cost impact:** Escalation transparency required

### Rule 4: Transparent Cost Tracking
Every premium escalation (Tier B/C) is logged with:
- Task description
- Why local failed (gate check that failed)
- Model used
- Approximate cost (~$0.01-0.05 for Tier B, ~$0.10-0.50 for Tier C)

**Weekly cost report includes:**
- List of all escalations this week
- Total cloud spend
- % of time using local models (target: 80%+)
- Any patterns showing "lazy escalation" (to fix)
- Any tasks where local surprised us (to note for next time)

### Rule 5: Hard Monthly Budget (You Set This)
- **What's your monthly API budget?** (e.g., $50/month, $100/month, $500/month?)
- Once set, I will NOT exceed it without explicit approval
- When approaching limit (80%), I'll alert you and default harder to local models
- If I breach it, I stop premium escalations immediately and notify you

### Rule 6: Cron/Heartbeat = 100% Local
- Background jobs (cron, heartbeat, automated monitoring): **ALWAYS local only**
- **NO cloud escalation in automated runs**
- Return best local attempt + known gaps instead
- Cost: $0 (by definition)

### Rule 7: The "Coffee Test"
- Before escalating to cloud, ask: **"Is this worth the cost of a coffee?"** (~$0.10-0.50)
- If the answer is no, use the local model even if it's 70% confidence instead of 95%
- Speed and perfection are not worth spending real money on routine tasks

**Cost impact:** Filters out $0.05+ escalations for low-impact decisions

---

## Weekly Cost Review (Friday 2 PM MT)

Every Friday at 2 PM, I will provide:

1. **Escalation Log** — All premium model uses this week
   - Task description
   - Why local failed
   - Model used
   - Cost

2. **Cost Summary**
   - Total cloud spend
   - Number of escalations
   - % local vs. cloud usage

3. **Trend Analysis**
   - Are we staying 80%+ local?
   - Any pattern of lazy escalation?
   - Where did local surprise us?

4. **Next Week Forecast**
   - Projected spend based on task pipeline
   - Any adjustments needed

---

## Cost Impact Examples

| Scenario | Local Usage | Spend/Day | Spend/Month |
|----------|-------------|-----------|-------------|
| **80%+ local** | qwen2.5:7b default | ~$0.00 | ~$0 |
| **70% local** | Most tasks local, some escalations | ~$5-10 | ~$150-300 |
| **60% local** | Frequent mid-tier usage | ~$15-20 | ~$450-600 |
| **40% local** | Heavy cloud reliance | ~$30-50 | ~$900-1500 |

**Target:** Stay at 80%+ local to keep monthly cost near $0.

---

## What I Will NEVER Do

- ❌ Casually escalate to Claude/OpenAI "just in case"
- ❌ Use premium models for routine extraction/summaries
- ❌ Hide API costs in background runs
- ❌ Escalate in cron/heartbeat jobs
- ❌ Treat cloud APIs as "free" upgrades
- ❌ Exceed monthly budget without asking
- ❌ Continue spending if limit is breached (will alert immediately)

---

## What I WILL Do

- ✅ Try local first, always
- ✅ Justify every escalation in ROUTE JSON
- ✅ Track and report costs transparently every Friday
- ✅ Alert you immediately if spending gets out of control
- ✅ Respect your monthly budget as a hard ceiling
- ✅ Prefer local even at slightly lower confidence if it saves money
- ✅ Use cron/heartbeat as 100% local-only background work

---

## ROUTE JSON Format (Always Includes Cost)

```json
{
  "task_type": "extract",
  "risk_level": "low",
  "quality_bar": "solid",
  "initial_tier": "A",
  "selected_model": "qwen2.5:7b",
  "fallback_models": ["llama3.1:8b"],
  "escalation_allowed": false,
  "reason": "Routine extraction task. Local model meets quality bar (valid schema, no contradictions). Cost: $0.",
  "estimated_cost": "$0.00"
}
```

---

## How to Set Your Budget

Tell me:
1. **Monthly API budget** — How much should I spend? ($0, $50, $100, $500?)
2. **Alert threshold** — When should I warn you? (e.g., 80% of budget)

Once you provide these, I'll embed them in SOUL.md and enforce them strictly in every ROUTE decision.

---

## Questions?

This framework is designed to keep you in control while maximizing efficiency. If you have questions about when to escalate, what counts as gate failure, or how to set your budget, ask before I spend money. Better to clarify than to regret.

---

**Status:** ACTIVE & EMBEDDED in:
- SOUL.md (multi-model strategy)
- MEMORY.md (core principles)
- COST-GOVERNANCE.md (this file)
- ROUTE JSON (every decision)

**Review Schedule:** Weekly Friday 2 PM MT cost reports
**Contact:** Alert immediately if budget breached
