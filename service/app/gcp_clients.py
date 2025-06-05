# app/gcp_clients.py
from google.cloud import firestore
from google.cloud import pubsub_v1
from .config import settings
import logging

logger = logging.getLogger(__name__)

db_firestore = None
try:
    # project se autodetecta si está en GCP, o lo toma de env var GOOGLE_CLOUD_PROJECT_ID
    db_firestore = firestore.Client(project=settings.google_cloud_project_id)
    logger.info(f"Firestore client initialized for project: {db_firestore.project}")
except Exception as e:
    logger.error(f"Failed to initialize Firestore client: {e}", exc_info=True)


publisher_client = None
topic_path_historical_data = None
if settings.google_cloud_project_id and settings.pubsub_historical_data_topic_id: # Asegurar que el topic_id esté en settings
    try:
        publisher_client = pubsub_v1.PublisherClient()
        topic_path_historical_data = publisher_client.topic_path(
            settings.google_cloud_project_id,
            settings.pubsub_historical_data_topic_id
        )
        # Verificar si el tópico existe (get_topic fallará si no existe o no hay permisos)
        try:
            publisher_client.get_topic(topic=topic_path_historical_data)
            logger.info(f"Pub/Sub topic '{settings.pubsub_historical_data_topic_id}' found and accessible.")
        except Exception as e_get_topic: # google.api_core.exceptions.NotFound u otros
            logger.error(f"Pub/Sub topic '{settings.pubsub_historical_data_topic_id}' not found or not accessible by the service account. Error: {e_get_topic}")
            logger.error("Please ensure the topic is created (e.g., by Terraform) and the service account has 'Pub/Sub Publisher' role on it, or 'Pub/Sub Editor' on the project if it needs to manage topics (not recommended for runtime SA).")
            # Considerar si el servicio debe fallar en arrancar si el tópico no es accesible.
            # Por ahora, solo logueamos el error. La publicación fallará más tarde.
            publisher_client = None # Asegurar que no se intente usar si no es accesible
            topic_path_historical_data = None
    except Exception as e:
        logger.error(f"Failed to initialize Pub/Sub client or topic path: {e}", exc_info=True)
        publisher_client = None
        topic_path_historical_data = None
else:
    logger.warning("Pub/Sub topic ID or project not configured. Pub/Sub client will not be initialized.")