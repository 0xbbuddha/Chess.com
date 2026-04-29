FROM python:3.11

WORKDIR /Mythic/

COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python3", "mythic/c2_functions/Chesscom.py"]
