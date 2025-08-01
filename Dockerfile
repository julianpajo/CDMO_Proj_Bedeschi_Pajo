FROM minizinc/minizinc:latest

RUN apt-get update && apt-get install -y python3 python3-pip

WORKDIR /app

COPY . /app

RUN pip install --break-system-packages -r requirements.txt

ENTRYPOINT ["python3", "run_models.py"]
