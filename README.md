# **Closed Loop Leverage Grid Bot Optimizer**

**A Defensive, Quantitative Engine for Deriving Grid Bot Parameters.**

This project implements the "Closed Loop" theory of leverage trading. Instead of guessing leverage and stop losses, this system calculates them mathematically based on market volatility, drift, and fee structures.

## **🧠 The Theory (The "Closed Loop")**

In a generic grid bot, users select leverage (e.g., 10x) and hope they don't get liquidated. In a **Closed Loop System**, leverage is an **output**, not an input.

1. **Volatility Cone:** We use Geometric Brownian Motion to calculate the probability bounds ($2\\sigma$) of price for the bot's duration.  
2. **Sane Stop Loss:** Calculated as Lower Bound \- Noise Buffer (ATR). This is the invalidation point.  
3. **Target Liquidation:** We engineer the margin such that Liquidation is mathematically forced to be **below** the Stop Loss.  
4. **Implicit Leverage:** The system tells you exactly how much Margin vs. Notional Value to deploy to achieve this safety structure.

## **🛠️ Installation**

pip install \-r requirements.txt

## **🚀 Usage**

Run the main script to analyze a ticker:

python \-m src.main

Or import the module in your own scripts:

from src.optimizer import ClosedLoopOptimizer  
\# ... see src/main.py for full implementation

## **🌐 Supported Exchanges**

The bot uses the ccxt library to fetch fees and data.  
Check if your exchange is supported here:  
👉 CCXT Supported Cryptocurrency Exchange Markets  
If your exchange is **not** on this list (or not in your local library version), the bot will run in **Offline Mode**:

1. It will fallback to **Binance** to fetch general Funding Rates and Spread.  
2. It will ask you to **manually input** your Maker/Taker fees.

## **🔍 Output Legend & Troubleshooting**

When running the report, the optimizer might refuse to generate parameters. Here is how to interpret those signals.

### **⛔ STOP: Negative Edge/Kelly**

This is a mathematical safety trigger. It means **you are statistically likely to lose money** on this trade configuration.

* **What is "Kelly"?** The Kelly Criterion is a formula used to determine the optimal bet size. If the result is zero or negative, the optimal strategy is to **bet nothing**.  
* **The Math:**$$Kelly \\% \= P\_{win} \- \\frac{1 \- P\_{win}}{\\text{Reward-to-Risk Ratio}}$$  
* **Why it happens:**  
  * **Risk is too high:** Your Stop Loss (derived from volatility) is too far away compared to your Take Profit target (Upper Bound).  
  * **Drift is negative:** The asset is trending downwards, but you are trying to open a Long Grid.  
* **How to Fix:**  
  1. **Wait:** Market conditions are currently unfavorable.  
  2. **Increase Duration:** Longer runtimes expand the upper bound (Reward), potentially fixing the ratio.

### **⛔ STOP: Invalid Risk Distance**

* **Meaning:** The calculated Stop Loss is **above** the Entry Price.  
* **Why it happens:** Extreme volatility or logic error in custom bounds. The bot cannot go Long if the stop loss is higher than the current price.

## **🧪 Testing**

We use pytest for unit and integration testing. To run the full suite:

python build.py

## **⚠️ Disclaimer**

**THIS SOFTWARE IS FOR EDUCATIONAL PURPOSES ONLY.**

This is not financial advice. The "Closed Loop" logic reduces risk but does not eliminate it. Market conditions can change instantly. The authors are not responsible for any financial losses incurred by using this code.

* **Do not** deploy capital you cannot afford to lose.  
* **Always** verify the numbers manually before entering a trade.  
* **APIs** (YFinance/CCXT) can provide delayed or incorrect data.

## **📂 Structure**

* src/analyzer.py: Historical Volatility & Drift math.  
* src/sniffer.py: Real-time Exchange Fee & Spread detection.  
* src/optimizer.py: The Core Math (Kelly, Closed Loop logic).
