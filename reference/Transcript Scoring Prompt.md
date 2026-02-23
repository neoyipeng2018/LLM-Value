# Transcript Scoring Prompt

You are scoring {COMPANY_NAME} ({TICKER}) on "roundaboutness"—the degree to which management demonstrates long-term, Austrian economics-style "roundabout" capital allocation thinking vs. short-term optimization.

Below is evidence extracted from the earnings call dated {DATE}:

{PASTE PASS 1 OUTPUT HERE}

---

## SCORING RUBRIC (-2 to +2 scale)

### DIMENSION 1: Capital Allocation Time Horizon
| Score | Criteria |
|-------|----------|
| +2 | Explicitly discusses 5-10+ year payback periods; willing to miss quarterly estimates for long-term investments; guidance philosophy emphasizes direction over precision |
| +1 | References multi-year investments; some tolerance for short-term pain; moderate long-term framing |
| 0 | Mixed signals or insufficient evidence; standard corporate speak |
| -1 | Heavy emphasis on quarterly/annual targets; reactive capital allocation; short guidance windows |
| -2 | Explicitly optimizing for next quarter; changing strategy based on stock price; short-term activist appeasement |

### DIMENSION 2: R&D and Reinvestment Philosophy
| Score | Criteria |
|-------|----------|
| +2 | Sustained high R&D/revenue with clear multi-year roadmap; building proprietary capabilities; willing to fund projects with uncertain but large payoffs |
| +1 | Above-average reinvestment with some long-term projects; building internal capabilities |
| 0 | Industry-average R&D; maintenance-level reinvestment |
| -1 | Cutting R&D to meet near-term targets; outsourcing core capabilities |
| -2 | Harvesting mode; minimal reinvestment; prioritizing extraction over building |

### DIMENSION 3: Debt and Financial Conservatism  
| Score | Criteria |
|-------|----------|
| +2 | Net cash or minimal debt; explicit fortress balance sheet philosophy; rejects leverage for "efficiency" |
| +1 | Conservative leverage with ample headroom; prioritizes debt paydown |
| 0 | Industry-average leverage; standard capital structure |
| -1 | Elevated leverage; borrowing for buybacks; tight covenants |
| -2 | Aggressive leverage; financial engineering focus; distressed balance sheet |

### DIMENSION 4: Owner-Operator Alignment
| Score | Criteria |
|-------|----------|
| +2 | Significant insider ownership (>5%); executives buying shares; comp tied to 5+ year metrics; founder-led |
| +1 | Meaningful insider stakes; long-term incentive plans; executives holding not selling |
| 0 | Standard institutional management; typical comp structure |
| -1 | Executives selling; option-heavy comp with short vesting; misaligned incentives |
| -2 | Serial insider selling; golden parachutes; extracted value from company |

### DIMENSION 5: Durability vs. Growth Language
| Score | Criteria |
|-------|----------|
| +2 | Primarily discusses moats, retention, sustainability; "survive and thrive through cycles"; downplays growth rate |
| +1 | Balance of durability and growth; references competitive advantages |
| 0 | Standard growth-focused corporate communication |
| -1 | Growth-at-all-costs rhetoric; market share obsession; competitive position secondary |
| -2 | Promotional/hype language; "disrupt or be disrupted" without substance; growth without profitability defense |

### DIMENSION 6: Counter-Cyclical Signals
| Score | Criteria |
|-------|----------|
| +2 | Evidence of investing during downturns; explicit counter-cyclical philosophy; holding capacity for optionality |
| +1 | Some counter-cyclical actions; maintaining investment through soft periods |
| 0 | Pro-cyclical but not aggressively so; standard corporate behavior |
| -1 | Cutting during downturns; reactive to cycle; following herd |
| -2 | Panic mode in downturns; aggressive cost-cutting that impairs long-term; selling assets at bottoms |

### DIMENSION 7: Stakeholder Patience Cultivation
| Score | Criteria |
|-------|----------|
| +2 | Actively pushes back on short-term analyst questions; explicitly tries to attract long-term shareholders; discourages quarterly focus |
| +1 | Some redirection to long-term metrics; mild pushback on short-termism |
| 0 | Standard analyst relations; answers questions as asked |
| -1 | Caters to short-term focused investors; provides excessive quarterly detail |
| -2 | Manages to analyst expectations; stock-price-driven communication |

---

## OUTPUT FORMAT:

For each dimension, provide:
1. **Score**: [-2 to +2]
2. **Key Evidence**: 1-2 most relevant quotes from the extraction
3. **Reasoning**: 2-3 sentences explaining the score

Then provide:
- **TOTAL SCORE**: Sum of all 7 dimensions (range: -14 to +14)
- **DECISION**: 
  - ≥ +4: PASS (add to watchlist for filing review)
  - 0 to +3: WATCH (needs more evidence, check filings carefully)
  - < 0: FAIL (disqualify)
- **KEY CONCERNS**: Any red flags or contradictions noted
- **TEMPORAL COMPARISON NOTE**: If you have access to prior transcripts, note any concerning changes in language or philosophy