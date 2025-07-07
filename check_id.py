# check_id.py
import os
import json
import requests
import datetime
from dotenv import load_dotenv
from requests.utils import cookiejar_from_dict

def main():
    load_dotenv()  # ← loads OPEN_TABLE_TOKEN and OPEN_TABLE_COOKIE from .env

    # ─── CONFIGURATION: 
    # 1) Put the ID you think is Sabayon’s into restaurant_id
    # 2) Copy the exact Referer string from your browser’s address bar
    #    when you load Sabayon’s page (including any query params).
    #    For example: 
    #      https://www.opentable.com/r/sabayon?covers=2&dateTime=2025-06-03T19%3A00
    restaurant_id = 1367977
    referer_url   = "https://www.opentable.ca/r/sabayon-montreal?corrid=1afcc7c8-7de6-42d4-b9f4-84b5e78825dd&p=2&sd=2025-07-17T19%3A00%3A00"
    # ────────────────────────────────────────────────────────────────────────────

    # Use any date/time for the lookup; even if it's before/noon, we’ll still get metadata back.
    today_str  = datetime.date.today().isoformat()  # e.g. "2025-06-04"
    test_time  = "12:00"  # arbitrary
    party_size = 4        # arbitrary

    token      = os.environ.get("OPEN_TABLE_TOKEN")
    raw_cookie = os.environ.get("OPEN_TABLE_COOKIE")

    if not token:
        print("ERROR: OPEN_TABLE_TOKEN not found in .env")
        return
    if not raw_cookie:
        print("ERROR: OPEN_TABLE_COOKIE not found in .env")
        return

    # ─── Parse raw_cookie into a dict, then attach to a Session ───
    cookie_dict = {}
    for pair in raw_cookie.split(";"):
        pair = pair.strip()
        if not pair or "=" not in pair:
            continue
        key, val = pair.split("=", 1)
        cookie_dict[key] = val

    session = requests.Session()
    session.cookies = cookiejar_from_dict(cookie_dict)
    # ─────────────────────────────────────────────────────────────────

    headers = {
        "Content-Type": "application/json",
        "Accept":       "application/json, text/plain, */*",
        "Origin":       "https://www.opentable.com",
        "Referer":      referer_url,
        "User-Agent":   "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/114.0.0.0 Safari/537.36",
        "x-csrf-token": token
    }

    payload = {
        "operationName": "RestaurantsAvailability",
        "variables": {
            "restaurantIds": [ restaurant_id ],
            "date":          today_str,
            "time":          test_time,
            "partySize":     party_size,
            "databaseRegion":"NA"
        },
        "extensions": {
            "persistedQuery": {
                "sha256Hash": "e6b87021ed6e865a7778aa39d35d09864c1be29c683c707602dd3de43c854d86"
            }
        }
    }

    url = "https://www.opentable.com/dapi/fe/gql?optype=query&opname=RestaurantsAvailability"

    print(f"→ Sending GraphQL availability request for restaurant ID {restaurant_id} …")
    try:
        # ─── Add a 15‐second timeout so we don’t hang forever ─────────────────────
        resp = session.post(url, headers=headers, json=payload, timeout=15)
        print("→ Received HTTP response!")  # This confirms we got _some_ response within 15 s
    except requests.exceptions.Timeout:
        print("REQUEST TIMEOUT: Server took longer than 15 seconds to respond.")
        return
    except requests.exceptions.RequestException as e:
        print("REQUEST ERROR:", e)
        return

    # At this point, we _did_ get a response (since no exception was raised).
    # Print out status code so we know what came back:
    print(f"→ HTTP {resp.status_code} {resp.reason}")

    if resp.status_code != 200:
        print("Response Headers:", resp.headers)
        print("Response Text:", resp.text)
        return

    # Now parse the JSON
    try:
        data = resp.json()
        print("→ Successfully parsed JSON!")  # debug confirmation
    except json.JSONDecodeError:
        print("ERROR: Response was not valid JSON:")
        print(resp.text)
        return

    availability_list = data.get("data", {}).get("availability", [])
    if not availability_list:
        print("No 'availability' node found. Possibly invalid ID or blocked.")
        print(json.dumps(data, indent=2))
        return

    node = availability_list[0]

    # 1) Print the entire availability node so you can inspect it
    print("\n── Full availability node ─────────────────────────────────")
    print(json.dumps(node, indent=2))

    # 2) Extract and print the restaurant’s display name
    name = None
    if isinstance(node.get("restaurant"), dict):
        name = node["restaurant"].get("name") or node["restaurant"].get("displayName")
    if not name:
        name = node.get("restaurantName") or node.get("name")

    if name:
        print(f"\n✅ Restaurant name (ID {restaurant_id}) → {name}\n")
    else:
        print("\n⚠️ Could not find a 'name' field—inspect the JSON above.\n")


if __name__ == "__main__":
    main()