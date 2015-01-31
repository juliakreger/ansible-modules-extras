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
module: os_heat
short_description: Create an OpenStack heat stack
extends_documentation_fragment: openstack
description:
   - Launches a heat stack and waits for it complete.
version_added: "0.1"
options:
  stack_name:
    description:
      - name of the heat stack
    required: true
    default: null
  disable_rollback:
    description:
      - If a stack fails to form, rollback will remove the stack
    required: false
    default: "false"
    choices: [ "true", "false" ]
  template_parameters:
    description:
      - a list of hashes of all the template variables for the stack
    required: false
    default: {}
  template:
    description:
      - the path of the heat template file
    required: true
    default: null

requirements: [ "shade" ]
author: Justina Chen
'''

EXAMPLES = '''
# Basic task example
tasks:
- name: launch ansible heat example
  os_heat:
    name: "ansible-heat"
    disable_rollback: no
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


def stack_operation(heat, name, operation):
    '''gets the status of a stack while it is created/deleted'''
    existed = []
    result = {}
    operation_complete = False
    while operation_complete == False:
        try:
            stack = heat.get(name)
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
    argument_spec = openstack_full_argument_spec(
        name                 = dict(required=True),
        template_parameters  = dict(required=False, type='dict', default={}),
        template             = dict(default=None, required=True),
        disable_rollback     = dict(default=False, type='bool')
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

    state = module.params['state']
    name = module.params['name']

    if state == 'present':
        tpl_files, template = template_utils.get_template_contents(module.params['template'])

        fields = {
            'stack_name': name,
            'disable_rollback': module.params['disable_rollback'],
            'parameters': utils.format_parameters(module.params['template_parameters']),
            'template': template,
            'files': dict(list(tpl_files.items()))
        }
        try:
            heat.stacks.create(**fields)
        except Exception, err:
            module.fail_json(msg=err.message)
        result = stack_operation(heat, stack_name, state)

    if state == 'absent':
        fields = {'stack_id': name}
        try:
            heat.stacks.delete(**fields)
        except Exception, err:
            if "not be found" not in err.message:
                module.fail_json(msg=err.message)
        result = stack_operation(heat, name, state)

    module.exit_json(**result)

# import module snippets
from ansible.module_utils.basic import *
from ansible.module_utils.openstack import *
if __name__ == '__main__':
    main()
