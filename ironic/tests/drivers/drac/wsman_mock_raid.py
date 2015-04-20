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
WSMan XML mocks for DRAC RAID interface
"""

from ironic.drivers.modules.drac import resource_uris
from ironic.tests.drivers.drac import utils as test_utils

Enumerations = {
    resource_uris.DCIM_ControllerView: {
        'ok': test_utils.load_wsman_xml('controller_view-enum-ok')
    },
    resource_uris.DCIM_VirtualDiskView: {
        'ok': test_utils.load_wsman_xml('virtual_disk_view-enum-ok')
    },
    resource_uris.DCIM_PhysicalDiskView: {
        'ok': test_utils.load_wsman_xml('physical_disk_view-enum-ok')
    }
}

Invocations = {
    resource_uris.DCIM_RAIDService: {
        'CreateVirtualDisk': {
            'ok': test_utils.load_wsman_xml(
                            'raid_service-invoke-create_virtual_disk-ok'),
            'error': test_utils.load_wsman_xml(
                            'raid_service-invoke-create_virtual_disk-error')
        },
        'DeleteVirtualDisk': {
            'ok': test_utils.load_wsman_xml(
                            'raid_service-invoke-delete_virtual_disk-ok'),
            'error': test_utils.load_wsman_xml(
                            'raid_service-invoke-delete_virtual_disk-error'),
        },
        'CreateTargetedConfigJob': {
            'ok': test_utils.load_wsman_xml(
                            'raid_service-invoke-create_targeted_config_job-'
                            'ok'),
            'error': test_utils.load_wsman_xml(
                            'raid_service-invoke-create_targeted_config_job-'
                            'error'),
        },
        'DeletePendingConfiguration': {
            'ok': test_utils.load_wsman_xml(
                            'raid_service-invoke-delete_pending_configuration-'
                            'ok'),
            'error': test_utils.load_wsman_xml(
                            'raid_service-invoke-delete_pending_configuration-'
                            'error')
        },
    }
}
