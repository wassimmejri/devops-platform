import os

class Config:
    FLASK_APP = os.getenv("FLASK_APP", "run.py")
    FLASK_ENV = os.getenv("FLASK_ENV", "development")
    SECRET_KEY = os.getenv("SECRET_KEY", "devops-platform-secret-key")

    # PostgreSQL (via kubectl port-forward)
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", "postgresql://devboard:devboard123@localhost:5432/devboard"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Redis
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

    # JWT
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "jwt-secret-key-change-in-production")
    JWT_ACCESS_TOKEN_EXPIRES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES", 86400))

    # Kubernetes
    K8S_MASTER_IP = os.getenv("K8S_MASTER_IP", "172.25.50.101")

    # Jenkins
    JENKINS_URL = os.getenv("JENKINS_URL", "http://172.25.50.101:8080")
    JENKINS_USER = os.getenv("JENKINS_USER", "admin")
    JENKINS_TOKEN = os.getenv("JENKINS_TOKEN", "")

    # Prometheus
    PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://172.25.50.101:9090")

    # Loki
    LOKI_URL = os.getenv("LOKI_URL", "http://172.25.50.101:3100")