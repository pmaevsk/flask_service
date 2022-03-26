FROM python:3.9

WORKDIR /flask_ht
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV FLASK_APP=app.py
EXPOSE 5000
CMD flask run -h 0.0.0.0 -p 5000