from threading import Thread
from queue import Queue, Empty
import logging
import subprocess


def run_subprocess_and_log(cmd_l, cwd=None, logger_name=None, encoding=None):
    logger = logging.getLogger(__name__ if logger_name is None else logger_name)
    encoding = "latin-1" if encoding is None else encoding
    p = subprocess.Popen(cmd_l, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=cwd)
    out_reader = NonBlockingStreamReader(p.stdout)
    err_reader = NonBlockingStreamReader(p.stderr)

    while True:
        out = out_reader.readline(0.1)
        if out is not None:
            logger.info(out.decode(encoding).strip())

        err = err_reader.readline(0.1)
        if err is not None:
            logger.error(err.decode(encoding).strip())

        if p.poll() is not None:
            break


class NonBlockingStreamReader:
    def __init__(self, stream):
        """
        stream: the stream to read from.
                Usually a process' stdout or stderr.
        """

        self._s = stream
        self._q = Queue()

        def _populate_queue(stream, queue):
            """
            Collect lines from 'stream' and put them in 'quque'.
            """

            while True:
                line = stream.readline()
                if line:
                    queue.put(line)
                else:
                    break

        self._t = Thread(target=_populate_queue, args=(self._s, self._q))
        self._t.daemon = True
        self._t.start()  # start collecting lines from the stream

    def readline(self, timeout=None):
        try:
            return self._q.get(block=timeout is not None, timeout=timeout)
        except Empty:
            return None