"""Fetch Binance P2P USDT/ARS ads and publish a bait-free best price as JSON.

The top ad is often a "cazabobos": a price far better than the rest, usually
with min ≈ max so only one exact amount qualifies. Real ads cluster tightly,
so anything too far from the median of the first page is dropped.

Usage: python3 scripts/p2p.py [out.json]
"""
import json
import statistics
import sys
import time
import urllib.request

URL = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
ROWS = 20
MAX_DEV = 0.005  # ads more than 0.5% away from the median are bait


def fetch(trade_type):
    body = json.dumps({
        "asset": "USDT", "fiat": "ARS", "tradeType": trade_type,
        "page": 1, "rows": ROWS, "payTypes": [], "publisherType": None,
    }).encode()
    req = urllib.request.Request(URL, data=body, headers={
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0",
    })
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)["data"]


def best(trade_type):
    """Best non-bait price; Binance already sorts ads best-first."""
    ads = [{
        "price": float(a["adv"]["price"]),
        "min": float(a["adv"]["minSingleTransAmount"]),
        "max": float(a["adv"]["maxSingleTransAmount"]),
        "user": a["advertiser"]["nickName"],
    } for a in fetch(trade_type)]
    med = statistics.median(a["price"] for a in ads)
    kept = [a for a in ads if abs(a["price"] - med) / med <= MAX_DEV]
    return {
        "price": kept[0]["price"],
        "median": med,
        "discarded": [a for a in ads if a not in kept],
    }


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "p2p.json"
    # tradeType is from the user's side: SELL lists buyers (what you get for USDT)
    sell, buy = best("SELL"), best("BUY")
    data = {
        "time": int(time.time()),
        "bid": sell["price"],
        "ask": buy["price"],
        "bidMedian": sell["median"],
        "askMedian": buy["median"],
        "discarded": {"bid": sell["discarded"], "ask": buy["discarded"]},
    }
    with open(out, "w") as f:
        json.dump(data, f, indent=1)
    print(json.dumps({k: data[k] for k in ("bid", "ask", "bidMedian", "askMedian")}),
          "discarded:", len(sell["discarded"]), len(buy["discarded"]))


if __name__ == "__main__":
    main()
