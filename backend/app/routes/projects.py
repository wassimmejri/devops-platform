from flask import Blueprint, request, jsonify
from app.utils.auth_decorator import keycloak_required, get_or_create_user, role_required
from app import db
from app.models.project import Project
from app.models.user import User
from app.services.k8s_service import create_namespace, delete_namespace
import re

projects_bp = Blueprint('projects', __name__)

def sanitize_namespace_name(project_name):
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

    namespace_name = sanitize_namespace_name(data['name'])
    success, msg   = create_namespace(namespace_name, labels={'project': data['name']})
    if not success:
        return jsonify({'message': f'Erreur création namespace: {msg}'}), 500

    project = Project(
        name=data['name'],
        description=data.get('description', ''),
        github_url=data.get('github_url', ''),
        github_branch=data.get('github_branch', 'main'),
        k8s_namespace=namespace_name,
        owner_id=user.id
    )
    db.session.add(project)
    db.session.commit()
    return jsonify({'message': 'Projet créé avec succès', 'project': project.to_dict(), 'namespace': namespace_name}), 201

@projects_bp.route('/', methods=['GET'])
@keycloak_required
def get_projects():
    user = get_or_create_user(request.userinfo)
    
    if user.role == 'admin-devops':
        projects = Project.query.all()
    else:
        projects = Project.query.filter_by(owner_id=user.id).all()
    
    return jsonify([p.to_dict() for p in projects]), 200

@projects_bp.route('/<int:project_id>', methods=['GET'])
@keycloak_required
def get_project(project_id):
    user    = get_or_create_user(request.userinfo)
    project = Project.query.filter_by(id=project_id, owner_id=user.id).first()
    if not project:
        return jsonify({'message': 'Projet introuvable'}), 404
    return jsonify(project.to_dict()), 200

@projects_bp.route('/<int:project_id>', methods=['PUT'])
@keycloak_required
def update_project(project_id):
    user    = get_or_create_user(request.userinfo)
    project = Project.query.filter_by(id=project_id, owner_id=user.id).first()
    if not project:
        return jsonify({'message': 'Projet introuvable'}), 404

    data = request.get_json()
    project.name          = data.get('name', project.name)
    project.description   = data.get('description', project.description)
    project.github_url    = data.get('github_url', project.github_url)
    project.github_branch = data.get('github_branch', project.github_branch)
    db.session.commit()
    return jsonify({'message': 'Projet modifié', 'project': project.to_dict()}), 200

# ── Suppression — admin-devops uniquement ────────────
@projects_bp.route('/<int:project_id>', methods=['DELETE'])
@keycloak_required
@role_required('admin-devops')
def delete_project(project_id):
    user    = get_or_create_user(request.userinfo)
    project = Project.query.filter_by(id=project_id, owner_id=user.id).first()
    if not project:
        return jsonify({'message': 'Projet introuvable'}), 404

    namespace = project.k8s_namespace
    if namespace:
        success, msg = delete_namespace(namespace)
        if not success:
            print(f"⚠️ Erreur suppression namespace {namespace}: {msg}")

    db.session.delete(project)
    db.session.commit()
    return jsonify({'message': 'Projet et namespace supprimés avec succès'}), 200