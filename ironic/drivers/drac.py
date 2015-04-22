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
DRAC Driver for remote system management using Dell Remote Access Card.
"""

from oslo_config import cfg
from oslo_utils import importutils

from ironic.common import exception
from ironic.common.i18n import _, _LE, _LI
from ironic.conductor import task_manager
from ironic.drivers import base
from ironic.drivers.modules import discoverd
from ironic.drivers.modules.drac import job
from ironic.drivers.modules.drac import management
from ironic.drivers.modules.drac import power
from ironic.drivers.modules.drac import raid
from ironic.drivers.modules.drac import vendor_passthru
from ironic.drivers.modules import pxe
from ironic.drivers import utils
from ironic.openstack.common import log as logging


opts = [
    cfg.IntOpt('query_raid_config_job_status_interval',
               default=120,
               help='After Ironic has created the RAID config job on DRAC, '
                    'it continues to check for status update on the config '
                    'job to determine whether the RAID configuration was '
                    'successfully finished or not at this interval, in '
                    'seconds')
]

CONF = cfg.CONF
opt_group = cfg.OptGroup(name='drac',
                         title='Options for the DRAC driver')
CONF.register_group(opt_group)
CONF.register_opts(opts, opt_group)

LOG = logging.getLogger(__name__)


class PXEDracDriver(base.BaseDriver):
    """Drac driver using PXE for deploy."""

    def __init__(self):
        if not importutils.try_import('pywsman'):
            raise exception.DriverLoadError(
                    driver=self.__class__.__name__,
                    reason=_('Unable to import pywsman library'))

        self.power = power.DracPower()
        self.deploy = pxe.PXEDeploy()
        self.management = management.DracManagement()
        self.inspect = discoverd.DiscoverdInspect.create_if_enabled(
            'PXEDracDriver')
        self.pxe_vendor = pxe.VendorPassthru()
        self.drac_vendor = vendor_passthru.DracVendorPassthru()
        self.mapping = {'pass_deploy_info': self.pxe_vendor,
                        'heartbeat': self.pxe_vendor,
                        'get_bios_config': self.drac_vendor,
                        'set_bios_config': self.drac_vendor,
                        'commit_bios_config': self.drac_vendor,
                        'abandon_bios_config': self.drac_vendor,
                        'list_raid_controllers': self.drac_vendor,
                        'list_physical_disks': self.drac_vendor,
                        'list_virtual_disks': self.drac_vendor,
                        'create_virtual_disk': self.drac_vendor,
                        'delete_virtual_disk': self.drac_vendor,
                        'apply_pending_raid_config': self.drac_vendor,
                        'delete_pending_raid_config': self.drac_vendor,
                        'create_raid_configuration': self.drac_vendor,
                        'get_job': self.drac_vendor,
                        'list_unfinished_jobs': self.drac_vendor}
        self.vendor = utils.MixinVendorInterface(self.mapping)

    @base.driver_periodic_task(
        spacing=CONF.drac.query_raid_config_job_status_interval,
        parallel=False)
    def _query_raid_config_job_status(self, manager, context):
        """Periodic task to check for update on running RAID config jobs."""

        filters = {'reserved': False, 'maintenance': False}
        fields = ['driver_internal_info']

        node_list = manager.iter_nodes(fields=fields, filters=filters)
        for (node_uuid, driver, driver_internal_info) in node_list:
            if 'drac' not in driver:
                continue

            if ('raid_config_job_ids' not in driver_internal_info or
                not driver_internal_info['raid_config_job_ids']):
                continue

            try:
                with task_manager.acquire(context, node_uuid) as task:
                    node = task.node

                    for config_job_id in node.driver_internal_info[
                                                        'raid_config_job_ids']:
                        config_job = job.get_job(node, job_id=config_job_id)

                        if config_job['state'] == 'Completed':
                            # TODO(ifarkas): remove this once the logic is
                            #                moved the generic RAID interface
                            properties = node.properties
                            properties['logical_disks'] = (
                                                raid.list_virtual_disks(node))
                            node.properties = properties

                            driver_internal_info = node.driver_internal_info
                            driver_internal_info['raid_config_job_ids'].remove(
                                config_job_id)
                            node.driver_internal_info = driver_internal_info

                            node.save()

                        elif config_job['state'] == 'Failed':
                            node.maintenance = True
                            node.last_error = config_job['message']
                            node.save()

                            LOG.error(
                                _LE("RAID configuration job failed for node "
                                    "%(node)s. Message: '%(message)s'."
                                    "Setting the node to maintenance mode."),
                                {'node': node_uuid,
                                 'message': config_job['message']})

            except exception.NodeNotFound:
                LOG.info(_LI("During query_raid_config_job_status, node "
                             "%(node)s was not found and presumed deleted by "
                             "another process."), {'node': node_uuid})
            except exception.NodeLocked:
                LOG.info(_LI("During query_raid_config_job_status, node "
                             "%(node)s was already locked by another process. "
                             "Skip."), {'node': node_uuid})
