"""Run this ONCE, locally, to produce a reusable OAuth token for the
Gmail API. Not run by the daily GitHub Actions job.

Usage:
    python automation/generate_gmail_token.py path/to/client_secret.json

It opens a browser for you to log into efparnell@gmail.com and
authorize, then prints a JSON blob. Paste that whole blob as the
value of the GMAIL_OAUTH_TOKEN GitHub secret, and paste the *client
secret file's own contents* as GMAIL_OAUTH_CLIENT.
"""

import sys

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]

if __name__ == "__main__":
    client_secret_path = sys.argv[1]
    flow = InstalledAppFlow.from_client_secrets_file(client_secret_path, SCOPES)
    creds = flow.run_local_server(port=0)
    print(creds.to_json())
