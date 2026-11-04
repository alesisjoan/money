"""Track the price of one Sky flight and keep a history of every change.

Watches the fastest 09:00 AEP→CUZ departure on 2027-01-28, cheapest fare
(Basic), as sold on skyairline.com/es/argentina (ARS, taxes included).
Uses the same search API the Sky site calls; the subscription key ships in
Sky's public frontend.

Usage: python3 scripts/sky.py out.json [previous.json]
"""
import json
import os
import sys
import time
import urllib.request

ORIGIN, DEST, DATE, DEP_TIME = "AEP", "CUZ", "2027-01-28", "09:00"
URL = "https://api.skyairline.com/farequoting/v1/search/flight?stage=IS"
KEY = "4c998b33d2aa4e8aba0f9a63d4c04d7d"
MAX_HISTORY = 2000


def search():
    body = json.dumps({
        "cabinClass": "Economy", "currency": None, "awardBooking": False,
        "pointOfSale": "AR", "searchType": "BRANDED",
        "itineraryParts": [{
            "origin": {"code": ORIGIN, "useNearbyLocations": False},
            "destination": {"code": DEST, "useNearbyLocations": False},
            "departureDate": {"date": DATE},
            "selectedOfferRef": None, "plusMinusDays": None,
        }],
        "passengers": {"ADT": 1, "CHD": 0, "INF": 0, "PET": 0},
        "trendIndicator": None, "preferredOperatingCarrier": None,
    }).encode()
    req = urllib.request.Request(URL, data=body, headers={
        "Content-Type": "application/json",
        "homemarket": "AR",
        "channel": "WEB",
        "ocp-apim-subscription-key": KEY,
        "Origin": "https://initial-sale.skyairline.com",
        "Referer": "https://initial-sale.skyairline.com/",
        "User-Agent": "Mozilla/5.0",
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)["itineraryParts"][0]


def pick(itineraries):
    """Fastest itinerary leaving at DEP_TIME; None if it's gone or sold out."""
    at_time = [i for i in itineraries
               if i["segments"][0]["departure"][11:16] == DEP_TIME]
    if not at_time:
        return None
    it = min(at_time, key=lambda i: i["totalDuration"])
    fares = [f for f in it["fares"] if f.get("status") and f.get("total")]
    if not fares:
        return None
    f = min(fares, key=lambda f: f["total"]["amount"])
    pax = f["priceByPassengerTypes"][0]
    seg = it["segments"]
    return {
        "price": f["total"]["amount"],
        "fare": pax["fare"]["amount"],
        "taxes": pax["taxes"]["amount"],
        "currency": f["total"]["currency"],
        "brand": f["brandId"],
        "seats": it["seatsRemaining"]["count"],
        "departure": seg[0]["departure"],
        "arrival": seg[-1]["arrival"],
        "duration": it["totalDuration"],
        "flights": [s["flight"]["airlineCode"] + str(s["flight"]["flightNumber"]) for s in seg],
    }


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "sky.json"
    prev_path = sys.argv[2] if len(sys.argv) > 2 else None
    history = []
    if prev_path and os.path.exists(prev_path):
        try:
            with open(prev_path) as f:
                history = json.load(f).get("history", [])
        except ValueError:
            pass

    now = int(time.time())
    cur = pick(search())
    price = cur["price"] if cur else None
    # store a point only when the price changes (null = not available)
    if not history or history[-1]["p"] != price:
        history.append({"t": now, "p": price})
    history = history[-MAX_HISTORY:]

    data = {
        "time": now,
        "route": f"{ORIGIN}-{DEST}",
        "date": DATE,
        "url": ("https://initial-sale.skyairline.com/es/argentina?origin=" + ORIGIN
                + "&destination=" + DEST + "&departureDate=" + DATE
                + "&arrivalDate=" + DATE + "&flightType=OW&ADT=1"),
        "current": cur,
        "history": history,
    }
    with open(out, "w") as f:
        json.dump(data, f, indent=1)
    print(json.dumps(cur), "history:", len(history))


if __name__ == "__main__":
    main()
