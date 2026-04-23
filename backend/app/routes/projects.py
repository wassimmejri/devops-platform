from flask import Blueprint, request, jsonify
from app.utils.auth_decorator import keycloak_required
from app import db
from app.models.project import Project
from app.models.user import User
from app.services.k8s_service import create_namespace
import re
from app.services.k8s_service import delete_namespace



projects_bp = Blueprint('projects', __name__)

def get_or_create_user(userinfo):
    """Récupère ou crée l'utilisateur local basé sur Keycloak"""
    email = userinfo.get('email', '')
    user = User.query.filter_by(email=email).first()
    if not user:
        user = User(
            email=email,
            full_name=userinfo.get('name', ''),
            password='keycloak',
            role='developer'
        )
        db.session.add(user)
        db.session.commit()
    return user

# ── Créer un projet ─────────────────────────────────
def sanitize_namespace_name(project_name):
    """Nettoie le nom pour en faire un namespace Kubernetes valide."""
    name = project_name.lower()
    name = re.sub(r'[\s_]+', '-', name)
    name = re.sub(r'[^a-z0-9-]', '', name)
    name = name.strip('-')
    return f"proj-{name}"[:63]

@projects_bp.route('/', methods=['POST'])
@keycloak_required
def create_project():
    user = get_or_create_user(request.userinfo)
    data = request.get_json()

    if not data.get('name'):
        return jsonify({'message': 'Le nom du projet est obligatoire'}), 400

    # 1. Générer un nom de namespace propre
    namespace_name = sanitize_namespace_name(data['name'])

    # 2. Créer le namespace Kubernetes
    success, msg = create_namespace(namespace_name, labels={'project': data['name']})
    if not success:
        return jsonify({'message': f'Erreur création namespace: {msg}'}), 500

    # 3. Créer le projet en base
    project = Project(
        name=data['name'],
        description=data.get('description', ''),
        github_url=data.get('github_url', ''),
        github_branch=data.get('github_branch', 'main'),
        k8s_namespace=namespace_name,   # <- on stocke le nom nettoyé
        owner_id=user.id
    )

    db.session.add(project)
    db.session.commit()

    return jsonify({
        'message': 'Projet créé avec succès',
        'project': project.to_dict(),
        'namespace': namespace_name
    }), 201

# ── Lister les projets ──────────────────────────────
@projects_bp.route('/', methods=['GET'])
@keycloak_required
def get_projects():
    user = get_or_create_user(request.userinfo)
    projects = Project.query.filter_by(owner_id=user.id).all()
    return jsonify([p.to_dict() for p in projects]), 200

# ── Détails d'un projet ─────────────────────────────
@projects_bp.route('/<int:project_id>', methods=['GET'])
@keycloak_required
def get_project(project_id):
    user = get_or_create_user(request.userinfo)
    project = Project.query.filter_by(id=project_id, owner_id=user.id).first()
    if not project:
        return jsonify({'message': 'Projet introuvable'}), 404
    return jsonify(project.to_dict()), 200

# ── Modifier un projet ──────────────────────────────
@projects_bp.route('/<int:project_id>', methods=['PUT'])
@keycloak_required
def update_project(project_id):
    user = get_or_create_user(request.userinfo)
    project = Project.query.filter_by(id=project_id, owner_id=user.id).first()
    if not project:
        return jsonify({'message': 'Projet introuvable'}), 404

    data = request.get_json()
    project.name = data.get('name', project.name)
    project.description = data.get('description', project.description)
    project.github_url = data.get('github_url', project.github_url)
    project.github_branch = data.get('github_branch', project.github_branch)

    db.session.commit()
    return jsonify({'message': 'Projet modifié', 'project': project.to_dict()}), 200

# ── Supprimer un projet ─────────────────────────────
@projects_bp.route('/<int:project_id>', methods=['DELETE'])
@keycloak_required
def delete_project(project_id):
    user = get_or_create_user(request.userinfo)
    project = Project.query.filter_by(id=project_id, owner_id=user.id).first()
    if not project:
        return jsonify({'message': 'Projet introuvable'}), 404

    # 1. Supprimer le namespace Kubernetes
    namespace = project.k8s_namespace
    if namespace:
        success, msg = delete_namespace(namespace)
        if not success:
            # On log l'erreur mais on continue la suppression du projet en base
            print(f"⚠️ Erreur suppression namespace {namespace}: {msg}")

    # 2. Supprimer le projet en base (cascade sur microservices grâce à la relation)
    db.session.delete(project)
    db.session.commit()

    return jsonify({'message': 'Projet et namespace supprimés avec succès'}), 200