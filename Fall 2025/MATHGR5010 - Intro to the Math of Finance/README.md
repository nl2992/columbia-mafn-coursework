# MATHGR5010 — Intro to the Math of Finance

**Term:** Fall 2025  
**Archive type:** Canvas Files export  
**Original files:** 41

## Course focus

The syllabus describes an applied introduction to mathematical methods for derivative pricing, risk management, and portfolio management. The archive follows the course progression from probability and arbitrage through futures, options, stochastic processes, Black–Scholes, bonds, portfolio theory, leverage, and value-at-risk.

## Module map

| Area | Contents |
| --- | --- |
| Core notes | `GR5010_Handout0_2025.pdf` through `GR5010_Handout17DynamicLeverage2025.pdf`, including probability, arbitrage, futures, options, Brownian motion, Greeks, Itô/PDE methods, Monte Carlo, bonds, portfolios, VaR, insurance, and leverage |
| Assignments and assessments | Four homework PDFs, midterm, practice final, and take-home final |
| Market and reading material | Bloomberg futures/volatility examples, negative-interest-rate Q&A, and the course readings list |
| Computational work | MATLAB scripts, Excel workbooks, and VBA starter text |

## Computational assets

| File | Purpose |
| --- | --- |
| [`BlackScholesStocks.m`](BlackScholesStocks.m) | Black–Scholes call/put pricing function |
| [`BlackScholesGraph.m`](BlackScholesGraph.m) | Compares a Black–Scholes call price curve with its terminal payoff |
| [`BrownianMotion.m`](BrownianMotion.m) | Simulates and plots multiple Brownian-motion trajectories |
| [`Excel2025OptionModel_NewMacExcelVersion.xlsm`](Excel2025OptionModel_NewMacExcelVersion.xlsm) | Macro-enabled options model workbook |
| [`BrownianMotion.xls`](BrownianMotion.xls) | Spreadsheet-based Brownian-motion exercise |
| [`HW1SPYmovingAve.xls`](HW1SPYmovingAve.xls), [`HW1SPYvol.xls`](HW1SPYvol.xls), [`Oil_CLZ25.xls`](Oil_CLZ25.xls) | Market-data and quantitative exercises |
| [`ExcelVBAoptionsCodeToModify2025.txt`](ExcelVBAoptionsCodeToModify2025.txt) | VBA code provided for modification |

## Suggested study path

1. Read the syllabus and Handouts 0–4 for probability, arbitrage, and futures.
2. Continue through Handouts 5–12 for options, stochastic processes, Itô/PDE methods, and Monte Carlo.
3. Finish with Handouts 13–17 for risk, fixed income, portfolios, insurance, and leverage.
4. Use the MATLAB and Excel assets as computational companions to the notes.

## Reproducibility notes

The MATLAB examples are teaching scripts rather than a packaged library. `BlackScholesStocks.m` uses `normcdf`, and `BlackScholesGraph.m` expects the function file to be on the MATLAB path. The Brownian-motion script uses a large nested-loop simulation and may take time to run. Macro-enabled Excel content should only be enabled when the workbook is trusted.

The syllabus is the authoritative source for course policies, assessment weighting, dates, and required readings.

## Related textbook found locally

The local Columbia MAFN workspace contains a copy matching the syllabus reference, *Options, Futures, and Other Derivatives*, 9th edition by John Hull. It is cataloged in the root [TEXTBOOK_CATALOG.md](../../TEXTBOOK_CATALOG.md) but was not copied into this repository because the source filename indicates a third-party archive and redistribution rights have not been verified. The same catalog also records *Active Portfolio Management* as a supplementary reference shared with MATHGR5380.
