import argparse
import asyncio
import json
import logging
import os
import pickle
import ssl
import time
from collections import deque
from typing import Callable, Deque, Dict, List, Optional, Union, cast
from urllib.parse import urlparse

import wsproto
import wsproto.events

import aioquic
from aioquic.asyncio.client import connect
from aioquic.asyncio.protocol import QuicConnectionProtocol
from aioquic.h0.connection import H0_ALPN, H0Connection
from aioquic.h3.connection import H3_ALPN, H3Connection
from aioquic.h3.events import (
    DataReceived,
    H3Event,
    HeadersReceived,
    PushPromiseReceived,
)
from aioquic.quic.configuration import QuicConfiguration
from aioquic.quic.events import QuicEvent
from aioquic.quic.logger import QuicLogger
from aioquic.tls import SessionTicket

from aioquic.quic.packet_builder import (
    PACKET_MAX_SIZE,
)

try:
    import uvloop
except ImportError:
    uvloop = None

logger = logging.getLogger("client")

HttpConnection = Union[H0Connection, H3Connection]

USER_AGENT = "aioquic/" + aioquic.__version__

delay_parallel = 0

session_ticket = None

zerortt_amplification_factor = 0

class URL:
    def __init__(self, url: str) -> None:
        parsed = urlparse(url)

        self.authority = parsed.netloc
        self.full_path = parsed.path
        if parsed.query:
            self.full_path += "?" + parsed.query
        self.scheme = parsed.scheme
        self.url = url


class HttpRequest:
    def __init__(
        self, method: str, url: URL, content: bytes = b"", headers: Dict = {}
    ) -> None:
        self.content = content
        self.headers = headers
        self.method = method
        self.url = url


class WebSocket:
    def __init__(
        self, http: HttpConnection, stream_id: int, transmit: Callable[[], None]
    ) -> None:
        self.http = http
        self.queue: asyncio.Queue[str] = asyncio.Queue()
        self.stream_id = stream_id
        self.subprotocol: Optional[str] = None
        self.transmit = transmit
        self.websocket = wsproto.Connection(wsproto.ConnectionType.CLIENT)

    async def close(self, code=1000, reason="") -> None:
        """
        Perform the closing handshake.
        """
        data = self.websocket.send(
            wsproto.events.CloseConnection(code=code, reason=reason)
        )
        self.http.send_data(stream_id=self.stream_id, data=data, end_stream=True)
        self.transmit()

    async def recv(self) -> str:
        """
        Receive the next message.
        """
        return await self.queue.get()

    async def send(self, message: str) -> None:
        """
        Send a message.
        """
        assert isinstance(message, str)

        data = self.websocket.send(wsproto.events.TextMessage(data=message))
        self.http.send_data(stream_id=self.stream_id, data=data, end_stream=False)
        self.transmit()

    def http_event_received(self, event: H3Event) -> None:
        if isinstance(event, HeadersReceived):
            for header, value in event.headers:
                if header == b"sec-websocket-protocol":
                    self.subprotocol = value.decode()
        elif isinstance(event, DataReceived):
            self.websocket.receive_data(event.data)

        for ws_event in self.websocket.events():
            self.websocket_event_received(ws_event)

    def websocket_event_received(self, event: wsproto.events.Event) -> None:
        if isinstance(event, wsproto.events.TextMessage):
            self.queue.put_nowait(event.data)


