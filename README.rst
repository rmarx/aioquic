aioquic for testing QUIC multiplexing behaviours
================================================
This is a fork of the aioquic project to aid in testing the multiplexing behaviours of other QUIC implementations.

To use:

1) on the host: build a dockercontainer using the dockerfile in scripts/

2) on the host: look at scripts/run_docker.sh and adapt to work for your own setup (mainly: where to mount the qlog directory)

    2.1) example: --volume=/home/you/whereYouNeedQlogOutput:/srv/aioquic/qlog

3) on the host: execute scripts/run_docker.sh, which will give you a bash entry into the container 

4) in the container: cd /srv/aioquic

5) in the container: look at the script scripts/run_tests.py. By default, it will perform 10 runs on each of the public QUIC endpoints that support /n type URLs. The qlog files are put in /srv/aioquic/qlog by default, which is why you needed the mountpoint in step 2 to extract them to your local machine.

6) in the container: if necessary, change scripts/run_tests.py to fit your needs (comment/uncomment things you don't need/want)

    6.1) Endpoints that support /n urls (in "proper_endpoints") can be run with any filesize, the others (each their own variable) need to be run 1-by-1 on the correct paths they support

7) in the container: in /srv/aioquic, run python3 scripts/run_tests.py 

8) on the host: find your qlog output in the mounted qlog volume from run_docker.sh

9) on the host: upload the .qlog files to https://qvis.edm.uhasselt.be for fun and profit!