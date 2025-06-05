# Dockerfile

# 1. Imagen Base:
#    Comenzamos con una imagen oficial de Python. 'slim' es una variante ligera.
#    Asegúrate de que la versión de Python (ej. 3.10, 3.11, 3.12) coincida con la que usaste
#    para desarrollo y la que es compatible con todas tus dependencias.
FROM python:3.11-slim
# FROM python:3.12-slim # O la versión que estés utilizando

# 2. Establecer Variables de Entorno (Opcional pero recomendado):
#    - PYTHONUNBUFFERED: Asegura que los print() y logs de Python se envíen directamente
#      a la terminal/logs del contenedor sin buffering, lo cual es bueno para Cloud Logging.
#    - PIP_NO_CACHE_DIR: Deshabilita el caché de pip, puede hacer la imagen un poco más pequeña.
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=off

# 3. Directorio de Trabajo:
#    Establece el directorio por defecto dentro del contenedor donde se ejecutarán los comandos.
WORKDIR /app

# 4. Copiar Archivo de Dependencias:
#    Copiamos SOLO requirements.txt primero. Docker guarda en caché las capas.
#    Si requirements.txt no cambia, Docker reutilizará la capa de dependencias instaladas,
#    haciendo las construcciones subsecuentes más rápidas si solo cambia el código fuente.
COPY ./requirements.txt /app/requirements.txt

# 5. Instalar Dependencias:
#    Actualiza pip y luego instala las librerías listadas en requirements.txt.
RUN pip install --upgrade pip && \
    pip install -r /app/requirements.txt

# 6. Copiar Código Fuente de la Aplicación:
#    Copia el directorio 'app' (que contiene todo nuestro código Python)
#    y cualquier otro archivo necesario en la raíz al directorio de trabajo del contenedor.
COPY ./app /app/app
# Si tuvieras otros archivos en la raíz que el CMD necesita (ej. un script de inicio), cópialos también.
# ¡NO COPIES .env, venv, .git, .vscode, etc. a la imagen Docker! (Usa .dockerignore para esto)

# 7. Copiar y configurar el script de inicio
COPY scripts/docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh

# 8. Exponer Puerto:
#    Cloud Run pasará el puerto a usar a través de la variable de entorno PORT
EXPOSE 8080

# 9. Comando de Inicio (CMD):
#    Define el comando que se ejecutará cuando se inicie un contenedor basado en esta imagen.
#    Usamos el script de inicio que maneja la variable PORT correctamente
CMD ["/app/docker-entrypoint.sh"]