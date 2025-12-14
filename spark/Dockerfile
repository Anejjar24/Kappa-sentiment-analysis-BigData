FROM apache/spark:3.5.0

USER root

# Installer pip + numpy + pandas + sklearn
RUN apt-get update && apt-get install -y python3-pip && \
    pip3 install --no-cache-dir numpy pandas scikit-learn

# Créer le répertoire Ivy pour l'utilisateur spark (pas root)
RUN mkdir -p /home/spark/.ivy2/cache && \
    mkdir -p /home/spark/.ivy2/jars && \
    chown -R spark:spark /home/spark/.ivy2 && \
    chmod -R 777 /home/spark/.ivy2

# Ajouter Spark au PATH
ENV SPARK_HOME=/opt/spark
ENV PATH=$SPARK_HOME/bin:$PATH

USER spark