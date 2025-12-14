import os
import requests
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv
from tabulate import tabulate
import matplotlib.pyplot as plt
import io
import base64
import webbrowser

# Load environment variables
load_dotenv()

API_KEY = os.getenv("ORDERFLOW_API_KEY")
API_URL = os.getenv("ORDERFLOW_API_URL")

# Configuration
SYMBOLS = ["BTCUSDT", "ETHUSDT"]
START_DATE = "2025-12-11"
END_DATE = "2025-12-13"

def fetch_candle_data(symbol, date, resolution):
    """
    Fetches candle data for a specific symbol, date, and resolution.
    """
    if not API_KEY or not API_URL:
        raise ValueError("API credentials not found in .env file (ORDERFLOW_API_KEY, ORDERFLOW_API_URL)")

    # Handle potential trailing slash or pre-included endpoint in API_URL
    base_url = API_URL.rstrip('/')
    if base_url.endswith('/candles'):
        url = base_url
    else:
        url = f"{base_url}/candles"
    params = {
        "symbol": symbol,
        "date": date,
        "resolution": resolution
    }
    headers = {
        "X-API-Key": API_KEY
    }

    try:
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        data = response.json()
        return data.get("data", [])
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data for {symbol} on {date} (Res: {resolution}): {e}")
        return []

def get_date_range(start, end):
    """
    Generates a list of dates between start and end (inclusive).
    """
    start_dt = datetime.strptime(start, "%Y-%m-%d")
    end_dt = datetime.strptime(end, "%Y-%m-%d")
    delta = end_dt - start_dt
    
    dates = []
    for i in range(delta.days + 1):
        day = start_dt + timedelta(days=i)
        dates.append(day.strftime("%Y-%m-%d"))
    return dates

def process_data(symbol, resolution):
    """
    Fetches and processes data for a symbol over the configured date range for a specific resolution.
    """
    print(f"Processing {symbol} at {resolution} resolution...")
    all_candles = []
    dates = get_date_range(START_DATE, END_DATE)

    for date in dates:
        print(f"  Fetching {date}...")
        candles = fetch_candle_data(symbol, date, resolution)
        all_candles.extend(candles)

    if not all_candles:
        print(f"No data found for {symbol} ({resolution}).")
        return None

    df = pd.DataFrame(all_candles)
    
    # Convert time to datetime
    df['datetime'] = pd.to_datetime(df['time'], unit='s')
    df.set_index('datetime', inplace=True)
    df.sort_index(inplace=True)

    # Calculate Rolling Returns
    # Determine window sizes based on resolution
    # Resolution "1m": 1 unit = 1 minute
    # Resolution "1s": 1 unit = 1 second
    
    if resolution == "1m":
        factor = 1
    elif resolution == "1s":
        factor = 60
    else:
        factor = 1 # Default fallback
        
    # 5 minute return
    df['ret_5m'] = df['close'].pct_change(5 * factor)
    # 10 minute return
    df['ret_10m'] = df['close'].pct_change(10 * factor)
    # 15 minute return
    df['ret_15m'] = df['close'].pct_change(15 * factor)

    return df

def analyze_volatility(df, window_col):
    """
    Analyzes volatility events for a specific window return column.
    """
    # Filter for moves > 0.5% (0.005)
    events = df[df[window_col].abs() >= 0.005].copy()
    
    if events.empty:
        return []

    # Bucketing
    # Define buckets: 0.5-0.6, 0.6-0.7, ..., >2.0
    # We use the absolute value for bucketing, but keep track of direction
    
    buckets = [
        (0.005, 0.006, "0.5% - 0.6%"),
        (0.006, 0.007, "0.6% - 0.7%"),
        (0.007, 0.008, "0.7% - 0.8%"),
        (0.008, 0.009, "0.8% - 0.9%"),
        (0.009, 0.010, "0.9% - 1.0%"),
        (0.010, 0.015, "1.0% - 1.5%"),
        (0.015, 0.020, "1.5% - 2.0%"),
        (0.020, float('inf'), "> 2.0%")
    ]

    results = []
    for low, high, label in buckets:
        # Pumps
        pumps = events[(events[window_col] >= low) & (events[window_col] < high)]
        # Dumps (using negative values for comparison, or absolute)
        # return is negative for dump. abs(return) is in range.
        dumps = events[(events[window_col] <= -low) & (events[window_col] > -high)]
        
        results.append({
            "Bucket": label,
            "Pumps": len(pumps),
            "Dumps": len(dumps)
        })

    return results

