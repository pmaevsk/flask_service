"# flask_service" 

docker build -t flask_service . 
docker run -d -p 5000:5000 flask_service