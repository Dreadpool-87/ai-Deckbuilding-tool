Code execution: **yes** (Python 3.12.14). Both `pool.csv` and `oracle.json` were readable; card facts come only from the synthetic Atomic-style Oracle, `benchmark-v1`. Oracle SHA-256 matched `e6eb4182d0474f6bf4691f487376b4b3f1e9435264252488aed77189a1c4d426`. The selected Validator 1.1.1 profile, `github-main-v0.2`, matched its pin `ffe3f958c342b70804941e6cec6604544d027cb8141aaf502f7749120f76bac0`.

**Mono-green Elf go-wide — 60 cards.** Develop cheap Elves, turn them into a threatening board with Benchmark Leader, and push through blockers with Benchmark Surge. Benchmark Reclaimer and Benchmark Companion help rebuild; Benchmark Beast gives the deck a threat that works on an empty board.

**Finalists [JUDGMENT].** Elf go-wide uses the eight one-drops and four Gatherings to maximize Leader and Surge while keeping room for Hunt and Shatter. Elf midrange uses the same early Scouts and recovery cards but shifts toward the fourth Beast and more standalone threats at the expense of a Surge or another Elf payoff; it plays better into repeated removal but has less closing power once it has several bodies. Green was the only eligible color and the pool had no eligible nonbasic fixing; the two options compete for slots within the same owned pool.

**Synergy-package decision [JUDGMENT].** I kept four Leaders, four Gatherings and three Surges because cheap bodies create pressure early and let a single spell break a stalled board. The strongest rejected alternative was a fourth Beast over the third Surge: Beast has a better floor after a wipe, but it neither grows with Leader nor turns a wide board into a trampling attack. Three Beasts and eight recovery/advantage creatures are enough to diversify the plan without making the opening turns slower.

**Creatures (23)**
- 4 × Benchmark Scout
- 4 × Benchmark Archer
- 4 × Benchmark Leader
- 4 × Benchmark Reclaimer
- 4 × Benchmark Companion
- 3 × Benchmark Beast

**Instants (3)**
- 3 × Benchmark Shatter

**Sorceries (11)**
- 4 × Benchmark Gathering
- 4 × Benchmark Hunt
- 3 × Benchmark Surge

**Lands (23)**
- 23 × Forest

```text
4 Benchmark Scout
4 Benchmark Archer
4 Benchmark Leader
4 Benchmark Reclaimer
4 Benchmark Companion
3 Benchmark Beast
3 Benchmark Shatter
4 Benchmark Gathering
4 Benchmark Hunt
3 Benchmark Surge
23 Forest
```

**How it plays.** FACT: Scout taps for green once summoning sickness no longer prevents it; a turn-one Scout plus a second Forest can accelerate a three-mana play on turn two. Gathering makes two **1/1 green Elf Warrior creature tokens**, with no intrinsic abilities. They get +1/+1 from each Leader. A Leader buffs other Elves, including other Leaders, but never itself. Gathering on turn two into Leader on turn three produces two 2/2 tokens that can already attack. Companion needs another Elf to draw, so after a wipe start with a cheap Elf, Gathering, or Reclaimer before relying on Companion. Reclaimer can return any target card from your graveyard to hand, such as a killed Leader, a spent Gathering or an answered Surge; graveyard exile can cut off that line. Surge gives all your creatures +3/+3 and trample for the turn, including Beast. These are finite synergies, with no loop. A Scout tapped to pay for Surge cannot also attack.

**Interaction [COUNT].** Four Hunts at MV 3 are creature removal through a fight, requiring both a creature you control and a creature you don't control; the opponent can answer your fighter in response, and a small Elf may trade down. Leader and Beast improve that line. Three Shatters at MV 2 destroy an artifact or enchantment at instant speed. Four Archers have reach; they block flyers but supply no evasion. Three Beasts have trample and three Surges grant it to the team. There are zero direct answers to planeswalkers or opposing graveyards and zero sweepers. Large creatures can outsize Hunt and wide boards can force defensive play until a Surge turns the race. Against a likely wipe, keep a reload card instead of spending all your Elf bodies. Companion (four conditional draws) and Reclaimer (four targeted recursions) give recovery without protection or an immediate replacement board.

**Marginal slots [JUDGMENT].** The fourth Hunt is weakest against creature-light decks; the replacement role is an independent threat or a more reliable answer. The third Shatter can be dead without a target; it is the first slot to turn into pressure when artifacts and enchantments are scarce. The third Surge is weak after a wipe; it is the slot for another standalone threat if games consistently empty the board. The only three unused eligible copies are the fourth Beast (the best independent threat, but another {2}{G}{G} non-Elf), fourth Shatter (useful if its targets are common), and fourth Surge (more closing power but risks multiples without a board). Those are conditional swap ideas; the list above is the validated one.

**Counts and evidence.** DERIVATION [COUNT]: I set 23 Forests first (38.33% of the deck) to support the double-green four- and five-mana spells even when Scout dies. There are 23 unconditional green land sources, zero conditional land sources, zero always- or conditionally-tapped lands, and four green nonland sources in Scout, which needs to be untapped and able to activate. Key demands are turn-one {G} for Scout or Archer, two total mana including {G} for the turn-two Elf setup, and {G}{G} for Beast or Surge. No alternative casting mode, land face, or Prepare layout applies. Nonland printed MV bins for 0/1/2/3/4/5/6/7+ are **0 / 8 / 15 / 8 / 3 / 3 / 0 / 0** (37 cards, weighted MV 89, mean 89/37). DERIVATION [EXACT]: in a uniform seven-card opening hand, the probability of 2–5 physical lands is **53613/65018 = 82.458704%**, summing C(23,k)C(37,7−k)/C(60,7) for k=2…5. This excludes Scout and mulligans; keep rate, castability and gameplay were not computed.

**Final checklist.** The sole active pool is the confirmed synthetic `pool.csv`; no merges, unavailable-card exceptions, token rows, unresolved names or unverified cards. The four off-color basics (Island, Mountain, Plains, Swamp) are outside the mono-green scope. All 37 nonlands are within owned quantities and the four-copy limit; 23 Basic Forests use the unlimited exception. Single independent deck; cross-deck allocation is not applicable. Grouped and import counts reconcile to 60. No commander dependence. Early Elf density, Leader and Surge give repeatable pressure; holding a reload addresses the wipe risk, and Beast supplies the runner-up plan's best standalone threat. Gateway returned **`VALIDATED_WITH_LIMITATIONS`**, execution and child exit 0; Validator copy limit, ownership against this declared pool, deck size, Oracle lookup and curve all passed. Failures and child uncertainties were empty; mana curve integrity was `ORACLE_ARITHMETIC_PASS` and Prepare audit was `NOT_APPLICABLE`. This is structural evidence, not complete legality, authenticated ownership or proof of strategic superiority. Raw output and exit evidence are in `02-gateway.*`.
