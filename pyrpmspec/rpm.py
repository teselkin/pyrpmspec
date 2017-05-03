
import os
import re
import sh
import yaml

import codecs

class RpmSpecParser(object):
    sections = {
        '_global': {
            'macros': {
                'define': re.compile(r'^%define\s+(.*)\s*$'),
                'global': re.compile(r'^%global\s+(.*)$'),
            },
        },
        '_root': {
            'macros': {
                'description': re.compile(r'^%description\s*$'),
            },
        },
        'description': {
            'keyword': 'description',
            'macros': {
                'description': re.compile(r'^%description\s*$'),
            },
        },
        'package': {
            'keyword': 'package',
            'macros': {
                'description': re.compile(r'^%description\s+(.*)\s*$'),
                'package': re.compile(r'^%package\s+(.*)\s*$'),
            },
        },
        'prep': {
            'keyword': 'prep',
            'macros': {
                'prep': re.compile(r'^%prep\s*$'),
                'setup': re.compile(r'^%setup\s*(.*)\s*$'),
                'patch': re.compile(r'^%patch(\d+)\s+(.*)\s*$'),
            },
        },
        'build': {
            'keyword': 'build',
            'macros': {
                'build': re.compile(r'^%build\s*$'),
            },
        },
        'configure': {
            'keyword': 'configure',
            'macros': {
                'configure': re.compile(r'^%configure\s+(.*)\s*$'),
            },
        },
        'install': {
            'keyword': 'install',
            'macros': {
                'install': re.compile(r'^%install\s*$'),
            },
        },
        'clean': {
            'keyword': 'clean',
            'macros': {
                'clean': re.compile(r'^%clean\s*$'),
            },
        },
        'pre': {
            'keyword': 'pre',
            'macros': {
                'pre': re.compile(r'^%pre\s+(.*)\s*$'),
            },
        },
        'preun': {
            'keyword': 'preun',
            'macros': {
                'preun': re.compile(r'^%preun\s+(.*)\s*$'),
            },
        },
        'post': {
            'keyword': 'post',
            'macros': {
                'post': re.compile(r'^%post\s+(.*)\s*(.*)\s*$'),
            },
        },
        'postun': {
            'keyword': 'postun',
            'macros': {
                'postun': re.compile(r'^%postun\s+(.*)\s*(.*)\s*$'),
            },
        },
        'files': {
            'keyword': 'files',
            'macros': {
                'attr': re.compile(r'^%attr\(.*\).*$'),
                'config': re.compile(r'^%config\(.*\).*'),
                'defattr': re.compile(r'^%defattr\(.*\).*$'),
                'dir': re.compile(r'^%dir\s+(.*)\s*$'),
                'doc': re.compile(r'^%doc\s+(.*)\s*$'),
                'docdir': re.compile(r'^%docdir\s+(.*)\s*$'),
                'files': re.compile(r'^%files\s*(.*)\s*$'),
                'lang': re.compile(r'^%lang\(.*\).*$'),
                'verify': re.compile(r'%verify\s+.*$'),
            },
        },
        'changelog': {
            'keyword': 'changelog',
            'macros': {
                'changelog': re.compile(r'^%changelog\s*$'),
            }
        },
    }

    def __init__(self, use_rpmspec=True):
        self.use_rpmspec = use_rpmspec

    def get_content(self, path):
        specs = []
        for root, dirs, files in os.walk(path):
            for f in files:
                if f.endswith('.spec'):
                    specs.append(os.path.join(root, f))

        for path in specs:
            content = []
            if self.use_rpmspec:
                for line in sh.rpmspec('-P', path):
                    content.append(line.rstrip())
            else:
                print(path)
                for line in codecs.open(path, 'r', 'iso-8859-1'):
                    content.append(line.rstrip())

            yield path, content

    def parse_path(self, path):
        specs = []
        for path, content in self.get_content(path):
            specs.append(self.parse_sections(self.split(content)))
        return specs

    def parse_sections(self, root):
        spec = RpmSpecSourcePackage()
        for section in root:
            if section.name == '_text':
                for lineno, line in section.content:
                    if re.match(r'^\s*(#.*|\%.*|)$', line):
                        continue
                    m = re.match(r'^\s*(?P<key>\w+)\s*:\s*(?P<value>.*)\s*$', line)
                    #kv = [x.strip() for x in line.split(':', maxsplit=1)]
                    #print(line)
                    #if len(kv) > 1:
                    if m:
                        key = m.group('key')
                        value = m.group('value')
                        key_ = key.split('(')[0].lower()
                        if key_.startswith('source'):
                            spec.sources[key] = value
                        elif key_.startswith('patch'):
                            spec.patches[key] = value
                        elif key_ in ['requires', 'buildrequires', 'provides',
                                     'conflicts', 'obsoletes', 'buildconflicts']:
                            spec.get(key_).append(value)
                        else:
                            spec.set(key_, value)
        #print(spec.dump())
        print(yaml.dump(spec.dump(),
                          default_style='',
                          default_flow_style=False))

        return spec

    def split(self, content):
        section = RpmSpecSection()
        section = section.subsection(name='_text')
        lineno = 0
        for linestr in content:
            lineno += 1
            line = (lineno, linestr)
            if re.match(r'^\s*$', line[1]):
                section.content.append(line)
                continue
            if re.match(r'^%\w.*$', line[1]):
                if re.match(r'^%if\s*.*$', line[1]):
                    #if section.name == 'package':
                    #    section = section.parent
                    section = section.subsection(name='if')
                    section.content.append(line)
                    section = section.subsection(name='_then')
                    continue

                if re.match(r'^%else\s*.*$', line[1]):
                    while section.name != 'if':
                        section = section.parent
                    section.content.append(line)
                    section = section.subsection(name='_else')
                    continue

                if re.match(r'^%endif\s*.*$', line[1]):
                    while section.name != 'if':
                        section = section.parent
                    section.content.append(line)
                    if section.parent.name == '_root':
                        section = section.parent.subsection(name='_text')
                    else:
                        section = section.parent
                    continue

                section_name = self._section_name(line[1], section.name)
                if section_name:
                    # line contains new section keyword
                    if section.name == 'if':
                        # 'if' section allows subsections
                        section = section.subsection(section_name)
                    else:
                        # Other sections don't
                        section = section.parent.subsection(section_name)
                    section.content.append(line)
                else:
                    section.content.append(line)
            else:
                section.content.append(line)
        return section.root

    def _section_name(self, line, section=''):
        for name, s in self.sections.items():
            keyword = s.get('keyword', None)
            if keyword is not None:
                regexp = s.get('macros', {}).get(keyword, None)
                if regexp.match(line):
                    return name
        return ''


