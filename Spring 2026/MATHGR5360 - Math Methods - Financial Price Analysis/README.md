# MATHGR5360 — Mathematical Methods: Financial Price Analysis

**Term:** Spring 2026  
**Archive type:** Canvas Files export  
**Original files:** 240

## Course focus

This is the largest and most data-intensive module in the archive. The course description and filenames indicate a blend of empirical financial-price analysis, statistical mechanics/econophysics, scaling laws, drawdowns, market microstructure, trend-following, portfolio construction, and trading-system evaluation.

## Module map

| Area | Contents |
| --- | --- |
| Course logistics | [`CourseDescription--FinancialPriceAnalysis--Spring2026.pdf`](<CourseDescription--FinancialPriceAnalysis--Spring2026.pdf>) |
| Market data | Intraday CSV files and ZIP archives, including 1-minute and 5-minute series, plus ticker-level datasets such as `HO-5minHLV.csv` |
| Empirical analysis | Excel workbooks and spreadsheets for volatility, variance ratios, probability densities, futures, commodities, drawdowns, CTA analysis, and transaction costs |
| Trading research | Trend following, optimization, push-response, market impact, strategy evaluation, and portfolio/drawdown constraints |
| Econophysics and stochastic methods | Brownian motion, Lévy scaling, power laws, turbulence, kinetic theory, and agent-based/zero-intelligence models |
| Research references | Papers and lecture material retained as PDFs, with original filenames and citation-style names |
| Visual outputs | Ticker- and statistic-specific GIF charts such as `CT`, `DES`, and `GPO` variants |
| Code | [`main.m`](main.m), [`ezread.m`](ezread.m), [`pdf-1min.c`](<pdf-1min.c>), and [`pdf-1sec.c`](<pdf-1sec.c>) |

## Computational entry points

[`main.m`](main.m) is a MATLAB trading-system experiment. It reads [`HO-5minHLV.csv`](<HO-5minHLV.csv>), uses [`ezread.m`](ezread.m) for mixed text/numeric CSV input, evaluates an in-sample/out-of-sample breakout and stop-loss configuration, and plots price, thresholds, trades, equity, and drawdown-related outputs. The script is a course/research experiment and should be reviewed before reuse.

The two C files provide low-level PDF/statistical computation examples. The spreadsheet and data assets are complementary to the papers and lecture material; they are not normalized into a single dataset schema.

## Data and reproducibility notes

- Several large ZIP archives contain market data and are tracked with Git LFS at repository level.
- Dataset naming encodes frequency, instrument, and missing-value treatment in many cases, for example `1min`, `5minHLV`, `Full`, `Day`, `skip`, and `HoldLastValue`.
- The course description lists dates and grading; it is the authoritative source for those details.
- Original filenames, including spaces, punctuation, and duplicated variants, are preserved to avoid losing source provenance.

## Related textbook found locally

The local Columbia MAFN workspace contains a full *Security Analysis*, 6th edition, file by Benjamin Graham as a supplementary value/market-analysis reference. It is cataloged in the root [TEXTBOOK_CATALOG.md](../../TEXTBOOK_CATALOG.md) but was not copied into this repository pending rights verification.
