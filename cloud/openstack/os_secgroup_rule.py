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
module: os_secgroup_rule
short_description: Add/Delete rule from an existing security group
extends_documentation_fragment: openstack
description:
   - Add or Remove rule from an existing security group
options:
   security_group:
     description:
        - Name of the security group
     required: true
   ip_protocol:
      description:
        - IP protocol
      choices: ['tcp', 'udp', 'icmp']
      default: tcp
   from_port:
      description:
        - Starting port
      required: true
   to_port:
      description:
        - Ending port
     required: true
   cidr:
      description:
        - Source IP address(es) in CIDR notation

requirements: ["shade"]
'''

EXAMPLES = '''
# Create a security group rule
- os_secgroup_rule: cloud=mordred
                    security_group=group foo
                    ip_protocol: tcp
                    from_port: 80
                    to_port: 80
                    cidr: 0.0.0.0/0
'''


def _security_group_rule(module, nova_client, action='create', **kwargs):
    f = getattr(nova_client.security_group_rules, action)
    try:
        secgroup = f(**kwargs)
    except Exception, e:
        module.fail_json(msg='Failed to %s security group rule: %s' %
                         (action, e.message))


def _get_rule_from_group(module, secgroup):
    for rule in secgroup.rules:
        if (rule['ip_protocol'] == module.params['ip_protocol'] and
            rule['from_port'] == module.params['from_port'] and
            rule['to_port'] == module.params['to_port'] and
            rule['ip_range']['cidr'] == module.params['cidr']):
            return rule
    return None

def main():

    argument_spec = openstack_full_argument_spec(
        security_group      = dict(required=True),
        ip_protocol         = dict(default='tcp', choices=['tcp', 'udp', 'icmp']),
        from_port           = dict(required=True),
        to_port             = dict(required=True),
        cidr                = dict(required=True),
    )
    module_kwargs = openstack_module_kwargs()
    module = AnsibleModule(argument_spec, **module_kwargs)

    try:
        cloud = shade.openstack_cloud(**module.params)
        nova_client = cloud.nova_client
        changed = False

        secgroup = cloud.get_security_group(module.params['security_group'])

        if module.params['state'] == 'present':
            if not secgroup:
                module.fail_json(msg='Could not find security group %s' %
                                 module.params['security_group'])

            if not _get_rule_from_group(module, secgroup):
                _security_group_rule(module, nova_client, 'create',
                                     parent_group_id=secgroup.id,
                                     ip_protocol=module.params['ip_protocol'],
                                     from_port=module.params['from_port'],
                                     to_port=module.params['to_port'],
                                     cidr=module.params['cidr'])
                changed = True


        if module.params['state'] == 'absent' and secgroup:
            rule = _get_rule_from_group(module, secgroup)
            if secgroup and rule:
                _security_group_rule(module, nova_client, 'delete',
                                     rule=rule['id'])
                changed = True

        module.exit_json(changed=changed, result="success")

    except shade.OpenStackCloudException as e:
        module.fail_json(msg=e.message)

# this is magic, see lib/ansible/module_common.py
from ansible.module_utils.basic import *
from ansible.module_utils.openstack import *
main()
