#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Reprodukálható H–I/R elemzés: két Q36-kompetencia relatív fontossága.

Forrás: Zenodo 21802516 – AI Coding Agents and Software Robots in Professional
Software Engineering (205 kitöltés). A bemeneti CSV lehet az eredeti, Zenodón közzétett, pontosvesszővel
tagolt teljes adatállomány, vagy annak kivonata a három szükséges
kérdőívoszloppal. Vesszővel és pontosvesszővel tagolt CSV is támogatott.

Futtatás (a két fájlt helyezd ugyanabba a könyvtárba):
    python -m pip install -r requirements.txt
    python human_control_analysis.py --input "AI Coding Agents and Software Robots in Professional Software Engineering_205.csv" --out-dir results

A program nincs a 193 elemzett sorra előszűrve: az eredeti 205-ből
Q39 szerint, majd a két érvényes Q36 válasz szerint választja ki a mintát.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any

from scipy.stats import binomtest

CATEGORIES = [
    "Not important",
    "Slightly important",
    "Moderately important",
    "Very important",
    "Essential",
]
CODE = {label: i + 1 for i, label in enumerate(CATEGORIES)}
HUMAN_Q39 = "Yes, and I answered from my own professional experience"
Q39_HEADER = "Q39. Are you a human?"
Q36_PREFIX = "Q36. Assume you are hiring a junior software developer"
A_ITEM = "[Ability to read and debug existing code without AI assistance]"
B_ITEM = "[Ability to evaluate and verify AI-generated output]"


def find_header(headers: list[str], marker: str, starts_with: str | None = None) -> str:
    matches = [
        header
        for header in headers
        if marker in header and (starts_with is None or header.startswith(starts_with))
    ]
    if len(matches) != 1:
        raise ValueError(f"Váratlan oszlopfejléc-találat ({marker!r}): {matches}")
    return matches[0]


def exact_binomial_p_manual(k: int, n: int) -> float:
    """Kétoldali egzakt előjelpróba p-értéke H0: theta=0,5 esetén.

    A binomiális eloszlás szimmetrikus, ezért mindkét oldalon
    P(X <= min(k, n-k))-t számolunk; az összeg maximum 1.
    Független ellenőrzés a scipy.stats.binomtest mellett.
    """
    smaller = min(k, n - k)
    return min(1.0, 2 * sum(math.comb(n, j) for j in range(smaller + 1)) / (2**n))


