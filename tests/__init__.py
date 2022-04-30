try:
    from motoapi.tests.test_motoapi import suite
except ImportError:
    from .test_motoapi import suite

__all__ = ['suite']
