import sys

from .globals import _app_ctx_stack


class AppContext:
    """The application context binds an application object implicitly
    to the current thread or greenlet.

    .. versionchanged:: 0.2.4
    """

    def __init__(self, app):
        self.app = app

    def push(self):
        """Binds the app context to the current context."""
        if hasattr(sys, 'exc_clear'):
            sys.exc_clear()
        _app_ctx_stack.push(self)

    def pop(self):
        """Pops the app context."""
        rv = _app_ctx_stack.pop()
        assert rv is self, 'Popped wrong app context.  (%r instead of %r)' \
            % (rv, self)

    def __enter__(self):
        self.push()
        return self

    def __exit__(self, exc_type, exc_value, tb):
        self.pop()

        if exc_type is not None:
            if exc_value.__traceback__ is not tb:
                raise exc_value.with_traceback(tb)
            raise exc_value
