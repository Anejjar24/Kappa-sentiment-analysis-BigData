import json
import os
from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, udf
from pyspark.sql.types import StructType, StructField, StringType, TimestampType, DoubleType, IntegerType

# --- 1. Hugging Face Libraries ---
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
import numpy as np
# ---------------------------------

# --- Configuration ---
KAFKA_BROKERS = "kafka:9092"
KAFKA_INPUT_TOPIC = "twitch-data-validated"  # The topic NiFi publishes validated data to
ELASTICSEARCH_NODES = "elasticsearch:9200"
ELASTICSEARCH_INDEX = "twitch_sentiment_analysis"
CHECKPOINT_LOCATION = "/tmp/spark/checkpoints"

# --- Hugging Face Model Setup ---
# The new 3-class model
MODEL_NAME = "j-hartmann/sentiment-roberta-large-english-3-classes"

# Define the 3-class mapping (based on the common Transformer output index)
# 0: Negative, 1: Neutral, 2: Positive
SENTIMENT_MAP = {
    0: "negative",
    1: "neutral",
    2: "positive"
}

# --- 2. UDF Logic Definition ---
def predict_sentiment_hf(text):
    """Loads the model and tokenizer, predicts sentiment for the given text."""
    try:
        # Load components globally (or lazily) to avoid loading them for every row
        global tokenizer, model
        
        # Check if components are already loaded in this worker process
        if 'tokenizer' not in globals() or 'model' not in globals():
            tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
            model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME)

        if not text or len(text) < 5:
            return SENTIMENT_MAP.get(1) # Return Neutral for short/empty messages

        # Ensure the model is in evaluation mode
        model.eval() 
        
        # Tokenization and Prediction
        inputs = tokenizer(text, return_tensors="pt", truncation=True, padding=True, max_length=512)
        
        with torch.no_grad():
            outputs = model(**inputs)
        
        # Get the predicted class index (0, 1, or 2)
        predicted_class = torch.argmax(outputs.logits, dim=-1).item()
        
        # Return the corresponding sentiment label
        return SENTIMENT_MAP.get(predicted_class, SENTIMENT_MAP.get(1))
            
    except Exception as e:
        print(f"HuggingFace Prediction Error: {e}")
        # Return Neutral on error to prevent stream failure
        return SENTIMENT_MAP.get(1) 

# Register the UDF
# Input type is String (chat message), output type is String (sentiment label)
predict_sentiment_udf = udf(predict_sentiment_hf, StringType())


def create_spark_session():
    """Initializes and returns a configured Spark Session."""
    spark = SparkSession.builder \
        .appName("TwitchSentimentAnalysis") \
        .config("spark.es.nodes", ELASTICSEARCH_NODES) \
        .config("spark.es.port", "9200") \
        .config("spark.es.net.http.auth.user", "") \
        .config("spark.es.net.http.auth.pass", "") \
        .config("spark.es.index.auto.create", "true") \
        .getOrCreate()
    
    spark.sparkContext.setLogLevel("ERROR")
    return spark

# --- 3. Main Streaming Logic ---
def run_stream():
    """Reads from Kafka, applies UDF, and writes to Elasticsearch."""
    spark = create_spark_session()
    
    # Define the schema of the incoming JSON data from NiFi/Producer
    # Based on your twitch_chat_producer.py output: {"text": "...", "user": "...", "timestamp": "...", "location": "Twitch"}
    schema = StructType([
        StructField("text", StringType(), True),
        StructField("user", StringType(), True),
        StructField("timestamp", StringType(), True), # Kafka value is string, will convert later
        StructField("location", StringType(), True)
    ])

    # Read data stream from Kafka
    kafka_df = spark \
        .readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", KAFKA_BROKERS) \
        .option("subscribe", KAFKA_INPUT_TOPIC) \
        .option("startingOffsets", "latest") \
        .load()

    # Cast Kafka value (binary) to string and parse JSON using the defined schema
    parsed_df = kafka_df \
        .select(from_json(col("value").cast("string"), schema).alias("data")) \
        .select("data.*") \
        .withColumn("processed_timestamp", col("timestamp").cast(TimestampType()))

    # --- Apply the Hugging Face UDF ---
    df_with_sentiment = parsed_df.withColumn(
        "sentiment", 
        predict_sentiment_udf(col("text"))
    )

    # Prepare the final output DataFrame for Elasticsearch
    output_df = df_with_sentiment.selectExpr(
        "text",
        "user",
        "timestamp", # Keep original timestamp field
        "processed_timestamp",
        "location",
        "sentiment"  # The new sentiment column from the 3-class model
    )

    # Write the stream to Elasticsearch
    query = output_df \
        .writeStream \
        .outputMode("append") \
        .format("org.elasticsearch.spark.sql") \
        .option("es.resource", ELASTICSEARCH_INDEX) \
        .option("checkpointLocation", CHECKPOINT_LOCATION) \
        .trigger(processingTime='5 seconds') \
        .start()

    print("Spark Streaming Job Started...")
    query.awaitTermination()

if __name__ == "__main__":
    run_stream()
