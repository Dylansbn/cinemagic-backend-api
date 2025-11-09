# Utiliser Python officiel
FROM python:3.11-slim

# Définir le répertoire de travail
WORKDIR /app

# Copier les fichiers nécessaires
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Exposer le port (optionnel mais propre)
EXPOSE 8000

# Lancer l’application avec le port dynamique fourni par Railway
CMD ["sh", "-c", "gunicorn server:app --bind 0.0.0.0:$PORT"]
