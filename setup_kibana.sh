#!/bin/bash

echo "Configuration de Kibana..."

# Créer le Data View
curl -X POST "http://localhost:5601/api/data_views/data_view" \
  -H "kbn-xsrf: true" \
  -H "Content-Type: application/json" \
  -d '{
    "data_view": {
      "title": "sentiment-analysis*",
      "name": "Sentiment Analysis",
      "timeFieldName": "processed_time"
    }
  }'

echo ""
echo "======================================"
echo "Kibana configuré!"
echo "======================================"
echo ""
echo "Créer des visualisations dans Kibana:"
echo ""
echo "1. Dashboard - Sentiment Analysis Real-Time"
echo "   - Pie Chart: Distribution des sentiments"
echo "   - Line Chart: Sentiments au fil du temps"
echo "   - Data Table: Derniers tweets analysés"
echo "   - Metric: Nombre total de tweets"
echo "   - Tag Cloud: Utilisateurs les plus actifs"
echo ""
echo "2. Accéder à Kibana: http://localhost:5601"
echo "3. Menu > Analytics > Dashboard"
echo "4. Create dashboard"
echo ""