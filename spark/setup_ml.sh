#!/bin/bash

echo "======================================"
echo "Configuration Spark ML Pipeline"
echo "======================================"

# Couleurs pour le terminal
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Désactiver la conversion de chemin Git Bash pour tout le script
export MSYS_NO_PATHCONV=1
# 1. Créer les dossiers nécessaires
echo -e "\n${BLUE}[1/6] Création des dossiers...${NC}"



# 2. Créer le topic Kafka pour les résultats
echo -e "\n${BLUE}[2/6] Création du topic Kafka 'sentiment-results'...${NC}"
sleep 5  # Attendre que Kafka soit prêt

docker exec kafka kafka-topics --create \
  --topic sentiment-results \
  --bootstrap-server localhost:9092 \
  --partitions 3 \
  --replication-factor 1 2>/dev/null || echo "Topic déjà créé"

# Lister tous les topics
echo -e "\n${GREEN}Topics Kafka disponibles :${NC}"
docker exec kafka kafka-topics --list --bootstrap-server localhost:9092

# 3. Copier le dataset dans le conteneur Spark
echo -e "\n${BLUE}[3/6] Préparation du dataset...${NC}"
if [ -f "YoutubeCommentsDataSet.csv" ]; then
    # Copier dans /opt/spark-apps/ ET dans /opt/spark/work-dir/
    docker cp YoutubeCommentsDataSet.csv spark-master:/opt/spark-apps/
    docker cp YoutubeCommentsDataSet.csv spark-master:/opt/spark/work-dir/
    echo -e "${GREEN}✓ Dataset copié dans le conteneur Spark${NC}"
else
    echo -e "${YELLOW}⚠ Fichier YoutubeCommentsDataSet.csv non trouvé!${NC}"
    echo "Veuillez placer le fichier dans le répertoire courant."
    exit 1
fi

# 4. Entraîner le modèle
echo -e "\n${BLUE}[4/6] Entraînement du modèle ML...${NC}"
echo "Cela peut prendre quelques minutes..."

docker exec spark-master spark-submit \
  --master local[*] \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0 \
  /opt/spark-apps/train_sentiment_model.py

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Modèle entraîné avec succès!${NC}"
else
    echo -e "${YELLOW}⚠ Erreur lors de l'entraînement du modèle${NC}"
    exit 1
fi

