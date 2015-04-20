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
DRAC Lifecycle job specific methods
"""

from oslo.utils import excutils

from ironic.common import exception
from ironic.common.i18n import _, _LE
from ironic.drivers.modules.drac import client as drac_client
from ironic.drivers.modules.drac import common as drac_common
from ironic.drivers.modules.drac import resource_uris
from ironic.openstack.common import log as logging

LOG = logging.getLogger(__name__)


def _get_job_attr(job_xml, attr_name):
    return drac_common.get_xml_attr(job_xml, attr_name,
                                    resource_uris.DCIM_LifecycleJob)


def get_job(node, **kwargs):
    """Get a details of a Lifecycle job of the node.

    :param node: an ironic node object.
    :param kwargs: a dictionary holding the Lifecycle job attributes:
        :job_id:
            ID of the Lifecycle job. (required)

    :returns: a dictionary containing:
        :id:
            ID of the Lifecycle job.
        :start_time:
            Timestamp to start processing the job.
        :until_time:
            Time interval after a job has started that it is permitted to run.
        :message:
            Detailed error information if error happened.
        :state:
            Status of the Lifecycle job.
        :percent_complete:
            Percentage of job completion.
    """
    job_id = None
    error_msgs = []

    # job_id validation
    try:
        job_id = str(kwargs['job_id'])
    except KeyError:
        error_msgs.append(_("'job_id' is not supplied."))
    except UnicodeEncodeError:
        error_msgs.append(_("'job_id' contains non-ASCII symbol."))

    if error_msgs:
        msg = (_('The following errors were encountered while parsing '
                 'the provided parameters:\n%s') % '\n'.join(error_msgs))
        raise exception.InvalidParameterValue(msg)

    client = drac_client.get_wsman_client(node)

    filter_query = ('select * from DCIM_LifecycleJob '
                    'where InstanceID="%s"' % job_id)
    try:
        doc = client.wsman_enumerate(resource_uris.DCIM_LifecycleJob,
                                     filter_query=filter_query)
    except exception.DracClientError as exc:
        with excutils.save_and_reraise_exception():
            LOG.error(_LE('DRAC driver failed to get the list of Lifecycle '
                          'job %(job_id)s for node %(node_uuid)s. '
                          'Reason: %(error)s.'),
                      {'job_id': job_id, 'node_uuid': node.uuid, 'error': exc})

    drac_job = drac_common.find_xml(doc, 'DCIM_LifecycleJob',
                                         resource_uris.DCIM_LifecycleJob)

    if drac_job is None:
        raise exception.DracLifecycleJobNotFound(job_id=job_id)
    else:
        return {'id': _get_job_attr(drac_job, 'InstanceID'),
                'start_time': _get_job_attr(drac_job, 'JobStartTime'),
                'until_time': _get_job_attr(drac_job, 'JobUntilTime'),
                'message': _get_job_attr(drac_job, 'Message'),
                'state': _get_job_attr(drac_job, 'JobStatus'),
                'percent_complete': _get_job_attr(drac_job, 'PercentComplete')}


def list_unfinished_jobs(node, **kwargs):
    """List unfinished config jobs of the node.

    :param node: an ironic node object.

    :returns: a dictionary containing:
        :id:
            ID of the lifecycle job.
        :name:
            Name of the lifecycle job.
        :state:
            Status of the lifecycle job.
        :percent_complete:
            Percentage of job completion.
    """

    client = drac_client.get_wsman_client(node)
    filter_query = ('select * from DCIM_LifecycleJob '
                    'where Name != "CLEARALL" and '
                          'JobStatus != "Reboot Completed" and '
                          'JobStatus != "Completed" and '
                          'JobStatus != "Completed with Errors" and '
                          'JobStatus != "Failed"')

    try:
        doc = client.wsman_enumerate(resource_uris.DCIM_LifecycleJob,
                                     filter_query=filter_query)
    except exception.DracClientError as exc:
        with excutils.save_and_reraise_exception():
            LOG.error(_LE('DRAC driver failed to list unfinished '
                          'configuration jobs for node %(node_uuid)s. '
                          'Reason: %(error)s.'),
                      {'node_uuid': node.uuid, 'error': exc})

    drac_jobs = drac_common.find_xml(doc, 'DCIM_LifecycleJob',
                                     resource_uris.DCIM_LifecycleJob,
                                     find_all=True)

    def _parse_drac_job(job):
        instance_id = _get_job_attr(job, 'InstanceID')
        name = _get_job_attr(job, 'Name')
        percent_complete = _get_job_attr(job, 'PercentComplete')

        return {'id': instance_id,
                'name': name,
                'percent_complete': percent_complete}

    return drac_common.parse_enumeration_list(drac_jobs,
                                              _parse_drac_job)