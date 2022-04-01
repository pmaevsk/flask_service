"# flask_service" 

docker build -t deploy_flask . 
docker run -p 5000:5000 -t -i deploy_flask:latest