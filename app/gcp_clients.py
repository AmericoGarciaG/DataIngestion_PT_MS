# app/gcp_clients.py
from google.cloud import firestore
from google.cloud import pubsub_v1
from .config import settings
import logging

logger = logging.getLogger(__name__)

db_firestore = None
try:
    # project se autodetecta si está en GCP, o lo toma de env var GOOGLE_CLOUD_PROJECT
    db_firestore = firestore.Client(project=settings.google_cloud_project)
    logger.info(f"Firestore client initialized for project: {db_firestore.project}")
except Exception as e:
    logger.error(f"Failed to initialize Firestore client: {e}", exc_info=True)


publisher_client = None
topic_path_historical_data = None
if settings.google_cloud_project: # O si está configurado para usar Pub/Sub
    try:
        publisher_client = pubsub_v1.PublisherClient()
        topic_path_historical_data = publisher_client.topic_path(
            settings.google_cloud_project,
            settings.pubsub_historical_data_topic_id
        )
        # Opcional: Crear el tópico si no existe (mejor hacerlo vía gcloud o IaC)
        try:
            publisher_client.get_topic(topic=topic_path_historical_data)
            logger.info(f"Pub/Sub topic '{settings.pubsub_historical_data_topic_id}' found.")
        except Exception: # google.api_core.exceptions.NotFound
            logger.warning(f"Pub/Sub topic '{settings.pubsub_historical_data_topic_id}' not found. Attempting to create...")
            publisher_client.create_topic(name=topic_path_historical_data)
            logger.info(f"Pub/Sub topic '{settings.pubsub_historical_data_topic_id}' created.")
    except Exception as e:
        logger.error(f"Failed to initialize Pub/Sub client or topic: {e}", exc_info=True)