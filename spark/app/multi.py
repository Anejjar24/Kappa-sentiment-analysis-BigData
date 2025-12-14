from pyspark.sql import SparkSession
from pyspark.ml import Pipeline
from pyspark.ml.feature import Tokenizer, StopWordsRemover, CountVectorizer, IDF, StringIndexer
from pyspark.ml.classification import (
    LogisticRegression, 
    RandomForestClassifier,
    LinearSVC,
    NaiveBayes,
    DecisionTreeClassifier,
    GBTClassifier
)
from pyspark.ml.evaluation import MulticlassClassificationEvaluator
from pyspark.sql.functions import col, lower, regexp_replace
import time

# Créer la session Spark
spark = SparkSession.builder \
    .appName("SentimentModelComparison") \
    .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0") \
    .getOrCreate()

print("=" * 70)
print("COMPARAISON DE MODÈLES DE SENTIMENT ANALYSIS AVEC SPARK ML")
print("=" * 70)

# 1. CHARGEMENT DES DONNÉES
print("\n[1/5] Chargement du dataset YouTube Comments...")
df = spark.read.csv(
    "YoutubeCommentsDataSet.csv",
    header=True,
    inferSchema=True
)

print(f"Nombre total de commentaires : {df.count()}")
df.show(5, truncate=50)

# Distribution des sentiments
print("\nDistribution des sentiments :")
df.groupBy("Sentiment").count().show()

# 2. PRÉTRAITEMENT DES DONNÉES
print("\n[2/5] Prétraitement des données...")
df_clean = df.select(
    regexp_replace(lower(col("Comment")), "[^a-zA-Z\\s]", "").alias("comment_clean"),
    col("Sentiment")
).filter(col("comment_clean") != "")

# 3. SPLIT TRAIN/TEST
print("\n[3/5] Split des données (80% train, 20% test)...")
train_data, test_data = df_clean.randomSplit([0.8, 0.2], seed=42)

print(f"Données d'entraînement : {train_data.count()}")
print(f"Données de test : {test_data.count()}")

# 4. DÉFINIR LES ÉTAPES DE PREPROCESSING COMMUNES
print("\n[4/5] Configuration du preprocessing pipeline...")

# Indexer les labels
indexer = StringIndexer(inputCol="Sentiment", outputCol="label")

# Tokenization
tokenizer = Tokenizer(inputCol="comment_clean", outputCol="words")

# Stop words removal
remover = StopWordsRemover(inputCol="words", outputCol="filtered_words")

# CountVectorizer
cv = CountVectorizer(inputCol="filtered_words", outputCol="raw_features", vocabSize=10000)

# TF-IDF
idf = IDF(inputCol="raw_features", outputCol="features")

# 5. DÉFINIR LES MODÈLES À TESTER
print("\n[5/5] Entraînement et évaluation des modèles...")
print("-" * 70)

# Dictionnaire des modèles à tester
models = {
    "Logistic Regression": LogisticRegression(
        maxIter=100,
        regParam=0.01,
        elasticNetParam=0.8,
        family="multinomial"
    ),
    "Random Forest": RandomForestClassifier(
        numTrees=100,
        maxDepth=10,
        seed=42
    ),
    "Linear SVM": LinearSVC(
        maxIter=100,
        regParam=0.01
    ),
    "Naive Bayes": NaiveBayes(
        smoothing=1.0,
        modelType="multinomial"
    ),
    "Decision Tree": DecisionTreeClassifier(
        maxDepth=10,
        seed=42
    ),
    "Gradient Boosted Trees": GBTClassifier(
        maxIter=100,
        maxDepth=5,
        seed=42
    )
}

# Stockage des résultats
results = []

# Évaluateurs
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

evaluator_precision = MulticlassClassificationEvaluator(
    labelCol="label",
    predictionCol="prediction",
    metricName="weightedPrecision"
)

evaluator_recall = MulticlassClassificationEvaluator(
    labelCol="label",
    predictionCol="prediction",
    metricName="weightedRecall"
)

