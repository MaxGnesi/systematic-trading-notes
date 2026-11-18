# The live bot in a container (Lecture 24 §11): the same code, the same Python, on any machine.
# Secrets and data are NOT in the image: the key is mounted read-only and the data folder from outside
# (see docker-compose.yml), so the image can be shared and rebuilt without ever containing a credential.
FROM python:3.11-slim

WORKDIR /app
COPY capstone/requirements.txt capstone/requirements.txt
RUN pip install --no-cache-dir -r capstone/requirements.txt

COPY capstone/ capstone/
RUN rm -rf capstone/data capstone/configs/.env capstone/configs/*.env

# logs go to the console, which Docker keeps (docker compose logs)
CMD ["python", "-X", "utf8", "-m", "capstone.run_bot"]
