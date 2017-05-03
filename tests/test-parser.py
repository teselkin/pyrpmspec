#!/usr/bin/python

from pyrpmspec.rpm import RpmSpecParser

import os
import shutil
import wget
import yaml

test_spec = 'http://pkgs.fedoraproject.org/' \
            'cgit/rpms/postgresql.git/plain/postgresql.spec'

if os.path.exists('tmp'):
    shutil.rmtree('tmp')
os.mkdir('tmp')
wget.download(test_spec, out='tmp')

parser = RpmSpecParser()
parsed = parser.parse('tmp/postgresql.spec')
for spec in parsed:
    print(yaml.dump(spec.dump(),
                    default_style='',
                    default_flow_style=False))
