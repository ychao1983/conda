# (c) 2012-2013 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

import os
import unittest
from os.path import dirname, join
import yaml

import conda.config as config

from test_cli import run_conda_command

# use condarc from source tree to run these tests against
config.rc_path = join(dirname(__file__), 'condarc')

# unset CIO_TEST

try:
    del os.environ['CIO_TEST']
except KeyError:
    pass


class TestConfig(unittest.TestCase):

    # These tests are mostly to ensure API stability

    def __init__(self, *args, **kwargs):
        config.rc = config.load_condarc(config.rc_path)
        super(TestConfig, self).__init__(*args, **kwargs)

    def test_globals(self):
        self.assertTrue(config.root_dir)
        self.assertTrue(config.pkgs_dirs)
        self.assertTrue(config.envs_dirs)
        self.assertTrue(config.default_prefix)
        self.assertTrue(config.platform)
        self.assertTrue(config.subdir)
        self.assertTrue(config.arch_name)
        self.assertTrue(config.bits in (32, 64))

    def test_pkgs_dir_prefix(self):
        root_dir = config.root_dir
        root_pkgs = join(root_dir, 'pkgs')
        for pi, po in [
            (root_dir, root_pkgs),
            (join(root_dir, 'envs', 'foo'), root_pkgs),
            ]:
            self.assertEqual(config.pkgs_dir_prefix(pi), po)

        if config.platform == 'win':
            self.assertEqual(config.pkgs_dir_prefix(r'C:\usr\local\foo'), r'C:\usr\local\.pkgs')
        else:
            self.assertEqual(config.pkgs_dir_prefix('/usr/local/foo'), '/usr/local/.pkgs')

    def test_proxy_settings(self):
        self.assertEqual(config.get_proxy_servers(),
                         {'http': 'http://user:pass@corp.com:8080',
                          'https': 'https://user:pass@corp.com:8080'})

    def test_normalize_urls(self):
        current_platform = config.subdir
        assert config.DEFAULT_CHANNEL_ALIAS == 'https://conda.binstar.org/'
        assert config.rc.get('channel_alias') == 'https://your.repo/'

        for channel in config.normalize_urls(['defaults', 'system',
            'https://binstar.org/username', 'file:///Users/username/repo',
            'username']):
            assert channel.endswith('/%s/' % current_platform)
        self.assertEqual(config.normalize_urls([
            'defaults', 'system', 'https://conda.binstar.org/username',
            'file:///Users/username/repo', 'username'
            ], 'osx-64'),
            [
                'http://repo.continuum.io/pkgs/free/osx-64/',
                'http://repo.continuum.io/pkgs/pro/osx-64/',
                'https://your.repo/binstar_username/osx-64/',
                'http://some.custom/channel/osx-64/',
                'http://repo.continuum.io/pkgs/free/osx-64/',
                'http://repo.continuum.io/pkgs/pro/osx-64/',
                'https://conda.binstar.org/username/osx-64/',
                'file:///Users/username/repo/osx-64/',
                'https://your.repo/username/osx-64/',
                ])

def _read_test_condarc():
    test_condarc = os.path.join(os.path.dirname(__file__), 'test_condarc')
    with open(test_condarc) as f:
        return f.read()

