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
module: os_stack
short_description: Create an OpenStack heat stack
extends_documentation_fragment: openstack
description:
   - Launches a heat stack and waits for it complete.
version_added: "0.1"
options:
  stack_name:
    description:
      - name of the stack
    required: true
    default: null
  rollback:
    description:
      - If a stack fails to form, rollback will remove the stack
    required: false
    default: true
    choices: [ "true", "false" ]
  template_parameters:
    description:
      - a list of hashes of all the template variables for the stack
    required: false
    default: {}
  template:
    description:
      - the path of the stack template file
    required: true
    default: null

requirements: [ "shade" ]
author: Justina Chen
'''

EXAMPLES = '''
# Basic task example
tasks:
- name: launch ansible heat example
  os_stack:
    name: "ansible-heat"
    rollback: yes
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
    import shade
    HAS_SHADE = True
except ImportError:
    HAS_SHADE = False


def main():
    argument_spec = openstack_full_argument_spec(
        name                 = dict(required=True),
        template_parameters  = dict(required=False, type='dict', default={}),
        template             = dict(default=None, required=True),
        rollback             = dict(default=True, type='bool')
    )
    module_kwargs = openstack_module_kwargs()
    module = AnsibleModule(argument_spec, **module_kwargs)

    if not HAS_SHADE:
        module.fail_json(msg='shade is required for this module')

    try:
        cloud = shade.openstack_cloud(**module.params)

        state = module.params['state']
        stack = cloud.get_stack(module.params['name'])

        if state == 'present':
            if stack:
                module.exit_json(changed=False)
            stack = cloud.create_stack(
                name=module.params['name'],
                rollback=module.params['rollback'],
                template=module.params['template'],
                wait=module.params['wait'],
                timeout=module.params['timeout'],
                **(module.params['template_parameters']),
            )
            module.exit_json(changed=True, stack=stack)

        if state == 'absent':
            if not stack:
                module.exit_json(changed=False)
            cloud.delete_stack(
                name=module.params['name'],
                wait=module.params['wait'],
                timeout=module.params['timeout'])

    except shade.OpenStackCloudException as e:
        module.fail_json(msg=e.message)
    result = stack_operation(heat, name, state)
    module.exit_json(**result)

# import module snippets
from ansible.module_utils.basic import *
from ansible.module_utils.openstack import *
if __name__ == '__main__':
    main()
