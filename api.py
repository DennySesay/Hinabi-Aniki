import json
import urllib.request
import urllib.error
from aqt import mw
from typing import Dict, Any

addon_dir = __name__.split('.')[0]

def send_session_payload(payload: Dict[str, Any]) -> bool:
    config = mw.addonManager.getConfig(addon_dir) or {}
    endpoint = config.get("hinabiEndpoint")
    api_key = config.get("apiKey")
    
    if not endpoint or not api_key:
        print("Hinabi add-on: Missing endpoint or API key in config.")
        return False
        
    req = urllib.request.Request(endpoint)
    req.add_header('Content-Type', 'application/json')
    req.add_header('X-API-Key', api_key)
    req.method = 'POST'
    
    data = json.dumps(payload).encode('utf-8')
    try:
        with urllib.request.urlopen(req, data=data, timeout=10) as response:
            return response.status in (200, 201)
    except urllib.error.URLError as e:
        print(f"Hinabi API error: {e}")
        if hasattr(e, 'read'):
            print(f"Hinabi API response body: {e.read().decode('utf-8', errors='replace')}")
        return False

def fetch_languages(endpoint_base: str, api_key: str) -> list:
    """Fetches the user's defined languages from the Hinabi backend."""
    from urllib.parse import urlparse
    
    if not endpoint_base or not api_key:
        return []
        
    try:
        # Construct base URL from the integrations endpoint (e.g. http://localhost:8080/integrations/... -> http://localhost:8080)
        parsed = urlparse(endpoint_base)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        
        # Determine the languages endpoint based on Hinabi's API structure (e.g., /integrations/anki/languages)
        req_url = f"{base_url}/integrations/anki/languages"
        
        req = urllib.request.Request(req_url)
        req.add_header('X-API-Key', api_key)
        req.method = 'GET'
        
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                data = json.loads(response.read().decode('utf-8'))
                return data
            return []
    except Exception as e:
        print(f"Hinabi API error fetching languages: {e}")
        return []
