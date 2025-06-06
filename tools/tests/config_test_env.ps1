# Crear y activar entorno virtual para pruebas
python -m venv .venv-test
.\.venv-test\Scripts\Activate.ps1

# Instalar dependencias
pip install -r requirements-test.txt
