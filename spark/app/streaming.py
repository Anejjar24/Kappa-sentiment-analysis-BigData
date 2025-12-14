from pyspark.sql import SparkSession
from pyspark.ml import PipelineModel
from pyspark.sql.functions import (
    from_json, col, udf, struct, to_json, 
    current_timestamp, when, lower, regexp_replace
)
from pyspark.sql.types import StructType, StructField, StringType, TimestampType
import json

# Créer la session Spark avec les packages nécessaires
spark = SparkSession.builder \
    .appName("YouTubeSentimentStreaming") \
    .config("spark.jars.packages", 
            "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0,"
            "org.elasticsearch:elasticsearch-spark-30_2.12:8.11.0") \
    .config("spark.es.nodes", "elasticsearch") \
    .config("spark.es.port", "9200") \
    .config("spark.es.nodes.wan.only", "true") \
    .config("spark.streaming.stopGracefullyOnShutdown", "true") \
    .getOrCreate()

spark.sparkContext.setLogLevel("WARN")

print("=" * 70)
print("STREAMING SENTIMENT ANALYSIS - YOUTUBE COMMENTS")
print("=" * 70)

# 1. CHARGER LE MEILLEUR MODÈLE
print("\n[1/5] Chargement du modèle ML...")

# Essayer de charger le meilleur modèle (changez selon vos résultats)
MODEL_PATHS = [
   # "./models/Logistic_Regression_model",
   # "./models/Random_Forest_model",
    "./models/Naive_Bayes_model"
    #,
   # "./models/Decision_Tree_model"
]

model = None
model_name = None

for model_path in MODEL_PATHS:
    try:
        model = PipelineModel.load(model_path)
        model_name = model_path.split("/")[-1]
        print(f"✓ Modèle chargé: {model_name}")
        break
    except Exception as e:
        continue

if model is None:
    print("❌ Aucun modèle trouvé! Assurez-vous d'avoir entraîné les modèles.")
    spark.stop()
    exit(1)

# Charger les métadonnées si disponibles
try:
    with open("./models/comparison_results.json", "r") as f:
        results = json.load(f)
        for r in results:
            if model_name and model_name.replace("_model", "") in r.get("model", ""):
                print(f"   - Accuracy: {r.get('accuracy', 0):.4f}")
                print(f"   - F1-Score: {r.get('f1_score', 0):.4f}")
                break
except:
    print("   (Métadonnées non disponibles)")

# 2. DÉFINIR LE SCHÉMA DES DONNÉES KAFKA
print("\n[2/5] Configuration du schéma Kafka...")

# Schéma pour le topic 'tweets-validated' (provenant de votre API YouTube)
schema = StructType([
    StructField("id", StringType(), True),
    StructField("text", StringType(), True),
    StructField("timestamp", StringType(), True),
    StructField("source", StringType(), True)
])

print("✓ Schéma configuré pour le topic 'tweets-validated'")

# 3. LIRE LE STREAM DEPUIS KAFKA
print("\n[3/5] Connexion au stream Kafka...")
kafka_df = spark \
    .readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "kafka:9092") \
    .option("subscribe", "tweets-validated") \
    .option("startingOffsets", "latest") \
    .option("failOnDataLoss", "false") \
    .load()

print("✓ Connecté au topic 'tweets-validated'")

# 4. PARSER ET PRÉPARER LES DONNÉES
print("\n[4/5] Préparation des données pour prédiction...")

# Parser les données JSON
parsed_df = kafka_df.select(
    from_json(col("value").cast("string"), schema).alias("data")
).select("data.*")

# Nettoyer le texte exactement comme lors de l'entraînement
df_clean = parsed_df.withColumn(
    "comment_clean",
    regexp_replace(lower(col("text")), "[^a-zA-Z\\s]", "")
).filter(col("comment_clean") != "")

# 5. PRÉDICTION EN TEMPS RÉEL
print("\n[5/5] Application du modèle ML...")

# Appliquer le modèle
predictions_df = model.transform(df_clean)

# Convertir la prédiction numérique en label lisible
# Note: Les labels peuvent varier selon votre StringIndexer
# Vérifiez l'ordre: neutral=0, negative=1, positive=2 (ou autre)
final_df = predictions_df.select(
    col("id"),
    col("text"),
    col("timestamp").cast(TimestampType()),
    col("source"),
    when(col("prediction") == 0.0, "neutral")
    .when(col("prediction") == 1.0, "negative")
    .when(col("prediction") == 2.0, "positive")
    .otherwise("unknown")
    .alias("sentiment"),
    col("probability"),
    current_timestamp().alias("predicted_at")
)

