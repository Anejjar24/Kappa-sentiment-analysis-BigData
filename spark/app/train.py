"""
Modèle de sentiment avancé pour YouTube Comments
"""

from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.ml.feature import *
from pyspark.ml.classification import RandomForestClassifier
from pyspark.ml import Pipeline
from pyspark.ml.evaluation import MulticlassClassificationEvaluator


def train_youtube_sentiment_model(spark):
    """
    Entraîne un modèle avancé de classification du sentiment YouTube :
    - Tokenization
    - StopWords
    - N-grams
    - TF-IDF
    - Random Forest (multiclass)
    """

    print("Chargement du dataset YouTube...")

    # 📌 Charger le dataset YouTubeCommentsDataSet.csv
    df = spark.read.csv(
        "YoutubeCommentsDataSet.csv",
        header=True,
        inferSchema=True
    )

    # Colonnes : Comment, Sentiment
    df = df.select("Comment", "Sentiment")

    # 🏷 Encodage des labels (negative, positive, neutral -> 0,1,2)
    indexer = StringIndexer(
        inputCol="Sentiment",
        outputCol="label"
    )

    # ------- PIPELINE FEATURES --------

    # 1. Tokenization
    tokenizer = Tokenizer(
        inputCol="Comment",
        outputCol="words"
    )

    # 2. Stop words removal
    remover = StopWordsRemover(
        inputCol="words",
        outputCol="filtered"
    )

    # 3. N-gram bigrams
    ngram = NGram(
        n=2,
        inputCol="filtered",
        outputCol="ngrams"
    )

    # 4. HashingTF sur mots
    hashingTF_words = HashingTF(
        inputCol="filtered",
        outputCol="rawFeatures_words",
        numFeatures=5000
    )

    # 5. HashingTF sur ngrams
    hashingTF_ngrams = HashingTF(
        inputCol="ngrams",
        outputCol="rawFeatures_ngrams",
        numFeatures=5000
    )

    # 6. TF-IDF pour words
    idf_words = IDF(
        inputCol="rawFeatures_words",
        outputCol="features_words"
    )

    # 7. TF-IDF pour ngrams
    idf_ngrams = IDF(
        inputCol="rawFeatures_ngrams",
        outputCol="features_ngrams"
    )

    # 8. Assembler
    assembler = VectorAssembler(
        inputCols=["features_words", "features_ngrams"],
        outputCol="features"
    )

    # 9. RandomForest (multiclass)
    rf = RandomForestClassifier(
        labelCol="label",
        featuresCol="features",
        numTrees=200,
        maxDepth=12,
        seed=42
    )

    # Pipeline complet
    pipeline = Pipeline(stages=[
        indexer,
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

    # Split train/test
    train, test = df.randomSplit([0.8, 0.2], seed=42)

    print("Entraînement du modèle avancé sur YouTube Comments...")
    model = pipeline.fit(train)

    # ------ Evaluation ------
    predictions = model.transform(test)

    evaluator = MulticlassClassificationEvaluator(
        labelCol="label",
        predictionCol="prediction",
        metricName="accuracy"
    )

    accuracy = evaluator.evaluate(predictions)
    print(f"🎯 Accuracy sur test set : {accuracy:.4f}")

    # Sauvegarde du modèle
    model.write().overwrite().save("/opt/spark-models/youtube_sentiment_model")
    print("📦 Modèle YouTube sauvegardé !")

    return model


# Utilisation
if __name__ == "__main__":
    spark = SparkSession.builder.appName("YouTubeSentimentTraining").getOrCreate()
    model = train_youtube_sentiment_model(spark)
