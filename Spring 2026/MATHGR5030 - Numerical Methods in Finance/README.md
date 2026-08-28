# MATHGR5030 — Numerical Methods in Finance

**Term:** Spring 2026  
**Archive type:** Canvas Files export

## Overview

Computational methods for financial mathematics, including root finding, interpolation and integration, random-number generation, Monte Carlo, basket and spread options, SABR and stochastic-volatility models, copulas, risk parity, least-squares Monte Carlo, and dimensional analysis.

## Course map

- [`lectures/`](lectures/): modules M1–M9, from scientific computing and root finding through copulas
- [`topics/`](topics/): risk parity, leave-one-out least-squares Monte Carlo, and dimensional analysis
- [`assignments/hw02/`](assignments/hw02/): homework brief
- [`assignments/hw03/`](assignments/hw03/): basket-option paper, workbook, notebooks, and Python scaffold
- [`assignments/hw04/`](assignments/hw04/): SABR notebook and [`option_models/`](assignments/hw04/option_models/) package scaffold
- [`assessments/midterm/`](assessments/midterm/): midterm problem statement and solution
- [`references/`](references/): supporting research papers

The notebooks and Python files are instructional scaffolding; several routines are intentionally incomplete and are not production pricing libraries.

## Textbook references

- Peter Jäckel, *Monte Carlo Methods in Finance*.
- Paul Glasserman, *Monte Carlo Methods in Financial Engineering*.

The local Columbia MAFN directory contains files matching these references. The full textbook files are not included here because redistribution rights were not verified.

## Technical notes

Observed Python dependencies include `numpy`, `scipy`, and `pyfeng`. The notebooks import the adjacent `basket.py` scaffold and `option_models` package; use the accompanying notebooks to reproduce the exercises.
