#!/usr/bin/python
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

# Based on AWS CloudFormation implementation

DOCUMENTATION = '''
---
module: heat
short_description: create an OpenStack heat stack
description:
     - Launches a heat stack and waits for it complete.
version_added: "0.1"
options:
  stack_name:
    description:
      - name of the heat stack
    required: true
    default: null
    aliases: []
  disable_rollback:
    description:
      - If a stcks fails to form, rollback will remove the stack
    required: false
    default: "false"
    choices: [ "true", "false" ]
    aliases: []
  template_parameters:
    description:
      - a list of hashes of all the template variables for the stack
    required: false
    default: {}
    aliases: []
  action:
    description:
      - If action is "create", stack will be created.
        If state is "delete", stack will be removed.
    required: true
    default: null
    aliases: []
  template:
    description:
      - the path of the heat template file
    required: true
    default: null
    aliases: []

requirements: [ "heatclient", "keystoneclient" ]
author: Justina Chen
'''

EXAMPLES = '''
# Basic task example
tasks:
- name: launch ansible heat example
  heat:
    stack_name: "ansible-heat"
    disable_rollback: "false"
    template: "files/heat-example.yaml"
    template_parameters:
      KeyName: "justina"
      DiskType: "ephemeral"
      InstanceType: "m1.small"
      Images: ["uuid", "uuid"]
'''

import json
import time
import os

try:
    from heatclient.client import Client
    from heatclient.common import template_utils
    from heatclient.common import utils
    from keystoneclient.v2_0 import client as ksclient
except ImportError:
    print("failed=True msg='heatclient and keystoneclient is required for this module'")

username = os.getenv('OS_USERNAME')
password = os.getenv('OS_PASSWORD')
tenant_name = os.getenv('OS_TENANT_NAME')
auth_url = os.getenv('OS_AUTH_URL')
if '' in (username, password, tenant_name, auth_url):
    print ("system environment variables are required for keystone authentication")

def stack_operation(heat, stack_name, operation):
    '''gets the status of a stack while it is created/deleted'''
    existed = []
    result = {}
    operation_complete = False
    while operation_complete == False:
        try:
            stack = heat.get(stack_name)
            existed.append('yes')
        except:
            if 'yes' in existed:
                result = dict(changed=True, output='Stack Deleted')
            else:
                result = dict(changed= True, output='Stack Not Found')
            break
        if 'Complete' in stack.status:
            result = dict(changed=True, output = 'Stack %s complete' % operation)
            break
        elif 'Fail' in stack.status:
            result = dict(failed=True, output = 'Stack %s failed' % operation)
            break
        else:
            time.sleep(5)
    return result

def main():
    argument_spec = openstack_argument_spec()
    argument_spec.update(dict(
            stack_name=dict(required=True),
            template_parameters=dict(required=False, type='dict', default={}),
            action=dict(default='create', choices=['create', 'delete']),
            template=dict(default=None, required=True),
            disable_rollback=dict(default=False, type='bool')
        )
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
    )

    # keystone authentication
    keystone = ksclient.Client(username=username, password=password,
                            tenant_name=tenant_name, auth_url=auth_url)
    auth_token = keystone.auth_ref['token']['id']
    heat_url = ''
    services = keystone.auth_ref['serviceCatalog']
    for service in services:
        if service['name'] == 'heat':
            heat_url = service['endpoints'][0]['publicURL']

    # creat heat client by using auth token
    stack_outputs = {}
    heat = Client('1', endpoint=heat_url, token=auth_token)
    result = {}

    action = module.params['action']
    stack_name = module.params['stack_name']

    if action == 'create':
        tpl_files, template = template_utils.get_template_contents(module.params['template'])

        fields = {
            'stack_name': stack_name,
            'disable_rollback': module.params['disable_rollback'],
            'parameters': utils.format_parameters(module.params['template_parameters']),
            'template': template,
            'files': dict(list(tpl_files.items()))
        }
        try:
            heat.stacks.create(**fields)
        except Exception, err:
            module.fail_json(msg=err.message)
        result = stack_operation(heat, stack_name, action)

    if action == 'delete':
        fields = {'stack_id': stack_name}
        try:
            heat.stacks.delete(**fields)
        except Exception, err:
            if "not be found" not in err.message:
                module.fail_json(msg=err.message)
        result = stack_operation(heat, stack_name, action)

    module.exit_json(**result)

# import module snippets
from ansible.module_utils.basic import *
from ansible.module_utils.openstack import *
if __name__ == '__main__':
    main()
