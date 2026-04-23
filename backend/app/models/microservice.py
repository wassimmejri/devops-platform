from app import db
from datetime import datetime

class Microservice(db.Model):
    __tablename__ = 'microservices'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    image = db.Column(db.String(255))
    port = db.Column(db.Integer, default=8080)
    replicas = db.Column(db.Integer, default=1)
    env_vars = db.Column(db.JSON, default={})
    status = db.Column(db.String(50), default='pending')
    # status : pending / running / error / stopped

    # Lien avec Jenkins
    jenkins_job_name = db.Column(db.String(255))

    # Lien avec Kubernetes
    k8s_deployment_name = db.Column(db.String(255))

    # Clé étrangère vers Project
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relation avec les déploiements
    deployments = db.relationship('Deployment', backref='microservice', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'image': self.image,
            'port': self.port,
            'replicas': self.replicas,
            'env_vars': self.env_vars,
            'status': self.status,
            'jenkins_job_name': self.jenkins_job_name,
            'k8s_deployment_name': self.k8s_deployment_name,
            'project_id': self.project_id,
            'created_at': str(self.created_at),
            'updated_at': str(self.updated_at)
        }