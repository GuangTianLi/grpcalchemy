"""
    gRPCAlchemy
    ~~~~~

    The Python micro framework for building gPRC application.
"""

__author__ = """GuangTian Li"""
__email__ = 'guangtian_li@qq.com'
__version__ = '0.2.9'

from .blueprint import Blueprint, Context, current_rpc
from .globals import current_app
from .server import Server
