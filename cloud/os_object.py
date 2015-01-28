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
module: os_object
short_description: Create or Delete object objects from OpenStack
extends_documentation_fragment: openstack
description:
   - Create or Delete object objects from OpenStack
options:
   state:
     description:
        - Indicate desired state of the resource
     choices: ['present', 'absent']
     default: present
   name:
     description:
        - Name to be give to the object
     required: true
   container:
     description:
        - The name of the container in which to create the object
     required: true
   file:
     description:
        - Path to local file to be uploaded
     required: true
requirements: ["shade"]
'''

EXAMPLES = '''
# Creates a object named 'fstab' in the 'config' container
- os_object: state=present name=fstab container=config file=/etc/fstab
'''

def main():
    argument_spec = openstack_full_argument_spec(
        name=dict(required=True),
        state=dict(default='present', choices=['absent', 'present']),
        container=dict(required=True),
        file=dict(required=True),
    )
    module_kwargs = openstack_module_kwargs()
    module = AnsibleModule(argument_spec, **module_kwargs)

    if not HAS_SHADE:
        module.fail_json(msg='shade is required for this module')

    changed = False
    name  = module.params['name']
    container = module.params['container']
    filename = module.params['file']

    try:
        cloud = shade.openstack_cloud(**openstack_auth(module))

        if not cloud.get_container(container):
            module.fail_json(msg='Container %s does not exist' % container)

        if module.params['state'] == 'present':
            if cloud.is_object_stale(container, name, filename):
                cloud.create_object(container, name, filename)
                changed = True
        else:
            if cloud.get_object_metadata(container, name):
                cloud.delete_object(container, name)
                changed= True
        module.exit_json(changed=changed, result="success")
    except shade.OpenStackCloudException as e:
        module.fail_json(msg=e.message)

# this is magic, see lib/ansible/module_common.py
from ansible.module_utils.basic import *
from ansible.module_utils.openstack import *
main()
