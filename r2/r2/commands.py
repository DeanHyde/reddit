# The contents of this file are subject to the Common Public Attribution
# License Version 1.0. (the "License"); you may not use this file except in
# compliance with the License. You may obtain a copy of the License at
# http://code.reddit.com/LICENSE. The License is based on the Mozilla Public
# License Version 1.1, but Sections 14 and 15 have been added to cover use of
# software over a computer network and provide for limited attribution for the
# Original Developer. In addition, Exhibit A has been modified to be consistent
# with Exhibit B.
#
# Software distributed under the License is distributed on an "AS IS" basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License for
# the specific language governing rights and limitations under the License.
#
# The Original Code is Reddit.
#
# The Original Developer is the Initial Developer.  The Initial Developer of the
# Original Code is CondeNet, Inc.
#
# All portions of the code written by CondeNet are Copyright (c) 2006-2010
# CondeNet, Inc. All Rights Reserved.
################################################################################
import paste.deploy.config
import paste.fixture
from paste.registry import RegistryManager
from paste.script import command
from paste.deploy import appconfig        
from r2.config.environment import load_environment
from paste.script.pluginlib import find_egg_info_dir
from pylons.wsgiapp import PylonsApp

#from pylons.commands import ShellCommand, ControllerCommand, \
#     RestControllerCommand

import os, sys
#
# commands that will be available by running paste with this app
#

class RunCommand(command.Command):
    max_args = 2
    min_args = 1

    usage = "CONFIGFILE CMDFILE.py"
    summary = "Executed CMDFILE with pylons support"
    group_name = "Reddit"


    parser = command.Command.standard_parser(verbose=True)
    parser.add_option('-c', '--command',
                      dest='command',
                      help="execute command in module")

    def command(self):
        here_dir = os.getcwd()

        if self.args[0].lower() == 'standalone':
            load_environment(setup_globals=False)
        else:
            config_name = 'config:%s' % self.args[0]

            conf = appconfig(config_name, relative_to=here_dir)
            conf.global_conf['running_as_script'] = True
            conf.update(dict(app_conf=conf.local_conf,
                             global_conf=conf.global_conf))
            paste.deploy.config.CONFIG.push_thread_config(conf)

            load_environment(conf.global_conf, conf.local_conf)

        # Load locals and populate with objects for use in shell
        sys.path.insert(0, here_dir)

        # Load the wsgi app first so that everything is initialized right
        wsgiapp = RegistryManager(PylonsApp())
        test_app = paste.fixture.TestApp(wsgiapp)

        # Query the test app to setup the environment
        tresponse = test_app.get('/_test_vars')
        request_id = int(tresponse.body)

        # Disable restoration during test_app requests
        test_app.pre_request_hook = lambda self: \
            paste.registry.restorer.restoration_end()
        test_app.post_request_hook = lambda self: \
            paste.registry.restorer.restoration_begin(request_id)

        # Restore the state of the Pylons special objects
        # (StackedObjectProxies)
        paste.registry.restorer.restoration_begin(request_id)

        loaded_namespace = {}

        if self.args[1:]:
            cmd = self.args[1]
            f = open(cmd);
            data = f.read()
            f.close()
            
            exec data in loaded_namespace
            
        if self.options.command:
            exec self.options.command in loaded_namespace
