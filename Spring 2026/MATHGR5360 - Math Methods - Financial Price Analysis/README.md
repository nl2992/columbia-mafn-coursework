# MATHGR5360 — Mathematical Methods: Financial Price Analysis

**Term:** Spring 2026  
**Archive type:** Canvas Files export

## Overview

A data-intensive course covering empirical financial-price analysis, statistical mechanics and econophysics, scaling laws, drawdowns, market microstructure, trend following, portfolio construction, and trading-system evaluation.

## Course map

- [`lectures/`](lectures/): introductory econophysics lectures, Fourier-transform notes, and turbulence lectures
- [`assignments/`](assignments/): homework and final-project files
- [`experiments/trend-following/`](experiments/trend-following/): MATLAB trend-following experiment, its CSV input, related workbooks, and result PDFs
- [`code/price-density/`](code/price-density/): C sources for price-change probability-density calculations
- [`data/market/`](data/market/): intraday market-data CSV/ZIP files and variants
- [`data/derived/`](data/derived/): derived numerical text data
- [`workbooks/`](workbooks/): Excel workbooks for empirical analysis and course exercises
- [`visuals/`](visuals/): ticker- and statistic-specific GIF charts
- [`readings/`](readings/): research papers and supporting course material
- [`notes/`](notes/): editable notes and trading-system documents
- [`reference/`](reference/): course description

The MATLAB entry point `experiments/trend-following/main.m` reads the adjacent `HO-5minHLV.csv` and uses `ezread.m`; run it from that experiment directory. Original filenames and data variants are preserved.

## Textbook reference

Benjamin Graham, *Security Analysis*, 6th edition.

The local Columbia MAFN directory contains a file matching this reference. The full textbook file is not included here because redistribution rights were not verified.

## Data note

Large datasets and binary files are tracked with Git LFS. Review source data, external links, and experiment assumptions before reuse.
