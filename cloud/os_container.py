#!/usr/bin/python

# Copyright (c) 2015 Hewlett-Packard Development Company, L.P.
# Copyright (c) 2013, Benno Joy <benno@ansible.com>
#
# This module is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This software is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this software.  If not, see <http://www.gnu.org/licenses/>.

try:
    import shade
    HAS_SHADE = True
except ImportError:
    HAS_SHADE = False


DOCUMENTATION = '''
---
module: os_container
short_description: Create or Delete object containers from OpenStack
extends_documentation_fragment: openstack
description:
   - Create or Delete object containers from OpenStack
options:
   state:
     description:
        - Indicate desired state of the resource
     choices: ['present', 'absent']
     default: present
   name:
     description:
        - Name to be give to the container
     required: true
  access:
     description:
        - desired container access level.
     required: false
     choices: ['private', 'public']
     default: private
requirements: ["shade"]
'''

EXAMPLES = '''
# Creates a router for tenant admin
- os_container: state=present name=photos access=private
'''

def main():
    argument_spec = openstack_full_argument_spec(
        name=dict(required=True),
        state=dict(default='present', choices=['absent', 'present']),
        access=dict(default='private', choices=['private', 'public']),
    )
    module_kwargs = openstack_module_kwargs()
    module = AnsibleModule(argument_spec, **module_kwargs)

    if not HAS_SHADE:
        module.fail_json(msg='shade is required for this module')

    changed = False
    name  = module.params['name']
    access = module.params['access']

    try:
        cloud = shade.openstack_cloud(**openstack_auth(module))

        container = cloud.get_container(name)
        if module.params['state'] == 'present':
            if not container:
                cloud.create_container(name)
                changed = True
            if cloud.get_container_access(name) != access:
                cloud.set_container_access(name, access)
                changed = True
        else:
            if container:
                cloud.delete_container(name)
                changed= True
        module.exit_json(changed=changed, result="success")
    except shade.OpenStackCloudException as e:
        module.fail_json(msg=e.message)

# this is magic, see lib/ansible/module_common.py
from ansible.module_utils.basic import *
from ansible.module_utils.openstack import *
main()
