# 🎭 Kappa Architecture for Real-Time Sentiment Analysis

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Docker](https://img.shields.io/badge/Docker-20.10+-blue.svg)](https://www.docker.com/)
[![Python](https://img.shields.io/badge/Python-3.8+-green.svg)](https://www.python.org/)
[![Spark](https://img.shields.io/badge/Apache%20Spark-3.5.0-orange.svg)](https://spark.apache.org/)

> A complete Big Data pipeline implementing the Kappa Architecture for real-time sentiment analysis of streaming chat data from platforms like Twitch and YouTube.

![Architecture Overview](assets/GlobalArchi.png)

## 📋 Table of Contents

- [Overview](#-overview)
- [Architecture](#-architecture)
- [Features](#-features)
- [Prerequisites](#-prerequisites)
- [Quick Start](#-quick-start)
- [Project Structure](#-project-structure)
- [Configuration](#-configuration)
- [Usage Guide](#-usage-guide)
- [Machine Learning Models](#-machine-learning-models)
- [Monitoring & Visualization](#-monitoring--visualization)
- [Troubleshooting](#-troubleshooting)
- [Performance](#-performance)
- [Contributing](#-contributing)
- [License](#-license)
- [Authors](#-authors)

## 🎯 Overview

This project implements a **Kappa Architecture** for processing and analyzing sentiment from live streaming chat platforms in real-time. It combines multiple Big Data technologies to create a robust, scalable, and fault-tolerant system.

### What is Kappa Architecture?

The Kappa Architecture simplifies the Lambda Architecture by using a single streaming processing layer for both real-time and historical data processing. This eliminates the complexity of maintaining separate batch and streaming codebases.

### Key Capabilities

- ✅ **Real-time ingestion** from YouTube and Twitch
- ✅ **Data validation** and quality checks with Apache NiFi
- ✅ **ML-powered sentiment analysis** (Spark ML + Hugging Face)
- ✅ **Live visualization** with Kibana dashboards
- ✅ **Scalable streaming** with Kafka and Spark Structured Streaming
- ✅ **Persistent storage** in Elasticsearch

## 🏗️ Architecture

### System Components

```
┌─────────────┐      ┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│   YouTube   │      │   Twitch    │      │   Other     │      │             │
│  Producer   │─────▶│  Producer   │─────▶│  Sources    │─────▶│   Kafka     │
└─────────────┘      └─────────────┘      └─────────────┘      │ raw-tweets  │
                                                                 └──────┬──────┘
                                                                        │
                                                                        ▼
                                                                 ┌─────────────┐
                                                                 │    NiFi     │
                                                                 │ (Validation)│
                                                                 └──────┬──────┘
                                                                        │
                                                                        ▼
                                                                 ┌─────────────┐
                                                                 │   Kafka     │
                                                                 │  validated  │
                                                                 └──────┬──────┘
                                                                        │
                                                                        ▼
                                                                 ┌─────────────┐
                                                                 │    Spark    │
                                                                 │  Streaming  │
                                                                 │  + ML Model │
                                                                 └──────┬──────┘
                                                                        │
                                                                        ▼
                                                                 ┌─────────────┐
                                                                 │Elasticsearch│
                                                                 └──────┬──────┘
                                                                        │
                                                                        ▼
                                                                 ┌─────────────┐
                                                                 │   Kibana    │
                                                                 │(Dashboards) │
                                                                 └─────────────┘
```

### Technology Stack

| Component | Technology | Port | Purpose |
|-----------|-----------|------|---------|
| **Message Broker** | Apache Kafka | 9092 | Distributed streaming platform |
| **Coordination** | Apache Zookeeper | 2181 | Kafka cluster management |
| **Data Validation** | Apache NiFi | 8080 | ETL and data quality |
| **Stream Processing** | Apache Spark | 8081 | Real-time analytics |
| **ML Framework** | Spark MLlib + Transformers | - | Sentiment prediction |
| **Search Engine** | Elasticsearch | 9200 | Document storage and indexing |
| **Visualization** | Kibana | 5601 | Interactive dashboards |

## ✨ Features

### Data Ingestion
- **Multi-source support**: YouTube comments, Twitch chat, extensible to other platforms
- **Real-time streaming**: Continuous data flow with configurable batch intervals
- **Error handling**: Automatic reconnection and retry mechanisms

### Data Validation
- **NiFi-based validation**: Schema validation, null checks, duplicate detection
- **Routing logic**: Valid messages to processing, invalid to error queue
- **Monitoring**: Visual flow tracking and statistics

### Machine Learning
- **Two approaches available**:
  1. **Spark ML** (Naive Bayes): Fast, lightweight, 71% accuracy
  2. **Hugging Face Transformers** (RoBERTa): State-of-the-art, 87% accuracy
- **Real-time prediction**: Sentiment classification (negative, neutral, positive)
- **Model comparison**: Automated evaluation and benchmarking

### Visualization
- **Real-time dashboards**: Auto-refreshing Kibana visualizations
- **Multiple chart types**: Donut charts, bar charts, word clouds, time series
- **Custom metrics**: Sentiment distribution, top users, trending topics

## 📦 Prerequisites

Before starting, ensure you have:

### Software Requirements
- **Docker**: Version 20.10 or higher
- **Docker Compose**: Version 1.29 or higher
- **Python**: Version 3.8 or higher
- **Git**: For cloning the repository

### Hardware Requirements
- **RAM**: Minimum 8 GB (16 GB recommended for Hugging Face models)
- **CPU**: 4+ cores recommended
- **Disk Space**: At least 20 GB free
- **Network**: Stable internet connection for model downloads

### API Keys (Optional)
- **YouTube Data API v3**: For YouTube comment ingestion ([Get key here](https://console.cloud.google.com))
- **Twitch OAuth Token**: For Twitch chat ingestion ([Generate token here](https://twitchapps.com/tmi/))

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/kappa-sentiment-analysis.git
cd kappa-sentiment-analysis
```

### 2. Configure Environment Variables

Create a `.env` file with your API credentials:

```bash
cat > .env << EOF
# YouTube API (optional)
YOUTUBE_API_KEY=your_youtube_api_key_here

# Twitch Configuration (optional)
TWITCH_OAUTH_TOKEN=oauth:your_token_here
TWITCH_NICKNAME=your_bot_nickname
TWITCH_CHANNEL=channel_to_monitor
EOF
```

### 3. Start the Infrastructure

```bash
# Build and start all Docker containers
docker compose build
docker compose up -d

# Wait 2-3 minutes for all services to initialize
# Check status
docker compose ps
```

### 4. Initialize the System

```bash
# Make scripts executable
chmod +x setup.sh setup_ml.sh setup_streaming.sh

# Run initial configuration (creates Kafka topics and ES index)
./setup.sh
```

### 5. Train ML Models

```bash
# This will train multiple models and save the best one
./setup_ml.sh

# Expected duration: 10-20 minutes
# Output: Trained models in /models directory
```

### 6. Configure NiFi Validation Flow

1. Open NiFi UI: http://localhost:8080
2. Login with credentials: `admin / adminadminadmin`
3. Upload template from `nifi/templates/nifi_flow.xml`
4. Drag the template onto the canvas
5. Start all processors

### 7. Start Data Producers

```bash
# Install Python dependencies
pip install -r requirements.txt

# Start YouTube producer (if configured)
python3 real_youtube_producer.py &

# Start Twitch producer (if configured)
python3 twitch_chat_producer.py &
```

### 8. Launch Spark Streaming

**Option A: Spark ML (Naive Bayes) - Recommended for resource-constrained environments**

```bash
./setup_streaming.sh
```

**Option B: Hugging Face Transformers (RoBERTa) - For maximum accuracy**

```bash
docker exec spark-master spark-submit \
  --master local[*] \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0,\
org.elasticsearch:elasticsearch-spark-30_2.12:8.11.0 \
  --conf spark.executor.memory=10g \
  --conf spark.executor.memoryOverhead=3g \
  --conf spark.driver.memory=4g \
  /opt/spark-apps/sentiment_analysis_hf.py
```

### 9. Access the Dashboards

- **Kibana**: http://localhost:5601
- **Spark Master UI**: http://localhost:8081
- **NiFi UI**: http://localhost:8080
- **Elasticsearch**: http://localhost:9200

## 📁 Project Structure

```
kappa-sentiment-analysis/
├── dataset/
│   └── YoutubeCommentsDataSet.csv          # Training dataset
├── elasticsearch/                          # ES configuration
├── kafka/                                  # Kafka data directory
├── kibana/                                 # Kibana data directory
├── models/                                 # Trained ML models (auto-generated)
├── nifi/
│   └── templates/
│       └── nifi_flow.xml                   # NiFi validation flow
├── spark/
│   ├── Dockerfile                          # Custom Spark image
│   └── app/
│       ├── train_sentiment_model.py        # Model training (Spark ML)
│       ├── streaming.py                    # Streaming with Naive Bayes
│       ├── sentiment_analysis_hf.py        # Streaming with Hugging Face
│       └── multi.py                        # Multi-model comparison
├── docker-compose.yml                      # Infrastructure definition
├── real_youtube_producer.py                # YouTube data producer
├── twitch_chat_producer.py                 # Twitch data producer
├── requirements.txt                        # Python dependencies
├── setup.sh                                # Initial setup script
├── setup_ml.sh                             # ML training script
├── setup_streaming.sh                      # Streaming launch script
└── README.md                               # This file
```

## ⚙️ Configuration

### Kafka Topics

The system uses three main Kafka topics:

| Topic | Purpose | Partitions |
|-------|---------|------------|
| `raw-tweets` | Unvalidated incoming messages | 3 |
| `tweets-validated` | Validated messages from NiFi | 3 |
| `sentiment-results` | Processed results with sentiment | 3 |

### Elasticsearch Index

Index name: `sentiment-analysis`

**Mapping:**
```json
{
  "text": "text",
  "user": "keyword",
  "timestamp": "date",
  "location": "keyword",
  "sentiment": "float",
  "sentiment_label": "keyword",
  "confidence": "float",
  "processed_time": "date"
}
```

### Spark Configuration

**For Spark ML (Naive Bayes):**
```bash
--conf spark.executor.memory=2g
--conf spark.driver.memory=2g
```

**For Hugging Face (RoBERTa):**
```bash
--conf spark.executor.memory=10g
--conf spark.executor.memoryOverhead=3g
--conf spark.driver.memory=4g
```

## 📖 Usage Guide

### Verifying Data Flow

**1. Check Kafka messages:**
```bash
# View raw messages
docker exec kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic raw-tweets \
  --from-beginning \
  --max-messages 10

# View validated messages
docker exec kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic tweets-validated \
  --from-beginning \
  --max-messages 10
```

**2. Query Elasticsearch:**
```bash
# Count indexed documents
curl -X GET "http://localhost:9200/sentiment-analysis/_count?pretty"

# Get latest 5 documents
curl -X GET "http://localhost:9200/sentiment-analysis/_search?pretty" \
  -H 'Content-Type: application/json' -d'
{
  "size": 5,
  "sort": [{"timestamp": {"order": "desc"}}]
}'

# Sentiment distribution
curl -X GET "http://localhost:9200/sentiment-analysis/_search?pretty" \
  -H 'Content-Type: application/json' -d'
{
  "size": 0,
  "aggs": {
    "sentiments": {
      "terms": {"field": "sentiment_label"}
    }
  }
}'
```

**3. Monitor Spark jobs:**
```bash
# View logs
docker logs -f spark-master

# Check Spark UI
open http://localhost:8081
```

### Creating Kibana Visualizations

**1. Create Index Pattern:**
- Navigate to Stack Management > Index Patterns
- Create pattern: `sentiment-analysis*`
- Select `timestamp` as time field

**2. Create Visualizations:**

**Donut Chart - Sentiment Distribution:**
- Type: Donut
- Metrics: Count
- Buckets: Terms aggregation on `sentiment_label`

**Bar Chart - Top Users:**
- Type: Horizontal Bar
- Metrics: Count
- Buckets: Terms on `user`, Size: 10

**Word Cloud:**
- Type: Tag Cloud
- Buckets: Terms on `text.keyword`, Size: 50

**3. Build Dashboard:**
- Navigate to Dashboard > Create
- Add all visualizations
- Enable auto-refresh (5 seconds)
- Save as "Real-Time Sentiment Analysis"

## 🤖 Machine Learning Models

### Approach Comparison

| Aspect | Spark ML (Naive Bayes) | Hugging Face (RoBERTa) |
|--------|------------------------|------------------------|
| **Accuracy** | 71.0% | 87.3% |
| **F1-Score** | 0.702 | 0.864 |
| **Inference Time** | ~15ms/message | ~150ms/message |
| **Memory** | 2-4 GB | 10-16 GB |
| **Setup Complexity** | Simple | Medium |
| **Best For** | High throughput, low latency | Maximum accuracy |

### Spark ML Models Trained

The training script evaluates multiple algorithms:

1. **Naive Bayes** ⭐ (Selected)
   - Accuracy: 71.0%
   - Training time: 6.92s
   - Best balance of speed and accuracy

2. **Logistic Regression**
   - Accuracy: 69.7%
   - Training time: 35.76s

3. **Random Forest**
   - Accuracy: 63.3%
   - Training time: 62.17s

4. **Decision Tree**
   - Accuracy: 63.7%
   - Training time: 41.85s

### Hugging Face Model

**Model**: `j-hartmann/sentiment-roberta-large-english-3-classes`

**Specifications:**
- Architecture: RoBERTa-large (355M parameters)
- Tokenization: Byte-Pair Encoding (50K vocab)
- Context window: 512 tokens
- Output classes: negative (0), neutral (1), positive (2)
- Performance: 87-90% accuracy on benchmark datasets

**First-time download**: ~1.3 GB (cached for subsequent runs)

## 📊 Monitoring & Visualization

### Available Interfaces

| Interface | URL | Description |
|-----------|-----|-------------|
| Kibana | http://localhost:5601 | Main dashboard and visualizations |
| Spark Master | http://localhost:8081 | Spark cluster and job monitoring |
| NiFi | http://localhost:8080 | Data flow validation tracking |
| Elasticsearch | http://localhost:9200 | Direct API access to stored data |

### Key Metrics to Monitor

**System Health:**
- Kafka consumer lag
- Spark streaming batch processing time
- Elasticsearch indexing rate
- NiFi processor queue size

**Business Metrics:**
- Sentiment distribution over time
- Message volume by source
- Top active users
- Trending topics/keywords

### Sample Dashboard Queries

**Sentiment trends over time:**
```json
{
  "query": {
    "range": {
      "timestamp": {
        "gte": "now-1h"
      }
    }
  },
  "aggs": {
    "sentiments_over_time": {
      "date_histogram": {
        "field": "timestamp",
        "interval": "5m"
      },
      "aggs": {
        "sentiment_breakdown": {
          "terms": {
            "field": "sentiment_label"
          }
        }
      }
    }
  }
}
```

## 🔧 Troubleshooting

### Common Issues

#### 1. Kafka Topic Not Found

**Symptom:** Streaming fails with "Topic does not exist"

**Solution:**
```bash
# List existing topics
docker exec kafka kafka-topics --list --bootstrap-server localhost:9092

# Recreate topics
./setup.sh
```

#### 2. Elasticsearch Index Creation Failed

**Symptom:** Error when creating index

**Solution:**
```bash
# Delete old index
curl -X DELETE "http://localhost:9200/sentiment-analysis"

# Recreate with setup script
./setup.sh
```

#### 3. Spark Out of Memory

**Symptom:** Job crashes with OOM error

**Solution:**
```bash
# Edit docker-compose.yml, increase worker memory:
services:
  spark-worker:
    environment:
      - SPARK_WORKER_MEMORY=8g

# Restart
docker compose restart spark-worker
```

#### 4. NiFi Processors Won't Start

**Symptom:** Processors remain in "Stopped" state

**Solutions:**
- Verify Kafka is accessible: `kafka:9092`
- Check processor configuration (right-click > Configure)
- Review NiFi logs: `docker logs nifi`

#### 5. Hugging Face Model Download Fails

**Symptom:** First run hangs or times out

**Solutions:**
```bash
# Ensure stable internet connection
# Pre-download model manually:
docker exec spark-master python3 -c "
from transformers import AutoTokenizer, AutoModelForSequenceClassification
tokenizer = AutoTokenizer.from_pretrained('j-hartmann/sentiment-roberta-large-english-3-classes')
model = AutoModelForSequenceClassification.from_pretrained('j-hartmann/sentiment-roberta-large-english-3-classes')
"
```

### Useful Commands

**Docker Management:**
```bash
# Stop all services
docker compose down

# Remove volumes (WARNING: data loss!)
docker compose down -v

# Restart specific service
docker compose restart kafka

# View resource usage
docker stats

# Clean unused images
docker system prune -a
```

**Kafka Debugging:**
```bash
# List consumer groups
docker exec kafka kafka-consumer-groups --list \
  --bootstrap-server localhost:9092

# Check consumer lag
docker exec kafka kafka-consumer-groups --describe \
  --group spark-streaming \
  --bootstrap-server localhost:9092
```

**Logs:**
```bash
# Follow all logs
docker compose logs -f

# Specific service logs
docker logs -f spark-master
docker logs -f kafka
docker logs -f nifi
```

## 📈 Performance

### Benchmarks

**Hardware:** Intel i7-10th Gen, 16GB RAM, SSD

| Metric | Spark ML | Hugging Face |
|--------|----------|--------------|
| Throughput | ~1000 msg/s | ~100 msg/s |
| Latency (p50) | 15ms | 120ms |
| Latency (p95) | 50ms | 300ms |
| CPU Usage | 30-40% | 60-80% |
| Memory Usage | 3GB | 12GB |

### Scaling Recommendations

**For higher throughput:**

1. **Add Spark Workers:**
```yaml
# docker-compose.yml
spark-worker-2:
  image: custom-spark:latest
  environment:
    - SPARK_MASTER=spark://spark-master:7077
    - SPARK_WORKER_CORES=4
    - SPARK_WORKER_MEMORY=4g
```

2. **Increase Kafka Partitions:**
```bash
docker exec kafka kafka-topics --alter \
  --topic tweets-validated \
  --partitions 10 \
  --bootstrap-server localhost:9092
```

3. **Add Elasticsearch Nodes:**
```yaml
# docker-compose.yml
elasticsearch-2:
  image: elasticsearch:8.11.0
  environment:
    - cluster.name=sentiment-cluster
    - discovery.seed_hosts=elasticsearch
```

## 🤝 Contributing

Contributions are welcome! Here's how you can help:

### Reporting Bugs

Please open an issue with:
- Description of the problem
- Steps to reproduce
- Expected vs actual behavior
- System information (OS, Docker version, etc.)

### Suggesting Features

Open an issue with:
- Clear description of the feature
- Use case and benefits
- Possible implementation approach

### Submitting Pull Requests

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines

- Follow PEP 8 for Python code
- Add comments for complex logic
- Update documentation for new features
- Test changes in a clean Docker environment

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

```
MIT License

Copyright (c) 2025 Zineb EL HALLA & Ihssane ANEJJAR

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
```

## 👥 Authors

**Zineb EL HALLA**
- GitHub: [@zineb-elhalla](https://github.com/zineb-elhalla)
- Email: zineb.elhalla@example.com

**Ihssane ANEJJAR**
- GitHub: [@ihssane-anejjar](https://github.com/ihssane-anejjar)
- Email: ihssane.anejjar@example.com

### Supervision

**Pr. LAZAR Hajar**
- Module: Big Data Architecture and Infrastructure
- Institution: 2ITE3

## 🙏 Acknowledgments

- Apache Software Foundation for Kafka, Spark, and NiFi
- Elastic for Elasticsearch and Kibana
- Hugging Face for the Transformers library
- The open-source community

## 📚 References

### Documentation
- [Apache Kafka Documentation](https://kafka.apache.org/documentation/)
- [Apache Spark Structured Streaming](https://spark.apache.org/docs/latest/structured-streaming-programming-guide.html)
- [Apache NiFi User Guide](https://nifi.apache.org/docs.html)
- [Elasticsearch Guide](https://www.elastic.co/guide/en/elasticsearch/reference/current/index.html)
- [Hugging Face Transformers](https://huggingface.co/docs/transformers/index)

### Papers & Articles
- Kappa Architecture (Jay Kreps) - [Link](http://milinda.pathirage.org/kappa-architecture.com/)
- RoBERTa: A Robustly Optimized BERT Pretraining Approach - [arXiv](https://arxiv.org/abs/1907.11692)

## 📞 Support

For questions or support:
- Open an issue on GitHub
- Email: support@example.com
- Documentation: [Wiki](https://github.com/your-username/kappa-sentiment-analysis/wiki)

---

**⭐ If you find this project helpful, please consider giving it a star!**

Made with ❤️ using Apache Spark, Kafka, and Hugging Face
