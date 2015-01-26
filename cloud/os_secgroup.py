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
except ImportError:
    print("failed=True msg='shade is required for this module'")


DOCUMENTATION = '''
---
module: os_secgroup
short_description: Add/Delete Nova security groups from an OpenStack cloud.
extends_documentation_fragment: openstack
description:
   - Add or Remove security groups from an OpenStack cloud.
options:
   state:
     description:
        - Indicate desired state of the resource
     choices: ['present', 'absent']
     default: present
   name:
     description:
        - Name that has to be given to the security group
     required: true
     default: None

requirements: ["shade"]
'''

EXAMPLES = '''
# Create a security group
- os_secgroup:  username=admin
                password=passme
                project_name=admin
                name=group foo
                description=security group for foo servers
'''


def _security_group(module, nova_client, action='create', **kwargs):
    f = getattr(nova_client.security_groups, action)
    try:
        secgroup = f(**kwargs)
    except Exception, e:
        module.fail_json(msg='Failed to %s security group %s: %s' %
                         (action, module.params['name'], e.message))


def main():

    argument_spec = openstack_full_argument_spec(
        name              = dict(required=True),
        description       = dict(default=None),
    )
    module_kwargs = openstack_module_kwargs()
    module = AnsibleModule(argument_spec, **module_kwargs)

    try:
        cloud = shade.openstack_cloud(**openstack_auth(module))
        nova_client = cloud.nova_client
        changed = False
        secgroup = cloud.get_security_group(module.params['name'])

        if module.params['state'] == 'present':
            secgroup = cloud.get_security_group(module.params['name'])
            if not secgroup:
                _security_group(module, nova_client, action='create',
                                name=module.params['name'],
                                description=module.params['description'])
                changed = True

        if secgroup and secgroup.description != module.params['description']:
            _security_group(module, nova_client, action='update',
                            group=secgroup.id,
                            name=module.params['name'],
                            description=module.params['description'])
            changed = True

        if module.params['state'] == 'absent':
            if secgroup:
                _security_group(module, nova_client, action='delete',
                                group=secgroup.id)
                changed = True

        module.exit_json(changed=changed, id=module.params['name'], result="success")

    except shade.OpenStackCloudException as e:
        module.fail_json(msg=e.message)

# this is magic, see lib/ansible/module_common.py
from ansible.module_utils.basic import *
from ansible.module_utils.openstack import *
main()
