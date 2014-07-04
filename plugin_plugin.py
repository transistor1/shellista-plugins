'''
plugin:
    Download and update plugins for Shellista
    usage: plugin [list|install|update|remove]'''

import string
import argparse
import re
import os
import importlib
import sys
import contextlib

from .. git import git_plugin as git
from ... tools.toolbox import bash

alias=['plugins']
shellista = sys.modules['__main__']
shellista_dir = os.path.abspath(os.path.dirname(shellista.__file__))
plugin_folder = os.path.join(shellista_dir,'plugins','extensions')
plugins = None

def _get_installed_plugins():
    #Quick-n-dirty hack to check which modules are installed.
    #Returns names of installed plugins
    #TODO: Fix this!!! (how?)
    return os.walk(plugin_folder).next()[1] #Get dirnames

def _is_plugin_installed(module_name):
    installed = _get_installed_plugins()
    if module_name in installed:
        return True
    return False
    
def _get_plugin_path_name(plugin_name):
    #Return the path of a plugin, whether it currently
    #exists or not.
    #This could possibly be enhanced in the future
    #So that plugins don't have to specifically be
    #under extensions
    return os.path.join(plugin_folder, plugin_name)


@contextlib.contextmanager
def _context_chdir(new_path, create_path=False):
    '''Change directories, saving the old path. To be used in
         a with statement'''
    os._old_path = os.getcwd()
    os.chdir(new_path)
    yield
    os.chdir(os._old_path)

#Get available plugins from plugin_urls.txt
def _enumerate_plugins():
    with PluginFile(os.path.join(os.path.dirname(os.path.abspath(__file__))
                        ,'plugin_urls.txt'),'r') as plugin_file:
        global plugins
        plugins = Plugins(plugin_file, PipePluginFactory())
        plugins.parse_file()

class Plugin():
    '''Represents a single plugin'''
    name = ''
    download_name = ''
    description = ''
    git_url = ''
    is_installed = False

    def __init__(self, **kwargs):
        for kw, arg in kwargs.iteritems():
            setattr(self, kw, arg)

class PluginFactory(list):
    '''Abstract class for different plugin factories.
        Purpose of this class is to convert text into plugin
        information.

        Class was abstracted so we can use a different type
        of update file if we outgrow pipe system'''
    def parse(self, line):
        raise NotImplementedError('Abstract method')

class PipePluginFactory(PluginFactory):
    '''Factory for converting pipe-delimited records into
        Plugin()s'''
    def parse(self, line):
        new_plugin = None
        line = line.lstrip()
        if line and (not line.startswith('#')):
            items = string.split(line, '|')
            new_plugin = Plugin(
                        name=items[0], 
                        download_name=items[1], 
                        description=items[2], 
                        git_url=items[3],
                        is_installed = _is_plugin_installed(items[1]))
                    
        return new_plugin

class PluginFile(file):
    '''File[-like] object representing a plugin file. Currently
        derived directly from file as a placeholder in case
        future functionality is required.'''
    pass

class Plugins(list):
    '''Represents a collection of Plugin objects.'''
    plugin_file = None
    plugin_factory = None

    def __init__(self, plugin_file, plugin_factory):
        self.plugin_file = plugin_file
        self.plugin_factory = plugin_factory

    def __str__(self):
        return self.plugins

    def parse_file(self):
        for line in self.plugin_file:
            plugin = self.plugin_factory.parse(line)
            if plugin:
                self.append(plugin)

def usage():
    print 'plugin [list [wildcard]|install <module name>|update <module name>]'

def plugin_list(self, wildcard='*'):
    #TODO: Enhance silly wildcard implementation
    #TODO: Make this better
    wildcard = wildcard.replace('*','.*')
    for plugin in plugins:
        if re.match(wildcard, plugin.name):
            print 'Name:{0}{2}\n- Description: {1}'.format(
                                    plugin.name,
                                    plugin.description,
                                    ' ** Installed' if plugin.is_installed
                                        else '')

def plugin_install(self, plugin_name):
    #TODO: Plugins should be a hash, not a list
    #TODO: Implement wildcard match
    if not _is_plugin_installed(plugin_name):
        for plugin in plugins:
            if plugin.name == plugin_name:
                new_plugin_path = _get_plugin_path_name(plugin_name)
                if not os.exists(new_plugin_path):
                    os.mkdir(new_plugin_path)
                with _context_chdir(new_plugin_path):
                    git.do_git('clone ' + plugin.git_url)
                
                filenames = [x for x in os.walk(new_plugin_path).next()[2]
                                if x.lower().endswith('_plugin.py')]
                
                for path in filenames:
                    (path, ext) = os.path.splitext(path)
                    relpath = os.path.relpath(new_plugin_path, shellista_dir)
                    self._hook_plugin_main(relpath, path)
                    
                print 'Successfully installed {0}'.format(plugin_name)
    else:
        print 'Plugin: {0} already installed. Use update to download latest'.format(plugin_name)


def _do_plugin_update(plugin_name):
    if _is_plugin_installed(plugin_name):
        with _context_chdir(_get_plugin_path_name(plugin_name)):
            git.do_git('pull')
            return True
    return False
        
def plugin_update(self, plugin_name = None):
    '''Update a plugin, or pass None to update all plugins'''
    #TODO: Implement wildcard match
    if plugin_name:
        to_update = [plugin_name]
    else:
        to_update = _get_installed_plugins()

    for plugin in to_update:
        if _do_plugin_update(plugin):
            print 'Successfully updated {0}'.format(plugin_name)
    
def plugin_remove(self, plugin_name):
    '''Remove a plugin'''
    raise NotImplementedError('Not implemented')

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
                plugin_update(self, *args)
            elif command == 'remove':
                plugin_remove(self, *args)
            else:
                usage()
        except Exception as e:
            #raise
            print 'Error: {0}'.format(e)
    else:
        usage()

#Enumerate all the available plugins on startup.
_enumerate_plugins()

