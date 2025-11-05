# --- Configuration de l'environnement de base ---
FROM --platform=linux/amd64 python:3.10

# Définit le répertoire de travail
WORKDIR /app

# Anciennes lignes (qui pointaient vers un fichier qui n'existe pas) :
# COPY requirements-pro.txt .
# RUN pip install --no-cache-dir -r requirements-pro.txt

# Nouvelles lignes (Correctes) :
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --- Copie du code et Lancement ---
# Copie le reste du code
COPY . .

# Définit la commande de démarrage (utilise Gunicorn)
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT} server:app"]