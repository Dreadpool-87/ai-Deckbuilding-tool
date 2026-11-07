"""Write deterministic, wholly synthetic benchmark inputs; no network or model calls."""
import argparse
import csv
import hashlib
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
BASICS = dict(zip("WUBRG", ("Plains", "Island", "Swamp", "Mountain", "Forest")))
PREPARE = "Benchmark Sentinel // Benchmark Insight"
TRANSFORM = "Benchmark Pupil // Benchmark Nightwing"


def dump(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8", newline="\n")


def card(name, pips, kind, subtype, rules, stats=None, **extra):
    mana = "".join("{" + ch + "}" for ch in pips)
    mv = sum(int(ch) if ch.isdigit() else 1 for ch in pips)
    colors = sorted(set(pips) & BASICS.keys())
    data = {"name": name, "layout": "normal", "manaCost": mana, "manaValue": mv,
            "colors": colors, "colorIdentity": colors, "types": [kind],
            "type": kind + (" — " + subtype if subtype else ""), "subtypes": subtype.split(),
            "supertypes": [], "text": rules}
    if stats:
        data["power"], data["toughness"] = stats.split("/")
    return dict(data, **extra)


def write_case(folder, case, pools):
    folder.mkdir()
    colors = case["colors"]
    variant = case.get("variant")
    oracle = {
        name: [card(name, "", "Land", name, f"({{T}}: Add {{{color}}}.)",
                    type=f"Basic Land — {name}", supertypes=["Basic"],
                    producedMana=[color], colorIdentity=[color])]
        for color, name in BASICS.items()
    }
    rows = []

    def add(record, quantity=4):
        name = record["name"]
        oracle.setdefault(name, []).append(record)
        rows.append((name, quantity, "BCH"))

    for color in colors:
        for label, *fields in pools[color]:
            add(card(f"Benchmark {label}", *fields))

    if len(colors) == 2:
        a, b = colors
        add(card(f"Benchmark {colors} Crossing", "", "Land", "",
                 f"This land enters tapped. {{T}}: Add {{{a}}} or {{{b}}}.",
                 producedMana=list(colors), colorIdentity=list(colors)))

    if variant in {"two", "reduced", "tester-shortage"}:
        alternatives = (
            ("Ember", "R", "Instant", "", "This spell deals 1 damage to any target."),
            ("Courier", "1R", "Creature", "Goblin", "Haste.", "2/2"),
            ("Smasher", "1R", "Creature", "Goblin", "This creature can't be blocked by artifact creatures.", "2/1"),
            ("Furnace", "2R", "Creature", "Elemental", "When this creature enters, it deals 2 damage to each opponent.", "2/2"),
            ("Spitter", "2R", "Creature", "Lizard", "{T}: This creature deals 1 damage to any target.", "2/3"),
            ("Slinger", "2R", "Sorcery", "", "This spell deals 3 damage to target creature. Draw a card."),
            ("Incinerator", "3R", "Creature", "Elemental", "Whenever this creature attacks, it deals 1 damage to each opponent.", "4/2"),
            ("Giant", "4R", "Creature", "Giant", "Trample.", "5/4"),
        )
        for label, *fields in alternatives:
            add(card(f"Benchmark {label}", *fields))

    if variant in {"transform", "ambiguous"}:
        add(card(TRANSFORM, "U", "Creature", "Human Wizard",
                 "At the beginning of your upkeep, you may reveal the top card of your library. "
                 "If it is an instant or sorcery card, transform this creature.", "1/1",
                 layout="transform", side="a", faceName="Benchmark Pupil"), 2)
        oracle[TRANSFORM].append(card(TRANSFORM, "", "Creature", "Insect",
                                      "Flying.", "3/2", layout="transform", side="b",
                                      faceName="Benchmark Nightwing", colors=["U"],
                                      colorIdentity=["U"], manaValue=1))
    if variant == "ambiguous":
        second = "Benchmark Pupil // Benchmark Emberwing"
        oracle[second] = [
            card(second, "R", "Creature", "Human Wizard", "When this creature attacks, transform it.",
                 "1/1", layout="transform", side="a", faceName="Benchmark Pupil"),
            card(second, "", "Creature", "Dragon", "Flying.", "2/2", layout="transform",
                 side="b", faceName="Benchmark Emberwing", colors=["R"], colorIdentity=["R"],
                 manaValue=1),
        ]
        rows = [("Benchmark Pupil", n, printing) if name == TRANSFORM else (name, n, printing)
                for name, n, printing in rows]

    if variant in {"prepare", "contradictory", "tester-prepare"}:
        add(card(PREPARE, "2W", "Creature", "Human Wizard",
                 "Whenever this creature attacks, prepare it.", "2/3", layout="prepare",
                 side="a", faceName="Benchmark Sentinel", colorIdentity=["W", "G"]), 2)
        oracle[PREPARE].append(
            card(PREPARE, "1G", "Sorcery", "", "Draw a card.", layout="prepare", side="b",
                 faceName="Benchmark Insight", colorIdentity=["W", "G"],
                 manaValue=3 if variant == "prepare" else 2))

    if variant in {"reduced", "tester-shortage"}:
        rows = [row for row in rows if row[0] != "Benchmark Spark"]
        rows += [("Benchmark Spark", 1, "BCH"), ("Benchmark Spark", 2, "BCH2")]

    collection = folder / "pool.csv"
    with collection.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(("Name", "Quantity", "Set"))
        writer.writerows(rows)

    deck = {}
    if variant == "tester-control":
        deck = dict.fromkeys(("Peek", "Deny", "Return", "Study", "Exile",
                              "Sweep", "Drake", "Purifier", "Seraph"), 4)
        deck = {f"Benchmark {name}": n for name, n in deck.items()}
        deck.update({"Island": 11, "Plains": 9, "Benchmark WU Crossing": 4})
    elif variant == "tester-shortage":
        deck = {name: 4 for name, _, _ in rows[:9]}
        deck["Benchmark Spark"] = 4
        deck["Mountain"] = 60 - sum(deck.values())
    elif variant == "tester-prepare":
        deck = {name: 4 for name, _, _ in rows[:8]}
        deck.update({PREPARE: 2, "Plains": 14, "Forest": 12})
    if deck:
        assert sum(deck.values()) == 60
        (folder / "frozen.txt").write_text(
            "".join(f"{n} {name}\n" for name, n in deck.items()), encoding="utf-8", newline="\n")

    instruction = (
        "Treat this closed, synthetic universe as the card source for this task. "
        "Benchmark-prefixed cards are intentionally fictitious; do not replace them with real cards. "
        "The listed pool is explicitly confirmed for this run only, with ordinary Casual copy rules "
        "and unlimited Basic lands. Do not use previous conversations or web searches for these records. "
        "Use the configured tool contract if tools are available; retain their actual execution evidence. "
    )
    if variant == "no-tools":
        instruction += "The visible CSV below is the only available input.\n\n" + collection.read_text(
            encoding="utf-8")
    else:
        oracle_file = folder / "oracle.json"
        dump(oracle_file, {"meta": {"version": "benchmark-v1"}, "data": oracle})
        digest = hashlib.sha256(oracle_file.read_bytes()).hexdigest()
        instruction += (
            f"Local files in this case directory: pool.csv and oracle.json. "
            f"Expected synthetic oracle SHA-256: {digest}. "
            "Use Gateway collection scope 'synthetic' if invoking it. "
        )
    if deck:
        instruction += "Use frozen.txt as the immutable baseline. "
    (folder / "task.txt").write_text(case["task"] + "\n\n" + instruction + "\n",
                                      encoding="utf-8", newline="\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="new directory for generated public-safe cases")
    args = parser.parse_args()
    args.output.mkdir()
    cases = json.loads((HERE / "cases.json").read_text(encoding="utf-8"))
    pools = json.loads((HERE / "pools.json").read_text(encoding="utf-8"))
    for case in cases:
        write_case(args.output / case["id"], case, pools)


if __name__ == "__main__":
    main()
