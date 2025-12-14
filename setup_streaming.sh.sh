#!/bin/bash

echo "========================================"
echo "CONFIGURATION STREAMING YOUTUBE COMMENTS"
echo "API YouTube → NiFi → Kafka → Spark → ES"
echo "========================================"

# Couleurs
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

export MSYS_NO_PATHCONV=1

# Fonction pour vérifier si un service est prêt
check_service() {
    local service=$1
    local url=$2
    local max_attempts=20
    local attempt=0
    
    echo -e "${YELLOW}Vérification de $service...${NC}"
    while [ $attempt -lt $max_attempts ]; do
        if curl -sf "$url" > /dev/null 2>&1; then
            echo -e "${GREEN}✓ $service est prêt!${NC}"
            return 0
        fi
        attempt=$((attempt + 1))
        sleep 2
    done
    
    echo -e "${RED}❌ $service non accessible${NC}"
    return 1
}

# 1. Vérifier que les modèles sont entraînés
echo -e "\n${BLUE}[1/6] Vérification des modèles ML...${NC}"
if [ ! -d "models/Logistic_Regression_model" ] && \
   [ ! -d "models/Random_Forest_model" ] && \
   [ ! -d "models/Naive_Bayes_model" ] && \
   [ ! -d "models/Decision_Tree_model" ]; then
    echo -e "${RED}❌ Aucun modèle trouvé!${NC}"
    echo "Veuillez d'abord entraîner les modèles avec: ./setup_comparison.sh"
    exit 1
fi
echo -e "${GREEN}✓ Modèles ML trouvés${NC}"

# 2. Vérifier les conteneurs Docker
echo -e "\n${BLUE}[2/6] Vérification des conteneurs...${NC}"

# Vérifier les conteneurs essentiels
REQUIRED_CONTAINERS=("kafka" "spark-master" "elasticsearch")
MISSING_CONTAINERS=()

for container in "${REQUIRED_CONTAINERS[@]}"; do
    if ! docker ps | grep -q "$container"; then
        MISSING_CONTAINERS+=("$container")
    fi
done

