import tkinter as tk
import sqlite3
import requests
from datetime import datetime
import time
import threading
import pandas as pd
import plotly.express as px

tracking_active = False  # FLAG

DB_NAME = 'polytracker_v2.db'  # upgraded DB version to prevent duplicates
API_BASE_URL = "https://gamma-api.polymarket.com/events"
TRADE_API_URL = "https://data-api.polymarket.com/trades"


def get_stealth_markets():
    filter_keywords = ["israel", "gaza", "hamas", "hezbollah", "lebanon", "iran", "netanyahu", "idf", "middle east",
                       "hostages"]
    all_markets = []
    seen_ids = set()  # o(1) fast!
    offset = 0
    headers = {"User-Agent": "Mozilla/5.0"}  # mask for the server that i am not a script

    while tracking_active:
        url = f"{API_BASE_URL}?limit=100&active=true&closed=false&offset={offset}"
        try:
            response = requests.get(url, headers=headers)
            if response.status_code != 200 or not response.json(): break  # make sure the server is return 200 OK

            for event in response.json():
                title = str(event.get('title', '')).lower()
                for market in event.get('markets', []):
                    c_id = market.get('conditionId')
                    q = str(market.get('question', '')).lower()

                    if c_id and c_id not in seen_ids and any(k in (title + " " + q) for k in filter_keywords):
                        all_markets.append({'id': c_id, 'title': market.get('question', '')})
                        seen_ids.add(c_id)

            offset += 100
            if offset >= 1000: break
        except:
            break

    return all_markets


def get_wallets_from_polymarket(condition_id):
    url = f"{TRADE_API_URL}?market={condition_id}&limit=1000"  # widthraw 1000 last trades
    try:
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        if response.status_code != 200: return []

        trades = []
        for trade in response.json():
            w = trade.get('user') or trade.get('proxyWallet')
            t_hash = trade.get('transactionHash') or str(trade.get('uuid', ''))  # get unique trade fingerprint
            if w and t_hash:
                trades.append((w.lower(), t_hash))
        return trades
    except:
        return []


def background_scanner():
    global tracking_active  # reading the current state of the FLAG
    conn = sqlite3.connect(DB_NAME)  # connection to DB
    cursor = conn.cursor()

    # added trade_hash UNIQUE to completely prevent duplicate data trap!
    cursor.execute('''CREATE TABLE IF NOT EXISTS all_bets
                      (
                          trade_hash
                          TEXT
                          UNIQUE,
                          wallet_address
                          TEXT,
                          market_question
                          TEXT,
                          condition_id
                          TEXT,
                          found_at
                          TEXT
                      )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS watchlist
                      (
                          wallet_address
                          TEXT
                          UNIQUE
                      )''')  # create watchlist table

    while tracking_active:
        log_to_screen(f"\n[{datetime.now().strftime('%H:%M:%S')}] Radar Cycle Started...")
        target_markets = get_stealth_markets()

        cursor.execute("SELECT wallet_address FROM watchlist")
        watched_wallets = set([row[0] for row in cursor.fetchall()])  # load tracked wallets fast

        for market in target_markets:
            if not tracking_active: break
            trades = get_wallets_from_polymarket(market['id'])

            for wallet, t_hash in trades:
                try:
                    cursor.execute("INSERT INTO all_bets VALUES (?, ?, ?, ?, ?)",
                                   (t_hash, wallet, market['title'], market['id'], str(datetime.now())))

                    if wallet in watched_wallets:
                        cursor.execute("SELECT COUNT(*) FROM all_bets WHERE wallet_address = ? AND condition_id = ?",
                                       (wallet, market['id']))
                        current_bets = cursor.fetchone()[0]

                        log_to_screen(
                            f"ALERT: [TARGET DETECTED] Watchlist target {wallet[:8]}... moved in {market['title']}")
                        log_to_screen(f"   > Status: Now holds {current_bets} bets in this specific market.")

                except sqlite3.IntegrityError:
                    pass

            conn.commit()  # save on DB
            time.sleep(0.1)  # prevent IP ban from the server

        log_to_screen(f"[{datetime.now().strftime('%H:%M:%S')}] Cycle Complete. Sleeping for 2 mins...")

        for _ in range(120):
            if not tracking_active: break
            time.sleep(1)

    conn.close()
    log_to_screen("Scanner Safely Stopped.")


