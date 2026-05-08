import requests
import os

def get_keycloak_base():
    return os.getenv('KEYCLOAK_URL')

def get_keycloak_host():
    host = os.getenv('KEYCLOAK_HOST', '')
    return {'Host': host} if host else {}

def get_admin_token():
    """Récupère un token admin Keycloak."""
    url = f"{get_keycloak_base()}/realms/master/protocol/openid-connect/token"
    headers = get_keycloak_host()
    headers['Content-Type'] = 'application/x-www-form-urlencoded'

    response = requests.post(url, headers=headers, data={
        'client_id':  'admin-cli',
        'username':   os.getenv('KEYCLOAK_ADMIN_USER', 'admin'),
        'password':   os.getenv('KEYCLOAK_ADMIN_PASSWORD', 'admin123'),
        'grant_type': 'password'
    }, timeout=10)

    if response.status_code == 200:
        return response.json().get('access_token')
    raise RuntimeError(f"Impossible d'obtenir le token admin: {response.text}")

def get_realm():
    return os.getenv('KEYCLOAK_REALM', 'devops-platform')

def get_headers():
    token = get_admin_token()
    headers = get_keycloak_host()
    headers['Authorization'] = f'Bearer {token}'
    headers['Content-Type']  = 'application/json'
    return headers

def list_users():
    """Liste tous les users du realm."""
    url = f"{get_keycloak_base()}/admin/realms/{get_realm()}/users"
    response = requests.get(url, headers=get_headers(), timeout=10)
    if response.status_code == 200:
        return response.json()
    raise RuntimeError(f"Erreur listing users: {response.text}")

def get_user(user_id):
    """Récupère un user par son ID Keycloak."""
    url = f"{get_keycloak_base()}/admin/realms/{get_realm()}/users/{user_id}"
    response = requests.get(url, headers=get_headers(), timeout=10)
    if response.status_code == 200:
        return response.json()
    raise RuntimeError(f"User introuvable: {response.text}")

def update_user_status(user_id, enabled: bool):
    """Active ou suspend un user."""
    url = f"{get_keycloak_base()}/admin/realms/{get_realm()}/users/{user_id}"
    response = requests.put(url, headers=get_headers(),
                            json={'enabled': enabled}, timeout=10)
    return response.status_code in [200, 204]

def get_user_roles(user_id):
    """Récupère les rôles realm d'un user."""
    url = f"{get_keycloak_base()}/admin/realms/{get_realm()}/users/{user_id}/role-mappings/realm"
    response = requests.get(url, headers=get_headers(), timeout=10)
    if response.status_code == 200:
        return response.json()
    return []

def get_realm_roles():
    """Liste tous les rôles du realm."""
    url = f"{get_keycloak_base()}/admin/realms/{get_realm()}/roles"
    response = requests.get(url, headers=get_headers(), timeout=10)
    if response.status_code == 200:
        return response.json()
    return []

def assign_role(user_id, role_name):
    """Assigne un rôle à un user."""
    # Récupère tous les rôles pour trouver l'objet rôle complet
    roles = get_realm_roles()
    role  = next((r for r in roles if r['name'] == role_name), None)
    if not role:
        raise RuntimeError(f"Rôle '{role_name}' introuvable")

    url = f"{get_keycloak_base()}/admin/realms/{get_realm()}/users/{user_id}/role-mappings/realm"
    response = requests.post(url, headers=get_headers(),
                             json=[role], timeout=10)
    return response.status_code in [200, 204]

def remove_role(user_id, role_name):
    """Retire un rôle d'un user."""
    roles = get_realm_roles()
    role  = next((r for r in roles if r['name'] == role_name), None)
    if not role:
        raise RuntimeError(f"Rôle '{role_name}' introuvable")

    url = f"{get_keycloak_base()}/admin/realms/{get_realm()}/users/{user_id}/role-mappings/realm"
    response = requests.delete(url, headers=get_headers(),
                               json=[role], timeout=10)
    return response.status_code in [200, 204]

def change_user_role(user_id, new_role):
    """Change le rôle d'un user (retire l'ancien, assigne le nouveau)."""
    current_roles = get_user_roles(user_id)
    managed_roles = ['admin-devops', 'developer']

    # Retire les rôles gérés par la plateforme
    for role in current_roles:
        if role['name'] in managed_roles:
            remove_role(user_id, role['name'])

    # Assigne le nouveau rôle
    return assign_role(user_id, new_role)

def delete_user(user_id):
    """Supprime un user de Keycloak."""
    url = f"{get_keycloak_base()}/admin/realms/{get_realm()}/users/{user_id}"
    response = requests.delete(url, headers=get_headers(), timeout=10)
    return response.status_code in [200, 204]

def reset_password_email(user_id):
    """Envoie un email de réinitialisation de mot de passe."""
    url = f"{get_keycloak_base()}/admin/realms/{get_realm()}/users/{user_id}/execute-actions-email"
    response = requests.put(url, headers=get_headers(),
                            json=['UPDATE_PASSWORD'], timeout=10)
    return response.status_code in [200, 204]