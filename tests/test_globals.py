import copy
import time
import unittest
from concurrent.futures.thread import ThreadPoolExecutor
from functools import partial

from grpcalchemy import globals


class GlobalsTestCase(unittest.TestCase):
    def test_basic_local(self):
        ns = globals.Local()
        ns.foo = 0
        values = []

        def value_setter(idx):
            time.sleep(0.01 * idx)
            ns.foo = idx
            time.sleep(0.02)
            values.append(ns.foo)

        with ThreadPoolExecutor(max_workers=5) as worker:
            worker.map(value_setter, [1, 2, 3])
        time.sleep(0.2)
        self.assertListEqual([1, 2, 3], sorted(values))

        def delfoo():
            del ns.foo

        delfoo()
        with self.assertRaises(AttributeError):
            ns.foo
        with self.assertRaises(AttributeError):
            delfoo()

        globals.release_local(ns)

    def test_local_release(self):
        ns = globals.Local()
        ns.foo = 42
        globals.release_local(ns)
        assert not hasattr(ns, 'foo')

        ls = globals.LocalStack()
        ls.push(42)
        globals.release_local(ls)
        assert ls.top is None

    def test_local_proxy(self):
        foo = []
        ls = globals.LocalProxy(lambda: foo)
        ls.append(42)
        ls.append(23)
        ls[1:] = [1, 2, 3]
        assert foo == [42, 1, 2, 3]
        assert repr(foo) == repr(ls)
        assert foo[0] == 42
        foo += [1]
        assert list(foo) == [42, 1, 2, 3, 1]

    def test_local_proxy_operations_math(self):
        foo = 2
        ls = globals.LocalProxy(lambda: foo)
        assert ls + 1 == 3
        assert 1 + ls == 3
        assert ls - 1 == 1
        assert 1 - ls == -1
        assert ls * 1 == 2
        assert 1 * ls == 2
        assert ls / 1 == 2
        assert 1.0 / ls == 0.5
        assert ls // 1.0 == 2.0
        assert 1.0 // ls == 0.0
        assert ls % 2 == 0
        assert 2 % ls == 0

    def test_local_proxy_operations_strings(self):
        foo = "foo"
        ls = globals.LocalProxy(lambda: foo)
        assert ls + "bar" == "foobar"
        assert "bar" + ls == "barfoo"
        assert ls * 2 == "foofoo"

        foo = "foo %s"
        assert ls % ("bar", ) == "foo bar"

    def test_local_stack(self):
        ident = globals.get_ident()

        ls = globals.LocalStack()
        assert ident not in ls._local.__storage__
        assert ls.top is None
        ls.push(42)
        assert ident in ls._local.__storage__
        assert ls.top == 42
        ls.push(23)
        assert ls.top == 23
        ls.pop()
        assert ls.top == 42
        ls.pop()
        assert ls.top is None
        assert ls.pop() is None
        assert ls.pop() is None

        proxy = ls()
        ls.push([1, 2])
        assert proxy == [1, 2]
        ls.push((1, 2))
        assert proxy == (1, 2)
        ls.pop()
        ls.pop()
        assert repr(proxy) == '<LocalProxy unbound>'

        assert ident not in ls._local.__storage__

    def test_local_proxies_with_callables(self):
        foo = 42
        ls = globals.LocalProxy(lambda: foo)
        assert ls == 42
        foo = [23]
        ls.append(42)
        assert ls == [23, 42]
        assert foo == [23, 42]

    def test_deepcopy_on_proxy(self):
        class Foo:
            attr = 42

            def __copy__(self):
                return self

            def __deepcopy__(self, memo):
                return self

        f = Foo()
        p = globals.LocalProxy(lambda: f)
        assert p.attr == 42
        assert copy.deepcopy(p) is f
        assert copy.copy(p) is f

        a = []
        p2 = globals.LocalProxy(lambda: [a])
        assert copy.copy(p2) == [a]
        assert copy.copy(p2)[0] is a

        assert copy.deepcopy(p2) == [a]
        assert copy.deepcopy(p2)[0] is not a

    def test_local_proxy_wrapped_attribute(self):
        class SomeClassWithWrapped:
            __wrapped__ = 'wrapped'

        def lookup_func():
            return 42

        partial_lookup_func = partial(lookup_func)

        proxy = globals.LocalProxy(lookup_func)
        assert proxy.__wrapped__ is lookup_func

        partial_proxy = globals.LocalProxy(partial_lookup_func)
        assert partial_proxy.__wrapped__ == partial_lookup_func

        ns = globals.Local()
        ns.foo = SomeClassWithWrapped()
        ns.bar = 42

        assert ns('foo').__wrapped__ == 'wrapped'
        with self.assertRaises(AttributeError):
            ns('bar').__wrapped__()


if __name__ == '__main__':
    unittest.main()
