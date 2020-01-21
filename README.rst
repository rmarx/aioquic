aioquic for testing QUIC multiplexing behaviours
================================================
This is a fork of the aioquic project to aid in testing the multiplexing behaviours of other QUIC implementations.

To use:

1) build a dockercontainer using the dockerfile in scripts/

2) look at scripts/run_docker.sh and adapt to work for your own setup (mainly: where to mount the qlog directory)

3) execute scripts/run_docker.sh, which will give you a bash entry into the container 

4) in the container: cd /srv/aioquic

5) look at the script scripts/run_tests.py. By default, it will perform 10 runs on each of the public QUIC endpoints that support /n type URLs.

6) if necessary, change scripts/run_tests.py to fit your needs (comment/uncomment things you don't need/want)

7) in /srv/aioquic, run python3 scripts/run_tests.py 

8) find your qlog output in the mounted qlog volume from run_docker.sh

9) upload the .qlog files to https://qvis.edm.uhasselt.be for fun and profit!