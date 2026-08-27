# MATHGR5030 — Numerical Methods in Finance

**Term:** Spring 2026  
**Archive type:** Canvas Files export  
**Original files:** 30

## Course focus

This module develops computational methods used in financial mathematics, including scientific computing, root finding, interpolation and integration, random-number generation, Monte Carlo methods, basket/spread options, SABR and other stochastic-volatility models, copulas, risk parity, least-squares Monte Carlo, and dimensional analysis.

## Module map

| Area | Contents |
| --- | --- |
| Core modules | `M1`–`M9` lecture PDFs covering scientific computing through copulas |
| Topics | `T1 RiskParity`, `T2 LOOLSM`, and `T3 Dimension Analysis` |
| [`HW2/`](HW2/README.md) | Homework 2 |
| [`HW3/`](HW3/README.md) | Basket-option reading, workbook, notebooks, and Python scaffold |
| [`HW4/`](HW4/README.md) | SABR notebook and `option_models` Python package scaffold |
| [`Exam/`](Exam/README.md) | Midterm problem statement and solution |
| [`Reference/`](Reference/README.md) | Papers on risk parity, implied-volatility root finding, SCRIP, and LOOLSM |

## Code assets

- [`HW3/basket.py`](HW3/basket.py) contains Monte Carlo and normal-model basket-option scaffolding. Some sections are deliberately left as instructional exercises.
- [`HW4/option_models/sabr.py`](HW4/option_models/sabr.py) contains SABR model class scaffolding for standard and conditional Monte Carlo approaches.
- The notebooks are the primary computational context for the homework code.

## Local execution

The observed Python imports are `numpy`, `scipy`, and `pyfeng`. Jupyter is useful for the notebooks. Because the exported code contains incomplete teaching exercises and may reflect the original classroom environment, treat it as course scaffolding rather than a production pricing library.

## Related textbooks found locally

The local Columbia MAFN workspace contains two Monte Carlo references: a Jäckel-titled *Monte Carlo Methods in Finance* file and a file titled *Monte Carlo Methods in Financial Engineering*. They are cataloged in the root [TEXTBOOK_CATALOG.md](../../TEXTBOOK_CATALOG.md); full-book binaries were not copied into this repository pending rights verification.
