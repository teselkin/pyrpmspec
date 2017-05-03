#!/usr/bin/python

import os
import re
import sh

import codecs

from pyrpmspec.objects import (RpmSpecSourcePackage,
    RpmSpecChangelogChange)


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

        spec = RpmSpecSourcePackage()
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
                            spec.sources[key] = value
                        elif key_.startswith('patch'):
                            spec.patches[key] = value
                        elif key_ in ['requires', 'buildrequires',
                                      'provides', 'conflicts',
                                      'obsoletes', 'buildconflicts']:
                            spec.get(key_).append(value)
                        else:
                            spec.set(key_, value)
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
