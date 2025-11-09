# Fichier: Dockerfile — VERSION FINALE STABLE POUR RAILWAY

# Utilise l'image Python officielle (AMD64 pour compatibilité Railway)
FROM --platform=linux/amd64 python:3.10

# Définit le répertoire de travail
WORKDIR /app

# Installe les dépendances système nécessaires (PostgreSQL, build tools, etc.)
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copie et installe les dépendances Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copie tout le code du projet dans le conteneur
COPY . .

# Déclare le port exposé (Railway attribue dynamiquement $PORT)
EXPOSE 8000

# Commande de démarrage : lance Gunicorn sur la variable $PORT fournie par Railway
CMD ["gunicorn", "server:app", "--bind", "0.0.0.0:${PORT}"]