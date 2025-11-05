# Fichier : cinemagic-backend/server.py

import os
import json
import time
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from supabase import create_client, Client
import stripe

# --- 1. INITIALISATION ---
load_dotenv()

# Clés secrètes du .env
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") # Utilisez ce nom pour la clé secrète
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET")
STRIPE_PRICE_ID = os.environ.get("STRIPE_PRICE_ID")
BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:5000") # URL de votre serveur

# Initialisation des clients
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
stripe.api_key = STRIPE_SECRET_KEY
app = Flask(__name__)

# --- 2. FONCTIONS UTILITAIRES DE LA BASE DE DONNÉES ---

def update_user_subscription(user_id: str, status: str, customer_id: str = None):
    """Met à jour le statut d'abonnement et l'ID Stripe dans Supabase."""
    # Note: 'statut_d_abonnement' correspond au nom de votre colonne en français
    data = {'statut_d_abonnement': status} 
    if customer_id:
        data['stripe_customer_id'] = customer_id
        
    try:
        # Utiliser la clé Service Role pour la mise à jour sécurisée du profil
        response = supabase.table('profiles').update(data).eq('id', user_id).execute()
        
        if response.data and len(response.data) > 0:
            print(f"✅ Profil {user_id} mis à jour : {status}")
            return True
        else:
            print(f"⚠️ Erreur: Profil {user_id} non trouvé ou non mis à jour.")
            return False
            
    except Exception as e:
        print(f"❌ Erreur DB pour l'utilisateur {user_id}: {e}")
        return False

# --- 3. LOGIQUE DE PAIEMENT (API CHACKOUT - Appelée par le Front-end) ---

@app.route('/create-checkout-session', methods=['POST'])
def create_checkout_session():
    """Crée une session de paiement Stripe pour l'essai gratuit."""
    data = request.get_json()
    user_id = data.get('userId') # ID Supabase de l'utilisateur
    
    # URL de retour vers le Front-end (http://localhost:3000)
    return_url = data.get('return_url', 'http://localhost:3000') 
    
    if not user_id:
        return jsonify({"error": "User ID manquant."}), 400

    try:
        # Étape 1: Créer ou récupérer le client Stripe
        profile = supabase.table('profiles').select('stripe_customer_id').eq('id', user_id).single().execute().data
        customer_id = profile.get('stripe_customer_id') if profile else None
        
        if not customer_id:
            # Créer le client Stripe
            customer = stripe.Customer.create(metadata={'supabase_user_id': user_id})
            customer_id = customer.id
            # Mettre à jour immédiatement la DB Supabase avec le customer_id
            update_user_subscription(user_id, 'free', customer_id)

        # Étape 2: Créer la session de checkout Stripe
        checkout_session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=['card'],
            line_items=[
                {
                    'price': STRIPE_PRICE_ID,
                    'quantity': 1,
                },
            ],
            mode='subscription',
            success_url=f"{return_url}/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{return_url}/cancel",
            subscription_data={
                'trial_period_days': 7, # Essai gratuit de 7 jours
            }
        )
        return jsonify({'url': checkout_session.url})

    except Exception as e:
        print(f"❌ Erreur Stripe: {e}")
        return jsonify({'error': str(e)}), 403

# --- 4. LOGIQUE WEBHOOK (Appelée par Stripe) ---

