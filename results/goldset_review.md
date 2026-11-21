# Gold-set draft review sheet

130 draft items from `results/gold_set_draft.jsonl`, riskiest first: uncertain labels, then computed, cross-company, single-filing lookups/text, and unanswerable traps. Excerpts are windows of at most 300 characters around each label's first phrase (up to 2 matching chunks per label; the total match count is shown). Regenerate with `python scripts/check_gold_draft.py --review results/goldset_review.md`.

Reviewer checklist: the number or claim in the gold answer appears in the excerpt for the right period/column; computed items' arithmetic in Notes is right; trap notes show the filing really cannot answer. Mark OK / FIX in the box.

## fg-105 - business - hard (UNCERTAIN LABEL)

- [ ] **Q:** What major gain and charge related to bottling and investee transactions did Coca-Cola record in other income (loss) in 2025?
- **Tickers:** KO
- **Gold answer:** It recognized a $1,952 million gain on the sale of its ownership interest in Coca-Cola Consolidated, and recorded a $1,274 million charge related to its bottling operations in Africa that became held for sale.
- **Label 1** (KO, verified, 1 matching chunk(s)): `gain of $1,952 million related to the sale of our ownership interest in Coca-Cola Consolidated`
  - `KO-10-K-2026-c0124`: "(Loss) — Net In 2025, other income (loss) — net was income of $1,073 million. The Company recognized a gain of $1,952 million related to the sale of our ownership interest in Coca-Cola Consolidated, Inc. (“Coke Consolidated”), an equity method investee, a net gain of $409 million related to realized"
- **Label 2** (KO, verified, uncertain, 2 matching chunk(s)): `charge of $1,274 million related to our bottling operations in Africa that became held for sale`
  - note: Matched chunks (c0125, c0264) do not themselves say 2025; the year comes from the preceding sentence 'In 2025, other income (loss) - net was income of $1,073 million' in c0124. Confirm the paragraph is the 2025 one.
  - `KO-10-K-2026-c0125`: "llion related to the substantial liquidation of a joint venture in China. The Company also recorded a charge of $1,274 million related to our bottling operations in Africa that became held for sale, a charge of $393 million related to the sale of our finished product operations in Nigeria, and other"
  - `KO-10-K-2026-c0264`: "llion related to the substantial liquidation of a joint venture in China. The Company also recorded a charge of $ 1,274 million related to our bottling operations in Africa that became held for sale, a charge of $ 393 million related to the sale of our finished product operations in Nigeria, and oth"

## fg-061 - computed - medium