class HttpClient(QuicConnectionProtocol):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.pushes: Dict[int, Deque[H3Event]] = {}
        self._http: Optional[HttpConnection] = None
        self._request_events: Dict[int, Deque[H3Event]] = {}
        self._request_waiter: Dict[int, asyncio.Future[Deque[H3Event]]] = {}
        self._websockets: Dict[int, WebSocket] = {}

        if self._quic.configuration.alpn_protocols[0].startswith("hq-"):
            self._http = H0Connection(self._quic)
        else:
            self._http = H3Connection(self._quic)

    async def get(self, url: str, headers: Dict = {}) -> Deque[H3Event]:
        """
        Perform a GET request.
        """
        logger.info("Sending GET request %s", url)

        return await self._request(
            HttpRequest(method="GET", url=URL(url), headers=headers)
        )

    async def post(self, url: str, data: bytes, headers: Dict = {}) -> Deque[H3Event]:
        """
        Perform a POST request.
        """
        return await self._request(
            HttpRequest(method="POST", url=URL(url), content=data, headers=headers)
        )

    async def websocket(self, url: str, subprotocols: List[str] = []) -> WebSocket:
        """
        Open a WebSocket.
        """
        request = HttpRequest(method="CONNECT", url=URL(url))
        stream_id = self._quic.get_next_available_stream_id()
        websocket = WebSocket(
            http=self._http, stream_id=stream_id, transmit=self.transmit
        )

        self._websockets[stream_id] = websocket

        headers = [
            (b":method", b"CONNECT"),
            (b":scheme", b"https"),
            (b":authority", request.url.authority.encode()),
            (b":path", request.url.full_path.encode()),
            (b":protocol", b"websocket"),
            (b"user-agent", USER_AGENT.encode()),
            (b"sec-websocket-version", b"13"),
        ]
        if subprotocols:
            headers.append(
                (b"sec-websocket-protocol", ", ".join(subprotocols).encode())
            )
        self._http.send_headers(stream_id=stream_id, headers=headers)

        self.transmit()

        return websocket

    def http_event_received(self, event: H3Event) -> None:
        if isinstance(event, (HeadersReceived, DataReceived)):
            stream_id = event.stream_id
            if stream_id in self._request_events:
                # http
                self._request_events[event.stream_id].append(event)
                if event.stream_ended:
                    request_waiter = self._request_waiter.pop(stream_id)
                    request_waiter.set_result(self._request_events.pop(stream_id))

            elif stream_id in self._websockets:
                # websocket
                websocket = self._websockets[stream_id]
                websocket.http_event_received(event)

            elif event.push_id in self.pushes:
                # push
                self.pushes[event.push_id].append(event)

        elif isinstance(event, PushPromiseReceived):
            self.pushes[event.push_id] = deque()
            self.pushes[event.push_id].append(event)

    def quic_event_received(self, event: QuicEvent) -> None:
        #  pass event to the HTTP layer
        if self._http is not None:
            for http_event in self._http.handle_event(event):
                self.http_event_received(http_event)

    async def _request(self, request: HttpRequest):
        stream_id = self._quic.get_next_available_stream_id()

        if "xx-fbcdn-shv-01" in str(request.url.url):
            logger.info("FACEBOOK INDIA TESTING")
            self._http.send_headers(
                stream_id=stream_id,
                headers=[
                    (b":method", request.method.encode()),
                    (b":scheme", request.url.scheme.encode()),
                    # (b":authority", request.url.authority.encode()), # don't set authority if we're setting host
                    (b":path", request.url.full_path.encode()),
                    (b"user-agent", USER_AGENT.encode()),
                    (b"host", str("scontent.xx.fbcdn.net").encode()),
                    (b"accept", "*/*".encode()),
                ]
                + [(k.encode(), v.encode()) for (k, v) in request.headers.items()],
            )
        else:
            self._http.send_headers(
                stream_id=stream_id,
                headers=[
                    (b":method", request.method.encode()),
                    (b":scheme", request.url.scheme.encode()),
                    (b":authority", request.url.authority.encode()),
                    (b":path", request.url.full_path.encode()),
                    (b"user-agent", USER_AGENT.encode()),
                ]
                + [(k.encode(), v.encode()) for (k, v) in request.headers.items()],
            )

        self._http.send_data(stream_id=stream_id, data=request.content, end_stream=True)

        waiter = self._loop.create_future()
        self._request_events[stream_id] = deque()
        self._request_waiter[stream_id] = waiter
        self.transmit()

        return await asyncio.shield(waiter)


async def perform_http_request(
    client: HttpClient, url: str, data: str, include: bool, output_dir: Optional[str], counter: int, headers: Dict = {}
) -> None:

    if delay_parallel is not 0 and counter is not 0:
        await asyncio.sleep(delay_parallel * counter)
        logger.info("Successfully Delayed parallel request %d by %.1f seconds", counter, counter * delay_parallel)

    # perform request
    start = time.time()
    if data is not None:
        http_events = await client.post(
            url,
            data=data.encode(),
            headers={"content-type": "application/x-www-form-urlencoded"},
        )
    else:
        http_events = await client.get(url=url,headers=headers)
    elapsed = time.time() - start

    # print speed
    octets = 0
    for http_event in http_events:
        if isinstance(http_event, DataReceived):
            octets += len(http_event.data)
    logger.info(
        "Received %d bytes in %.1f s (%.3f Mbps)"
        % (octets, elapsed, octets * 8 / elapsed / 1000000)
    )

    # output response
    if output_dir is not None:
        output_path = os.path.join(
            output_dir, os.path.basename(urlparse(url).path) or "index.html"
        )
        with open(output_path, "wb") as output_file:
            for http_event in http_events:
                if isinstance(http_event, HeadersReceived) and include:
                    headers = b""
                    for k, v in http_event.headers:
                        headers += k + b": " + v + b"\r\n"
                    if headers:
                        output_file.write(headers + b"\r\n")
                elif isinstance(http_event, DataReceived):
                    output_file.write(http_event.data)


