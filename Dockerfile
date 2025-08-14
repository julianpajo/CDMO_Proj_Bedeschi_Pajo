FROM python:3.9-slim-bullseye

RUN apt-get update && apt-get install -y \
    wget curl unzip \
    libgl1 libegl1 libx11-6 libfontconfig1 \
 && wget https://github.com/MiniZinc/MiniZincIDE/releases/download/2.8.6/MiniZincIDE-2.8.6-bundle-linux-x86_64.tgz \
 && tar -xzf MiniZincIDE-2.8.6-bundle-linux-x86_64.tgz \
 && mv MiniZincIDE-2.8.6-bundle-linux-x86_64 /opt/minizinc \
 && ln -s /opt/minizinc/bin/minizinc /usr/local/bin/minizinc \
 && rm MiniZincIDE-2.8.6-bundle-linux-x86_64.tgz \
 && rm -rf /var/lib/apt/lists/*


WORKDIR /app

COPY . /app

RUN pip install --no-cache-dir --break-system-packages -r requirements.txt

RUN python -m amplpy.modules install base --no-cache-dir \
 && python -m amplpy.modules install cplex gurobi --no-cache-dir || true

ENTRYPOINT ["python", "run_models.py"]
