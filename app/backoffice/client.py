# backoffice/client.py

import requests
import xmltodict
from django.conf import settings


class BackOfficeClient:

    def __init__(self):
        self.base_url = settings.BACKOFFICE_BASE_URL.rstrip("/")
        self.username = settings.BACKOFFICE_USERNAME
        self.password = settings.BACKOFFICE_PASSWORD
        self.token = None

        # Reusable session (better performance)
        self.session = requests.Session()

    # -------------------------------------------------
    # LOGIN
    # -------------------------------------------------
    def login(self):

        url = f"{self.base_url}/auth/Login"

        payload = {
            "username": self.username,
            "password": self.password,
        }

        response = self.session.post(
            url,
            json=payload,
            timeout=10,
        )
        response.raise_for_status()

        data = response.json()

        # Handle multiple token formats
        self.token = (
            data.get("token")
            or data.get("accessToken")
            or data.get("data", {}).get("token")
        )

        if not self.token:
            raise Exception("BackOffice login failed: No token received")

        # Set default headers
        self.session.headers.update({
            "Authorization": f"Bearer {self.token}"
        })

    # -------------------------------------------------
    # GENERIC JSON REQUEST
    # -------------------------------------------------
    def get_json(self, endpoint):

        url = f"{self.base_url}{endpoint}"

        response = self.session.get(url, timeout=15)
        response.raise_for_status()

        data = response.json()

        # Optional: validate success flag
        if isinstance(data, dict) and not data.get("isSuccess", True):
            raise Exception(
                f"BackOffice API error: {data.get('message')}"
            )

        return data

    # -------------------------------------------------
    # GENERIC XML REQUEST
    # -------------------------------------------------
    def get_xml(self, endpoint):

        url = f"{self.base_url}{endpoint}"

        response = self.session.get(url, timeout=15)
        response.raise_for_status()

        try:
            parsed = xmltodict.parse(response.text)
        except Exception as e:
            raise Exception(f"Invalid XML response: {e}")

        return parsed

    # -------------------------------------------------
    # HIGH-LEVEL HELPERS (Optional but Clean)
    # -------------------------------------------------
    def fetch_investors(self):
        return self.get_json("/GetInvestorList").get("data", [])

    def fetch_instruments(self):
        return self.get_json("/GetInstrumentList").get("data", [])

    def fetch_positions(self):
        data = self.get_xml("/ClientsPosition")
        positions = data.get("Positions", {}).get("InsertOne", [])

        if not isinstance(positions, list):
            positions = [positions]

        return positions

    def fetch_limits(self):
        data = self.get_xml("/ClientsLimit")
        limits = data.get("Clients", {}).get("Limits", [])

        if not isinstance(limits, list):
            limits = [limits]

        return limits
