<<<<<<< f305992f4b1287c4a3de2d7cf7374253df5028e7
aioquic
=======

|rtd| |pypi-v| |pypi-pyversions| |pypi-l| |tests| |codecov| |black|

.. |rtd| image:: https://readthedocs.org/projects/aioquic/badge/?version=latest
    :target: https://aioquic.readthedocs.io/

.. |pypi-v| image:: https://img.shields.io/pypi/v/aioquic.svg
    :target: https://pypi.python.org/pypi/aioquic

.. |pypi-pyversions| image:: https://img.shields.io/pypi/pyversions/aioquic.svg
    :target: https://pypi.python.org/pypi/aioquic

.. |pypi-l| image:: https://img.shields.io/pypi/l/aioquic.svg
    :target: https://pypi.python.org/pypi/aioquic

.. |tests| image:: https://github.com/aiortc/aioquic/workflows/tests/badge.svg
    :target: https://github.com/aiortc/aioquic/actions

.. |codecov| image:: https://img.shields.io/codecov/c/github/aiortc/aioquic.svg
    :target: https://codecov.io/gh/aiortc/aioquic

.. |black| image:: https://img.shields.io/badge/code%20style-black-000000.svg
    :target: https://github.com/python/black

What is ``aioquic``?
--------------------

``aioquic`` is a library for the QUIC network protocol in Python. It features
a minimal TLS 1.3 implementation, a QUIC stack and an HTTP/3 stack.

QUIC standardisation is not finalised yet, but ``aioquic`` closely tracks the
specification drafts and is regularly tested for interoperability against other
`QUIC implementations`_.

To learn more about ``aioquic`` please `read the documentation`_.

Why should I use ``aioquic``?
-----------------------------

``aioquic`` has been designed to be embedded into Python client and server
libraries wishing to support QUIC and / or HTTP/3. The goal is to provide a
common codebase for Python libraries in the hope of avoiding duplicated effort.

Both the QUIC and the HTTP/3 APIs follow the "bring your own I/O" pattern,
leaving actual I/O operations to the API user. This approach has a number of
advantages including making the code testable and allowing integration with
different concurrency models.

Features
--------

- QUIC stack conforming with draft-23
- HTTP/3 stack conforming with draft-23
- minimal TLS 1.3 implementation
- IPv4 and IPv6 support
- connection migration and NAT rebinding
- logging TLS traffic secrets
- logging QUIC events in QLOG format
- HTTP/3 server push support

Requirements
------------

``aioquic`` requires Python 3.6 or better, and the OpenSSL development headers.

Linux
.....

On Debian/Ubuntu run:

.. code-block:: console

   $ sudo apt install libssl-dev python3-dev

On Alpine Linux you will also need the following:

.. code-block:: console

   $ sudo apt install bsd-compat-headers libffi-dev

OS X
....

On OS X run:

.. code-block:: console

   $ brew install openssl

You will need to set some environment variables to link against OpenSSL:

.. code-block:: console

   $ export CFLAGS=-I/usr/local/opt/openssl/include
   $ export LDFLAGS=-L/usr/local/opt/openssl/lib

Running the examples
--------------------

After checking out the code using git you can run:

.. code-block:: console

   $ pip install -e .
   $ pip install aiofiles asgiref httpbin starlette wsproto

HTTP/3 server
.............

You can run the example server, which handles both HTTP/0.9 and HTTP/3:

.. code-block:: console

   $ python examples/http3_server.py --certificate tests/ssl_cert.pem --private-key tests/ssl_key.pem

HTTP/3 client
.............

You can run the example client to perform an HTTP/3 request:

.. code-block:: console

  $ python examples/http3_client.py --ca-certs tests/pycacert.pem https://localhost:4433/

Alternatively you can perform an HTTP/0.9 request:

.. code-block:: console

  $ python examples/http3_client.py --ca-certs tests/pycacert.pem --legacy-http https://localhost:4433/

You can also open a WebSocket over HTTP/3:

.. code-block:: console

  $ python examples/http3_client.py --ca-certs tests/pycacert.pem wss://localhost:4433/ws

License
-------

``aioquic`` is released under the `BSD license`_.

.. _read the documentation: https://aioquic.readthedocs.io/en/latest/
.. _QUIC implementations: https://github.com/quicwg/base-drafts/wiki/Implementations
.. _cryptography: https://cryptography.io/
.. _BSD license: https://aioquic.readthedocs.io/en/latest/license.html
=======
aioquic for testing QUIC multiplexing behaviours
================================================
This is a fork of the aioquic project to aid in testing the multiplexing behaviours of other QUIC implementations.

To use:
1. build a dockercontainer using the dockerfile in scripts/
2. look at scripts/run_docker.sh and adapt to work for your own setup (mainly: where to mount the qlog directory)
3. execute scripts/run_docker.sh, which will give you a bash entry into the container 
4. in the container: cd /srv/aioquic
5. look at the script scripts/run_tests.py. By default, it will perform 10 runs on each of the public QUIC endpoints that support /n type URLs.
6. if necessary, change scripts/run_tests.py to fit your needs (comment/uncomment things you don't need/want)
7. in /srv/aioquic, run python3 scripts/run_tests.py 
8. find your qlog output in the mounted qlog volume from run_docker.sh
9. upload the .qlog files to https://qvis.edm.uhasselt.be for fun and profit!
>>>>>>> Update test configurations
