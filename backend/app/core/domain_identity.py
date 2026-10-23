import hashlib

def site_id_for_domain(domain: str) -> str:
    return "site_" + hashlib.sha256(domain.lower().rstrip(".").encode("idna")).hexdigest()
