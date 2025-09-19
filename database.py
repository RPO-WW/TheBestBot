import logging

LOG = logging.getLogger(__name__)


def _hello_world() -> None:
	LOG.info("Hello world!")


_hello_world()
