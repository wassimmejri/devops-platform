from app import db
from datetime import datetime

class Deployment(db.Model):
    __tablename__ = 'deployments'

    id = db.Column(db.Integer, primary_key=True)
    version = db.Column(db.String(100))
    status = db.Column(db.String(50), default='pending')
    # status : pending / building / testing / deploying / success / failed

    # Logs du pipeline Jenkins
    build_logs = db.Column(db.Text)

    # Numéro du build Jenkins
    jenkins_build_number = db.Column(db.Integer)

    # Durée du déploiement en secondes
    duration = db.Column(db.Integer)

    # Clé étrangère vers Microservice
    microservice_id = db.Column(db.Integer, db.ForeignKey('microservices.id'), nullable=False)

    # Qui a déclenché le déploiement
    triggered_by = db.Column(db.Integer, db.ForeignKey('users.id'))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    finished_at = db.Column(db.DateTime)

    # Relation
    triggered_by_user = db.relationship('User', backref='deployments')

    def to_dict(self):
        return {
            'id': self.id,
            'version': self.version,
            'status': self.status,
            'build_logs': self.build_logs,
            'jenkins_build_number': self.jenkins_build_number,
            'duration': self.duration,
            'microservice_id': self.microservice_id,
            'triggered_by': self.triggered_by,
            'created_at': str(self.created_at),
            'finished_at': str(self.finished_at) if self.finished_at else None
        }