# Transcript Evidence Extraction Prompt

You are analyzing an earnings call transcript for {COMPANY_NAME} ({TICKER}) dated {DATE}.

Extract VERBATIM quotes (with speaker attribution) that are relevant to the following categories. Do NOT interpret or score—only extract. If no relevant quotes exist for a category, state "No relevant evidence found."

---

### CATEGORY 1: Capital Allocation Time Horizon
Look for statements about:
- Investment payback periods mentioned (quarters vs. years)
- Willingness to sacrifice short-term results for long-term positioning
- Guidance philosophy (tight quarterly targets vs. long-term compounding)
- M&A rationale (synergies timeline, integration horizons)
- Capacity/capex investments and expected return timelines

### CATEGORY 2: R&D and Reinvestment Philosophy
Look for statements about:
- R&D spending rationale and expected outcomes
- Internal capability building vs. outsourcing
- Technology/infrastructure investments
- Training and human capital development
- Patents, IP, or proprietary process development

### CATEGORY 3: Debt and Financial Conservatism
Look for statements about:
- Leverage philosophy and target ratios
- Cash deployment priorities
- Buyback vs. debt paydown decisions
- Liquidity buffer philosophy
- Covenant headroom discussions

### CATEGORY 4: Owner-Operator Alignment
Look for statements about:
- Executive stock ownership (buying vs. selling)
- Compensation structure discussions
- Insider alignment with shareholders
- "We eat our own cooking" type statements
- Long-term incentive plan details

### CATEGORY 5: Durability vs. Growth Language
Look for statements about:
- Competitive moat discussions
- Customer retention/stickiness metrics
- Pricing power evidence
- "Sustainable" vs. "accelerate growth" framing
- Market share defense vs. expansion rhetoric

### CATEGORY 6: Counter-Cyclical Behavior
Look for statements about:
- Actions during downturns (hiring when others fire, investing when others cut)
- Opportunistic M&A during market stress
- Maintaining long-term investments despite short-term pressure
- Willingness to hold excess capacity/inventory

### CATEGORY 7: Analyst Q&A Dynamics
Look for statements about:
- How management responds to short-term focused questions
- Pushback against quarterly thinking from analysts
- Redirection to long-term metrics
- Patience cultivation with the investor base

---

OUTPUT FORMAT:
For each category, provide:
- Direct quotes with speaker name and context
- Timestamp or section reference if available
- Note if the statement was in prepared remarks vs. Q&A

Do NOT provide any scoring, interpretation, or summary. Only extract.