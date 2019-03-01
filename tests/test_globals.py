import time
import unittest
from concurrent.futures.thread import ThreadPoolExecutor

from grpcalchemy.globals import Local, LocalProxy, LocalStack, release_local


class GlobalsTestCase(unittest.TestCase):
    def test_basic_local(self):
        ns = Local()
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

        release_local(ns)

    def test_local_release(self):
        ns = Local()
        ns.foo = 42
        release_local(ns)
        assert not hasattr(ns, 'foo')

        ls = LocalStack()
        ls.push(42)
        release_local(ls)
        assert ls.top is None

    def test_local_proxy(self):
        foo = []
        ls = LocalProxy(lambda: foo)
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
        ls = LocalProxy(lambda: foo)
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


if __name__ == '__main__':
    unittest.main()
