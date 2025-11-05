# --- Configuration de l'environnement de base ---
FROM --platform=linux/amd64 python:3.10

# Définit le répertoire de travail
WORKDIR /app

# Anciennes lignes (qui pointaient vers un fichier qui n'existe pas) :
# COPY requirements-pro.txt .
# RUN pip install --no-cache-dir -r requirements-pro.txt

# Lignes 13-14:
RUN pip install --no-cache-dir -r requirements.txt

# Lignes 16-17:
# Copie le reste du code de l'application
COPY . .

# NOUVEAU: Expose le port de l'application
EXPOSE 8000

# Ligne 20: Définit la commande de démarrage (utilise Gunicorn)
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "server:app"]