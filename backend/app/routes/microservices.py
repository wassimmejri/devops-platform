from flask import Blueprint, request, jsonify
from app.utils.auth_decorator import keycloak_required, get_or_create_user
from app import db
from app.models.microservice import Microservice
from app.models.project import Project
import re

microservices_bp = Blueprint('microservices', __name__)


def sanitize_jenkins_job_name(project_name, ms_name):
    """Nettoie le nom pour en faire un job Jenkins valide (pas d'espaces, caractères spéciaux)."""
    raw = f"{project_name}-{ms_name}"
    # Remplace tout ce qui n'est pas lettre, chiffre ou tiret par un tiret
    cleaned = re.sub(r'[^a-zA-Z0-9-]', '-', raw)
    # Supprime les tirets multiples et les tirets en début/fin
    cleaned = re.sub(r'-+', '-', cleaned).strip('-')
    return cleaned


@microservices_bp.route('/<int:project_id>/microservices', methods=['POST'])
@keycloak_required
def create_microservice(project_id):
    user = get_or_create_user(request.userinfo)
    project = Project.query.filter_by(id=project_id, owner_id=user.id).first()
    if not project:
        return jsonify({'message': 'Projet introuvable'}), 404

    data = request.get_json()
    job_name = sanitize_jenkins_job_name(project.name, data['name'])
    
    microservice = Microservice(
        name=data['name'],
        image=data.get('image', ''),
        port=data.get('port', 8080),
        replicas=data.get('replicas', 1),
        env_vars=data.get('env_vars', {}),
        project_id=project_id,
        k8s_deployment_name=f"{project.k8s_namespace}-{data['name']}",
        jenkins_job_name=job_name
    )
    db.session.add(microservice)
    db.session.commit()
    return jsonify({
        'message': 'Microservice ajouté avec succès',
        'microservice': microservice.to_dict()
    }), 201


@microservices_bp.route('/<int:project_id>/microservices', methods=['GET'])
@keycloak_required
def get_microservices(project_id):
    user = get_or_create_user(request.userinfo)
    project = Project.query.filter_by(id=project_id, owner_id=user.id).first()
    if not project:
        return jsonify({'message': 'Projet introuvable'}), 404
    return jsonify([m.to_dict() for m in project.microservices]), 200


@microservices_bp.route('/microservices/<int:microservice_id>', methods=['PUT'])
@keycloak_required
def update_microservice(microservice_id):
    user = get_or_create_user(request.userinfo)
    microservice = Microservice.query.join(Project).filter(
        Microservice.id == microservice_id,
        Project.owner_id == user.id
    ).first()
    if not microservice:
        return jsonify({'message': 'Microservice introuvable'}), 404

    data = request.get_json()
    microservice.name = data.get('name', microservice.name)
    microservice.image = data.get('image', microservice.image)
    microservice.port = data.get('port', microservice.port)
    microservice.replicas = data.get('replicas', microservice.replicas)
    microservice.env_vars = data.get('env_vars', microservice.env_vars)
    db.session.commit()
    return jsonify({
        'message': 'Microservice modifié avec succès',
        'microservice': microservice.to_dict()
    }), 200


@microservices_bp.route('/microservices/<int:microservice_id>', methods=['DELETE'])
@keycloak_required
def delete_microservice(microservice_id):
    user = get_or_create_user(request.userinfo)
    microservice = Microservice.query.join(Project).filter(
        Microservice.id == microservice_id,
        Project.owner_id == user.id
    ).first()
    if not microservice:
        return jsonify({'message': 'Microservice introuvable'}), 404

    db.session.delete(microservice)
    db.session.commit()
    return jsonify({'message': 'Microservice supprimé avec succès'}), 200


@microservices_bp.route('/microservices/<int:microservice_id>/deployments', methods=['GET'])
@keycloak_required
def get_deployments(microservice_id):
    user = get_or_create_user(request.userinfo)
    
    microservice = Microservice.query.join(Project).filter(
        Microservice.id == microservice_id,
        Project.owner_id == user.id
    ).first()
    
    if not microservice:
        return jsonify({'message': 'Microservice introuvable'}), 404
    
    deployments = [d.to_dict() for d in microservice.deployments]
    return jsonify(deployments), 200