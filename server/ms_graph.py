import os
import requests
import msal
from datetime import datetime, timedelta, timezone
import json
import tomllib

# https://entra.microsoft.com/#view/Microsoft_AAD_RegisteredApps/AppPermissions.ReactView/objectId/eea65c79-5712-4b11-9722-18bde7b4f5a6/appId/65bfa9ac-2627-4d48-86ef-728bb863e903
# https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps/ApplicationMenuBlade/~/CallAnAPI/appId/65bfa9ac-2627-4d48-86ef-728bb863e903/isMSAApp~/false
# https://github.com/AzureAD/microsoft-authentication-library-for-python

# Note: Outlook credentials stored in 1Password under Outlook.

MS_GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"
SCOPES = ["Calendars.Read"]
TOKEN_CACHE_FILE = "token_cache.json"

def save_token(token):
    with open(TOKEN_CACHE_FILE, "w") as f:
        json.dump(token, f)

def load_token():
    if os.path.exists(TOKEN_CACHE_FILE):
        with open(TOKEN_CACHE_FILE, "r") as f:
            return json.load(f)
    return None

def get_access_token():

    with open("ms-auth.toml", "rb") as f:
        config = tomllib.load(f)

    app_id = config["APPLICATION_ID"]
    tennent_id = config["TENNANT_ID"]
    authority = f'https://login.microsoftonline.com/{tennent_id}'
    app = msal.PublicClientApplication(app_id, authority=authority)

    # Try to load and use refresh token
    token = load_token()
    if token and "refresh_token" in token:
        result = app.acquire_token_by_refresh_token(token["refresh_token"], SCOPES)
        if "access_token" in result:
            save_token(result)
            return result["access_token"]
        # If refresh fails, fall through to device code

    # Device code flow
    flow = app.initiate_device_flow(scopes=SCOPES)
    if "user_code" not in flow:
        raise Exception("Failed to create device flow")
    print(flow["message"])
    result = app.acquire_token_by_device_flow(flow)
    if "access_token" in result:
        save_token(result)
        return result["access_token"]
    else:
        raise Exception(f"Failed to get token: {result.get('error_description')}")


def get_headers():
    token = get_access_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    return headers

def get_events(headers):
    resp = requests.get(
        f"{MS_GRAPH_BASE_URL}/me/events",
        headers=headers
    )
    if resp.status_code == 200:
        return resp.json().get("value", [])
    else:
        raise Exception(f"Error fetching events: {resp.status_code} {resp.text}")


def get_today_events(headers):
    # now = datetime.now(timezone.utc)
    now = datetime.now()
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1) - timedelta(seconds=1)
    url = (
        f"{MS_GRAPH_BASE_URL}/me/calendarView"
        f"?startDateTime={start.isoformat()}"
        f"&endDateTime={end.isoformat()}"
        "&$orderby=start/dateTime"
    )

    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    return resp.json().get("value", [])

def main():

    try:
        headers = get_headers()
        evts = get_today_events(headers)
        print("Today's Events:")
        for event in evts:
            start = event['start']['dateTime']
            subject = event['subject']
            print(f"- {start}: {subject}")
    except Exception as e:
        print(f"Error obtaining access token: {e}")
        return

if __name__ == "__main__":
    main()