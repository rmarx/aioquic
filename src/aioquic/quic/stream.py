from typing import Optional

from . import events
from .packet import QuicStreamFrame
from .packet_builder import QuicDeliveryState
from .rangeset import RangeSet
from .logger import QuicLoggerTrace

import logging
logger = logging.getLogger("client")

class QuicStream:
    def __init__(
        self,
        stream_id: Optional[int] = None,
        max_stream_data_local: int = 0,
        max_stream_data_remote: int = 0,
        quic_logger: Optional[QuicLoggerTrace] = None,
    ) -> None:

        logger.info("stream created %s", str(stream_id))

        self.is_blocked = False
        self.max_stream_data_local = max_stream_data_local
        self.max_stream_data_local_sent = max_stream_data_local
        self.max_stream_data_remote = max_stream_data_remote
        self.send_buffer_is_empty = True

        self._recv_buffer = bytearray()
        self._recv_buffer_fin: Optional[int] = None
        self._recv_buffer_start = 0  # the offset for the start of the buffer
        self._recv_highest = 0  # the highest offset ever seen
        self._recv_ranges = RangeSet()

        self._send_acked = RangeSet()
        self._send_buffer = bytearray()
        self._send_buffer_fin: Optional[int] = None
        self._send_buffer_start = 0  # the offset for the start of the buffer
        self._send_buffer_stop = 0  # the offset for the stop of the buffer
        self._send_highest = 0
        self._send_pending = RangeSet()
        self._send_pending_eof = False

        self._quic_logger = quic_logger

        self.__stream_id = stream_id

    @property
    def stream_id(self) -> Optional[int]:
        return self.__stream_id

    # reader

    def add_frame(self, frame: QuicStreamFrame) -> Optional[events.StreamDataReceived]:
        """
        Add a frame of received data.
        """
        pos = frame.offset - self._recv_buffer_start
        count = len(frame.data)
        frame_end = frame.offset + count

        extralogging = False
        if self.stream_id is not None and self.stream_id % 4 is 0:
            extralogging = True

        # if frame.offset < self._recv_buffer_start:
        #     if extralogging:
        #         # never actually seen this during testing so far
        #         logger.info("///////////////////////////////////////////////////////////////////////////////")
        #         logger.info("%d : offset before highest received, indicates duplicate! %d %d", self.stream_id, frame.offset, self._recv_highest)

        # we should receive no more data beyond FIN!
        if self._recv_buffer_fin is not None and frame_end > self._recv_buffer_fin:
            raise Exception("Data received beyond FIN")
        if frame.fin:
            self._recv_buffer_fin = frame_end
        if frame_end > self._recv_highest:
            self._recv_highest = frame_end
        # else:
        #     if extralogging:
        #         logger.info("\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\/")
        #         logger.info("%d : !!frame_end before highest received, indicates duplicate! %d %d", self.stream_id, frame.offset, self._recv_highest)



        # if extralogging:
        #    logger.info("%d : add_frame %d %d", self.stream_id, frame.offset, count)

        # fast path: new in-order chunk
        if pos == 0 and count and not self._recv_buffer:
            # if extralogging:
            #   logger.info("%d : add_frame fast path : %d %d %d. Highest received: %d", self.stream_id, frame.offset, count, frame.offset + count, self._recv_highest)

            if self._quic_logger is not None:
                self._quic_logger.log_event(
                    category="http",
                    event="data_moved",
                    data=self._quic_logger.encode_data_moved_from_quic(
                        stream_id=self.stream_id,
                        offset=frame.offset,
                        length=len(frame.data)
                    ),
                )

            self._recv_buffer_start += count
            return events.StreamDataReceived(
                data=frame.data, end_stream=frame.fin, stream_id=self.__stream_id
            )

        # discard duplicate data
        if pos < 0:
            # if extralogging:
            #     # never actually seen this during testing so far
            #     logger.info("--------------------------------------------------------------------------------------")
            #     logger.info("%d : add_frame discard duplicates : %d %d %d", self.stream_id, frame.offset, count, pos)
            frame.data = frame.data[-pos:]
            frame.offset -= pos
            pos = 0

        # marked received range
        if frame_end > frame.offset:
            self._recv_ranges.add(frame.offset, frame_end, extralogging)
            # if extralogging:
            #     logger.info("%d : add_frame : added range %d -> %d", self.stream_id, frame.offset, frame_end)
            #     logger.info("%d : add_frame : open ranges now %s", self.stream_id, self._recv_ranges.__repr__())
        # else:
        #     if extralogging:
        #         logger.info("--------------------------------------------------------------------------------------")
        #         logger.info("%d : TODO VERIFY : add_frame probably duplicate : %d %d", self.stream_id, frame_end, frame.offset)

        # add new data
        gap = pos - len(self._recv_buffer)
        if gap > 0:
            self._recv_buffer += bytearray(gap)
        # if extralogging:
            # logger.info("%d : add_frame appending to recvbuffer : should be %d, offset is actually %d (diff %d). %d %d. buffer len %d. highest received: %d", self.stream_id, self._recv_buffer_start, frame.offset, pos, count, gap, len(self._recv_buffer), self._recv_highest)
            # logger.info("%d : add_frame : open ranges now %s", self.stream_id, self._recv_ranges.__repr__())
        self._recv_buffer[pos : pos + count] = frame.data

        # return data from the front of the buffer
        data = self._pull_data()
        end_stream = self._recv_buffer_start == self._recv_buffer_fin
        if data or end_stream:
            return events.StreamDataReceived(
                data=data, end_stream=end_stream, stream_id=self.__stream_id
            )
        else:
            return None

    def _pull_data(self) -> bytes:
        """
        Remove data from the front of the buffer.
        """
        try:
            has_data_to_read = self._recv_ranges[0].start == self._recv_buffer_start
        except IndexError:
            has_data_to_read = False
        if not has_data_to_read:
            return b""


        # extralogging = False
        # if self.stream_id is not None and self.stream_id % 4 is 0:
        #     extralogging = True


        r = self._recv_ranges.shift()
        pos = r.stop - r.start
        data = bytes(self._recv_buffer[:pos])
        del self._recv_buffer[:pos]
        self._recv_buffer_start = r.stop

        if self._quic_logger is not None:
            self._quic_logger.log_event(
                category="http",
                event="data_moved",
                data=self._quic_logger.encode_data_moved_from_quic(
                    stream_id=self.stream_id,
                    offset=r.start,
                    length=len(data)
                ),
            )

        # if extralogging:
        #     logger.info("%d : _pull_data : amount %d, buffer start was at %d, is now at %d, total bytes buffered %d", self.stream_id, len(data), r.start, self._recv_buffer_start, len(self._recv_buffer))
            # logger.info("%d : _pull_data : COUNTS : %d vs %d", self.stream_id, self.DEBUG_normalCount, self.DEBUG_bufferedCount)

        return data

    # writer

    @property
    def next_send_offset(self) -> int:
        """
        The offset for the next frame to send.

        This is used to determine the space needed for the frame's `offset` field.
        """
        try:
            return self._send_pending[0].start
        except IndexError:
            return self._send_buffer_stop

    def get_frame(
        self, max_size: int, max_offset: Optional[int] = None
    ) -> Optional[QuicStreamFrame]:
        """
        Get a frame of data to send.
        """
        # get the first pending data range
        try:
            r = self._send_pending[0]
        except IndexError:
            if self._send_pending_eof:
                # FIN only
                self._send_pending_eof = False
                return QuicStreamFrame(fin=True, offset=self._send_buffer_fin)

            self.send_buffer_is_empty = True
            return None

        # apply flow control
        start = r.start
        stop = min(r.stop, start + max_size)
        if max_offset is not None and stop > max_offset:
            stop = max_offset
        if stop <= start:
            return None

        # create frame
        frame = QuicStreamFrame(
            data=bytes(
                self._send_buffer[
                    start - self._send_buffer_start : stop - self._send_buffer_start
                ]
            ),
            offset=start,
        )
        self._send_pending.subtract(start, stop)

        # track the highest offset ever sent
        if stop > self._send_highest:
            self._send_highest = stop

        # if the buffer is empty and EOF was written, set the FIN bit
        if self._send_buffer_fin == stop:
            frame.fin = True
            self._send_pending_eof = False

        return frame

    def on_data_delivery(
        self, delivery: QuicDeliveryState, start: int, stop: int
    ) -> None:
        """
        Callback when sent data is ACK'd.
        """
        self.send_buffer_is_empty = False
        if delivery == QuicDeliveryState.ACKED:
            if stop > start:
                self._send_acked.add(start, stop)
                first_range = self._send_acked[0]
                if first_range.start == self._send_buffer_start:
                    size = first_range.stop - first_range.start
                    self._send_acked.shift()
                    self._send_buffer_start += size
                    del self._send_buffer[:size]
        else:
            if stop > start:
                self._send_pending.add(start, stop)
            if stop == self._send_buffer_fin:
                self.send_buffer_empty = False
                self._send_pending_eof = True

    def write(self, data: bytes, end_stream: bool = False) -> None:
        """
        Write some data bytes to the QUIC stream.
        """
        assert self._send_buffer_fin is None, "cannot call write() after FIN"
        size = len(data)

        if size:
            self.send_buffer_is_empty = False
            self._send_pending.add(
                self._send_buffer_stop, self._send_buffer_stop + size
            )
            self._send_buffer += data
            self._send_buffer_stop += size
        if end_stream:
            self.send_buffer_is_empty = False
            self._send_buffer_fin = self._send_buffer_stop
            self._send_pending_eof = True
