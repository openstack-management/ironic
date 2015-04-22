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
DRAC VendorPassthru Driver
"""

from oslo.utils import excutils
from oslo.utils import importutils

from ironic.common import exception
from ironic.common.i18n import _LE
from ironic.conductor import task_manager
from ironic.drivers import base
from ironic.drivers.modules.drac import bios
from ironic.drivers.modules.drac import common as drac_common
from ironic.drivers.modules.drac import job as drac_job
from ironic.drivers.modules.drac import raid as drac_raid
from ironic.openstack.common import log as logging

pywsman = importutils.try_import('pywsman')

LOG = logging.getLogger(__name__)

REQUIRED_PROPERTIES = {}
COMMON_PROPERTIES = REQUIRED_PROPERTIES


class DracVendorPassthru(base.VendorInterface):
    """Interface for DRAC specific methods."""

    def get_properties(self):
        return COMMON_PROPERTIES

    def validate(self, task, **kwargs):
        return drac_common.parse_driver_info(task.node)

    @base.passthru(['GET'], async=False)
    def get_bios_config(self, task, **kwargs):
        return bios.get_config(task.node)

    @base.passthru(['POST'], async=False)
    def set_bios_config(self, task, **kwargs):
        reboot_required = bios.set_config(task, **kwargs)

        return {'commit_needed': reboot_required,
                'reboot_needed': reboot_required}

    @base.passthru(['POST'], async=False)
    def commit_bios_config(self, task, **kwargs):
        return {'committing': bios.commit_config(task, **kwargs)}

    @base.passthru(['DELETE'], async=False)
    def abandon_bios_config(self, task, **kwargs):
        return {'abandoned': bios.abandon_config(task)}

    @base.passthru(['GET'], method='list_raid_controllers', async=False)
    @task_manager.require_exclusive_lock
    def list_raid_controllers(self, task, **kwargs):
        return {'raid_controllers': drac_raid.list_raid_controllers(task.node)}

    @base.passthru(['GET'], method='list_physical_disks', async=False)
    @task_manager.require_exclusive_lock
    def list_physical_disks(self, task, **kwargs):
        return {'physical_disks': drac_raid.list_physical_disks(task.node)}

    @base.passthru(['GET'], method='list_virtual_disks', async=False)
    @task_manager.require_exclusive_lock
    def list_virtual_disks(self, task, **kwargs):
        return {'virtual_disks': drac_raid.list_virtual_disks(task.node)}

    @base.passthru(['POST'], method='create_virtual_disk', async=False)
    @task_manager.require_exclusive_lock
    def create_virtual_disk(self, task, **kwargs):
        return drac_raid.create_virtual_disk(task.node, **kwargs)

    @base.passthru(['POST'], method='delete_virtual_disk', async=False)
    @task_manager.require_exclusive_lock
    def delete_virtual_disk(self, task, **kwargs):
        return drac_raid.delete_virtual_disk(task.node, **kwargs)

    @base.passthru(['POST'], method='apply_pending_raid_config', async=False)
    @task_manager.require_exclusive_lock
    def apply_pending_raid_config(self, task, **kwargs):
        return {'job_id': drac_raid.apply_pending_config(task.node,
                                                              **kwargs)}

    @base.passthru(['POST'], method='delete_pending_raid_config', async=False)
    @task_manager.require_exclusive_lock
    def delete_pending_raid_config(self, task, **kwargs):
        return drac_raid.delete_pending_config(task.node, **kwargs)

    @base.passthru(['POST'], method='get_job', async=False)
    @task_manager.require_exclusive_lock
    def get_job(self, task, **kwargs):
        return {'job': drac_job.get_job(task.node, **kwargs)}

    @base.passthru(['GET'], method='list_unfinished_jobs', async=False)
    @task_manager.require_exclusive_lock
    def list_unfinished_jobs(self, task, **kwargs):
        return {'unfinished_jobs': drac_job.list_unfinished_jobs(task.node,
                                                                 **kwargs)}

    @base.passthru(['POST'], method='create_raid_configuration', async=False)
    @task_manager.require_exclusive_lock
    def create_raid_configuration(self, task, **kwargs):
        try:
            drac_raid.create_configuration(task.node, **kwargs)
        except exception.DracRequestFailed as exc:
            with excutils.save_and_reraise_exception():
                node = task.node
                LOG.error(_LE('DRAC driver failed to create RAID '
                              'configuration on node %(node_uuid)s. '
                              'Reason: %(error)s.'),
                          {'node_uuid': node.uuid, 'error': exc})
                node.maintenance = True
                node.last_error = exc
                node.save()