def start_scanning():
    global tracking_active
    if tracking_active: return
    tracking_active = True
    status_label.config(text="Status: RADAR ACTIVE", fg="#00ff00")
    threading.Thread(target=background_scanner,
                     daemon=True).start()  # daemon is true tells the system to kill the process


def stop_scanning():
    global tracking_active
    tracking_active = False
    status_label.config(text="Status: RADAR STOPPED", fg="red")
    log_to_screen("\n[SYSTEM] Stopping radar... Please wait.")


def log_to_screen(message):
    text_area.insert(tk.END, message + "\n")
    text_area.see(tk.END)


def show_whales():
    text_area.delete('1.0', tk.END)
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT wallet_address, COUNT(*) as bet_count FROM all_bets GROUP BY wallet_address ORDER BY bet_count DESC LIMIT 20")
        whales = cursor.fetchall()
        conn.close()

        text_area.insert(tk.END, "TOP 20 WHALES (LIVE DATABASE SCAN):\n" + "-" * 50 + "\n")
        for w in whales:
            text_area.insert(tk.END, f"> {w[0]}  |  Actions: {w[1]}\n")
    except:
        log_to_screen("Database error.")


def calculate_win_rate():
    raw_input = target_entry.get().strip() 

    target_wallet = raw_input
    if target_wallet.startswith(">"): target_wallet = target_wallet[1:].strip()
    if "|" in target_wallet: target_wallet = target_wallet.split("|")[0].strip()

    if len(target_wallet) < 42:
        log_to_screen("\nError: Wallet address too short. Check your input.")
        return

    log_to_screen(f"\n[ANALYSIS] Deep-Diving into {target_wallet[:10]}...")
    url = f"https://data-api.polymarket.com/profile?user={target_wallet.lower()}"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Origin": "https://polymarket.com",
        "Referer": "https://polymarket.com/"
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)

        if response.status_code == 404:
            alt_url = f"https://data-api.polymarket.com/profile/{target_wallet.lower()}"
            response = requests.get(alt_url, headers=headers, timeout=15)

        if response.status_code == 200:
            data = response.json()

            profit = float(data.get('profit') or 0)
            volume = float(data.get('volume') or 0)
            trades = data.get('tradesCount') or 0

            roi = (profit / volume * 100) if volume > 0 else 0

            log_to_screen(f"   > Success: Volume ${volume:,.2f} | P&L: ${profit:,.2f}")
            log_to_screen(f"   > Calculated ROI: {roi:.2f}% | Trades: {trades}")
            log_to_screen(f"   > Verdict: {'SMART MONEY' if profit > 0 else 'HIGH RISK'}")

        elif response.status_code == 404:
            log_to_screen(
                "   > Error 404: Wallet not found in Data-API. This whale might not have a public profile record yet.")
        else:
            log_to_screen(f"   > Error: Server returned status {response.status_code}.")

    except Exception as e:
        log_to_screen(f"   > System Error: {str(e)}")


def delete_from_watchlist():
    # remove target from watchlist DB and refresh UI instantly
    raw_input = target_entry.get().strip().lower()

    # SMART CLEANING: removes '>' and anything after '|' or spaces
    target_wallet = raw_input
    if target_wallet.startswith(">"): target_wallet = target_wallet[1:].strip()
    if "|" in target_wallet: target_wallet = target_wallet.split("|")[0].strip()
    if " " in target_wallet: target_wallet = target_wallet.split(" ")[0].strip()

    if not target_wallet:
        log_to_screen("\nError: Paste a wallet address to remove.")
        return
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM watchlist WHERE wallet_address = ?", (target_wallet,))
        conn.commit()
        conn.close()
        log_to_screen(f"\n[SYSTEM] Target {target_wallet[:8]}... REMOVED from Watchlist.")

        # REFRESH the view so user sees it is gone
        show_watchlist()
    except Exception as e:
        log_to_screen(f"\nDatabase Error: {e}")


