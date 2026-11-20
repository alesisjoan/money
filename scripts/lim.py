"""Track the cheapest DIRECT BUE→LIM flight on 2027-01-28 on Sky and JetSMART.

Any departure time, one adult, ARS, taxes included. Keeps a price history per
airline (a point only when the price changes, null = no direct flight).

- Sky: same fare-search API as scripts/sky.py (plain HTTP).
- JetSMART: booking.jetsmart.com sits behind a queue-it + Fastly challenge,
  so a headless Chromium opens the search once and then reads
  api/Flight/FlightPageData?withTax=true from inside the page.

If one airline fails, its last known data is kept and the error is recorded.

Usage: python3 scripts/lim.py out.json [previous.json]
"""
import json
import os
import sys
import time

from sky import search as sky_search

ORIGIN, DEST, DATE = "BUE", "LIM", "2027-01-28"
MAX_HISTORY = 2000

SKY_URL = ("https://initial-sale.skyairline.com/es/argentina?origin=" + ORIGIN
           + "&destination=" + DEST + "&departureDate=" + DATE
           + "&arrivalDate=" + DATE + "&flightType=OW&ADT=1")
JS_URL = ("https://booking.jetsmart.com/Flight/InternalSelect?o1=" + ORIGIN
          + "&d1=" + DEST + "&dd1=" + DATE
          + "&ADT=1&CHD=0&inl=0&r=false&s=true&mon=true&cur=ARS&culture=es-AR&rc=AR")


def sky():
    """Cheapest direct Sky fare in ARS, plus the same flight+fare bought in USD."""
    best = sky_direct()
    if best:
        usd = sky_direct("USD", best["flight"], best["brand"])
        best["usd"] = usd["price"] if usd else None
    return best


def sky_direct(currency=None, flight=None, brand=None):
    """Cheapest fare among Sky's single-segment itineraries (optionally one
    flight and brand); None if none."""
    best = None
    for it in sky_search(ORIGIN, DEST, DATE, currency):
        seg = it["segments"]
        if len(seg) != 1:
            continue
        number = seg[0]["flight"]["airlineCode"] + str(seg[0]["flight"]["flightNumber"])
        if flight and number != flight:
            continue
        for f in it["fares"]:
            if not (f.get("status") and f.get("total")):
                continue
            label = "BASIC" if f["brandId"] == "ZO" else f["brandId"]
            if brand and label != brand:
                continue
            if best and f["total"]["amount"] >= best["price"]:
                continue
            pax = f["priceByPassengerTypes"][0]
            best = {
                "price": f["total"]["amount"],
                "fare": pax["fare"]["amount"],
                "taxes": pax["taxes"]["amount"],
                "brand": label,
                "seats": it["seatsRemaining"]["count"],
                "from": seg[0]["origin"],
                "departure": seg[0]["departure"][:16],
                "arrival": seg[0]["arrival"][:16],
                "duration": it["totalDuration"],
                "flight": number,
            }
    return best


def jetsmart():
    """Cheapest JetSMART non-connecting flight (taxes included); None if none."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        # since 2026-11-19 the challenge shows a CAPTCHA to the headless shell
        # and to anything with navigator.webdriver set: use full Chromium
        # (new headless mode) without the automation flag
        browser = p.chromium.launch(
            channel="chromium",
            args=["--disable-blink-features=AutomationControlled"])
        page = browser.new_page(locale="es-AR", user_agent=(
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"))
        page.goto(JS_URL, timeout=90000)
        # queue-it / Fastly challenge redirects to the results page when passed
        page.wait_for_url("**/V2/Flight**", timeout=90000)
        # the search lives in the session: re-run it per currency, then read it.
        # USD is a real USD quote (cheaper than converting the ARS price,
        # which carries Argentine taxes on foreign currency).
        ars, usd = page.evaluate("""async (base) => {
            const get = async (cur) => {
                await fetch(base.replace('cur=ARS', 'cur=' + cur));
                const r = await fetch('/api/Flight/FlightPageData?withTax=true');
                if (!r.ok) throw new Error('FlightPageData ' + cur + ' ' + r.status);
                return r.json();
            };
            return [await get('ARS'), await get('USD')];
        }""", JS_URL)
        browser.close()

    def direct(data):
        return [f for f in data["Outbound"]["Flights"]
                if not f["IsConnected"] and len(f["Legs"]) == 1]

    flights = direct(ars)
    if not flights:
        return None
    f = min(flights, key=lambda f: f["BaseNormalPrice"])
    same = [u["BaseNormalPrice"] for u in direct(usd)
            if u["FlightNumber"] == f["FlightNumber"] and u["DepartureTime"] == f["DepartureTime"]]
    return {
        "price": round(f["BaseNormalPrice"], 2),
        "usd": round(min(same), 2) if same else None,
        "club": round(f["BaseDcPrice"], 2),
        "from": f["OriginIata"],
        "departure": f["DepartureTime"][:16].replace(" ", "T"),
        "arrival": f["ArrivalTime"][:16].replace(" ", "T"),
        "duration": f["Duration"]["Hours"] * 60 + f["Duration"]["Minutes"],
        "flight": "JA" + f["FlightNumber"].strip(),
        "count": len(flights),
    }


def update(prev, fetch, url, now):
    """Run one airline's fetch and fold the result into its previous state."""
    state = dict(prev or {}, url=url)
    history = state.get("history", [])
    try:
        cur = fetch()
    except Exception as e:  # keep last data, surface the error
        state["error"] = f"{type(e).__name__}: {e}"[:300]
        print(url, "ERROR", state["error"], file=sys.stderr)
        return state
    price = cur["price"] if cur else None
    if not history or history[-1]["p"] != price:
        history.append({"t": now, "p": price})
    state.update(time=now, current=cur, history=history[-MAX_HISTORY:], error=None)
    print(url[:40], json.dumps(cur))
    return state


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "lim.json"
    prev_path = sys.argv[2] if len(sys.argv) > 2 else None
    prev = {}
    if prev_path and os.path.exists(prev_path):
        try:
            with open(prev_path) as f:
                prev = json.load(f)
        except ValueError:
            pass

    now = int(time.time())
    data = {
        "time": now,
        "route": f"{ORIGIN}-{DEST}",
        "date": DATE,
        "sky": update(prev.get("sky"), sky, SKY_URL, now),
        "jetsmart": update(prev.get("jetsmart"), jetsmart, JS_URL, now),
    }
    with open(out, "w") as f:
        json.dump(data, f, indent=1)
    # fail the run only if both airlines failed
    if data["sky"].get("error") and data["jetsmart"].get("error"):
        sys.exit(1)


if __name__ == "__main__":
    main()
