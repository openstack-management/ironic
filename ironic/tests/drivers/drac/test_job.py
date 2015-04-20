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
Test class for DRAC job interface
"""
import mock

from ironic.common import exception
from ironic.drivers.modules.drac import client as drac_client
from ironic.drivers.modules.drac import job as drac_job
from ironic.drivers.modules.drac import resource_uris
from ironic.tests.conductor import utils as mgr_utils
from ironic.tests.db import base as db_base
from ironic.tests.db import utils as db_utils
from ironic.tests.drivers.drac import utils as test_utils
from ironic.tests.drivers.drac import wsman_mock_job
from ironic.tests.objects import utils as obj_utils

INFO_DICT = db_utils.get_test_drac_info()


@mock.patch.object(drac_client, 'pywsman')
class DracJobTestCase(db_base.DbTestCase):

    def setUp(self):
        super(DracJobTestCase, self).setUp()
        mgr_utils.mock_the_extension_manager(driver='fake_drac')
        self.node = obj_utils.create_test_node(self.context,
                                               driver='fake_drac',
                                               driver_info=INFO_DICT)

    def test_get_job(self, mock_pywsman):
        expected_job = {
            'id': 'JID_205731134272',
            'message': 'Job completed successfully.',
            'percent_complete': '100',
            'start_time': 'TIME_NOW',
            'state': 'Completed',
            'until_time': 'TIME_NA'
        }
        mock_pywsman_client = mock_pywsman.Client.return_value
        mock_pywsman_client.enumerate.return_value = (
            test_utils.mock_wsman_root(
                wsman_mock_job.Enumerations[
                    resource_uris.DCIM_LifecycleJob]['completed']))

        job = drac_job.get_job(self.node, job_id='JID_205731134272')

        mock_pywsman_client.enumerate.assert_called_once_with(mock.ANY,
            mock.ANY, resource_uris.DCIM_LifecycleJob)
        self.assertEqual(expected_job, job)

    def test_get_job_not_found(self, mock_pywsman):
        mock_pywsman_client = mock_pywsman.Client.return_value
        mock_pywsman_client.enumerate.return_value = (
            test_utils.mock_wsman_root(
                wsman_mock_job.Enumerations[
                    resource_uris.DCIM_LifecycleJob]['not_found']))

        self.assertRaises(exception.DracLifecycleJobNotFound,
                          drac_job.get_job, self.node,
                          job_id='does not exist')
