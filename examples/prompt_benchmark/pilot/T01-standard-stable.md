**COMPLETE FOR STANDARD — Deck Tester v3.4.2.** The unchanged 60-card white-blue control deck has enough cheap interaction to buy time, but its two-mana answers ask for different opening lands. Prioritize an early untapped Island or a planned turn-one Crossing, then make sure you have the color for the answer you expect to need.

[COUNT] **Validation and ownership.** Python 3.12.14 read `frozen.txt`, the sole confirmed synthetic inventory `pool.csv`, and the closed Atomic-style benchmark-v1 Oracle. The main deck is **36 nonlands + 24 physical lands = 60**, with no sideboard, unresolved names, tokens, alternate faces or copy-limit violations. **OWNERSHIP: PASS** against this pool: every listed nonbasic (including Benchmark WU Crossing) needs four copies and has one confirmed row of four; Island and Plains are unlimited Basic lands. I aggregated all pool rows before comparing. Gateway validation was **EXECUTED**, top-level **VALIDATED_WITH_LIMITATIONS**, gateway and Validator child exits **0/0**. The frozen list was checked against the validated SHA and left unchanged.

[COUNT] **Mana curve: PASS.** MV bins 0/1/2/3/4/5/6/7+: **0/8/8/8/4/8/0/0**. The per-card ledger checks the Oracle value against printed cost; all records use normal layouts. The weighted sum is **104** and the nonland average is **104 ÷ 36 = 2.889**, calculated from verified counts. There are **11 Islands, 9 Plains and 4 always-tapped Crossings** (zero conditional taplands). That's 15 blue and 13 white land sources, with Crossing counted in each color but paying only one mana per tap. There is no ramp or other fixing in the list.

[EXACT] **Opening and land drops.** With 24 physical lands in 60, the opening seven averages **2.80 lands**. The probabilities for **0 through 7** lands are **2.16%, 12.10%, 26.94%, 30.87%, 19.64%, 6.93%, 1.25%, 0.09%**, respectively. **84.39%** have 2–5 lands; this is a land range, not a keep rate. The following are probabilities of *seeing* at least the required number of physical lands by each turn, in 1v1 with natural draws, no mulligans and no card selection.

| At least this many lands by that turn | T1 | T2 | T3 | T4 | T5 |
|---|---:|---:|---:|---:|---:|
| Play | 97.84% | 90.99% | 78.87% | 63.18% | 46.71% |
| Draw | 98.82% | 94.45% | 85.59% | 72.59% | 57.27% |

[EXACT] **Key-card access.** With the same draw assumptions, the chance to see at least one copy of Deny or Exile, **each measured separately**, is **44.48% play / 48.75% draw** by turn two. Sweep by turn four is **52.77% / 56.55%**. Drake and Seraph are each **56.55% / 60.10%** by turn five. These are cards seen, not spells paid for.

[EXACT] **Turn-two mana only, from land drops.** This selected comparison asks whether the lands seen can produce the named payment **on T2**, with a legal T1 and T2 drop sequence; it does not require drawing the spell, model opposing targets, use Peek, or claim that the best sequence can be predicted on turn one. A Crossing can provide mana only if played on T1. “Color shortfall” is the difference from being able to produce any two mana.

| Turn-two test | Play | Draw |
|---|---:|---:|
| Any two mana | 89.71% | 93.55% |
| Benchmark Exile: `{1}{W}` | 81.54% | 86.65% |
| Benchmark Deny: `{U}{U}` | 61.11% | 68.56% |
| Exile color shortfall | 8.17 pp | 6.91 pp |
| Deny color shortfall | 28.59 pp | 24.99 pp |

[JUDGMENT] **How to play it.** Crossing into Island supports either Exile or Deny, depending on which color Crossing supplies. Crossing into Plains supports Exile but not Deny. An Island on turn one lets you cast Peek (scry two, then draw) or hold up Return; a Crossing may be the better first drop if T2 Deny matters and an Island is already in hand. Favor hands that offer a real early action in their available colors. Two lands alone can be misleading, especially if both are Crossings. Keep planning for `{2}{W}{W}` for Sweep: the early single-white benchmark does not cover it. Drake also needs `{U}{U}` at five mana and Seraph needs `{W}{W}`; don't assume that reaching five lands pays for either finisher.

[JUDGMENT] **Control plan and pressure points.** Deny answers a spell on the stack; Exile permanently removes an attacking or blocking creature, so it cannot stop a creature that stays out of combat. Return buys time or lets you reuse a Purifier or Drake if the tempo loss is acceptable. Pass with mana up when Deny or Exile could matter; if no answer is needed and the window allows, use Study at the opponent's end step to draw two. Sweep clears both sides, so avoid committing a finisher into your own likely reset. After a Sweep, Drake replaces itself on entry and attacks in the air; Seraph adds flying lifelink to help stabilize. Purifier gives four artifact/enchantment answers. There is no dedicated graveyard hate and little recourse against resolved noncreature permanents outside Purifier's targets.

[JUDGMENT] **Four slots to watch, with the baseline kept intact.** Return is temporary and can let an opponent replay an enter ability, but it's the cheapest creature interaction. Purifier can lack a target, but it's the dedicated artifact/enchantment answer. Sweep can strand in hand on one white source or cost you your own creature, but catches up against a wide board. Four Seraphs contribute to the eight five-drops, but removing their role would cost evasive pressure and lifelink.

**Evidence and limits.** Oracle SHA-256 `0c012f9ba190c0a7903b91e9b1a07bc9d1de8d2dfd63b2149dbb484c0489f44c`; frozen list SHA-256 `90cadc8cf79b8d4d0cca6a5e90d04d68b04ec24bb70d93cae6338253caaca191`; Validator v1.1.1 profile `github-main-v0.2`, SHA-256 `ffe3f958c342b70804941e6cec6604544d027cb8141aaf502f7749120f76bac0`. Exact calculations used without-replacement counts; checks reconciled the curve, inventory and distributions, and verified that a freshly drawn Crossing cannot pay immediately, one dual cannot pay both blue pips, and two Crossings alone cannot provide two mana on T2. No Monte Carlo, mulligan simulation or gameplay test was run.
