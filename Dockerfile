# Use the official lightweight Python image.
# https://hub.docker.com/_/python
FROM python:3.11-slim

RUN apt update && apt install -y --no-install-recommends \
pandoc \
&& \
apt-get clean && \
rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Install production dependencies.
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Allow statements and log messages to immediately appear in the Knative logs
ENV PYTHONUNBUFFERED True

# Copy local code to the container image.
ENV APP_HOME /app
WORKDIR $APP_HOME
COPY . ./app

EXPOSE 5006

# Run the web service on container startup. 
CMD ["fastapi", "run", "./app/main.py", "--port", "5006"]