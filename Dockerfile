FROM python:3.11
WORKDIR /app
ADD ./src ./src
RUN 
RUN pip install kopf
CMD kopf run -m mini_pg.kopf  --liveness=http://0.0.0.0:8080/healthz