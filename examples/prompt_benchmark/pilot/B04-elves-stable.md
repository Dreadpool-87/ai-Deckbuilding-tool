Code execution: yes (Python 3.12.14). Files readable: yes. Card source: closed synthetic Atomic-style Oracle, benchmark-v1, SHA-256 `e6eb4182d0474f6bf4691f487376b4b3f1e9435264252488aed77189a1c4d426`.

**Mono-green Elf swarm — exactly 60 cards, Casual 1v1.** Build a board of cheap Elves, grow it with Benchmark Leader, and use Benchmark Surge to push through blockers. Benchmark Companion and Benchmark Reclaimer give the deck a way to rebuild when the first wave is answered.

**Synergy-package decision [JUDGMENT].** The Elf swarm can start on turn one with Scout or Archer, use Gathering to add two bodies, and turn those bodies into damage or cards with Leader and Companion. The strongest alternative is a heavier Beast-and-Hunt midrange build: a standalone 5/4 trampler is useful after a wipe, but more four-mana non-Elves would delay development or displace interaction and would neither receive Leader's bonus nor enable Companion. Two Beasts preserve the independent threat; the remaining slots favor a broad board with Surge as the shared payoff. The closed pool offers no comparable control or combo plan.

| Group | Cards |
|---|---|
| Creatures (22) | 4 × Benchmark Scout; 4 × Benchmark Archer; 4 × Benchmark Leader; 4 × Benchmark Reclaimer; 4 × Benchmark Companion; 2 × Benchmark Beast |
| Instants (3) | 3 × Benchmark Shatter |
| Sorceries (11) | 4 × Benchmark Gathering; 4 × Benchmark Hunt; 3 × Benchmark Surge |
| Lands (24) | 24 × Forest |

```text
4 Benchmark Scout
4 Benchmark Archer
4 Benchmark Leader
4 Benchmark Reclaimer
4 Benchmark Companion
2 Benchmark Beast
3 Benchmark Shatter
4 Benchmark Gathering
4 Benchmark Hunt
3 Benchmark Surge
24 Forest
```

[COUNT] **Mana.** 24 lands (40%), all untapped Forests; 24 unconditional green land sources and zero land sources of any other color. Scout adds four potential green sources that need to survive until they can tap. Nonland MV 0/1/2/3/4/5/6/7+: **0/8/15/8/2/3/0/0**, respectively. Scout and Archer each need green on turn one; Gathering and Leader each need `{1}{G}` to build the board early. Beast and Surge need double green; reaching four or five mana is the bottleneck. I set 24 lands before filling spells to support that top end without requiring Scout to survive. [EXACT] **84.39%** of fresh seven-card hands have 2–5 physical lands, using 24/60; this is a land-range result.

**Enablers, payoffs and recovery [JUDGMENT].**

- **Develop:** Scout is an Elf that ramps once it can tap; don't count it as mana the turn it enters. With two Forests and a surviving turn-one Scout, turn two can support a three-mana play. If Companion is that play, keep another Elf on the battlefield through its enter-trigger check to draw. Archer starts the Elf count and has reach; Gathering creates **two 1/1 green Elf Warrior creature tokens** with no printed abilities.
- **Press:** Leader gives each *other* Elf you control +1/+1, so Gathering's tokens each grow with a Leader present; removing the Leader shrinks them immediately. The bonus helps your Elves survive fights, but Hunt still needs a suitable creature on each side and does nothing on an empty board. Use Hunt to clear a key blocker, then Surge to give the creatures you control +3/+3 and trample until end of turn. Surge is best with attackers already able to attack; it does not grant haste. These are conditional synergies, not a deterministic combo.
- **Rebuild:** Keep a follow-up threat in hand when already ahead. After a wipe, Reclaimer puts a target card from your graveyard back into your hand: Gathering rebuilds width, Leader restores the anthem, and Surge gives a rebuilt board a second finish. Reclaimer needs an eligible target and doesn't put it straight onto the battlefield. Companion refills only with another Elf, so lead with a cheap Elf or Gathering first when you can. Beast pressures independently of those pieces.

[COUNT] **Roles and gaps.** 20 Elf creature cards plus 4 Gathering; 4 creature removal spells (board-dependent Hunt), 3 artifact/enchantment answers (Shatter), 2 bodies with inherent trample (Beast) and 3 team trample effects (Surge). For card advantage there are 4 conditional Companion draws and 4 Reclaimer recursion cards, plus Gathering's 4 two-body effects. The main closers are the 3 Surge and 2 Beast copies, with 4 Leader supporting the swarm. There is no dedicated graveyard hate, sweep or direct planeswalker removal in this list; a large blocker can also be too big to fight without losing a threat.

**Weakest slots [JUDGMENT].** Shatter can sit dead without a target, Hunt requires both a board and a favorable fight, and Beast doesn't advance the Elf package. If expanding the pool later, look for a flexible green permanent answer, less risky creature interaction, or a resilient Elf finisher, respectively. All ten nonbasic names are represented. The four unused copies are two Beasts (keep the curve and Elf density), one Shatter (avoid too many narrow draws), and one Surge (avoid stacking five-drops that need a board).

**Validation.** Active collection: this run's synthetic `pool.csv` only; no prior collection to add or replace, no tokens or emblems skipped, no unresolved names, and no committed-card exclusions. Pool mode: **INDEPENDENT_DECKS**; per-deck ownership **PASS**; independent pool reset **PASS** (one deck built from the full eligible pool); cross-deck physical assembly **NOT CHECKED**. Gateway validation was **EXECUTED**, result **VALIDATED_WITH_LIMITATIONS**, gateway and Validator child exits **0/0**. Exact size **36 + 24 = 60**, copy limit and ownership passed (Basic Forest is unlimited); no commander-dependent cards or alternate layouts. The displayed list and import block reconcile with the validated list. Gateway discovery was **EXECUTED** and returned **CANDIDATES_NOT_VALIDATED**; the deck decisions use the actual Oracle text, not search coverage alone. Validator v1.1.1, `github-main-v0.2`, SHA-256 `ffe3f958c342b70804941e6cec6604544d027cb8141aaf502f7749120f76bac0`. This is structural validation against the synthetic inputs; no gameplay, mulligan or win-rate test was run.
