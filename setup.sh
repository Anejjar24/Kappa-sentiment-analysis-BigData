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

# Lister les topics
echo "Topics Kafka créés:"
docker exec kafka kafka-topics --list --bootstrap-server localhost:9092



echo ""
echo "======================================"
echo "Configuration terminée!"
echo "======================================"
echo ""
echo "Accès aux interfaces:"
echo "- NiFi: http://localhost:8080 (admin/adminadminadmin)"

