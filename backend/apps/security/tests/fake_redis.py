"""Minimal in-process Redis double for hermetic auth-protection tests.

Implements exactly the commands the security modules use, including a Python
equivalent of the two Lua scripts (progressive lockout + reputation penalty).
The REAL Lua is validated separately against real Redis by
``scripts/verify_edge_security.py`` / ``verify_auth_protection.py``; this double
only needs to exercise the Python module logic (counting, tiers, TTL checks,
set cardinality, NX semantics) deterministically in CI.

TTL is modelled as "seconds remaining as last set" (no wall-clock decay), which
is all the module logic under test inspects.
"""
from apps.security import progressive, reputation


class _Pipeline:
    def __init__(self, store):
        self._store = store
        self._ops = []

    def __getattr__(self, name):
        def _record(*args, **kwargs):
            self._ops.append((name, args, kwargs))
            return self
        return _record

    def execute(self):
        results = []
        for name, args, kwargs in self._ops:
            results.append(getattr(self._store, name)(*args, **kwargs))
        self._ops = []
        return results


class FakeRedis:
    def __init__(self):
        self.kv = {}          # key -> value
        self.sets = {}        # key -> set()
        self.ttl_map = {}     # key -> seconds remaining (as last set)

    # -- strings/counters ------------------------------------------------- #
    def incrby(self, key, amount=1):
        self.kv[key] = int(self.kv.get(key, 0)) + int(amount)
        return self.kv[key]

    def get(self, key):
        val = self.kv.get(key)
        return None if val is None else str(val)

    def set(self, key, value, nx=False, ex=None, px=None):
        if nx and key in self.kv:
            return None
        self.kv[key] = value
        if ex is not None:
            self.ttl_map[key] = int(ex)
        elif px is not None:
            self.ttl_map[key] = max(1, int(px) // 1000)
        return True

    def expire(self, key, seconds):
        if key in self.kv or key in self.sets:
            self.ttl_map[key] = int(seconds)
            return True
        return False

    def ttl(self, key):
        if key not in self.kv and key not in self.sets:
            return -2
        return self.ttl_map.get(key, -1)

    def exists(self, *keys):
        return sum(1 for k in keys if k in self.kv or k in self.sets)

    def delete(self, *keys):
        removed = 0
        for key in keys:
            removed += 1 if (self.kv.pop(key, None) is not None
                             or self.sets.pop(key, None) is not None) else 0
            self.ttl_map.pop(key, None)
        return removed

    # -- sets ------------------------------------------------------------- #
    def scard(self, key):
        return len(self.sets.get(key, set()))

    def sadd(self, key, *members):
        bucket = self.sets.setdefault(key, set())
        before = len(bucket)
        bucket.update(members)
        return len(bucket) - before

    def spop(self, key, count=1):
        bucket = self.sets.get(key, set())
        popped = []
        for _ in range(count):
            if not bucket:
                break
            popped.append(bucket.pop())
        return popped

    # -- pipeline / lua --------------------------------------------------- #
    def pipeline(self, transaction=True):
        return _Pipeline(self)

    def eval(self, script, numkeys, *args):
        keys = args[:numkeys]
        argv = args[numkeys:]
        if script == progressive._FAIL_LUA:
            fail_key, block_key = keys
            window = int(argv[0])
            num_tiers = int(argv[1])
            tiers = argv[2:]
            count = self.incrby(fail_key, 1)
            self.expire(fail_key, window)
            block = 0
            for i in range(num_tiers):
                threshold = int(tiers[i * 2])
                duration = int(tiers[i * 2 + 1])
                if count >= threshold:
                    block = duration
            if block > 0:
                self.set(block_key, count, ex=block)
            return [count, block]
        if script == reputation._PENALIZE_LUA:
            score_key, block_key = keys
            points, decay, threshold, block_seconds = (int(a) for a in argv[:4])
            score = self.incrby(score_key, points)
            self.expire(score_key, decay)
            if score >= threshold:
                self.set(block_key, score, ex=block_seconds)
            return score
        raise NotImplementedError("FakeRedis.eval: unrecognised script")

    def ping(self):
        return True
