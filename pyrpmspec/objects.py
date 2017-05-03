

class RpmSpecObjectMixin(object):
    def __getattr__(self, item):
        obj = self._schema[item]
        if obj.get('private', False):
            return self.__dict__[item]
        else:
            return self.__dict__.setdefault(item, eval(obj['default'])()
                                            if obj.get('callable', False)
                                            else obj['default'])

    def __setattr__(self, key, value):
        obj = self._schema[key]
        if obj.get('private', False):
            self.__dict__[key] = value
            return
        type_ = obj['type']
        if isinstance(value, eval(type_)):
            self.__dict__[key] = value
        else:
            raise Exception("Wrong type")

    def __delattr__(self, item):
        self.__dict__.pop(item, None)

    def get(self, key, default=Exception()):
        try:
            return getattr(self, key)
        except Exception:
            if isinstance(default, Exception):
                raise Exception("Key '{}' not found".format(key))
            else:
                return default

    def set(self, key, value):
        setattr(self, key, value)

    def dump(self, keys=None, exclude=[]):
        result = {}
        if keys is None:
            keys = self._schema.keys()
        for key in keys:
            if key in exclude:
                continue
            if self._schema[key].get('private', False):
                continue
            if key in self.__dict__:
                schema = self._schema[key]
                name = schema.get('name', key)
                dump = schema.get('dump', None)
                sorted = schema.get('sorted', True)
                if dump:
                    result[name] = dump(self.__dict__[key])
                else:
                    result[name] = self.__dict__[key]
                if isinstance(result[name], list):
                    if sorted:
                        result[name].sort()
        return result

    def load(self, data, keys=None):
        if keys is None:
            keys = data.keys()
        for name in keys:
            key = name.replace('-', '_')
            if self._schema[key].get('private', False):
                continue
            value = data[name]
            schema = self._schema[key]
            if schema.get('callable', False):
                self.__dict__[key] = eval(schema['default'])()
                loader = schema.get('load', None)
                if loader:
                    self.__dict__[key] = loader(value)
                else:
                    self.__dict__[key].load(value)
            else:
                if isinstance(value, list):
                    self.__dict__[key] = value[:]
                elif isinstance(value, dict):
                    self.__dict__[key] = {}.update(value)
                else:
                    self.__dict__[key] = value
        return self


class RpmSpecSourcePackage(RpmSpecObjectMixin):
    _schema = {
        'name': {
            'default': '',
            'type': 'str',
        },
        'version': {
            'default': '',
            'type': 'str',
        },
        'release': {
            'default': '',
            'type': 'str',
        },
        'epoch': {
            'default': '',
            'type': 'str',
        },
        'summary': {
            'default': '',
            'type': 'str',
        },
        'group': {
            'default': '',
            'type': 'str',
        },
        'license': {
            'default': '',
            'type': 'str',
        },
        'url': {
            'default': '',
            'type': 'str',
        },
        'buildarch': {
            'default': '',
            'type': 'str',
        },
        'excludearch': {
            'default': '',
            'type': 'str',
        },
        'exclusivearch': {
            'default': '',
            'type': 'str',
        },
        'packager': {
            'default': '',
            'type': 'str',
        },
        'vcs': {
            'default': '',
            'type': 'str',
        },
        'buildroot': {
            'default': '',
            'type': 'str',
        },
        'vendor': {
            'default': '',
            'type': 'str',
        },
        'prefix': {
            'default': '',
            'type': 'str',
        },
        'autoreq': {
            'default': '',
            'type': 'str',
        },
        'autoreqprov': {
            'default': '',
            'type': 'str',
        },
        'sources': {
            'default': 'dict',
            'callable': True,
        },
        'patches': {
            'default': 'dict',
            'callable': True,
        },
        'description': {
            'default': 'list',
            'callable': True,
        },
        'buildrequires': {
            'default': 'list',
            'callable': True,
        },
        'requires': {
            'default': 'list',
            'callable': True,
        },
        'provides': {
            'default': 'list',
            'callable': True,
        },
        'conflicts': {
            'default': 'list',
            'callable': True,
        },
        'obsoletes': {
            'default': 'list',
            'callable': True,
        },
        'buildconflicts': {
            'default': 'list',
            'callable': True,
        },
        'changelog': {
            'default': 'list',
            'callable': True,
            'sorted': False,
            'dump': lambda x: [xx.dump() for xx in x],
        }
    }


class RpmSpecChangelogChange(RpmSpecObjectMixin):
    _schema = {
        'date': {
            'default': '',
            'type': 'str',
        },
        'author': {
            'default': '',
            'type': 'str',
        },
        'author_email': {
            'default': '',
            'type': 'str',
        },
        'title': {
            'default': '',
            'type': 'str',
        },
    }
