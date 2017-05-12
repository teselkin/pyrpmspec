#!/usr/bin/python

import os
import re
import sh

import codecs

from pyrpmspec.objects import RpmSpec
from pyrpmspec.objects import RpmSpecChangelogChange


class RpmSpecParser(object):
    sections = {
        '_global': {
            'macros': {
                'define': re.compile(r'^%define\s+(?P<args>.*)\s*$'),
                'global': re.compile(r'^%global\s+(?P<args>.*)$'),
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
                'description': re.compile(r'^%description\s+(?P<args>.*)\s*$'),
                'package': re.compile(r'^%package\s+(?P<args>.*)\s*$'),
            },
        },
        'prep': {
            'keyword': 'prep',
            'macros': {
                'prep': re.compile(r'^%prep\s*$'),
                'setup': re.compile(r'^%setup\s*(?P<args>.*)\s*$'),
                'patch': re.compile(r'^%patch(\d+)\s+(?P<args>.*)\s*$'),
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
                'configure': re.compile(r'^%configure\s+(?P<args>.*)\s*$'),
            },
        },
        'install': {
            'keyword': 'install',
            'macros': {
                'install': re.compile(r'^%install\s*$'),
            },
        },
        'check': {
            'keyword': 'check',
            'macros': {
                'check': re.compile(r'^%check\s*$'),
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
                'pre': re.compile(r'^%pre\s+(?P<args>.*)\s*$'),
            },
        },
        'preun': {
            'keyword': 'preun',
            'macros': {
                'preun': re.compile(r'^%preun\s+(?P<args>.*)\s*$'),
            },
        },
        'post': {
            'keyword': 'post',
            'macros': {
                'post': re.compile(r'^%post\s+(?P<args>.*)\s*$'),
            },
        },
        'postun': {
            'keyword': 'postun',
            'macros': {
                'postun': re.compile(r'^%postun\s+(?P<args>.*)\s*$'),
            },
        },
        'files': {
            'keyword': 'files',
            'macros': {
                'attr': re.compile(r'^%attr(?P<args>\(.*\).*)$'),
                'config': re.compile(r'^%config(?P<args>\(.*\).*)'),
                'defattr': re.compile(r'^%defattr(?P<args>\(.*\).*)$'),
                'dir': re.compile(r'^%dir\s+(?P<args>.*)\s*$'),
                'doc': re.compile(r'^%doc\s+(?P<args>.*)\s*$'),
                'docdir': re.compile(r'^%docdir\s+(?P<args>.*)\s*$'),
                'files': re.compile(r'^%files\s*(?P<args>.*)\s*$'),
                'lang': re.compile(r'^%lang(?P<args>\(.*\).*)$'),
                'verify': re.compile(r'%verify\s+(?P<args>.*)$'),
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

    def find_specs(self, path):
        specs = []

        if os.path.isdir(path):
            for root, dirs, files in os.walk(path):
                for f in files:
                    if f.endswith('.spec'):
                        specs.append(os.path.join(root, f))
        elif os.path.isfile(path):
            if path.endswith('.spec'):
                specs.append(path)

        return specs

    def spec_content(self, path):
        for path in self.find_specs(path):
            content = []
            if self.use_rpmspec:
                for line in sh.rpmspec('-P', path):
                    content.append(line.rstrip())
            else:
                print(path)
                for line in codecs.open(path, 'r', 'iso-8859-1'):
                    content.append(line.rstrip())

            yield path, content

    def parse(self, path):
        parsed = []
        for path, content in self.spec_content(path):
            parsed.append(self.parse_sections(self.split(content)))
        return parsed

    def parse_sections(self, root):
        re_empty_line = r'^\s*(#.*|\%.*|)$'
        re_key_value = r'^\s*(?P<key>\w+)\s*:\s*(?P<value>.*)\s*$'
        re_rpm_changelog_header = re.compile(
            r'^\s*\*\s+(?P<date>\w{3}\s\w{3}\s\d\d?\s\d{4})\s(?P<author>.+)'
            r'\s<(?P<author_email>.*)>[\s-]+(?P<title>.*)$')

        spec = RpmSpec()
        for section in root:
            if section.name == '_text':
                for lineno, line in section.content:
                    if re.match(re_empty_line, line):
                        continue
                    m = re.match(re_key_value, line)
                    if m:
                        key = m.group('key')
                        value = m.group('value')
                        key_ = key.split('(')[0].lower()
                        if key_.startswith('source'):
                            spec.source.sources[key] = value
                        elif key_.startswith('patch'):
                            spec.source.patches[key] = value
                        elif key_ in ['requires', 'buildrequires',
                                      'provides', 'conflicts',
                                      'obsoletes', 'buildconflicts']:
                            spec.source.get(key_).append(value)
                        else:
                            spec.source.set(key_, value)
            elif section.name == 'changelog':
                for lineno, line in section.content:
                    m = re_rpm_changelog_header.match(line)
                    if m:
                        change = RpmSpecChangelogChange()
                        change.date = m.group('date')
                        change.author = m.group('author')
                        change.author_email = m.group('author_email')
                        change.title = m.group('title')
                        spec.changelog.append(change)
            elif section.name == 'package':
                pass

        return spec

    def split(self, content):
        section = RpmSpecSection()
        root = section.root
        lineno = 0
        for linestr in content:
            lineno += 1
            line = (lineno, linestr)
            if re.match(r'^\s*$', line[1]):
                section.add_content(line)
                continue
            if re.match(r'^%\w.*$', line[1]):
                match = re.match(r'^%if\s*(?P<args>.*)$', line[1])
                if match:
                    section = section.subsection(name='if')
                    section.args = match.groupdict().get('args', '')
                    section.add_content(line)
                    section = section.subsection(name='_then')
                    continue

                if re.match(r'^%else\s*.*$', line[1]):
                    while section.name != 'if':
                        section = section.parent
                    section.add_content(line)
                    section = section.subsection(name='_else')
                    continue

                if re.match(r'^%endif\s*.*$', line[1]):
                    while section.name != 'if':
                        section = section.parent
                    section.add_content(line)
                    if root.var.get('move_section', None) == section:
                        section = section.move()
                    section = section.parent
                    continue

                merge = False
                parent, section_name, groups =\
                    self.get_parent(line[1], section)
                if section_name is None:
                    merge = True
                    parent, section_name, groups =\
                        self.get_parent(line[1], section, full_scan=False)
                if root.var.get('move_section'):
                    root.var.setdefault('new_parent', parent)
                    if root.var['new_parent'].level > parent.level:
                        root.var['new_parent'] = parent
                    section = section.subsection(section_name)
                    continue

                if section_name:
                    section = parent.subsection(section_name, merge=merge)

                if not merge:
                    section.args = groups.get('args', '')

                section.add_content(line)
            else:
                section.add_content(line)
        return root

    def get_parent(self, line, section, full_scan=True):
        # Create reversed tree of sections (from current at [0]
        # down to _root at [-1])
        tree = []
        while section.name != '_root':
            tree.append(section)
            section = section.parent
        tree.append(section)

        section_ptr = 0
        for section in tree:
            # If section name is meaningless, skip it
            if section.name in ['_text', 'if', '_then', '_else']:
                section_ptr += 1
                continue

            section_name, groups = self.parse_line(line, section)
            if section_name is None:
                if full_scan:
                    continue
                else:
                    section = tree[section_ptr]
                    return section.parent, section.name, groups

            if section.name == '_root':
                return tree[-1], section_name, groups
            else:
                return tree[section_ptr], section_name, groups

        return tree[-1], None, groups

    def parse_line(self, line, section):
        if section.name == '_root':
            for name, schema in self.sections.items():
                keyword = schema.get('keyword', None)
                if keyword is None:
                    continue
                macros = schema.get('macros', {})
                regexp = macros.get(keyword, None)
                m = regexp.match(line)
                if m:
                    return name, m.groupdict()
        else:
            schema = self.sections.get(section.name, {})
            keyword = schema.get('keyword', None)
            macros = schema.get('macros', {})
            for name, regexp in macros.items():
                if name == keyword:
                    continue
                m = regexp.match(line)
                if m:
                    return name, m.groupdict()
        return None, {}


class RpmSpecSection(object):
    def __init__(self, name='_root', parent=None, root=None, level=None):
        self.name = name
        self.args = ''
        self.var = {}

        if root is None:
            self._root = self
            self._parent = self
            self.level = 0
        else:
            self._root = root
            self._parent = parent
            self.level = parent.level + 1

        if level:
            self.level = level

        self._subsections = []
        self._content = []

        if self.name == 'if':
            self._root.var.setdefault('move_section', self)
            self._root.var.setdefault('new_parent', self._parent)

    def __iter__(self):
        for section in self._subsections:
            yield section

    def subsection(self, name, merge=True):
        # Only one section could be '_root'
        if name == '_root':
            return self._root

        # ['_text', ] section(s) can't have subsections,
        # so create one from it's parent, or return existing
        if self.name == '_text':
            if name == '_text':
                return self
            else:
                section = self._parent.subsection(name)
                return section

        # Some sections could be merged
        if len(self._subsections):
            if self._subsections[-1].name == name:
                if merge:
                    return self._subsections[-1]

        if self.name == 'if':
            if name not in ['_then', '_else']:
                raise Exception("'if' allows only '_then' or '_else' sections")

        section = RpmSpecSection(name=name, parent=self, root=self.root)
        self._subsections.append(section)

        return section

    def move(self, section=None, parent=None):
        if section is None:
            section = self._root.var.pop('move_section', self)
        if parent is None:
            parent = self._root.var.pop('new_parent', None)
        section.parent.remove_section(section)
        parent.add_section(section)
        section._parent = parent
        return section

    def add_section(self, section):
        self._subsections.append(section)

    def remove_section(self, section):
        self._subsections.remove(section)

    def add_content(self, line):
        if self.name in ['if', 'changelog']:
            self.content.append(line)
            return

        if len(self._subsections) == 0:
            section = self.subsection(name='_text')
        else:
            if self._subsections[-1].name == '_text':
                section = self._subsections[-1]
            else:
                section = self.subsection(name='_text')
        section.content.append(line)

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

    def __str__(self):
        return '{} ({})'.format(self.name, self.args)
