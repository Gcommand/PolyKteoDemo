FROM python:3.11-slim

# Attempt to update C++ runtime - CAUTION!
RUN apt-get update && apt-get install -y --only-upgrade libstdc++6 gcc g++ # May need specific versions or sources

WORKDIR /app
COPY . /app

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

CMD ["gunicorn", "--bind", "0.0.0.0:$PORT", "app:app"]