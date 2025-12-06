from kafka import KafkaProducer
import json
import time
import random
from datetime import datetime

# Créer le producteur Kafka
producer = KafkaProducer(
    bootstrap_servers=['localhost:9093'],
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

# Exemples de tweets (positifs et négatifs)
sample_tweets = [
    # Tweets positifs
    "I absolutely love this product! Best purchase ever!",
    "Amazing service, highly recommend to everyone!",
    "This is fantastic! Exceeded all my expectations!",
    "Great quality and fast delivery. Very satisfied!",
    "Wonderful experience from start to finish!",
    "Incredible value for money. Will buy again!",
    "Outstanding customer support. Thank you!",
    "Perfect! Exactly what I was looking for!",
    "Excellent quality and great price!",
    "Super happy with this purchase!",
    
    # Tweets négatifs
    "Terrible product, complete waste of money!",
    "Worst experience ever. Very disappointed!",
    "Poor quality, broke after one day.",
    "Horrible customer service. Never again!",
    "Not worth the price. Total disappointment.",
    "Awful product. Do not recommend!",
    "Very unhappy with this purchase.",
    "Bad quality and overpriced.",
    "Frustrated with the poor service.",
    "Regret buying this. Complete failure!"
]

users = ["@user1", "@user2", "@user3", "@user4", "@user5"]
locations = ["New York", "London", "Paris", "Tokyo", "Dubai", "Sydney"]

def generate_tweet():
    """Génère un tweet aléatoire"""
    return {
        "text": random.choice(sample_tweets),
        "user": random.choice(users),
        "timestamp": datetime.now().isoformat(),
        "location": random.choice(locations)
    }

print("Démarrage du producteur de tweets...")
print("Envoi vers Kafka topic: raw-tweets")
print("Appuyez sur Ctrl+C pour arrêter\n")

try:
    tweet_count = 0
    while True:
        # Générer un tweet
        tweet = generate_tweet()
        
        # Envoyer à Kafka
        producer.send('raw-tweets', value=tweet)
        
        tweet_count += 1
        print(f"[{tweet_count}] Envoyé: {tweet['text'][:50]}... | User: {tweet['user']}")
        
        # Attendre entre 2 et 5 secondes
        time.sleep(random.uniform(2, 5))
        
except KeyboardInterrupt:
    print(f"\nArrêt du producteur. {tweet_count} tweets envoyés.")
    producer.close()