def copy_selection():
    try:
        selected_text = text_area.selection_get()
        root.clipboard_clear()
        root.clipboard_append(selected_text)
        log_to_screen(f"\n[SYSTEM] Copied to clipboard.")
    except tk.TclError:
        log_to_screen("\nError: Please highlight text using your mouse first.")


def paste_wallet():
    try:
        clipboard_text = root.clipboard_get()
        target_entry.delete(0, tk.END)
        target_entry.insert(0, clipboard_text)
    except tk.TclError:
        log_to_screen("\nError: Clipboard is empty or doesn't contain text.")


def analyze_target():
    target_wallet = target_entry.get().strip().lower()
    if not target_wallet:
        log_to_screen("\nError: Please paste a wallet address in the Target box.")
        return

    text_area.delete('1.0', tk.END)
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT market_question, COUNT(*) as bet_count FROM all_bets WHERE wallet_address = ? GROUP BY market_question ORDER BY bet_count DESC",
            (target_wallet,))
        portfolio = cursor.fetchall()
        conn.close()

        if not portfolio:
            text_area.insert(tk.END, f"No records found for wallet: {target_wallet}\n")
            return

        text_area.insert(tk.END, f"DEEP DIVE PORTFOLIO: {target_wallet[:8]}...\n")
        text_area.insert(tk.END, "=" * 60 + "\n")
        for item in portfolio:
            text_area.insert(tk.END, f"- {item[0]}\n   (Total bets on this: {item[1]})\n\n")

    except Exception as e:
        log_to_screen(f"\nError: {e}")


def show_graph():
    target_wallet = target_entry.get().strip().lower()
    if not target_wallet:
        log_to_screen("\nError: Please paste a wallet address in the Target box.")
        return

    try:
        conn = sqlite3.connect(DB_NAME)
        query = f"SELECT found_at FROM all_bets WHERE wallet_address = '{target_wallet}' ORDER BY found_at ASC"
        df = pd.read_sql_query(query, conn)
        conn.close()

        if df.empty:
            log_to_screen("\nNo data to graph.")
            return

        log_to_screen("\nGenerating Dark Mode Spline Line Chart in browser...")
        df['found_at'] = pd.to_datetime(df['found_at'])
        df['cumulative_bets'] = range(1, len(df) + 1)
        fig = px.line(df, x='found_at', y='cumulative_bets', title=f'Activity: {target_wallet[:8]}...',
                      template='plotly_dark', line_shape='spline')
        fig.show()
    except Exception as e:
        log_to_screen(f"\nGraph Error: {e}")


def show_watchlist_graph():
    try:
        conn = sqlite3.connect(DB_NAME)
        query = "SELECT wallet_address, found_at FROM all_bets WHERE wallet_address IN (SELECT wallet_address FROM watchlist) ORDER BY found_at ASC"
        df = pd.read_sql_query(query, conn)
        conn.close()

        if df.empty:
            log_to_screen("\nNo watchlist data to graph.")
            return

        log_to_screen("\nGenerating Watchlist Activity Graph in browser...")
        df['found_at'] = pd.to_datetime(df['found_at'])
        df['cumulative'] = df.groupby('wallet_address').cumcount() + 1
        fig = px.line(df, x='found_at', y='cumulative', color='wallet_address', title='Watchlist Whales Comparison',
                      template='plotly_dark', line_shape='spline')
        fig.show()
    except Exception as e:
        log_to_screen(f"\nGraph Error: {e}")


def add_to_watchlist():
    target_wallet = target_entry.get().strip().lower()
    if not target_wallet:
        log_to_screen("\nError: Paste a wallet address in the Target box to track.")
        return
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO watchlist VALUES (?)", (target_wallet,))
        conn.commit()
        conn.close()
        log_to_screen(f"\n[SYSTEM] Target {target_wallet[:8]}... added to WATCHLIST.")
    except Exception as e:
        log_to_screen(f"\nDatabase Error: {e}")


