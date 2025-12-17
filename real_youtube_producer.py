"""
Producteur YouTube avec l'API YouTube Data API v3
Installer: pip install google-api-python-client kafka-python
"""

from googleapiclient.discovery import build
from kafka import KafkaProducer
import json
from datetime import datetime
import time

# Configuration YouTube API v3
YOUTUBE_API_KEY = "AIzaSyDm6RDg8y2VWlHnsYlPRyjm6q7ql-kH8ew"  # À remplacer par votre clé API

# Configuration Kafka
producer = KafkaProducer(
    bootstrap_servers=['localhost:9093'],
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

# Initialiser le client YouTube
youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)

def get_video_comments(video_id, max_results=100):
    """
    Récupère les commentaires d'une vidéo YouTube
    """
    try:
        request = youtube.commentThreads().list(
            part="snippet",
            videoId=video_id,
            maxResults=max_results,
            textFormat="plainText"
        )
        response = request.execute()
        
        return response.get('items', [])
    
    except Exception as e:
        print(f"Erreur lors de la récupération des commentaires: {e}")
        return []

def search_videos(query, max_results=10):
    """
    Recherche des vidéos YouTube basées sur une requête
    """
    try:
        request = youtube.search().list(
            part="id,snippet",
            q=query,
            type="video",
            maxResults=max_results,
            order="date"  # Les plus récentes d'abord
        )
        response = request.execute()
        
        video_ids = [item['id']['videoId'] for item in response.get('items', [])]
        return video_ids
    
    except Exception as e:
        print(f"Erreur lors de la recherche de vidéos: {e}")
        return []

def process_comment(comment_item):
    """
    Traite un commentaire et l'envoie à Kafka
    """
    try:
        snippet = comment_item['snippet']['topLevelComment']['snippet']
        
        # Créer la structure similaire aux tweets
        comment_data = {
            "text": snippet['textDisplay'],
            "user": snippet['authorDisplayName'],
            "timestamp": snippet['publishedAt'],
            "location": snippet.get('authorChannelId', {}).get('value', 'Unknown')
        }
        
        # Envoyer à Kafka (même topic que les tweets pour compatibilité)
        producer.send('raw-tweets', value=comment_data)
        print(f"Commentaire envoyé: {comment_data['text'][:50]}...")
        
    except Exception as e:
        print(f"Erreur lors du traitement du commentaire: {e}")

def stream_youtube_comments(keywords, interval=60):
    """
    Simule un streaming en récupérant périodiquement les nouveaux commentaires
    
    Args:
        keywords: Liste de mots-clés pour la recherche (ex: ["python", "machine learning"])
        interval: Intervalle en secondes entre chaque récupération
    """
    print(f"Démarrage du streaming YouTube pour: {keywords}")
    processed_comments = set()  # Pour éviter les doublons
    
    while True:
        try:
            # Rechercher des vidéos pour chaque mot-clé
            for keyword in keywords:
                print(f"\nRecherche de vidéos pour: {keyword}")
                video_ids = search_videos(keyword, max_results=5)
                
                # Récupérer les commentaires de chaque vidéo
                for video_id in video_ids:
                    print(f"Récupération des commentaires pour la vidéo: {video_id}")
                    comments = get_video_comments(video_id, max_results=50)
                    
                    for comment in comments:
                        comment_id = comment['id']
                        
                        # Éviter les doublons
                        if comment_id not in processed_comments:
                            process_comment(comment)
                            processed_comments.add(comment_id)
                    
                    # Pause pour respecter les limites de l'API
                    time.sleep(1)
            
            print(f"\nAttente de {interval} secondes avant la prochaine récupération...")
            time.sleep(interval)
            
        except KeyboardInterrupt:
            print("\nArrêt du streaming...")
            break
        except Exception as e:
            print(f"Erreur dans la boucle principale: {e}")
            time.sleep(interval)

if __name__ == "__main__":
    # Définir les mots-clés (similaire aux règles Twitter)
    keywords = [
    "iPhone review",      # Beaucoup d'avis détaillés
    "Tesla news",         # Opinions très polarisées
    "AI tutorial",        # Mix de frustration/satisfaction
    "crypto crash",       # Sentiments négatifs forts
    "best laptop 2024"    # Comparaisons et opinions
    ]
    
    # Lancer le streaming
    # interval=60 signifie une vérification toutes les 60 secondes
    stream_youtube_comments(keywords, interval=60)