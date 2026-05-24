# Golden Intake Report

This report validates eval fixture intake before candidate rows are promoted to strict goldens.

## Summary

- examples scanned: 47
- packs scanned: 4
- structural errors: 0
- review warnings: 127

| Pack | Examples |
| --- | ---: |
| `market_fit_v1` | 10 |
| `market_fit_v2` | 7 |
| `market_fit_v2_candidates` | 16 |
| `market_fit_v3_candidates` | 14 |

## Findings

| Severity | Code | Pack | Example | Detail |
| --- | --- | --- | --- | --- |
| warning | `duplicate_source_url` | `market_fit_v1` | `eval_007` | Duplicate key https://x.com/AimInvestments/status/2048802995182473431: market_fit_v1/eval_007, market_fit_v1/eval_009 |
| warning | `duplicate_x_status` | `market_fit_v1` | `eval_007` | Duplicate key x_status:2048802995182473431: market_fit_v1/eval_007, market_fit_v1/eval_009 |
| warning | `duplicate_source_url` | `market_fit_v1` | `eval_009` | Duplicate key https://x.com/AimInvestments/status/2048802995182473431: market_fit_v1/eval_007, market_fit_v1/eval_009 |
| warning | `duplicate_x_status` | `market_fit_v1` | `eval_009` | Duplicate key x_status:2048802995182473431: market_fit_v1/eval_007, market_fit_v1/eval_009 |
| warning | `duplicate_example_id` | `market_fit_v2` | `eval_v2_010` | Duplicate key eval_v2_010: market_fit_v2/eval_v2_010, market_fit_v2_candidates/eval_v2_010 |
| warning | `duplicate_source_text` | `market_fit_v2` | `eval_v2_010` | Duplicate key 819a74d2be70eac3142a163c4eff52fb1790629d72182f996ab02bbb8931ee82: market_fit_v2/eval_v2_010, market_fit_v2_candidates/eval_v2_010 |
| warning | `duplicate_source_url` | `market_fit_v2` | `eval_v2_010` | Duplicate key https://x.com/coinbureau/status/2058155996019614079: market_fit_v2/eval_v2_010, market_fit_v2_candidates/eval_v2_010 |
| warning | `duplicate_x_status` | `market_fit_v2` | `eval_v2_010` | Duplicate key x_status:2058155996019614079: market_fit_v2/eval_v2_010, market_fit_v2_candidates/eval_v2_010 |
| warning | `grok_candidate_requires_review` | `market_fit_v2` | `eval_v2_010` | Treat as candidate-only until source text and market rules are independently checked. |
| warning | `duplicate_example_id` | `market_fit_v2` | `eval_v2_012` | Duplicate key eval_v2_012: market_fit_v2/eval_v2_012, market_fit_v2_candidates/eval_v2_012 |
| warning | `duplicate_source_text` | `market_fit_v2` | `eval_v2_012` | Duplicate key f4c59542d183d45d3fdc476c7bdcca4974127b2887d37cefa827095d79a490bb: market_fit_v2/eval_v2_012, market_fit_v2_candidates/eval_v2_012 |
| warning | `duplicate_source_url` | `market_fit_v2` | `eval_v2_012` | Duplicate key https://x.com/VladTheInflator/status/2058251938043761032: market_fit_v2/eval_v2_012, market_fit_v2_candidates/eval_v2_012 |
| warning | `duplicate_x_status` | `market_fit_v2` | `eval_v2_012` | Duplicate key x_status:2058251938043761032: market_fit_v2/eval_v2_012, market_fit_v2_candidates/eval_v2_012 |
| warning | `grok_candidate_requires_review` | `market_fit_v2` | `eval_v2_012` | Treat as candidate-only until source text and market rules are independently checked. |
| warning | `duplicate_example_id` | `market_fit_v2` | `eval_v2_013` | Duplicate key eval_v2_013: market_fit_v2/eval_v2_013, market_fit_v2_candidates/eval_v2_013 |
| warning | `duplicate_source_text` | `market_fit_v2` | `eval_v2_013` | Duplicate key f683b60218663cec342024a2f46523359b2fbc1039243c77d84e3fb47537aaf2: market_fit_v2/eval_v2_013, market_fit_v2_candidates/eval_v2_013 |
| warning | `duplicate_source_url` | `market_fit_v2` | `eval_v2_013` | Duplicate key https://x.com/ColinTCrypto/status/2058219613091995682: market_fit_v2/eval_v2_013, market_fit_v2_candidates/eval_v2_013 |
| warning | `duplicate_x_status` | `market_fit_v2` | `eval_v2_013` | Duplicate key x_status:2058219613091995682: market_fit_v2/eval_v2_013, market_fit_v2_candidates/eval_v2_013 |
| warning | `grok_candidate_requires_review` | `market_fit_v2` | `eval_v2_013` | Treat as candidate-only until source text and market rules are independently checked. |
| warning | `duplicate_example_id` | `market_fit_v2` | `eval_v3_004` | Duplicate key eval_v3_004: market_fit_v2/eval_v3_004, market_fit_v3_candidates/eval_v3_004 |
| warning | `duplicate_source_text` | `market_fit_v2` | `eval_v3_004` | Duplicate key a04944adaf3cfd692d713a5503b82315dcecc7bbd2f15ec895fbc10e95e2667b: market_fit_v2/eval_v3_004, market_fit_v3_candidates/eval_v3_004 |
| warning | `duplicate_source_url` | `market_fit_v2` | `eval_v3_004` | Duplicate key https://x.com/kimmonismus/status/2058226072596971694: market_fit_v2/eval_v3_004, market_fit_v3_candidates/eval_v3_004 |
| warning | `duplicate_x_status` | `market_fit_v2` | `eval_v3_004` | Duplicate key x_status:2058226072596971694: market_fit_v2/eval_v3_004, market_fit_v3_candidates/eval_v3_004 |
| warning | `grok_candidate_requires_review` | `market_fit_v2` | `eval_v3_004` | Treat as candidate-only until source text and market rules are independently checked. |
| warning | `duplicate_example_id` | `market_fit_v2` | `eval_v3_005` | Duplicate key eval_v3_005: market_fit_v2/eval_v3_005, market_fit_v3_candidates/eval_v3_005 |
| warning | `duplicate_source_text` | `market_fit_v2` | `eval_v3_005` | Duplicate key a49b667248795f6fd208e133c12648fdc8aaa67dca0f8c33324b31c096aa75bf: market_fit_v2/eval_v3_005, market_fit_v3_candidates/eval_v3_005 |
| warning | `duplicate_source_url` | `market_fit_v2` | `eval_v3_005` | Duplicate key https://x.com/haider1/status/2058150952100614534: market_fit_v2/eval_v3_005, market_fit_v3_candidates/eval_v3_005 |
| warning | `duplicate_x_status` | `market_fit_v2` | `eval_v3_005` | Duplicate key x_status:2058150952100614534: market_fit_v2/eval_v3_005, market_fit_v3_candidates/eval_v3_005 |
| warning | `grok_candidate_requires_review` | `market_fit_v2` | `eval_v3_005` | Treat as candidate-only until source text and market rules are independently checked. |
| warning | `duplicate_example_id` | `market_fit_v2` | `eval_v3_009` | Duplicate key eval_v3_009: market_fit_v2/eval_v3_009, market_fit_v3_candidates/eval_v3_009 |
| warning | `duplicate_source_text` | `market_fit_v2` | `eval_v3_009` | Duplicate key b0599357ac273dae32a4a03b02d9a7551ca7b1085c130b171d86a9dd7b929702: market_fit_v2/eval_v3_009, market_fit_v3_candidates/eval_v3_009 |
| warning | `duplicate_source_url` | `market_fit_v2` | `eval_v3_009` | Duplicate key https://x.com/ChristianHeiens/status/2058276490979291142: market_fit_v2/eval_v3_009, market_fit_v3_candidates/eval_v3_009 |
| warning | `duplicate_x_status` | `market_fit_v2` | `eval_v3_009` | Duplicate key x_status:2058276490979291142: market_fit_v2/eval_v3_009, market_fit_v3_candidates/eval_v3_009 |
| warning | `grok_candidate_requires_review` | `market_fit_v2` | `eval_v3_009` | Treat as candidate-only until source text and market rules are independently checked. |
| warning | `duplicate_example_id` | `market_fit_v2` | `eval_v3_012` | Duplicate key eval_v3_012: market_fit_v2/eval_v3_012, market_fit_v3_candidates/eval_v3_012 |
| warning | `duplicate_source_text` | `market_fit_v2` | `eval_v3_012` | Duplicate key c98f204e808fd1f4468f2c465917411f78be560baef9881f6d83c67676f7afc4: market_fit_v2/eval_v3_012, market_fit_v3_candidates/eval_v3_012 |
| warning | `duplicate_source_url` | `market_fit_v2` | `eval_v3_012` | Duplicate key https://x.com/iamfakeguru/status/2058198756130959505: market_fit_v2/eval_v3_012, market_fit_v3_candidates/eval_v3_012 |
| warning | `duplicate_x_status` | `market_fit_v2` | `eval_v3_012` | Duplicate key x_status:2058198756130959505: market_fit_v2/eval_v3_012, market_fit_v3_candidates/eval_v3_012 |
| warning | `grok_candidate_requires_review` | `market_fit_v2` | `eval_v3_012` | Treat as candidate-only until source text and market rules are independently checked. |
| warning | `candidate_pack_not_promoted` | `market_fit_v2_candidates` | `eval_v2_001` | Candidate schema version must be explicitly promoted before becoming strict goldens. |
| warning | `grok_candidate_requires_review` | `market_fit_v2_candidates` | `eval_v2_001` | Treat as candidate-only until source text and market rules are independently checked. |
| warning | `candidate_pack_not_promoted` | `market_fit_v2_candidates` | `eval_v2_002` | Candidate schema version must be explicitly promoted before becoming strict goldens. |
| warning | `grok_candidate_requires_review` | `market_fit_v2_candidates` | `eval_v2_002` | Treat as candidate-only until source text and market rules are independently checked. |
| warning | `candidate_pack_not_promoted` | `market_fit_v2_candidates` | `eval_v2_003` | Candidate schema version must be explicitly promoted before becoming strict goldens. |
| warning | `grok_candidate_requires_review` | `market_fit_v2_candidates` | `eval_v2_003` | Treat as candidate-only until source text and market rules are independently checked. |
| warning | `candidate_pack_not_promoted` | `market_fit_v2_candidates` | `eval_v2_004` | Candidate schema version must be explicitly promoted before becoming strict goldens. |
| warning | `grok_candidate_requires_review` | `market_fit_v2_candidates` | `eval_v2_004` | Treat as candidate-only until source text and market rules are independently checked. |
| warning | `candidate_pack_not_promoted` | `market_fit_v2_candidates` | `eval_v2_005` | Candidate schema version must be explicitly promoted before becoming strict goldens. |
| warning | `grok_candidate_requires_review` | `market_fit_v2_candidates` | `eval_v2_005` | Treat as candidate-only until source text and market rules are independently checked. |
| warning | `candidate_pack_not_promoted` | `market_fit_v2_candidates` | `eval_v2_006` | Candidate schema version must be explicitly promoted before becoming strict goldens. |
| warning | `grok_candidate_requires_review` | `market_fit_v2_candidates` | `eval_v2_006` | Treat as candidate-only until source text and market rules are independently checked. |
| warning | `candidate_pack_not_promoted` | `market_fit_v2_candidates` | `eval_v2_007` | Candidate schema version must be explicitly promoted before becoming strict goldens. |
| warning | `grok_candidate_requires_review` | `market_fit_v2_candidates` | `eval_v2_007` | Treat as candidate-only until source text and market rules are independently checked. |
| warning | `candidate_pack_not_promoted` | `market_fit_v2_candidates` | `eval_v2_008` | Candidate schema version must be explicitly promoted before becoming strict goldens. |
| warning | `grok_candidate_requires_review` | `market_fit_v2_candidates` | `eval_v2_008` | Treat as candidate-only until source text and market rules are independently checked. |
| warning | `candidate_pack_not_promoted` | `market_fit_v2_candidates` | `eval_v2_009` | Candidate schema version must be explicitly promoted before becoming strict goldens. |
| warning | `grok_candidate_requires_review` | `market_fit_v2_candidates` | `eval_v2_009` | Treat as candidate-only until source text and market rules are independently checked. |
| warning | `candidate_pack_not_promoted` | `market_fit_v2_candidates` | `eval_v2_010` | Candidate schema version must be explicitly promoted before becoming strict goldens. |
| warning | `duplicate_example_id` | `market_fit_v2_candidates` | `eval_v2_010` | Duplicate key eval_v2_010: market_fit_v2/eval_v2_010, market_fit_v2_candidates/eval_v2_010 |
| warning | `duplicate_source_text` | `market_fit_v2_candidates` | `eval_v2_010` | Duplicate key 819a74d2be70eac3142a163c4eff52fb1790629d72182f996ab02bbb8931ee82: market_fit_v2/eval_v2_010, market_fit_v2_candidates/eval_v2_010 |
| warning | `duplicate_source_url` | `market_fit_v2_candidates` | `eval_v2_010` | Duplicate key https://x.com/coinbureau/status/2058155996019614079: market_fit_v2/eval_v2_010, market_fit_v2_candidates/eval_v2_010 |
| warning | `duplicate_x_status` | `market_fit_v2_candidates` | `eval_v2_010` | Duplicate key x_status:2058155996019614079: market_fit_v2/eval_v2_010, market_fit_v2_candidates/eval_v2_010 |
| warning | `grok_candidate_requires_review` | `market_fit_v2_candidates` | `eval_v2_010` | Treat as candidate-only until source text and market rules are independently checked. |
| warning | `candidate_pack_not_promoted` | `market_fit_v2_candidates` | `eval_v2_011` | Candidate schema version must be explicitly promoted before becoming strict goldens. |
| warning | `grok_candidate_requires_review` | `market_fit_v2_candidates` | `eval_v2_011` | Treat as candidate-only until source text and market rules are independently checked. |
| warning | `candidate_pack_not_promoted` | `market_fit_v2_candidates` | `eval_v2_012` | Candidate schema version must be explicitly promoted before becoming strict goldens. |
| warning | `duplicate_example_id` | `market_fit_v2_candidates` | `eval_v2_012` | Duplicate key eval_v2_012: market_fit_v2/eval_v2_012, market_fit_v2_candidates/eval_v2_012 |
| warning | `duplicate_source_text` | `market_fit_v2_candidates` | `eval_v2_012` | Duplicate key f4c59542d183d45d3fdc476c7bdcca4974127b2887d37cefa827095d79a490bb: market_fit_v2/eval_v2_012, market_fit_v2_candidates/eval_v2_012 |
| warning | `duplicate_source_url` | `market_fit_v2_candidates` | `eval_v2_012` | Duplicate key https://x.com/VladTheInflator/status/2058251938043761032: market_fit_v2/eval_v2_012, market_fit_v2_candidates/eval_v2_012 |
| warning | `duplicate_x_status` | `market_fit_v2_candidates` | `eval_v2_012` | Duplicate key x_status:2058251938043761032: market_fit_v2/eval_v2_012, market_fit_v2_candidates/eval_v2_012 |
| warning | `grok_candidate_requires_review` | `market_fit_v2_candidates` | `eval_v2_012` | Treat as candidate-only until source text and market rules are independently checked. |
| warning | `candidate_pack_not_promoted` | `market_fit_v2_candidates` | `eval_v2_013` | Candidate schema version must be explicitly promoted before becoming strict goldens. |
| warning | `duplicate_example_id` | `market_fit_v2_candidates` | `eval_v2_013` | Duplicate key eval_v2_013: market_fit_v2/eval_v2_013, market_fit_v2_candidates/eval_v2_013 |
| warning | `duplicate_source_text` | `market_fit_v2_candidates` | `eval_v2_013` | Duplicate key f683b60218663cec342024a2f46523359b2fbc1039243c77d84e3fb47537aaf2: market_fit_v2/eval_v2_013, market_fit_v2_candidates/eval_v2_013 |
| warning | `duplicate_source_url` | `market_fit_v2_candidates` | `eval_v2_013` | Duplicate key https://x.com/ColinTCrypto/status/2058219613091995682: market_fit_v2/eval_v2_013, market_fit_v2_candidates/eval_v2_013 |
| warning | `duplicate_x_status` | `market_fit_v2_candidates` | `eval_v2_013` | Duplicate key x_status:2058219613091995682: market_fit_v2/eval_v2_013, market_fit_v2_candidates/eval_v2_013 |
| warning | `grok_candidate_requires_review` | `market_fit_v2_candidates` | `eval_v2_013` | Treat as candidate-only until source text and market rules are independently checked. |
| warning | `candidate_pack_not_promoted` | `market_fit_v2_candidates` | `eval_v2_014` | Candidate schema version must be explicitly promoted before becoming strict goldens. |
| warning | `grok_candidate_requires_review` | `market_fit_v2_candidates` | `eval_v2_014` | Treat as candidate-only until source text and market rules are independently checked. |
| warning | `candidate_pack_not_promoted` | `market_fit_v2_candidates` | `eval_v2_015` | Candidate schema version must be explicitly promoted before becoming strict goldens. |
| warning | `grok_candidate_requires_review` | `market_fit_v2_candidates` | `eval_v2_015` | Treat as candidate-only until source text and market rules are independently checked. |
| warning | `candidate_pack_not_promoted` | `market_fit_v2_candidates` | `eval_v2_016` | Candidate schema version must be explicitly promoted before becoming strict goldens. |
| warning | `grok_candidate_requires_review` | `market_fit_v2_candidates` | `eval_v2_016` | Treat as candidate-only until source text and market rules are independently checked. |
| warning | `candidate_pack_not_promoted` | `market_fit_v3_candidates` | `eval_v3_001` | Candidate schema version must be explicitly promoted before becoming strict goldens. |
| warning | `grok_candidate_requires_review` | `market_fit_v3_candidates` | `eval_v3_001` | Treat as candidate-only until source text and market rules are independently checked. |
| warning | `candidate_pack_not_promoted` | `market_fit_v3_candidates` | `eval_v3_002` | Candidate schema version must be explicitly promoted before becoming strict goldens. |
| warning | `grok_candidate_requires_review` | `market_fit_v3_candidates` | `eval_v3_002` | Treat as candidate-only until source text and market rules are independently checked. |
| warning | `candidate_pack_not_promoted` | `market_fit_v3_candidates` | `eval_v3_003` | Candidate schema version must be explicitly promoted before becoming strict goldens. |
| warning | `grok_candidate_requires_review` | `market_fit_v3_candidates` | `eval_v3_003` | Treat as candidate-only until source text and market rules are independently checked. |
| warning | `candidate_pack_not_promoted` | `market_fit_v3_candidates` | `eval_v3_004` | Candidate schema version must be explicitly promoted before becoming strict goldens. |
| warning | `duplicate_example_id` | `market_fit_v3_candidates` | `eval_v3_004` | Duplicate key eval_v3_004: market_fit_v2/eval_v3_004, market_fit_v3_candidates/eval_v3_004 |
| warning | `duplicate_source_text` | `market_fit_v3_candidates` | `eval_v3_004` | Duplicate key a04944adaf3cfd692d713a5503b82315dcecc7bbd2f15ec895fbc10e95e2667b: market_fit_v2/eval_v3_004, market_fit_v3_candidates/eval_v3_004 |
| warning | `duplicate_source_url` | `market_fit_v3_candidates` | `eval_v3_004` | Duplicate key https://x.com/kimmonismus/status/2058226072596971694: market_fit_v2/eval_v3_004, market_fit_v3_candidates/eval_v3_004 |
| warning | `duplicate_x_status` | `market_fit_v3_candidates` | `eval_v3_004` | Duplicate key x_status:2058226072596971694: market_fit_v2/eval_v3_004, market_fit_v3_candidates/eval_v3_004 |
| warning | `grok_candidate_requires_review` | `market_fit_v3_candidates` | `eval_v3_004` | Treat as candidate-only until source text and market rules are independently checked. |
| warning | `candidate_pack_not_promoted` | `market_fit_v3_candidates` | `eval_v3_005` | Candidate schema version must be explicitly promoted before becoming strict goldens. |
| warning | `duplicate_example_id` | `market_fit_v3_candidates` | `eval_v3_005` | Duplicate key eval_v3_005: market_fit_v2/eval_v3_005, market_fit_v3_candidates/eval_v3_005 |
| warning | `duplicate_source_text` | `market_fit_v3_candidates` | `eval_v3_005` | Duplicate key a49b667248795f6fd208e133c12648fdc8aaa67dca0f8c33324b31c096aa75bf: market_fit_v2/eval_v3_005, market_fit_v3_candidates/eval_v3_005 |
| warning | `duplicate_source_url` | `market_fit_v3_candidates` | `eval_v3_005` | Duplicate key https://x.com/haider1/status/2058150952100614534: market_fit_v2/eval_v3_005, market_fit_v3_candidates/eval_v3_005 |
| warning | `duplicate_x_status` | `market_fit_v3_candidates` | `eval_v3_005` | Duplicate key x_status:2058150952100614534: market_fit_v2/eval_v3_005, market_fit_v3_candidates/eval_v3_005 |
| warning | `grok_candidate_requires_review` | `market_fit_v3_candidates` | `eval_v3_005` | Treat as candidate-only until source text and market rules are independently checked. |
| warning | `candidate_pack_not_promoted` | `market_fit_v3_candidates` | `eval_v3_006` | Candidate schema version must be explicitly promoted before becoming strict goldens. |
| warning | `grok_candidate_requires_review` | `market_fit_v3_candidates` | `eval_v3_006` | Treat as candidate-only until source text and market rules are independently checked. |
| warning | `candidate_pack_not_promoted` | `market_fit_v3_candidates` | `eval_v3_007` | Candidate schema version must be explicitly promoted before becoming strict goldens. |
| warning | `grok_candidate_requires_review` | `market_fit_v3_candidates` | `eval_v3_007` | Treat as candidate-only until source text and market rules are independently checked. |
| warning | `candidate_pack_not_promoted` | `market_fit_v3_candidates` | `eval_v3_008` | Candidate schema version must be explicitly promoted before becoming strict goldens. |
| warning | `grok_candidate_requires_review` | `market_fit_v3_candidates` | `eval_v3_008` | Treat as candidate-only until source text and market rules are independently checked. |
| warning | `candidate_pack_not_promoted` | `market_fit_v3_candidates` | `eval_v3_009` | Candidate schema version must be explicitly promoted before becoming strict goldens. |
| warning | `duplicate_example_id` | `market_fit_v3_candidates` | `eval_v3_009` | Duplicate key eval_v3_009: market_fit_v2/eval_v3_009, market_fit_v3_candidates/eval_v3_009 |
| warning | `duplicate_source_text` | `market_fit_v3_candidates` | `eval_v3_009` | Duplicate key b0599357ac273dae32a4a03b02d9a7551ca7b1085c130b171d86a9dd7b929702: market_fit_v2/eval_v3_009, market_fit_v3_candidates/eval_v3_009 |
| warning | `duplicate_source_url` | `market_fit_v3_candidates` | `eval_v3_009` | Duplicate key https://x.com/ChristianHeiens/status/2058276490979291142: market_fit_v2/eval_v3_009, market_fit_v3_candidates/eval_v3_009 |
| warning | `duplicate_x_status` | `market_fit_v3_candidates` | `eval_v3_009` | Duplicate key x_status:2058276490979291142: market_fit_v2/eval_v3_009, market_fit_v3_candidates/eval_v3_009 |
| warning | `grok_candidate_requires_review` | `market_fit_v3_candidates` | `eval_v3_009` | Treat as candidate-only until source text and market rules are independently checked. |
| warning | `candidate_pack_not_promoted` | `market_fit_v3_candidates` | `eval_v3_010` | Candidate schema version must be explicitly promoted before becoming strict goldens. |
| warning | `grok_candidate_requires_review` | `market_fit_v3_candidates` | `eval_v3_010` | Treat as candidate-only until source text and market rules are independently checked. |
| warning | `candidate_pack_not_promoted` | `market_fit_v3_candidates` | `eval_v3_011` | Candidate schema version must be explicitly promoted before becoming strict goldens. |
| warning | `grok_candidate_requires_review` | `market_fit_v3_candidates` | `eval_v3_011` | Treat as candidate-only until source text and market rules are independently checked. |
| warning | `candidate_pack_not_promoted` | `market_fit_v3_candidates` | `eval_v3_012` | Candidate schema version must be explicitly promoted before becoming strict goldens. |
| warning | `duplicate_example_id` | `market_fit_v3_candidates` | `eval_v3_012` | Duplicate key eval_v3_012: market_fit_v2/eval_v3_012, market_fit_v3_candidates/eval_v3_012 |
| warning | `duplicate_source_text` | `market_fit_v3_candidates` | `eval_v3_012` | Duplicate key c98f204e808fd1f4468f2c465917411f78be560baef9881f6d83c67676f7afc4: market_fit_v2/eval_v3_012, market_fit_v3_candidates/eval_v3_012 |
| warning | `duplicate_source_url` | `market_fit_v3_candidates` | `eval_v3_012` | Duplicate key https://x.com/iamfakeguru/status/2058198756130959505: market_fit_v2/eval_v3_012, market_fit_v3_candidates/eval_v3_012 |
| warning | `duplicate_x_status` | `market_fit_v3_candidates` | `eval_v3_012` | Duplicate key x_status:2058198756130959505: market_fit_v2/eval_v3_012, market_fit_v3_candidates/eval_v3_012 |
| warning | `grok_candidate_requires_review` | `market_fit_v3_candidates` | `eval_v3_012` | Treat as candidate-only until source text and market rules are independently checked. |
| warning | `candidate_pack_not_promoted` | `market_fit_v3_candidates` | `eval_v3_013` | Candidate schema version must be explicitly promoted before becoming strict goldens. |
| warning | `grok_candidate_requires_review` | `market_fit_v3_candidates` | `eval_v3_013` | Treat as candidate-only until source text and market rules are independently checked. |
| warning | `candidate_pack_not_promoted` | `market_fit_v3_candidates` | `eval_v3_014` | Candidate schema version must be explicitly promoted before becoming strict goldens. |
| warning | `grok_candidate_requires_review` | `market_fit_v3_candidates` | `eval_v3_014` | Treat as candidate-only until source text and market rules are independently checked. |

## Promotion Rule

- Structural errors block promotion.
- Grok-sourced rows remain candidates until the source text and market rules are independently checked.
- Duplicate or near-duplicate rows should be merged, dropped, or justified before promotion.
- Strict goldens must pass `make evals` or `make evals-v2` without `--allow-failures`.
