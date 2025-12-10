import socket
from abc import ABC

import requests
from settings import Settings

# Map hostnames to the same IP
DOMAIN_TO_IP = {
    "https://traction-tenant-proxy-test.apps.silver.devops.gov.bc.ca": "142.34.194.118",
}

# Save the original function
_original_getaddrinfo = socket.getaddrinfo

# Patch socket.getaddrinfo
def fake_getaddrinfo(host, port, *args, **kwargs):
    if host in DOMAIN_TO_IP:
        ip = DOMAIN_TO_IP[host]
        # Return a valid getaddrinfo tuple
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, '', (ip, port))]
    return _original_getaddrinfo(host, port, *args, **kwargs)

socket.getaddrinfo = fake_getaddrinfo


class BaseAgent(ABC):
    def __init__(self):
        self.agent_url = Settings.ISSUER_URL
        self.headers = Settings.ISSUER_HEADERS | {"Content-Type": "application/json"}
        self.session = requests.Session()

    def get_invite(self):                    
        r = self.session.post(
            f"{self.agent_url}/out-of-band/create-invitation?auto_accept=true",
            json={"handshake_protocols": Settings.HANDSHAKE_PROTOCOLS},
            headers=self.headers,
        )
        invitation = r.json()
        
        r = self.session.get(
            f"{self.agent_url}/connections",
            params={"invitation_msg_id": invitation["invi_msg_id"]},
            headers=self.headers,
        )
        connection = r.json()["results"][0]
        
        return {
            "invitation_url": invitation["invitation_url"],
            "connection_id": connection["connection_id"],
        }

    def is_up(self):
        try:
            r = self.session.get(
                f"{self.agent_url}/status",
                headers=self.headers,
            )
            if r.status_code != 200:
                raise Exception(r.content)

            r.json()
        except Exception:
            return False

        return True

    def send_message(self, connection_id, msg):
        self.session.post(
            f"{self.agent_url}/connections/{connection_id}/send-message",
            json={"content": msg},
            headers=self.headers,
        )
