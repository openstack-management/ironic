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


class DracCreateRaidConfigurationTestCase(db_base.DbTestCase):

    def setUp(self):
        super(DracCreateRaidConfigurationTestCase, self).setUp()
        mgr_utils.mock_the_extension_manager(driver='fake_drac')
        self.node = obj_utils.create_test_node(self.context,
                                               driver='fake_drac',
                                               driver_info=INFO_DICT)
        self.root_logical_disk = {
            'controller': 'RAID.Integrated.1-1',
            'size_gb': 50,
            'raid_level': '1',
            'number_of_physical_disks': 2,
            'disk_type': 'hdd',
            'interface_type': 'sas',
            'volume_name': 'root_volume',
            'is_root_volume': True
        }
        self.nonroot_logical_disks = [
            {'controller': 'RAID.Integrated.1-1',
             'size_gb': 100,
             'number_of_physical_disks': 3,
             'raid_level': '5',
             'disk_type': 'hdd',
             'interface_type': 'sas',
             'volume_name': 'data_volume1'},
            {'controller': 'RAID.Integrated.1-1',
             'size_gb': 100,
             'number_of_physical_disks': 3,
             'raid_level': '5',
             'disk_type': 'hdd',
             'interface_type': 'sas',
             'volume_name': 'data_volume2'}
        ]
        self.logical_disks = ([self.root_logical_disk] +
                               self.nonroot_logical_disks)
        self.target_raid_configuration = {'logical_disks': self.logical_disks}
        self.node.extra['target_raid_configuration'] = (
                                                self.target_raid_configuration)
        self.physical_disk = {
            'controller': 'RAID.Integrated.1-1',
            'id': 'Disk.Bay.0:Enclosure.Internal.0-1:RAID.Integrated.1-1',
            'disk_type': 'hdd',
            'interface_type': 'sas',
            'size_gb': 500,
            'free_size_gb': 500,
            'vendor': 'vendor',
            'model': 'model',
            'serial_number': 'serial',
            'firmware_version': '42',
            'state': 'ok',
            'raid_state': 'ready'
        }

        self.physical_disks = []
        for i in range(8):
            disk = self.physical_disk.copy()
            disk['id'] = (
                'Disk.Bay.%s:Enclosure.Internal.0-1:RAID.Integrated.1-1' % i)
            disk['serial_number'] = 'serial%s' % i
            self.physical_disks.append(disk)

    def test__filter_logical_disks_root_only(self):
        logical_disks = drac_raid._filter_logical_disks(
                self.target_raid_configuration['logical_disks'], True, False)

        self.assertEqual(1, len(logical_disks))
        self.assertEqual('root_volume', logical_disks[0]['volume_name'])

    def test__filter_logical_disks_nonroot_only(self):
        logical_disks = drac_raid._filter_logical_disks(
            self.target_raid_configuration['logical_disks'], False, True)

        self.assertEqual(2, len(logical_disks))
        self.assertEqual('data_volume1', logical_disks[0]['volume_name'])
        self.assertEqual('data_volume2', logical_disks[1]['volume_name'])

    def test__filter_logical_disks_excelude_all(self):
        logical_disks = drac_raid._filter_logical_disks(
            self.target_raid_configuration['logical_disks'], False, False)

        self.assertEqual(0, len(logical_disks))

    def test__filter_disks_by_availability(self):
        for i in range(7):
            self.physical_disks[i]['raid_state'] = 'degraded'

        filtered_physical_disks = drac_raid._filter_physical_disks(
                                self.physical_disks, self.root_logical_disk)

        self.assertEqual(1, len(filtered_physical_disks))
        self.assertEqual(self.physical_disks[7]['serial_number'],
                         filtered_physical_disks[0]['serial_number'])

    def test__filter_disks_by_controller(self):
        for i in range(7):
            self.physical_disks[i]['controller'] = 'not the one you need'

        filtered_physical_disks = drac_raid._filter_physical_disks(
                                self.physical_disks, self.root_logical_disk)

        self.assertEqual(1, len(filtered_physical_disks))
        self.assertEqual(self.physical_disks[7]['serial_number'],
                         filtered_physical_disks[0]['serial_number'])

    def test__filter_disks_by_disk_type(self):
        for i in range(7):
            self.physical_disks[i]['interface_type'] = 'not the one you need'

        filtered_physical_disks = drac_raid._filter_physical_disks(
                                self.physical_disks, self.root_logical_disk)

        self.assertEqual(1, len(filtered_physical_disks))
        self.assertEqual(self.physical_disks[7]['serial_number'],
                         filtered_physical_disks[0]['serial_number'])

    def test__filter_disks_by_interface_type(self):
        for i in range(7):
            self.physical_disks[i]['disk_type'] = 'not the one you need'

        filtered_physical_disks = drac_raid._filter_physical_disks(
                                self.physical_disks, self.root_logical_disk)

        self.assertEqual(1, len(filtered_physical_disks))
        self.assertEqual(self.physical_disks[7]['serial_number'],
                         filtered_physical_disks[0]['serial_number'])

    def test__match_disks_valid_config(self):
        drac_raid._match_physical_disks(self.logical_disks,
                                        self.physical_disks)

        for disk in self.logical_disks:
            self.assertIn('physical_disks', disk)
            self.assertEqual(disk['number_of_physical_disks'],
                             len(disk['physical_disks']))

    def test__match_disks_no_valid_config(self):
        self.physical_disks.pop()

        self.assertRaises(exception.DracInvalidRaidConfiguration,
                          drac_raid._match_physical_disks, self.logical_disks,
                          self.physical_disks)

    def test__match_disks_with_predefined_physical_disks(self):
        predefined_match = [
            'Disk.Bay.5:Enclosure.Internal.0-1:RAID.Integrated.1-1',
            'Disk.Bay.6:Enclosure.Internal.0-1:RAID.Integrated.1-1'
        ]
        self.root_logical_disk['physical_disks'] = predefined_match
        self.root_logical_disk.pop('number_of_physical_disks')
        self.root_logical_disk.pop('disk_type')
        self.root_logical_disk.pop('interface_type')

        drac_raid._match_physical_disks(self.logical_disks,
                                        self.physical_disks)

        for disk in self.logical_disks:
            self.assertIn('physical_disks', disk)

            if disk.get('is_root_volume'):
                self.assertEqual(predefined_match, disk['physical_disks'])
            else:
                self.assertEqual(disk['number_of_physical_disks'],
                                 len(disk['physical_disks']))

    def test__match_disks_no_valid_config_with_predefined_physical_disks(self):
        self.root_logical_disk['physical_disks'] = [
            'Disk.Bay.0:Enclosure.Internal.0-1:RAID.Integrated.1-1',
            'Disk.Bay.1:Enclosure.Internal.0-1:RAID.Integrated.1-1',
            'Disk.Bay.2:Enclosure.Internal.0-1:RAID.Integrated.1-1'
        ]

        self.assertRaises(exception.DracInvalidRaidConfiguration,
                          drac_raid._match_physical_disks, self.logical_disks,
                          self.physical_disks)

    def test__add_missing_options(self):
        logical_disk = self.logical_disks[0]
        logical_disk['physical_disks'] = self.physical_disks[:2]
        self.assertNotIn('span_depth', logical_disk)
        self.assertNotIn('span_length', logical_disk)

        drac_raid._add_missing_options([logical_disk])
        self.assertEqual(1, logical_disk['span_depth'])
        self.assertEqual(len(logical_disk['physical_disks']),
                         logical_disk['span_length'])

    def test__calculate_spans_for_2_disk_and_raid_level_1(self):
        raid_level = '1'
        disks_count = 2

        span_depth, span_length = drac_raid._calculate_spans(raid_level,
                                                             disks_count)
        self.assertEqual(2, span_depth)
        self.assertEqual(1, span_length)

    def test__calculate_spans_for_7_disk_and_raid_level_50(self):
        raid_level = '5+0'
        disks_count = 7

        span_depth, span_length = drac_raid._calculate_spans(raid_level,
                                                             disks_count)
        self.assertEqual(6, span_depth)
        self.assertEqual(2, span_length)

    def test__calculate_spans_for_7_disk_and_raid_level_10(self):
        raid_level = '1+0'
        disks_count = 7

        span_depth, span_length = drac_raid._calculate_spans(raid_level,
                                                             disks_count)
        self.assertEqual(6, span_depth)
        self.assertEqual(3, span_length)

    def test__calculate_spans_for_invalid_raid_level(self):
        raid_level = 'foo'
        disks_count = 7

        self.assertRaises(exception.DracInvalidRaidConfiguration,
                          drac_raid._calculate_spans, raid_level, disks_count)

    @mock.patch.object(drac_raid, 'list_physical_disks', autospec=True)
    @mock.patch.object(drac_client, 'get_wsman_client', autospec=True)
    def test_create_configuration(self, mock_client, mock_list_physical_disks):
        mock_list_physical_disks.return_value = self.physical_disks
        create_disk_selectors = {
            'CreationClassName': 'DCIM_RAIDService',
            'SystemName': 'DCIM:ComputerSystem',
            'Name': 'DCIM:RAIDService',
            'SystemCreationClassName': 'DCIM_ComputerSystem'
        }
        create_disk_properties = {
            'Target': 'RAID.Integrated.1-1',
            'PDArray': [
                'Disk.Bay.0:Enclosure.Internal.0-1:RAID.Integrated.1-1',
                'Disk.Bay.1:Enclosure.Internal.0-1:RAID.Integrated.1-1'
            ],
            'VDPropNameArray': ['Size', 'RAIDLevel', mock.ANY, mock.ANY],
            'VDPropValueArray': ['51200', '4', mock.ANY, mock.ANY]
        }
        apply_config_selectors = {
            'CreationClassName': 'DCIM_RAIDService',
            'SystemName': 'DCIM:ComputerSystem',
            'Name': 'DCIM:RAIDService',
            'SystemCreationClassName': 'DCIM_ComputerSystem'
        }
        apply_config_properties = {'ScheduledStartTime': 'TIME_NOW',
                                   'Target': 'RAID.Integrated.1-1'}
        apply_config_return_value = drac_client.RET_CREATED
        mock_drac_client = mock_client.return_value
        config = {'wsman_invoke.return_value.find.return_value.text': 42}
        mock_drac_client.configure_mock(**config)
        self.node.save = mock.Mock(name='save')

        drac_raid.create_configuration(self.node, create_root_volume=True,
                                                  create_nonroot_volumes=False)

        mock_drac_client.wsman_invoke.assert_has_calls([
            mock.call(resource_uris.DCIM_RAIDService, 'CreateVirtualDisk',
                create_disk_selectors, create_disk_properties),
            mock.call(resource_uris.DCIM_RAIDService,
                'CreateTargetedConfigJob', apply_config_selectors,
                apply_config_properties,
                expected_return=apply_config_return_value)
        ])
        self.assertEqual([42],
                         self.node.driver_internal_info['raid_config_job_ids'])
        self.node.save.assert_called_once_with()

    @mock.patch.object(drac_raid, 'list_physical_disks', autospec=True)
    @mock.patch.object(drac_client, 'get_wsman_client', autospec=True)
    def test_create_configuration_with_multiple_controllers(self, mock_client,
            mock_list_physical_disks):
        self.root_logical_disk['controller'] = 'controller-2'
        self.physical_disks[0]['controller'] = 'controller-2'
        self.physical_disks[1]['controller'] = 'controller-2'
        mock_list_physical_disks.return_value = self.physical_disks
        apply_config_properties_controller1 = {
            'ScheduledStartTime': 'TIME_NOW',
            'Target': 'RAID.Integrated.1-1',
        }
        apply_config_properties_controller2 = {
            'ScheduledStartTime': 'TIME_NOW',
            'Target': 'controller-2',
        }
        apply_config_return_value = drac_client.RET_CREATED
        mock_drac_client = mock_client.return_value
        mock_job_id1 = mock.Mock()
        mock_job_id1.text = 42
        mock_job_id2 = mock.Mock()
        mock_job_id2.text = 3
        config = {'wsman_invoke.return_value.find.side_effect': [mock_job_id1,
                                                                 mock_job_id2]}
        mock_drac_client.configure_mock(**config)

        drac_raid.create_configuration(self.node, create_root_volume=True,
                                                  create_nonroot_volumes=True)

        mock_drac_client.wsman_invoke.assert_has_calls([
            mock.call(resource_uris.DCIM_RAIDService,
                'CreateTargetedConfigJob', mock.ANY,
                apply_config_properties_controller1,
                expected_return=apply_config_return_value),
            mock.call(resource_uris.DCIM_RAIDService,
                'CreateTargetedConfigJob', mock.ANY,
                apply_config_properties_controller2,
                expected_return=apply_config_return_value)
        ], any_order=True)
        self.assertEqual([42, 3],
                         self.node.driver_internal_info['raid_config_job_ids'])

    @mock.patch.object(drac_raid, 'list_physical_disks', autospec=True)
    @mock.patch.object(drac_client, 'get_wsman_client', autospec=True)
    def test_create_configuration_with_reboot(self, mock_client,
                                              mock_list_physical_disks):
        mock_list_physical_disks.return_value = self.physical_disks
        create_disk_selectors = {
            'CreationClassName': 'DCIM_RAIDService',
            'SystemName': 'DCIM:ComputerSystem',
            'Name': 'DCIM:RAIDService',
            'SystemCreationClassName': 'DCIM_ComputerSystem'
        }
        create_disk_properties = {
            'Target': 'RAID.Integrated.1-1',
            'PDArray': [
                'Disk.Bay.0:Enclosure.Internal.0-1:RAID.Integrated.1-1',
                'Disk.Bay.1:Enclosure.Internal.0-1:RAID.Integrated.1-1'
            ],
            'VDPropNameArray': ['Size', 'RAIDLevel', mock.ANY, mock.ANY],
            'VDPropValueArray': ['51200', '4', mock.ANY, mock.ANY]
        }
        apply_config_selectors = {
            'CreationClassName': 'DCIM_RAIDService',
            'SystemName': 'DCIM:ComputerSystem',
            'Name': 'DCIM:RAIDService',
            'SystemCreationClassName': 'DCIM_ComputerSystem'
        }
        apply_config_properties = {'ScheduledStartTime': 'TIME_NOW',
                                   'Target': 'RAID.Integrated.1-1',
                                   'RebootJobType': '3'}
        apply_config_return_value = drac_client.RET_CREATED
        mock_drac_client = mock_client.return_value
        config = {'wsman_invoke.return_value.find.return_value.text': 42}
        mock_drac_client.configure_mock(**config)
        self.node.save = mock.Mock(name='save')

        drac_raid.create_configuration(self.node, create_root_volume=True,
                                                  create_nonroot_volumes=False,
                                                  reboot=True)

        mock_drac_client.wsman_invoke.assert_has_calls([
            mock.call(resource_uris.DCIM_RAIDService, 'CreateVirtualDisk',
                create_disk_selectors, create_disk_properties),
            mock.call(resource_uris.DCIM_RAIDService,
                'CreateTargetedConfigJob', apply_config_selectors,
                apply_config_properties,
                expected_return=apply_config_return_value)
        ])
        self.assertEqual([42],
                         self.node.driver_internal_info['raid_config_job_ids'])
        self.node.save.assert_called_once_with()