# Tests for the conda config command
def test_config_command():
    test_condarc = os.path.join(os.path.dirname(__file__), 'test_condarc')
    try:
        # Test that creating the file adds the defaults channel
        assert not os.path.exists('test_condarc')
        stdout, stderr = run_conda_command('config', '--file', test_condarc, '--add',
            'channels', 'test')
        assert stdout == stderr == ''
        assert _read_test_condarc() == """\
channels:
  - test
  - defaults
"""
        os.unlink(test_condarc)

        # When defaults is explicitly given, it should not be added
        stdout, stderr = run_conda_command('config', '--file', test_condarc, '--add',
    'channels', 'test', '--add', 'channels', 'defaults')
        assert stdout == stderr == ''
        assert _read_test_condarc() == """\
channels:
  - defaults
  - test
"""
        os.unlink(test_condarc)

        # Duplicate keys should not be added twice
        stdout, stderr = run_conda_command('config', '--file', test_condarc, '--add',
        'channels', 'test')
        assert stdout == stderr == ''
        stdout, stderr = run_conda_command('config', '--file', test_condarc, '--add',
        'channels', 'test')
        assert stdout == ''
        assert stderr == "Skipping channels: test, item already exists\n"
        assert _read_test_condarc() == """\
channels:
  - test
  - defaults
"""
        os.unlink(test_condarc)

        # Test --get
        with open(test_condarc, 'w') as f:
            f.write("""\
channels:
  - test
  - defaults

create_default_packages:
  - ipython
  - numpy

changeps1: no

always_yes: yes

invalid_key: yes
""")

        stdout, stderr = run_conda_command('config', '--file', test_condarc, '--get')
        assert stdout == """\
--set always_yes True
--set changeps1 False
--add channels 'defaults'
--add channels 'test'
--add create_default_packages 'numpy'
--add create_default_packages 'ipython'
"""
        assert stderr == "invalid_key is not a valid key\n"

        stdout, stderr = run_conda_command('config', '--file', test_condarc,
        '--get', 'channels')

        assert stdout == """\
--add channels 'defaults'
--add channels 'test'
"""
        assert stderr == ""

        stdout, stderr = run_conda_command('config', '--file', test_condarc,
        '--get', 'changeps1')

        assert stdout == """\
--set changeps1 False
"""
        assert stderr == ""

        stdout, stderr = run_conda_command('config', '--file', test_condarc,
            '--get', 'changeps1', 'channels')

        assert stdout == """\
--set changeps1 False
--add channels 'defaults'
--add channels 'test'
"""
        assert stderr == ""

        stdout, stderr = run_conda_command('config', '--file', test_condarc,
        '--get', 'allow_softlinks')

        assert stdout == ""
        assert stderr == ""

        stdout, stderr = run_conda_command('config', '--file', test_condarc,
        '--get', 'track_features')

        assert stdout == ""
        assert stderr == ""

        stdout, stderr = run_conda_command('config', '--file', test_condarc,
        '--get', 'invalid_key')

        assert stdout == ""
        assert "invalid choice: 'invalid_key'" in stderr

        stdout, stderr = run_conda_command('config', '--file', test_condarc,
        '--get', 'not_valid_key')

        assert stdout == ""
        assert "invalid choice: 'not_valid_key'" in stderr

        os.unlink(test_condarc)

        # Now test the YAML "parser"
        condarc = """\
 channels :
   -  test
   -  defaults \n\

 create_default_packages:
    - ipython
    - numpy

 changeps1 :  no

# Here is a comment
 always_yes: yes \n\
"""
        # First verify that this itself is valid YAML
        assert yaml.load(condarc) == {'channels': ['test', 'defaults'],
            'create_default_packages': ['ipython', 'numpy'], 'changeps1':
            False, 'always_yes': True}

        with open(test_condarc, 'w') as f:
            f.write(condarc)

        stdout, stderr = run_conda_command('config', '--file', test_condarc, '--get')

        assert stdout == """\
--set always_yes True
--set changeps1 False
--add channels 'defaults'
--add channels 'test'
--add create_default_packages 'numpy'
--add create_default_packages 'ipython'
"""
        assert stderr == ''

        # List keys with nonstandard whitespace are not yet supported. For
        # now, just test that it doesn't muck up the file.
        stdout, stderr = run_conda_command('config', '--file', test_condarc, '--add',
            'create_default_packages', 'sympy')
        assert stdout == ''
        assert stderr == """\
Error: Could not parse the yaml file. Use -f to use the
yaml parser (this will remove any structure or comments from the existing
.condarc file). Reason: modified yaml doesn't match what it should be
"""
        assert _read_test_condarc() == condarc

#         assert _read_test_condarc() == """\
#  channels :
#    -  test
#    -  defaults \n\
#
#  create_default_packages:
#     - sympy
#     - ipython
#     - numpy
#
#  changeps1 :  no
#
# # Here is a comment
#  always_yes: yes \n\
# """

        stdout, stderr = run_conda_command('config', '--file', test_condarc, '--add',
            'channels', 'mychannel')
        assert stdout == stderr == ''

        assert _read_test_condarc() == """\
 channels :
   - mychannel
   -  test
   -  defaults \n\

 create_default_packages:
    - ipython
    - numpy

 changeps1 :  no

# Here is a comment
 always_yes: yes \n\
"""

        os.unlink(test_condarc)


    finally:
        try:
            pass
            os.unlink(test_condarc)
        except OSError:
            pass
