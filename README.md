# 👁️ PolyTracker Pro: My Geopolitical Intelligence Command Center

**PolyTracker Pro** is an advanced financial intelligence and analytics suite I developed to monitor and analyze "Whale" activity on Polymarket in real-time. My system focuses on identifying early capital movements in high-sensitivity geopolitical markets, specifically within the Middle East.

---

## 🛠️ Core Capabilities I Developed

* **Stealth Radar Scanner**: I built an asynchronous scanner that monitors hundreds of markets and performs offline keyword filtering (Israel, IDF, Iran, Gaza, etc.) without leaving footprints on the server.
* **Whale Fingerprinting**: I implemented a unique identification system using `trade_hash` to completely prevent data duplication, ensuring 100% statistical accuracy in my database.
* **ROI & P&L Analysis**: I created a financial analysis engine that connects to user profiles to calculate cumulative profitability, trading volume, and classify users as "Smart Money" or "High Risk".
* **Advanced Watchlist**: I designed an active tracking system with real-time alerts for new actions and position changes of targets I’ve flagged.
* **Time-Series Visualization**: I integrated Plotly to generate smooth Spline graphs that visualize the "pulse" of individual whales or compare my entire watchlist on a continuous timeline.

---

## 📊 My Operational Manual

I designed the UI with a Dark-Mode Cyber theme to maintain focus during intelligence gathering:

| Command | Technical Description |
| :--- | :--- |
| **START SCANNER** | Launches my background thread for a recursive scan every 2 minutes. |
| **SHOW TOP WHALES** | Queries my DB for the top 20 most active wallets based on unique transactions. |
| **ROI / P&L** | Executes a deep API call to analyze target's past performance and return on investment. |
| **TRACK/UNTRACK** | I use this to add or remove specific wallets from my prioritized monitoring database. |
| **CHART** | Renders an interactive browser-based graph to analyze activity speed and position accumulation. |

---

## 🏗️ Technical Architecture

* **Language**: Python 3.10+
* **GUI Library**: Tkinter (My Custom Cyber Theme)
* **Database**: SQLite3 (With Integrity Error handling to block duplicate trades)
* **Data Processing**: Pandas (For asynchronous data manipulation)
* **Graphic Engine**: Plotly Express (Rendering Spline Curves)
* **Source File**: `Polymarket_Tracker_IL.py`

---

## ⚙️ Deployment & Distribution

### How I package it into a standalone EXE
I can deploy my system as a single executable for Windows using this command:
```bash
pyinstaller --onefile --noconsole --name PolyTracker_Pro --collect-all pandas --collect-all plotly Polymarket_Tracker_IL.py
