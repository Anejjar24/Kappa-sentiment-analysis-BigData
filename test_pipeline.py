#!/usr/bin/env python3
"""
Script de test end-to-end pour l'architecture Kappa
Vérifie que tous les composants fonctionnent correctement
"""

import requests
import json
import time
from kafka import KafkaProducer, KafkaConsumer
from datetime import datetime

class KappaTester:
    def __init__(self):
        self.results = {
            "kafka": False,
            "nifi": False,
            "spark": False,
            "elasticsearch": False,
            "kibana": False
        }
    
    def test_kafka(self):
        """Test la connexion à Kafka"""
        print("\n🔍 Test Kafka...")
        try:
            producer = KafkaProducer(
                bootstrap_servers=['localhost:9093'],
                value_serializer=lambda v: json.dumps(v).encode('utf-8')
            )
            
            test_message = {
                "text": "Test message",
                "user": "@tester",
                "timestamp": datetime.now().isoformat(),
                "location": "Test"
            }
            
            producer.send('raw-tweets', value=test_message)
            producer.flush()
            producer.close()
            
            print("   ✅ Kafka est accessible et opérationnel")
            self.results["kafka"] = True
            return True
        except Exception as e:
            print(f"   ❌ Erreur Kafka: {e}")
            return False
    
    def test_elasticsearch(self):
        """Test ElasticSearch"""
        print("\n🔍 Test ElasticSearch...")
        try:
            response = requests.get("http://localhost:9200/_cluster/health")
            if response.status_code == 200:
                health = response.json()
                print(f"   ✅ ElasticSearch est UP - Status: {health['status']}")
                
                # Vérifier l'index
                index_response = requests.get("http://localhost:9200/sentiment-analysis/_count")
                if index_response.status_code == 200:
                    count = index_response.json()['count']
                    print(f"   📊 Documents dans l'index: {count}")
                
                self.results["elasticsearch"] = True
                return True
            else:
                print(f"   ❌ ElasticSearch non accessible")
                return False
        except Exception as e:
            print(f"   ❌ Erreur ElasticSearch: {e}")
            return False
    
    def test_kibana(self):
        """Test Kibana"""
        print("\n🔍 Test Kibana...")
        try:
            response = requests.get("http://localhost:5601/api/status")
            if response.status_code == 200:
                print("   ✅ Kibana est accessible")
                self.results["kibana"] = True
                return True
            else:
                print(f"   ❌ Kibana non accessible")
                return False
        except Exception as e:
            print(f"   ❌ Erreur Kibana: {e}")
            return False
    
    def test_nifi(self):
        """Test NiFi"""
        print("\n🔍 Test NiFi...")
        try:
            response = requests.get("http://localhost:8080/nifi")
            if response.status_code == 200:
                print("   ✅ NiFi est accessible")
                self.results["nifi"] = True
                return True
            else:
                print(f"   ❌ NiFi non accessible")
                return False
        except Exception as e:
            print(f"   ❌ Erreur NiFi: {e}")
            return False
    
    def test_spark(self):
        """Test Spark Master"""
        print("\n🔍 Test Spark...")
        try:
            response = requests.get("http://localhost:8081")
            if response.status_code == 200:
                print("   ✅ Spark Master est accessible")
                self.results["spark"] = True
                return True
            else:
                print(f"   ❌ Spark Master non accessible")
                return False
        except Exception as e:
            print(f"   ❌ Erreur Spark: {e}")
            return False
    
    def send_test_batch(self):
        """Envoie un batch de test"""
        print("\n📤 Envoi d'un batch de test...")
        try:
            producer = KafkaProducer(
                bootstrap_servers=['localhost:9093'],
                value_serializer=lambda v: json.dumps(v).encode('utf-8')
            )
            
            test_tweets = [
                {"text": "I love this product!", "user": "@test1", 
                 "timestamp": datetime.now().isoformat(), "location": "Paris"},
                {"text": "Terrible experience", "user": "@test2",
                 "timestamp": datetime.now().isoformat(), "location": "London"},
                {"text": "Amazing service!", "user": "@test3",
                 "timestamp": datetime.now().isoformat(), "location": "NYC"}
            ]
            
            for tweet in test_tweets:
                producer.send('raw-tweets', value=tweet)
                print(f"   📨 Envoyé: {tweet['text'][:30]}...")
            
            producer.flush()
            producer.close()
            print("   ✅ Batch envoyé avec succès")
            return True
        except Exception as e:
            print(f"   ❌ Erreur d'envoi: {e}")
            return False
    
    def verify_pipeline(self):
        """Vérifie le pipeline end-to-end"""
        print("\n⏳ Attente de 10 secondes pour le traitement...")
        time.sleep(10)
        
        try:
            response = requests.get("http://localhost:9200/sentiment-analysis/_search?size=5&sort=processed_time:desc")
            if response.status_code == 200:
                results = response.json()
                hits = results['hits']['total']['value']
                
                if hits > 0:
                    print(f"\n✅ Pipeline fonctionnel! {hits} documents traités")
                    print("\n📊 Exemples de résultats:")
                    for hit in results['hits']['hits'][:3]:
                        doc = hit['_source']
                        print(f"   - Text: {doc.get('text', 'N/A')[:40]}...")
                        print(f"     Sentiment: {doc.get('sentiment_label', 'N/A')}")
                        print(f"     Confidence: {doc.get('confidence', 'N/A'):.2f}")
                        print()
                    return True
                else:
                    print("   ⚠️ Aucun document traité pour le moment")
                    return False
        except Exception as e:
            print(f"   ❌ Erreur de vérification: {e}")
            return False
    
    def run_all_tests(self):
        """Exécute tous les tests"""
        print("="*60)
        print("🧪 Test de l'Architecture Kappa - Sentiment Analysis")
        print("="*60)
        
        # Tests de connectivité
        self.test_kafka()
        self.test_nifi()
        self.test_spark()
        self.test_elasticsearch()
        self.test_kibana()
        
        # Test du pipeline
        if all([self.results["kafka"], self.results["elasticsearch"]]):
            self.send_test_batch()
            self.verify_pipeline()
        
        # Résumé
        print("\n" + "="*60)
        print("📋 RÉSUMÉ DES TESTS")
        print("="*60)
        for component, status in self.results.items():
            status_icon = "✅" if status else "❌"
            print(f"{status_icon} {component.upper()}: {'OK' if status else 'ÉCHEC'}")
        
        all_ok = all(self.results.values())
        print("\n" + "="*60)
        if all_ok:
            print("🎉 TOUS LES TESTS RÉUSSIS!")
            print("Architecture Kappa opérationnelle!")
        else:
            print("⚠️ CERTAINS TESTS ONT ÉCHOUÉ")
            print("Vérifiez les logs des composants en échec")
        print("="*60)
        
        return all_ok

if __name__ == "__main__":
    tester = KappaTester()
    success = tester.run_all_tests()
    exit(0 if success else 1)