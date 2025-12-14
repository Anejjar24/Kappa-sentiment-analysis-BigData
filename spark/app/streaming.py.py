from pyspark.sql import SparkSession
from pyspark.ml import Pipeline
from pyspark.ml.feature import Tokenizer, StopWordsRemover, CountVectorizer, IDF, StringIndexer
from pyspark.ml.classification import LogisticRegression, RandomForestClassifier
from pyspark.ml.evaluation import MulticlassClassificationEvaluator
from pyspark.sql.functions import col, lower, regexp_replace

# Créer la session Spark
spark = SparkSession.builder \
    .appName("SentimentModelTraining") \
    .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0") \
    .getOrCreate()

print("=" * 50)
print("ENTRAÎNEMENT DU MODÈLE DE SENTIMENT ANALYSIS")
print("=" * 50)

# 1. CHARGEMENT DES DONNÉES
print("\n[1/6] Chargement du dataset YouTube Comments...")
df = spark.read.csv(
    "YoutubeCommentsDataSet.csv",
    header=True,
    inferSchema=True
)

print(f"Nombre total de commentaires : {df.count()}")
df.show(5, truncate=50)

# Afficher la distribution des sentiments
print("\nDistribution des sentiments :")
df.groupBy("Sentiment").count().show()

# 2. PRÉTRAITEMENT DES DONNÉES
print("\n[2/6] Prétraitement des données...")

# Nettoyer le texte
df_clean = df.select(
    regexp_replace(lower(col("Comment")), "[^a-zA-Z\\s]", "").alias("comment_clean"),
    col("Sentiment")
).filter(col("comment_clean") != "")

# 3. FEATURE ENGINEERING
print("\n[3/6] Feature Engineering avec Pipeline ML...")

# Indexer les labels (neutral, negative, positive -> 0, 1, 2)
indexer = StringIndexer(inputCol="Sentiment", outputCol="label")

# Tokenization : séparer les mots
tokenizer = Tokenizer(inputCol="comment_clean", outputCol="words")

# Enlever les stop words (the, is, at, etc.)
remover = StopWordsRemover(inputCol="words", outputCol="filtered_words")

# CountVectorizer : convertir les mots en vecteurs de fréquence
cv = CountVectorizer(inputCol="filtered_words", outputCol="raw_features", vocabSize=10000)

# TF-IDF : pondérer l'importance des mots
idf = IDF(inputCol="raw_features", outputCol="features")

# Modèle de classification - Logistic Regression
lr = LogisticRegression(
    maxIter=100,
    regParam=0.01,
    elasticNetParam=0.8,
    family="multinomial"
)

# Alternative : Random Forest (décommenter pour utiliser)
# rf = RandomForestClassifier(numTrees=100, maxDepth=10)

# Créer le pipeline complet
pipeline = Pipeline(stages=[
    indexer,
    tokenizer,
    remover,
    cv,
    idf,
    lr  # ou rf pour Random Forest
])

# 4. SPLIT TRAIN/TEST
print("\n[4/6] Split des données (80% train, 20% test)...")
train_data, test_data = df_clean.randomSplit([0.8, 0.2], seed=42)

print(f"Données d'entraînement : {train_data.count()}")
print(f"Données de test : {test_data.count()}")

# 5. ENTRAÎNEMENT DU MODÈLE
print("\n[5/6] Entraînement du modèle en cours...")
model = pipeline.fit(train_data)
print("✓ Modèle entraîné avec succès!")

# 6. ÉVALUATION DU MODÈLE
print("\n[6/6] Évaluation du modèle...")
predictions = model.transform(test_data)

# Afficher quelques prédictions
print("\nExemples de prédictions :")
predictions.select("comment_clean", "Sentiment", "prediction", "probability").show(10, truncate=50)

# Calculer les métriques
evaluator_accuracy = MulticlassClassificationEvaluator(
    labelCol="label",
    predictionCol="prediction",
    metricName="accuracy"
)

evaluator_f1 = MulticlassClassificationEvaluator(
    labelCol="label",
    predictionCol="prediction",
    metricName="f1"
)

accuracy = evaluator_accuracy.evaluate(predictions)
f1_score = evaluator_f1.evaluate(predictions)

print("\n" + "=" * 50)
print("RÉSULTATS DU MODÈLE")
print("=" * 50)
print(f"Accuracy : {accuracy:.4f} ({accuracy*100:.2f}%)")
print(f"F1-Score : {f1_score:.4f}")

# Matrice de confusion
print("\nMatrice de confusion :")
predictions.groupBy("Sentiment", "prediction").count().show()

# 7. SAUVEGARDER LE MODÈLE
print("\n[7/7] Sauvegarde du modèle...")
model_path = "./models/sentiment_model"
model.write().overwrite().save(model_path)
print(f"✓ Modèle sauvegardé dans : {model_path}")

# Sauvegarder aussi les métadonnées
metadata = {
    "accuracy": accuracy,
    "f1_score": f1_score,
    "vocab_size": 10000,
    "model_type": "LogisticRegression"
}

import json
with open("./models/model_metadata.json", "w") as f:
    json.dump(metadata, f, indent=2)

print("\n" + "=" * 50)
print("ENTRAÎNEMENT TERMINÉ!")
print("=" * 50)

spark.stop()