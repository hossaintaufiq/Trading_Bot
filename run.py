"""
One-Click Launcher for Nexus Binance Trading Bot.
Checks dependencies, port availability, automatically opens the web dashboard,
and runs the high-performance Uvicorn server.
"""

import os
import sys
import time
import socket
import webbrowser
import threading


def check_port_available(port: int) -> bool:
    """Check if the target port is free."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) != 0


def find_free_port(start_port: int = 8000) -> int:
    port = start_port
    while port < start_port + 50:
        if check_port_available(port):
            return port
        port += 1
    return start_port


def open_browser_delayed(url: str, delay: float = 1.2):
    """Wait for server to start and then launch browser."""
    time.sleep(delay)
    print(f"\n[+] Launching Dashboard: {url}")
    webbrowser.open(url)


def print_banner(port: int):
    print("=" * 68)
    print(r"""
  _   _ _____ ____ _____ _   _ _   _ _____   ____   ___ _____ 
 | \ | | ____|  _ \_   _| | | | \ | | ____| | __ ) / _ \_   _|
 |  \| |  _| | |_) || | | | | |  \| |  _|   |  _ \| | | || |  
 | |\  | |___|  __/ | | | |_| | |\  | |___  | |_) | |_| || |  
 |_| \_|_____|_|    |_|  \___/|_| \_|_____| |____/ \___/ |_|  
    """)
    print("  🔱 NEPTUNE BOT — QUANTITATIVE DAY TRADING & MULTI-BOT SUITE")
    print("=" * 68)
    print(f"  [>] Local Web UI:    http://localhost:{port}")
    print(f"  [>] Active Fleet:    Neptune Autonomous Multi-Bot Fleet")
    print(f"  [>] Telemetry:       1-Second Live Ticks / 15-Second Radar Scan")
    print(f"  [>] Day Trader Pack: Scanner, Bracket Planner, Time Machine (Monte Carlo)")
    print(f"  [>] Paper Balance:   $10,000.00 Simulated USDT")
    print("=" * 68)
    print("  Press Ctrl+C to pause the bot and shutdown the server.\n")


def main():
    try:
        import fastapi
        import uvicorn
        import ccxt
        import aiohttp
        import pandas
    except ImportError as e:
        print(f"[!] Missing dependency: {e}")
        print("[!] Installing required packages...")
        os.system(f"{sys.executable} -m pip install fastapi uvicorn ccxt aiohttp pandas numpy websockets")

    import uvicorn

    port = find_free_port(8000)
    url = f"http://localhost:{port}"

    # Launch browser in a background thread
    threading.Thread(target=open_browser_delayed, args=(url,), daemon=True).start()

    print_banner(port)

    # Run Uvicorn ASGI server
    uvicorn.run("server:app", host="127.0.0.1", port=port, log_level="info")


if __name__ == "__main__":
    main()
