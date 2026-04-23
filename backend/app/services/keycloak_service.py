import requests
import os
import jwt as pyjwt
from jwt import PyJWKClient

def get_keycloak_base_url():
    return f"{os.getenv('KEYCLOAK_URL')}/realms/{os.getenv('KEYCLOAK_REALM')}/protocol/openid-connect"

def get_keycloak_headers():
    host = os.getenv('KEYCLOAK_HOST', '')
    if host:
        return {'Host': host}
    return {}

def get_token(username, password):
    try:
        headers = get_keycloak_headers()
        headers['Content-Type'] = 'application/x-www-form-urlencoded'
        
        response = requests.post(
            f"{get_keycloak_base_url()}/token",
            headers=headers,
            data={
                'client_id': os.getenv('KEYCLOAK_CLIENT_ID'),
                'client_secret': os.getenv('KEYCLOAK_CLIENT_SECRET'),
                'username': username,
                'password': password,
                'grant_type': 'password',
                'scope': 'openid profile email'
            },
            timeout=10
        )
        print(f"[DEBUG] Keycloak token status: {response.status_code}")
        if response.status_code == 200:
            return response.json()
        print(f"[ERROR] Keycloak login failed: {response.text}")
        return None
    except Exception as e:
        print(f"[ERROR] get_token: {str(e)}")
        return None


def verify_token(token):
    try:
        # URL des clés publiques Keycloak
        certs_url = (
            f"{os.getenv('KEYCLOAK_URL')}/realms/{os.getenv('KEYCLOAK_REALM')}"
            f"/protocol/openid-connect/certs"
        )

        headers = get_keycloak_headers()

        # Récupérer les clés JWKS manuellement avec nos headers
        jwks_response = requests.get(certs_url, headers=headers, timeout=100)
        print(f"[DEBUG] JWKS status: {jwks_response.status_code}")

        if jwks_response.status_code != 200:
            print(f"[ERROR] Cannot fetch JWKS: {jwks_response.text}")
            return None

        jwks_data = jwks_response.json()

        # Décoder le header du token pour trouver le kid
        unverified_header = pyjwt.get_unverified_header(token)
        kid = unverified_header.get('kid')
        print(f"[DEBUG] Token kid: {kid}")

        # Trouver la bonne clé dans le JWKS
        from jwt.algorithms import RSAAlgorithm
        rsa_key = None
        for key in jwks_data.get('keys', []):
            if key.get('kid') == kid:
                rsa_key = RSAAlgorithm.from_jwk(key)
                break

        if not rsa_key:
            # Si pas de kid match, prendre la première clé RSA
            for key in jwks_data.get('keys', []):
                if key.get('kty') == 'RSA':
                    rsa_key = RSAAlgorithm.from_jwk(key)
                    break

        if not rsa_key:
            print("[ERROR] No RSA key found in JWKS")
            return None

        # Décoder le token avec la clé publique
        payload = pyjwt.decode(
            token,
            rsa_key,
            algorithms=["RS256"],
            options={"verify_aud": False}
        )

        print(f"[DEBUG] Token valid for user: {payload.get('preferred_username')}")

        return {
            'sub': payload.get('sub'),
            'email': payload.get('email', ''),
            'name': payload.get('name', payload.get('preferred_username', '')),
            'preferred_username': payload.get('preferred_username', ''),
            'roles': payload.get('realm_access', {}).get('roles', [])
        }

    except pyjwt.ExpiredSignatureError:
        print("[ERROR] Token expiré")
        return None
    except pyjwt.InvalidTokenError as e:
        print(f"[ERROR] Token invalide: {str(e)}")
        return None
    except Exception as e:
        print(f"[ERROR] verify_token: {str(e)}")
        return None


def refresh_token(refresh_tok):
    try:
        headers = get_keycloak_headers()
        headers['Content-Type'] = 'application/x-www-form-urlencoded'
        
        response = requests.post(
            f"{get_keycloak_base_url()}/token",
            headers=headers,
            data={
                'client_id': os.getenv('KEYCLOAK_CLIENT_ID'),
                'client_secret': os.getenv('KEYCLOAK_CLIENT_SECRET'),
                'refresh_token': refresh_tok,
                'grant_type': 'refresh_token'
            },
            timeout=10
        )
        if response.status_code == 200:
            return response.json()
        print(f"[ERROR] Refresh failed: {response.text}")
        return None
    except Exception as e:
        print(f"[ERROR] refresh_token: {str(e)}")
        return None


def logout(refresh_tok):
    try:
        headers = get_keycloak_headers()
        headers['Content-Type'] = 'application/x-www-form-urlencoded'
        
        response = requests.post(
            f"{get_keycloak_base_url()}/logout",
            headers=headers,
            data={
                'client_id': os.getenv('KEYCLOAK_CLIENT_ID'),
                'client_secret': os.getenv('KEYCLOAK_CLIENT_SECRET'),
                'refresh_token': refresh_tok,
            },
            timeout=10
        )
        return response.status_code in [200, 204]
    except Exception as e:
        print(f"[ERROR] logout: {str(e)}")
        return False