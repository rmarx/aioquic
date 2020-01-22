# to build: sudo docker build -t aioquic .
sudo docker stop aioquic && sudo docker rm aioquic
sudo docker run -it --privileged --cap-add=NET_ADMIN -p 4433:4433/udp --name aioquic --volume=/home/robin/aioquic_docker/qlog/run3:/srv/aioquic/qlog aioquic


# sudo docker exec -it aioquic bash (to get back in if you would exit)