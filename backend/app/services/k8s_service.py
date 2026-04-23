from kubernetes import client, config
from kubernetes.client.rest import ApiException
import os

def get_k8s_clients():
    """Retourne (AppsV1Api, CoreV1Api) selon la config dispo."""
    kubeconfig_path = os.getenv('K8S_CONFIG_PATH')
    if kubeconfig_path and os.path.exists(kubeconfig_path):
        config.load_kube_config(config_file=kubeconfig_path)
    else:
        try:
            config.load_incluster_config()
        except config.ConfigException:
            config.load_kube_config()  # fallback sur default
    return client.AppsV1Api(), client.CoreV1Api()

def create_namespace(name, labels=None):
    """Crée un namespace Kubernetes. Retourne (success: bool, message: str)."""
    if labels is None:
        labels = {}
    labels['managed-by'] = 'devops-platform'

    _, core_v1 = get_k8s_clients()
    body = client.V1Namespace(
        metadata=client.V1ObjectMeta(name=name, labels=labels)
    )
    try:
        core_v1.create_namespace(body=body)
        return True, f"Namespace '{name}' créé"
    except ApiException as e:
        if e.status == 409:
            return True, f"Namespace '{name}' existe déjà"
        return False, f"Erreur Kubernetes: {e.reason}"
    except Exception as e:
        return False, f"Erreur inattendue: {str(e)}"
    
def delete_namespace(name):
    """
    Supprime un namespace Kubernetes.
    Retourne (success: bool, message: str).
    """
    _, core_v1 = get_k8s_clients()
    try:
        core_v1.delete_namespace(name=name)
        return True, f"Namespace '{name}' supprimé"
    except ApiException as e:
        if e.status == 404:
            return True, f"Namespace '{name}' n'existe pas"
        return False, f"Erreur Kubernetes: {e.reason}"
    except Exception as e:
        return False, f"Erreur inattendue: {str(e)}"

def list_pods(namespace):
    _, core_v1 = get_k8s_clients()
    pods = core_v1.list_namespaced_pod(namespace)
    return [{'name': p.metadata.name, 'status': p.status.phase} for p in pods.items]

def scale_deployment(namespace, deployment_name, replicas):
    apps_v1, _ = get_k8s_clients()
    body = {'spec': {'replicas': replicas}}
    apps_v1.patch_namespaced_deployment_scale(deployment_name, namespace, body)
    return {'deployment': deployment_name, 'replicas': replicas}