'''usage: plugin [list|install|update|remove]'''

import string
import argparse
import re
import os
import importlib
import sys

from .. git import git_plugin as git
from ... tools.toolbox import bash

alias=['plugins']
shellista = sys.modules['__main__']
shellista_dir = os.path.abspath(os.path.dirname(shellista.__file__))
plugin_folder = os.path.join(shellista_dir,'plugins','extensions')
sys.path.append(shellista_dir)

def _is_plugin_installed(module_name):
    #Quick-n-dirty hack to check which modules are installed.
    #TODO: Fix this!!!
    subdirs = os.walk(plugin_folder).next()[1] #Get dirnames
    if module_name in subdirs:
       return True
    return False

class Plugin():
    name = ''
    download_name = ''
    description = ''
    git_url = ''
    is_installed = False

    def __init__(self, **kwargs):
        for kw, arg in kwargs.iteritems():
            setattr(self, kw, arg)

class PluginFactory(list):
    def parse(self, line):
        raise NotImplementedError()

class PipePluginFactory(PluginFactory):
    def parse(self, line):
        items = string.split(line, '|')
        new_plugin = Plugin(name=items[0], download_name=items[1], description=items[2], git_url=items[3])
        new_plugin.is_installed = _is_plugin_installed(new_plugin.download_name)
        return new_plugin

class PluginFile(file):
    pass

class Plugins(list):
    plugin_file = None
    plugin_factory = None

    def __init__(self, plugin_file, plugin_factory):
        self.plugin_file = plugin_file
        self.plugin_factory = plugin_factory

    def __str__(self):
        return self.plugins

    def parse_file(self):
        for line in self.plugin_file:
            if not line.lstrip().startswith('#'):
                plugin = self.plugin_factory.parse(line)
                self.append(plugin)

plugins = None
with PluginFile(os.path.join(os.path.dirname(os.path.abspath(__file__))
                    ,'plugin_urls.txt'),'r') as plugin_file:
    plugins = Plugins(plugin_file, PipePluginFactory())
    plugins.parse_file()

def usage():
    print 'plugin [list [wildcard]|install <module name>|update <module name>]'

def plugin_list(self, wildcard='*'):
    #TODO: Enhance silly wildcard implementation
    #TODO: Make this better
    wildcard = wildcard.replace('*','.*')
    for plugin in plugins:
        if re.match(wildcard, plugin.name):
            print 'Name:{0}\n- Description: {1}'.format(plugin.name, plugin.description)

def _patch_shellista(self):
    #TODO: Expose patch logic in Shellista class so we can use it here
    #This is just a temporary fix to get this working now
    filenames = [x for x in os.walk('.').next()[2] if x.lower().endswith('_plugin.py')]
    for path in filenames:
        mod_name = os.path.splitext(path)[0].lower().replace('_plugin','')
        full_name = 'plugins.extensions.{0}.{0}_plugin'.format(mod_name)
        lib = importlib.import_module(full_name)
        name = 'do_{0}'.format(mod_name)
        if self.addCmdList(path.lower()):
            setattr(shellista.Shellista, name, self._CmdGenerator(lib.main))

def plugin_install(self, plugin_name):
    #TODO: Fix this ugly directory hack. Quick n dirty
    #TODO: Plugins should be a hash, not a list
    if not _is_plugin_installed(plugin_name):
        for plugin in plugins:
            if plugin.name == plugin_name:
                cwd = os.getcwd()
                try:
                    new_plugin_path = os.path.join(plugin_folder, plugin_name)
                    os.mkdir(new_plugin_path)
                    os.chdir(new_plugin_path)
                    git.do_git('clone ' + plugin.git_url)
                    os.chdir(cwd)
                    _patch_shellista(self)
                finally:
                    os.chdir(cwd)
    else:
        print 'Already installed'

def plugin_update(plugin_name):
    raise NotImplementedError()

def plugin_remove(plugin_name):
    raise NotImplementedError()

def main(self, line):
    args = re.split('\s+', line)
    if len(args) > 0 and args[0]:

        command = args[0]
        args = args[1:]

        try:
            if command == 'list':
                plugin_list(self, *args)
            elif command == 'install':
                plugin_install(self, *args)
            elif command == 'update':
                plugin_update(*args)
            elif command == 'remove':
                plugin_remove(*args)
        except Exception as e:
            print 'Error: {0}'.format(e)
    else:
        usage()