def generate_plot_base64(results, title):
    """
    Generates a bar chart from results and returns it as a base64 encoded string.
    """
    if not results:
        # Return empty image placeholder or None
        return None

    df_res = pd.DataFrame(results)
    
    # Plotting
    fig, ax = plt.subplots(figsize=(6, 4)) # Smaller size for side-by-side
    
    x = range(len(df_res))
    width = 0.35
    
    ax.bar([i - width/2 for i in x], df_res['Pumps'], width, label='Pumps', color='green')
    ax.bar([i + width/2 for i in x], df_res['Dumps'], width, label='Dumps', color='red')
    
    ax.set_xlabel('Volatility Bucket')
    ax.set_ylabel('Events')
    ax.set_title(title, fontsize=10)
    ax.set_xticks(x)
    ax.set_xticklabels(df_res['Bucket'], rotation=45, ha='right', fontsize=8)
    ax.tick_params(axis='y', labelsize=8)
    ax.legend(fontsize=8)
    
    plt.tight_layout()
    
    # Save to buffer
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    img_str = base64.b64encode(buf.read()).decode('utf-8')
    plt.close(fig)
    
    return img_str

def main():
    if not os.path.exists(".env"):
        print("Warning: .env file not found. Ensure ORDERFLOW_API_KEY and ORDERFLOW_API_URL are set.")
    
    html_sections = []
    
    for symbol in SYMBOLS:
        # Fetch 1m data
        df_1m = process_data(symbol, "1m")
        # Fetch 1s data
        df_1s = process_data(symbol, "1s")
        
        if df_1m is None and df_1s is None:
            continue
            
        print(f"\n{'='*40}")
        print(f"REPORT: {symbol}")
        print(f"{'='*40}")
        
        symbol_html = f"<h2>{symbol}</h2>"
        
        windows = [
            ("5m", "ret_5m", "5 Minute Window"),
            ("10m", "ret_10m", "10 Minute Window"),
            ("15m", "ret_15m", "15 Minute Window")
        ]
        
        for win_id, win_col, win_title in windows:
            symbol_html += f"<h3>{win_title}</h3>"
            symbol_html += "<div class='chart-container'>"
            
            # 1m Analysis
            plot_1m = None
            if df_1m is not None:
                results_1m = analyze_volatility(df_1m, win_col)
                print(f"\n--- {win_title} (1m) ---")
                if results_1m:
                    print(tabulate(results_1m, headers="keys", tablefmt="grid"))
                    plot_1m = generate_plot_base64(results_1m, f"{symbol} - {win_title} (1m Res)")
                else:
                    print("No events found.")
            
            if plot_1m:
                symbol_html += f"<div><h4>1m Resolution</h4><img src='data:image/png;base64,{plot_1m}'></div>"
            else:
                 symbol_html += f"<div><h4>1m Resolution</h4><p>No events found.</p></div>"

            # 1s Analysis
            plot_1s = None
            if df_1s is not None:
                results_1s = analyze_volatility(df_1s, win_col)
                print(f"\n--- {win_title} (1s) ---")
                if results_1s:
                    print(tabulate(results_1s, headers="keys", tablefmt="grid"))
                    plot_1s = generate_plot_base64(results_1s, f"{symbol} - {win_title} (1s Res)")
                else:
                    print("No events found.")
            
            if plot_1s:
                symbol_html += f"<div><h4>1s Resolution</h4><img src='data:image/png;base64,{plot_1s}'></div>"
            else:
                 symbol_html += f"<div><h4>1s Resolution</h4><p>No events found.</p></div>"
                 
            symbol_html += "</div><hr>"

        html_sections.append(symbol_html)

    # Generate full HTML
    html_content = f"""
    <html>
    <head>
        <title>Volatility Report</title>
        <style>
            body {{ font-family: sans-serif; padding: 20px; }}
            .chart-container {{ display: flex; flex-wrap: wrap; gap: 20px; }}
            .chart-container > div {{ flex: 1; min-width: 400px; }}
            img {{ max-width: 100%; border: 1px solid #ddd; }}
            table {{ border-collapse: collapse; width: 100%; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        </style>
    </head>
    <body>
        <h1>Volatility Analysis Report</h1>
        {"".join(html_sections)}
    </body>
    </html>
    """
    
    with open("volatility_report.html", "w") as f:
        f.write(html_content)
    
    print("\nReport saved to volatility_report.html. Opening in browser...")
    webbrowser.open("file://" + os.path.abspath("volatility_report.html"))

if __name__ == "__main__":
    main()
