#!/usr/bin/python

# Copyright (c) 2014 Hewlett-Packard Development Company, L.P.
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
module: os_image
short_description: Add/Delete images from OpenStack Cloud
extends_documentation_fragment: openstack
description:
   - Add or Remove images from the OpenStack Image Repository
options:
   state:
     description:
        - Indicate desired state of the resource
     choices: ['present', 'absent']
     default: present
   name:
     description:
        - Name that has to be given to the image
     required: true
     default: None
   disk_format:
     description:
        - The format of the disk that is getting uploaded
     required: false
     default: qcow2
   container_format:
     description:
        - The format of the container
     required: false
     default: bare
   owner:
     description:
        - The owner of the image
     required: false
     default: None
   min_disk:
     description:
        - The minimum disk space required to deploy this image
     required: false
     default: None
   min_ram:
     description:
        - The minimum ram required to deploy this image
     required: false
     default: None
   is_public:
     description:
        - Whether the image can be accessed publicly. Note that publicizing an image requires admin role by default.
     required: false
     default: 'yes'
   copy_from:
     description:
        - A url from where the image can be downloaded, mutually exclusive with file parameter
     required: false
     default: None
   timeout:
     description:
        - The time to wait for the image process to complete in seconds
     required: false
     default: 180
   file:
     description:
        - The path to the file which has to be uploaded, mutually exclusive with copy_from
     required: false
     default: None
   ramdisk:
     descrption:
        - The name of an existing ramdisk image that will be associated with this image
     required: false
     default: None
   kernel:
     descrption:
        - The name of an existing kernel image that will be associated with this image
     required: false
     default: None
   properties:
     description:
        - Additional properties to be associated with this image
requirements: ["shade"]
'''

EXAMPLES = '''
# Upload an image from an HTTP URL
- os_image: username=admin
                password=passme
                project_name=admin
                name=cirros
                container_format=bare
                disk_format=qcow2
                state=present
                copy_from=http:launchpad.net/cirros/trunk/0.3.0/+download/cirros-0.3.0-x86_64-disk.img
                kernel=cirros-vmlinuz
                ramdisk=cirros-initrd
                properties:
                    cpu_arch=x86_64
                    distro=ubuntu
'''

import time


def _glance_image_create(module, params, client):
    kwargs = {
                'name':             params.get('name'),
                'disk_format':      params.get('disk_format'),
                'container_format': params.get('container_format'),
                'owner':            params.get('owner'),
                'is_public':        params.get('is_public'),
                'copy_from':        params.get('copy_from'),
    }
    try:
        timeout = params.get('timeout')
        expire = time.time() + timeout
        image = client.images.create(**kwargs)
        if not params['copy_from']:
            image.update(data=open(params['file'], 'rb'))
        while time.time() < expire:
            image = client.images.get(image.id)
            if image.status == 'active':
                break
            time.sleep(5)
    except Exception, e:
        module.fail_json(msg="Error in creating image: %s" % type(e))
    if image.status == 'active':
        return image
    else:
        module.fail_json(msg=" The module timed out, please check manually " + image.status)


def _glance_delete_image(module, params, client):
    try:
        for image in client.images.list():
            if image.name == params['name']:
                client.images.delete(image)
    except Exception, e:
        module.fail_json(msg="Error in deleting image: %s" % e.message)
    module.exit_json(changed=True, result="Deleted")


def _glance_update_image_properties(module, properties, image):
    try:
        image.update(properties=properties)
    except Exception, e:
        module.fail_json(msg="Failed to update image properties for %s: %s" %
                         (image.id, e.message))


def main():

    argument_spec = openstack_full_argument_spec(
        name              = dict(required=True),
        disk_format       = dict(default='qcow2', choices=['ami', 'ari', 'aki', 'vhd', 'vmdk', 'raw', 'qcow2', 'vdi', 'iso']),
        container_format  = dict(default='bare', choices=['ami', 'aki', 'ari', 'bare', 'ovf', 'ova']),
        owner             = dict(default=None),
        min_disk          = dict(default=None),
        min_ram           = dict(default=None),
        is_public         = dict(default=False),
        copy_from         = dict(default= None),
        file              = dict(default=None),
        ramdisk           = dict(default=None),
        kernel            = dict(default=None),
        properties        = dict(default=None),
    )
    module_kwargs = openstack_module_kwargs(
        mutually_exclusive = [['file','copy_from']],
    )
    module = AnsibleModule(argument_spec, **module_kwargs)

    if not HAS_SHADE:
        module.fail_json(msg='shade is required for this module')

    if module.params['state'] == 'present':
        if not module.params['file'] and not module.params['copy_from']:
            module.fail_json(msg="Either file or copy_from variable should be set to create the image")

    try:
        cloud = shade.openstack_cloud(**openstack_auth(module))

        changed = False
        image = cloud.get_image(name_or_id=module.params['name'])

        if module.params['state'] == 'present':
            if not image:
                image = _glance_image_create(module, module.params, cloud.glance_client)
                changed = True

        img_props = {}
        for attr in ['ramdisk', 'kernel']:
            if module.params[attr]:
                other_image_id = cloud.get_image_id(module.params[attr])
                if image.properties.get('%s_id' % attr) != other_image_id:
                    spec = '%s_id' % attr
                    img_props[spec] = other_image_id

        properties = module.params['properties']
        if properties:
            for k, v in properties.iteritems():
                if image.properties.get(k) != v:
                    img_props[k] = v

        if img_props:
            changed=True
            _glance_update_image_properties(module, img_props, image)

        if module.params['state'] == 'absent':
            if not image:
                module.exit_json(changed=False, result="success")
            else:
                _glance_delete_image(module, module.params, cloud.glance_client)
                changed = True

        module.exit_json(changed=changed, id=image.id, result="success")

    except shade.OpenStackCloudException as e:
        module.fail_json(msg=e.message)

# this is magic, see lib/ansible/module_common.py
from ansible.module_utils.basic import *
from ansible.module_utils.openstack import *
main()
