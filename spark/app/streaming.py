from pyspark.sql import SparkSession
from pyspark.ml import PipelineModel
from pyspark.sql.functions import (
    from_json, col, struct, to_json,
    current_timestamp, lower, regexp_replace, expr
)
from pyspark.sql.types import StructType, StructField, StringType
import json

# =========================
# Spark Session
# =========================
spark = SparkSession.builder \
    .appName("YouTubeSentimentStreaming") \
    .config("spark.es.nodes", "elasticsearch") \
    .config("spark.es.port", "9200") \
    .config("spark.es.nodes.wan.only", "false") \
    .config("spark.streaming.stopGracefullyOnShutdown", "true") \
    .getOrCreate()

spark.sparkContext.setLogLevel("WARN")

print("=" * 70)
print("STREAMING SENTIMENT ANALYSIS - NAIVE BAYES")
print("=" * 70)

# =========================
# 1. Charger Naive Bayes
# =========================
model_path = "./models/Naive_Bayes_model"
model = PipelineModel.load(model_path)
model_name = "Naive_Bayes_model"

# CORRECTION : Extraire les labels depuis StringIndexerModel
# Le pipeline contient : [CountVectorizer, IDF, StringIndexer, NaiveBayes]
# Les labels sont dans le StringIndexer (3ème étape, index 2)
string_indexer = None
for stage in model.stages:
    if hasattr(stage, 'labels'):  # Trouver le StringIndexerModel
        string_indexer = stage
        break

if string_indexer is None:
    # Fallback : définir manuellement les labels
    print("⚠ StringIndexer non trouvé, utilisation des labels par défaut")
    labels = ["negative", "neutral", "positive"]
else:
    labels = string_indexer.labels

print("✓ Modèle chargé:", model_name)
print("✓ Ordre des labels:", labels)

# =========================
# 2. Schema Kafka
# =========================
schema = StructType([
    StructField("text", StringType(), True),
    StructField("user", StringType(), True),
    StructField("timestamp", StringType(), True),
    StructField("location", StringType(), True)
])

# =========================
# 3. Lire depuis Kafka
# =========================
kafka_df = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "kafka:9092") \
    .option("subscribe", "tweets-validated") \
    .option("startingOffsets", "earliest") \
    .load()

parsed_df = kafka_df.select(
    from_json(col("value").cast("string"), schema).alias("data")
).select("data.*")

# =========================
# 4. Nettoyage
# =========================
df_clean = parsed_df.withColumn(
    "comment_clean",
    regexp_replace(lower(col("text")), "[^a-zA-Z\\s]", "")
)

# =========================
# 5. Prédiction
# =========================
predictions_df = model.transform(df_clean)

# Construire l'expression SQL pour mapper prediction -> label
labels_sql = ",".join([f"'{l}'" for l in labels])

final_df = predictions_df.select(
    col("text"),
    col("user"),
    col("timestamp"),
    col("location").alias("source"),
    expr(f"array({labels_sql})[int(prediction)]").alias("sentiment"),
    current_timestamp().alias("predicted_at")
)

# =========================
# 6. Elasticsearch
# =========================
def write_to_elasticsearch(batch_df, batch_id):
    if batch_df.count() > 0:
        try:
            batch_df.write \
                .format("org.elasticsearch.spark.sql") \
                .option("es.resource", "sentiment-predictions") \
                .option("es.write.operation", "index") \
                .option("es.mapping.id", "timestamp") \
                .mode("append") \
                .save()
            print(f"✓ Batch {batch_id} : {batch_df.count()} documents envoyés à Elasticsearch")
        except Exception as e:
            print(f"❌ Erreur Batch {batch_id}: {e}")
    else:
        print(f"⚠ Batch {batch_id} vide, rien à envoyer")

query_es = final_df.writeStream \
    .foreachBatch(write_to_elasticsearch) \
    .option("checkpointLocation", "/tmp/checkpoint-es") \
    .start()

# =========================
# 7. Kafka output
# =========================
query_kafka = final_df.selectExpr(
    "to_json(struct(*)) AS value"
).writeStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "kafka:9092") \
    .option("topic", "sentiment-results") \
    .option("checkpointLocation", "/tmp/checkpoint-kafka") \
    .start()

# =========================
# 8. Console
# =========================
console_query = final_df.writeStream \
    .format("console") \
    .outputMode("append") \
    .option("truncate", "false") \
    .start()

# =========================
# 9. Await
# =========================
print("\n" + "=" * 70)
print("✓ STREAMING DÉMARRÉ - En attente de messages Kafka...")
print("=" * 70 + "\n")

try:
    spark.streams.awaitAnyTermination()
except KeyboardInterrupt:
    print("\n⚠ Arrêt du streaming...")
    query_es.stop()
    query_kafka.stop()
    console_query.stop()
    spark.stop()
    print("✓ Streaming arrêté proprement")