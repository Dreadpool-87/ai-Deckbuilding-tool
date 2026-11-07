# Same-host exploratory pilot

This is one matched pair per role with synthetic inputs. It uses the preregistered rubric in the [benchmark protocol](../README.md). Two fresh Work sessions inherited the same host model and reasoning setting. Exact underlying model revision, decoding controls, token counts and comparable elapsed timing were unavailable. Both arms used the same baseline tool checkout `0fd38ab2846a0e4c575e6ecac947b006407f913b`, Python 3.12.14, matching task and data bytes, local tools, and the same limits. The two cases within each arm shared the same host session, so the Tester pair does not count as a separately seeded replicate.

| Case | Stable result | Candidate result | Critical violations | Strategy score |
| --- | --- | --- | --- | --- |
| B04 Elf tribal | [Answer](B04-elves-stable.md), [validation](B04-elves-stable-validation.json) | [Answer](B04-elves-candidate.md), [validation](B04-elves-candidate-validation.json) | 0 / 0 | 12 / 12 |
| T01 Standard control | [Answer](T01-standard-stable.md), [validation](T01-standard-stable-validation.json) | [Answer](T01-standard-candidate.md), [validation](T01-standard-candidate-validation.json) | 0 / 0 | 11 / 11 |

Strategy scores are out of 12. Two reviewers independently scored the randomized outputs without being given arm labels and agreed in every category. Both Builder runs preserved ownership, exact counts and group/import parity. The decks differed in the land/Beast trade-off (24/2 versus 23/3). Both Tester runs preserved the frozen deck and matched its weighted curve of 104. Each scored 1/2 for card selection because the analysis did not compare marginal cuts with specific eligible alternatives. All Gateway validations returned `VALIDATED_WITH_LIMITATIONS`, Gateway and child exits 0/0. Stable Builder also ran discovery with child exit 0. Gateway actions per arm were 3 stable and 2 candidate. Tool-call timing and host token usage are `NOT_VERIFIED`. A single avoided discovery call cannot establish a general efficiency improvement.

Prompt SHA-256 for this run:

| Role | Stable | Candidate |
| --- | --- | --- |
| Builder | `7091722a2860896e3e9938be0be446f7e554cbe2b8e2676131bd559c767eb9db` | `1c30d1518c824e310b8ee970862bf86b6fa46ef90e80aacf578e71eccaa7a70b` |
| Tester | `a6623ab594552061199ea57bc235e929a38598025c67df11082df6dd41e96c4e` | `d8524eb5e67084950e00d983f2634a1e113e917973aeaff03ba919c702f38753` |

These results are exploratory. They do not establish behavioral equivalence, strategic non-inferiority or cross-host portability. Gate E remains `NOT_VERIFIED`.
