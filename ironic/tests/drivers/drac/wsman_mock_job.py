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
WSMan XML mocks for DRAC Lifecycle job interface
"""

from ironic.drivers.modules.drac import resource_uris
from ironic.tests.drivers.drac import utils as test_utils

Enumerations = {
    resource_uris.DCIM_LifecycleJob: {
        'completed': test_utils.load_wsman_xml('lifecycle_job-enum-completed'),
        'failed': test_utils.load_wsman_xml('lifecycle_job-enum-failed'),
        'running': test_utils.load_wsman_xml('lifecycle_job-enum-running'),
        'not_found': test_utils.load_wsman_xml('lifecycle_job-enum-not_found')
    }
}
