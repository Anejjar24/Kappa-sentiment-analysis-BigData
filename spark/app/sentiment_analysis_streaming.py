from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.types import *
from pyspark.ml import PipelineModel
from pyspark.ml.feature import Tokenizer, StopWordsRemover, HashingTF, IDF
from pyspark.ml.classification import LogisticRegression
from pyspark.ml import Pipeline
import json

# Créer la session Spark
spark = SparkSession.builder \
    .appName("KappaSentimentAnalysis") \
    .config("spark.jars.packages", 
            "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0,"
            "org.elasticsearch:elasticsearch-spark-30_2.12:8.11.0") \
    .config("spark.es.nodes", "elasticsearch") \
    .config("spark.es.port", "9200") \
    .config("spark.es.nodes.wan.only", "true") \
    .getOrCreate()

spark.sparkContext.setLogLevel("WARN")

# Schéma des données entrantes
schema = StructType([
    StructField("text", StringType(), True),
    StructField("user", StringType(), True),
    StructField("timestamp", StringType(), True),
    StructField("location", StringType(), True)
])

# Lire depuis Kafka
kafka_df = spark \
    .readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "kafka:9092") \
    .option("subscribe", "tweets-validated") \
    .option("startingOffsets", "latest") \
    .load()

# Parser les messages JSON
parsed_df = kafka_df.select(
    from_json(col("value").cast("string"), schema).alias("data")
).select("data.*")

# Ajouter un ID unique
parsed_df = parsed_df.withColumn("id", monotonically_increasing_id())

# Fonction pour entraîner le modèle (à exécuter une fois)
def train_sentiment_model():
    print("Entraînement du modèle de sentiment...")
    
    # Données d'entraînement exemples (remplacer par un vrai dataset)
    training_data = [
        (0, "I hate this product it's terrible"),
        (0, "This is the worst experience ever"),
        (0, "Disappointed and frustrated with the service"),
        (1, "This is amazing I love it"),
        (1, "Excellent product highly recommend"),
        (1, "Great experience very satisfied"),
        (0, "Poor quality waste of money"),
        (1, "Outstanding service will buy again"),
        (0, "Not worth the price terrible quality"),
        (1, "Fantastic product exceeded expectations")
    ]
    
    train_df = spark.createDataFrame(training_data, ["label", "text"])
    
    # Pipeline ML
    tokenizer = Tokenizer(inputCol="text", outputCol="words")
    remover = StopWordsRemover(inputCol="words", outputCol="filtered")
    hashingTF = HashingTF(inputCol="filtered", outputCol="rawFeatures", numFeatures=1000)
    idf = IDF(inputCol="rawFeatures", outputCol="features")
    lr = LogisticRegression(maxIter=10, regParam=0.001)
    
    pipeline = Pipeline(stages=[tokenizer, remover, hashingTF, idf, lr])
    
    # Entraîner
    model = pipeline.fit(train_df)
    
    # Sauvegarder
    model.write().overwrite().save("/opt/spark-models/sentiment_model")
    print("Modèle sauvegardé avec succès!")
    
    return model

# Charger ou entraîner le modèle
try:
    model = PipelineModel.load("/opt/spark-models/sentiment_model")
    print("Modèle chargé depuis le disque")
except:
    model = train_sentiment_model()

# Fonction pour appliquer le modèle par batch
def process_batch(batch_df, batch_id):
    if batch_df.isEmpty():
        return
    
    print(f"Traitement du batch {batch_id} avec {batch_df.count()} enregistrements")
    
    # Appliquer le modèle
    predictions = model.transform(batch_df)
    
    # Extraire les résultats
    results = predictions.select(
        col("id"),
        col("text"),
        col("user"),
        col("timestamp"),
        col("location"),
        col("prediction").alias("sentiment"),
        col("probability").getItem(1).alias("confidence")
    )
    
    # Ajouter des labels lisibles
    results = results.withColumn(
        "sentiment_label",
        when(col("sentiment") == 1.0, "positive").otherwise("negative")
    )
    
    # Ajouter metadata
    results = results.withColumn("processed_time", current_timestamp())
    
    # Afficher quelques résultats
    print("Exemples de prédictions:")
    results.select("text", "sentiment_label", "confidence").show(5, truncate=False)
    
    # Écrire dans ElasticSearch
    results.write \
        .format("org.elasticsearch.spark.sql") \
        .option("es.resource", "sentiment-analysis/tweet") \
        .option("es.mapping.id", "id") \
        .mode("append") \
        .save()
    
    print(f"Batch {batch_id} envoyé à ElasticSearch")

# Démarrer le streaming
query = parsed_df.writeStream \
    .foreachBatch(process_batch) \
    .outputMode("update") \
    .option("checkpointLocation", "/tmp/checkpoint") \
    .start()

print("Streaming démarré. En attente de données...")
query.awaitTermination()