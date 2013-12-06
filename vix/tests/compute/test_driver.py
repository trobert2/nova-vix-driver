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
import platform
import unittest

from nova.compute import task_states
from nova.openstack.common import jsonutils
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
        fake_iso_image_ids = 'fakeid'
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
        os.path.join = mock.MagicMock(return_value=fake_base_vmdk_path)
        fake_image_info.get().get().lower.return_value = str(cow).lower()
        fake_image_info.get().get().split.return_value = fake_iso_image_ids\
            .split(',')
        utils.get_free_port = mock.MagicMock()
        utils.get_free_port.return_value = 9999

        self._VixDriver.spawn(context=fake_context, instance=fake_instance,
                              image_meta=fake_image_meta,
                              injected_files=fake_injected_files,
                              admin_password=fake_admin_password,
                              network_info=fake_network_info,
                              block_device_info=fake_block_device_info)
        print fake_image_info.get().get.mock_calls


        self._image_cache.get_image_info.assert_called_with(
            fake_context, fake_instance['image_ref'])

        self._VixDriver._check_player_compatibility.assert_called_with(cow)
        self._VixDriver._delete_existing_instance.assert_called_with(
            fake_instance['name'])
        self._pathutils.create_instance_dir.assert_called_with(
            fake_instance['name'])
        self.assertEqual(self._image_cache.get_cached_image.call_count, 3)
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
                iso_paths=[fake_base_vmdk_path, fake_base_vmdk_path],
                floppy_path=fake_floppy_path,
                networks=[],
                boot_order=fake_image_info.get().get(),
                vnc_enabled=True,
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
                iso_paths=[fake_base_vmdk_path, fake_base_vmdk_path],
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

    def test_attach_volume(self):
        fake_instance = mock.MagicMock()
        fake_context = mock.MagicMock()
        fake_connection_info = mock.MagicMock()
        fake_mountpoint = mock.MagicMock()

        self.assertRaises(NotImplementedError,
                          self._VixDriver.attach_volume, fake_context,
                          fake_connection_info, fake_instance,
                          fake_mountpoint)

    def test_deattach_volume(self):
        fake_instance = mock.MagicMock()
        fake_connection_info = mock.MagicMock()
        fake_mountpoint = mock.MagicMock()

        self.assertRaises(NotImplementedError,
                          self._VixDriver.detach_volume,
                          fake_connection_info,  fake_instance,
                          fake_mountpoint)

    def test_get_volume_connector(self):
        fake_instance = mock.MagicMock()
        self.assertRaises(NotImplementedError,
                          self._VixDriver.get_volume_connector,
                          fake_instance)

    def test_get_host_memory_info(self):
        total_mem = 2147483648
        free_mem = 1073741824
        utils.get_host_memory_info = mock.MagicMock()
        utils.get_host_memory_info.return_value = (total_mem, free_mem)
        response = self._VixDriver._get_host_memory_info()
        utils.get_host_memory_info.assert_called_once()
        self.assertEqual(response, (2048, 1024, 1024))

    def test_get_local_hdd_info_gb(self):
        total_disk = 2147483648
        free_disk = 1073741824
        fake_dir = 'fake dir'
        utils.get_disk_info = mock.MagicMock()
        utils.get_disk_info.return_value = (total_disk, free_disk)
        self._pathutils.get_instances_dir = mock.MagicMock()
        self._pathutils.get_instances_dir.return_value = fake_dir
        response = self._VixDriver._get_local_hdd_info_gb()
        utils.get_disk_info.assert_called_once_with(fake_dir)
        self.assertEqual(response, (2, 1, 1))

    def test_get_hypervisor_version(self):
        self._conn.get_software_version.return_value = 10
        response = self._VixDriver._get_hypervisor_version()
        self._conn.get_software_version.assert_called_once()
        self.assertEqual(response, 10)

    def test_get_available_resource(self):
        fake_nodename = 'fake_name'
        total_disk = 2147483648
        free_disk = 1073741824
        total_mem = 2147483648
        free_mem = 1073741824
        vcpus = 2
        fake_dir = 'fake dir'
        compare_dict = {'vcpus': vcpus,
                        'memory_mb': 2048,
                        'memory_mb_used': 1024,
                        'local_gb': 2,
                        'local_gb_used': 1,
                        'hypervisor_type': "vix",
                        'hypervisor_version': 10,
                        'hypervisor_hostname': 'fake_hostname',
                        'vcpus_used': 0,
                        'cpu_info': 0,
                        'supported_instances': 0}

        jsonutils.dumps = mock.MagicMock()
        jsonutils.dumps.return_value = 0
        platform.node = mock.MagicMock()
        platform.node.return_value = 'fake_hostname'
        self._conn.get_software_version = mock.MagicMock()
        self._conn.get_software_version.return_value = 10
        utils.get_host_memory_info = mock.MagicMock()
        utils.get_host_memory_info.return_value = (total_mem, free_mem)
        utils.get_disk_info = mock.MagicMock()
        utils.get_disk_info.return_value = (total_disk, free_disk)
        self._pathutils.get_instances_dir = mock.MagicMock()
        self._pathutils.get_instances_dir.return_value = fake_dir
        utils.get_cpu_count = mock.MagicMock()
        utils.get_cpu_count.return_value = vcpus

        response = self._VixDriver.get_available_resource(fake_nodename)
        utils.get_host_memory_info.assert_called_once()
        utils.get_disk_info.assert_called_once_with(fake_dir)
        self._conn.get_software_version.assert_called_once()
        platform.node.assert_called_once()
        self.assertEqual(jsonutils.dumps.call_count, 2)
        self.assertEqual(response, compare_dict)

    def test_update_stats(self):
        total_disk = 2147483648
        free_disk = 1073741824
        total_mem = 2147483648
        free_mem = 1073741824
        fake_dir = 'fake dir'
        compare_dict = {'host_memory_total': 2048,
                        'host_memory_overhead': 1024,
                        'host_memory_free': 1024,
                        'host_memory_free_computed': 1024,
                        'disk_total': 2,
                        'disk_used': 1,
                        'disk_available': 1,
                        'hypervisor_hostname': 'fake_hostname',
                        'supported_instances': [('i686', 'vix', 'hvm'),
                                                ('x86_64', 'vix', 'hvm')],}

        platform.node = mock.MagicMock()
        platform.node.return_value = 'fake_hostname'
        utils.get_host_memory_info = mock.MagicMock()
        utils.get_host_memory_info.return_value = (total_mem, free_mem)
        utils.get_disk_info = mock.MagicMock()
        utils.get_disk_info.return_value = (total_disk, free_disk)
        self._pathutils.get_instances_dir = mock.MagicMock()
        self._pathutils.get_instances_dir.return_value = fake_dir

        self._VixDriver._update_stats()

        utils.get_host_memory_info.assert_called_once()
        utils.get_disk_info.assert_called_once_with(fake_dir)
        platform.node.assert_called_once()
        self.assertEqual(self._VixDriver._stats, compare_dict)

    def _test_get_host_stats(self, refresh):
        self._VixDriver.get_host_stats(refresh=refresh)
        self.assertIsNotNone(self._VixDriver._stats)

    def test_get_host_stats_refresh_true(self):
        self._test_get_host_stats(True)

    def test_get_host_stats_refresh_false(self):
        self._test_get_host_stats(False)

    def _test_snapshot(self, implemented):
        fake_name = 'fake name'
        fake_instance = mock.MagicMock()
        fake_context = mock.MagicMock()
        fake_update_task_state = mock.MagicMock()
        fake_path = 'fake/path'
        fake_root_vmdk_path = 'fake/root/vmdk/path'
        fake_vm = mock.MagicMock()
        self._conn.open_vm.return_value = fake_vm
        self._pathutils.get_root_vmdk_path.return_value = fake_root_vmdk_path
        self._pathutils.get_vmx_path.return_value = fake_path
        vixutils.VixVM.create_snapshot = mock.MagicMock()
        vixutils.VixVM.remove_snapshot = mock.MagicMock()
        vixutils.get_vix_host_type = mock.MagicMock()

        if not implemented:
            vixutils.get_vix_host_type.return_value = vixutils.VIX_VMWARE_PLAYER
            self.assertRaises(NotImplementedError, self._VixDriver.snapshot,
                              fake_context, fake_instance, fake_name,
                              fake_update_task_state)
        else:
            self._VixDriver.snapshot(fake_context, fake_instance, fake_name,
                                     fake_update_task_state)

            vixutils.get_vix_host_type.assert_called_once()
            self._pathutils.get_vmx_path.assert_called_with(
                fake_instance['name'])
            self._conn.open_vm.assert_called_with(fake_path)
            print self._conn.open_vm.mock_calls
            self.assertEqual(fake_update_task_state.call_count, 2)
            fake_vm.__enter__().create_snapshot.assert_called_with(
                name="Nova snapshot")
            self._image_cache.save_glance_image.assert_called_with(
                fake_context, fake_name, fake_root_vmdk_path)
            vixutils.VixVM.remove_snapshot.assert_called_once()

    def test_snapshot_not_implemented(self):
        self._test_snapshot(False)

    def test_snapshot(self):
        self._test_snapshot(True)

    def test_pause(self):
        fake_instance = mock.MagicMock()
        vixutils.VixVM.pause = mock.MagicMock()
        self._VixDriver.pause(fake_instance)
        vixutils.VixVM.pause.assert_called_once()

    def test_unpause(self):
        fake_instance = mock.MagicMock()
        vixutils.VixVM.unpause = mock.MagicMock()
        self._VixDriver.unpause(fake_instance)
        vixutils.VixVM.unpause.assert_called_once()

    def test_suspend(self):
        fake_instance = mock.MagicMock()
        vixutils.VixVM.suspend = mock.MagicMock()
        self._VixDriver.suspend(fake_instance)
        vixutils.VixVM.suspend.assert_called_once()

    def test_resume(self):
        fake_instance = mock.MagicMock()
        fake_network_info = mock.MagicMock()
        vixutils.VixVM.power_on = mock.MagicMock()
        self._VixDriver.resume(fake_instance, fake_network_info)
        vixutils.VixVM.power_on.assert_called_once()

    def test_power_off(self):
        fake_instance = mock.MagicMock()
        vixutils.VixVM.power_off = mock.MagicMock()
        self._VixDriver.power_off(fake_instance)
        vixutils.VixVM.power_off.assert_called_once()

    def test_power_on(self):
        fake_instance = mock.MagicMock()
        fake_context = mock.MagicMock()
        fake_network_info = mock.MagicMock()
        vixutils.VixVM.power_on = mock.MagicMock()
        self._VixDriver.power_on(fake_instance, fake_context,
                                 fake_network_info)
        vixutils.VixVM.power_on.assert_called_once()

    def test_live_migration(self):
        fake_context = mock.MagicMock()
        fake_recover_method = mock.MagicMock()
        fake_dest = 'fake/dest'
        fake_post_method = mock.MagicMock()
        fake_instance = mock.MagicMock()
        self.assertRaises(NotImplementedError, self._VixDriver.live_migration,
                          fake_context, fake_instance, fake_dest,
                          fake_post_method, fake_recover_method)

    def test_pre_live_migration(self):
        fake_context = mock.MagicMock()
        fake_block_device_info = mock.MagicMock()
        fake_disk = 'fake/dest'
        fake_network_info = mock.MagicMock()
        fake_instance = mock.MagicMock()
        self.assertRaises(NotImplementedError,
                          self._VixDriver.pre_live_migration, fake_context,
                          fake_instance, fake_block_device_info,
                          fake_network_info, fake_disk)

    def test_post_live_migration_at_destination(self):
        fake_context = mock.MagicMock()
        fake_network_info = mock.MagicMock()
        fake_instance_ref = mock.MagicMock()
        self.assertRaises(NotImplementedError,
                          self._VixDriver.post_live_migration_at_destination,
                          fake_context, fake_instance_ref, fake_network_info)

    def test_check_can_live_migrate_destination(self):
        fake_context = mock.MagicMock()
        fake_src_computer = mock.MagicMock()
        fake_dest_computer = mock.MagicMock()
        fake_instance_ref = mock.MagicMock()
        self.assertRaises(NotImplementedError,
                          self._VixDriver.check_can_live_migrate_destination,
                          fake_context, fake_instance_ref,
                          fake_src_computer, fake_dest_computer)

    def test_check_can_live_migrate_destination_cleanup(self):
        fake_context = mock.MagicMock()
        fake_dest_data = mock.MagicMock()
        self.assertRaises(
            NotImplementedError,
            self._VixDriver.check_can_live_migrate_destination_cleanup,
            fake_context, fake_dest_data)

    def test_check_can_live_migrate_source(self):
        fake_context = mock.MagicMock()
        fake_instance_ref = mock.MagicMock()
        fake_dest_data = mock.MagicMock()
        self.assertRaises(NotImplementedError,
                          self._VixDriver.check_can_live_migrate_source,
                          fake_context, fake_instance_ref, fake_dest_data)


    def test_get_host_ip_addr(self):
        response = self._VixDriver.get_host_ip_addr()
        self.assertIsNotNone(response)

    def _test_get_vnc_console(self, vnc_enabled):
        fake_instance = mock.MagicMock()
        fake_path = 'fake/path'
        vnc_port = 9999
        self._conn.open_vm().__enter__().get_vnc_settings.return_value = (
            vnc_enabled, vnc_port)
        self._pathutils.get_vmx_path.return_value = fake_path

        if vnc_enabled:
            response = self._VixDriver.get_vnc_console(fake_instance)
            self._pathutils.get_vmx_path.assert_called_with(
                fake_instance['name'])
            self._conn.open_vm.assert_called_with(fake_path)
            self._conn.open_vm().__enter__().get_vnc_settings\
                .assert_called_once()
            self.assertIsNotNone(response)
        else:
            self.assertRaises(utils.VixException,
                              self._VixDriver.get_vnc_console, fake_instance)

    def test_get_vnc_console(self):
        self._test_get_vnc_console(True)

    def test_get_vnc_console_disabled(self):
        self._test_get_vnc_console(False)

    def test_get_console_output(self):
        fake_instance = mock.MagicMock()
        reponse = self._VixDriver.get_console_output(fake_instance)
        self.assertEqual(reponse, '')