def save_session_ticket(ticket: SessionTicket) -> None:
    """
    Callback which is invoked by the TLS engine when a new session ticket
    is received.
    """
    logger.info(">>>>>>>>>>>>>>>>>>>>>>>>>>>")
    logger.info("New session ticket received")
    logger.info("<<<<<<<<<<<<<<<<<<<<<<<<<<<")
    if args.session_ticket:
        with open(args.session_ticket, "wb") as fp:
            pickle.dump(ticket, fp)

    global session_ticket
    session_ticket = ticket

    # logger.info("Session ticket is now")
    logger.info( session_ticket )


async def run(
    configuration: QuicConfiguration,
    urls: List[str],
    data: str,
    include: bool,
    parallel: int,
    output_dir: Optional[str],
) -> None:
    url = urls[0]
    # parse URL
    parsed = urlparse(urls[0])
    assert parsed.scheme in (
        "https",
        "wss",
    ), "Only https:// or wss:// URLs are supported."
    if ":" in parsed.netloc:
        host, port_str = parsed.netloc.split(":")
        port = int(port_str)
    else:
        host = parsed.netloc
        port = 443

    global session_ticket

    async with connect(
        host,
        port,
        configuration=configuration,
        create_protocol=HttpClient,
        session_ticket_handler=save_session_ticket,
    ) as client:
        client = cast(HttpClient, client)

        logger.info( "Session ticket already known here?:" )
        logger.info( session_ticket is not None )

        # perform request
        coros = [
            perform_http_request(
                client=client,
                url=urls[i],
                data=data,
                include=include,
                output_dir=output_dir,
                counter=i
            )
            for i in range(parallel)
        ]
        await asyncio.gather(*coros)

        try: 
            if session_ticket is not None:
                configuration.session_ticket = session_ticket

                logger.info("------------------------------------------")
                logger.info("------------------------------------------")
                logger.info("------------------------------------------")
                logger.info("ATTEMPTING RESUMPTION WITH SESSION TICKET")


                async with connect(
                        host,
                        port,
                        configuration=configuration,
                        create_protocol=HttpClient,
                        session_ticket_handler=save_session_ticket,
                        wait_connected=False
                ) as client2:
                    client2 = cast(HttpClient, client2)

                    logger.info("Attempting 0RTT, not waiting until connected")




                    if configuration.quic_logger is not None:
                        client2._http._quic_logger.log_event( # this gets the correct trace
                            category="transport",
                            event="session_ticket_used",
                            data={
                                "not_valid_after": str(session_ticket.not_valid_after), 
                                "not_valid_before": str(session_ticket.not_valid_before), 
                                "age_add": str(session_ticket.age_add), 
                                "server_name": session_ticket.server_name,
                                "resumption_secret": str(session_ticket.resumption_secret),
                                "cipher_suite": str(session_ticket.cipher_suite),
                                "max_early_data_size": str(session_ticket.max_early_data_size),
                            }
                        )


                    allowance = "sendmemore0rtt_" * 370 # pylsqpack buffer size is 4096 bytes long, string is 15 chars, encodes down to less in utf8, 370 was experimentally defined 

                    # when cache busting on facebook (or other cdns), make sure the second url is different from the first
                    if url.find("?buster=") >= 0:
                        url += "nr2for0rtt"


                    # amplification factor 0 = normal 0-RTT
                    # 1 = 3.5 packets of 0-RTT 
                    # 2 = 7 packets of 0-RTT, split over 2 requests (because pylsqpack doesn't allow very large headers, so we do 2 requests to get the same result)
                    headers = {}
                    # headers["x-fb-debug"] = "True" # works, but headers are encrypted... so useless

                    if zerortt_amplification_factor > 0:
                        headers["x-0rtt-allowance"] = allowance # add a large header to make sure the 0-RTT request spans multiple packets (about 3.5 with the above header size)

                    if zerortt_amplification_factor < 2:
                        await perform_http_request( client=client2, url=url, data=data, headers=headers, include=include, output_dir=output_dir, counter=0 )
                    else:
                        requests2 = [
                            perform_http_request(
                                client=client2,
                                url=url,
                                data=data,
                                include=include,
                                output_dir=output_dir,
                                counter=i,
                                headers=headers,
                            )
                            for i in range(zerortt_amplification_factor)
                        ]
                        await asyncio.gather(*requests2)

                    # response = await client2.get( url=url, headers=headers )
                    # response = await client2.get( "/6000" )
                    # await client2.wait_connected()

                    # logger.info("DONE GETTING STUFF")
                    # logger.info( response )

                    # await client2.wait_connected()

                    if client2._quic.tls.session_resumed:
                        logger.info("SESSION RESUMED SUCCESSFULLY!")
                    else:
                        logger.error("SESSION NOT RESUMED")
                    if client2._quic.tls.early_data_accepted:
                        logger.info("SESSION EARLY_DATA_ACCEPTED SUCCESSFULLY!")
                    else:
                        logger.error("EARLY_DATA NOT ACCEPTED?!?")

                    client2.close()
                    await client2.wait_closed()
                        
            else:
                logger.info("----------------------------------------------------")
                logger.error("No session ticket received, so not doing 0rtt, sorry")
                logger.error( session_ticket )
        except ConnectionError as ce:
            logger.error("Connection error encountered")
            logger.error( ce )


