# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 Cloudbase Solutions Srl
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import mock
import os
import unittest

from oslo.config import cfg
from vix.compute import driver
from vix.compute import image_cache
from vix.compute import pathutils
from vix import utils
from vix import vixlib
from vix import vixutils


class VixDriverTestCase(unittest.TestCase):
    """Unit tests for Nova VIX driver"""

    def setUp(self):
        self.CONF = mock.MagicMock()
        cfg.CONF = mock.MagicMock(return_value=self.CONF)
        virtapi = mock.MagicMock()
        self._conn = mock.MagicMock()
        self._pathutils = mock.MagicMock()
        self._image_cache = mock.MagicMock()

        vixutils.VixConnection = mock.MagicMock(return_value=self._conn)
        pathutils.PathUtils = mock.MagicMock(return_value=self._pathutils)
        image_cache.ImageCache = mock.MagicMock(return_value=self._image_cache)
        self._VixDriver = driver.VixDriver(virtapi)

    def test_list_instances(self):
        self._VixDriver.list_instances()
        self._conn.list_running_vms.assert_called_once()

    def test_delete_existing_instance(self):
        fake_instance_name = 'fake_name'
        fake_path = 'fake/path'
        self._pathutils.get_vmx_path.return_value = fake_path

        self._VixDriver._delete_existing_instance(fake_instance_name)

        self._pathutils.get_vmx_path.assert_called_with('fake_name')
        self._conn.vm_exists.assert_called_with(fake_path)
        self._conn.unregister_vm_and_delete_files.assert_called_with(
            fake_path, True)

    def test_clone_vmdk_vm(self):
        fake_src_vmdk = 'src/fake.vmdk'
        fake_file_name = 'fake.vmdk'
        fake_root_vmdk_path = 'root/fake.vmdk'
        fake_dest_vmx_path = 'dest/fake.vmdk'
        fake_vmdk_path = 'path/fake.vmdk'
        fake_split = mock.MagicMock()
        fake_base = mock.MagicMock()

        os.path.basename = mock.MagicMock(return_value=fake_base)
        os.path.splitext = mock.MagicMock(return_value=fake_split)
        os.path.dirname = mock.MagicMock()
        os.path.join = mock.MagicMock(return_value=fake_vmdk_path)
        vixutils.get_vmx_value = mock.MagicMock()
        vixutils.get_vmx_value.return_value = fake_file_name
        vixutils.set_vmx_value = mock.MagicMock()

        self._VixDriver._clone_vmdk_vm(fake_src_vmdk, fake_root_vmdk_path,
                                       fake_dest_vmx_path)

        self._conn.create_vm.assert_called_once()
        self._conn.clone_vm.assert_called_with(fake_split[0] + ".vmx",
                                               fake_dest_vmx_path, True)
        self._pathutils.rename.assert_called_with(fake_vmdk_path,
                                                  fake_root_vmdk_path)
        vixutils.set_vmx_value.assert_called_with(fake_split[0] + ".vmsd",
                                                  "sentinel0", fake_base)

    def test_check_player_compatibility(self):
        vixutils.get_vix_host_type = mock.MagicMock(
            return_value=vixutils.VIX_VMWARE_PLAYER)
        self.assertRaises(NotImplementedError,
                          self._VixDriver._check_player_compatibility, True)

    def _test_spawn(self, cow):

        fake_admin_password = 'fake password'
        fake_instance = mock.MagicMock()
        fake_context = mock.MagicMock()
        fake_image_meta = mock.MagicMock()
        fake_injected_files = mock.MagicMock()
        fake_network_info = mock.MagicMock()
        fake_block_device_info = mock.MagicMock()
        fake_image_info = mock.MagicMock()
        fake_iso_image_ids = mock.MagicMock()
        fake_base_vmdk_path = 'fake/base/vmdk/path'
        fake_root_vmdk_path = 'fake/root/vmdk/path'
        fake_vmx_path = 'fake/vmx/path'
        fake_floppy_path = 'fake/floppy/path'

        self._image_cache.get_image_info.return_value = fake_image_info
        self._VixDriver._check_player_compatibility = mock.MagicMock()
        self._VixDriver._delete_existing_instance =  mock.MagicMock()
        self._VixDriver._clone_vmdk_vm =  mock.MagicMock()
        self._image_cache.get_cached_image.return_value = fake_base_vmdk_path
        self._pathutils.get_root_vmdk_path.return_value = fake_root_vmdk_path
        self._pathutils.get_vmx_path.return_value = fake_vmx_path
        self._pathutils.get_floppy_path.return_value = fake_floppy_path
        os.path.join = mock.MagicMock()
        fake_image_info.get().get().lower.return_value = str(cow).lower()
        fake_image_info.get().get().split.return_value = fake_iso_image_ids
        utils.get_free_port = mock.MagicMock()
        utils.get_free_port.return_value = 9999

        self._VixDriver.spawn(context=fake_context, instance=fake_instance,
                              image_meta=fake_image_meta,
                              injected_files=fake_injected_files,
                              admin_password=fake_admin_password,
                              network_info=fake_network_info,
                              block_device_info=fake_block_device_info)
        print self._conn.create_vm.mock_calls

        self._image_cache.get_image_info.assert_called_with(
            fake_context, fake_instance['image_ref'])

        self._VixDriver._check_player_compatibility.assert_called_with(cow)
        self._VixDriver._delete_existing_instance.assert_called_with(
            fake_instance['name'])
        self._pathutils.create_instance_dir.assert_called_with(
            fake_instance['name'])
        self.assertEqual(self._image_cache.get_cached_image.call_count, 2)#3
        self._pathutils.get_root_vmdk_path.assert_called_with(
            fake_instance['name'])
        self._pathutils.get_vmx_path.assert_called_with(fake_instance['name'])
        if cow:
            self._VixDriver._clone_vmdk_vm.assert_called_with(
                fake_base_vmdk_path, fake_root_vmdk_path, fake_vmx_path)
            self.assertEqual(self._pathutils.copy.call_count, 1)
            self._conn.update_vm.assert_called_with(
                vmx_path=fake_vmx_path,
                display_name=fake_instance.get("display_name"),
                guest_os=fake_image_info.get().get(),
                num_vcpus=fake_instance['vcpus'],
                mem_size_mb=fake_instance['memory_mb'],
                iso_paths=[self._conn.get_tools_iso_path()],
                floppy_path=fake_floppy_path,
                networks=[],
                boot_order=fake_image_info.get().get(),
                vnc_enabled=self.CONF.vnc_enabled,
                vnc_port=9999, nested_hypervisor=fake_image_info.get().get())
        else:
            self.assertEqual(self._pathutils.copy.call_count, 2)
            self._conn.create_vm.assert_called_with(
                vmx_path=fake_vmx_path,
                display_name=fake_instance.get("display_name"),
                guest_os=fake_image_info.get().get(),
                num_vcpus=fake_instance['vcpus'],
                mem_size_mb=fake_instance['memory_mb'],
                disk_paths=[fake_root_vmdk_path],
                iso_paths=[os.path.join()],
                floppy_path=fake_floppy_path,
                networks=[],
                boot_order=fake_image_info.get().get(),
                vnc_enabled=True,
                vnc_port=9999, nested_hypervisor=fake_image_info.get().get())

        os.path.join.assert_called_with(
            self._conn.get_tools_iso_path(),
            "%s.iso" % fake_image_info.get().get())
        self._pathutils.get_floppy_path.assert_called_with(
            fake_instance['name'])
        utils.get_free_port.assert_called_once()
        self._conn.open_vm.assert_called_with(fake_vmx_path)

    def test_spawn_cow(self):
        self._test_spawn(cow=True)

    def test_spawn_no_cow(self):
        self._test_spawn(cow=False)

    def _test_exec_vm_action(self, vm_exists):
        fake_instance = mock.MagicMock()
        fake_action = mock.MagicMock()

        fake_path = 'fake/path'
        self._pathutils.get_vmx_path.return_value = fake_path
        self._conn.vm_exists.return_value = vm_exists
        if not vm_exists:
            self.assertRaises(Exception, self._VixDriver._exec_vm_action,
                              fake_instance, fake_action)
        else:
            response = self._VixDriver._exec_vm_action(fake_instance,
                                                       fake_action)
            self._conn.open_vm.assert_called_with(fake_path)
            self.assertIsNotNone(response)

    def test_exec_vm_action_vm_exists_false(self):
        self._test_exec_vm_action(False)

    def test_exec_vm_action_vm_exists_true(self):
        self._test_exec_vm_action(True)

    def test_reboot(self):
        fake_instance = mock.MagicMock()
        fake_context = mock.MagicMock()
        fake_network_info = mock.MagicMock()
        vixutils.reboot = mock.MagicMock()
        self._VixDriver.reboot(fake_context, fake_instance,
                               fake_network_info, reboot_type=None)
        vixutils.reboot.assert_called_once()

    def test_destroy(self):
        fake_instance = mock.MagicMock()
        fake_network_info = mock.MagicMock()
        self._VixDriver._delete_existing_instance = mock.MagicMock()
        self._VixDriver.destroy(fake_instance, fake_network_info)
        self._VixDriver._delete_existing_instance.assert_called_with(
            fake_instance['name'], True)

    def test_get_info(self):
        fake_instance = mock.MagicMock()

        vixutils.get_power_state = mock.MagicMock(
            return_value=vixlib.VIX_POWERSTATE_POWERED_ON)

        response = self._VixDriver.get_info(fake_instance)
        print response
        vixutils.get_power_state.assert_called_once()
        self.assertIsNotNone(response)

    def test_get_hypervisor_version(self):
        self._conn.get_software_version.return_value = 10
        response = self._VixDriver._get_hypervisor_version()
        self._conn.get_software_version.assert_called_once()
        self.assertEqual(response, 10)




