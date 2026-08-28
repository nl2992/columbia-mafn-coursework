# MATHGR5010 — Intro to the Math of Finance

**Term:** Fall 2025  
**Archive type:** Canvas Files export

## Overview

An applied introduction to mathematical finance: probability, arbitrage, futures, options, Brownian motion, Itô/PDE methods, Monte Carlo, bonds, portfolio theory, leverage, and value-at-risk.

## Course map

- [`lectures/`](lectures/): Handouts 0–17, from probability and arbitrage through portfolio insurance and dynamic leverage
- [`assignments/`](assignments/): homework files and the volatility-smile exercise
- [`assessments/`](assessments/): midterm, practice final, and take-home final
- [`computational/matlab/`](computational/matlab/): Black–Scholes and Brownian-motion scripts
- [`computational/excel/`](computational/excel/): option, futures, Brownian-motion, volatility, and VBA workbooks
- [`readings/`](readings/): market and course reading material
- [`reference/`](reference/): syllabus

Recommended order: syllabus and Handouts 0–4, Handouts 5–12, then Handouts 13–17. Use the MATLAB and Excel files alongside the lecture sequence.

## Textbook references

- John Hull, *Options, Futures, and Other Derivatives*, 9th edition — ISBN 9780133456318.
- Richard C. Grinold and Ronald N. Kahn, *Active Portfolio Management: A Quantitative Approach for Providing Superior Returns and Controlling Risk* — ISBN 9780070248823.

The local Columbia MAFN directory contains copies matching these references. The full textbook files are not included here because redistribution rights were not verified.

## Technical notes

`BlackScholesGraph.m` calls `BlackScholesStocks.m`; `BrownianMotion.m` simulates Brownian-motion trajectories. The MATLAB examples use `normcdf`; the macro-enabled Excel workbook should only be opened when the source is trusted. The syllabus remains authoritative for course policies and required readings.
