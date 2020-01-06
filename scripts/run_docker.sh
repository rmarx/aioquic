# to build: sudo docker build -t aioquic .
sudo docker stop aioquic && sudo docker rm aioquic
sudo docker run -it --privileged --cap-add=NET_ADMIN -p 4433:4433/udp --name aioquic --volume=/home/robin/aioquic_docker/qlog:/srv/aioquic/qlog --volume=/home/robin/aioquic_docker/aioquic/trunk:/srv/aioquic_live aioquic


# sudo docker exec -it aioquic bash
# cd /srv/aioquic/qlog/
# python3 ../examples/http3_server.py --certificate ../tests/ssl_cert.pem --private-key ../tests/ssl_key.pem --quic-log server.qlog
# python3 ../examples/http3_client.py --quic-log client.qlog https://quic.aiortc.org:4433/1000000
# python3 ../../examples/http3_client.py --parallel 10 --delay-parallel 0.5 --quic-log staggered500ms_10_1MB_aioquic.qlog https://quic.aiortc.org/1000000
# python3 ../../examples/http3_client.py --quic-log parallel_10_multiple_mvfst.qlog --urls https://fb.mvfst.net:4433/1000000 --urls https://fb.mvfst.net:4433/100000 --urls https://fb.mvfst.net:4433/1000  --urls https://fb.mvfst.net:4433/100 --urls https://fb.mvfst.net:4433/10
 