def analyze(input_path: Path, output_dir: Path) -> dict[str, Any]:
    # Zenodo distributes the full 205-response CSV with semicolon separation.
    # A comma-separated export or a smaller, unfiltered column extract also works.
    with input_path.open("r", encoding="utf-8-sig", newline="") as handle:
        for delimiter in (";", ",", "\t"):
            handle.seek(0)
            reader = csv.DictReader(handle, delimiter=delimiter)
            headers = list(reader.fieldnames or [])
            try:
                a_header = find_header(headers, A_ITEM, Q36_PREFIX)
                b_header = find_header(headers, B_ITEM, Q36_PREFIX)
                q39_header = find_header(headers, Q39_HEADER)
            except ValueError:
                continue
            rows = list(reader)
            break
        else:
            raise ValueError(
                "Hiányzó Q36/Q39 fejléc vagy nem támogatott CSV-tagolás "
                "(támogatott: pontosvessző, vessző, tabulátor)."
            )

    if not rows:
        raise ValueError("A CSV üres.")

    raw_count = len(rows)
    statuses = Counter((row.get(q39_header) or "").strip() for row in rows)
    human_rows = [row for row in rows if (row.get(q39_header) or "").strip() == HUMAN_Q39]
    valid_pairs: list[tuple[int, int]] = []
    excluded_reasons = Counter()
    data_errors: list[str] = []

    for index, row in enumerate(human_rows, start=1):
        a_raw = (row.get(a_header) or "").strip()
        b_raw = (row.get(b_header) or "").strip()
        if a_raw in CODE and b_raw in CODE:
            valid_pairs.append((CODE[a_raw], CODE[b_raw]))
        elif a_raw in {"Unable to judge", ""} or b_raw in {"Unable to judge", ""}:
            excluded_reasons[(a_raw or "<blank>", b_raw or "<blank>")] += 1
        else:
            data_errors.append(f"Emberi rekord #{index}: ismeretlen kategória: {a_raw!r} / {b_raw!r}")

    if data_errors:
        raise ValueError("Nem elfogadható válaszkategória(k):\n" + "\n".join(data_errors))

    pairs = len(valid_pairs)
    higher_a = sum(a > b for a, b in valid_pairs)
    tied = sum(a == b for a, b in valid_pairs)
    higher_b = sum(a < b for a, b in valid_pairs)
    discordant = higher_a + higher_b
    if discordant == 0:
        raise ValueError("Nincs eltérő értékelés, az előjelpróba nem értelmezhető.")
    if higher_a + higher_b + tied != pairs:
        raise AssertionError("A három irány szerinti csoport nem adja vissza az értékelhető párokat.")

    table = [[sum(a == i and b == j for a, b in valid_pairs) for j in range(1, 6)] for i in range(1, 6)]
    if sum(sum(line) for line in table) != pairs:
        raise AssertionError("A kereszttábla nem adja vissza a mintanagyságot.")

    observed_theta = higher_a / discordant
    test = binomtest(higher_a, discordant, p=0.5, alternative="two-sided")
    ci = test.proportion_ci(confidence_level=0.95, method="exact")
    p_check = exact_binomial_p_manual(higher_a, discordant)
    if abs(test.pvalue - p_check) > 1e-12:
        raise AssertionError("A SciPy és a független kombinatorikus p-érték-ellenőrzés eltér.")

    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / "Q36_kereszttabla.csv").open("w", encoding="utf-8-sig", newline="") as h:
        w = csv.writer(h)
        w.writerow(["Q36/02 \\ Q36/07", *CATEGORIES, "Összesen"])
        for name, nums in zip(CATEGORIES, table):
            w.writerow([name, *nums, sum(nums)])
        w.writerow(["Összesen", *(sum(row[j] for row in table) for j in range(5)), pairs])

    result: dict[str, Any] = {
        "source_file": input_path.name,
        "source_sha256": hashlib.sha256(input_path.read_bytes()).hexdigest(),
        "questions": {"A": a_header, "B": b_header, "filter_Q39": q39_header},
        "raw_n": raw_count,
        "q39_answers": dict(statuses),
        "q39_eligible_n": len(human_rows),
        "q36_unassessable_pairs": [
            {"Q36_02": a, "Q36_07": b, "n": n}
            for (a, b), n in sorted(excluded_reasons.items())
        ],
        "valid_paired_n": pairs,
        "comparisons": {"A_higher": higher_a, "tied": tied, "B_higher": higher_b},
        "discordant_n": discordant,
        "observed_conditional_share": observed_theta,
        "exact_two_sided_sign_test": {
            "null_conditional_probability": 0.5,
            "positive_signs": higher_a,
            "negative_signs": higher_b,
            "p_value": test.pvalue,
            "manual_p_value_check": p_check,
            "alpha": 0.05,
            "conditional_proportion_95CI_clopper_pearson": [ci.low, ci.high],
            "reject_H0_at_alpha_0_05": bool(test.pvalue < 0.05),
        },
        "full_sample_description": {
            "A_higher_percent": 100 * higher_a / pairs,
            "tied_percent": 100 * tied / pairs,
            "B_higher_percent": 100 * higher_b / pairs,
            "net_direction_percent_points": 100 * (higher_a - higher_b) / pairs,
        },
        "marginal_A": {name: sum(table[i]) for i, name in enumerate(CATEGORIES)},
        "marginal_B": {name: sum(row[j] for row in table) for j, name in enumerate(CATEGORIES)},
        "crosstab": table,
    }

    (output_dir / "results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary = (
        "# H–I/R: relatív kompetenciafontosság – elemzési eredmények\n\n"
        f"- Eredeti kitöltések száma: **{raw_count}**\n"
        f"- Q39 alapján megtartott, saját szakmai tapasztalatból válaszoló emberként azonosított kitöltések: **{len(human_rows)}**\n"
        f"- Mindkét Q36-tételben értékelhető párok: **{pairs}**\n"
        f"- Q36/02 fontosabb: **{higher_a} ({100*higher_a/pairs:.1f}%)**\n"
        f"- Egyformán fontos: **{tied} ({100*tied/pairs:.1f}%)**\n"
        f"- Q36/07 fontosabb: **{higher_b} ({100*higher_b/pairs:.1f}%)**\n"
        f"- Az eltérő válaszpárok száma: **{discordant}**\n"
        f"- Feltételes irányarány (Q36/02 magasabb): **{observed_theta:.4f} ({100*observed_theta:.1f}%)**\n"
        f"- Kétoldali egzakt előjelpróba: **p = {test.pvalue:.12g}**\n"
        f"- 95%-os Clopper–Pearson CI (feltételes irányarány): **[{ci.low:.4f}; {ci.high:.4f}]**\n"
        f"- Kétoldali, előre kijelölt szignifikanciaszint: **0,05**; H0-elutasítás: **{'igen' if test.pvalue < 0.05 else 'nem'}**\n"
        f"- Teljes mintás leíró nettó iránykülönbség: **{100*(higher_a-higher_b)/pairs:.1f} százalékpont**\n\n"
        "Az eredmény a két konkrét juniorfelvételi KOMPETENCIAELVÁRÁS fontossági besorolását hasonlítja össze; "
        "nem méri a tényleges kompetenciát, az MI-kimenetek tényleges humán ellenőrzését, "
        "vagy a teljes szoftverfejlesztői populációt. A vizsgálat feltáró jellegű: a leíró "
        "megoszlást a próbabeállítás lezárása előtt már ismertük. A páron belüli 88 egyező "
        "besorolás lényeges leíró adat, a feltételes előjelpróba azonban csak a 105 eltérő párt használja.\n"
    )
    (output_dir / "eredmenyek.md").write_text(summary, encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path(__file__).with_name("human_control_raw_205.csv"))
    parser.add_argument("--out-dir", type=Path, default=Path(__file__).with_name("human_control_results"))
    args = parser.parse_args()
    result = analyze(args.input, args.out_dir)
    test = result["exact_two_sided_sign_test"]
    print(f"Kitöltések: {result['raw_n']} → Q39: {result['q39_eligible_n']} → teljes párok: {result['valid_paired_n']}")
    print(f"Q36/02 magasabb / egyező / Q36/07 magasabb: {result['comparisons']}")
    print(f"Eltérő párok: {result['discordant_n']}; irányarány: {result['observed_conditional_share']:.4f}")
    print(f"Kétoldali egzakt p-érték: {test['p_value']:.12g}")
    ci_low, ci_high = test["conditional_proportion_95CI_clopper_pearson"]
    print(f"95%-os Clopper–Pearson CI: [{ci_low:.4f}, {ci_high:.4f}]")
    print(f"Eredmények: {args.out_dir.resolve()}")


if __name__ == "__main__":
    main()