def show_watchlist():
    text_area.delete('1.0', tk.END)
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT wallet_address FROM watchlist")
        targets = cursor.fetchall()
        conn.close()
        text_area.insert(tk.END, "ACTIVE WATCHLIST TARGETS:\n" + "=" * 50 + "\n")
        if not targets:
            text_area.insert(tk.END, "Watchlist is currently empty.\n")
        for t in targets:
            # check if we have action counts in DB for them
            conn = sqlite3.connect(DB_NAME)
            c2 = conn.cursor()
            c2.execute("SELECT COUNT(*) FROM all_bets WHERE wallet_address = ?", (t[0],))
            count = c2.fetchone()[0]
            conn.close()
            text_area.insert(tk.END, f"> {t[0]} | actions: {count}\n")  # matches
    except Exception as e:
        log_to_screen(f"Database error: {e}")


root = tk.Tk()
root.title("PolyTracker Pro - Intelligence Command Center")
root.geometry("1250x700")
root.configure(bg="#0f0f0f")

tk.Label(root, text="PolyTracker Control Center", bg="#0f0f0f", fg="#00ffcc", font=("Courier New", 18, "bold")).pack(
    pady=10)
status_label = tk.Label(root, text="Status: RADAR STOPPED", bg="#0f0f0f", fg="red", font=("Arial", 12, "bold"))
status_label.pack()

button_frame = tk.Frame(root, bg="#0f0f0f")
button_frame.pack(pady=10)
tk.Button(button_frame, text="START SCANNER", command=start_scanning, bg="#1e5128", fg="white",
          font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=10)
tk.Button(button_frame, text="STOP SCANNER", command=stop_scanning, bg="#801313", fg="white",
          font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=10)
tk.Button(button_frame, text="SHOW TOP WHALES", command=show_whales, bg="#2b2b2b", fg="white",
          font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=10)
tk.Button(button_frame, text="SHOW WATCHLIST", command=show_watchlist, bg="#2b2b2b", fg="white",
          font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=10)

target_frame = tk.Frame(root, bg="#1a1a1a", bd=2, relief="groove")
target_frame.pack(pady=10, padx=20, fill="x")

tk.Label(target_frame, text="Target Wallet:", bg="#1a1a1a", fg="#ffaa00", font=("Arial", 10, "bold")).pack(side=tk.LEFT,
                                                                                                           padx=5,
                                                                                                           pady=10)
target_entry = tk.Entry(target_frame, bg="#2b2b2b", fg="#00ff00", font=("Consolas", 10), width=40)
target_entry.pack(side=tk.LEFT, padx=5)

tk.Button(target_frame, text="COPY", command=copy_selection, bg="#5c4d0c", fg="white", font=("Arial", 9, "bold")).pack(
    side=tk.LEFT, padx=2)
tk.Button(target_frame, text="PASTE", command=paste_wallet, bg="#005f73", fg="white", font=("Arial", 9, "bold")).pack(
    side=tk.LEFT, padx=2)
tk.Button(target_frame, text="ANALYZE", command=analyze_target, bg="#4a4a4a", fg="white",
          font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=2)
tk.Button(target_frame, text="ROI/P&L", command=calculate_win_rate, bg="#1e5128", fg="white",
          font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=2)
tk.Button(target_frame, text="CHART", command=show_graph, bg="#4a4a4a", fg="white", font=("Arial", 9, "bold")).pack(
    side=tk.LEFT, padx=2)
tk.Button(target_frame, text="UNTRACK", command=delete_from_watchlist, bg="#801313", fg="white",
          font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=2)
tk.Button(target_frame, text="TRACK", command=add_to_watchlist, bg="#4a0c5c", fg="white",
          font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=2)

text_area = tk.Text(root, bg="#000000", fg="#00ff00", font=("Consolas", 11), height=20, width=130, relief="flat")
text_area.pack(pady=10)
log_to_screen("System Ready. Waiting for commands...")

root.mainloop()
