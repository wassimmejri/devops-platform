from app import db
from datetime import datetime

class Project(db.Model):
    __tablename__ = 'projects'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    github_url = db.Column(db.String(255))
    github_branch = db.Column(db.String(100), default='main')
    k8s_namespace = db.Column(db.String(100))
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relations
    owner = db.relationship('User', backref='projects')
    microservices = db.relationship('Microservice', backref='project', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'github_url': self.github_url,
            'github_branch': self.github_branch,
            'k8s_namespace': self.k8s_namespace,
            'owner_id': self.owner_id,
            'created_at': str(self.created_at)
        }