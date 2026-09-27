# STAT 5263 Homework 1 - Starter Script
# Due: October 2, 2026

# ============================================================================
# Problem 1: Simulating Random Processes
# ============================================================================

# 1(a) Normal random process
set.seed(123)  # For reproducibility
n <- 48

# Simulate and plot normal process (repeat several times)
par(mfrow = c(2, 2))
for (i in 1:4) {
  X <- rnorm(n, mean = 0, sd = 1)
  plot(X, type = "l", main = paste("Normal Process", i), 
       xlab = "Time", ylab = "Value")
}
par(mfrow = c(1, 1))

# 1(b) Chi-square random process
par(mfrow = c(2, 2))
for (i in 1:4) {
  X <- rchisq(n, df = 2)
  plot(X, type = "l", main = paste("Chi-square Process", i), 
       xlab = "Time", ylab = "Value")
}
par(mfrow = c(1, 1))

# 1(c) t-distributed random process
par(mfrow = c(2, 2))
for (i in 1:4) {
  X <- rt(n, df = 5)
  plot(X, type = "l", main = paste("t-distributed Process", i), 
       xlab = "Time", ylab = "Value")
}
par(mfrow = c(1, 1))

# 1(d) Benchmark for significance
# For n = 48: ±1.96/sqrt(48) = ?
benchmark <- 1.96 / sqrt(48)
cat("Benchmark (±1.96/sqrt(48)):", round(benchmark, 4), "\n")
cat("Given sample ACF values:\n")
cat("  Normal: 0.27\n")
cat("  Chi-square: -0.08\n")
cat("  t-distributed: 0.04\n")

# ============================================================================
# Problem 2: Stationarity of Processes
# ============================================================================

# Note: Problems 2(a) through 2(e) are theoretical exercises

# ============================================================================
# Problem 3: Constant Process
# ============================================================================

# Theoretical exercise about Yt = X for all t

# ============================================================================
# Problem 4: Sinusoidal Process with Uniform Randomness
# ============================================================================

# 4(a)-(d) Theoretical exercises about Xt = sin(2πUt)

# ============================================================================
# Problem 5: Sum of Uncorrelated Stationary Sequences
# ============================================================================

# Theoretical exercise

# ============================================================================
# Problem 6: Australian Retail Sales Data
# ============================================================================

# Load the retail data
# Note: You'll need to download retail.xlsx from CourseWorks
# and place it in the working directory

library(readxl)  # For reading Excel files

# Load data (adjust filename if needed)
# retail_data <- read_excel("retail.xlsx")

# For now, create placeholder for the analysis
cat("Problem 6: Australian Retail Sales Data\n")
cat("Waiting for retail.xlsx to be downloaded from CourseWorks\n")

# Once data is loaded:
# 6(a) Plot the time series
# plot(retail_data[, 1], type = "l", main = "Supermarket & Grocery Sales (NSW)")

# 6(b) Seasonal plots
# Use ggplot2 or base R to create seasonal plots

# 6(c) Sample ACF
# acf_result <- acf(retail_data[, 1], plot = TRUE)

# 6(d)-(e) Evaluate AI responses about stationarity, trends, and forecasting

# ============================================================================
# Useful functions to remember:
# ============================================================================
# rnorm(), rchisq(), rt()  - Generate random variables
# acf()                     - Compute autocorrelation function
# pacf()                    - Partial autocorrelation function
# mean(), var()             - Summary statistics
# plot()                    - Basic plotting
# read_excel()              - Read Excel files (needs readxl package)