if [ ${#MISSING_CONTAINERS[@]} -gt 0 ]; then
    echo -e "${YELLOW}⚠ Conteneurs manquants: ${MISSING_CONTAINERS[*]}${NC}"
    echo -e "${BLUE}Démarrage des conteneurs...${NC}"
    docker-compose up -d
    sleep 15
else
    echo -e "${GREEN}✓ Tous les conteneurs sont actifs${NC}"
fi

# 3. Attendre que les services soient prêts
echo -e "\n${BLUE}[3/6] Attente des services...${NC}"
check_service "Elasticsearch" "http://localhost:9200"
sleep 5

# 4. Vérifier les topics Kafka
echo -e "\n${BLUE}[4/6] Vérification des topics Kafka...${NC}"

# Lister les topics existants
echo -e "${GREEN}Topics Kafka disponibles:${NC}"
docker exec kafka kafka-topics --list --bootstrap-server localhost:9092

# Créer le topic sentiment-results s'il n'existe pas
docker exec kafka kafka-topics --create \
  --topic sentiment-results \
  --bootstrap-server localhost:9092 \
  --partitions 3 \
  --replication-factor 1 2>/dev/null && \
  echo -e "${GREEN}✓ Topic 'sentiment-results' créé${NC}" || \
  echo -e "${YELLOW}Topic 'sentiment-results' existe déjà${NC}"

# Vérifier que le topic d'entrée existe
if docker exec kafka kafka-topics --list --bootstrap-server localhost:9092 | grep -q "tweets-validated"; then
    echo -e "${GREEN}✓ Topic 'tweets-validated' trouvé${NC}"
else
    echo -e "${YELLOW}⚠ Topic 'tweets-validated' non trouvé${NC}"
    echo "Assurez-vous que NiFi envoie des données vers ce topic"
fi

# 5. Copier les fichiers vers Spark
echo -e "\n${BLUE}[5/6] Copie des fichiers vers Spark...${NC}"

# Copier le script de streaming
if [ -f "app/streaming.py" ]; then
    docker cp app/streaming.py spark-master:/opt/spark-apps/
    echo -e "${GREEN}✓ streaming.py copié${NC}"
else
    echo -e "${RED}❌ app/streaming.py non trouvé!${NC}"
    exit 1
fi

# Copier les modèles
echo -e "${BLUE}Copie des modèles ML...${NC}"
docker cp models spark-master:/opt/spark-apps/
echo -e "${GREEN}✓ Modèles copiés${NC}"

# 6. Configuration Elasticsearch
echo -e "\n${BLUE}[6/6] Configuration de l'index Elasticsearch...${NC}"
sleep 3

# Créer l'index sentiment-predictions
curl -X PUT "http://localhost:9200/sentiment-predictions" \
  -H 'Content-Type: application/json' \
  -d '{
    "settings": {
      "number_of_shards": 1,
      "number_of_replicas": 0
    },
    "mappings": {
      "properties": {
        "id": { "type": "keyword" },
        "text": { 
          "type": "text",
          "fields": {
            "keyword": { "type": "keyword" }
          }
        },
        "sentiment": { "type": "keyword" },
        "source": { "type": "keyword" },
        "timestamp": { "type": "date" },
        "predicted_at": { "type": "date" }
      }
    }
  }' 2>/dev/null && \
  echo -e "\n${GREEN}✓ Index 'sentiment-predictions' créé${NC}" || \
  echo -e "\n${YELLOW}Index 'sentiment-predictions' existe déjà${NC}"

# Vérifier les index
echo -e "\n${GREEN}Index Elasticsearch disponibles:${NC}"
curl -s "http://localhost:9200/_cat/indices?v" | grep -E "sentiment|health"

# 7. Démarrer Spark Streaming
echo -e "\n${BLUE}═══════════════════════════════════════${NC}"
echo -e "${BLUE}DÉMARRAGE DU SPARK STREAMING${NC}"
echo -e "${BLUE}═══════════════════════════════════════${NC}"
echo -e "\n${YELLOW}Le streaming va traiter les commentaires du topic 'tweets-validated'${NC}"
echo -e "${YELLOW}Assurez-vous que NiFi envoie des données vers Kafka${NC}\n"

read -p "Voulez-vous démarrer le streaming maintenant? (y/n): " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "\n${BLUE}Lancement du Spark Streaming...${NC}"
    
    # Option 1: Lancer en mode interactif (voir les logs)
    docker exec -it spark-master spark-submit \
      --master local[*] \
      --driver-memory 4g \
      --executor-memory 4g \
      --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0,org.elasticsearch:elasticsearch-spark-30_2.12:8.11.0 \
      /opt/spark-apps/streaming.py
    
    # Option 2: Lancer en arrière-plan (décommenter si nécessaire)
    # docker exec -d spark-master spark-submit \
    #   --master local[*] \
    #   --driver-memory 4g \
    #   --executor-memory 4g \
    #   --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0,org.elasticsearch:elasticsearch-spark-30_2.12:8.11.0 \
    #   /opt/spark-apps/streaming.py
    # 
    # echo -e "${GREEN}✓ Spark Streaming démarré en arrière-plan${NC}"
    # echo -e "Pour voir les logs: ${YELLOW}docker logs -f spark-master${NC}"
else
    echo -e "${YELLOW}Streaming non démarré${NC}"
fi

# 8. Instructions finales
echo -e "\n${BLUE}═══════════════════════════════════════${NC}"
echo -e "${GREEN}CONFIGURATION TERMINÉE${NC}"
echo -e "${BLUE}═══════════════════════════════════════${NC}"

echo -e "\n${BLUE}📊 Services disponibles:${NC}"
echo -e "  • Spark UI:          ${YELLOW}http://localhost:8080${NC}"
echo -e "  • Spark Jobs:        ${YELLOW}http://localhost:4040${NC}"
echo -e "  • Elasticsearch:     ${YELLOW}http://localhost:9200${NC}"
echo -e "  • Kibana:            ${YELLOW}http://localhost:5601${NC}"

echo -e "\n${BLUE}📋 Topics Kafka:${NC}"
echo -e "  • Input:  ${YELLOW}tweets-validated${NC} (depuis NiFi + API YouTube)"
echo -e "  • Output: ${YELLOW}sentiment-results${NC} (prédictions ML)"

echo -e "\n${BLUE}📈 Index Elasticsearch:${NC}"
echo -e "  • ${YELLOW}sentiment-predictions${NC} (stockage des prédictions)"

echo -e "\n${BLUE}🔧 Commandes utiles:${NC}"
echo -e "  • Démarrer streaming:  ${YELLOW}docker exec -it spark-master spark-submit --master local[*] --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0,org.elasticsearch:elasticsearch-spark-30_2.12:8.11.0 /opt/spark-apps/streaming.py${NC}"
echo -e "  • Voir logs Spark:     ${YELLOW}docker logs -f spark-master${NC}"
echo -e "  • Compter messages:    ${YELLOW}curl http://localhost:9200/sentiment-predictions/_count?pretty${NC}"
echo -e "  • Lire topic Kafka:    ${YELLOW}docker exec kafka kafka-console-consumer --bootstrap-server localhost:9092 --topic sentiment-results --from-beginning${NC}"

echo -e "\n${BLUE}📊 Configuration Kibana:${NC}"
echo -e "  1. Ouvrir ${YELLOW}http://localhost:5601${NC}"
echo -e "  2. Aller dans Management → Index Patterns"
echo -e "  3. Créer pattern: ${YELLOW}sentiment-predictions${NC}"
echo -e "  4. Champ de temps: ${YELLOW}predicted_at${NC}"
echo -e "  5. Créer des visualisations dans Dashboard"

echo -e "\n${GREEN}✓ Prêt à traiter les commentaires YouTube en temps réel!${NC}"
echo -e "${BLUE}═══════════════════════════════════════${NC}\n"