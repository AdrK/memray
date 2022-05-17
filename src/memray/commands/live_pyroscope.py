import argparse
from contextlib import suppress

from memray import SocketReader
from memray._errors import MemrayCommandError
from memray.reporters.pyroscope import Pyroscope

class LivePyroscopeCommand:
    """Remotely monitor allocations through Pyroscope"""

    def prepare_parser(self, parser: argparse.ArgumentParser) -> None:
        #TODO: Name clash?
        parser.add_argument(
            "port",
            help="Remote port to connect to",
            default=None,
            type=int,
        )

    def run(self, args: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
        #TODO: Start pyroscope server?
        #TODO: Handle keyboard interrupts
        with suppress(KeyboardInterrupt):
            self.start_live_interface(args.port)

    def start_uploading(self, port: int) -> None:
        if port >= 2**16 or port <= 0:
            raise MemrayCommandError(f"Invalid port: {port}", exit_code=1)

        with SocketReader(port=port) as reader:
            while True:
                snapshot = list(reader.get_current_snapshot(merge_threads=False))
                Pyroscope.update_snapshot(snapshot, reader.has_native_traces)
