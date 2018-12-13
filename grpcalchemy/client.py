class Client:

    def __init__(self, target, credentials=None, options=None):
        from grpc import _channel  # pylint: disable=cyclic-import

        self.channel = _channel.Channel(target, () if options is None else options, credentials)


    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.channel._close()
        return False



