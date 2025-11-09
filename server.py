# Fichier : cinemagic-backend/server.py — VERSION FINALE STABLE POUR RAILWAY

import os
import json
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from supabase import create_client, Client
import stripe
from flask_cors import CORS

# --- 1. INITIALISATION DES VARIABLES D'ENVIRONNEMENT ---
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
STRIPE_WH_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:5000")

# --- 2. CONFIGURATION DES CLIENTS ET DE FLASK ---
app = Flask(__name__)

# CORS — autorise ton frontend local + Railway frontend (ajuste si tu as un autre domaine)
CORS(app, origins=[
    "http://localhost:3000",
    "https://cinemagic-frontend.up.railway.app"
])

# Initialisation Supabase et Stripe
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
stripe.api_key = STRIPE_SECRET_KEY


# --- 3. FONCTION UTILE : MISE À JOUR ABONNEMENT ---
def update_user_subscription(user_id: str, status: str, customer_id: str = None):
    """Met à jour les informations d'abonnement dans la table Supabase 'profiles'."""
    try:
        data = {"subscription_status": status}
        if customer_id:
            data["stripe_customer_id"] = customer_id
        supabase.table("profiles").update(data).eq("id", user_id).execute()
        return True
    except Exception as e:
        print(f"Erreur lors de la mise à jour de Supabase : {e}")
        return False


# --- 4. CRÉATION DE LA SESSION STRIPE CHECKOUT ---
@app.route('/create-checkout-session', methods=['POST'])
def create_checkout_session():
    data = request.get_json()
    user_id = data.get('userId')
    price_id = data.get('priceId')
    return_url = data.get('return_url', 'http://localhost:3000')

    if not user_id or not price_id:
        return jsonify({"error": "User ID ou Price ID manquant."}), 400

    try:
        # Récupère le client Stripe s'il existe déjà
        profile = supabase.table('profiles').select('stripe_customer_id').eq('id', user_id).single().execute().data
        customer_id = profile.get('stripe_customer_id') if profile else None

        # Si le client n'existe pas, le créer
        if not customer_id:
            customer = stripe.Customer.create(metadata={'supabase_user_id': user_id})
            customer_id = customer.id
            update_user_subscription(user_id, 'free', customer_id)

        # Crée la session de paiement
        checkout_session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=['card'],
            line_items=[{'price': price_id, 'quantity': 1}],
            mode='subscription',
            success_url=f"{return_url}/dashboard?session_id={{CHECKOUT_SESSION_ID}}&success=true",
            cancel_url=f"{return_url}/pricing",
            subscription_data={'trial_period_days': 0}
        )
        return jsonify({'url': checkout_session.url}), 200

    except Exception as e:
        print(f"❌ Erreur Stripe : {e}")
        return jsonify({'error': str(e)}), 500


# --- 5. WEBHOOK STRIPE (optionnel, à compléter si besoin) ---
@app.route('/webhook', methods=['POST'])
def webhook():
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WH_SECRET)
    except Exception as e:
        print(f"⚠️ Erreur Webhook : {e}")
        return jsonify(success=False), 400

    # Exemple de gestion d'événement
    if event['type'] == 'invoice.payment_succeeded':
        customer_id = event['data']['object']['customer']
        print(f"✅ Paiement réussi pour {customer_id}")

    return jsonify(success=True), 200


# --- 6. LOGIQUE MONTAGE VIDÉO (SIMULÉE) ---
@app.route('/montage-video', methods=['POST'])
def start_montage():
    """Simule le lancement d'un montage vidéo IA."""
    return jsonify({
        "message": "Montage lancé avec succès !",
        "result_url_mock": "http://localhost:3000/videos/montage_simule.mp4"
    }), 200


# --- 7. LANCEMENT LOCAL UNIQUEMENT (non utilisé en production Docker) ---
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)