#!/bin/bash

echo "======================================"
echo "Configuration Spark ML Pipeline"
echo "Comparaison de Modèles ML"
echo "======================================"

# Couleurs pour le terminal
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Désactiver la conversion de chemin Git Bash
export MSYS_NO_PATHCONV=1

# 1. Créer les dossiers nécessaires
echo -e "\n${BLUE}[1/7] Création des dossiers...${NC}"
mkdir -p models
echo -e "${GREEN}✓ Dossiers créés${NC}"

# 2. Vérifier que les conteneurs sont en cours d'exécution
echo -e "\n${BLUE}[2/7] Vérification des conteneurs Docker...${NC}"
if ! docker ps | grep -q spark-master; then
    echo -e "${RED}❌ Le conteneur spark-master n'est pas en cours d'exécution${NC}"
    echo "Veuillez démarrer les conteneurs avec: docker-compose up -d"
    exit 1
fi

if ! docker ps | grep -q kafka; then
    echo -e "${RED}❌ Le conteneur kafka n'est pas en cours d'exécution${NC}"
    echo "Veuillez démarrer les conteneurs avec: docker-compose up -d"
    exit 1
fi

echo -e "${GREEN}✓ Conteneurs actifs${NC}"

# 3. Créer le topic Kafka pour les résultats
echo -e "\n${BLUE}[3/7] Création du topic Kafka 'sentiment-results'...${NC}"
sleep 3  # Attendre que Kafka soit prêt

docker exec kafka kafka-topics --create \
  --topic sentiment-results \
  --bootstrap-server localhost:9092 \
  --partitions 3 \
  --replication-factor 1 2>/dev/null || echo "Topic déjà créé"

# Lister tous les topics
echo -e "\n${GREEN}Topics Kafka disponibles :${NC}"
docker exec kafka kafka-topics --list --bootstrap-server localhost:9092

# 4. Vérifier que le dataset existe
echo -e "\n${BLUE}[4/7] Vérification du dataset...${NC}"
if [ ! -f "YoutubeCommentsDataSet.csv" ]; then
    echo -e "${RED}❌ Fichier YoutubeCommentsDataSet.csv non trouvé!${NC}"
    echo "Veuillez placer le fichier dans le répertoire courant."
    exit 1
fi
echo -e "${GREEN}✓ Dataset trouvé${NC}"

# 5. Copier les fichiers dans le conteneur Spark
echo -e "\n${BLUE}[5/7] Copie des fichiers dans le conteneur...${NC}"

# Copier le dataset
docker cp YoutubeCommentsDataSet.csv spark-master:/opt/spark-apps/
docker cp YoutubeCommentsDataSet.csv spark-master:/opt/spark/work-dir/

# Copier le script de comparaison de modèles depuis le dossier app
if [ -f "app/multi.py" ]; then
    docker cp app/multi.py spark-master:/opt/spark-apps/
    echo -e "${GREEN}✓ Fichier app/multi.py copié${NC}"
else
    echo -e "${RED}❌ Fichier app/multi.py non trouvé!${NC}"
    echo "Structure attendue:"
    echo "  ├── setup_comparison.sh (script actuel)"
    echo "  ├── app/"
    echo "  │   └── multi.py"
    echo "  └── YoutubeCommentsDataSet.csv"
    exit 1
fi

# 6. Créer le dossier models dans le conteneur
echo -e "\n${BLUE}[6/7] Création des dossiers dans le conteneur...${NC}"
docker exec spark-master mkdir -p /opt/spark-apps/models
docker exec spark-master mkdir -p /opt/spark/work-dir/models
echo -e "${GREEN}✓ Dossiers créés dans le conteneur${NC}"

# 7. Lancer l'entraînement et la comparaison des modèles
echo -e "\n${BLUE}[7/7] Lancement de la comparaison des modèles ML...${NC}"
echo -e "${YELLOW}⏳ Cela peut prendre 10-15 minutes selon la taille du dataset...${NC}"
echo ""

# Choisir le fichier à exécuter
SCRIPT_NAME="multi.py"

docker exec spark-master spark-submit \
  --master local[*] \
  --driver-memory 4g \
  --executor-memory 4g \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0 \
  /opt/spark-apps/$SCRIPT_NAME

if [ $? -eq 0 ]; then
    echo -e "\n${GREEN}========================================${NC}"
    echo -e "${GREEN}✓ Comparaison terminée avec succès!${NC}"
    echo -e "${GREEN}========================================${NC}"
    
    # Récupérer les résultats
    echo -e "\n${BLUE}Récupération des résultats...${NC}"
    
    # Essayer de copier depuis différents chemins possibles
    docker cp spark-master:/opt/spark-apps/models/comparison_results.json ./models/ 2>/dev/null || \
    docker cp spark-master:/opt/spark/work-dir/models/comparison_results.json ./models/ 2>/dev/null || \
    echo -e "${YELLOW}⚠ Fichier de résultats non trouvé (peut être normal)${NC}"
    
    # Afficher les résultats s'ils existent
    if [ -f "./models/comparison_results.json" ]; then
        echo -e "\n${GREEN}📊 Résultats de la comparaison :${NC}"
        cat ./models/comparison_results.json
    fi
    
else
    echo -e "\n${RED}========================================${NC}"
    echo -e "${RED}❌ Erreur lors de l'entraînement${NC}"
    echo -e "${RED}========================================${NC}"
    exit 1
fi

echo -e "\n${BLUE}======================================"
echo "Configuration terminée!"
echo -e "======================================${NC}"