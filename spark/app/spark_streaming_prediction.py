from pyspark.sql import SparkSession
from pyspark.ml import PipelineModel
from pyspark.sql.functions import from_json, col, to_json, struct, current_timestamp
from pyspark.sql.types import StructType, StructField, StringType
import json

# Créer la session Spark avec les packages nécessaires
spark = SparkSession.builder \
    .appName("RealTimeSentimentPrediction") \
    .config("spark.jars.packages", 
            "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0,"
            "org.elasticsearch:elasticsearch-spark-30_2.12:8.11.0") \
    .config("spark.streaming.stopGracefullyOnShutdown", "true") \
    .getOrCreate()

spark.sparkContext.setLogLevel("WARN")

print("=" * 60)
print("DÉMARRAGE DU STREAMING AVEC PRÉDICTION EN TEMPS RÉEL")
print("=" * 60)

# 1. CHARGER LE MODÈLE PRÉ-ENTRAÎNÉ
print("\n[1/4] Chargement du modèle pré-entraîné...")
model_path = "./models/sentiment_model"
model = PipelineModel.load(model_path)
print("✓ Modèle chargé avec succès!")

# Charger les métadonnées
with open("./models/model_metadata.json", "r") as f:
    metadata = json.load(f)
    print(f"   - Accuracy du modèle : {metadata['accuracy']:.4f}")
    print(f"   - F1-Score : {metadata['f1_score']:.4f}")

# 2. DÉFINIR LE SCHÉMA DES DONNÉES KAFKA
print("\n[2/4] Configuration de la connexion Kafka...")
schema = StructType([
    StructField("id", StringType(), True),
    StructField("text", StringType(), True),
    StructField("timestamp", StringType(), True),
    StructField("source", StringType(), True)
])

# 3. LIRE LE STREAM DEPUIS KAFKA
print("\n[3/4] Connexion au topic Kafka 'tweets-validated'...")
kafka_df = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "kafka:9092") \
    .option("subscribe", "tweets-validated") \
    .option("startingOffsets", "latest") \
    .option("failOnDataLoss", "false") \
    .load()

# Parser les données JSON
parsed_df = kafka_df.select(
    from_json(col("value").cast("string"), schema).alias("data")
).select("data.*")

# 4. PRÉPARER LES DONNÉES POUR LA PRÉDICTION
print("\n[4/4] Application du modèle pour prédiction en temps réel...")

# Renommer la colonne pour correspondre au modèle
prepared_df = parsed_df.select(
    col("id"),
    col("text").alias("comment_clean"),
    col("timestamp"),
    col("source")
)

# Appliquer le modèle pour faire des prédictions
predictions_df = model.transform(prepared_df)

# Convertir l'index de prédiction en label lisible
from pyspark.sql.functions import when

final_df = predictions_df.select(
    col("id"),
    col("comment_clean").alias("text"),
    col("timestamp"),
    col("source"),
    when(col("prediction") == 0.0, "neutral")
    .when(col("prediction") == 1.0, "negative")
    .when(col("prediction") == 2.0, "positive")
    .alias("sentiment"),
    col("probability"),
    current_timestamp().alias("predicted_at")
)

# 5. ÉCRIRE LES RÉSULTATS DANS ELASTICSEARCH
print("\n📊 Envoi des prédictions vers Elasticsearch...")

es_query = final_df.select(
    col("id"),
    col("text"),
    col("sentiment"),
    col("timestamp"),
    col("source"),
    col("predicted_at")
).writeStream \
    .outputMode("append") \
    .format("org.elasticsearch.spark.sql") \
    .option("es.nodes", "elasticsearch") \
    .option("es.port", "9200") \
    .option("es.resource", "sentiment-predictions/_doc") \
    .option("es.mapping.id", "id") \
    .option("checkpointLocation", "/tmp/checkpoint-es") \
    .start()

# 6. ÉCRIRE AUSSI DANS LA CONSOLE (pour debugging)
console_query = final_df.writeStream \
    .outputMode("append") \
    .format("console") \
    .option("truncate", "false") \
    .option("numRows", "5") \
    .start()

# 7. OPTIONNEL : Écrire dans un nouveau topic Kafka pour d'autres consommateurs
kafka_output_df = final_df.select(
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

kafka_query = kafka_output_df.writeStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "kafka:9092") \
    .option("topic", "sentiment-results") \
    .option("checkpointLocation", "/tmp/checkpoint-kafka") \
    .start()

print("\n" + "=" * 60)
print("✓ STREAMING ACTIF - Prédictions en cours...")
print("=" * 60)
print("\n📍 Destinations des résultats :")
print("   1. Elasticsearch : http://localhost:9200/sentiment-predictions")
print("   2. Kafka Topic   : sentiment-results")
print("   3. Console       : Affichage en temps réel")
print("\n⏸️  Appuyez sur Ctrl+C pour arrêter...\n")

# Attendre la fin du streaming
spark.streams.awaitAnyTermination()