- [ ] **Q:** By what percentage did Apple's Services net sales grow in fiscal 2025 versus fiscal 2024? Round to one decimal place.
- **Tickers:** AAPL
- **Gold answer:** About 13.5%: Services net sales rose from $96,169 million to $109,158 million (the filing's table rounds this to 14%).
- **Notes:** (109,158 - 96,169) / 96,169 = 12,989 / 96,169 = 13.51% -> 13.5% (rounded to 1 dp). Filing shows 14% (whole-number rounding).
- **Label 1** (AAPL, verified, 1 matching chunk(s)): `Services 109,158 96,169`
  - `AAPL-10-K-2025-c0062`: "eptember 28, 2024 \| September 30, 2023 \| \| --- \| --- \| --- \| --- \| \| Net sales: \| \| \| \| \| Products \| $307,003 \| $294,866 \| $298,085 \| \| Services \| 109,158 \| 96,169 \| 85,200 \| \| Total net sales \| 416,161 \| 391,035 \| 383,285 \| \| Cost of sales: \| \| \| \| \| Products \| 194,116 \| 185,233 \| 189,282 \| \| Servi"

## fg-062 - computed - medium

- [ ] **Q:** What was Apple's gross margin percentage for fiscal 2025 (gross margin divided by total net sales)? Round to one decimal place.
- **Tickers:** AAPL
- **Gold answer:** About 46.9%: gross margin of $195,201 million on total net sales of $416,161 million.
- **Notes:** 195,201 / 416,161 = 46.905% -> 46.9% (rounded to 1 dp).
- **Label 1** (AAPL, verified, 2 matching chunk(s)): `Gross margin 195,201 180,683`
  - `AAPL-10-K-2025-c0052`: "\| --- \| --- \| \| Gross margin: \| \| \| \| \| Products \| $112,887 \| $109,633 \| $108,803 \| \| Services \| 82,314 \| 71,050 \| 60,345 \| \| Total gross margin \| $195,201 \| $180,683 \| $169,148 \| \| Gross margin percentage: \| \| \| \| \| --- \| --- \| --- \| --- \| \| Products \| 36.8% \| 37.2% \| 36.5% \| \| Services \| 75.4% \|"
  - `AAPL-10-K-2025-c0062`: "ducts \| 194,116 \| 185,233 \| 189,282 \| \| Services \| 26,844 \| 25,119 \| 24,855 \| \| Total cost of sales \| 220,960 \| 210,352 \| 214,137 \| \| Gross margin \| 195,201 \| 180,683 \| 169,148 \| \| Operating expenses: \| \| \| \| \| Research and development \| 34,550 \| 31,370 \| 29,915 \| \| Selling, general and administrati"
- **Label 2** (AAPL, verified, 3 matching chunk(s)): `Total net sales 416,161 391,035`
  - `AAPL-10-K-2025-c0062`: "- \| --- \| --- \| --- \| \| Net sales: \| \| \| \| \| Products \| $307,003 \| $294,866 \| $298,085 \| \| Services \| 109,158 \| 96,169 \| 85,200 \| \| Total net sales \| 416,161 \| 391,035 \| 383,285 \| \| Cost of sales: \| \| \| \| \| Products \| 194,116 \| 185,233 \| 189,282 \| \| Services \| 26,844 \| 25,119 \| 24,855 \| \| Total cost"
  - `AAPL-10-K-2025-c0073`: "\| 26,694 \| 28,300 \| \| Wearables, Home and Accessories \| 35,686 \| 37,005 \| 39,845 \| \| Services (1) \| 109,158 \| 96,169 \| 85,200 \| \| Total net sales \| $416,161 \| $391,035 \| $383,285 \| \| Portion of total net sales that was included in deferred revenue as of the beginning of the period \| $8,229 \| $7,728"

## fg-063 - computed - medium

- [ ] **Q:** By what percentage did Apple's net income change from fiscal 2024 to fiscal 2025? Round to one decimal place.
- **Tickers:** AAPL
- **Gold answer:** Net income rose about 19.5%, from $93,736 million to $112,010 million.
- **Notes:** (112,010 - 93,736) / 93,736 = 18,274 / 93,736 = 19.495% -> 19.5% (rounded to 1 dp).
- **Label 1** (AAPL, verified, 5 matching chunk(s)): `Net income $112,010 $93,736`
  - `AAPL-10-K-2025-c0062`: "Income before provision for income taxes \| 132,729 \| 123,485 \| 113,736 \| \| Provision for income taxes \| 20,719 \| 29,749 \| 16,741 \| \| Net income \| $112,010 \| $93,736 \| $96,995 \| \| Earnings per share: \| \| \| \| \| Basic \| $7.49 \| $6.11 \| $6.16 \| \| Diluted \| $7.46 \| $6.08 \| $6.13 \| \| Shares used in compu"
  - `AAPL-10-K-2025-c0063`: "NSIVE INCOME (In millions) \| \| Years ended September 27, 2025 \| September 28, 2024 \| September 30, 2023 \| \| --- \| --- \| --- \| --- \| \| Net income \| $112,010 \| $93,736 \| $96,995 \| \| Other comprehensive income/(loss): \| \| \| \| \| Change in foreign currency translation, net of tax \| (267) \| 395 \| (765) \|"

## fg-064 - computed - hard

- [ ] **Q:** What was the operating margin of Microsoft's Intelligent Cloud segment in fiscal year 2026? Round to one decimal place.
- **Tickers:** MSFT
- **Gold answer:** About 41.3%: segment operating income of $56,972 million on revenue of $137,791 million.
- **Notes:** 56,972 / 137,791 = 41.347% -> 41.3% (rounded to 1 dp). Both rows are in the Intelligent Cloud block of the segment results table.
- **Label 1** (MSFT, verified, 2 matching chunk(s)): `Revenue $137,791 $106,265` + `Operating income $56,972 $44,589`
  - `MSFT-10-K-2026-c0071`: "422 \| 12% \| \| Operating expenses \| 31,100 \| 28,615 \| 9% \| \| Operating income \| $83,879 \| $69,773 \| 20% \| \| Intelligent Cloud \| \| \| \| \| Revenue \| $137,791 \| $106,265 \| 30% \| \| Cost of revenue \| 57,876 \| 40,171 \| 44% \| \| Operating expenses \| 22,943 \| 21,505 \| 7% \| \| Operating income \| $56,972 \| $44,58"
  - `MSFT-10-K-2026-c0154`: "1 \| \| Operating expenses \| 31,100 \| 28,615 \| 27,548 \| \| Operating income \| $83,879 \| $69,773 \| $59,661 \| \| Intelligent Cloud \| \| \| \| \| Revenue \| $137,791 \| $106,265 \| $87,464 \| \| Cost of revenue \| 57,876 \| 40,171 \| 29,611 \| \| Operating expenses \| 22,943 \| 21,505 \| 20,040 \| \| Operating income \| $56,9"

## fg-065 - computed - medium

- [ ] **Q:** What was Microsoft's effective tax rate for fiscal year 2026, computed as provision for income taxes divided by income before income taxes? Round to one decimal place.
- **Tickers:** MSFT
- **Gold answer:** About 19.4%: provision for income taxes of $32,185 million on income before income taxes of $165,934 million.
- **Notes:** 32,185 / 165,934 = 19.396% -> 19.4% (rounded to 1 dp).
- **Label 1** (MSFT, verified, 2 matching chunk(s)): `Income before income taxes 165,934` + `Provision for income taxes 32,185`
  - `MSFT-10-K-2026-c0092`: "\| 7,223 \| 7,609 \| \| Operating income \| 155,237 \| 128,528 \| 109,433 \| \| Other income (expense), net \| 10,697 \| (4,901) \| (1,646) \| \| Income before income taxes \| 165,934 \| 123,627 \| 107,787 \| \| Provision for income taxes \| 32,185 \| 21,795 \| 19,651 \| \| Net income \| $133,749 \| $101,832 \| $88,136 \| \| Ea"
  - `MSFT-10-K-2026-c0134`: "-- \| \| Year Ended June 30, \| 2026 \| 2025 \| 2024 \| \| U.S. \| $103,591 \| $69,212 \| $62,886 \| \| Foreign \| 62,343 \| 54,415 \| 44,901 \| \| Income before income taxes \| $165,934 \| $123,627 \| $107,787 \| 73 PART II Item 8 Effective Tax Rate We adopted Accounting Standards Update 2023-09, Income Taxes (Topic 74"

## fg-066 - computed - hard

- [ ] **Q:** How much larger was revenue in Microsoft's Productivity and Business Processes segment than in its Intelligent Cloud segment in fiscal year 2026?
- **Tickers:** MSFT
- **Gold answer:** Productivity and Business Processes revenue ($139,996 million) exceeded Intelligent Cloud revenue ($137,791 million) by $2,205 million.
- **Notes:** 139,996 - 137,791 = 2,205 ($ millions).
- **Label 1** (MSFT, verified, 2 matching chunk(s)): `Revenue $139,996 $120,810`
  - `MSFT-10-K-2026-c0071`: "ons, except percentages) \| 2026 \| 2025 \| Percentage Change \| \| --- \| --- \| --- \| --- \| \| Productivity and Business Processes \| \| \| \| \| Revenue \| $139,996 \| $120,810 \| 16% \| \| Cost of revenue \| 25,017 \| 22,422 \| 12% \| \| Operating expenses \| 31,100 \| 28,615 \| 9% \| \| Operating income \| $83,879 \| $69,77"
  - `MSFT-10-K-2026-c0154`: "llions) \| \| \| \| \| --- \| --- \| --- \| --- \| \| Year Ended June 30, \| 2026 \| 2025 \| 2024 \| \| Productivity and Business Processes \| \| \| \| \| Revenue \| $139,996 \| $120,810 \| $106,820 \| \| Cost of revenue \| 25,017 \| 22,422 \| 19,611 \| \| Operating expenses \| 31,100 \| 28,615 \| 27,548 \| \| Operating income \| $83,"
- **Label 2** (MSFT, verified, 2 matching chunk(s)): `Revenue $137,791 $106,265`
  - `MSFT-10-K-2026-c0071`: "422 \| 12% \| \| Operating expenses \| 31,100 \| 28,615 \| 9% \| \| Operating income \| $83,879 \| $69,773 \| 20% \| \| Intelligent Cloud \| \| \| \| \| Revenue \| $137,791 \| $106,265 \| 30% \| \| Cost of revenue \| 57,876 \| 40,171 \| 44% \| \| Operating expenses \| 22,943 \| 21,505 \| 7% \| \| Operating income \| $56,972 \| $44,58"
  - `MSFT-10-K-2026-c0154`: "1 \| \| Operating expenses \| 31,100 \| 28,615 \| 27,548 \| \| Operating income \| $83,879 \| $69,773 \| $59,661 \| \| Intelligent Cloud \| \| \| \| \| Revenue \| $137,791 \| $106,265 \| $87,464 \| \| Cost of revenue \| 57,876 \| 40,171 \| 29,611 \| \| Operating expenses \| 22,943 \| 21,505 \| 20,040 \| \| Operating income \| $56,9"

## fg-067 - computed - medium

- [ ] **Q:** What was the AWS segment's operating margin in 2025? Round to one decimal place.
- **Tickers:** AMZN
- **Gold answer:** About 35.4%: AWS operating income of $45,606 million on AWS net sales of $128,725 million.
- **Notes:** 45,606 / 128,725 = 35.429% -> 35.4% (rounded to 1 dp).
- **Label 1** (AMZN, verified, 1 matching chunk(s)): `AWS 107,556 128,725`
  - `AMZN-10-K-2026-c0054`: "31, 2024 \| 2025 \| \| --- \| --- \| --- \| \| Net Sales: \| \| \| \| North America \| $387,497 \| $426,305 \| \| International \| 142,906 \| 161,894 \| \| AWS \| 107,556 \| 128,725 \| \| Consolidated \| $637,959 \| $716,924 \| \| Year-over-year Percentage Growth: \| \| \| \| North America \| 10% \| 10% \| \| International \| 9 \| 13"
- **Label 2** (AMZN, verified, 1 matching chunk(s)): `AWS 39,834 45,606`
  - `AMZN-10-K-2026-c0060`: "r 31, 2024 \| 2025 \| \| --- \| --- \| --- \| \| Operating Income \| \| \| \| North America \| $24,967 \| $29,619 \| \| International \| 3,792 \| 4,750 \| \| AWS \| 39,834 \| 45,606 \| \| Consolidated \| $68,593 \| $79,975 \| Operating income was $68.6 billion and $80.0 billion for 2024 and 2025. Operating income for 2025 in"

## fg-068 - computed - medium

- [ ] **Q:** By what percentage did Amazon's net income grow from 2024 to 2025? Round to one decimal place.
- **Tickers:** AMZN
- **Gold answer:** About 31.1%, from $59,248 million in 2024 to $77,670 million in 2025.
- **Notes:** (77,670 - 59,248) / 59,248 = 18,422 / 59,248 = 31.093% -> 31.1% (rounded to 1 dp).
- **Label 1** (AMZN, verified, 4 matching chunk(s)): `Net income $30,425 $59,248 $77,670`
  - `AMZN-10-K-2026-c0074`: "CASH, CASH EQUIVALENTS, AND RESTRICTED CASH, BEGINNING OF PERIOD \| $54,253 \| $73,890 \| $82,312 \| \| OPERATING ACTIVITIES: \| \| \| \| \| Net income \| 30,425 \| 59,248 \| 77,670 \| \| Adjustments to reconcile net income to net cash from operating activities: \| \| \| \| \| Depreciation and amortization of property"
  - `AMZN-10-K-2026-c0076`: "sion for income taxes \| (7,120) \| (9,265) \| (19,087) \| \| Equity-method investment activity, net of tax \| (12) \| (101) \| (554) \| \| Net income \| $30,425 \| $59,248 \| $77,670 \| \| Basic earnings per share \| $2.95 \| $5.66 \| $7.29 \| \| Diluted earnings per share \| $2.90 \| $5.53 \| $7.17 \|"

## fg-069 - computed - medium

- [ ] **Q:** What was Google Cloud's operating margin in 2025? Round to one decimal place.
- **Tickers:** GOOGL
- **Gold answer:** About 23.7%: Google Cloud operating income of $13,910 million on revenues of $58,705 million.
- **Notes:** 13,910 / 58,705 = 23.695% -> 23.7% (rounded to 1 dp).
- **Label 1** (GOOGL, verified, 1 matching chunk(s)): `Google Cloud 43,229 58,705`
  - `GOOGL-10-K-2026-c0070`: "264,590 \| 294,691 \| \| Google subscriptions, platforms, and devices \| 40,340 \| 48,030 \| \| Google Services total \| 304,930 \| 342,721 \| \| Google Cloud \| 43,229 \| 58,705 \| \| Other Bets \| 1,648 \| 1,537 \| \| Hedging gains (losses) \| 211 \| (127) \| \| Total revenues \| $350,018 \| $402,836 \| Google Services Goo"
- **Label 2** (GOOGL, verified, 1 matching chunk(s)): `Google Cloud 6,112 13,910`
  - `GOOGL-10-K-2026-c0074`: "Year Ended December 31, 2024 \| 2025 \| \| --- \| --- \| --- \| \| Operating income (loss): \| \| \| \| Google Services \| $121,263 \| $139,404 \| \| Google Cloud \| 6,112 \| 13,910 \| \| Other Bets \| (4,444) \| (7,515) \| \| Alphabet-level activities (1) \| (10,541) \| (16,760) \| \| Total income from operations \| $112,390"

## fg-070 - computed - medium

- [ ] **Q:** By what percentage did Google Cloud revenues grow from 2024 to 2025? Round to one decimal place.
- **Tickers:** GOOGL
- **Gold answer:** About 35.8%, from $43,229 million to $58,705 million (the filing rounds this to 36%).
- **Notes:** (58,705 - 43,229) / 43,229 = 15,476 / 43,229 = 35.800% -> 35.8% (rounded to 1 dp). Filing text says $15.5 billion, or 36%.
- **Label 1** (GOOGL, verified, 1 matching chunk(s)): `Google Cloud 43,229 58,705`
  - `GOOGL-10-K-2026-c0070`: "264,590 \| 294,691 \| \| Google subscriptions, platforms, and devices \| 40,340 \| 48,030 \| \| Google Services total \| 304,930 \| 342,721 \| \| Google Cloud \| 43,229 \| 58,705 \| \| Other Bets \| 1,648 \| 1,537 \| \| Hedging gains (losses) \| 211 \| (127) \| \| Total revenues \| $350,018 \| $402,836 \| Google Services Goo"

## fg-071 - computed - medium

- [ ] **Q:** What share of NVIDIA's fiscal 2026 total revenue came from the Data Center end market? Round to one decimal place.
- **Tickers:** NVDA
- **Gold answer:** About 89.7%: Data Center revenue of $193,737 million out of total revenue of $215,938 million.
- **Notes:** 193,737 / 215,938 = 89.719% -> 89.7% (rounded to 1 dp).
- **Label 1** (NVDA, verified, 1 matching chunk(s)): `Data Center $193,737 $115,186` + `Total revenue $215,938 $130,497`
  - `NVDA-10-K-2026-c0170`: "\| Year Ended Jan 25, 2026 \| Jan 26, 2025 \| Jan 28, 2024 \| \| --- \| --- \| --- \| --- \| \| Revenue by End Market: \| (In millions) \| \| \| \| Data Center \| $193,737 \| $115,186 \| $47,525 \| \| Compute \| 162,361 \| 102,196 \| 38,950 \| \| Networking \| 31,376 \| 12,990 \| 8,575 \| \| Gaming \| 16,042 \| 11,350 \| 10,447 \| \|"

## fg-072 - computed - hard

- [ ] **Q:** What was the operating margin of NVIDIA's Graphics segment in fiscal year 2026? Round to one decimal place.
- **Tickers:** NVDA
- **Gold answer:** About 40.8%: Graphics operating income of $9,156 million on Graphics revenue of $22,459 million.
- **Notes:** 9,156 / 22,459 = 40.768% -> 40.8% (rounded to 1 dp).
- **Label 1** (NVDA, verified, 1 matching chunk(s)): `Graphics 22,459 14,304`
  - `NVDA-10-K-2026-c0094`: "\| Jan 26, 2025 \| $ Change \| % Change \| \| --- \| --- \| --- \| --- \| --- \| \| Compute & Networking \| $193,479 \| $116,193 \| $77,286 \| 67% \| \| Graphics \| 22,459 \| 14,304 \| 8,155 \| 57% \| \| Total \| $215,938 \| $130,497 \| $85,441 \| 65% \| Operating Income by Reportable Segments"
- **Label 2** (NVDA, verified, 1 matching chunk(s)): `Graphics 9,156 5,085`
  - `NVDA-10-K-2026-c0095`: "s) \| Jan 26, 2025 \| $ Change \| % Change \| \| --- \| --- \| --- \| --- \| --- \| \| Compute & Networking \| $130,141 \| $82,875 \| $47,266 \| 57% \| \| Graphics \| 9,156 \| 5,085 \| 4,071 \| 80% \| \| Total \| $139,297 \| $87,960 \| $51,337 \| 58% \| Compute & Networking revenue – The year over year increase was driven by t"

## fg-073 - computed - medium

- [ ] **Q:** By what percentage did Tesla's total automotive revenues change from 2024 to 2025? Round to one decimal place.
- **Tickers:** TSLA
- **Gold answer:** They declined about 9.8%, from $77,070 million to $69,526 million (the filing rounds this to (10)%).
- **Notes:** (69,526 - 77,070) / 77,070 = -7,544 / 77,070 = -9.788% -> -9.8% (rounded to 1 dp).
- **Label 1** (TSLA, verified, 2 matching chunk(s)): `Total automotive revenues 69,526 77,070`
  - `TSLA-10-K-2026-c0084`: "3 \| 2,763 \| 1,790 \| (770) \| (28)% \| 973 \| 54% \| \| Automotive leasing \| 1,712 \| 1,827 \| 2,120 \| (115) \| (6)% \| (293) \| (14)% \| \| Total automotive revenues \| 69,526 \| 77,070 \| 82,419 \| (7,544) \| (10)% \| (5,349) \| (6)% \| \| Services and other \| 12,530 \| 10,534 \| 8,319 \| 1,996 \| 19% \| 2,215 \| 27% \| \| Tot"
  - `TSLA-10-K-2026-c0108`: "$72,480 \| $78,509 \| \| Automotive regulatory credits \| 1,993 \| 2,763 \| 1,790 \| \| Automotive leasing \| 1,712 \| 1,827 \| 2,120 \| \| Total automotive revenues \| 69,526 \| 77,070 \| 82,419 \| \| Energy generation and storage \| 12,771 \| 10,086 \| 6,035 \| \| Services and other \| 12,530 \| 10,534 \| 8,319 \| \| Total"

## fg-074 - computed - hard

- [ ] **Q:** What was the gross margin of Tesla's energy generation and storage business in 2025? Round to one decimal place.
- **Tickers:** TSLA
- **Gold answer:** About 29.8%: energy generation and storage revenues of $12,771 million less cost of revenues of $8,969 million.
- **Notes:** (12,771 - 8,969) / 12,771 = 3,802 / 12,771 = 29.771% -> 29.8% (rounded to 1 dp).
- **Label 1** (TSLA, verified, 1 matching chunk(s)): `Energy generation and storage 12,771 10,086`
  - `TSLA-10-K-2026-c0108`: "3 \| 2,763 \| 1,790 \| \| Automotive leasing \| 1,712 \| 1,827 \| 2,120 \| \| Total automotive revenues \| 69,526 \| 77,070 \| 82,419 \| \| Energy generation and storage \| 12,771 \| 10,086 \| 6,035 \| \| Services and other \| 12,530 \| 10,534 \| 8,319 \| \| Total revenues \| 94,827 \| 97,690 \| 96,773 \| \| Cost of revenues \|"
- **Label 2** (TSLA, verified, 1 matching chunk(s)): `Energy generation and storage 8,969 7,446`
  - `TSLA-10-K-2026-c0108`: "870 \| 65,121 \| \| Automotive leasing \| 898 \| 1,003 \| 1,268 \| \| Total automotive cost of revenues \| 57,165 \| 62,873 \| 66,389 \| \| Energy generation and storage \| 8,969 \| 7,446 \| 4,894 \| \| Services and other \| 11,599 \| 9,921 \| 7,830 \| \| Total cost of revenues \| 77,733 \| 80,240 \| 79,113 \| \| Gross profit"

## fg-075 - computed - medium

- [ ] **Q:** What was Tesla's total gross margin percentage in 2025? Round to one decimal place.
- **Tickers:** TSLA
- **Gold answer:** About 18.0%: gross profit of $17,094 million on total revenues of $94,827 million.
- **Notes:** 17,094 / 94,827 = 18.026% -> 18.0% (rounded to 1 dp).
- **Label 1** (TSLA, verified, 2 matching chunk(s)): `Gross profit 17,094 17,450`
  - `TSLA-10-K-2026-c0088`: "t \| $3,802 \| $2,640 \| $1,141 \| \| \| \| \| \| Gross margin energy generation and storage segment \| 29.8% \| 26.2% \| 18.9% \| \| \| \| \| \| Total gross profit \| $17,094 \| $17,450 \| $17,660 \| \| \| \| \| \| Total gross margin \| 18.0% \| 17.9% \| 18.2% \| \| \| \| \| Automotive & Services and Other Segment Cost of automotive"
  - `TSLA-10-K-2026-c0108`: "rage \| 8,969 \| 7,446 \| 4,894 \| \| Services and other \| 11,599 \| 9,921 \| 7,830 \| \| Total cost of revenues \| 77,733 \| 80,240 \| 79,113 \| \| Gross profit \| 17,094 \| 17,450 \| 17,660 \| \| Operating expenses \| \| \| \| \| Research and development \| 6,411 \| 4,540 \| 3,969 \| \| Selling, general and administrative \| 5"
- **Label 2** (TSLA, verified, 3 matching chunk(s)): `Total revenues 94,827 97,690`
  - `TSLA-10-K-2026-c0084`: "\| (6)% \| (3,134) \| (3)% \| \| Energy generation and storage segment revenue \| 12,771 \| 10,086 \| 6,035 \| 2,685 \| 27% \| 4,051 \| 67% \| \| Total revenues \| $94,827 \| $97,690 \| $96,773 \| $(2,863) \| (3)% \| $917 \| 1% \| Automotive & Services and Other Segment Automotive sales revenue includes revenues"
  - `TSLA-10-K-2026-c0108`: "26 \| 77,070 \| 82,419 \| \| Energy generation and storage \| 12,771 \| 10,086 \| 6,035 \| \| Services and other \| 12,530 \| 10,534 \| 8,319 \| \| Total revenues \| 94,827 \| 97,690 \| 96,773 \| \| Cost of revenues \| \| \| \| \| Automotive sales \| 56,267 \| 61,870 \| 65,121 \| \| Automotive leasing \| 898 \| 1,003 \| 1,268 \| \|"

## fg-076 - computed - medium

- [ ] **Q:** What was JPMorgan Chase's overhead ratio (total noninterest expense divided by total net revenue) in 2025? Round to one decimal place.
- **Tickers:** JPM
- **Gold answer:** About 52.4%: total noninterest expense of $95,640 million over total net revenue of $182,447 million.
- **Notes:** 95,640 / 182,447 = 52.420% -> 52.4% (rounded to 1 dp). Overhead ratio definition taken from the filing's glossary (Total noninterest expense / Total net revenue).
- **Label 1** (JPM, verified, 4 matching chunk(s)): `Total noninterest expense 95,640 91,797`
  - `JPM-10-K-2026-c0110`: "\| 2023 \| \| \| Selected income statement data \| \| \| \| \| \| \| \| Total net revenue \| \| $182,447 \| \| $177,556 \| (g) \| $158,104 \| \| Total noninterest expense \| \| 95,640 \| \| 91,797 \| (g) \| 87,172 \| \| Pre-provision profit (a) \| \| 86,807 \| \| 85,759 \| \| 70,932 \| \| Provision for credit losses \| \| 14,212 \| (e)"
  - `JPM-10-K-2026-c0118`: "\| $87,004 \| $84,973 \| \| 2% \| \| Net interest income \| 95,443 \| 92,583 \| \| 3 \| \| Total net revenue \| 182,447 \| 177,556 \| \| 3 \| \| Total noninterest expense \| 95,640 \| 91,797 \| \| 4 \| \| Pre-provision profit \| 86,807 \| 85,759 \| \| 1 \| \| Provision for credit losses \| 14,212 \| 10,678 \| \| 33 \| \| Net income \|"
- **Label 2** (JPM, verified, 4 matching chunk(s)): `Total net revenue 182,447 177,556`
  - `JPM-10-K-2026-c0110`: "\| \| \| --- \| --- \| --- \| --- \| --- \| --- \| --- \| \| \| 2025 \| \| 2024 \| \| 2023 \| \| \| Selected income statement data \| \| \| \| \| \| \| \| Total net revenue \| \| $182,447 \| \| $177,556 \| (g) \| $158,104 \| \| Total noninterest expense \| \| 95,640 \| \| 91,797 \| (g) \| 87,172 \| \| Pre-provision profit (a) \| \| 86,807 \| \|"
  - `JPM-10-K-2026-c0118`: "come statement data \| \| \| \| \| \| Noninterest revenue \| $87,004 \| $84,973 \| \| 2% \| \| Net interest income \| 95,443 \| 92,583 \| \| 3 \| \| Total net revenue \| 182,447 \| 177,556 \| \| 3 \| \| Total noninterest expense \| 95,640 \| 91,797 \| \| 4 \| \| Pre-provision profit \| 86,807 \| 85,759 \| \| 1 \| \| Provision for cred"

## fg-077 - computed - medium

- [ ] **Q:** By what percentage did JPMorgan Chase's net income change from 2024 to 2025? Round to one decimal place.
- **Tickers:** JPM
- **Gold answer:** It declined about 2.4%, from $58,471 million to $57,048 million (the filing reports (2)%).
- **Notes:** (57,048 - 58,471) / 58,471 = -1,423 / 58,471 = -2.434% -> -2.4% (rounded to 1 dp).
- **Label 1** (JPM, verified, 9 matching chunk(s)): `Net income 57,048 58,471`
  - `JPM-10-K-2026-c0110`: "20 \| \| Income before income tax expense \| \| 72,595 \| \| 75,081 \| \| 61,612 \| \| Income tax expense \| \| 15,547 \| \| 16,610 \| \| 12,060 \| \| Net income \| \| $57,048 \| \| $58,471 \| \| $49,552 \| \| Earnings per share data \| \| \| \| \| \| \| \| Net income: Basic \| \| $20.05 \| \| $19.79 \| \| $16.25 \| \| Diluted \| \| 20.02 \| \|"
  - `JPM-10-K-2026-c0118`: "e \| 95,640 \| 91,797 \| \| 4 \| \| Pre-provision profit \| 86,807 \| 85,759 \| \| 1 \| \| Provision for credit losses \| 14,212 \| 10,678 \| \| 33 \| \| Net income \| 57,048 \| 58,471 \| \| (2) \| \| Diluted earnings per share \| 20.02 \| 19.75 \| \| 1 \| \| Selected ratios and metrics \| \| \| \| \| \| Return on common equity \| 17%"

## fg-078 - computed - medium

- [ ] **Q:** By what percentage did JPMorgan Chase's Markets revenue grow in 2025? Round to one decimal place.
- **Tickers:** JPM
- **Gold answer:** About 19.2%, from $30,007 million to $35,782 million (the filing reports 19%).
- **Notes:** (35,782 - 30,007) / 30,007 = 5,775 / 30,007 = 19.245% -> 19.2% (rounded to 1 dp).
- **Label 1** (JPM, verified, 1 matching chunk(s)): `Markets (d) 35,782 30,007`
  - `JPM-10-K-2026-c0118`: "\| \| Memo: \| \| \| \| \| \| NII excluding Markets (c) \| $92,591 \| $92,419 \| \| — \| \| NIR excluding Markets (c) \| 57,208 \| 58,167 \| \| (2) \| \| Markets (d) \| 35,782 \| 30,007 \| \| 19 \| \| Total net revenue - managed basis \| $185,581 \| $180,593 \| \| 3% \|"

## fg-079 - computed - medium

- [ ] **Q:** What was Coca-Cola's gross margin percentage in 2025? Round to one decimal place.
- **Tickers:** KO
- **Gold answer:** About 61.6%: gross profit of $29,544 million on net operating revenues of $47,941 million.
- **Notes:** 29,544 / 47,941 = 61.626% -> 61.6% (rounded to 1 dp).
- **Label 1** (KO, verified, 1 matching chunk(s)): `Gross Profit 29,544 28,737`
  - `KO-10-K-2026-c0150`: "\| --- \| --- \| --- \| --- \| \| Net Operating Revenues \| $47,941 \| $47,061 \| $45,754 \| \| Cost of goods sold \| 18,397 \| 18,324 \| 18,520 \| \| Gross Profit \| 29,544 \| 28,737 \| 27,234 \| \| Selling, general and administrative expenses \| 14,521 \| 14,582 \| 13,972 \| \| Other operating charges \| 1,261 \| 4,163 \| 1,9"
- **Label 2** (KO, verified, 3 matching chunk(s)): `Net Operating Revenues $47,941 $47,061`
  - `KO-10-K-2026-c0150`: "MENTS OF INCOME (In millions except per share data) \| Year Ended December 31, \| 2025 \| 2024 \| 2023 \| \| --- \| --- \| --- \| --- \| \| Net Operating Revenues \| $47,941 \| $47,061 \| $45,754 \| \| Cost of goods sold \| 18,397 \| 18,324 \| 18,520 \| \| Gross Profit \| 29,544 \| 28,737 \| 27,234 \| \| Selling, general and"
  - `KO-10-K-2026-c0267`: "2023 \| \| --- \| --- \| --- \| --- \| \| United States \| $19,127 \| $18,362 \| $16,550 \| \| International \| 28,814 \| 28,699 \| 29,204 \| \| Net operating revenues \| $47,941 \| $47,061 \| $45,754 \| For the year"

## fg-080 - computed - medium

- [ ] **Q:** By how many employees did Coca-Cola's headcount change between December 31, 2024 and December 31, 2025, and why?
- **Tickers:** KO
- **Gold answer:** It fell by about 3,800 employees (roughly 5.5%), from approximately 69,700 to approximately 65,900, primarily due to 2025 divestiture activity.
- **Notes:** 69,700 - 65,900 = 3,800; 3,800 / 69,700 = 5.452% -> 5.5% (rounded to 1 dp). Headcounts are approximate in the filing.
- **Label 1** (KO, verified, 1 matching chunk(s)): `approximately 65,900 and 69,700 employees`
  - `KO-10-K-2026-c0024`: "t important asset, and we strive to attract and retain high-performing talent. As of December 31, 2025 and 2024, our Company had approximately 65,900 and 69,700 employees, respectively, of which approximately 8,900 were located in the United States. The decrease in the total number of employees was"
- **Label 2** (KO, verified, 1 matching chunk(s)): `decrease in the total number of employees was primarily due to 2025 divestiture activity`
  - `KO-10-K-2026-c0024`: "0 and 69,700 employees, respectively, of which approximately 8,900 were located in the United States. The decrease in the total number of employees was primarily due to 2025 divestiture activity. Our Company, through its divisions and subsidiaries, is a party to numerous collective bargaining agreem"

## fg-106 - cross_company - hard

- [ ] **Q:** Which had more employees at its latest fiscal year end, Apple or Microsoft?
- **Tickers:** AAPL, MSFT
- **Gold answer:** Microsoft: approximately 223,000 full-time employees at June 30, 2026, versus approximately 166,000 full-time equivalent employees at Apple at September 27, 2025.
- **Notes:** Different dates and definitions (FTE vs full-time); answer should note them.
- **Label 1** (AAPL, verified, 1 matching chunk(s)): `approximately 166,000 full-time equivalent employees`
  - `AAPL-10-K-2025-c0009`: "d to inclusion and to providing a workplace free of harassment or discrimination. As of September 27, 2025, the Company had approximately 166,000 full-time equivalent employees. The Company believes that compensation should be competitive and equitable, and offers discretionary cash and equity award"
- **Label 2** (MSFT, verified, 1 matching chunk(s)): `employed approximately 223,000 people on a full-time basis`
  - `MSFT-10-K-2026-c0012`: "rms, and portals that provide content and online offerings to end users. HUMAN CAPITAL RESOURCES As of June 30, 2026, we employed approximately 223,000 people on a full-time basis, 121,000 in the U.S. and 102,000 internationally. Of the total employees, 89,000 were in operations, including product s"

## fg-107 - cross_company - hard

- [ ] **Q:** Which generated more revenue in 2025: Amazon's AWS segment or Alphabet's Google Cloud segment, and by how much?
- **Tickers:** AMZN, GOOGL
- **Gold answer:** AWS: $128,725 million of net sales versus Google Cloud revenues of $58,705 million, a difference of $70,020 million.
- **Notes:** 128,725 - 58,705 = 70,020 ($ millions).
- **Label 1** (AMZN, verified, 1 matching chunk(s)): `AWS 107,556 128,725`
  - `AMZN-10-K-2026-c0054`: "31, 2024 \| 2025 \| \| --- \| --- \| --- \| \| Net Sales: \| \| \| \| North America \| $387,497 \| $426,305 \| \| International \| 142,906 \| 161,894 \| \| AWS \| 107,556 \| 128,725 \| \| Consolidated \| $637,959 \| $716,924 \| \| Year-over-year Percentage Growth: \| \| \| \| North America \| 10% \| 10% \| \| International \| 9 \| 13"
- **Label 2** (GOOGL, verified, 1 matching chunk(s)): `Google Cloud 43,229 58,705`
  - `GOOGL-10-K-2026-c0070`: "264,590 \| 294,691 \| \| Google subscriptions, platforms, and devices \| 40,340 \| 48,030 \| \| Google Services total \| 304,930 \| 342,721 \| \| Google Cloud \| 43,229 \| 58,705 \| \| Other Bets \| 1,648 \| 1,537 \| \| Hedging gains (losses) \| 211 \| (127) \| \| Total revenues \| $350,018 \| $402,836 \| Google Services Goo"

## fg-108 - cross_company - hard

- [ ] **Q:** Compare 2025 operating income of Amazon's AWS segment with Alphabet's Google Cloud segment.
- **Tickers:** AMZN, GOOGL
- **Gold answer:** AWS operating income was $45,606 million versus Google Cloud operating income of $13,910 million, so AWS earned $31,696 million more.
- **Notes:** 45,606 - 13,910 = 31,696 ($ millions).
- **Label 1** (AMZN, verified, 1 matching chunk(s)): `AWS 39,834 45,606`
  - `AMZN-10-K-2026-c0060`: "r 31, 2024 \| 2025 \| \| --- \| --- \| --- \| \| Operating Income \| \| \| \| North America \| $24,967 \| $29,619 \| \| International \| 3,792 \| 4,750 \| \| AWS \| 39,834 \| 45,606 \| \| Consolidated \| $68,593 \| $79,975 \| Operating income was $68.6 billion and $80.0 billion for 2024 and 2025. Operating income for 2025 in"
- **Label 2** (GOOGL, verified, 1 matching chunk(s)): `Google Cloud 6,112 13,910`
  - `GOOGL-10-K-2026-c0074`: "Year Ended December 31, 2024 \| 2025 \| \| --- \| --- \| --- \| \| Operating income (loss): \| \| \| \| Google Services \| $121,263 \| $139,404 \| \| Google Cloud \| 6,112 \| 13,910 \| \| Other Bets \| (4,444) \| (7,515) \| \| Alphabet-level activities (1) \| (10,541) \| (16,760) \| \| Total income from operations \| $112,390"

## fg-109 - cross_company - hard

- [ ] **Q:** Which reported higher net income for its most recent fiscal year in these filings, Microsoft or NVIDIA?
- **Tickers:** MSFT, NVDA
- **Gold answer:** Microsoft: $133,749 million for fiscal 2026 (ended June 30, 2026) versus NVIDIA's $120,067 million for fiscal 2026 (ended January 25, 2026); a $13,682 million difference.
- **Notes:** 133,749 - 120,067 = 13,682 ($ millions). Fiscal years end on different dates.
- **Label 1** (MSFT, verified, 6 matching chunk(s)): `Net income $133,749 $101,832`
  - `MSFT-10-K-2026-c0070`: "\| \| Revenue \| $331,839 \| $281,724 \| 18% \| \| Gross margin \| 225,465 \| 193,893 \| 16% \| \| Operating income \| 155,237 \| 128,528 \| 21% \| \| Net income \| 133,749 \| 101,832 \| 31% \| \| Diluted earnings per share \| 17.95 \| 13.64 \| 32% \| \| Adjusted net income (non-GAAP) \| 128,786 \| 105,452 \| 22% \| \| Adjusted d"
  - `MSFT-10-K-2026-c0078`: "30) \| 4,763 \| 1,482 \| (237)% \| 221% \| \| Adjusted other income (expense), net (non-GAAP) \| $4,167 \| $(138) \| $(164) \| 3,120% \| 16% \| \| Net income \| $133,749 \| $101,832 \| $88,136 \| 31% \| 16% \| \| Net (gains) losses from investments in OpenAI, net of tax of $1,567 , $(1,143), and $(356) \| (4,963) \| 3,62"
- **Label 2** (NVDA, verified, 5 matching chunk(s)): `Net income $120,067 $72,880`
  - `NVDA-10-K-2026-c0089`: "\| 71.1% \| 75.0% \| -3.9 pts \| \| Operating expenses \| $23,076 \| $16,405 \| Up 41% \| \| Operating income \| $130,387 \| $81,453 \| Up 60% \| \| Net income \| $120,067 \| $72,880 \| Up 65% \| \| Net income per diluted share \| $4.90 \| $2.94 \| Up 67% \| Revenue for fiscal year 2026 was $215.9 billion, up 65% from a ye"
  - `NVDA-10-K-2026-c0118`: "\| 11,063 \| 2,573 \| 846 \| \| Income before income tax \| 141,450 \| 84,026 \| 33,818 \| \| Income tax expense \| 21,383 \| 11,146 \| 4,058 \| \| Net income \| $120,067 \| $72,880 \| $29,760 \| \| Net income per share: \| \| \| \| \| Basic \| $4.93 \| $2.97 \| $1.21 \| \| Diluted \| $4.90 \| $2.94 \| $1.19 \| \| Weighted average s"

## fg-110 - cross_company - medium

- [ ] **Q:** Which had higher diluted earnings per share in its latest fiscal year, JPMorgan Chase or Microsoft?
- **Tickers:** JPM, MSFT
- **Gold answer:** JPMorgan Chase: $20.02 for 2025, versus Microsoft's $17.95 for fiscal 2026.
- **Label 1** (JPM, verified, 2 matching chunk(s)): `Diluted earnings per share 20.02 19.75`
  - `JPM-10-K-2026-c0118`: "it \| 86,807 \| 85,759 \| \| 1 \| \| Provision for credit losses \| 14,212 \| 10,678 \| \| 33 \| \| Net income \| 57,048 \| 58,471 \| \| (2) \| \| Diluted earnings per share \| 20.02 \| 19.75 \| \| 1 \| \| Selected ratios and metrics \| \| \| \| \| \| Return on common equity \| 17% \| 18% \| \| \| \| Return on tangible common equity \|"
  - `JPM-10-K-2026-c0361`: "5,681 \| $56,868 \| $47,760 \| \| Net income per common share data \| \| \| \| \| Basic earnings per share \| $20.05 \| $19.79 \| $16.25 \| \| Diluted earnings per share \| 20.02 \| 19.75 \| 16.23 \| \| Weighted-average basic shares \| 2,776.5 \| 2,873.9 \| 2,938.6 \| \| Weighted-average diluted shares \| 2,781.5 \| 2,879.0"
- **Label 2** (MSFT, verified, 1 matching chunk(s)): `Diluted $17.95 $13.64`
  - `MSFT-10-K-2026-c0092`: "\| 21,795 \| 19,651 \| \| Net income \| $133,749 \| $101,832 \| $88,136 \| \| Earnings per share: \| \| \| \| \| Basic \| $18.00 \| $13.70 \| $11.86 \| \| Diluted \| $17.95 \| $13.64 \| $11.80 \| \| Weighted average shares outstanding: \| \| \| \| \| Basic \| 7,429 \| 7,433 \| 7,431 \| \| Diluted \| 7,453 \| 7,465 \| 7,469 \| Refer to"

## fg-111 - cross_company - medium

- [ ] **Q:** Compare Tesla's and Coca-Cola's total revenues for 2025.
- **Tickers:** TSLA, KO
- **Gold answer:** Tesla's total revenues were $94,827 million versus Coca-Cola's net operating revenues of $47,941 million; Tesla's were about 2.0 times Coca-Cola's.
- **Notes:** 94,827 / 47,941 = 1.978 -> about 2.0x (rounded to 1 dp).
- **Label 1** (TSLA, verified, 3 matching chunk(s)): `Total revenues 94,827 97,690`
  - `TSLA-10-K-2026-c0084`: "\| (6)% \| (3,134) \| (3)% \| \| Energy generation and storage segment revenue \| 12,771 \| 10,086 \| 6,035 \| 2,685 \| 27% \| 4,051 \| 67% \| \| Total revenues \| $94,827 \| $97,690 \| $96,773 \| $(2,863) \| (3)% \| $917 \| 1% \| Automotive & Services and Other Segment Automotive sales revenue includes revenues"
  - `TSLA-10-K-2026-c0108`: "26 \| 77,070 \| 82,419 \| \| Energy generation and storage \| 12,771 \| 10,086 \| 6,035 \| \| Services and other \| 12,530 \| 10,534 \| 8,319 \| \| Total revenues \| 94,827 \| 97,690 \| 96,773 \| \| Cost of revenues \| \| \| \| \| Automotive sales \| 56,267 \| 61,870 \| 65,121 \| \| Automotive leasing \| 898 \| 1,003 \| 1,268 \| \|"
- **Label 2** (KO, verified, 3 matching chunk(s)): `Net Operating Revenues $47,941 $47,061`
  - `KO-10-K-2026-c0150`: "MENTS OF INCOME (In millions except per share data) \| Year Ended December 31, \| 2025 \| 2024 \| 2023 \| \| --- \| --- \| --- \| --- \| \| Net Operating Revenues \| $47,941 \| $47,061 \| $45,754 \| \| Cost of goods sold \| 18,397 \| 18,324 \| 18,520 \| \| Gross Profit \| 29,544 \| 28,737 \| 27,234 \| \| Selling, general and"
  - `KO-10-K-2026-c0267`: "2023 \| \| --- \| --- \| --- \| --- \| \| United States \| $19,127 \| $18,362 \| $16,550 \| \| International \| 28,814 \| 28,699 \| 29,204 \| \| Net operating revenues \| $47,941 \| $47,061 \| $45,754 \| For the year"

## fg-112 - cross_company - medium

- [ ] **Q:** How did Amazon's and JPMorgan Chase's employee counts compare at December 31, 2025?
- **Tickers:** AMZN, JPM
- **Gold answer:** Amazon employed approximately 1,576,000 full-time and part-time employees versus 318,512 at JPMorganChase.
- **Label 1** (AMZN, verified, 1 matching chunk(s)): `employed approximately 1,576,000 full-time and part-time employees`
  - `AMZN-10-K-2026-c0007`: "ur employees are critical to our mission of being Earth’s most customer-centric company. As of December 31, 2025, we employed approximately 1,576,000 full-time and part-time employees. Additionally, we use independent contractors and temporary personnel to supplement our workforce. Competition for q"
- **Label 2** (JPM, verified, 2 matching chunk(s)): `had 318,512 employees globally`
  - `JPM-10-K-2026-c0023`: "full-time and part-time employees and does not include the Firm’s contractors. Global workforce As of December 31, 2025, JPMorganChase had 318,512 employees globally. JPMorganChase’s employees are located in 66 countries, with 58% of the Firm’s employees located in the U.S"
  - `JPM-10-K-2026-c0024`: "full-time and part-time employees and does not include the Firm’s contractors. Global workforce As of December 31, 2025, JPMorganChase had 318,512 employees globally. JPMorganChase’s employees are located in 66 countries, with 58% of the Firm’s employees located in the U.S. The following table prese"

## fg-113 - cross_company - medium

- [ ] **Q:** Compare JPMorgan Chase's and Amazon's total assets at December 31, 2025.
- **Tickers:** JPM, AMZN
- **Gold answer:** JPMorgan Chase's total assets were $4,424,900 million versus Amazon's $818,042 million.
- **Notes:** Amazon's balance sheet lists 2024 then 2025; $818,042M is the 2025 column.
- **Label 1** (JPM, verified, 2 matching chunk(s)): `Total assets $4,424,900 $4,002,814`
  - `JPM-10-K-2026-c0112`: "s, net of allowance for credit losses \| \| 777,332 \| \| 681,320 \| \| 571,552 \| \| Loans \| \| 1,493,429 \| \| 1,347,988 \| \| 1,323,706 \| \| Total assets \| \| 4,424,900 \| \| 4,002,814 \| \| 3,875,393 \| \| Deposits \| \| 2,559,320 \| \| 2,406,032 \| \| 2,400,688 \| \| Long-term debt \| \| 435,206 \| \| 401,418 \| \| 391,825 \| \| C"
  - `JPM-10-K-2026-c0133`: "4 \| 32,223 \| 12 \| \| Goodwill, MSRs and other intangible assets \| 64,458 \| 64,560 \| — \| \| Other assets \| 198,775 \| 178,197 \| 12 \| \| Total assets \| $4,424,900 \| $4,002,814 \| 11% \| Cash and due from banks and deposits with banks decreased driven by Markets activities in CIB"
- **Label 2** (AMZN, verified, 1 matching chunk(s)): `Total assets $624,894 $818,042`
  - `AMZN-10-K-2026-c0078`: "et \| 252,665 \| 357,025 \| \| Operating leases \| 76,141 \| 86,054 \| \| Goodwill \| 23,074 \| 23,273 \| \| Other assets \| 82,147 \| 122,607 \| \| Total assets \| $624,894 \| $818,042 \| \| LIABILITIES AND STOCKHOLDERS’ EQUITY \| \| \| \| Current liabilities: \| \| \| \| Accounts payable \| $94,363 \| $121,909 \| \| Accrued expe"

## fg-114 - cross_company - medium

- [ ] **Q:** How do Apple's and Microsoft's fiscal year ends differ?
- **Tickers:** AAPL, MSFT
- **Gold answer:** Apple's fiscal year is the 52- or 53-week period ending on the last Saturday of September (fiscal 2025 ended September 27, 2025); Microsoft's fiscal year ends June 30 (fiscal 2026 ended June 30, 2026).
- **Label 1** (AAPL, verified, 3 matching chunk(s)): `fiscal year is the 52- or 53-week period that ends on the last Saturday of September`
  - `AAPL-10-K-2025-c0004`: "sonal computers, tablets, wearables and accessories, and sells a variety of related services. The Company’s fiscal year is the 52- or 53-week period that ends on the last Saturday of September. Products iPhone iPhone ® is the Company’s line of smartphones based on its iOS operating system. The iPhon"
  - `AAPL-10-K-2025-c0049`: "Apple Watch Series 11, Apple Watch SE 3 and Apple Watch Ultra 3 • AirPods Pro 3 Fiscal Period The Company’s fiscal year is the 52- or 53-week period that ends on the last Saturday of September. An additional week is included in the first fiscal quarter every five or six years to realign the Company’"
- **Label 2** (MSFT, verified, 1 matching chunk(s)): `for the year ended June 30, 2026 compared to the year ended June 30, 2025`
  - `MSFT-10-K-2026-c0065`: "l Statements (Part II, Item 8 of this Form 10-K). This section generally discusses the results of our operations for the year ended June 30, 2026 compared to the year ended June 30, 2025. For a discussion of the year ended June 30, 2025 compared to the year ended June 30, 2024, please refer to Part"

## fg-115 - cross_company - medium

- [ ] **Q:** Compare NVIDIA's and Alphabet's employee headcounts at their latest fiscal year ends.
- **Tickers:** NVDA, GOOGL
- **Gold answer:** NVIDIA had approximately 42,000 employees at the end of fiscal 2026, while Alphabet had 190,820 employees at December 31, 2025.
- **Label 1** (NVDA, verified, 1 matching chunk(s)): `we had approximately 42,000 employees in 38 countries`
  - `NVDA-10-K-2026-c0023`: "1A. Risk Factors” for a discussion of these potential impacts. Human Capital Management As of the end of fiscal year 2026, we had approximately 42,000 employees in 38 countries; 31,000 were engaged in research and development and 11,000 were engaged in sales, marketing, operations, and administrativ"
- **Label 2** (GOOGL, verified, 2 matching chunk(s)): `Alphabet had 190,820 employees`
  - `GOOGL-10-K-2026-c0010`: "earning resources that help them provide feedback and manage performance, to coaching and individual support. As of December 31, 2025, Alphabet had 190,820 employees. We have work councils and statutory employee representation obligations in certain countries, and we are committed to supporting prot"
  - `GOOGL-10-K-2026-c0011`: "earning resources that help them provide feedback and manage performance, to coaching and individual support. As of December 31, 2025, Alphabet had 190,820 employees. We have work councils and statutory employee representation obligations in certain countries, and we are committed to supporting prot"

## fg-116 - cross_company - hard

- [ ] **Q:** Compare research and development expense at Apple (fiscal 2025) and Microsoft (fiscal 2026).
- **Tickers:** AAPL, MSFT
- **Gold answer:** Apple's R&D expense was $34,550 million in fiscal 2025; Microsoft's was $35,562 million in fiscal 2026, $1,012 million more.
- **Notes:** 35,562 - 34,550 = 1,012 ($ millions). Different fiscal periods.
- **Label 1** (AAPL, verified, 1 matching chunk(s)): `Research and development 34,550 31,370`
  - `AAPL-10-K-2025-c0062`: "tal cost of sales \| 220,960 \| 210,352 \| 214,137 \| \| Gross margin \| 195,201 \| 180,683 \| 169,148 \| \| Operating expenses: \| \| \| \| \| Research and development \| 34,550 \| 31,370 \| 29,915 \| \| Selling, general and administrative \| 27,601 \| 26,097 \| 24,932 \| \| Total operating expenses \| 62,151 \| 57,467 \| 54,"
- **Label 2** (MSFT, verified, 2 matching chunk(s)): `Research and development 35,562 32,488`
  - `MSFT-10-K-2026-c0074`: "ES Research and Development \| (In millions, except percentages) \| 2026 \| 2025 \| Percentage Change \| \| --- \| --- \| --- \| --- \| \| Research and development \| $35,562 \| $32,488 \| 9% \| \| As a percent of revenue \| 11% \| 12% \| (1)ppt \| Research and development expenses include payroll, stock-based compensa"
  - `MSFT-10-K-2026-c0092`: "4,276 \| 74,330 \| 58,842 \| \| Total cost of revenue \| 106,374 \| 87,831 \| 74,114 \| \| Gross margin \| 225,465 \| 193,893 \| 171,008 \| \| Research and development \| 35,562 \| 32,488 \| 29,510 \| \| Sales and marketing \| 26,710 \| 25,654 \| 24,456 \| \| General and administrative \| 7,956 \| 7,223 \| 7,609 \| \| Operating"

## fg-117 - cross_company - hard

- [ ] **Q:** How do Apple and Tesla each describe the impact of tariffs on their businesses?
- **Tickers:** AAPL, TSLA
- **Gold answer:** Apple says tariffs on its products or components can have a material adverse impact on its business, results and financial condition, including supply chain, availability of rare earths and other materials, pricing and gross margin. Tesla says the current tariff regime will have a relatively larger impact on its energy generation and storage business than on its automotive business.
- **Label 1** (AAPL, verified, 1 matching chunk(s)): `the availability of rare earths and other raw materials and components, pricing and gross margin`
  - `AAPL-10-K-2025-c0050`: "iness, results of operations and financial condition, including impacting the Company’s supply chain, the availability of rare earths and other raw materials and components, pricing and gross margin. The ultimate impact remains uncertain and will depend on several factors, including whether addition"
- **Label 2** (TSLA, verified, 1 matching chunk(s)): `The current tariff regime will have a relatively larger impact on our energy generation and storage business`
  - `TSLA-10-K-2026-c0070`: "hich could have a meaningfully adverse impact on demand for our products and our profitability. The current tariff regime will have a relatively larger impact on our energy generation and storage business compared to our automotive business. While we prepare for near-term challenges to our business"

## fg-118 - cross_company - medium

- [ ] **Q:** Which earned more net income attributable to common shareholders in 2025, Coca-Cola or Tesla?
- **Tickers:** KO, TSLA
- **Gold answer:** Coca-Cola: $13,107 million attributable to its shareowners versus Tesla's $3,794 million attributable to common stockholders.
- **Label 1** (KO, verified, 2 matching chunk(s)): `Net Income Attributable to Shareowners of The Coca-Cola Company $13,107`
  - `KO-10-K-2026-c0150`: ",137 \| 10,649 \| 10,703 \| \| Less: Net income (loss) attributable to noncontrolling interests \| 30 \| 18 \| (11) \| \| Net Income Attributable to Shareowners of The Coca-Cola Company \| $13,107 \| $10,631 \| $10,714 \| \| Basic Net Income Per Share 1 \| $3.05 \| $2.47 \| $2.48 \| \| Diluted Net Income Per Share 1 \|"
  - `KO-10-K-2026-c0156`: "1 \| 19,801 \| 19,209 \| \| Reinvested Earnings \| \| \| \| \| Balance at beginning of year \| 76,054 \| 73,782 \| 71,019 \| \| Net income attributable to shareowners of The Coca-Cola Company \| 13,107 \| 10,631 \| 10,714 \| \| Dividends (per share — $2.04 , $1.94 and $1.84 in 2025, 2024 and 2023, respectively) \| (8,7"
- **Label 2** (TSLA, verified, 2 matching chunk(s)): `Net income attributable to common stockholders $3,794 $7,091`
  - `TSLA-10-K-2026-c0109`: "attributable to noncontrolling interests and redeemable noncontrolling interests in subsidiaries \| 61 \| 62 \| (23) \| \| Net income attributable to common stockholders \| $3,794 \| $7,091 \| $14,997 \| \| Net income per share of common stock attributable to common stockholders \| \| \| \| \| Basic \| $1.18 \| $2.2"
  - `TSLA-10-K-2026-c0132`: "per share of common stock (in millions): \| \| Year Ended December 31, 2025 \| 2024 \| 2023 \| \| --- \| --- \| --- \| --- \| \| Net income attributable to common stockholders \| $3,794 \| $7,091 \| $14,997 \| \| Less: Buy-outs of noncontrolling interests \| — \| (39) \| (2) \| \| Net income used in computing basic and"

## fg-119 - cross_company - medium

- [ ] **Q:** Whose total revenue grew faster in 2025, Alphabet or Amazon?
- **Tickers:** GOOGL, AMZN
- **Gold answer:** Alphabet: revenues rose 15% year over year to $402.8 billion, versus a 12% increase in Amazon's net sales.
- **Label 1** (GOOGL, verified, 1 matching chunk(s)): `Revenues were $402.8 billion, an increase of 15% year over year`
  - `GOOGL-10-K-2026-c0069`: "ee Note 12 of the Notes to Consolidated Financial Statements included in Item 8 of this Annual Report on Form 10-K. • Revenues were $402.8 billion, an increase of 15% year over year, primarily driven by an increase in Google Services revenues of $37.8 billion, or 12%, and an increase in Google Cloud"
- **Label 2** (AMZN, verified, 2 matching chunk(s)): `Sales increased 12% in 2025, compared to the prior year`
  - `AMZN-10-K-2026-c0054`: "les Mix: \| \| \| \| North America \| 61% \| 59% \| \| International \| 22 \| 23 \| \| AWS \| 17 \| 18 \| \| Consolidated \| 100% \| 100% \| Sales increased 12% in 2025, compared to the prior year. Changes in foreign exchange rates increased net sales by $4.4 billion in 2025. For a discussion of the effect of foreign"
  - `AMZN-10-K-2026-c0055`: "Sales increased 12% in 2025, compared to the prior year. Changes in foreign exchange rates increased net sales by $4.4 billion in 2025. For a discussion of the effect of foreign exchange rates on sales growth, see “Effect of Foreign Exchange Rates” below. North America sales increased 10% in 2025, c"

## fg-120 - cross_company - medium

- [ ] **Q:** Compare Apple's and NVIDIA's cash and cash equivalents at their latest fiscal year ends.
- **Tickers:** AAPL, NVDA
- **Gold answer:** Apple had $35,934 million at September 27, 2025, versus NVIDIA's $10,605 million at January 25, 2026.
- **Notes:** Cash and cash equivalents only (excludes marketable securities).
- **Label 1** (AAPL, verified, 1 matching chunk(s)): `Cash and cash equivalents $35,934 $29,943`
  - `AAPL-10-K-2025-c0064`: "ds, and par value) \| \| September 27, 2025 \| September 28, 2024 \| \| --- \| --- \| --- \| \| ASSETS: \| \| \| \| Current assets: \| \| \| \| Cash and cash equivalents \| $35,934 \| $29,943 \| \| Marketable securities \| 18,763 \| 35,228 \| \| Accounts receivable, net \| 39,777 \| 33,410 \| \| Vendor non-trade receivables \| 3"
- **Label 2** (NVDA, verified, 2 matching chunk(s)): `Cash and cash equivalents $10,605 $8,589`
  - `NVDA-10-K-2026-c0099`: "r additional information. Liquidity and Capital Resources \| \| Jan 25, 2026 (In millions) \| Jan 26, 2025 \| \| --- \| --- \| --- \| \| Cash and cash equivalents \| $10,605 \| $8,589 \| \| Marketable securities \| 51,951 \| 34,621 \| \| Cash, cash equivalents, and marketable securities \| $62,556 \| $43,210 \| 42 Tabl"
  - `NVDA-10-K-2026-c0120`: "(In millions, except par value) \| \| Jan 25, 2026 \| Jan 26, 2025 \| \| --- \| --- \| --- \| \| Assets \| \| \| \| Current assets: \| \| \| \| Cash and cash equivalents \| $10,605 \| $8,589 \| \| Marketable securities \| 51,951 \| 34,621 \| \| Accounts receivable, net \| 38,466 \| 23,065 \| \| Inventories \| 21,403 \| 10,080 \|"

## fg-021 - financial_lookup - easy

- [ ] **Q:** What were Apple's total net sales for fiscal year 2025?
- **Tickers:** AAPL
- **Gold answer:** Apple's total net sales were $416,161 million for fiscal 2025 (year ended September 27, 2025).
- **Notes:** Consolidated Statements of Operations and MD&A segment/product tables.
- **Label 1** (AAPL, verified, 5 matching chunk(s)): `Total net sales $416,161`
  - `AAPL-10-K-2025-c0050`: "6,952 \| (8)% \| 72,559 \| \| Japan \| 28,703 \| 15% \| 25,052 \| 3% \| 24,257 \| \| Rest of Asia Pacific \| 33,696 \| 10% \| 30,658 \| 4% \| 29,615 \| \| Total net sales \| $416,161 \| 6% \| $391,035 \| 2% \| $383,285 \|"
  - `AAPL-10-K-2025-c0051`: "\| Wearables, Home and Accessories \| 35,686 \| (4)% \| 37,005 \| (7)% \| 39,845 \| \| Services (1) \| 109,158 \| 14% \| 96,169 \| 13% \| 85,200 \| \| Total net sales \| $416,161 \| 6% \| $391,035 \| 2% \| $383,285 \| (1) Services net sales include amortization of the deferred value of services bundled in the sales pri"

## fg-022 - financial_lookup - easy

- [ ] **Q:** What was Apple's net income for fiscal year 2025?
- **Tickers:** AAPL
- **Gold answer:** Apple's net income was $112,010 million for fiscal 2025 (year ended September 27, 2025).
- **Label 1** (AAPL, verified, 5 matching chunk(s)): `Net income $112,010 $93,736`
  - `AAPL-10-K-2025-c0062`: "Income before provision for income taxes \| 132,729 \| 123,485 \| 113,736 \| \| Provision for income taxes \| 20,719 \| 29,749 \| 16,741 \| \| Net income \| $112,010 \| $93,736 \| $96,995 \| \| Earnings per share: \| \| \| \| \| Basic \| $7.49 \| $6.11 \| $6.16 \| \| Diluted \| $7.46 \| $6.08 \| $6.13 \| \| Shares used in compu"
  - `AAPL-10-K-2025-c0063`: "NSIVE INCOME (In millions) \| \| Years ended September 27, 2025 \| September 28, 2024 \| September 30, 2023 \| \| --- \| --- \| --- \| --- \| \| Net income \| $112,010 \| $93,736 \| $96,995 \| \| Other comprehensive income/(loss): \| \| \| \| \| Change in foreign currency translation, net of tax \| (267) \| 395 \| (765) \|"

## fg-023 - financial_lookup - easy

- [ ] **Q:** What were Apple's diluted earnings per share for fiscal year 2025?
- **Tickers:** AAPL
- **Gold answer:** Apple's diluted earnings per share were $7.46 for fiscal 2025.
- **Label 1** (AAPL, verified, 1 matching chunk(s)): `Diluted $7.46 $6.08`
  - `AAPL-10-K-2025-c0062`: "0,719 \| 29,749 \| 16,741 \| \| Net income \| $112,010 \| $93,736 \| $96,995 \| \| Earnings per share: \| \| \| \| \| Basic \| $7.49 \| $6.11 \| $6.16 \| \| Diluted \| $7.46 \| $6.08 \| $6.13 \| \| Shares used in computing earnings per share: \| \| \| \| \| Basic \| 14,948,500 \| 15,343,783 \| 15,744,231 \| \| Diluted \| 15,004,697 \|"

## fg-024 - financial_lookup - medium

- [ ] **Q:** What were Apple's Greater China net sales in fiscal year 2025, and how did they change from 2024?
- **Tickers:** AAPL
- **Gold answer:** Greater China net sales were $64,377 million in fiscal 2025, down 4% from $66,952 million in fiscal 2024.
- **Label 1** (AAPL, verified, 1 matching chunk(s)): `Greater China 64,377 (4)% 66,952`
  - `AAPL-10-K-2025-c0050`: "- \| --- \| --- \| --- \| \| Americas \| $178,353 \| 7% \| $167,045 \| 3% \| $162,560 \| \| Europe \| 111,032 \| 10% \| 101,328 \| 7% \| 94,294 \| \| Greater China \| 64,377 \| (4)% \| 66,952 \| (8)% \| 72,559 \| \| Japan \| 28,703 \| 15% \| 25,052 \| 3% \| 24,257 \| \| Rest of Asia Pacific \| 33,696 \| 10% \| 30,658 \| 4% \| 29,615 \| \|"

## fg-025 - financial_lookup - medium

- [ ] **Q:** What were Apple's iPhone net sales in fiscal year 2023?
- **Tickers:** AAPL
- **Gold answer:** Apple's iPhone net sales were $200,583 million in fiscal 2023.
- **Notes:** Prior-year column lookup (tests period alignment); 2025 iPhone was $209,586M.
- **Label 1** (AAPL, verified, 1 matching chunk(s)): `iPhone $209,586 4% $201,183 —% $200,583`
  - `AAPL-10-K-2025-c0051`: "025, 2024 and 2023 (dollars in millions): \| \| 2025 \| Change \| 2024 \| Change \| 2023 \| \| --- \| --- \| --- \| --- \| --- \| --- \| \| iPhone \| $209,586 \| 4% \| $201,183 \| —% \| $200,583 \| \| Mac \| 33,708 \| 12% \| 29,984 \| 2% \| 29,357 \| \| iPad \| 28,023 \| 5% \| 26,694 \| (6)% \| 28,300 \| \| Wearables, Home and Accesso"

## fg-026 - financial_lookup - easy

- [ ] **Q:** What was Microsoft's total revenue for fiscal year 2026?
- **Tickers:** MSFT
- **Gold answer:** Microsoft's total revenue was $331,839 million for fiscal year 2026 (year ended June 30, 2026), up 18%.
- **Label 1** (MSFT, verified, 3 matching chunk(s)): `Total revenue 331,839 281,724`
  - `MSFT-10-K-2026-c0071`: "venue \| 23,481 \| 25,238 \| (7)% \| \| Operating expenses \| 16,185 \| 15,245 \| 6% \| \| Operating income \| $14,386 \| $14,166 \| 2% \| \| Total \| \| \| \| \| Revenue \| $331,839 \| $281,724 \| 18% \| \| Cost of revenue \| 106,374 \| 87,831 \| 21% \| \| Operating expenses \| 70,228 \| 65,365 \| 7% \| \| Operating income \| $155,23"
  - `MSFT-10-K-2026-c0092`: "6 \| 2025 \| 2024 \| \| Revenue: \| \| \| \| \| Product \| $64,696 \| $63,946 \| $64,773 \| \| Service and other \| 267,143 \| 217,778 \| 180,349 \| \| Total revenue \| 331,839 \| 281,724 \| 245,122 \| \| Cost of revenue: \| \| \| \| \| Product \| 12,098 \| 13,501 \| 15,272 \| \| Service and other \| 94,276 \| 74,330 \| 58,842 \| \| Tota"

## fg-027 - financial_lookup - easy

- [ ] **Q:** What was Microsoft's net income for fiscal year 2026?
- **Tickers:** MSFT
- **Gold answer:** Microsoft's net income was $133,749 million for fiscal year 2026 (year ended June 30, 2026).
- **Label 1** (MSFT, verified, 6 matching chunk(s)): `Net income $133,749 $101,832`
  - `MSFT-10-K-2026-c0070`: "\| \| Revenue \| $331,839 \| $281,724 \| 18% \| \| Gross margin \| 225,465 \| 193,893 \| 16% \| \| Operating income \| 155,237 \| 128,528 \| 21% \| \| Net income \| 133,749 \| 101,832 \| 31% \| \| Diluted earnings per share \| 17.95 \| 13.64 \| 32% \| \| Adjusted net income (non-GAAP) \| 128,786 \| 105,452 \| 22% \| \| Adjusted d"
  - `MSFT-10-K-2026-c0078`: "30) \| 4,763 \| 1,482 \| (237)% \| 221% \| \| Adjusted other income (expense), net (non-GAAP) \| $4,167 \| $(138) \| $(164) \| 3,120% \| 16% \| \| Net income \| $133,749 \| $101,832 \| $88,136 \| 31% \| 16% \| \| Net (gains) losses from investments in OpenAI, net of tax of $1,567 , $(1,143), and $(356) \| (4,963) \| 3,62"

## fg-028 - financial_lookup - easy

- [ ] **Q:** What were Microsoft's total assets as of June 30, 2026?
- **Tickers:** MSFT
- **Gold answer:** Microsoft's total assets were $758,376 million as of June 30, 2026.
- **Label 1** (MSFT, verified, 1 matching chunk(s)): `Total assets $758,376 $619,003`
  - `MSFT-10-K-2026-c0094`: "5,405 \| \| Goodwill \| 119,651 \| 119,509 \| \| Intangible assets, net \| 18,609 \| 22,604 \| \| Other long-term assets \| 38,805 \| 40,565 \| \| Total assets \| $758,376 \| $619,003 \| \| Liabilities and stockholders’ equity \| \| \| \| Current liabilities: \| \| \| \| Accounts payable \| $42,416 \| $27,724 \| \| Current porti"

## fg-029 - financial_lookup - medium

- [ ] **Q:** What was revenue for Microsoft's Intelligent Cloud segment in fiscal year 2026?
- **Tickers:** MSFT
- **Gold answer:** Intelligent Cloud revenue was $137,791 million in fiscal year 2026, up 30% from $106,265 million.
- **Label 1** (MSFT, verified, 1 matching chunk(s)): `Intelligent Cloud` + `Revenue $137,791 $106,265 30%`
  - `MSFT-10-K-2026-c0071`: "er Copilot advertising expenses. Operating income increased $26.7 billion or 21% driven by growth in Productivity and Business Processes and Intelligent Cloud. Revenue and operating income both included a favorable foreign currency impact of 2%. 37 PART II Item 7 Current year net income and diluted"

## fg-030 - financial_lookup - medium

- [ ] **Q:** How much LinkedIn revenue did Microsoft report for fiscal year 2025?
- **Tickers:** MSFT
- **Gold answer:** Microsoft reported LinkedIn revenue of $17,812 million for fiscal year 2025 (year ended June 30, 2025).
- **Notes:** Prior-year column (fiscal 2026 LinkedIn was $19,817M).
- **Label 1** (MSFT, verified, 1 matching chunk(s)): `LinkedIn 19,817 17,812 16,372`
  - `MSFT-10-K-2026-c0155`: "79,828 \| \| Microsoft 365 Commercial products and cloud services \| 101,997 \| 87,767 \| 76,969 \| \| XBOX \| 21,790 \| 23,455 \| 21,503 \| \| LinkedIn \| 19,817 \| 17,812 \| 16,372 \| \| Windows and Devices \| 17,084 \| 17,314 \| 17,026 \| \| Search advertising \| 15,176 \| 13,878 \| 12,306 \| \| Microsoft 365 Consumer prod"

## fg-031 - financial_lookup - easy

- [ ] **Q:** What were Amazon's total net sales in 2025?
- **Tickers:** AMZN
- **Gold answer:** Amazon's total net sales were $716,924 million in 2025.
- **Notes:** Amazon's statement lists columns 2023 | 2024 | 2025 (oldest first).
- **Label 1** (AMZN, verified, 1 matching chunk(s)): `Total net sales 574,785 637,959 716,924`
  - `AMZN-10-K-2026-c0076`: "--- \| --- \| --- \| \| Net product sales \| $255,887 \| $272,311 \| $296,266 \| \| Net service sales \| 318,898 \| 365,648 \| 420,658 \| \| Total net sales \| 574,785 \| 637,959 \| 716,924 \| \| Operating expenses: \| \| \| \| \| Cost of sales \| 304,739 \| 326,288 \| 356,414 \| \| Fulfillment \| 90,619 \| 98,505 \| 109,074 \| \| T"

## fg-032 - financial_lookup - medium

- [ ] **Q:** What was Amazon's net income in 2024?
- **Tickers:** AMZN
- **Gold answer:** Amazon's net income was $59,248 million in 2024.
- **Notes:** Columns are 2023 | 2024 | 2025; 2025 net income was $77,670M.
- **Label 1** (AMZN, verified, 4 matching chunk(s)): `Net income $30,425 $59,248 $77,670`
  - `AMZN-10-K-2026-c0074`: "CASH, CASH EQUIVALENTS, AND RESTRICTED CASH, BEGINNING OF PERIOD \| $54,253 \| $73,890 \| $82,312 \| \| OPERATING ACTIVITIES: \| \| \| \| \| Net income \| 30,425 \| 59,248 \| 77,670 \| \| Adjustments to reconcile net income to net cash from operating activities: \| \| \| \| \| Depreciation and amortization of property"
  - `AMZN-10-K-2026-c0076`: "sion for income taxes \| (7,120) \| (9,265) \| (19,087) \| \| Equity-method investment activity, net of tax \| (12) \| (101) \| (554) \| \| Net income \| $30,425 \| $59,248 \| $77,670 \| \| Basic earnings per share \| $2.95 \| $5.66 \| $7.29 \| \| Diluted earnings per share \| $2.90 \| $5.53 \| $7.17 \|"

## fg-033 - financial_lookup - easy

- [ ] **Q:** What were Amazon's diluted earnings per share in 2025?
- **Tickers:** AMZN
- **Gold answer:** Amazon's diluted earnings per share were $7.17 in 2025.
- **Label 1** (AMZN, verified, 1 matching chunk(s)): `Diluted earnings per share $2.90 $5.53 $7.17`
  - `AMZN-10-K-2026-c0076`: "\| (12) \| (101) \| (554) \| \| Net income \| $30,425 \| $59,248 \| $77,670 \| \| Basic earnings per share \| $2.95 \| $5.66 \| $7.29 \| \| Diluted earnings per share \| $2.90 \| $5.53 \| $7.17 \|"

## fg-034 - financial_lookup - easy

- [ ] **Q:** What were AWS segment net sales in 2025?
- **Tickers:** AMZN
- **Gold answer:** AWS net sales were $128,725 million in 2025, up 20% from $107,556 million in 2024.
- **Label 1** (AMZN, verified, 1 matching chunk(s)): `AWS 107,556 128,725`
  - `AMZN-10-K-2026-c0054`: "31, 2024 \| 2025 \| \| --- \| --- \| --- \| \| Net Sales: \| \| \| \| North America \| $387,497 \| $426,305 \| \| International \| 142,906 \| 161,894 \| \| AWS \| 107,556 \| 128,725 \| \| Consolidated \| $637,959 \| $716,924 \| \| Year-over-year Percentage Growth: \| \| \| \| North America \| 10% \| 10% \| \| International \| 9 \| 13"

## fg-035 - financial_lookup - medium

- [ ] **Q:** What were Amazon's net sales attributed to Germany in 2025?
- **Tickers:** AMZN
- **Gold answer:** Amazon's net sales attributed to Germany were $45,900 million in 2025.
- **Notes:** Note 10 geographic table (columns 2023 | 2024 | 2025).
- **Label 1** (AMZN, verified, 1 matching chunk(s)): `Germany 37,588 40,856 45,900`
  - `AMZN-10-K-2026-c0139`: "ns): \| \| Year Ended December 31, 2023 \| 2024 \| 2025 \| \| --- \| --- \| --- \| --- \| \| United States \| $395,637 \| $438,015 \| $489,657 \| \| Germany \| 37,588 \| 40,856 \| 45,900 \| \| United Kingdom \| 33,591 \| 37,855 \| 43,212 \| \| Japan \| 26,002 \| 27,401 \| 30,688 \| \| Rest of world \| 81,967 \| 93,832 \| 107,467 \| \|"

## fg-036 - financial_lookup - easy

- [ ] **Q:** What were Alphabet's total revenues in 2025?
- **Tickers:** GOOGL
- **Gold answer:** Alphabet's total revenues were $402,836 million in 2025, up 15% from 2024.
- **Label 1** (GOOGL, verified, 1 matching chunk(s)): `Total revenues $350,018 $402,836`
  - `GOOGL-10-K-2026-c0070`: "\| 304,930 \| 342,721 \| \| Google Cloud \| 43,229 \| 58,705 \| \| Other Bets \| 1,648 \| 1,537 \| \| Hedging gains (losses) \| 211 \| (127) \| \| Total revenues \| $350,018 \| $402,836 \| Google Services Google Advertising Google Search & other Google Search & other revenues increased $26.4 billion from 2024 to 2025"

## fg-037 - financial_lookup - easy

- [ ] **Q:** What was Alphabet's net income in 2025?
- **Tickers:** GOOGL
- **Gold answer:** Alphabet's net income was $132,170 million in 2025.
- **Label 1** (GOOGL, verified, 1 matching chunk(s)): `Net income $100,118 $132,170`
  - `GOOGL-10-K-2026-c0068`: "9,039 \| $16,649 \| 15% \| \| Operating margin \| 32% \| 32% \| \| 0% \| \| Other income (expense), net \| $7,425 \| $29,787 \| $22,362 \| 301% \| \| Net income \| $100,118 \| $132,170 \| $32,052 \| 32% \| \| Diluted net income per share (1) \| $8.04 \| $10.81 \| $2.77 \| 34% \|"

## fg-038 - financial_lookup - easy

- [ ] **Q:** What was Alphabet's diluted net income per share in 2025?
- **Tickers:** GOOGL
- **Gold answer:** Alphabet's diluted net income per share was $10.81 in 2025.
- **Label 1** (GOOGL, verified, 2 matching chunk(s)): `Diluted net income per share` + `$8.04 $10.81`
  - `GOOGL-10-K-2026-c0068`: "32% \| \| 0% \| \| Other income (expense), net \| $7,425 \| $29,787 \| $22,362 \| 301% \| \| Net income \| $100,118 \| $132,170 \| $32,052 \| 32% \| \| Diluted net income per share (1) \| $8.04 \| $10.81 \| $2.77 \| 34% \|"
  - `GOOGL-10-K-2026-c0098`: "\| 19,697 \| 26,656 \| \| Net income \| $73,795 \| $100,118 \| $132,170 \| \| Basic net income per share (Note 12) \| $5.84 \| $8.13 \| $10.91 \| \| Diluted net income per share (Note 12) \| $5.80 \| $8.04 \| $10.81 \| See accompanying notes. 49. Table of Contents Alphabet Inc. Alphabet Inc. CONSOLIDATED STATEMENTS"

## fg-039 - financial_lookup - easy

- [ ] **Q:** What were Google Cloud revenues in 2025?
- **Tickers:** GOOGL
- **Gold answer:** Google Cloud revenues were $58,705 million in 2025.
- **Label 1** (GOOGL, verified, 1 matching chunk(s)): `Google Cloud 43,229 58,705`
  - `GOOGL-10-K-2026-c0070`: "264,590 \| 294,691 \| \| Google subscriptions, platforms, and devices \| 40,340 \| 48,030 \| \| Google Services total \| 304,930 \| 342,721 \| \| Google Cloud \| 43,229 \| 58,705 \| \| Other Bets \| 1,648 \| 1,537 \| \| Hedging gains (losses) \| 211 \| (127) \| \| Total revenues \| $350,018 \| $402,836 \| Google Services Goo"

## fg-040 - financial_lookup - medium

- [ ] **Q:** What were Alphabet's YouTube ads revenues in 2024?
- **Tickers:** GOOGL
- **Gold answer:** YouTube ads revenues were $36,147 million in 2024.
- **Notes:** Prior-year column (2025 was $40,367M).
- **Label 1** (GOOGL, verified, 1 matching chunk(s)): `YouTube ads 36,147 40,367`
  - `GOOGL-10-K-2026-c0070`: "by type (in millions): \| \| Year Ended December 31, 2024 \| 2025 \| \| --- \| --- \| --- \| \| Google Search & other \| $198,084 \| $224,532 \| \| YouTube ads \| 36,147 \| 40,367 \| \| Google Network \| 30,359 \| 29,792 \| \| Google advertising \| 264,590 \| 294,691 \| \| Google subscriptions, platforms, and devices \| 40,3"

## fg-041 - financial_lookup - easy

- [ ] **Q:** What was NVIDIA's revenue for fiscal year 2026?
- **Tickers:** NVDA
- **Gold answer:** NVIDIA's revenue was $215,938 million for fiscal year 2026 (year ended January 25, 2026), up 65%.
- **Label 1** (NVDA, verified, 4 matching chunk(s)): `Revenue $215,938 $130,497`
  - `NVDA-10-K-2026-c0089`: "2026 Summary \| \| Year Ended Jan 25, 2026 ($ in millions, except per share data) \| Jan 26, 2025 \| Change \| \| --- \| --- \| --- \| --- \| \| Revenue \| $215,938 \| $130,497 \| Up 65% \| \| Gross margin \| 71.1% \| 75.0% \| -3.9 pts \| \| Operating expenses \| $23,076 \| $16,405 \| Up 41% \| \| Operating income \| $130,38"
  - `NVDA-10-K-2026-c0118`: "of Income (In millions, except per share data) \| \| Year Ended Jan 25, 2026 \| Jan 26, 2025 \| Jan 28, 2024 \| \| --- \| --- \| --- \| --- \| \| Revenue \| $215,938 \| $130,497 \| $60,922 \| \| Cost of revenue \| 62,475 \| 32,639 \| 16,621 \| \| Gross profit \| 153,463 \| 97,858 \| 44,301 \| \| Operating expenses \| \| \| \| \|"

## fg-042 - financial_lookup - easy

- [ ] **Q:** What was NVIDIA's net income for fiscal year 2026?
- **Tickers:** NVDA
- **Gold answer:** NVIDIA's net income was $120,067 million for fiscal year 2026.
- **Label 1** (NVDA, verified, 5 matching chunk(s)): `Net income $120,067 $72,880`
  - `NVDA-10-K-2026-c0089`: "\| 71.1% \| 75.0% \| -3.9 pts \| \| Operating expenses \| $23,076 \| $16,405 \| Up 41% \| \| Operating income \| $130,387 \| $81,453 \| Up 60% \| \| Net income \| $120,067 \| $72,880 \| Up 65% \| \| Net income per diluted share \| $4.90 \| $2.94 \| Up 67% \| Revenue for fiscal year 2026 was $215.9 billion, up 65% from a ye"
  - `NVDA-10-K-2026-c0118`: "\| 11,063 \| 2,573 \| 846 \| \| Income before income tax \| 141,450 \| 84,026 \| 33,818 \| \| Income tax expense \| 21,383 \| 11,146 \| 4,058 \| \| Net income \| $120,067 \| $72,880 \| $29,760 \| \| Net income per share: \| \| \| \| \| Basic \| $4.93 \| $2.97 \| $1.21 \| \| Diluted \| $4.90 \| $2.94 \| $1.19 \| \| Weighted average s"

## fg-043 - financial_lookup - medium

- [ ] **Q:** What was NVIDIA's net income per diluted share for fiscal year 2025?
- **Tickers:** NVDA
- **Gold answer:** NVIDIA's net income per diluted share was $2.94 for fiscal year 2025 (year ended January 26, 2025).
- **Notes:** Prior-year column (fiscal 2026 was $4.90).
- **Label 1** (NVDA, verified, 1 matching chunk(s)): `Net income per diluted share $4.90 $2.94`
  - `NVDA-10-K-2026-c0089`: "$23,076 \| $16,405 \| Up 41% \| \| Operating income \| $130,387 \| $81,453 \| Up 60% \| \| Net income \| $120,067 \| $72,880 \| Up 65% \| \| Net income per diluted share \| $4.90 \| $2.94 \| Up 67% \| Revenue for fiscal year 2026 was $215.9 billion, up 65% from a year ago. Data Center revenue for fiscal year 2026 wa"

## fg-044 - financial_lookup - medium

- [ ] **Q:** What was NVIDIA's Data Center end-market revenue in fiscal year 2026?
- **Tickers:** NVDA
- **Gold answer:** Data Center revenue was $193,737 million in fiscal year 2026.
- **Notes:** Revenue by End Market table; distinct from Compute & Networking segment revenue ($193,479M).
- **Label 1** (NVDA, verified, 1 matching chunk(s)): `Data Center $193,737 $115,186`
  - `NVDA-10-K-2026-c0170`: "\| Year Ended Jan 25, 2026 \| Jan 26, 2025 \| Jan 28, 2024 \| \| --- \| --- \| --- \| --- \| \| Revenue by End Market: \| (In millions) \| \| \| \| Data Center \| $193,737 \| $115,186 \| $47,525 \| \| Compute \| 162,361 \| 102,196 \| 38,950 \| \| Networking \| 31,376 \| 12,990 \| 8,575 \| \| Gaming \| 16,042 \| 11,350 \| 10,447 \| \|"

## fg-045 - financial_lookup - medium

- [ ] **Q:** How much of NVIDIA's fiscal 2026 revenue came from customers headquartered in China (including Hong Kong)?
- **Tickers:** NVDA
- **Gold answer:** Revenue from customers headquartered in China (including Hong Kong) was $19,677 million in fiscal 2026, down from $25,048 million in fiscal 2025.
- **Notes:** Geography is based on customer headquarters location, per the filing.
- **Label 1** (NVDA, verified, 1 matching chunk(s)): `China (including Hong Kong) 19,677 25,048`
  - `NVDA-10-K-2026-c0169`: "cation (1): \| (In millions) \| \| \| \| United States \| $149,617 \| $77,482 \| $31,533 \| \| Taiwan (2) \| 42,345 \| 23,600 \| 14,912 \| \| China (including Hong Kong) \| 19,677 \| 25,048 \| 12,330 \| \| Other \| 4,299 \| 4,367 \| 2,147 \| \| Total revenue \| $215,938 \| $130,497 \| $60,922 \| (1) In the third quarter of fisc"

## fg-046 - financial_lookup - easy

- [ ] **Q:** What were Tesla's total revenues in 2025?
- **Tickers:** TSLA
- **Gold answer:** Tesla's total revenues were $94,827 million in 2025, down 3% from $97,690 million in 2024.
- **Label 1** (TSLA, verified, 3 matching chunk(s)): `Total revenues 94,827 97,690`
  - `TSLA-10-K-2026-c0084`: "\| (6)% \| (3,134) \| (3)% \| \| Energy generation and storage segment revenue \| 12,771 \| 10,086 \| 6,035 \| 2,685 \| 27% \| 4,051 \| 67% \| \| Total revenues \| $94,827 \| $97,690 \| $96,773 \| $(2,863) \| (3)% \| $917 \| 1% \| Automotive & Services and Other Segment Automotive sales revenue includes revenues"
  - `TSLA-10-K-2026-c0108`: "26 \| 77,070 \| 82,419 \| \| Energy generation and storage \| 12,771 \| 10,086 \| 6,035 \| \| Services and other \| 12,530 \| 10,534 \| 8,319 \| \| Total revenues \| 94,827 \| 97,690 \| 96,773 \| \| Cost of revenues \| \| \| \| \| Automotive sales \| 56,267 \| 61,870 \| 65,121 \| \| Automotive leasing \| 898 \| 1,003 \| 1,268 \| \|"

## fg-047 - financial_lookup - easy

- [ ] **Q:** What was Tesla's net income attributable to common stockholders in 2025?
- **Tickers:** TSLA
- **Gold answer:** Net income attributable to common stockholders was $3,794 million in 2025.
- **Label 1** (TSLA, verified, 2 matching chunk(s)): `Net income attributable to common stockholders $3,794 $7,091`
  - `TSLA-10-K-2026-c0109`: "attributable to noncontrolling interests and redeemable noncontrolling interests in subsidiaries \| 61 \| 62 \| (23) \| \| Net income attributable to common stockholders \| $3,794 \| $7,091 \| $14,997 \| \| Net income per share of common stock attributable to common stockholders \| \| \| \| \| Basic \| $1.18 \| $2.2"
  - `TSLA-10-K-2026-c0132`: "per share of common stock (in millions): \| \| Year Ended December 31, 2025 \| 2024 \| 2023 \| \| --- \| --- \| --- \| --- \| \| Net income attributable to common stockholders \| $3,794 \| $7,091 \| $14,997 \| \| Less: Buy-outs of noncontrolling interests \| — \| (39) \| (2) \| \| Net income used in computing basic and"

## fg-048 - financial_lookup - easy

- [ ] **Q:** What was Tesla's diluted net income per share in 2025?
- **Tickers:** TSLA
- **Gold answer:** Tesla's diluted net income per share attributable to common stockholders was $1.08 in 2025.
- **Label 1** (TSLA, verified, 1 matching chunk(s)): `Diluted $1.08 $2.04 $4.30`
  - `TSLA-10-K-2026-c0109`: "91 \| $14,997 \| \| Net income per share of common stock attributable to common stockholders \| \| \| \| \| Basic \| $1.18 \| $2.23 \| $4.73 \| \| Diluted \| $1.08 \| $2.04 \| $4.30 \| \| Weighted average shares used in computing net income per share of common stock \| \| \| \| \| Basic \| 3,225 \| 3,197 \| 3,174 \| \| Diluted"

## fg-049 - financial_lookup - easy

- [ ] **Q:** What were Tesla's energy generation and storage revenues in 2025?
- **Tickers:** TSLA
- **Gold answer:** Energy generation and storage revenues were $12,771 million in 2025, up from $10,086 million in 2024.
- **Label 1** (TSLA, verified, 1 matching chunk(s)): `Energy generation and storage 12,771 10,086`
  - `TSLA-10-K-2026-c0108`: "3 \| 2,763 \| 1,790 \| \| Automotive leasing \| 1,712 \| 1,827 \| 2,120 \| \| Total automotive revenues \| 69,526 \| 77,070 \| 82,419 \| \| Energy generation and storage \| 12,771 \| 10,086 \| 6,035 \| \| Services and other \| 12,530 \| 10,534 \| 8,319 \| \| Total revenues \| 94,827 \| 97,690 \| 96,773 \| \| Cost of revenues \|"

## fg-050 - financial_lookup - easy

- [ ] **Q:** What were Tesla's total assets as of December 31, 2025?
- **Tickers:** TSLA
- **Gold answer:** Tesla's total assets were $137,806 million as of December 31, 2025.
- **Label 1** (TSLA, verified, 1 matching chunk(s)): `Total assets $137,806 $122,070`
  - `TSLA-10-K-2026-c0106`: "\| 5,160 \| \| Digital assets \| 1,008 \| 1,076 \| \| Deferred tax assets \| 6,925 \| 6,524 \| \| Other non-current assets \| 5,045 \| 4,609 \| \| Total assets \| $137,806 \| $122,070 \| \| Liabilities \| \| \| \| Current liabilities \| \| \| \| Accounts payable \| $13,371 \| $12,474 \| \| Accrued liabilities and other \| 13,279"

## fg-051 - financial_lookup - easy

- [ ] **Q:** What was JPMorgan Chase's total net revenue in 2025?
- **Tickers:** JPM
- **Gold answer:** JPMorgan Chase's total net revenue (reported) was $182,447 million in 2025, up 3%.
- **Notes:** Reported basis; managed-basis total net revenue was $185,581M.
- **Label 1** (JPM, verified, 4 matching chunk(s)): `Total net revenue 182,447 177,556`
  - `JPM-10-K-2026-c0110`: "\| \| \| --- \| --- \| --- \| --- \| --- \| --- \| --- \| \| \| 2025 \| \| 2024 \| \| 2023 \| \| \| Selected income statement data \| \| \| \| \| \| \| \| Total net revenue \| \| $182,447 \| \| $177,556 \| (g) \| $158,104 \| \| Total noninterest expense \| \| 95,640 \| \| 91,797 \| (g) \| 87,172 \| \| Pre-provision profit (a) \| \| 86,807 \| \|"
  - `JPM-10-K-2026-c0118`: "come statement data \| \| \| \| \| \| Noninterest revenue \| $87,004 \| $84,973 \| \| 2% \| \| Net interest income \| 95,443 \| 92,583 \| \| 3 \| \| Total net revenue \| 182,447 \| 177,556 \| \| 3 \| \| Total noninterest expense \| 95,640 \| 91,797 \| \| 4 \| \| Pre-provision profit \| 86,807 \| 85,759 \| \| 1 \| \| Provision for cred"

## fg-052 - financial_lookup - easy

- [ ] **Q:** What was JPMorgan Chase's net income in 2025?
- **Tickers:** JPM
- **Gold answer:** JPMorgan Chase's net income was $57,048 million in 2025, down 2% from 2024.
- **Label 1** (JPM, verified, 9 matching chunk(s)): `Net income 57,048 58,471`
  - `JPM-10-K-2026-c0110`: "20 \| \| Income before income tax expense \| \| 72,595 \| \| 75,081 \| \| 61,612 \| \| Income tax expense \| \| 15,547 \| \| 16,610 \| \| 12,060 \| \| Net income \| \| $57,048 \| \| $58,471 \| \| $49,552 \| \| Earnings per share data \| \| \| \| \| \| \| \| Net income: Basic \| \| $20.05 \| \| $19.79 \| \| $16.25 \| \| Diluted \| \| 20.02 \| \|"
  - `JPM-10-K-2026-c0118`: "e \| 95,640 \| 91,797 \| \| 4 \| \| Pre-provision profit \| 86,807 \| 85,759 \| \| 1 \| \| Provision for credit losses \| 14,212 \| 10,678 \| \| 33 \| \| Net income \| 57,048 \| 58,471 \| \| (2) \| \| Diluted earnings per share \| 20.02 \| 19.75 \| \| 1 \| \| Selected ratios and metrics \| \| \| \| \| \| Return on common equity \| 17%"

## fg-053 - financial_lookup - easy

- [ ] **Q:** What were JPMorgan Chase's diluted earnings per share in 2025?
- **Tickers:** JPM
- **Gold answer:** JPMorgan Chase's diluted earnings per share were $20.02 in 2025.
- **Label 1** (JPM, verified, 2 matching chunk(s)): `Diluted earnings per share 20.02 19.75`
  - `JPM-10-K-2026-c0118`: "it \| 86,807 \| 85,759 \| \| 1 \| \| Provision for credit losses \| 14,212 \| 10,678 \| \| 33 \| \| Net income \| 57,048 \| 58,471 \| \| (2) \| \| Diluted earnings per share \| 20.02 \| 19.75 \| \| 1 \| \| Selected ratios and metrics \| \| \| \| \| \| Return on common equity \| 17% \| 18% \| \| \| \| Return on tangible common equity \|"
  - `JPM-10-K-2026-c0361`: "5,681 \| $56,868 \| $47,760 \| \| Net income per common share data \| \| \| \| \| Basic earnings per share \| $20.05 \| $19.79 \| $16.25 \| \| Diluted earnings per share \| 20.02 \| 19.75 \| 16.23 \| \| Weighted-average basic shares \| 2,776.5 \| 2,873.9 \| 2,938.6 \| \| Weighted-average diluted shares \| 2,781.5 \| 2,879.0"

## fg-054 - financial_lookup - easy

- [ ] **Q:** What were JPMorgan Chase's total assets at December 31, 2025?
- **Tickers:** JPM
- **Gold answer:** JPMorgan Chase's total assets were $4,424,900 million at December 31, 2025.
- **Label 1** (JPM, verified, 2 matching chunk(s)): `Total assets $4,424,900 $4,002,814`
  - `JPM-10-K-2026-c0112`: "s, net of allowance for credit losses \| \| 777,332 \| \| 681,320 \| \| 571,552 \| \| Loans \| \| 1,493,429 \| \| 1,347,988 \| \| 1,323,706 \| \| Total assets \| \| 4,424,900 \| \| 4,002,814 \| \| 3,875,393 \| \| Deposits \| \| 2,559,320 \| \| 2,406,032 \| \| 2,400,688 \| \| Long-term debt \| \| 435,206 \| \| 401,418 \| \| 391,825 \| \| C"
  - `JPM-10-K-2026-c0133`: "4 \| 32,223 \| 12 \| \| Goodwill, MSRs and other intangible assets \| 64,458 \| 64,560 \| — \| \| Other assets \| 198,775 \| 178,197 \| 12 \| \| Total assets \| $4,424,900 \| $4,002,814 \| 11% \| Cash and due from banks and deposits with banks decreased driven by Markets activities in CIB"

## fg-055 - financial_lookup - medium

- [ ] **Q:** What was JPMorgan Chase's Standardized CET1 capital ratio at the end of 2025?
- **Tickers:** JPM
- **Gold answer:** The Standardized CET1 capital ratio was 14.6% at December 31, 2025, compared with 15.7% a year earlier.
- **Label 1** (JPM, verified, 1 matching chunk(s)): `CET1 capital 14.6% 15.7%`
  - `JPM-10-K-2026-c0118`: "\| $126.99 \| $116.07 \| \| 9 \| \| Tangible book value per share \| 107.56 \| 97.3 \| \| 11 \| \| Capital ratios - Standardized (a)(b) \| \| \| \| \| \| CET1 capital \| 14.6% \| 15.7% \| \| \| \| Tier 1 capital \| 15.5 \| 16.8 \| \| \| \| Total capital \| 17.4 \| 18.5 \| \| \| \| Memo: \| \| \| \| \| \| NII excluding Markets (c) \| $92,591"

## fg-056 - financial_lookup - easy

- [ ] **Q:** What were Coca-Cola's net operating revenues in 2025?
- **Tickers:** KO
- **Gold answer:** Coca-Cola's net operating revenues were $47,941 million in 2025.
- **Label 1** (KO, verified, 3 matching chunk(s)): `Net Operating Revenues $47,941 $47,061`
  - `KO-10-K-2026-c0150`: "MENTS OF INCOME (In millions except per share data) \| Year Ended December 31, \| 2025 \| 2024 \| 2023 \| \| --- \| --- \| --- \| --- \| \| Net Operating Revenues \| $47,941 \| $47,061 \| $45,754 \| \| Cost of goods sold \| 18,397 \| 18,324 \| 18,520 \| \| Gross Profit \| 29,544 \| 28,737 \| 27,234 \| \| Selling, general and"
  - `KO-10-K-2026-c0267`: "2023 \| \| --- \| --- \| --- \| --- \| \| United States \| $19,127 \| $18,362 \| $16,550 \| \| International \| 28,814 \| 28,699 \| 29,204 \| \| Net operating revenues \| $47,941 \| $47,061 \| $45,754 \| For the year"

## fg-057 - financial_lookup - easy

- [ ] **Q:** What was net income attributable to shareowners of The Coca-Cola Company in 2025?
- **Tickers:** KO
- **Gold answer:** Net income attributable to shareowners of The Coca-Cola Company was $13,107 million in 2025.
- **Label 1** (KO, verified, 2 matching chunk(s)): `Net Income Attributable to Shareowners of The Coca-Cola Company $13,107`
  - `KO-10-K-2026-c0150`: ",137 \| 10,649 \| 10,703 \| \| Less: Net income (loss) attributable to noncontrolling interests \| 30 \| 18 \| (11) \| \| Net Income Attributable to Shareowners of The Coca-Cola Company \| $13,107 \| $10,631 \| $10,714 \| \| Basic Net Income Per Share 1 \| $3.05 \| $2.47 \| $2.48 \| \| Diluted Net Income Per Share 1 \|"
  - `KO-10-K-2026-c0156`: "1 \| 19,801 \| 19,209 \| \| Reinvested Earnings \| \| \| \| \| Balance at beginning of year \| 76,054 \| 73,782 \| 71,019 \| \| Net income attributable to shareowners of The Coca-Cola Company \| 13,107 \| 10,631 \| 10,714 \| \| Dividends (per share — $2.04 , $1.94 and $1.84 in 2025, 2024 and 2023, respectively) \| (8,7"

## fg-058 - financial_lookup - easy

- [ ] **Q:** What was Coca-Cola's diluted net income per share in 2025?
- **Tickers:** KO
- **Gold answer:** Coca-Cola's diluted net income per share was $3.04 in 2025.
- **Label 1** (KO, verified, 1 matching chunk(s)): `Diluted Net Income Per Share 1 $3.04 $2.46`
  - `KO-10-K-2026-c0150`: "hareowners of The Coca-Cola Company \| $13,107 \| $10,631 \| $10,714 \| \| Basic Net Income Per Share 1 \| $3.05 \| $2.47 \| $2.48 \| \| Diluted Net Income Per Share 1 \| $3.04 \| $2.46 \| $2.47 \| \| Average Shares Outstanding — Basic \| 4,303 \| 4,309 \| 4,323 \| \| Effect of dilutive securities \| 10 \| 11 \| 16 \| \| Av"

## fg-059 - financial_lookup - easy

- [ ] **Q:** What were Coca-Cola's total assets as of December 31, 2025?
- **Tickers:** KO
- **Gold answer:** Coca-Cola's total assets were $104,816 million as of December 31, 2025.
- **Label 1** (KO, verified, 1 matching chunk(s)): `Total Assets $104,816 $100,549`
  - `KO-10-K-2026-c0152`: "Trademarks with indefinite lives \| 12,531 \| 13,301 \| \| Goodwill \| 15,491 \| 18,139 \| \| Other noncurrent assets \| 14,696 \| 13,403 \| \| Total Assets \| $104,816 \| $100,549 \| \| LIABILITIES AND EQUITY \| \| \| \| Current Liabilities \| \| \| \| Accounts payable and accrued expenses \| $14,813 \| $21,712 \| \| Loans a"

## fg-060 - financial_lookup - medium

- [ ] **Q:** What percentage of Coca-Cola's 2025 net operating revenues came from the North America operating segment?
- **Tickers:** KO
- **Gold answer:** The North America operating segment accounted for 40.8% of Coca-Cola's net operating revenues in 2025 (40.1% in 2024).
- **Notes:** Segment share-of-revenue table in MD&A.
- **Label 1** (KO, verified, 1 matching chunk(s)): `North America 40.8 40.1`
  - `KO-10-K-2026-c0118`: "is as follows: \| Year Ended December 31, \| 2025 \| 2024 \| \| --- \| --- \| --- \| \| EMEA \| 22.6% \| 21.8% \| \| Latin America \| 13.2 \| 13.8 \| \| North America \| 40.8 \| 40.1 \| \| Asia Pacific \| 11.1 \| 10.9 \| \| Bottling Investments \| 12.0 \| 13.2 \| \| Corporate \| 0.3 \| 0.2 \| \| Total \| 100.0% \| 100.0% \| The percen"

## fg-081 - business - easy

- [ ] **Q:** What share of Apple's fiscal 2025 net sales came through direct versus indirect distribution channels?
- **Tickers:** AAPL
- **Gold answer:** Direct channels accounted for 40% and indirect channels (e.g. third-party cellular carriers and other resellers) for 60% of total net sales in 2025.
- **Label 1** (AAPL, verified, 2 matching chunk(s)): `direct and indirect distribution channels accounted for 40% and 60%`
  - `AAPL-10-K-2025-c0005`: "esellers, for the sale of its products and certain of its services. During 2025, the Company’s net sales through its direct and indirect distribution channels accounted for 40% and 60%, respectively"
  - `AAPL-10-K-2025-c0006`: "esellers, for the sale of its products and certain of its services. During 2025, the Company’s net sales through its direct and indirect distribution channels accounted for 40% and 60%, respectively, of total net sales. Competition The markets for the Company’s products and services are highly compe"

## fg-082 - legal - medium

- [ ] **Q:** What changes has Apple made in the EU to comply with the Digital Markets Act, and what risk does it note?
- **Tickers:** AAPL
- **Gold answer:** Apple changed iOS, iPadOS, the App Store and Safari in the EU, including new business terms and alternative fee structures, alternative app distribution, alternative payment processing, and additional developer tools/APIs; its compliance plan has been challenged by the Commission and the DMA provides for significant fines and penalties.
- **Label 1** (AAPL, verified, 1 matching chunk(s)): `seeks to comply with the Digital Markets Act`
  - `AAPL-10-K-2025-c0032`: "luding the Company. For example, the Company has implemented changes to iOS, iPadOS, the App Store and Safari ® in the EU as it seeks to comply with the Digital Markets Act (“DMA”), including new business terms and alternative fee structures for iOS and iPadOS apps, alternative methods of distributi"
- **Label 2** (AAPL, verified, 1 matching chunk(s)): `The DMA provides for significant fines and penalties for noncompliance`
  - `AAPL-10-K-2025-c0032`: "he DMA’s obligations, it has been challenged by the Commission and may be challenged further by private litigants. The DMA provides for significant fines and penalties for noncompliance. While the changes introduced by the Company in the EU are intended to reduce new privacy and security risks that"

## fg-083 - geoeconomic - medium

- [ ] **Q:** What U.S. government trade investigation affecting semiconductors does Apple mention in its 10-K?
- **Tickers:** AAPL
- **Gold answer:** Apple notes that the U.S. Department of Commerce initiated an investigation under Section 232 of the Trade Expansion Act of 1962 into imports of semiconductors, semiconductor manufacturing equipment, and derivative products, including downstream products containing semiconductors.
- **Label 1** (AAPL, verified, 3 matching chunk(s)): `initiated an investigation under Section 232 of the Trade Expansion Act`
  - `AAPL-10-K-2025-c0013`: "h may include additional sector-based tariffs or other measures. For example, the U.S. Department of Commerce has initiated an investigation under Section 232 of the Trade Expansion Act of 1962, as amended, into, among other things, imports of semiconductors, semiconductor manufacturing equipment, a"
  - `AAPL-10-K-2025-c0049`: "h may include additional sector-based tariffs or other measures. For example, the U.S. Department of Commerce has initiated an investigation under Section 232 of the Trade Expansion Act of 1962, as amended, into, among other things, imports of semiconductors, semiconductor manufacturing equipment, a"

## fg-084 - business - medium

- [ ] **Q:** How did Microsoft's investments in OpenAI affect its fiscal 2026 net income and diluted EPS?
- **Tickers:** MSFT
- **Gold answer:** Net gains from investments in OpenAI increased fiscal 2026 net income by $5.0 billion and diluted EPS by $0.67 (in fiscal 2025, net losses reduced them by $3.6 billion and $0.49).
- **Label 1** (MSFT, verified, 1 matching chunk(s)): `net gains from investments in OpenAI, which resulted in an increase in net income and diluted EPS of $5.0 billion and $0.67`
  - `MSFT-10-K-2026-c0071`: ". 37 PART II Item 7 Current year net income and diluted EPS were positively impacted by net gains from investments in OpenAI, which resulted in an increase in net income and diluted EPS of $5.0 billion and $0.67, respectively. Prior year net income and diluted EPS were negatively impacted by net los"

## fg-085 - business - medium

- [ ] **Q:** What does Microsoft include in 'Microsoft Cloud' revenue, and how much was it in fiscal 2026?
- **Tickers:** MSFT
- **Gold answer:** Microsoft Cloud revenue comprises Microsoft 365 Commercial cloud, Azure and other cloud services, the commercial portion of LinkedIn, and Dynamics 365; it increased 27% to $214.4 billion in fiscal 2026.
- **Label 1** (MSFT, verified, 1 matching chunk(s)): `Microsoft Cloud revenue increased 27% to $214.4 billion`
  - `MSFT-10-K-2026-c0065`: "ther products and services; and income taxes. Highlights from fiscal year 2026 compared with fiscal year 2025 included: • Microsoft Cloud revenue increased 27% to $214.4 billion. • Commercial remaining performance obligation increased 84% to $678 billion. • Microsoft 365 Commercial cloud revenue inc"
- **Label 2** (MSFT, verified, 2 matching chunk(s)): `includes Microsoft 365 Commercial cloud, Azure and other cloud services, the commercial portion of LinkedIn, and Dynamics 365`
  - `MSFT-10-K-2026-c0155`: "2 \| 45 \| \| Total \| $331,839 \| $281,724 \| $245,122 \| Our Microsoft Cloud revenue, which includes Microsoft 365 Commercial cloud, Azure and other cloud services, the commercial portion of LinkedIn, and Dynamics 365, was $"
  - `MSFT-10-K-2026-c0156`: "Our Microsoft Cloud revenue, which includes Microsoft 365 Commercial cloud, Azure and other cloud services, the commercial portion of LinkedIn, and Dynamics 365, was $ 214.4 billion, $ 168.9 billion, and $ 137.7 billion in fiscal years 2026, 2025, and 2024, respectively. These amounts are included i"

## fg-086 - business - easy

- [ ] **Q:** How many full-time employees did Microsoft have at June 30, 2026, and how were they split between the U.S. and internationally?
- **Tickers:** MSFT
- **Gold answer:** Approximately 223,000 full-time employees: 121,000 in the U.S. and 102,000 internationally.
- **Label 1** (MSFT, verified, 1 matching chunk(s)): `employed approximately 223,000 people on a full-time basis, 121,000 in the U.S. and 102,000 internationally`
  - `MSFT-10-K-2026-c0012`: "vide content and online offerings to end users. HUMAN CAPITAL RESOURCES As of June 30, 2026, we employed approximately 223,000 people on a full-time basis, 121,000 in the U.S. and 102,000 internationally. Of the total employees, 89,000 were in operations, including product support and consulting ser"

## fg-087 - business - medium

- [ ] **Q:** What significant charges were included in Amazon's 2025 operating income?
- **Tickers:** AMZN
- **Gold answer:** Operating income for 2025 included $2.5 billion of charges recorded in Q3 2025 for the settlement of a lawsuit with the FTC, and $2.7 billion of estimated severance costs (of which $1.8 billion was recorded in Q3 2025), primarily related to planned role eliminations.
- **Label 1** (AMZN, verified, 1 matching chunk(s)): `charges of $2.5 billion we recorded in Q3 2025 related to the settlement of a lawsuit with the FTC`
  - `AMZN-10-K-2026-c0060`: "ing income was $68.6 billion and $80.0 billion for 2024 and 2025. Operating income for 2025 includes charges of $2.5 billion we recorded in Q3 2025 related to the settlement of a lawsuit with the FTC and $2.7 billion, of which $1.8 billion was recorded in Q3 2025, of estimated severance costs primar"
- **Label 2** (AMZN, verified, 3 matching chunk(s)): `of estimated severance costs primarily related to planned role eliminations`
  - `AMZN-10-K-2026-c0060`: "ed to the settlement of a lawsuit with the FTC and $2.7 billion, of which $1.8 billion was recorded in Q3 2025, of estimated severance costs primarily related to planned role eliminations. We believe that operating income is a more meaningful measure than gross profit and gross margin due to the div"
  - `AMZN-10-K-2026-c0082`: "pacted our International segment. For the year ended December 31, 2025, we recorded approximately $ 2.7 billion of estimated severance costs primarily related to planned role eliminations, of which $ 1.8 billion was recorded in Q3 2025 and $ 730 million"

## fg-088 - business - easy

- [ ] **Q:** How does seasonality affect Amazon's business?
- **Tickers:** AMZN
- **Gold answer:** Amazon's business is affected by seasonality, which has historically resulted in higher sales volume during its fourth quarter, which ends December 31.
- **Label 1** (AMZN, verified, 1 matching chunk(s)): `higher sales volume during our fourth quarter, which ends December 31`
  - `AMZN-10-K-2026-c0007`: "ur proprietary technology. Seasonality Our business is affected by seasonality, which historically has resulted in higher sales volume during our fourth quarter, which ends December 31. Human Capital Our employees are critical to our mission of being Earth’s most customer-centric company. As of Dece"

## fg-089 - geoeconomic - medium

- [ ] **Q:** What restrictions does Amazon describe on its operations in India?
- **Tickers:** AMZN
- **Gold answer:** India restricts the ownership or control of Indian companies by foreign entities involved in online multi-brand retail trading; Amazon notes such regulation of its businesses there (and in the PRC) involves unique risks and may change.
- **Label 1** (AMZN, verified, 1 matching chunk(s)): `In India, the government restricts the ownership or control of Indian companies by foreign entities`
  - `AMZN-10-K-2026-c0015`: "na through contractual relationships with third parties that hold PRC licenses to provide services. In India, the government restricts the ownership or control of Indian companies by foreign entities involved in online multi-brand retail trading activities. For www.amazon.in, we provide certain mark"

## fg-090 - business - medium

- [ ] **Q:** What acquisitions did Alphabet agree to in 2025, and at what prices?
- **Tickers:** GOOGL
- **Gold answer:** Alphabet entered definitive agreements to acquire Wiz, a cloud security platform, for $32.0 billion, and Intersect, a data center and energy infrastructure solutions provider, for $4.8 billion in cash plus assumption of debt; both were expected to close in 2026 subject to regulatory approvals.
- **Label 1** (GOOGL, verified, 2 matching chunk(s)): `acquire Wiz, a leading cloud security platform, for $32.0 billion`
  - `GOOGL-10-K-2026-c0069`: "expense. Other Information: 32. Table of Contents Alphabet Inc. • In 2025, we entered into definitive agreements to acquire Wiz, a leading cloud security platform, for $32.0 billion, and Intersect, a provider of data center and energy infrastructure solutions, for $4.8 billion in cash plus the assu"
  - `GOOGL-10-K-2026-c0146`: "25, respectively. Note 8. Acquisitions Pending Acquisitions In March 2025, we entered into a definitive agreement to acquire Wiz, a leading cloud security platform, for $ 32.0 billion, subject to closing adjustments, in an all-cash transaction. The acquisition of Wiz is expected to close in 2026, su"
- **Label 2** (GOOGL, verified, 1 matching chunk(s)): `Intersect, a provider of data center and energy infrastructure solutions, for $4.8 billion`
  - `GOOGL-10-K-2026-c0069`: "red into definitive agreements to acquire Wiz, a leading cloud security platform, for $32.0 billion, and Intersect, a provider of data center and energy infrastructure solutions, for $4.8 billion in cash plus the assumption of debt. Both acquisitions are expected to close in 2026, subject to customa"

## fg-091 - legal - hard

- [ ] **Q:** What did the European Commission decide in 2025 about Google's advertising technology business, and how did Alphabet respond?
- **Tickers:** GOOGL
- **Gold answer:** In September 2025 the EC found Google infringed EU competition law through 'self-preferencing' in its ad tech business, imposed a EUR 3.0 billion fine and ordered it to cease the practices; Google appealed in November 2025, recognized a $3.5 billion charge in Q3 2025, and placed bank guarantees in Q4 2025 instead of paying cash.
- **Notes:** Converted from a planned trap: the corpus search found this fine, so it is answerable.
- **Label 1** (GOOGL, verified, 1 matching chunk(s)): `The EC decision imposed a € 3.0 billion fine`
  - `GOOGL-10-K-2026-c0151`: "s through "self-preferencing" practices on the buy-side and the sell-side relating to Google's advertising technology business. The EC decision imposed a € 3.0 billion fine and directed Google to cease and desist the alleged "self-preferencing" practices. We appealed the ruling in November 2025. We"
- **Label 2** (GOOGL, verified, 1 matching chunk(s)): `3.5 billion in the third quarter of 2025, and we placed bank guarantees`
  - `GOOGL-10-K-2026-c0151`: "actices. We appealed the ruling in November 2025. We recognized a charge of 76. Table of Contents Alphabet Inc. $ 3.5 billion in the third quarter of 2025, and we placed bank guarantees in the fourth quarter of 2025 in lieu of cash payment. In September 2024, the UK also issued a Statement of Object"

## fg-092 - business - easy

- [ ] **Q:** How does Google Cloud generate its revenues?
- **Tickers:** GOOGL
- **Gold answer:** Google Cloud Platform primarily generates consumption-based fees and subscriptions for infrastructure, platform and other services (including AI offerings such as Vertex AI and Gemini Enterprise, and cybersecurity); Google Workspace and other enterprise services also contribute.
- **Label 1** (GOOGL, verified, 4 matching chunk(s)): `Google Cloud Platform primarily generates consumption-based fees and subscriptions`
  - `GOOGL-10-K-2026-c0065`: "rs, and the timing of product launches. Google Cloud Google Cloud revenues are comprised of the following: • Google Cloud Platform primarily generates consumption-based fees and subscriptions for infrastructure, platform, and other services. These services provide access to solutions such as AI offe"
  - `GOOGL-10-K-2026-c0066`: "rs, and the timing of product launches. Google Cloud Google Cloud revenues are comprised of the following: • Google Cloud Platform primarily generates consumption-based fees and subscriptions for infrastructure, platform, and other services. These services provide access to solutions such as AI offe"

## fg-093 - business - medium

- [ ] **Q:** What Waymo-related charge affected Alphabet's Other Bets results in 2025?
- **Tickers:** GOOGL
- **Gold answer:** Other Bets' 2025 operating loss of $7.5 billion included a $2.1 billion employee compensation charge for Waymo recognized in the fourth quarter, based on estimated stock valuation.
- **Label 1** (GOOGL, verified, 1 matching chunk(s)): `$2.1 billion employee compensation charge recognized in the fourth quarter for Waymo`
  - `GOOGL-10-K-2026-c0069`: "ty securities. • Other Bets operating loss of $7.5 billion for the year ended December 31, 2025 included a $2.1 billion employee compensation charge recognized in the fourth quarter for Waymo, primarily reflected in research and development expenses, based on estimated stock valuation. In February 2"

## fg-094 - geoeconomic - medium

- [ ] **Q:** What U.S. export licensing requirement did NVIDIA face for its H20 products, and what was the financial impact?
- **Tickers:** NVDA
- **Gold answer:** In April 2025 the U.S. government required a license to export H20 integrated circuits (and circuits achieving H20's memory/interconnect bandwidth) to China (including Hong Kong and Macau) and D:5 countries; NVIDIA incurred a $4.5 billion charge in Q1 fiscal 2026 for H20 excess inventory and purchase obligations.
- **Label 1** (NVDA, verified, 2 matching chunk(s)): `requires a license for export to China (including Hong Kong and Macau) and D:5 countries`
  - `NVDA-10-K-2026-c0020`: "te parent headquartered in, Country Group D5, including China. In April 2025, the USG informed us that it requires a license for export to China (including Hong Kong and Macau) and D:5 countries, or to companies headquartered or with an ultimate parent therein, of our H20 integrated circuits and any"
  - `NVDA-10-K-2026-c0061`: "te parent headquartered in, Country Group D5, including China. In April 2025, the USG informed us that it requires a license for export to China (including Hong Kong and Macau) and D:5 countries, or to companies headquartered or with an ultimate parent therein, of our H20 integrated circuits and any"
- **Label 2** (NVDA, verified, 3 matching chunk(s)): `incurred a $4.5 billion charge in the first quarter of fiscal year 2026 associated with H20`
  - `NVDA-10-K-2026-c0020`: "memory bandwidth, interconnect bandwidth, or combination thereof. As a result of these requirements, we incurred a $4.5 billion charge in the first quarter of fiscal year 2026 associated with H20 for excess inventory and purchase obligations, as the demand for H20 products diminished. In August 2025"
  - `NVDA-10-K-2026-c0061`: "memory bandwidth, interconnect bandwidth, or combination thereof. As a result of these requirements, we incurred a $4.5 billion charge in the first quarter of fiscal year 2026 associated with H20 for excess inventory and purchase obligations, as the demand for H20 products diminished. In August 2025"

## fg-095 - risk_factors - easy

- [ ] **Q:** How concentrated was NVIDIA's revenue among direct customers in fiscal year 2026?
- **Tickers:** NVDA
- **Gold answer:** Sales to one direct customer represented 22% of total revenue and sales to another represented 14%, primarily attributable to the Compute & Networking segment.
- **Label 1** (NVDA, verified, 4 matching chunk(s)): `sales to one direct customer represented 22% of total revenue and sales to another direct customer represented 14% of total revenue`
  - `NVDA-10-K-2026-c0051`: "m a limited number of customers, and this trend may continue. For fiscal year 2026, sales to one direct customer represented 22% of total revenue and sales to another direct customer represented 14% of total revenue, all of which were primarily attributable to the Compute & Networking segment. With"
  - `NVDA-10-K-2026-c0095`: "ect customers and this trend may continue. Direct Customers – For fiscal year 2026, sales to one direct customer represented 22% of total revenue and sales to another direct customer represented 14% of total revenue, all of which were primarily attributable to the Compute & Networking segment. For f"

## fg-096 - geoeconomic - medium

- [ ] **Q:** What does NVIDIA say about its H200 export license for China?
- **Tickers:** NVDA
- **Gold answer:** In February 2026 the U.S. government granted a license to ship small amounts of H200 products to specific China-based customers; NVIDIA had not generated revenue under it, H200s must be inspected in the U.S. before shipment and are subject to a 25% tariff upon importation into the U.S.
- **Label 1** (NVDA, verified, 4 matching chunk(s)): `we have not generated any revenue under the H200 licensing program`
  - `NVDA-10-K-2026-c0020`: "ted a license that would allow us to ship small amounts of H200 products to specific China-based customers. To date, we have not generated any revenue under the H200 licensing program, and do not yet know whether any imports will be allowed into China. The license requires that the H200s go through"
  - `NVDA-10-K-2026-c0061`: "ted a license that would allow us to ship small amounts of H200 products to specific China-based customers. To date, we have not generated any revenue under the H200 licensing program, and do not yet know whether any imports will be allowed into China. The license requires that the H200s go through"
- **Label 2** (NVDA, verified, 6 matching chunk(s)): `subject to a 25% tariff upon importation into the United States`
  - `NVDA-10-K-2026-c0020`: "d States prior to any shipment to the customer. As a result, any H200 shipped under the new licensing program will be subject to a 25% tariff upon importation into the United States. In the event that we are able to sell licensed products into the China market, we may not be able to pass along all o"
  - `NVDA-10-K-2026-c0021`: "d States prior to any shipment to the customer. As a result, any H200 shipped under the new licensing program will be subject to a 25% tariff upon importation into the United States. In the event that we are able to sell licensed products into the China market, we may not be able to pass along all o"

## fg-097 - geoeconomic - easy

- [ ] **Q:** Which Tesla business does the company say is more affected by the current tariff regime?
- **Tickers:** TSLA
- **Gold answer:** Tesla says the current tariff regime will have a relatively larger impact on its energy generation and storage business than on its automotive business.
- **Label 1** (TSLA, verified, 1 matching chunk(s)): `The current tariff regime will have a relatively larger impact on our energy generation and storage business`
  - `TSLA-10-K-2026-c0070`: "hich could have a meaningfully adverse impact on demand for our products and our profitability. The current tariff regime will have a relatively larger impact on our energy generation and storage business compared to our automotive business. While we prepare for near-term challenges to our business"

## fg-098 - business - easy

- [ ] **Q:** When did Tesla launch its Robotaxi service and what vehicles does it use?
- **Tickers:** TSLA
- **Gold answer:** Tesla launched its Robotaxi autonomous ride-hailing service in June 2025; it currently operates with Model Y vehicles and is expected in time to include Cybercab, Tesla's purpose-built autonomous vehicle.
- **Label 1** (TSLA, verified, 1 matching chunk(s)): `In June 2025, we launched our Robotaxi service`
  - `TSLA-10-K-2026-c0007`: "ludes the equivalent naming convention, “FSD (Capability)” that is used in the European, Middle East and Asia-Pacific regions. In June 2025, we launched our Robotaxi service, an autonomous ride-hailing platform that harnesses our technology and vehicles. We expect this service will open access to an"
- **Label 2** (TSLA, verified, 1 matching chunk(s)): `Our Robotaxi business currently operates with Model Y vehicles`
  - `TSLA-10-K-2026-c0007`: "ptions, unlock the potential to advance a service-driven business model based on AI, software and fleet-based profits. Our Robotaxi business currently operates with Model Y vehicles but, in time, will include Cybercab, our purpose-built autonomous vehicle. 2 Table of Contents Energy Generation and S"

## fg-099 - business - easy

- [ ] **Q:** How many consumer vehicles did Tesla produce and deliver in 2025, and how much energy storage did it deploy?
- **Tickers:** TSLA
- **Gold answer:** Tesla produced approximately 1.66 million and delivered approximately 1.64 million consumer vehicles in 2025, and deployed 46.7 GWh of energy storage products.
- **Label 1** (TSLA, verified, 1 matching chunk(s)): `produced approximately 1.66 million consumer vehicles and delivered approximately 1.64 million consumer vehicles`
  - `TSLA-10-K-2026-c0070`: "sed on long-term growth opportunities as we continue to make prudent investments. In 2025, we produced approximately 1.66 million consumer vehicles and delivered approximately 1.64 million consumer vehicles. We are focused on profitable growth via a differentiated and efficiently managed product por"
- **Label 2** (TSLA, verified, 2 matching chunk(s)): `we deployed 46.7 GWh of energy storage products`
  - `TSLA-10-K-2026-c0070`: "capitalizing on our AI investments and scalable mobility infrastructure to advance a service-driven business model. In 2025, we deployed 46.7 GWh of energy storage products. We are focused on ramping the production, increasing the market penetration of our energy storage products, developing our ba"
  - `TSLA-10-K-2026-c0071`: "scalable mobility infrastructure to advance a service-driven business model. In 2025, we deployed 46.7 GWh of energy storage products. We are focused on ramping the production, increasing the market penetration of our energy storage products, developing our battery technologies and vertically integr"

## fg-100 - business - medium

- [ ] **Q:** What is the Apple Card transaction described in JPMorgan Chase's 10-K?
- **Tickers:** JPM
- **Gold answer:** On January 7, 2026, JPMorganChase announced Chase will become the new issuer of Apple Card; it entered a forward purchase commitment on December 30, 2025 to acquire the Apple credit card portfolio, with closing expected in approximately 24 months.
- **Label 1** (JPM, verified, 2 matching chunk(s)): `Chase will become the new issuer of Apple Card`
  - `JPM-10-K-2026-c0119`: "enue lines, primarily Principal transactions revenue. Apple Card transaction: On January 7, 2026, JPMorganChase announced that Chase will become the new issuer of Apple Card. The Firm entered into a forward purchase commitment on December 30, 2025 to acquire the Apple credit card portfolio, with an"
  - `JPM-10-K-2026-c0449`: "vative receivables. (i) Represents lending-related financial instruments. (j) On January 7, 2026, JPMorganChase announced that Chase will become the new issuer of Apple Card. The Firm entered into a forward purchase commitment on December 30, 2025 to acquire the Apple credit card portfolio, with an"
- **Label 2** (JPM, verified, 2 matching chunk(s)): `with an expected closing in approximately 24 months`
  - `JPM-10-K-2026-c0119`: "Card. The Firm entered into a forward purchase commitment on December 30, 2025 to acquire the Apple credit card portfolio, with an expected closing in approximately 24 months (the “Apple Card transaction”). Refer to CCB segment results on pages 65–68, Capital Risk Management on pages 89–99 and Note"
  - `JPM-10-K-2026-c0449`: "Card. The Firm entered into a forward purchase commitment on December 30, 2025 to acquire the Apple credit card portfolio, with an expected closing in approximately 24 months (the “Apple Card transaction”). At December 31, 2025, includes estimated total credit exposure related to the Apple Card tra"

## fg-101 - business - medium

- [ ] **Q:** What full-year 2026 outlook did JPMorgan Chase provide?
- **Tickers:** JPM
- **Gold answer:** Management expected 2026 net interest income of approximately $103 billion (about $95 billion excluding Markets), adjusted expense of approximately $105 billion, and a Card Services net charge-off rate of approximately 3.4%.
- **Notes:** Forward-looking outlook stated in the filing (answerable); contrast with trap asking for projected net income.
- **Label 1** (JPM, verified, 1 matching chunk(s)): `expects net interest income to be approximately $103 billion`
  - `JPM-10-K-2026-c0124`: "in connection with announcing its results for the year and quarter ended December 31, 2025: Full-year 2026 • Management expects net interest income to be approximately $103 billion and net interest income excluding Markets to be approximately $95 billion, market dependent. • Management expects adjus"
- **Label 2** (JPM, verified, 1 matching chunk(s)): `expects adjusted expense to be approximately $105 billion`
  - `JPM-10-K-2026-c0124`: "y $103 billion and net interest income excluding Markets to be approximately $95 billion, market dependent. • Management expects adjusted expense to be approximately $105 billion, market dependent. • Management expects the net charge-off rate in Card Services to be approximately 3.4%. Net interest i"

## fg-102 - business - easy

- [ ] **Q:** How large and geographically spread is JPMorgan Chase's workforce?
- **Tickers:** JPM
- **Gold answer:** At December 31, 2025, JPMorganChase had 318,512 employees located in 66 countries, with 58% in the U.S.
- **Label 1** (JPM, verified, 2 matching chunk(s)): `had 318,512 employees globally`
  - `JPM-10-K-2026-c0023`: "full-time and part-time employees and does not include the Firm’s contractors. Global workforce As of December 31, 2025, JPMorganChase had 318,512 employees globally. JPMorganChase’s employees are located in 66 countries, with 58% of the Firm’s employees located in the U.S"
  - `JPM-10-K-2026-c0024`: "full-time and part-time employees and does not include the Firm’s contractors. Global workforce As of December 31, 2025, JPMorganChase had 318,512 employees globally. JPMorganChase’s employees are located in 66 countries, with 58% of the Firm’s employees located in the U.S. The following table prese"
- **Label 2** (JPM, verified, 2 matching chunk(s)): `located in 66 countries, with 58% of the Firm's employees located in the U.S`
  - `JPM-10-K-2026-c0023`: "workforce As of December 31, 2025, JPMorganChase had 318,512 employees globally. JPMorganChase’s employees are located in 66 countries, with 58% of the Firm’s employees located in the U.S"
  - `JPM-10-K-2026-c0024`: "workforce As of December 31, 2025, JPMorganChase had 318,512 employees globally. JPMorganChase’s employees are located in 66 countries, with 58% of the Firm’s employees located in the U.S. The following table presents the distribution of the Firm’s global workforce by region and by line of business"

## fg-103 - business - easy

- [ ] **Q:** What share of Coca-Cola's worldwide unit case volume came from its five largest independent bottling partners in 2025?
- **Tickers:** KO
- **Gold answer:** Its five largest independent bottling partners combined represented 44% of total worldwide unit case volume in 2025.
- **Label 1** (KO, verified, 1 matching chunk(s)): `these five bottling partners combined represented 44% of our total worldwide unit case volume`
  - `KO-10-K-2026-c0010`: "Cambodia, Laos, Thailand, Vietnam and territories in 13 states in the western United States. In 2025, these five bottling partners combined represented 44% of our total worldwide unit case volume. Being a bottler does not create a legal partnership or joint venture between us and our bottlers. Our"

## fg-104 - risk_factors - medium

- [ ] **Q:** What risks does Coca-Cola describe related to refranchising its bottling operations?
- **Tickers:** KO
- **Gold answer:** Coca-Cola continues to seek to refranchise consolidated bottling operations; these activities require significant senior-management attention and may be a distraction, and failure to complete them on favorable terms or misaligned refranchising partners could adversely affect results.
- **Label 1** (KO, verified, 1 matching chunk(s)): `continue to seek opportunities to refranchise our consolidated bottling operations`
  - `KO-10-K-2026-c0046`: "initiative to focus on our core business of building brands and leading our system of bottling partners, we continue to seek opportunities to refranchise our consolidated bottling operations. Our refranchising activities require significant attention and effort on the part of, and therefore may be"
- **Label 2** (KO, verified, 1 matching chunk(s)): `may be a distraction for, senior management`
  - `KO-10-K-2026-c0046`: "idated bottling operations. Our refranchising activities require significant attention and effort on the part of, and therefore may be a distraction for, senior management. If we are unable to complete future refranchising transactions on terms and conditions favorable to us, or if our refranchising"

## fg-121 - unanswerable - medium

- [ ] **Q:** How many iPhone units did Apple sell in fiscal year 2025?
- **Tickers:** AAPL
- **Gold answer:** (unanswerable - model should refuse)
- **Search notes:** TRAP (metric not reported). Apple reports iPhone net sales in dollars ($209,586M) but no unit volumes; the only 'units' hits are restricted stock units. Searched AAPL chunks: BM25 top-5 for the question = AAPL-10-K-2025-c0049, AAPL-10-K-2025-c0004, AAPL-10-K-2025-c0051, AAPL-10-K-2025-c0074, AAPL-10-K-2025-c0070; none of the regex searches below found a passage stating the requested fact. Regex (case-insensitive unless noted) over all AAPL chunks: /units? sold/ 0 hits in 0 chunks; /unit sales/ 0 hits in 0 chunks; /million (iPhone|units)/ 0 hits in 0 chunks; /\bunits\b/ 2 hits in 2 chunks.

## fg-122 - unanswerable - medium

- [ ] **Q:** What were Apple's total net sales in the fourth quarter of fiscal 2025?
- **Tickers:** AAPL
- **Gold answer:** (unanswerable - model should refuse)
- **Search notes:** TRAP (period not broken out). The 10-K gives annual totals only; 'fourth quarter' hits are about legal settlements, the share repurchase program, product launches and an accounting standard, and the only 'three months ended' hit is the Q4 share repurchase table. Searched AAPL chunks: BM25 top-5 for the question = AAPL-10-K-2025-c0049, AAPL-10-K-2025-c0070, AAPL-10-K-2025-c0009, AAPL-10-K-2025-c0105, AAPL-10-K-2025-c0098; none of the regex searches below found a passage stating the requested fact. Regex (case-insensitive unless noted) over all AAPL chunks: /fourth quarter/ 8 hits in 7 chunks; /quarterly (financial|results|data)/ 0 hits in 0 chunks; /three months ended/ 1 hits in 1 chunks.

## fg-123 - unanswerable - medium

- [ ] **Q:** What were Apple's net sales in India in fiscal year 2025?
- **Tickers:** AAPL
- **Gold answer:** (unanswerable - model should refuse)
- **Search notes:** TRAP (region not broken out). India is included in the Europe reportable segment ('Europe includes European countries, as well as India, the Middle East and Africa'); country-level net sales are given only for the U.S. and China. Other India hits concern manufacturing and tariffs. Searched AAPL chunks: BM25 top-5 for the question = AAPL-10-K-2025-c0049, AAPL-10-K-2025-c0095, AAPL-10-K-2025-c0070, AAPL-10-K-2025-c0009, AAPL-10-K-2025-c0005; none of the regex searches below found a passage stating the requested fact. Regex (case-insensitive unless noted) over all AAPL chunks: /\bIndia\b/ 8 hits in 7 chunks.

## fg-124 - unanswerable - hard

- [ ] **Q:** According to Apple's 10-K, which bank will become the new issuer of Apple Card?
- **Tickers:** AAPL
- **Gold answer:** (unanswerable - model should refuse)
- **Search notes:** TRAP (fact only in another company's filing). Apple's 10-K (filed Oct 2025) only describes Apple Card as a co-branded credit card and names no issuer; the Jan 2026 announcement appears only in JPM's 10-K. A correct answer must refuse when restricted to Apple's filing. Searched AAPL chunks: BM25 top-5 for the question = AAPL-10-K-2025-c0005, AAPL-10-K-2025-c0049, AAPL-10-K-2025-c0119, AAPL-10-K-2025-c0103, AAPL-10-K-2025-c0004; none of the regex searches below found a passage stating the requested fact. Regex (case-insensitive unless noted) over all AAPL chunks: /Apple Card/ 1 hits in 1 chunks; /\bJPMorgan\b|\bChase\b/ 0 hits in 0 chunks; /new issuer/ 0 hits in 0 chunks; /Goldman/ 0 hits in 0 chunks.

## fg-125 - unanswerable - medium

- [ ] **Q:** What were Azure revenues, in dollars, for Microsoft's fiscal year 2026?
- **Tickers:** MSFT
- **Gold answer:** (unanswerable - model should refuse)
- **Search notes:** TRAP (metric not reported). Microsoft discloses only Azure growth (41%); dollar revenue is reported for broader lines (Server products and cloud services $129,425M; Microsoft Cloud $214.4B), not Azure alone. Searched MSFT chunks: BM25 top-5 for the question = MSFT-10-K-2026-c0070, MSFT-10-K-2026-c0065, MSFT-10-K-2026-c0072, MSFT-10-K-2026-c0155, MSFT-10-K-2026-c0156; none of the regex searches below found a passage stating the requested fact. Regex (case-insensitive unless noted) over all MSFT chunks: /Azure[^.]{0,80}\$ ?[0-9]/ 0 hits in 0 chunks; /Azure and other cloud services revenue (was|of|totaled)/ 0 hits in 0 chunks.

## fg-126 - unanswerable - medium

- [ ] **Q:** How many paid Microsoft 365 Copilot seats did Microsoft have at the end of fiscal 2026?
- **Tickers:** MSFT
- **Gold answer:** (unanswerable - model should refuse)
- **Search notes:** TRAP (metric not reported). Only Microsoft 365 Commercial seat growth (6%) and a seat definition are disclosed; no Copilot seat count. Searched MSFT chunks: BM25 top-5 for the question = MSFT-10-K-2026-c0069, MSFT-10-K-2026-c0072, MSFT-10-K-2026-c0003, MSFT-10-K-2026-c0152, MSFT-10-K-2026-c0004; none of the regex searches below found a passage stating the requested fact. Regex (case-insensitive unless noted) over all MSFT chunks: /seats/ 3 hits in 2 chunks; /Copilot[^.]{0,60}(users|subscribers|seats)/ 0 hits in 0 chunks.

## fg-127 - unanswerable - medium

- [ ] **Q:** How much does Microsoft plan to spend on capital expenditures in fiscal year 2027?
- **Tickers:** MSFT
- **Gold answer:** (unanswerable - model should refuse)
- **Search notes:** TRAP (future-period figure). No capex plan for FY2027 is given; 'fiscal year 2027' hits are NOL expiry dates and lease commencement dates. Searched MSFT chunks: BM25 top-5 for the question = MSFT-10-K-2026-c0068, MSFT-10-K-2026-c0082, MSFT-10-K-2026-c0144, MSFT-10-K-2026-c0003, MSFT-10-K-2026-c0065; none of the regex searches below found a passage stating the requested fact. Regex (case-insensitive unless noted) over all MSFT chunks: /fiscal year 2027/ 2 hits in 2 chunks; /fiscal 2027/ 0 hits in 0 chunks; /expect(s)? capital expenditures/ 0 hits in 0 chunks.

## fg-128 - unanswerable - hard

- [ ] **Q:** Why did Microsoft acquire Nintendo in fiscal year 2026?
- **Tickers:** MSFT
- **Gold answer:** (unanswerable - model should refuse)
- **Search notes:** TRAP (fabricated event). No acquisition of Nintendo (or any mention of Nintendo) appears in the filing; the premise is false. Searched MSFT chunks: BM25 top-5 for the question = MSFT-10-K-2026-c0070, MSFT-10-K-2026-c0072, MSFT-10-K-2026-c0068, MSFT-10-K-2026-c0155, MSFT-10-K-2026-c0065; none of the regex searches below found a passage stating the requested fact. Regex (case-insensitive unless noted) over all MSFT chunks: /Nintendo/ 0 hits in 0 chunks.

## fg-129 - unanswerable - medium

- [ ] **Q:** How many Amazon Prime members were there at the end of 2025?
- **Tickers:** AMZN
- **Gold answer:** (unanswerable - model should refuse)
- **Search notes:** TRAP (metric not reported). Prime is described (benefits, membership fees in subscription sales) but no member count is disclosed. Searched AMZN chunks: BM25 top-5 for the question = AMZN-10-K-2026-c0124, AMZN-10-K-2026-c0085, AMZN-10-K-2026-c0122, AMZN-10-K-2026-c0098, AMZN-10-K-2026-c0059; none of the regex searches below found a passage stating the requested fact. Regex (case-insensitive unless noted) over all AMZN chunks: /Prime members/ 9 hits in 7 chunks; /members/ 10 hits in 8 chunks.

## fg-130 - unanswerable - medium

- [ ] **Q:** What were Amazon's net sales in India in 2025?
- **Tickers:** AMZN
- **Gold answer:** (unanswerable - model should refuse)
- **Search notes:** TRAP (region not broken out). Net sales by country are given only for the United States, Germany, United Kingdom, Japan and Rest of world; India hits are about foreign-ownership regulation and taxes. Searched AMZN chunks: BM25 top-5 for the question = AMZN-10-K-2026-c0124, AMZN-10-K-2026-c0123, AMZN-10-K-2026-c0015, AMZN-10-K-2026-c0135, AMZN-10-K-2026-c0122; none of the regex searches below found a passage stating the requested fact. Regex (case-insensitive unless noted) over all AMZN chunks: /\bIndia\b/ 5 hits in 3 chunks; /Germany \|/ 1 hits in 1 chunks.

## fg-131 - unanswerable - medium

- [ ] **Q:** What were Amazon's net sales in the third quarter of 2025?
- **Tickers:** AMZN
- **Gold answer:** (unanswerable - model should refuse)
- **Search notes:** TRAP (period not broken out). No quarterly income statement; 'Q3 2025' hits concern the FTC settlement charge and severance timing, not quarterly sales. Searched AMZN chunks: BM25 top-5 for the question = AMZN-10-K-2026-c0124, AMZN-10-K-2026-c0122, AMZN-10-K-2026-c0065, AMZN-10-K-2026-c0123, AMZN-10-K-2026-c0143; none of the regex searches below found a passage stating the requested fact. Regex (case-insensitive unless noted) over all AMZN chunks: /Q3 2025[^.]{0,60}(net sales|sales)/ 0 hits in 0 chunks; /Quarterly Results/ 0 hits in 0 chunks; /three months ended September 30/ 0 hits in 0 chunks.

## fg-132 - unanswerable - medium

- [ ] **Q:** How much AWS revenue came from generative AI services in 2025?
- **Tickers:** AMZN
- **Gold answer:** (unanswerable - model should refuse)
- **Search notes:** TRAP (metric not reported). AWS is reported only as a segment total ($128,725M); no AI-specific revenue figure is disclosed. Searched AMZN chunks: BM25 top-5 for the question = AMZN-10-K-2026-c0054, AMZN-10-K-2026-c0085, AMZN-10-K-2026-c0103, AMZN-10-K-2026-c0057, AMZN-10-K-2026-c0137; none of the regex searches below found a passage stating the requested fact. Regex (case-insensitive unless noted) over all AMZN chunks: /generative AI[^.]{0,80}revenue/ 0 hits in 0 chunks; /AI[^.]{0,40}revenue (of|was)/ 0 hits in 0 chunks.

## fg-133 - unanswerable - medium

- [ ] **Q:** How many paid subscribers does the Gemini app have?
- **Tickers:** GOOGL
- **Gold answer:** (unanswerable - model should refuse)
- **Search notes:** TRAP (metric not reported). The filing discusses Gemini models and growth in paid subscriptions across YouTube and Google One, but gives no Gemini app subscriber count. Searched GOOGL chunks: BM25 top-5 for the question = GOOGL-10-K-2026-c0065, GOOGL-10-K-2026-c0106, GOOGL-10-K-2026-c0066, GOOGL-10-K-2026-c0004, GOOGL-10-K-2026-c0005; none of the regex searches below found a passage stating the requested fact. Regex (case-insensitive unless noted) over all GOOGL chunks: /Gemini[^.]{0,80}(subscribers|users)/ 0 hits in 0 chunks; /paid subscriptions/ 2 hits in 2 chunks.

## fg-134 - unanswerable - medium

- [ ] **Q:** How much revenue did Waymo generate in 2025?
- **Tickers:** GOOGL
- **Gold answer:** (unanswerable - model should refuse)
- **Search notes:** TRAP (entity not broken out). Waymo is part of Other Bets, reported only in aggregate ($1,537M revenue in 2025); Waymo hits are about a compensation charge and a funding round. Searched GOOGL chunks: BM25 top-5 for the question = GOOGL-10-K-2026-c0069, GOOGL-10-K-2026-c0063, GOOGL-10-K-2026-c0073, GOOGL-10-K-2026-c0076, GOOGL-10-K-2026-c0075; none of the regex searches below found a passage stating the requested fact. Regex (case-insensitive unless noted) over all GOOGL chunks: /Waymo[^.]{0,80}revenue/ 0 hits in 0 chunks; /Other Bets revenues/ 1 hits in 1 chunks.

## fg-135 - unanswerable - medium

- [ ] **Q:** What were Google Cloud revenues in the fourth quarter of 2025?
- **Tickers:** GOOGL
- **Gold answer:** (unanswerable - model should refuse)
- **Search notes:** TRAP (period not broken out). Only annual segment revenues are given; 'fourth quarter' hits concern the Waymo charge and EC fine bank guarantees. Searched GOOGL chunks: BM25 top-5 for the question = GOOGL-10-K-2026-c0069, GOOGL-10-K-2026-c0074, GOOGL-10-K-2026-c0071, GOOGL-10-K-2026-c0072, GOOGL-10-K-2026-c0070; none of the regex searches below found a passage stating the requested fact. Regex (case-insensitive unless noted) over all GOOGL chunks: /fourth quarter/ 2 hits in 2 chunks; /three months ended December 31/ 0 hits in 0 chunks.

## fg-136 - unanswerable - medium

- [ ] **Q:** How many YouTube Premium subscribers did Alphabet have at the end of 2025?
- **Tickers:** GOOGL
- **Gold answer:** (unanswerable - model should refuse)
- **Search notes:** TRAP (metric not reported). No subscriber counts are disclosed; 'subscribers' appears only as a generic revenue factor. Searched GOOGL chunks: BM25 top-5 for the question = GOOGL-10-K-2026-c0007, GOOGL-10-K-2026-c0065, GOOGL-10-K-2026-c0105, GOOGL-10-K-2026-c0172, GOOGL-10-K-2026-c0006; none of the regex searches below found a passage stating the requested fact. Regex (case-insensitive unless noted) over all GOOGL chunks: /YouTube Premium/ 0 hits in 0 chunks; /subscribers/ 2 hits in 2 chunks.

## fg-137 - unanswerable - medium

- [ ] **Q:** How many Blackwell GPUs did NVIDIA ship in fiscal year 2026?
- **Tickers:** NVDA
- **Gold answer:** (unanswerable - model should refuse)
- **Search notes:** TRAP (metric not reported). NVIDIA reports revenue, not unit shipments; Blackwell is discussed qualitatively. Searched NVDA chunks: BM25 top-5 for the question = NVDA-10-K-2026-c0011, NVDA-10-K-2026-c0010, NVDA-10-K-2026-c0007, NVDA-10-K-2026-c0006, NVDA-10-K-2026-c0086; none of the regex searches below found a passage stating the requested fact. Regex (case-insensitive unless noted) over all NVDA chunks: /shipped [0-9]/ 0 hits in 0 chunks; /Blackwell[^.]{0,60}(million|units)/ 0 hits in 0 chunks.

## fg-138 - unanswerable - hard

- [ ] **Q:** Which company was NVIDIA's largest direct customer, accounting for 22% of fiscal 2026 revenue?
- **Tickers:** NVDA
- **Gold answer:** (unanswerable - model should refuse)
- **Search notes:** TRAP (identity not disclosed). The filing states one direct customer was 22% of revenue (and another 14%) but does not name them; companies named elsewhere appear as competitors (e.g. Microsoft, Amazon) or contract manufacturers (e.g. Hon Hai), never as the 22% customer. Case-sensitive 'Customer A/B' labels: 0 hits. Searched NVDA chunks: BM25 top-5 for the question = NVDA-10-K-2026-c0169, NVDA-10-K-2026-c0095, NVDA-10-K-2026-c0170, NVDA-10-K-2026-c0096, NVDA-10-K-2026-c0150; none of the regex searches below found a passage stating the requested fact. Regex (case-insensitive unless noted) over all NVDA chunks: /22% of total revenue/ 3 hits in 3 chunks; /Customer [A-Z]\b/ 0 hits in 0 chunks.

## fg-139 - unanswerable - medium

- [ ] **Q:** What revenue does NVIDIA forecast for fiscal year 2027?
- **Tickers:** NVDA
- **Gold answer:** (unanswerable - model should refuse)
- **Search notes:** TRAP (future-period figure). 'fiscal year 2027' hits cover Rubin shipment timing, Gaming supply constraints and tax payment timing; no revenue forecast is given. Searched NVDA chunks: BM25 top-5 for the question = NVDA-10-K-2026-c0010, NVDA-10-K-2026-c0089, NVDA-10-K-2026-c0171, NVDA-10-K-2026-c0126, NVDA-10-K-2026-c0154; none of the regex searches below found a passage stating the requested fact. Regex (case-insensitive unless noted) over all NVDA chunks: /fiscal (year )?2027/ 15 hits in 11 chunks; /expect[^.]{0,40}revenue/ 1 hits in 1 chunks; /outlook|guidance/ 3 hits in 3 chunks.

## fg-140 - unanswerable - medium

- [ ] **Q:** How much revenue did NVIDIA earn from customers headquartered in India in fiscal 2026?
- **Tickers:** NVDA
- **Gold answer:** (unanswerable - model should refuse)
- **Search notes:** TRAP (region not broken out). Geographic revenue is given only for United States, Taiwan, China (including Hong Kong) and Other; India hits concern facilities and tax examinations. Searched NVDA chunks: BM25 top-5 for the question = NVDA-10-K-2026-c0169, NVDA-10-K-2026-c0061, NVDA-10-K-2026-c0020, NVDA-10-K-2026-c0126, NVDA-10-K-2026-c0096; none of the regex searches below found a passage stating the requested fact. Regex (case-insensitive unless noted) over all NVDA chunks: /\bIndia\b/ 3 hits in 2 chunks.

## fg-141 - unanswerable - medium

- [ ] **Q:** How many Cybertrucks did Tesla deliver in 2025?
- **Tickers:** TSLA
- **Gold answer:** (unanswerable - model should refuse)
- **Search notes:** TRAP (metric not reported). Only total consumer vehicle deliveries (~1.64 million) are given; Cybertruck hits describe the product. Searched TSLA chunks: BM25 top-5 for the question = TSLA-10-K-2026-c0199, TSLA-10-K-2026-c0188, TSLA-10-K-2026-c0184, TSLA-10-K-2026-c0024, TSLA-10-K-2026-c0027; none of the regex searches below found a passage stating the requested fact. Regex (case-insensitive unless noted) over all TSLA chunks: /Cybertruck[^.]{0,80}(deliver|units|[0-9],[0-9]{3})/ 0 hits in 0 chunks; /Cybertruck/ 5 hits in 4 chunks.

## fg-142 - unanswerable - medium

- [ ] **Q:** How much revenue did Tesla's Robotaxi service generate in 2025?
- **Tickers:** TSLA
- **Gold answer:** (unanswerable - model should refuse)
- **Search notes:** TRAP (metric not reported). Robotaxi launch (June 2025) and strategy are described but no Robotaxi revenue figure is disclosed. Searched TSLA chunks: BM25 top-5 for the question = TSLA-10-K-2026-c0189, TSLA-10-K-2026-c0188, TSLA-10-K-2026-c0199, TSLA-10-K-2026-c0007, TSLA-10-K-2026-c0184; none of the regex searches below found a passage stating the requested fact. Regex (case-insensitive unless noted) over all TSLA chunks: /Robotaxi[^.]{0,80}revenue/ 0 hits in 0 chunks; /Robotaxi/ 24 hits in 18 chunks.

## fg-143 - unanswerable - hard

- [ ] **Q:** How many Optimus robots did Tesla sell in 2025?
- **Tickers:** TSLA
- **Gold answer:** (unanswerable - model should refuse)
- **Search notes:** TRAP (fabricated premise). The filing describes Optimus as a humanoid robot in development in a nascent industry; no sales are reported, so the premise is false. Searched TSLA chunks: BM25 top-5 for the question = TSLA-10-K-2026-c0008, TSLA-10-K-2026-c0116, TSLA-10-K-2026-c0034, TSLA-10-K-2026-c0070, TSLA-10-K-2026-c0199; none of the regex searches below found a passage stating the requested fact. Regex (case-insensitive unless noted) over all TSLA chunks: /Optimus/ 7 hits in 6 chunks.

## fg-144 - unanswerable - medium

- [ ] **Q:** What were Tesla's revenues from customers in Germany in 2025?
- **Tickers:** TSLA
- **Gold answer:** (unanswerable - model should refuse)
- **Search notes:** TRAP (region not broken out). Revenue by geography is given only for United States, China and Other international; Germany appears separately only in the long-lived assets table and in facility/regulation text. Searched TSLA chunks: BM25 top-5 for the question = TSLA-10-K-2026-c0185, TSLA-10-K-2026-c0121, TSLA-10-K-2026-c0189, TSLA-10-K-2026-c0012, TSLA-10-K-2026-c0184; none of the regex searches below found a passage stating the requested fact. Regex (case-insensitive unless noted) over all TSLA chunks: /Germany/ 4 hits in 4 chunks; /China \| 20,962/ 1 hits in 1 chunks.

## fg-145 - unanswerable - medium

- [ ] **Q:** How much revenue did the Apple Card portfolio contribute to JPMorgan Chase in 2025?
- **Tickers:** JPM
- **Gold answer:** (unanswerable - model should refuse)
- **Search notes:** TRAP (event not yet occurred). The Apple Card transaction is a forward purchase commitment with closing expected in ~24 months; the filing discloses provisions and capital impacts but no Apple Card revenue in 2025. Searched JPM chunks: BM25 top-5 for the question = JPM-10-K-2026-c0577, JPM-10-K-2026-c0119, JPM-10-K-2026-c0449, JPM-10-K-2026-c0295, JPM-10-K-2026-c0253; none of the regex searches below found a passage stating the requested fact. Regex (case-insensitive unless noted) over all JPM chunks: /Apple Card/ 39 hits in 28 chunks; /Apple credit card/ 3 hits in 3 chunks.

## fg-146 - unanswerable - medium

- [ ] **Q:** How much bitcoin does JPMorgan Chase hold on its balance sheet?
- **Tickers:** JPM
- **Gold answer:** (unanswerable - model should refuse)
- **Search notes:** TRAP (metric not reported). No bitcoin holdings are disclosed; 'crypto' hits are cryptography and a list of fintech competition areas. Searched JPM chunks: BM25 top-5 for the question = JPM-10-K-2026-c0052, JPM-10-K-2026-c0571, JPM-10-K-2026-c0235, JPM-10-K-2026-c0211, JPM-10-K-2026-c0659; none of the regex searches below found a passage stating the requested fact. Regex (case-insensitive unless noted) over all JPM chunks: /bitcoin/ 0 hits in 0 chunks; /crypto/ 3 hits in 3 chunks.

## fg-147 - unanswerable - medium

- [ ] **Q:** What net income does JPMorgan Chase project for 2026?
- **Tickers:** JPM
- **Gold answer:** (unanswerable - model should refuse)
- **Search notes:** TRAP (future-period figure not given). The 2026 outlook covers net interest income (~$103B), adjusted expense (~$105B) and the Card net charge-off rate (~3.4%) only; no net income projection. Searched JPM chunks: BM25 top-5 for the question = JPM-10-K-2026-c0124, JPM-10-K-2026-c0596, JPM-10-K-2026-c0349, JPM-10-K-2026-c0597, JPM-10-K-2026-c0598; none of the regex searches below found a passage stating the requested fact. Regex (case-insensitive unless noted) over all JPM chunks: /expects? (net income|NII|net interest income)/ 1 hits in 1 chunks; /outlook/ 34 hits in 19 chunks.

## fg-148 - unanswerable - medium

- [ ] **Q:** What were net operating revenues from Coca-Cola Zero Sugar in 2025?
- **Tickers:** KO
- **Gold answer:** (unanswerable - model should refuse)
- **Search notes:** TRAP (product not broken out). Revenue is reported by segment and concentrate vs finished product operations, not by brand; Zero Sugar hits are brand lists and definitions. Searched KO chunks: BM25 top-5 for the question = KO-10-K-2026-c0005, KO-10-K-2026-c0092, KO-10-K-2026-c0158, KO-10-K-2026-c0004, KO-10-K-2026-c0002; none of the regex searches below found a passage stating the requested fact. Regex (case-insensitive unless noted) over all KO chunks: /Zero Sugar[^.]{0,80}(revenue|\$)/ 0 hits in 0 chunks; /Zero Sugar/ 8 hits in 6 chunks.

## fg-149 - unanswerable - medium

- [ ] **Q:** What is Coca-Cola's market share in India?
- **Tickers:** KO
- **Gold answer:** (unanswerable - model should refuse)
- **Search notes:** TRAP (metric not reported). 'market share' hits are generic risk language; India hits concern unit case volume rankings, refranchising and regulation, with no share figure. Searched KO chunks: BM25 top-5 for the question = KO-10-K-2026-c0245, KO-10-K-2026-c0008, KO-10-K-2026-c0009, KO-10-K-2026-c0158, KO-10-K-2026-c0002; none of the regex searches below found a passage stating the requested fact. Regex (case-insensitive unless noted) over all KO chunks: /market share/ 3 hits in 3 chunks; /\bIndia\b/ 29 hits in 25 chunks.

## fg-150 - unanswerable - medium

- [ ] **Q:** How many vending machines does Coca-Cola operate worldwide?
- **Tickers:** KO
- **Gold answer:** (unanswerable - model should refuse)
- **Search notes:** TRAP (metric not reported). The only vending hit mentions new vending and dispensing equipment generically; no count is disclosed. Searched KO chunks: BM25 top-5 for the question = KO-10-K-2026-c0008, KO-10-K-2026-c0158, KO-10-K-2026-c0016, KO-10-K-2026-c0002, KO-10-K-2026-c0009; none of the regex searches below found a passage stating the requested fact. Regex (case-insensitive unless noted) over all KO chunks: /vending/ 1 hits in 1 chunks; /machines/ 3 hits in 2 chunks.
