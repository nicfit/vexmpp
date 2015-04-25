# -*- coding: utf-8 -*-
import math
import logging
from collections import OrderedDict

log = logging.getLogger(__name__)


class BaseMetric:
    def __init__(self, name, type_=int):
        self.name = name
        self._value = type_()
        self._type = type_

    @property
    def value(self):
        return self._value

    def update(self, val):
        raise NotImplementedError()

    def __str__(self):
        return "<{name}>{_value}</{name}>".format(**self.__dict__)


class CounterMetric(BaseMetric):
    def update(self, val):
        self._value = val

    def inc(self, val=1):
        self._value += val

    def dec(self, val=1):
        self._value -= val


class ValueMetric(BaseMetric):
    def __init__(self, name, initial_val=None, type_=None):
        if type_ is None:
            if initial_val is not None:
                type_ = type(type_)
            else:
                type_ = int
        super().__init__(name, type_)

        self._count = 0
        self._min, self._max = None, None
        self._total = 0
        self._total_squared = 0
        if initial_val is not None:
            self.update(initial_val)

    def update(self, val):
        self._total += val
        self._total_squared += val * val
        self._min = min(val, self._min) if self._min is not None else val
        self._max = max(val, self._max) if self._max is not None else val

        self._count += 1
        self._value = val

    @property
    def min(self):
        return self._min

    @property
    def max(self):
        return self._max

    @property
    def average(self):
        try:
            return self._total / self._count
        except ZeroDivisionError:
            return None

    # http://stackoverflow.com/questions/5543651/
    #      computing-standard-deviation-in-a-stream
    @property
    def stdev(self):
        s0 = self._count
        s1 = self._total
        s2 = self._total_squared
        try:
            return math.sqrt((s0 * s2 - s1 * s1) / (s0 * (s0 - 1)))
        except ZeroDivisionError:
            return None


class MetricsGroup(object):
    def __init__(self, name):
        self.name = name
        self._metrics = OrderedDict()

    def add(self, s):
        self._metrics[s.name] = s
        return s

    @property
    def metrics(self):
        return [m for m in self._metrics]

    def __str__(self):
        stats = ''.join([str(s) for s in self._metrics.values()])
        return "<{name}>{stats}</{name}>".format(name=self.name, stats=stats)

    def __getitem__(self, key):
        return self._metrics[key]

    def valueDict(self):
        metric_vals = {}
        for n, v in self._metrics.items():
            metric_vals[n] = v.value
        return metric_vals

    @classmethod
    def fromString(clazz, s):
        instance = clazz()

        # currently XML, meh
        from lxml import etree
        try:
            metrics_elem = etree.fromstring(s)
            metrics_elem = metrics_elem.xpath("/metrics/%s" % clazz.__name__)[0]
            for elem in metrics_elem.getchildren():
                m = instance[elem.tag]
                m.update(m._type(elem.text))
        except Exception as ex:
            raise ValueError("{} : {}".format(s, str(ex)))

        return instance
