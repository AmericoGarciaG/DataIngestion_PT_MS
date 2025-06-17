# app/gcp_clients.py
"""
Clientes para servicios de Google Cloud Platform.

Este módulo centraliza la inicialización de los clientes de Google Cloud Platform (GCP)
que la aplicación necesita, como Firestore y Pub/Sub. Proporciona instancias compartidas
de estos clientes para ser utilizadas por otros módulos de la aplicación.

Attributes:
    db_firestore (firestore.Client): Cliente de Firestore inicializado o None si falló.
    publisher_client (pubsub_v1.PublisherClient): Cliente de Pub/Sub inicializado o None si falló.
    topic_path_historical_data (str): Ruta completa del tópico de Pub/Sub para datos históricos o None.
"""

from google.cloud import firestore
from google.cloud import pubsub_v1
from .config import settings
import logging

logger = logging.getLogger(__name__)

# Inicialización del cliente de Firestore
db_firestore = None
try:
    # project se autodetecta si está en GCP, o lo toma de env var GOOGLE_CLOUD_PROJECT_ID
    db_firestore = firestore.Client(project=settings.google_cloud_project_id)
    logger.info(f"Firestore client initialized for project: {db_firestore.project}")
except Exception as e:
    logger.error(f"Failed to initialize Firestore client: {e}", exc_info=True)


# Inicialización del cliente de Pub/Sub y configuración del tópico
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



'''
gcp_clients.py
Propósito: Este módulo centraliza la inicialización de los clientes de Google Cloud Platform (GCP) que la aplicación de servicio necesita, como el cliente de Firestore y el cliente de Pub/Sub. Proporciona instancias compartidas de estos clientes para ser utilizadas por otros módulos de la aplicación.

Funcionamiento Principal:

Importación de Configuración: Importa la instancia settings del módulo service.app.config.
Inicialización del Cliente Firestore (db_firestore):
Intenta crear una instancia de firestore.Client().
El ID del proyecto GCP se pasa explícitamente (project=settings.google_cloud_project_id), aunque el cliente también puede autodetectarlo si la aplicación se ejecuta en un entorno GCP con metadatos disponibles o si GOOGLE_APPLICATION_CREDENTIALS está configurado.
Registra un mensaje de éxito o error durante la inicialización.
Inicialización del Cliente Pub/Sub (publisher_client y topic_path_historical_data):
Verifica si settings.google_cloud_project_id y settings.pubsub_historical_data_topic_id están configurados.
Si es así, intenta crear una instancia de pubsub_v1.PublisherClient().
Construye la ruta completa del tópico (topic_path_historical_data) utilizando el ID del proyecto y el ID del tópico.
Verificación del Tópico: Intenta obtener información del tópico (publisher_client.get_topic()). Esto sirve como una verificación de que el tópico existe y la cuenta de servicio tiene permisos para accederlo (al menos para publicar).
Si la verificación del tópico falla (ej. no encontrado, sin permisos), registra un error detallado y establece publisher_client y topic_path_historical_data a None para evitar intentos de uso fallidos.
Registra mensajes de éxito o error durante la inicialización.
Si el ID del proyecto o del tópico no están configurados, registra una advertencia indicando que el cliente Pub/Sub no se inicializará.
Dependencias:

Google Cloud Client Libraries para Python: google-cloud-firestore, google-cloud-pubsub.
Módulo interno: service.app.config (para acceder a settings).
logging (módulo estándar).
Uso: Este módulo no se ejecuta directamente. Otros módulos importan las instancias de cliente que proporciona:

python
# Ejemplo de uso en otro módulo:
# from .gcp_clients import db_firestore, publisher_client, topic_path_historical_data
#
# if db_firestore:
#     doc_ref = db_firestore.collection("my_collection").document("my_doc")
#     # ... usar doc_ref ...
#
# if publisher_client and topic_path_historical_data:
#     # ... publicar mensaje ...
Entradas:

Parámetros de configuración de la instancia settings:
settings.google_cloud_project_id
settings.pubsub_historical_data_topic_id (que se inicializa desde settings.pubsub_topic_name en config.py).
Salidas y Efectos Secundarios:

Proporciona las variables globales db_firestore, publisher_client, y topic_path_historical_data que contienen las instancias de cliente o la ruta del tópico, o None si la inicialización falló.
Imprime mensajes de log sobre el estado de la inicialización de los clientes.
Mejores Prácticas y Consideraciones:

Inicialización Única: Inicializar los clientes una vez al inicio de la aplicación (cuando se importa este módulo) y reutilizarlos es eficiente, ya que evita la sobrecarga de crear nuevos clientes para cada solicitud u operación.
Manejo de Errores en la Inicialización: El script incluye bloques try-except para capturar errores durante la inicialización de los clientes y registrarlos, lo que ayuda a diagnosticar problemas de configuración o permisos.
Verificación de Tópico Pub/Sub: La verificación explícita de la existencia y accesibilidad del tópico Pub/Sub es una buena práctica para detectar problemas de configuración tempranamente (ej. el tópico no fue creado por Terraform, o la SA no tiene el rol roles/pubsub.publisher).
Permisos de la Cuenta de Servicio: La cuenta de servicio bajo la cual se ejecuta la aplicación necesita los permisos IAM adecuados para Firestore (ej. roles/datastore.user) y Pub/Sub (ej. roles/pubsub.publisher para el tópico específico, o roles/pubsub.editor a nivel de proyecto si necesita gestionar tópicos, aunque esto último no es recomendable para la SA de ejecución).
Configuración del Proyecto: Asegurarse de que settings.google_cloud_project_id esté correctamente configurado en .env es crucial.
'''