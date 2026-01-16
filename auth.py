import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

SCOPES = ['https://www.googleapis.com/auth/drive']

def authenticate_google_drive():
    """Authenticates the user and returns the Drive service credentials."""
    import streamlit as st
    
    # 1. Check Streamlit Secrets (Cloud / Deployment)
    # 1. Check Streamlit Secrets (Cloud / Deployment)
    try:
        if "google_drive" in st.secrets:
            # Expected structure in secrets.toml:
            # [google_drive]
            # token = "..."
            # refresh_token = "..."
            # token_uri = "..."
            # client_id = "..."
            # client_secret = "..."
            # scopes = ["..."]
            secret_config = st.secrets["google_drive"]
            creds = Credentials(
                token=secret_config.get("token"),
                refresh_token=secret_config.get("refresh_token"),
                token_uri=secret_config.get("token_uri"),
                client_id=secret_config.get("client_id"),
                client_secret=secret_config.get("client_secret"),
                scopes=secret_config.get("scopes", SCOPES)
            )
            return creds
    except Exception:
        # Secrets not found or malformed, falling back to local auth
        pass

    # 2. Check Local Token File
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    # 3. Interactive Login (Local Only)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                creds = None # Force re-login if refresh fails

        if not creds:
            if not os.path.exists('credentials.json'):
                print("credentials.json not found. Drive features disabled.")
                return None
                
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            # Run local server for auth
            creds = flow.run_local_server(port=0)
        
        # Save the credentials for the next run
        # We only save to file if we are using the file-based flow
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    return creds
