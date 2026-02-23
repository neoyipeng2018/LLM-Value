# Filings Evidence Extraction Prompt

You are analyzing SEC filings for {COMPANY_NAME} ({TICKER}). The documents include:
- 10-K Annual Report (FY{YEAR})
- Most recent 10-Q (if applicable)
- Proxy Statement/DEF 14A

Extract VERBATIM text and specific data points relevant to the following categories. Do NOT interpret or score. Reference the specific filing and section for each extract.

---

### CATEGORY 1: Capital Allocation History (from 10-K)
Extract from MD&A, Business section, and Cash Flow discussion:
- Historical capex as % of revenue (5-year trend if available)
- Acquisition spending and stated rationale
- Depreciation vs. capex ratio (maintenance vs. growth)
- Cash flow deployment priorities stated by management
- Any "capital allocation framework" discussions

### CATEGORY 2: R&D Investment (from 10-K)
Extract from financial statements and MD&A:
- R&D expense (absolute and % of revenue) for past 3-5 years
- Capitalized software/development costs
- Discussion of R&D priorities and outcomes
- Any R&D personnel or facility investments

### CATEGORY 3: Debt Structure and Covenants (from 10-K/10-Q)
Extract from Notes to Financial Statements:
- Total debt and debt maturity schedule
- Debt/EBITDA and interest coverage ratios
- Covenant terms and current headroom
- Credit facility details and availability
- Net cash/debt position

### CATEGORY 4: Executive Compensation (from Proxy/DEF 14A)
Extract from Compensation Discussion & Analysis:
- CEO and NEO total compensation breakdown
- Performance metric weightings (short-term vs. long-term)
- Vesting schedules for equity awards
- Stock ownership requirements
- Clawback provisions
- Any "realizable pay" vs. "reported pay" discussion

### CATEGORY 5: Insider Ownership (from Proxy)
Extract from Security Ownership section:
- Directors and officers beneficial ownership table
- Changes in insider ownership vs. prior year
- Insider transaction summary (buys vs. sells)
- 10b5-1 plan disclosures

### CATEGORY 6: Related Party Transactions (from Proxy and 10-K)
Extract from Related Party Transactions section:
- All disclosed related party transactions
- Amounts and nature of transactions
- Board approval process described
- Any unusual arrangements

### CATEGORY 7: Risk Factors and Competitive Position (from 10-K)
Extract from Risk Factors and Business sections:
- Top 3-5 risk factors by prominence
- Competitive advantage/moat descriptions
- Customer concentration data
- Contract length and renewal patterns
- Switching cost discussions

### CATEGORY 8: Accounting Policies and Estimates (from 10-K)
Extract from Critical Accounting Policies section:
- Revenue recognition policy details
- Key estimates and assumptions
- Any policy changes in the period
- Auditor's opinion (clean vs. qualified)
- Any material weaknesses in internal controls

### CATEGORY 9: Segment and Geographic Detail (from 10-K)
Extract from Notes to Financial Statements:
- Segment ROIC or margins if disclosed
- Geographic revenue breakdown
- Related party revenue as % of total
- Customer concentration metrics

---

OUTPUT FORMAT:
For each category:
- Provide verbatim extracts with section references
- Include specific numerical data points
- Note any disclosures that seem unusual or boilerplate
- Highlight any year-over-year changes if visible

Do NOT score or interpret. Only extract.