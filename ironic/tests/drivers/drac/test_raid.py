#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""
Test class for DRAC RAID interface
"""
import mock

from ironic.common import exception
from ironic.drivers.modules.drac import client as drac_client
from ironic.drivers.modules.drac import raid as drac_raid
from ironic.drivers.modules.drac import resource_uris
from ironic.tests.conductor import utils as mgr_utils
from ironic.tests.db import base as db_base
from ironic.tests.db import utils as db_utils
from ironic.tests.drivers.drac import utils as test_utils
from ironic.tests.drivers.drac import wsman_mock_raid
from ironic.tests.objects import utils as obj_utils

INFO_DICT = db_utils.get_test_drac_info()


@mock.patch.object(drac_client, 'pywsman')
class DracQueryRaidConfigurationTestCase(db_base.DbTestCase):

    def setUp(self):
        super(DracQueryRaidConfigurationTestCase, self).setUp()
        mgr_utils.mock_the_extension_manager(driver='fake_drac')
        self.node = obj_utils.create_test_node(self.context,
                                               driver='fake_drac',
                                               driver_info=INFO_DICT)

    def test_list_raid_controllers(self, mock_pywsman):
        mock_pywsman_client = mock_pywsman.Client.return_value
        mock_pywsman_client.enumerate.return_value = (
            test_utils.mock_wsman_root(
                wsman_mock_raid.Enumerations[
                    resource_uris.DCIM_ControllerView]['ok']))
        wsman_raid_controllers = [{'id': 'RAID.Integrated.1-1',
                                   'model': 'PERC H710 Mini'}]

        raid_controllers = drac_raid.list_raid_controllers(self.node)

        mock_pywsman_client.enumerate.assert_called_once_with(mock.ANY, None,
            resource_uris.DCIM_ControllerView)
        self.assertEqual(raid_controllers, wsman_raid_controllers)

    def test_list_virtual_disks(self, mock_pywsman):
        mock_pywsman_client = mock_pywsman.Client.return_value
        mock_pywsman_client.enumerate.return_value = (
            test_utils.mock_wsman_root(
                wsman_mock_raid.Enumerations[
                    resource_uris.DCIM_VirtualDiskView]['ok']))
        wsman_virtual_disks = [{'controller': 'RAID.Integrated.1-1',
                                'id': 'Disk.Virtual.0:RAID.Integrated.1-1',
                                'size_gb': 558,
                                'raid_level': '1',
                                'name': 'disk 0',
                                'state': 'ok',
                                'raid_state': 'online'}]

        physical_disks = drac_raid.list_virtual_disks(self.node)

        mock_pywsman_client.enumerate.assert_called_once_with(mock.ANY, None,
            resource_uris.DCIM_VirtualDiskView)
        self.assertEqual(physical_disks, wsman_virtual_disks)

    def test_list_physical_disks(self, mock_pywsman):
        mock_pywsman_client = mock_pywsman.Client.return_value
        mock_pywsman_client.enumerate.return_value = (
            test_utils.mock_wsman_root(
                wsman_mock_raid.Enumerations[
                    resource_uris.DCIM_PhysicalDiskView]['ok']))
        wsman_physical_disks = [
            {'controller': 'RAID.Integrated.1-1',
             'id': 'Disk.Bay.0:Enclosure.Internal.0-1:RAID.Integrated.1-1',
             'disk_type': 'hdd',
             'interface_type': 'sas',
             'size_gb': 558,
             'free_size_gb': 558,
             'vendor': 'SEAGATE',
             'model': 'ST600MM0006',
             'serial_number': 'S0M3EVL6',
             'firmware_version': 'LS0A',
             'state': 'ok',
             'raid_state': 'ready'},
            {'controller': 'RAID.Integrated.1-1',
             'id': 'Disk.Bay.1:Enclosure.Internal.0-1:RAID.Integrated.1-1',
             'disk_type': 'hdd',
             'interface_type': 'sas',
             'size_gb': 558,
             'free_size_gb': 558,
             'vendor': 'SEAGATE',
             'model': 'ST600MM0006',
             'serial_number': 'S0M3EY2Z',
             'firmware_version': 'LS0A',
             'state': 'ok',
             'raid_state': 'ready'}
        ]

        physical_disks = drac_raid.list_physical_disks(self.node)

        mock_pywsman_client.enumerate.assert_called_once_with(mock.ANY, None,
            resource_uris.DCIM_PhysicalDiskView)
        self.assertEqual(physical_disks, wsman_physical_disks)


class DracManageVirtualDisksTestCase(db_base.DbTestCase):

    def setUp(self):
        super(DracManageVirtualDisksTestCase, self).setUp()
        mgr_utils.mock_the_extension_manager(driver='fake_drac')
        self.node = obj_utils.create_test_node(self.context,
                                               driver='fake_drac',
                                               driver_info=INFO_DICT)

    @mock.patch.object(drac_client, 'pywsman')
    def test_create_virtual_disk_ok(self, mock_pywsman):
        mock_pywsman_client = mock_pywsman.Client.return_value
        mock_pywsman_client.invoke.return_value = (
            test_utils.mock_wsman_root(
                wsman_mock_raid.Invocations[
                    resource_uris.DCIM_RAIDService][
                        'CreateVirtualDisk']['ok']))

        drac_raid.create_virtual_disk(self.node, raid_controller='controller',
            physical_disks=['disk1', 'disk2'], size_mb=42, raid_level='1+0')

        mock_pywsman_client.invoke.assert_called_once_with(mock.ANY,
            resource_uris.DCIM_RAIDService, 'CreateVirtualDisk', mock.ANY)

    @mock.patch.object(drac_client, 'pywsman')
    def test_create_virtual_disk_error(self, mock_pywsman):
        mock_pywsman_client = mock_pywsman.Client.return_value
        mock_pywsman_client.invoke.return_value = (
            test_utils.mock_wsman_root(
                wsman_mock_raid.Invocations[
                    resource_uris.DCIM_RAIDService][
                        'CreateVirtualDisk']['error']))

        self.assertRaises(exception.DracOperationFailed,
                          drac_raid.create_virtual_disk, self.node,
                          raid_controller='controller',
                          physical_disks=['disk1', 'disk2'], size_mb=42,
                          raid_level='1+0')

    def test_create_virtual_disk_missing_controller(self):
        self.assertRaises(exception.InvalidParameterValue,
                          drac_raid.create_virtual_disk, self.node,
                          physical_disks=['disk1', 'disk2'], size_mb=42,
                          raid_level='1+0')

    def test_create_virtual_disk_missing_disks(self):
        self.assertRaises(exception.InvalidParameterValue,
                          drac_raid.create_virtual_disk, self.node,
                          raid_controller='controller',
                          size_mb=42,
                          raid_level='1+0')

    def test_create_virtual_disk_missing_size(self):
        self.assertRaises(exception.InvalidParameterValue,
                          drac_raid.create_virtual_disk, self.node,
                          raid_controller='controller',
                          physical_disks=['disk1', 'disk2'],
                          raid_level='1+0')

    def test_create_virtual_disk_missing_raid_level(self):
        self.assertRaises(exception.InvalidParameterValue,
                          drac_raid.create_virtual_disk, self.node,
                          raid_controller='controller',
                          physical_disks=['disk1', 'disk2'], size_mb=42)

    @mock.patch.object(drac_client, 'get_wsman_client')
    def test_create_virtual_disk_calling_client_with_correct_params(
            self, mock_get_client):
        expected_selectors = {'CreationClassName': 'DCIM_RAIDService',
                              'SystemName': 'DCIM:ComputerSystem',
                              'Name': 'DCIM:RAIDService',
                              'SystemCreationClassName': 'DCIM_ComputerSystem'}
        expected_properties = {'Target': 'controller',
                                'PDArray': ['disk1', 'disk2'],
                                'VDPropNameArray': ['Size', 'RAIDLevel'],
                                'VDPropValueArray': ['42', '2048']}
        mock_drac_client = mock_get_client.return_value

        drac_raid.create_virtual_disk(self.node, raid_controller='controller',
            physical_disks=['disk1', 'disk2'], size_mb=42, raid_level='1+0')

        mock_drac_client.wsman_invoke.assert_called_once_with(
            resource_uris.DCIM_RAIDService, 'CreateVirtualDisk',
            expected_selectors, expected_properties)

    @mock.patch.object(drac_client, 'pywsman')
    def test_delete_virtual_disk_ok(self, mock_pywsman):
        mock_pywsman_client = mock_pywsman.Client.return_value
        mock_pywsman_client.invoke.return_value = (
            test_utils.mock_wsman_root(
                wsman_mock_raid.Invocations[
                    resource_uris.DCIM_RAIDService][
                        'DeleteVirtualDisk']['ok']))

        drac_raid.delete_virtual_disk(self.node, virtual_disk='vdisk')

        mock_pywsman_client.invoke.assert_called_once_with(mock.ANY,
            resource_uris.DCIM_RAIDService, 'DeleteVirtualDisk', mock.ANY)

    @mock.patch.object(drac_client, 'pywsman')
    def test_delete_virtual_disk_error(self, mock_pywsman):
        mock_pywsman_client = mock_pywsman.Client.return_value
        mock_pywsman_client.invoke.return_value = (
            test_utils.mock_wsman_root(
                wsman_mock_raid.Invocations[
                    resource_uris.DCIM_RAIDService][
                        'DeleteVirtualDisk']['error']))

        self.assertRaises(exception.DracOperationFailed,
                          drac_raid.delete_virtual_disk, self.node,
                          virtual_disk='vdisk')

    def test_delete_virtual_disk_missing_virtual_disk(self):
        self.assertRaises(exception.InvalidParameterValue,
                          drac_raid.delete_virtual_disk, self.node)

    @mock.patch.object(drac_client, 'get_wsman_client')
    def test_delete_virtual_disk_calling_client_with_correct_params(
            self, mock_get_client):
        expected_selectors = {'CreationClassName': 'DCIM_RAIDService',
                              'SystemName': 'DCIM:ComputerSystem',
                              'Name': 'DCIM:RAIDService',
                              'SystemCreationClassName': 'DCIM_ComputerSystem'}
        expected_properties = {'Target': 'vdisk'}
        mock_drac_client = mock_get_client.return_value

        drac_raid.delete_virtual_disk(self.node, virtual_disk='vdisk')

        mock_drac_client.wsman_invoke.assert_called_once_with(
            resource_uris.DCIM_RAIDService, 'DeleteVirtualDisk',
            expected_selectors, expected_properties)

    @mock.patch.object(drac_client, 'pywsman')
    def test_apply_pending_config_ok(self, mock_pywsman):
        mock_pywsman_client = mock_pywsman.Client.return_value
        mock_pywsman_client.invoke.return_value = (
            test_utils.mock_wsman_root(
                wsman_mock_raid.Invocations[
                    resource_uris.DCIM_RAIDService][
                        'CreateTargetedConfigJob']['ok']))

        job_id = drac_raid.apply_pending_config(self.node,
                                                raid_controller='controller')

        mock_pywsman_client.invoke.assert_called_once_with(mock.ANY,
            resource_uris.DCIM_RAIDService, 'CreateTargetedConfigJob',
            mock.ANY)
        self.assertEqual('JID_252423451279', job_id)

    @mock.patch.object(drac_client, 'pywsman')
    def test_apply_pending_config_error(self, mock_pywsman):
        mock_pywsman_client = mock_pywsman.Client.return_value
        mock_pywsman_client.invoke.return_value = (
            test_utils.mock_wsman_root(
                wsman_mock_raid.Invocations[
                    resource_uris.DCIM_RAIDService][
                        'CreateTargetedConfigJob']['error']))

        self.assertRaises(exception.DracOperationFailed,
                          drac_raid.apply_pending_config, self.node,
                          raid_controller='controller')

    def test_apply_pending_config_missing_controller(self):
        self.assertRaises(exception.InvalidParameterValue,
                          drac_raid.apply_pending_config, self.node)

    @mock.patch.object(drac_client, 'get_wsman_client')
    def test_apply_pending_config_calling_client_with_correct_params(
            self, mock_get_client):
        expected_selectors = {'CreationClassName': 'DCIM_RAIDService',
                              'SystemName': 'DCIM:ComputerSystem',
                              'Name': 'DCIM:RAIDService',
                              'SystemCreationClassName': 'DCIM_ComputerSystem'}
        expected_properties = {'ScheduledStartTime': 'TIME_NOW',
                                'Target': 'controller'}
        expected_return = drac_client.RET_CREATED
        mock_drac_client = mock_get_client.return_value

        drac_raid.apply_pending_config(self.node,
                                            raid_controller='controller')

        mock_drac_client.wsman_invoke.assert_called_once_with(
            resource_uris.DCIM_RAIDService, 'CreateTargetedConfigJob',
            expected_selectors, expected_properties,
            expected_return=expected_return)

    @mock.patch.object(drac_client, 'pywsman')
    def test_delete_pending_config_ok(self, mock_pywsman):
        mock_pywsman_client = mock_pywsman.Client.return_value
        mock_pywsman_client.invoke.return_value = (
            test_utils.mock_wsman_root(
                wsman_mock_raid.Invocations[
                    resource_uris.DCIM_RAIDService][
                        'DeletePendingConfiguration']['ok']))

        drac_raid.delete_pending_config(self.node,
                                        raid_controller='controller')

        mock_pywsman_client.invoke.assert_called_once_with(mock.ANY,
            resource_uris.DCIM_RAIDService, 'DeletePendingConfiguration',
            mock.ANY)

    @mock.patch.object(drac_client, 'pywsman')
    def test_delete_pending_config_error(self, mock_pywsman):
        mock_pywsman_client = mock_pywsman.Client.return_value
        mock_pywsman_client.invoke.return_value = (
            test_utils.mock_wsman_root(
                wsman_mock_raid.Invocations[
                    resource_uris.DCIM_RAIDService][
                        'DeletePendingConfiguration']['error']))

        self.assertRaises(exception.DracOperationFailed,
                          drac_raid.delete_pending_config, self.node,
                          raid_controller='controller')

    def test_delete_pending_config_missing_controller(self):
        self.assertRaises(exception.InvalidParameterValue,
                          drac_raid.delete_pending_config, self.node)

    @mock.patch.object(drac_client, 'get_wsman_client')
    def test_delete_pending_config_calling_client_with_correct_params(
            self, mock_get_client):
        expected_selectors = {'CreationClassName': 'DCIM_RAIDService',
                              'SystemName': 'DCIM:ComputerSystem',
                              'Name': 'DCIM:RAIDService',
                              'SystemCreationClassName': 'DCIM_ComputerSystem'}
        expected_properties = {'Target': 'controller'}
        mock_drac_client = mock_get_client.return_value

        drac_raid.delete_pending_config(self.node,
                                            raid_controller='controller')

        mock_drac_client.wsman_invoke.assert_called_once_with(
            resource_uris.DCIM_RAIDService, 'DeletePendingConfiguration',
            expected_selectors, expected_properties)
