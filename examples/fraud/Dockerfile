FROM python:3.10

WORKDIR /fraud

COPY requirements.txt .
RUN pip3 install -r requirements.txt --no-cache-dir

COPY simulate_synth.py .

CMD python3 simulate_synth.py
