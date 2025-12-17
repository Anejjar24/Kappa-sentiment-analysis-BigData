# twitch_chat_producer.py — Using kafka-python
import socket
import json
from datetime import datetime
from kafka import KafkaProducer  # Change this import

# -----------------------------
# Kafka configuration
# -----------------------------
producer = KafkaProducer(
    bootstrap_servers=['localhost:9093'],
    value_serializer=lambda v: json.dumps(v).encode('utf-8'),
    client_id='twitch-chat-producer'
)

# -----------------------------
# Twitch IRC configuration
# -----------------------------
server = "irc.chat.twitch.tv"
port = 6667

nickname = "shadowlight2019"
token = "oauth:v0ckl468prvym0sz1a6nidw33t42vt"
channel = "#xqc"

print(f"Connecting to Twitch chat → {channel}")

# -----------------------------
# Connect to Twitch IRC
# -----------------------------
sock = socket.socket()
sock.connect((server, port))

sock.send(f"PASS {token}\n".encode("utf-8"))
sock.send(f"NICK {nickname}\n".encode("utf-8"))
sock.send(f"JOIN {channel}\n".encode("utf-8"))

print("Connected. Streaming messages → Kafka (topic: twitch-data)\n")

# -----------------------------
# Main Loop
# -----------------------------
while True:
    try:
        resp = sock.recv(2048).decode("utf-8", errors="ignore")

        # Keep-alive mechanism
        if resp.startswith("PING"):
            sock.send("PONG\n".encode("utf-8"))
            continue

        # Extract actual chat messages
        if "PRIVMSG" in resp:
            try:
                prefix, message = resp.split("PRIVMSG", 1)
                user = prefix.split("!", 1)[0].replace(":", "").strip()
                text = message.split(":", 1)[1].strip()

                if len(text) < 1:
                    continue

                event = {
                    "text": text,
                    "user": user[:50],
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "location": "Twitch"
                }

                # Send to Kafka using kafka-python
                producer.send('twitch-data', value=event)

                print(f"[{user[:15]:<15}] {text[:80]}")
            except:
                pass

    except KeyboardInterrupt:
        print("\nStopped by user.")
        break
    except Exception as e:
        print(f"Error: {e}")
        continue

producer.flush()
print("Producer shut down cleanly.")
