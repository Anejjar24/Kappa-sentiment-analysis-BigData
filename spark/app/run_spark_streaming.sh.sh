#!/bin/bash

echo "Soumission de l'application Spark Streaming..."

docker exec spark-master spark-submit \
  --master spark://spark-master:7077 \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0,org.elasticsearch:elasticsearch-spark-30_2.12:8.11.0 \
  --conf spark.es.nodes=elasticsearch \
  --conf spark.es.port=9200 \
  --conf spark.es.nodes.wan.only=true \
  --driver-memory 1g \
  --executor-memory 1g \
  /opt/spark-apps/sentiment_analysis_streaming.py

echo "Application Spark lancée!"