# Entraîner et évaluer chaque modèle
for model_name, classifier in models.items():
    print(f"\n{'='*70}")
    print(f"MODÈLE: {model_name}")
    print(f"{'='*70}")
    
    try:
        # Créer le pipeline complet pour ce modèle
        pipeline = Pipeline(stages=[
            indexer,
            tokenizer,
            remover,
            cv,
            idf,
            classifier
        ])
        
        # Entraînement
        print(f"Entraînement en cours...")
        start_time = time.time()
        model = pipeline.fit(train_data)
        training_time = time.time() - start_time
        print(f"✓ Entraînement terminé en {training_time:.2f} secondes")
        
        # Prédiction
        print(f"Prédiction sur les données de test...")
        predictions = model.transform(test_data)
        
        # Calcul des métriques
        accuracy = evaluator_accuracy.evaluate(predictions)
        f1 = evaluator_f1.evaluate(predictions)
        precision = evaluator_precision.evaluate(predictions)
        recall = evaluator_recall.evaluate(predictions)
        
        # Afficher les résultats
        print(f"\n📊 RÉSULTATS POUR {model_name}:")
        print(f"  • Accuracy  : {accuracy:.4f} ({accuracy*100:.2f}%)")
        print(f"  • F1-Score  : {f1:.4f}")
        print(f"  • Precision : {precision:.4f}")
        print(f"  • Recall    : {recall:.4f}")
        print(f"  • Temps     : {training_time:.2f}s")
        
        # Afficher quelques exemples de prédictions
        print(f"\nExemples de prédictions:")
        predictions.select("comment_clean", "Sentiment", "prediction").show(5, truncate=50)
        
        # Matrice de confusion
        print(f"\nMatrice de confusion:")
        predictions.groupBy("Sentiment", "prediction").count().orderBy("Sentiment", "prediction").show()
        
        # Stocker les résultats
        results.append({
            "model": model_name,
            "accuracy": accuracy,
            "f1_score": f1,
            "precision": precision,
            "recall": recall,
            "training_time": training_time
        })
        
    except Exception as e:
        print(f"❌ Erreur lors de l'entraînement de {model_name}: {str(e)}")
        results.append({
            "model": model_name,
            "accuracy": 0,
            "f1_score": 0,
            "precision": 0,
            "recall": 0,
            "training_time": 0,
            "error": str(e)
        })

# 6. RÉSUMÉ COMPARATIF
print("\n" + "="*70)
print("RÉSUMÉ COMPARATIF DES MODÈLES")
print("="*70)

# Créer un DataFrame des résultats
results_data = [(
    r["model"],
    r["accuracy"],
    r["f1_score"],
    r["precision"],
    r["recall"],
    r["training_time"]
) for r in results if "error" not in r]

results_df = spark.createDataFrame(
    results_data,
    ["Model", "Accuracy", "F1_Score", "Precision", "Recall", "Training_Time"]
)

print("\nClassement par Accuracy:")
results_df.orderBy(col("Accuracy").desc()).show(truncate=False)

print("\nClassement par F1-Score:")
results_df.orderBy(col("F1_Score").desc()).show(truncate=False)

# Trouver le meilleur modèle
best_model = max(results, key=lambda x: x.get("accuracy", 0))
print(f"\n🏆 MEILLEUR MODÈLE: {best_model['model']}")
print(f"   Accuracy: {best_model['accuracy']:.4f} ({best_model['accuracy']*100:.2f}%)")
print(f"   F1-Score: {best_model['f1_score']:.4f}")

# 7. SAUVEGARDER LES RÉSULTATS
print("\n" + "="*70)
print("Sauvegarde des résultats...")

import json
with open("./models/comparison_results.json", "w") as f:
    json.dump(results, f, indent=2)

print("✓ Résultats sauvegardés dans: ./models/comparison_results.json")

print("\n" + "="*70)
print("COMPARAISON TERMINÉE!")
print("="*70)

spark.stop()