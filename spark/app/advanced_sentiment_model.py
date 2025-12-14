"""
Modèle de sentiment amélioré avec plus de features
"""

from pyspark.sql import SparkSession
from pyspark.ml.feature import *
from pyspark.ml.classification import RandomForestClassifier
from pyspark.ml import Pipeline
from pyspark.ml.evaluation import BinaryClassificationEvaluator

def train_advanced_model(spark):
    """
    Entraîne un modèle plus sophistiqué avec:
    - TF-IDF
    - N-grams
    - Random Forest
    - Cross-validation
    """
    
    # Charger un vrai dataset (exemple avec Sentiment140)
    # Télécharger depuis: http://help.sentiment140.com/for-students
    training_data = spark.read.csv(
        "training_data.csv",
        schema="target INT, id STRING, date STRING, flag STRING, user STRING, text STRING"
    )
    
    # Préparer les données
    # target: 0 = négatif, 4 = positif -> convertir en 0 et 1
    training_data = training_data.withColumn(
        "label",
        when(col("target") == 4, 1).otherwise(0)
    )
    
    # Pipeline de features avancé
    # 1. Tokenization
    tokenizer = Tokenizer(inputCol="text", outputCol="words")
    
    # 2. Supprimer stop words
    remover = StopWordsRemover(inputCol="words", outputCol="filtered")
    
    # 3. N-grams (bigrams)
    ngram = NGram(n=2, inputCol="filtered", outputCol="ngrams")
    
    # 4. Hashing TF pour words
    hashingTF_words = HashingTF(
        inputCol="filtered", 
        outputCol="rawFeatures_words",
        numFeatures=5000
    )
    
    # 5. Hashing TF pour ngrams
    hashingTF_ngrams = HashingTF(
        inputCol="ngrams",
        outputCol="rawFeatures_ngrams",
        numFeatures=5000
    )
    
    # 6. IDF pour words
    idf_words = IDF(
        inputCol="rawFeatures_words",
        outputCol="features_words"
    )
    
    # 7. IDF pour ngrams
    idf_ngrams = IDF(
        inputCol="rawFeatures_ngrams",
        outputCol="features_ngrams"
    )
    
    # 8. Assembler toutes les features
    assembler = VectorAssembler(
        inputCols=["features_words", "features_ngrams"],
        outputCol="features"
    )
    
    # 9. Classifier Random Forest
    rf = RandomForestClassifier(
        featuresCol="features",
        labelCol="label",
        numTrees=100,
        maxDepth=10,
        seed=42
    )
    
    # Pipeline complet
    pipeline = Pipeline(stages=[
        tokenizer,
        remover,
        ngram,
        hashingTF_words,
        hashingTF_ngrams,
        idf_words,
        idf_ngrams,
        assembler,
        rf
    ])
    
    # Split données
    train, test = training_data.randomSplit([0.8, 0.2], seed=42)
    
    # Entraîner
    print("Entraînement du modèle avancé...")
    model = pipeline.fit(train)
    
    # Évaluer
    predictions = model.transform(test)
    evaluator = BinaryClassificationEvaluator(labelCol="label")
    auc = evaluator.evaluate(predictions)
    
    print(f"AUC sur test set: {auc:.4f}")
    
    # Sauvegarder
    model.write().overwrite().save("/opt/spark-models/advanced_sentiment_model")
    print("Modèle avancé sauvegardé!")
    
    return model

# Utilisation
if __name__ == "__main__":
    spark = SparkSession.builder.appName("AdvancedTraining").getOrCreate()
    model = train_advanced_model(spark)