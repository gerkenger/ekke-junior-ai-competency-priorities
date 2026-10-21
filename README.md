# Junior developer competency priorities: paired analysis

This repository contains the Python analysis supporting the exploratory mini-paper *Independent Code Debugging and AI-Output Verification in Junior Developer Hiring: A Paired Comparison of Perceived Competency Importance*.

It compares two Question 36 items, answered by the same respondent, about hypothetical junior-developer hiring: (A) reading/debugging existing code **without** AI assistance, and (B) evaluating/verifying AI-generated output. It uses a two-sided exact paired sign test and reports a 95% exact Clopper–Pearson confidence interval for the direction **among unequal pairs**.

## Data provenance

**Original dataset:** Kusper, G., Zaletnyik, P. T., Brindusescu, A. A., & Mahringer, T. (2026). *AI Coding Agents and Software Robots in Professional Software Engineering* (Version 1) [Data set]. Zenodo. https://doi.org/10.5281/zenodo.21802516

The dataset's 205-response CSV is available from the above Zenodo record under **Files** as:

`AI Coding Agents and Software Robots in Professional Software Engineering_205.csv`

**The survey data are not included in this code repository.** Download the original CSV from Zenodo to preserve attribution, provenance, and the original publication location. The Zenodo CSV uses **semicolon (`;`) delimiters**; the script detects this automatically. It also accepts a comma-separated CSV export of the original 205-record XLSX. The published dataset contains 205 rows before the analytical Q39 and Q36 screening.

## How to run

1. Install Python 3.13 (the analysis was checked with Python 3.13.5 and SciPy 1.17.0).
2. Download the **original CSV** from the Zenodo record and put it next to `human_control_analysis.py`.
3. In this repository's folder run:

```bash
python -m pip install -r requirements.txt
python human_control_analysis.py --input "AI Coding Agents and Software Robots in Professional Software Engineering_205.csv" --out-dir results
```

If your system uses the `python3` command, substitute `python3` in both lines. On Windows, `py` is another possible launcher. The input can alternatively be a 205-row CSV containing Q39 and both specified Q36 columns, preserving their original questionnaire headers and responses; no pre-filtering should be performed.

## Outputs

The script generates files in the specified `results/` directory:

- `results.json` — data provenance checksum, screening counts, marginal distributions, directional comparisons, exact p-value, confidence interval, and 5×5 cross-tabulation.
- `Q36_kereszttabla.csv` — full cross-tabulation with row and column totals.
- `eredmenyek.md` — compact Hungarian-language descriptive and inferential summary.

The Python program independently verifies the SciPy two-sided binomial p-value against a direct combinatorial calculation. It fails with a clear error if questionnaire columns or response categories do not match those required.

## Expected checks

| Quantity | Expected value |
|---|---:|
| Original responses | 205 |
| Q39 self-reported human/professional-experience responses | 200 |
| Complete ordinal Q36 item pairs | 193 |
| A higher than B | 75 |
| A equals B | 88 |
| B higher than A | 30 |
| Unequal pairs used by the sign test | 105 |
| Conditional share A higher among unequal pairs | 0.7142857 |
| Two-sided exact p-value | 0.0000131536731462 |
| 95% Clopper–Pearson interval (conditional share) | 0.6179–0.7982 |

The analysis was cross-checked against a complete 205-row, 63-column CSV export of the original XLSX. Both comma-separated and semicolon-separated input formats are supported; verification results should match the checks above.

## Interpretation limits

This is an **exploratory** analysis: the distributions were inspected before the final research question and statistical test were fixed. The respondents are not a documented probability sample of all software developers, and respondent independence cannot be guaranteed. The Q36 items measure **ratings of importance in hypothetical junior hiring**, not actual developer competencies, hiring decisions, or instructional effects. The conditional 71.4% figure applies to **105 unequal ratings**, not all 193 valid pairs.

## Software acknowledgement

The analysis script was written with assistance from OpenAI ChatGPT (GPT-6), then checked mathematically. The author reports running the code twice on a personal computer. The versions reported above describe the validated preparation environment, not independently verified details of the author's local system.