if __name__ == "__main__":
    defaults = QuicConfiguration(is_client=True)

    parser = argparse.ArgumentParser(description="HTTP/3 client")
    parser.add_argument("url", type=str, nargs='?', help="the URL to query (must be HTTPS)")
    parser.add_argument("--urls", action="append", help="specify multiple urls")
    parser.add_argument(
        "--ca-certs", type=str, help="load CA certificates from the specified file"
    )
    parser.add_argument(
        "-d", "--data", type=str, help="send the specified data in a POST request"
    )
    parser.add_argument(
        "-i",
        "--include",
        action="store_true",
        help="include the HTTP response headers in the output",
    )
    parser.add_argument(
        "--max-data",
        type=int,
        help="connection-wide flow control limit (default: %d)" % defaults.max_data,
    )
    parser.add_argument(
        "--max-stream-data",
        type=int,
        help="per-stream flow control limit (default: %d)" % defaults.max_stream_data,
    )
    parser.add_argument(
        "-k",
        "--insecure",
        action="store_true",
        help="do not validate server certificate",
    )
    parser.add_argument("--legacy-http", action="store_true", help="use HTTP/0.9")
    parser.add_argument(
        "--output-dir", type=str, help="write downloaded files to this directory",
    )
    parser.add_argument(
        "-q", "--quic-log", type=str, help="log QUIC events to a file in QLOG format"
    )
    parser.add_argument(
        "-l",
        "--secrets-log",
        type=str,
        help="log secrets to a file, for use with Wireshark",
    )
    parser.add_argument(
        "-s",
        "--session-ticket",
        type=str,
        help="read and write session ticket from the specified file",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="increase logging verbosity"
    )

    parser.add_argument(
        "--delay-parallel", type=float, default=0, help="delay each parallel request by this many seconds"
    )
    parser.add_argument(
        "--parallel", type=int, default=1, help="perform this many requests in parallel"
    )
    parser.add_argument(
        "--amplification-factor", type=int, default=0, help="include additional 0rtt data. 0, 1, or 2"
    )

    args = parser.parse_args()

    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        level=logging.DEBUG if args.verbose else logging.INFO,
    )

    if args.output_dir is not None and not os.path.isdir(args.output_dir):
        raise Exception("%s is not a directory" % args.output_dir)

    # prepare configuration
    configuration = QuicConfiguration(
        is_client=True, alpn_protocols=H0_ALPN if args.legacy_http else H3_ALPN
    )
    if args.ca_certs:
        configuration.load_verify_locations(args.ca_certs)
    if args.insecure:
        configuration.verify_mode = ssl.CERT_NONE
    if args.max_data:
        configuration.max_data = args.max_data
    if args.max_stream_data:
        configuration.max_stream_data = args.max_stream_data
    if args.quic_log:
        configuration.quic_logger = QuicLogger()
    if args.secrets_log:
        configuration.secrets_log_file = open(args.secrets_log, "a")
    if args.session_ticket:
        try:
            with open(args.session_ticket, "rb") as fp:
                configuration.session_ticket = pickle.load(fp)
        except FileNotFoundError:
            pass

    delay_parallel = args.delay_parallel

    if delay_parallel is not 0:
        logger.info("Parallel delay is at %d", delay_parallel)

    if args.urls:
        args.parallel = len( args.urls )
        logger.info("Multiple urls passed, requesting %d", args.parallel)
        logger.info(args.urls)
        if delay_parallel <= 0.0:
            delay_parallel = 0.001 # asyncio doesn't always keep order of launch, so enforce order of urls manually this way

    else:
        if args.parallel and args.parallel > 1:
            args.urls = []
            logger.info("Requesting url in parallel %d times", args.parallel)
            for i in range(args.parallel):
                args.urls.append(args.url)
        else:
            args.urls = [args.url]

    if args.amplification_factor:
        zerortt_amplification_factor = args.amplification_factor
        logger.info("Amplification factor is at %d", zerortt_amplification_factor)

    if uvloop is not None:
        uvloop.install()
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(
            run(
                configuration=configuration,
                urls=args.urls,
                data=args.data,
                include=args.include,
                parallel=args.parallel,
                output_dir=args.output_dir
            )
        )
    finally:
        logger.info("Writing qlog at the end")
        if configuration.quic_logger is not None:
            with open(args.quic_log, "w") as logger_fp:
                json.dump(configuration.quic_logger.to_dict(), logger_fp)
