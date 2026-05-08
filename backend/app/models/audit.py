from app import db
from datetime import datetime

class AuditLog(db.Model):
    __tablename__ = 'audit_logs'

    id          = db.Column(db.Integer, primary_key=True)
    timestamp   = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    user_email  = db.Column(db.String(255), nullable=False)
    user_role   = db.Column(db.String(50), nullable=True)
    action      = db.Column(db.String(100), nullable=False)
    resource    = db.Column(db.String(255), nullable=True)
    detail      = db.Column(db.Text, nullable=True)
    status      = db.Column(db.String(20), default='success')  # success / failed
    ip_address  = db.Column(db.String(50), nullable=True)

    def to_dict(self):
        return {
            'id':         self.id,
            'timestamp':  self.timestamp.isoformat(),
            'user_email': self.user_email,
            'user_role':  self.user_role,
            'action':     self.action,
            'resource':   self.resource,
            'detail':     self.detail,
            'status':     self.status,
            'ip_address': self.ip_address,
        }