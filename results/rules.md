## Extractor: `rules`

**Field accuracy: 66.7%** over 360 fields (0 wrong values, rest left blank) in 1.7s

Model calls: 0 (0.0 per doc, 0 tokens in / 0 out) · extraction latency p50 1.4 ms, p95 3.8 ms

| Field | Accuracy |
|---|---|
| borrower | 66.7% |
| property_address | 66.7% |
| loan_amount | 66.7% |
| interest_rate | 66.7% |
| maturity_date | 66.7% |
| ltv | 66.7% |
| noi | 66.7% |
| units | 66.7% |

| Layout | Accuracy |
|---|---|
| layout_key_value | 100.0% |
| layout_lender | 100.0% |
| layout_narrative | 0.0% |

<details><summary>First failures</summary>

| Doc | Field | Expected | Got |
|---|---|---|---|
| doc_002.pdf | borrower | Lakeshore Investors LLC | None |
| doc_002.pdf | property_address | 2029 Park Boulevard, Tampa, FL 33649 | None |
| doc_002.pdf | loan_amount | 59350000 | None |
| doc_002.pdf | interest_rate | 5.65 | None |
| doc_002.pdf | maturity_date | 2029-10-01 | None |
| doc_002.pdf | ltv | 68.0 | None |
| doc_002.pdf | noi | 5383000 | None |
| doc_002.pdf | units | 116 | None |
| doc_005.pdf | borrower | Lakeshore Residential LLC | None |
| doc_005.pdf | property_address | 7009 Main Street, Nashville, TN 37295 | None |
| doc_005.pdf | loan_amount | 9900000 | None |
| doc_005.pdf | interest_rate | 8.05 | None |
| doc_005.pdf | maturity_date | 2033-06-01 | None |
| doc_005.pdf | ltv | 72.0 | None |
| doc_005.pdf | noi | 3018000 | None |
| doc_005.pdf | units | 324 | None |
| doc_008.pdf | borrower | Oak Hollow Residential LLC | None |
| doc_008.pdf | property_address | 1420 Oak Avenue, Tampa, FL 33667 | None |
| doc_008.pdf | loan_amount | 43100000 | None |
| doc_008.pdf | interest_rate | 8.0 | None |

</details>