class RpmSpecSection(object):
    def __init__(self, name='_root', parent=None, root=None):
        self.name = name
        if root is None:
            self._root = self
            self._parent = self
        else:
            self._root = root
            self._parent = parent
        self._subsections = []
        self._content = []

    def __iter__(self):
        for section in self._subsections:
            yield section

    def subsection(self, name):
        if self.name in ['_text', '_then', '_else']:
            section = self._parent.subsection(name)
        else:
            section = RpmSpecSection(name=name, parent=self, root=self.root)
            self._subsections.append(section)
        return section

    @property
    def sections(self):
        return self._subsections[:]

    @property
    def parent(self):
        return self._parent

    @property
    def root(self):
        return self._root

    @property
    def content(self):
        return self._content



class RpmSpecChangelog(object):
    re_rpm_changelog_header = re.compile(r'^\s*\*\s+(\w{3}\s\w{3}\s\d\d?\s\d{4})\s(.+)\s<(.*)>[\s-]+(.*)$')

    def __init__(self):
        self.changes = []

    def parse_spec(self, spec):
        for section in spec.sections:
            if section.name == 'changelog':
                for lineno, line in section.content:
                    match = self.re_rpm_changelog_header.match(line)
                    if match:
                        self.changes.append(RpmSpecChangelogChange(date=match.group(1),
                                                                   author=match.group(2),
                                                                   email=match.group(3),
                                                                   title=match.group(4)))


class RpmSpecChangelogChange(object):
    def __init__(self, date, author, email, title=''):
        self.date = date
        self.author = author
        self.email = email
        self.title = title
        self.comments = []

    def __str__(self):
        return str("{} :: {} :: {} :: {}".format(self.date,
                                                 self.author,
                                                 self.email,
                                                 self.title))


class RpmSpecObjectMixin():
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
        except:
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
                if dump:
                    result[name] = dump(self.__dict__[key])
                else:
                    result[name] = self.__dict__[key]
                if isinstance(result[name], list):
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
    }