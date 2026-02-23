# Filings Scoring Prompt

You are scoring {COMPANY_NAME} ({TICKER}) on "roundaboutness" based on SEC filings evidence.

Below is evidence extracted from filings dated {DATES}:

{PASTE PASS 1 OUTPUT HERE}

---

## SCORING RUBRIC (-2 to +2 scale)

### DIMENSION 1: Capital Allocation Track Record
| Score | Criteria |
|-------|----------|
| +2 | Capex/Revenue stable or growing; acquisitions with clear strategic fit; depreciation < capex (investing mode); stated framework prioritizes long-term returns |
| +1 | Above-maintenance capex; reasonable acquisition history; some long-term focus |
| 0 | Maintenance-level investment; standard corporate behavior |
| -1 | Capex declining; acquisitions look like financial engineering; under-investing |
| -2 | Clear harvesting; depreciation >> capex; serial dilutive acquisitions |

### DIMENSION 2: R&D Intensity and Consistency
| Score | Criteria |
|-------|----------|
| +2 | R&D/Revenue above industry average AND stable/growing over 5 years; clear roadmap |
| +1 | Above-average R&D with reasonable consistency |
| 0 | Industry-average R&D; maintenance R&D |
| -1 | Below-average or declining R&D trend |
| -2 | Minimal R&D; clearly harvesting existing products/IP |

### DIMENSION 3: Balance Sheet Strength
| Score | Criteria |
|-------|----------|
| +2 | Net cash position or Debt/EBITDA < 1x; ample covenant headroom; no near-term maturities |
| +1 | Moderate leverage (1-2x); comfortable liquidity; no refinancing risk |
| 0 | Industry-average leverage (2-3x); adequate but not exceptional |
| -1 | Elevated leverage (3-4x); tightening covenants; near-term maturities |
| -2 | High leverage (>4x); covenant risk; refinancing needs in stressed market |

### DIMENSION 4: Compensation Alignment
| Score | Criteria |
|-------|----------|
| +2 | Long-term metrics (≥3 year) dominate comp; ROIC/TSR focus; CEO owns >3x salary in stock; clawbacks robust |
| +1 | Mix of short and long-term; some ROIC component; meaningful ownership |
| 0 | Standard comp structure; 1-year performance + 3-year cliff vesting |
| -1 | Revenue/EPS growth focus; short vesting; low ownership requirements |
| -2 | Aggressive stock option grants; guaranteed bonuses; no real alignment |

### DIMENSION 5: Insider Ownership and Behavior
| Score | Criteria |
|-------|----------|
| +2 | Insiders own >5% aggregate; net buyers over past 3 years; founder/family involvement |
| +1 | Meaningful insider ownership (2-5%); no significant selling |
| 0 | Typical institutional management (~1%); mixed insider transactions |
| -1 | Low insider ownership; net sellers; heavy 10b5-1 selling |
| -2 | Minimal ownership; aggressive selling; signs of extraction |

### DIMENSION 6: Related Party Cleanliness
| Score | Criteria |
|-------|----------|
| +2 | No material related party transactions; clean governance structure |
| +1 | Minimal, clearly disclosed, arm's-length related party activity |
| 0 | Some related party activity but appears standard |
| -1 | Elevated related party transactions; some questionable arrangements |
| -2 | Significant related party transactions; unclear business rationale; governance concerns |

### DIMENSION 7: Competitive Position Evidence
| Score | Criteria |
|-------|----------|
| +2 | Clear moat articulated and supported by data (customer retention >90%, long contracts, high switching costs); low customer concentration |
| +1 | Some moat evidence; reasonable competitive position |
| 0 | Standard competitive position; some concentration risk |
| -1 | Weakening position; high customer concentration; commoditizing |
| -2 | No moat evidence; high customer churn; losing market share |

### DIMENSION 8: Accounting Quality
| Score | Criteria |
|-------|----------|
| +2 | Conservative policies; clean audit opinion; no material weaknesses; stable policies over time |
| +1 | Reasonable policies; clean audit; minor estimate changes |
| 0 | Standard GAAP; typical estimates and judgments |
| -1 | Aggressive revenue recognition; policy changes that boost earnings; auditor commentary |
| -2 | Material weaknesses; auditor qualification; restatements; accounting complexity |

---

## OUTPUT FORMAT:

For each dimension, provide:
1. **Score**: [-2 to +2]
2. **Key Evidence**: Specific data points or quotes from filings
3. **Reasoning**: 2-3 sentences explaining the score

Then provide:
- **TOTAL SCORE**: Sum of all 8 dimensions (range: -16 to +16)
- **DECISION**:
  - ≥ +5: PASS (proceed to position sizing)
  - +1 to +4: WATCH (needs monitoring, potential add on weakness)
  - ≤ 0: FAIL (disqualify)
- **RED FLAGS**: Specific concerns from the filings
- **GOVERNANCE NOTES**: Any unusual board structure, voting rights, or control issues
- **CROSS-CHECK WITH TRANSCRIPT**: Note any contradictions between filing data and management's spoken commentary