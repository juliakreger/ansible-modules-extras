#!/usr/bin/python
#coding: utf-8 -*-

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
    from shade import meta
except ImportError:
    print("failed=True msg='shade is required for this module'")


DOCUMENTATION = '''
---
module: os_compute_volume
short_description: Attach/Detach Volumes from OpenStack VM's
extends_documentation_fragment: openstack
description:
   - Attach or Detach volumes from OpenStack VM's
options:
   state:
     description:
        - Indicate desired state of the resource
     choices: ['present', 'absent']
     default: present
   server:
     description:
       - Name or id of server you want to attach a volume to
     required: true
   volume:
     description:
      - Name or id of volume you want to attach to a server
     required: true
   device:
     description:
      - Device you want to attach
     required: false
     default: None
requirements: ["shade"]
'''

EXAMPLES = '''
# Attaches a volume to a compute host
- name: attach a volume
  hosts: localhost
  tasks:
  - name: attach volume to host
    os_compute_volume:
      state: present
      username: admin
      password: admin
      project_name: admin
      auth_url: https://region-b.geo-1.identity.hpcloudsvc.com:35357/v2.0/
      region_name: region-b.geo-1
      server: Mysql-server
      volume: mysql-data
      device: /dev/vdb
'''

def _wait_for_detach(cloud, module):
    expires = float(module.params['timeout']) + time.time()
    while time.time() < expires:
        volume = cloud.get_volume(module.params['volume'], cache=False)
        if volume.status == 'available':
            break
    return volume


def _check_server_attachments(volume, server_id):
    for attach in volume.attachments:
        if server_id == attach['server_id']:
            return True
    return False


def _check_device_attachment(volume, device, server_id):
    for attach in volume.attachments:
        if server_id == attach['server_id'] and device == attach['device']:
            return True
    return False


def _present_volume(cloud, nova, module, server, volume):

    try:
        if _check_server_attachments(volume, server.id)
            # Attached. Now, do we care about device?
            if (module.params['device'] and
                not _check_device_attachment(
                    volume, modules.params['device'],
                    server.id)):
                nova.volumes.delete_server_volume(server.id, volume.id)
                volume = _wait_for_detach(cloud, module)
            else:
                server = cloud.get_server_by_id(server.id)
                hostvars = meta.get_hostvars_from_server(cloud, server)
                module.exit_json(
                    changed=False,
                    result='Volume already attached',
                    attachments=volume.attachments)
    except Exception as e:
        module.fail_json(msg='Error processing volume:%s' % str(e))

    if volume.status != 'available':
        module.fail_json(msg='Cannot attach volume, not available')
    try:
        nova.volumes.create_server_volume(module.params['server_id'],
                                          volume.id,
                                          module.params['device'])
    except Exception as e:
        module.fail_json(msg='Cannot add volume to server:%s' % str(n))

    if module.params['wait']:
        expires = float(module.params['timeout']) + time.time()
        attachment = None
        while time.time() < expires:
            volume = cloud.get_volume(volume.id, cache=False)
            for attach in volume.attachments:
                if attach['server_id'] == module.params['server_id']:
                    attachment = attach
                    break

    if attachment:
        server = cloud.get_server_by_id(module.params['server_id'])
        hostvars = meta.get_hostvars_from_server(cloud, server)
        module.exit_json(
            changed=True, id=volume.id, attachments=volume.attachments,
            openstack=hostvars,
        )
    module.fail_json(
        msg='Adding volume {volume} to server {server} timed out'.format(
            volume=volume.display_name, server=module.params['server_id']))


def _absent_volume(cloud, nova, module, server, volume):

    if not _check_server_attachments(volume, server.id):
        module.exit_json(changed=False, msg='Volume is not attached to server')

    try:
        nova.volumes.delete_server_volume(server.id, volume.id)
        if module.params['wait']:
            _wait_for_detach(cloud, module)
    except Exception as e:
        module.fail_json(msg='Error removing volume from server:%s' % str(e))
    module.exit_json(changed=True, result='Detached volume from server')


def main():
    argument_spec = openstack_full_argument_spec(
        server=dict(required=True),
        volume=dict(required=True),
        device=dict(default=None),
    )
    module_kwargs = openstack_module_kwargs()

    module = AnsibleModule(argument_spec, **module_kwargs)

    try:
        cloud = shade.openstack_cloud(**module.params)
        nova = cloud.nova_client

        server = cloud.get_server(module.params['server'])
        volume = cloud.get_volume(module.params['volume'])

        if module.params['state'] == 'present':
            _present_volume(cloud, nova, module, server, volume)
        if module.params['state'] == 'absent':
            _absent_volume(cloud, nova, module, server, volume)

    except shade.OpenStackCloudException as e:
        module.fail_json(msg=e.message)

# this is magic, see lib/ansible/module_utils/common.py
from ansible.module_utils.basic import *
from ansible.module_utils.openstack import *
main()
