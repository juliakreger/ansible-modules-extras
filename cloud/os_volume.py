#!/usr/bin/python

# Copyright (c) 2014 Hewlett-Packard Development Company, L.P.
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

import time

try:
    import shade
    HAS_SHADE = True
except ImportError:
    HAS_SHADE = False

from cinderclient import exceptions as cinder_exc


DOCUMENTATION = '''
---
module: os_volume
short_description: Create/Delete Cinder Volumes
extends_documentation_fragment: openstack
description:
   - Create or Remove cinder block storage volumes
options:
   state:
     description:
        - Indicate desired state of the resource
     choices: ['present', 'absent']
     default: present
   size:
     description:
        - Size of volume in GB
     requried: true
     default: None
   display_name:
     description:
        - Name of volume
     required: true
     default: None
   display_description:
     description:
       - String describing the volume
     required: false
     default: None
   volume_type:
     description:
       - Volume type for volume
     required: false
     default: None
   image:
     descritpion:
       - Image name or id for boot from volume
     required: false
     default: None
   snapshot_id:
     description:
       - Volume snapshot id to create from
     required: false
     default: None
requirements: ["shade"]
'''

EXAMPLES = '''
# Creates a new volume
- name: create a volume
  hosts: localhost
  tasks:
  - name: create 40g test volume
    os_volume:
      state: present
      username: username
      password: Equality7-2521
      project_name: username-project1
      auth_url: https://region-b.geo-1.identity.hpcloudsvc.com:35357/v2.0/
      region_name: region-b.geo-1
      availability_zone: az2
      size: 40
      display_name: test_volume
'''

def _present_volume(module, cinder, cloud):
    if cloud.volume_exists(module.param['display_name']):
        v = cloud.get_volume(module.param['display_name'])
        module.exit_json(changed=False, id=v.id, info=v._info)

    volume_args = dict(
        size=module.params['size'],
        volume_type=module.params['volume_type'],
        display_name=module.params['display_name'],
        display_description=module.params['display_description'],
        snapshot_id=module.params['snapshot_id'],
        availability_zone=module.params['availability_zone'],
    )
    if module.params['image']:
        image_id = cloud.get_image_id(module.params['image'])
        volume_args['imageRef'] = image_id

    volume = cloud.volume_create(
        volume_args, wait=module.params['wait'],
        timeout=module.params['timeout'])
    module.exit_json(changed=True, id=volume.id, info=volume._info)


def _absent_volume(module, cloud):

    try:
        cloud.delete_volume(
            module.params['display_name'],
            module.params['wait'], module.params['timeout'])
    except shade.OpenStackCloudTimeout:
        module.exit_json(changed=False, result="Volume deletion timed-out")
    module.exit_json(changed=True, result='Volume Deleted')


def main():
    argument_spec = openstack_full_argument_spec(
        size=dict(required=True),
        volume_type=dict(default=None),
        display_name=dict(required=True, aliases=['name']),
        display_description=dict(default=None, aliases=['description']),
        image=dict(default=None),
        snapshot_id=dict(default=None),
    )
    module_kwargs = openstack_module_kwargs(
        mutually_exclusive = [
            ['image', 'snapshot_id'],
        ],
    )
    module = AnsibleModule(argument_spec=argument_spec, **module_kwargs)

    if not HAS_SHADE:
        module.fail_json(msg='shade is required for this module')

    try:
        cloud = shade.openstack_cloud(**openstack_auth(module))
        if module.params['state'] == 'present':
            _present_volume(module, cloud)
        if module.params['state'] == 'absent':
            _absent_volume(module, cloud)
    except shade.OpenStackCloudException as e:
        module.fail_json(msg=e.message)

# this is magic, see lib/ansible/module_common.py
from ansible.module_utils.basic import *
from ansible.module_utils.openstack import *
main()
