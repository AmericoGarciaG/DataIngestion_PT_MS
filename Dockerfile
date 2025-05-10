# Dockerfile

# 1. Imagen Base: Empieza desde una imagen oficial de Python ligera ('slim').
#    Especifica la versión de Python (ej. 3.10). Asegúrate de que coincida con la que usaste para desarrollar.
FROM python:3.10-slim

# 2. Directorio de Trabajo: Establece el directorio donde se ejecutarán los comandos dentro del contenedor.
WORKDIR /code

# 3. Copiar Dependencias: Copia SOLO el archivo requirements.txt primero.
#    Docker guarda en caché las capas. Si requirements.txt no cambia, no reinstalará
#    las dependencias cada vez, haciendo la construcción más rápida.
COPY ./requirements.txt /code/requirements.txt

# 4. Instalar Dependencias: Actualiza pip y luego instala las librerías listadas en requirements.txt.
#    --no-cache-dir evita guardar caché de pip, haciendo la imagen un poco más pequeña.
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /code/requirements.txt

# 5. Copiar Código Fuente: Copia el resto del código de la aplicación (la carpeta 'app') al contenedor.
COPY ./app /code/app
# Si tuvieras otros directorios o archivos en la raíz necesarios en producción, los copiarías aquí.
# ¡NO COPIES .env NI venv!

# 6. Exponer Puerto: Informa a Docker que la aplicación dentro del contenedor escuchará en el puerto 8000.
#    Esto NO publica el puerto a la máquina host, solo lo documenta. Render usará esta información.
EXPOSE 8000

# 7. Comando de Inicio: Define el comando que se ejecutará cuando se inicie un contenedor basado en esta imagen.
#    Ejecuta Uvicorn de la misma forma que lo haríamos localmente, apuntando a nuestra app FastAPI.
#    - Usa host 0.0.0.0 para que sea accesible desde fuera del contenedor.
#    - Usa el puerto 8000 (el que expusimos).
#    - ¡NO uses --reload en producción!
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]