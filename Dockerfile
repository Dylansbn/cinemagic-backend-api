# Fichier: Dockerfile - CODE FINAL CORRIGÉ ET ROBUSTE

# Utilise l'image Python officielle et spécifie l'architecture AMD64
FROM --platform=linux/amd64 python:3.10

# Définit le répertoire de travail
WORKDIR /app

# Installe les dépendances système nécessaires
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copie et installe les paquets
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copie le reste du code de l'application
COPY . .

# Déclaration du port
EXPOSE 8000

# CORRECTION FINALE CRITIQUE: Commande de démarrage dynamique et robuste
# Utilise sh -c pour interpréter la variable $PORT de l'hébergeur
CMD ["sh", "-c", "python -m gunicorn server:app --bind 0.0.0.0:${PORT}"]