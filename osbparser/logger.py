import logging

__all__ = ["log"]

logging.basicConfig(format='[%(name)s] %(levelname)s: %(message)s')

log = logging.getLogger("osbparser")
log.setLevel("DEBUG")
