# syntax=docker/dockerfile:1
FROM python:3.9
ADD . /flask_ht
WORKDIR /flask_ht
COPY requirements.txt /flask_ht
COPY ./templates /flask_ht
RUN pip3 install --upgrade pip -r requirements.txt
# ENV FLASK_APP=app.py
CMD [ "python", "app.py" ]
EXPOSE 5000