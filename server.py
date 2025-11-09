# Fichier : cinemagic-backend/server.py - CODE FINAL CORRIGÉ

import os
import json
import time
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from supabase import create_client, Client
import stripe
from flask_cors import CORS  # <-- Importation de Flask-CORS

# --- 1. INITIALISATION ---
load_dotenv()

# Clés secrètes du .env / Rendu (Railay)
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
STRIPE_WH_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET")
STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY")
BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:5000") 

# Initialisation des clients
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
stripe.api_key = STRIPE_SECRET_KEY
app = Flask(__name__) 

# CORRECTION CRITIQUE: Configuration CORS pour autoriser le Front-end
# Ceci résout l'erreur de sécurité du navigateur
CORS(app, origins=["http://localhost:3000", "https://cinemagic-backend-api-production.up.railway.app"])


# --- 2. FONCTIONS UTILITAIRES DE LA BASE DE DONNÉES (Omis pour la concision) ---
def update_user_subscription(user_id: str, status: str, customer_id: str = None):
    # ... (Votre logique de mise à jour de Supabase)
    return True

# --- 3. LOGIQUE DE PAIEMENT (API CHECKOUT) ---

@app.route('/create-checkout-session', methods=['POST'])
def create_checkout_session():
    """Crée une session de paiement Stripe."""
    data = request.get_json()
    user_id = data.get('userId') 
    price_id = data.get('priceId') # ID du plan Stripe (reçu du Frontend)
    return_url = data.get('return_url', 'http://localhost:3000') 
    
    if not user_id or not price_id:
        return jsonify({"error": "User ID ou Price ID manquant."}), 400

    try:
        # Étape 1: Créer ou récupérer le client Stripe
        profile = supabase.table('profiles').select('stripe_customer_id').eq('id', user_id).single().execute().data
        customer_id = profile.get('stripe_customer_id') if profile else None
        
        if not customer_id:
            customer = stripe.Customer.create(metadata={'supabase_user_id': user_id})
            customer_id = customer.id
            update_user_subscription(user_id, 'free', customer_id) # Initialiser le statut

        # Étape 2: Créer la session de checkout Stripe
        checkout_session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=['card'],
            line_items=[
                {
                    'price': price_id, 
                    'quantity': 1,
                },
            ],
            mode='subscription',
            success_url=f"{return_url}/dashboard?session_id={{CHECKOUT_SESSION_ID}}&success=true", 
            cancel_url=f"{return_url}/pricing", 
            subscription_data={'trial_period_days': 0}
        )
        return jsonify({'url': checkout_session.url}), 200

    except Exception as e:
        print(f"❌ Erreur Stripe: {e}")
        return jsonify({'error': str(e)}), 500

# --- 4. LOGIQUE WEBHOOK (Omis pour la concision) ---
@app.route('/webhook', methods=['POST'])
def webhook():
    return jsonify(success=True)

# --- 5. LOGIQUE DE MONTAGE VIDEO (Omis pour la concision) ---
@app.route('/montage-video', methods=['POST'])
def start_montage():
    return jsonify({"message": "Montage lancé avec succès!", "result_url_mock": "http://localhost:3000/videos/montage_simule.mp4"}), 200

# --- 6. LANCEMENT DU SERVEUR LOCAL (Commenté pour le déploiement Docker) ---

# if __name__ == '__main__':
#     app.run(host='0.0.0.0', port=5000, debug=True)