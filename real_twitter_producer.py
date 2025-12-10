"""
Producteur Twitter réel avec l'API Twitter v2
Installer: pip install tweepy
"""

import tweepy
from kafka import KafkaProducer
import json
from datetime import datetime

# Configuration Twitter API v2
BEARER_TOKEN = "AAAAAAAAAAAAAAAAAAAAAP1%2F5wEAAAAAkTshhL952S%2Fv08s3uRJE3KAGox0%3D5zXn5NzR1CvkLs6tNK3H9lPmbVOnrJmoGQeXEZom9lhyihQQZA"
# Configuration Kafka
producer = KafkaProducer(
    bootstrap_servers=['localhost:9093'],
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

class TwitterStreamListener(tweepy.StreamingClient):
    
    def on_tweet(self, tweet):
        try:
            # Extraire les informations
            tweet_data = {
                "text": tweet.text,
                "user": tweet.author_id,
                "timestamp": datetime.now().isoformat(),
                "location": getattr(tweet, 'geo', {}).get('place_id', 'Unknown')
            }
            
            # Envoyer à Kafka
            producer.send('raw-tweets', value=tweet_data)
            print(f"Tweet envoyé: {tweet.text[:50]}...")
            
        except Exception as e:
            print(f"Erreur: {e}")
    
    def on_error(self, status):
        print(f"Erreur Twitter API: {status}")
        return False

# Créer le stream
stream = TwitterStreamListener(bearer_token=BEARER_TOKEN)

# Ajouter des règles de filtrage
# Exemple: tweets mentionnant certains mots-clés
stream.add_rules(tweepy.StreamRule("python OR machine learning OR AI"))

# Démarrer le streaming
print("Démarrage du streaming Twitter...")
stream.filter(tweet_fields=["author_id", "geo", "created_at"])