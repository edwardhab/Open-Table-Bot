import os
import json
import time
import datetime
import requests
from dotenv import load_dotenv

class OpenTable:
    def __init__(self, open_table_token, restaurant_id, date, time_str, party_size,
                 firstName, lastName, email, phone_no):
        self.open_table_token = open_table_token
        self.restaurant_id    = restaurant_id
        self.date             = date       # e.g. "2025-06-03"
        self.time             = time_str   # e.g. "19:00"
        self.party_size       = party_size
        self.firstName        = firstName
        self.lastName         = lastName
        self.email            = email
        self.phone_no         = phone_no
        self.url_head         = "https://www.opentable.com/dapi"
        self.headers = {
            "content-type": "application/json",
            "origin":       "https://www.opentable.com",
            "user-agent":   "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/114.0.0.0 Safari/537.36",
            "x-csrf-token": self.open_table_token
        }

    def find_restaurant_times(self):
        url = f"{self.url_head}/fe/gql?optype=query&opname=RestaurantsAvailability"
        payload = json.dumps({
            "operationName": "RestaurantsAvailability",
            "variables": {
                "restaurantIds": [ self.restaurant_id ],
                "date":          self.date,
                "time":          self.time,
                "partySize":     self.party_size,
                "databaseRegion":"NA"
            },
            "extensions": {
                "persistedQuery": {
                    "sha256Hash": "e6b87021ed6e865a7778aa39d35d09864c1be29c683c707602dd3de43c854d86"
                }
            }
        })
        response = requests.post(url, headers=self.headers, data=payload)
        return response.json()

    def find_slot(self, availability_json):
        """
        Returns (slotAvailabilityToken, slotHash) for the closest available slot,
        or (None, None) if no slots are available.
        """
        slots = availability_json["data"]["availability"][0]["availabilityDays"][0]["slots"]
        available_slots = [s for s in slots if s["isAvailable"]]
        if not available_slots:
            return None, None

        # Choose the slot with the smallest offset from the requested time
        chosen = min(available_slots, key=lambda x: abs(x["timeOffsetMinutes"]))
        return chosen["slotAvailabilityToken"], chosen["slotHash"]

    def booking_reservation(self, slot_token, slot_hash):
        url = f"{self.url_head}/booking/make-reservation"
        payload = json.dumps({
            "restaurantId":          self.restaurant_id,
            "slotAvailabilityToken": slot_token,
            "slotHash":              slot_hash,
            "isModify":              False,
            "reservationDateTime":   f"{self.date}T{self.time}",
            "partySize":             self.party_size,
            "firstName":             self.firstName,
            "lastName":              self.lastName,
            "email":                 self.email,
            "country":               "CA",
            "reservationType":       "Standard",
            "reservationAttribute":  "default",
            "additionalServiceFees": [],
            "tipAmount":             0,
            "tipPercent":            0,
            "pointsType":            "Standard",
            "points":                100,
            "diningAreaId":          1,
            "fbp":                   "fb.1.1685721920137.7677309689611231",
            "phoneNumber":           self.phone_no,
            "phoneNumberCountryId":  "CA",
            "optInEmailRestaurant":  False
        })
        resp = requests.post(url, headers=self.headers, data=payload)
        print("Booking response:", resp.text)


if __name__ == "__main__":
    load_dotenv()

    # === CONFIGURATION: Adjust these values to match your reservation ===
    restaurant_id    = 1367977               # ← Sabayon’s OpenTable ID
    desired_date     = "2025-07-17"       # ← The date you want to reserve (YYYY-MM-DD)
    desired_time     = "19:00"            # ← The time you want (HH:MM, 24‑hour)
    party_size       = 4                  # ← Number of people in your party

    open_table_token = os.environ["OPEN_TABLE_TOKEN"]
    firstName        = os.environ["FIRST_NAME"]
    lastName         = os.environ["LAST_NAME"]
    email            = os.environ["EMAIL"]
    phone_no         = os.environ["PHONE_NO"]
    # ===================================================================

    bot = OpenTable(
        open_table_token=open_table_token,
        restaurant_id=restaurant_id,
        date=desired_date,
        time_str=desired_time,
        party_size=party_size,
        firstName=firstName,
        lastName=lastName,
        email=email,
        phone_no=phone_no
    )

    # --- Polling setup: start at exactly noon local time ---
    poll_start = datetime.datetime(2025, 6, 3, 12, 0, 0)   # 2025‑06‑03 12:00:00
    poll_interval_seconds = 1  # check every 1 second

    print(f"Waiting until {poll_start.time()} to start polling...")
    while datetime.datetime.now() < poll_start:
        # Sleep in short bursts so we wake up right at noon
        time_to_start = (poll_start - datetime.datetime.now()).total_seconds()
        if time_to_start > 0.5:
            time.sleep(0.5)
        else:
            break

    print("🔍 Starting to poll for available slots…")
    while True:
        availability_response = bot.find_restaurant_times()
        slot_token, slot_hash = bot.find_slot(availability_response)

        if slot_token and slot_hash:
            print("🎉 Slot found! Attempting to book…")
            bot.booking_reservation(slot_token, slot_hash)
            break

        # If no slot yet, wait a few seconds and try again
        time.sleep(poll_interval_seconds)