@app.route('/webhook', methods=['POST'])
def webhook():
    """Gère les événements de paiement Stripe et met à jour Supabase."""
    event = None
    payload = request.data
    sig_header = request.headers.get('stripe-signature')
    
    try:
        # Vérification de la signature du webhook pour la sécurité
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        # Signature invalide
        return 'Invalid payload', 400
    except stripe.error.SignatureVerificationError as e:
        # Signature invalide
        return 'Invalid signature', 400

    # Gérer les événements importants pour la monétisation
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        customer_id = session.get('customer')
        
        # Le paiement est passé, l'abonnement commence (en 'trial' si période d'essai)
        if customer_id:
            # Récupérer l'ID Supabase stocké sur le client Stripe
            customer = stripe.Customer.retrieve(customer_id)
            user_id = customer.metadata.get('supabase_user_id')
            
            if user_id:
                # Si le statut est déjà 'active', on le laisse. Sinon, on le met à 'trial'.
                # Le statut 'trial' sera mis à jour en 'active' ou 'past_due' par l'événement customer.subscription.updated
                update_user_subscription(user_id, 'trial', customer_id) 

    elif event['type'] == 'customer.subscription.updated' or event['type'] == 'customer.subscription.deleted':
        subscription = event['data']['object']
        customer_id = subscription.get('customer')
        status = subscription.get('status')
        
        # Récupérer l'ID utilisateur Supabase (via le customer_id)
        customer = stripe.Customer.retrieve(customer_id)
        user_id = customer.metadata.get('supabase_user_id')
        
        # Le statut 'active' ou 'past_due' (si échec de paiement) ou 'canceled'
        if user_id:
            update_user_subscription(user_id, status)
        
    return jsonify(success=True)

# --- 5. LOGIQUE DE MONTAGE VIDEO (Le Cœur de l'IA - Appelée par le Front-end) ---

def check_user_quota(user_id):
    """Vérifie si l'utilisateur a le droit de lancer un montage (quota 1/1 ou abonnement actif)."""
    try:
        # Note: 'statut_d_abonnement' doit correspondre au nom de votre colonne
        profile = supabase.table('profiles').select('statut_d_abonnement, montages_restants').eq('id', user_id).single().execute().data
        
        if not profile:
            return False, "Profil utilisateur introuvable."
            
        status = profile['statut_d_abonnement']
        restants = profile['montages_restants']

        if status == 'active':
            return True, "Montage illimité (abonnement actif)."
        
        if status == 'trial' and restants >= 1:
            return True, f"Montage gratuit autorisé (Reste: {restants})."
            
        return False, "Limite de montage atteinte. Veuillez vous abonner pour continuer."

    except Exception as e:
        print(f"Erreur de quota: {e}")
        return False, "Erreur lors de la vérification du quota."

def process_video_montage(user_id, video_path, theme):
    """
    Simule la logique complexe de montage vidéo IA.
    Ceci est la fonction MVP qui sera remplacée par un vrai moteur IA (FFmpeg, Computer Vision, etc.).
    """
    print(f"🎬 Début du montage pour utilisateur {user_id} - Thème: {theme} - Fichier: {video_path}")
    
    # --- LOGIQUE IA MVP (Simulée) ---
    # Ici, vous auriez l'intégration de votre modèle Computer Vision / FFmpeg.
    time.sleep(5) # Simule le temps de traitement de 5 secondes
    
    montage_url = f"http://localhost:3000/videos/montage_{user_id}_{time.time()}.mp4"
    print(f"✅ Montage terminé. URL de la vidéo : {montage_url}")
    
    # Mettre à jour la base de données après un montage si l'utilisateur est en essai
    profile_data = supabase.table('profiles').select('statut_d_abonnement').eq('id', user_id).single().execute().data
    if profile_data and profile_data['statut_d_abonnement'] == 'trial':
        # Décrémente le quota de 1 à 0
        supabase.table('profiles').update({'montages_restants': 0}).eq('id', user_id).execute()
        print("Quota décrémenté.")
        
    return montage_url

@app.route('/montage-video', methods=['POST'])
def start_montage():
    """Point d'entrée pour le Front-end pour lancer un montage."""
    data = request.get_json()
    user_id = data.get('userId')
    video_path = data.get('videoPath')
    theme = data.get('theme')

    if not user_id or not video_path:
        return jsonify({"error": "Paramètres manquants."}), 400

    # 1. Vérification du quota
    can_mount, reason = check_user_quota(user_id)
    if not can_mount:
        return jsonify({"error": reason}), 403 # 403 Forbidden

    # 2. Lancer la tâche de montage
    montage_url = process_video_montage(user_id, video_path, theme)
    
    return jsonify({
        "message": "Montage lancé avec succès!", 
        "result_url_mock": montage_url
    }), 200

# --- 6. LANCEMENT DU SERVEUR ---

 # if __name__ == '__main__':
#     # Flask utilise le port 5000 par défaut
#     app.run(debug=True)