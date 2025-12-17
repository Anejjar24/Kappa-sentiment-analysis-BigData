#!/bin/bash

echo "🚀 Launching Spark Streaming Sentiment Analysis with ML"
echo "📊 Reading from: Kafka topic 'twitch-data-validated'"
echo "🤖 Using: 3-class Spark ML model (neg/neu/pos)"
echo "📈 Writing to: Elasticsearch index 'twitch_sentiment_analysis'"
echo "================================================================"

docker exec -it spark-master \
/opt/spark/bin/spark-submit \
--master spark://spark-master:7077 \
--packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0,org.elasticsearch:elasticsearch-spark-30_2.12:8.15.3 \
--conf spark.driver.extraJavaOptions="-Divy.cache.dir=/tmp -Divy.home=/tmp" \
--conf spark.executor.extraJavaOptions="-Divy.cache.dir=/tmp -Divy.home=/tmp" \
--conf spark.executorEnv.TRANSFORMERS_CACHE=/tmp/huggingface \
--conf spark.executorEnv.HF_HOME=/tmp/huggingface \
/opt/spark-apps/spark_streaming_with_model.py
