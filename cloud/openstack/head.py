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
module: head
short_description: create an OpenStack head stack
description:
     - Launches a head stack and waits for it complete.
version_added: "0.1"
options:
  stack_name:
    description:
      - name of the head stack
    required: true
    default: null
    aliases: []
  disable_rollback:
    description:
      - If a stacks fails to form, rollback will remove the stack
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
      - the path of the cloudformation template
    required: true
    default: null
    aliases: []
  stack_policy:
    description:
      - the path of the cloudformation stack policy
    required: false
    default: null
    aliases: []
    version_added: "x.x"
  tags:
    description:
      - Dictionary of tags to associate with stack and it's resources during stack creation. Cannot be updated later.
        Requires at least Boto version 2.6.0.
    required: false
    default: null
    aliases: []
    version_added: "1.4"
  username:
    description:
      - The username used to connect to the OpenStack service. If not set then the value of the OS_USERNAME environment variable is used.
    required: false
    default: null
    aliases: [ 'username' ]
    version_added: "1.5"
  password:
    description:
      - The password used to connect to the OpenStack service. If not set then the value of the OS_PASSWORD environment variable is used.
    required: false
    default: null
    aliases: [ 'password' ]
    version_added: "1.5"
  tenant_name:
    description:
      - Tenant ID for accessing OpenStack. If not set then the value of the OS_TENANT_NAME environment variable is used.
    required: false
    default: null
    aliases: [ 'tenant_name' ]
    version_added: "1.5"
  auth_url:
    description:
      - The head url to use. If not specified then the value of the OS_AUTH_URL environment variable, if any, is used.
    required: false
    aliases: ['auth_url' ]
    version_added: "1.5"

requirements: [ "heatclient", "keystoneclient" ]
author: Justina Chen
'''

EXAMPLES = '''
# Basic task example
tasks:
- name: launch ansible head example
  head:
    stack_name: "ansible-head"
    disable_rollback: true
    template: "files/head-example.json"
    template_parameters:
      KeyName: "jmartin"
      DiskType: "ephemeral"
      InstanceType: "m1.small"
      ClusterSize: 3
    tags:
      Stack: "ansible-head"
'''

import json
import time

try:
    from heatclient.client import Client
    from keystoneclient.v2_0 import client as ksclient
except ImportError:
    print("failed=True msg='headclient is required for this module'")

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
        if '%s_COMPLETE' % operation == stack.status:
            result = dict(changed=True, output = 'Stack %s complete' % operation)
            break
        if  'ROLLBACK_COMPLETE' == stack.status or '%s_ROLLBACK_COMPLETE' % operation == stack.status:
            result = dict(failed=True, output = 'Problem with %s. Rollback complete' % operation)
            break
        elif '%s_FAILED' % operation == stack.status:
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
            state=dict(default='present', choices=['present', 'absent']),
            template=dict(default=None, required=True),
            stack_policy=dict(default=None, required=False),
            disable_rollback=dict(default=False, type='bool'),
            tags=dict(default=None)
        )
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
    )

    action = module.params['action']
    stack_name = module.params['stack_name']
    template_body = open(module.params['template'], 'r').read()
    if module.params['stack_policy'] is not None:
        stack_policy_body = open(module.params['stack_policy'], 'r').read()
    else:
        stack_policy_body = None
    disable_rollback = module.params['disable_rollback']
    template_parameters = module.params['template_parameters']
    tags = module.params['tags']
    username = module.params['username']
    password = module.params['password']
    tenant_name = module.params['tenant_name']
    auth_url = module.params['auth_url']

    kwargs = dict()
    if tags is not None:
        kwargs['tags'] = tags


    # convert the template parameters ansible passes into a tuple for boto
    template_parameters_tup = [(k, v) for k, v in template_parameters.items()]
    stack_outputs = {}

    keystone = ksclient.Client(username=username, password=password,
                            tenant_name=tenant_name, auth_url=auth_url)
    auth_token = keystone.auth_ref['token']['id']
    tenant_id = keystone.auth_ref['token']['tenant']['id']
    heat_url = '%s/%s' % (auth_url,tenant_id)

    heat = Client('1', endpoint=heat_url, token=auth_token)
    result = {}
    operation = None

    if action == 'create':
        try:
            heat.stacks.create(stack_name, parameters=template_parameters_tup,
                             template_body=template_body,
                             stack_policy_body=stack_policy_body,
                             disable_rollback=disable_rollback,
                             capabilities=['CAPABILITY_IAM'],
                             **kwargs)
            operation = 'CREATE'
        except Exception, err:
            if 'AlreadyExistsException' in err or 'already exists' in err:
                update = True
            else:
                module.fail_json(msg=err)
        if not update:
            result = stack_operation(heat, stack_name, operation)

    if action == 'delete':
        heat.stacks.delete(stack_name)
        result = stack_operation(heat, stack_name, operation)

    module.exit_json(**result)

# import module snippets
from ansible.module_utils.basic import *
from ansible.module_utils.openstack import *
if __name__ == '__main__':
    main()
