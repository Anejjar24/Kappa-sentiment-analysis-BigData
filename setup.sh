#!/bin/bash

echo "======================================"
echo "Configuration Architecture Kappa"
echo "======================================"

# Installer les dépendances Python
echo "Installation des dépendances Python..."
pip3 install -r requirements.txt

# Créer les topics Kafka
echo "Création des topics Kafka..."
sleep 30  # Attendre que Kafka soit prêt

docker exec kafka kafka-topics --create \
  --topic raw-tweets \
  --bootstrap-server localhost:9092 \
  --partitions 3 \
  --replication-factor 1

docker exec kafka kafka-topics --create \
  --topic tweets-validated \
  --bootstrap-server localhost:9092 \
  --partitions 3 \
  --replication-factor 1
# 3. Créer le topic Kafka pour les résultats
sleep 30  # Attendre que Kafka soit prêt

docker exec kafka kafka-topics --create \
  --topic sentiment-results \
  --bootstrap-server localhost:9092 \
  --partitions 3 \
  --replication-factor 1 2>/dev/null || echo "Topic déjà créé"
# Lister les topics
echo "Topics Kafka créés:"
docker exec kafka kafka-topics --list --bootstrap-server localhost:9092

# Créer l'index ElasticSearch
echo "Configuration ElasticSearch..."
sleep 10

curl -X PUT "http://localhost:9200/sentiment-analysis" -H 'Content-Type: application/json' -d'
{
  "settings": {
    "number_of_shards": 1,
    "number_of_replicas": 0
  },
  "mappings": {
    "properties": {
      "text": { "type": "text" },
      "user": { "type": "keyword" },
      "timestamp": { "type": "date" },
      "location": { "type": "keyword" },
      "sentiment": { "type": "float" },
      "sentiment_label": { "type": "keyword" },
      "confidence": { "type": "float" },
      "processed_time": { "type": "date" }
    }
  }
}
'

echo ""
echo "======================================"
echo "Configuration terminée!"
echo "======================================"
echo ""
echo "Accès aux interfaces:"
echo "- NiFi: http://localhost:8080 (admin/adminadminadmin)"
echo "- Spark Master: http://localhost:8081"
echo "- Kibana: http://localhost:5601"
echo "- ElasticSearch: http://localhost:9200"
echo ""
echo "Étapes suivantes:"
echo "1. Configurer le flow dans NiFi"
echo "2. Lancer le producteur: python3 twitter_producer.py"
echo "3. Soumettre l'application Spark"
echo "4. Visualiser dans Kibana"
echo ""

echo ""
echo "======================================"
echo "Configuration terminée!"
echo "======================================"
echo ""
echo "Accès aux interfaces:"
echo "- NiFi: http://localhost:8080 (admin/adminadminadmin)"

