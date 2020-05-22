import functools
import warnings


class GeogeniusDeprecation(DeprecationWarning):
    pass


warnings.simplefilter("ignore", DeprecationWarning)
warnings.simplefilter("always", GeogeniusDeprecation)


def deprecation(message):
    warnings.warn(message, GeogeniusDeprecation)


def deprecate_module_attr(mod, deprecated):
    """Return a wrapped object that warns about deprecated accesses"""
    deprecated = set(deprecated)

    class Wrapper(object):
        def __getattr__(self, attr):
            if attr in deprecated:
                warnings.warn("Property {} is deprecated".format(attr), GeogeniusDeprecation)

            return getattr(mod, attr)

        def __setattr__(self, attr, value):
            if attr in deprecated:
                warnings.warn("Property {} is deprecated".format(attr), GeogeniusDeprecation)
            return setattr(mod, attr, value)

    return Wrapper()


def deprecate_class(klass, dep_name):
    @functools.wraps(klass)
    def wrappedklass(*args, **kwargs):
        warnings.simplefilter("ignore", DeprecationWarning)
        warnings.simplefilter("always", GeogeniusDeprecation)
        warnings.warn("Class {} has been deprecated, use {} instead".format(dep_name, klass.__name__),
                      GeogeniusDeprecation)
        warnings.simplefilter("default", GeogeniusDeprecation)
        return klass(*args, **kwargs)

    return wrappedklass
