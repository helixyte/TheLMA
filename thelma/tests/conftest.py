"""
"""
import collections
from itertools import chain

from _pytest.python import getfixturemarker
import pytest

from everest.entities.base import Entity


__docformat__ = 'reStructuredText en'
__all__ = []


class Fixture(object):
    __count = 0
    def __init__(self, value_cls, args=None, kw=None):
        """
        Constructor.

        :param value_cls: Value class of the fixture.
        :param tuple args: Positional arguments to pass to the factory.
        :param dict kw: Keyword arguments to pass to the factory.
        :note: The positional and keyword arguments may contain references to
            other :class:`Fixture` objects which will be resolved when the
            fixture is used for the first time.
        """
        #: Counter enabling sorting of fixtures by sequence of instantiation.
        self.count = Fixture.__count
        self.value_cls = value_cls
        if args is None:
            args = ()
        self.args = args
        if kw is None:
            kw = {}
        self.kw = kw
        Fixture.__count += 1
        self.__resolved = False

    def resolve_parameters(self, request):
        if (len(self.args) > 0 or len(self.kw) > 0) and not self.__resolved:
            self.args = self.__resolve_parameters(self.args, request)
            self.kw = self.__resolve_parameters(self.kw, request)
            self.__resolved = True

    def __resolve_parameters(self, params, request):
        if isinstance(params, collections.Mapping):
            result = dict(self.__resolve_parameters(params.items(), request))
        else:
            new_params = []
            for param in params:
                if isinstance(param, Fixture):
                    fixture_func = getattr(request.module, param.name)
                    new_param = \
                        request.getfuncargvalue(fixture_func.func_name)
                else:
                    if isinstance(param, (list, tuple, set)):
                        new_param = self.__resolve_parameters(param, request)
                    elif not getfixturemarker(param) is None:
                        new_param = request.getfuncargvalue(param.func_name)
                    else:
                        new_param = param
                new_params.append(new_param)
            result = type(params)(new_params)
        return result


class TestObjectFactory(object):
    def __init__(self, entity_generator_func, args=None, kw=None):
        self.__entity_generator_func = entity_generator_func
        if args is None:
            args = ()
        self.__init_args = args
        if kw is None:
            kw = {}
        self.__init_kw = kw
        self.__instances = {}

    def __call__(self, *args, **kw):
        _args = args + self.__init_args[len(args):]
        _kw = self.__init_kw.copy()
        _kw.update(kw)
        key = tuple(chain((id(arg) for arg in _args),
                          ((k, id(v)) for (k, v) in sorted(_kw.items()))))
        try:
            obj = self.__instances[key]
        except KeyError:
            obj = self.__entity_generator_func(*_args, **_kw)
            self.__instances[key] = obj
        return obj

    def new(self, *args, **kw):
        _args = args + self.__init_args[len(args):]
        _kw = self.__init_kw.copy()
        _kw.update(kw)
        return self.__entity_generator_func(*_args, **_kw)

    @property
    def init_args(self):
        return self.__init_args

    @property
    def init_kw(self):
        return self.__init_kw.copy()


@pytest.fixture
def test_object_fac(): # pylint: disable=W0613
    return TestObjectFactory


def make_fixture(fixture):
    @pytest.fixture(scope='function')
    def func(request, fixture_factory_registry):
        # Convert fixture parameters (args and kw).
        fixture.resolve_parameters(request)
        fac_fixture = fixture_factory_registry.get(fixture.value_cls)
        if fac_fixture is None:
            # If there is no factory, we use the specified value class
            # directly (unless it is an entity subclass in which case we
            # expect a factory to be registered).
            if callable(fixture.value_cls) \
               and not issubclass(fixture.value_cls, Entity):
                value = fixture.value_cls(*fixture.args, **fixture.kw)
            else:
                raise RuntimeError('No factory registered for class %s.'
                                   % fixture.value_cls)
        else:
            fac = request.getfuncargvalue(fac_fixture.func_name)
            value = fac.new(*fixture.args, **fixture.kw)
        return value
    func.func_name = fixture.name
    return func


def pytest_pycollect_makemodule(path, parent):
    mod = path.pyimport()
    fixtures = getattr(mod, 'Fixtures', None)
    if not fixtures is None:
        fixture_map = dict([item
                            for item in fixtures.__dict__.items()
                            if isinstance(item[-1], Fixture)])
        for fx_name, fx_inst in sorted(fixture_map.items(),
                                       key=lambda item: item[-1].count):
            fx_inst.name = fx_name
            func = make_fixture(fx_inst)
            # Make the newly created fixture discoverable by pytest.
            setattr(mod, fx_name, func)
    return pytest.Module(path, parent)