print("✓ Pipeline de prédiction configuré")

# 6. ÉCRIRE DANS ELASTICSEARCH
print("\n📊 Configuration de la sortie vers Elasticsearch...")

def write_to_elasticsearch(batch_df, batch_id):
    """Écrire un batch dans Elasticsearch"""
    try:
        if batch_df.count() > 0:
            # Préparer les données pour ES
            es_df = batch_df.select(
                col("id"),
                col("text"),
                col("sentiment"),
                col("timestamp"),
                col("source"),
                col("predicted_at")
            )
            
            # Écrire dans Elasticsearch
            es_df.write \
                .format("org.elasticsearch.spark.sql") \
                .option("es.resource", "sentiment-predictions/_doc") \
                .option("es.mapping.id", "id") \
                .option("es.write.operation", "upsert") \
                .mode("append") \
                .save()
            
            print(f"✓ Batch {batch_id}: {batch_df.count()} prédictions envoyées à Elasticsearch")
    except Exception as e:
        print(f"❌ Erreur batch {batch_id}: {str(e)}")

query_elasticsearch = final_df \
    .writeStream \
    .foreachBatch(write_to_elasticsearch) \
    .option("checkpointLocation", "/tmp/checkpoint-es") \
    .start()

print("✓ Stream vers Elasticsearch 'sentiment-predictions' démarré")

# 7. ÉCRIRE DANS KAFKA (topic de sortie)
print("\n📤 Configuration de la sortie vers Kafka...")

kafka_output = final_df.select(
    col("id").alias("key"),
    to_json(struct(
        col("id"),
        col("text"),
        col("sentiment"),
        col("timestamp"),
        col("source"),
        col("predicted_at")
    )).alias("value")
)

query_kafka = kafka_output \
    .writeStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "kafka:9092") \
    .option("topic", "sentiment-results") \
    .option("checkpointLocation", "/tmp/checkpoint-kafka") \
    .start()

print("✓ Stream vers Kafka 'sentiment-results' démarré")

# 8. AFFICHER DANS LA CONSOLE (pour monitoring)
print("\n🖥️  Configuration de l'affichage console...")

console_query = final_df.select(
    "id", 
    "text", 
    "sentiment",
    "source",
    "predicted_at"
) \
    .writeStream \
    .outputMode("append") \
    .format("console") \
    .option("truncate", "false") \
    .option("numRows", "3") \
    .start()

print("✓ Affichage console activé")

# 9. STATISTIQUES EN TEMPS RÉEL
print("\n📈 Configuration des statistiques...")

from pyspark.sql.functions import window, count

stats_df = final_df \
    .withWatermark("predicted_at", "2 minutes") \
    .groupBy(
        window("predicted_at", "1 minute"),
        "sentiment"
    ) \
    .agg(count("*").alias("count")) \
    .select(
        col("window.start").alias("window_start"),
        col("window.end").alias("window_end"),
        col("sentiment"),
        col("count")
    )

query_stats = stats_df \
    .writeStream \
    .outputMode("update") \
    .format("console") \
    .option("truncate", "false") \
    .start()

print("✓ Statistiques en temps réel activées")

# 10. INFORMATIONS FINALES
print("\n" + "="*70)
print("🚀 PIPELINE STREAMING ACTIF")
print("="*70)
print("\n📊 Architecture du flux:")
print("  API YouTube → NiFi")
print("       ↓")
print("  Kafka Topic: tweets-validated")
print("       ↓")
print("  Spark Streaming + ML Model")
print("       ↓")
print("  ├→ Elasticsearch: sentiment-predictions")
print("  └→ Kafka Topic: sentiment-results")
print("\n")
print("ℹ️  Informations:")
print(f"  • Modèle utilisé: {model_name}")
print("  • Topic input: tweets-validated")
print("  • Topic output: sentiment-results")
print("  • Index Elasticsearch: sentiment-predictions")
print("\n")
print("📍 Services:")
print("  • Elasticsearch: http://localhost:9200")
print("  • Kibana: http://localhost:5601")
print("  • Spark UI: http://localhost:4040")
print("\n")
print("⏹️  Appuyez sur Ctrl+C pour arrêter")
print("="*70)

# Attendre la fin du streaming
try:
    spark.streams.awaitAnyTermination()
except KeyboardInterrupt:
    print("\n\n⏹️  Arrêt du streaming...")
    query_elasticsearch.stop()
    query_kafka.stop()
    query_console.stop()
    query_stats.stop()
    print("✓ Tous les streams arrêtés")
    spark.stop()
    print("✓ Session Spark fermée")