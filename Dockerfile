# Usa una imagen base oficial de Python (versión más reciente recomendada)
FROM python:3.13-slim

# Establece el directorio de trabajo en el contenedor
WORKDIR /code

# Copia el archivo de dependencias primero para aprovechar el caché de Docker
COPY ./requirements.txt /code/requirements.txt

# Instala las dependencias
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /code/requirements.txt

# Copia el directorio de la aplicación (app) y otros archivos necesarios
COPY ./app /code/app
# Si tienes otros archivos como .env (aunque no recomendado en prod), cópialos aquí
# COPY ./.env /code/.env # No hagas esto si usas las env vars de Render

# Expón el puerto en el que corre la aplicación (debe coincidir con Uvicorn/FastAPI)
# Render espera 10000 por defecto, pero detecta EXPOSE o puedes configurarlo.
# Usemos 8000 como en config.py por consistencia. Render puede mapearlo.
EXPOSE 8000

# Comando para correr la aplicación usando Uvicorn
# Render ejecutará este comando. Asegúrate de NO usar --reload en producción.
# Usa el host 0.0.0.0 para que sea accesible desde fuera del contenedor.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]