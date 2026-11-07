**COMPLETE FOR STANDARD — frozen white-blue control, 60 main / 0 sideboard.** Gateway: `VALIDATED_WITH_LIMITATIONS`; **MANA CURVE: VERIFIED; OWNERSHIP: PASS** against the declared synthetic pool. The key findings: turn-two {U}{U} is substantially harder than turn-two {1}{W}; only 46.71% on the play naturally see five lands by turn five; and the deck has good ways to reset combat, but only eight dedicated finishers.

**FACT — source and baseline.** Code execution was available (Python 3.12.14); `frozen.txt`, `pool.csv` and `oracle.json` were readable. The exact bytes of `frozen.txt` were unchanged, SHA-256 `90cadc8cf79b8d4d0cca6a5e90d04d68b04ec24bb70d93cae6338253caaca191`. Card facts came only from the synthetic Atomic-style Oracle `benchmark-v1`, with matching SHA-256 `0c012f9ba190c0a7903b91e9b1a07bc9d1de8d2dfd63b2149dbb484c0489f44c`. No unresolved names, tokens, MDFCs, unusual mana costs or Prepare cards. Casual 1v1 assumptions apply.

**DERIVATION [COUNT].** The deck has **24 physical lands (40%) + 36 nonlands = 60**. Bins for MV 0/1/2/3/4/5/6/7+ are **0 / 8 / 8 / 8 / 4 / 8 / 0 / 0**. The ledger reconciles printed costs to Oracle values and yields weighted MV **104**; mean **104/36 = 26/9 ≈ 2.889**, calculated from verified nonland counts. The single confirmed `pool.csv` provides four copies of each of the ten nonbasic names used; each is required four times (e.g. Benchmark WU Crossing: one row of 4 → 4 owned, 4 required). No repeated printings or shortages. Eleven Island and nine Plains qualify for the Basic-land exception. The four-copy check passed separately.

**Mana and opening diagnostics [EXACT].** Benchmark WU Crossing is always tapped on entry (four copies; zero conditionally tapped), and can subsequently make either color, one mana at a time. There are **15 blue sources** (11 immediately usable Islands and 4 Crossings after untapping) and **13 white sources** (9 immediately usable Plains and 4 Crossings after untapping). No nonland mana sources or ramp. {U} supports turn-one Peek or Return; {1}{W} is the first white requirement (Exile), while Deny needs {U}{U} on turn two. Sweep needs {2}{W}{W}; Drake and Seraph need {3}{U}{U} and {3}{W}{W}, respectively.

For a uniform seven from 60 without replacement, the probabilities of opening with **0 through 7 physical lands**, respectively, are **2.161%, 12.104%, 26.941%, 30.870%, 19.645%, 6.933%, 1.255%, 0.090%**. Mean: **2.8**; **2–5: 84.390%**. That last event is about land count, not a keep rate.

| Natural access event | On play | On draw |
|---|---:|---:|
| ≥1 land seen by turn 1 | 97.84% | 98.82% |
| ≥2 lands seen by turn 2 | 90.99% | 94.45% |
| ≥3 lands seen by turn 3 | 78.87% | 85.59% |
| ≥4 lands seen by turn 4 | 63.18% | 72.59% |
| ≥5 lands seen by turn 5 | 46.71% | 57.27% |
| Peek seen by turn 1 | 39.95% | 44.48% |
| Deny or Exile, each individually seen by turn 2 | 44.48% | 48.75% |
| Sweep seen by turn 4 | 52.77% | 56.55% |
| Drake or Seraph, each individually seen by turn 5 | 56.55% | 60.10% |

Land and spell access use `7+t−1` cards on the play and `7+t` on the draw, by the turn's first main phase. Land access is not a count of land drops made, and spell access is not mana access.

| Mana event, with land sequencing only | On play | On draw |
|---|---:|---:|
| Turn 1: an untapped {W} source (no white one-drop in list) | 70.02% | 75.11% |
| Turn 1: an untapped {U} source | 77.76% | 82.37% |
| Turn 2: two usable mana including {W} | 81.54% | 86.65% |
| Same, with Exile also seen | 34.37% | 40.80% |
| Turn 2: two usable {U} mana | 61.11% | 68.56% |
| Same, with Deny also seen | 24.65% | 31.16% |

The turn-two denominator is C(60,s)×(60−s) for the unordered cards available by turn one and the next natural draw, with s=7 on the play and 8 on the draw. This asks whether a legal land sequence can support each specified payment separately, using only lands available at each drop. A turn-two Crossing cannot help that turn; a turn-one Crossing plus an Island can supply {U}{U}, but two Crossings cannot. The lines can require different turn-one choices; these are not gameplay castability or target estimates. All exact figures exclude mulligans, scry, extra draw, opponent actions and other effects.

**Practical verdict [JUDGMENT].** Keep hands with usable early blue or a Crossing you can play before you need to interact, and an actual route to the white or double-blue spell you expect to use. With Crossing plus Island, lead Crossing to hold up Deny on turn two unless you need turn-one Peek or Return. A Plains alongside an Island can pay for Exile but cannot pay for Deny. With no pressure and three open mana, you can hold a counter and spend mana on instant-speed Study if there is no spell worth countering. Peek scries two then draws, improving selection, whereas Study draws two for material recovery. These effects are outside the natural-draw diagnostics.

The four Denys counter spells before they resolve. Four Returns bounce creatures for tempo; they do not permanently remove a reusable threat. Four Exiles permanently answer only attacking or blocking creatures, so a utility creature that stays out of combat can evade them. Four Purifiers can destroy artifacts or enchantments on entry. Four Sweeps destroy all creatures, including yours; avoid committing a finisher when you expect to sweep. There is no direct removal for a resolved planeswalker or graveyard hate. Drake immediately replaces itself and attacks in the air; Seraph's flying and lifelink give a way to race, but it needs to deal damage to gain life. Use one finisher to close and keep a second in reserve when possible.

The most questionable allocations are the fourth Return (weak into repeatable enters triggers; cutting it costs one-mana tempo), fourth Purifier (often just a 2/2 without a target; cutting it costs an answer on a body), fourth Sweep (can clog hands or clear your own clock; cutting it costs recovery against wide boards), and fourth Seraph (adds a five-drop with double white; cutting it costs an evasive stabilizer). These are observations about the frozen list; no swaps were made.

**Execution and limits.** The pinned Validator 1.1.1 used profile `github-main-v0.2`, SHA-256 `ffe3f958c342b70804941e6cec6604544d027cb8141aaf502f7749120f76bac0`. Gateway and child both exited 0; no child failures or uncertainties, `ORACLE_ARITHMETIC_PASS`, Prepare `NOT_APPLICABLE`. Independent checks reconciled the source and list hashes, ownership rows, costs, bin totals, opening distribution and Gateway's 2–5 result; the mana enumeration checked outcome totals and tapped-land cases. Raw evidence is in `02-gateway.*` and `03-exact-audit.*`. Full legality and authenticated ownership are outside Gateway scope. Simulations, London rates, full castability, gameplay and Forge were not computed or run.
