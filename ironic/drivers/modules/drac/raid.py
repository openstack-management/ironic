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
DRAC RAID specific methods
"""

from oslo.utils import excutils

from ironic.common import exception
from ironic.common.i18n import _, _LE, _LI
from ironic.drivers.modules.drac import client as drac_client
from ironic.drivers.modules.drac import common as drac_common
from ironic.drivers.modules.drac import resource_uris
from ironic.openstack.common import log as logging

LOG = logging.getLogger(__name__)

OPTIONAL_VIRTUAL_DISK_PROPS = {
    'disk_name': 'VirtualDiskName',
    'span_depth': 'SpanDepth',
    'span_length': 'SpanLength'
}

RAID_LEVELS = {
    'non-raid': '1',
    '0': '2',
    '1': '4',
    '5': '64',
    '6': '128',
    '1+0': '2048',
    '5+0': '8192',
    '6+0': '16384',
}

REVERSE_RAID_LEVELS = dict((v, k) for (k, v) in RAID_LEVELS.items())

PHYISICAL_DISK_MEDIA_TYPE = {
    '0': 'hdd',
    '1': 'ssd'
}

PHYISICAL_DISK_BUS_PROTOCOL = {
    '0': 'unknown',
    '1': 'scsi',
    '2': 'pata',
    '3': 'fibre',
    '4': 'usb',
    '5': 'sata',
    '6': 'sas'
}

DISK_PRIMARY_STATUS = {
    '0': 'unknown',
    '1': 'ok',
    '2': 'degraded',
    '3': 'error'
}

DISK_RAID_STATUS = {
    '0': 'unknown',
    '1': 'ready',
    '2': 'online',
    '3': 'foreign',
    '4': 'offline',
    '5': 'blocked',
    '6': 'failed',
    '7': 'degraded',
    '8': 'non-RAID'
}


def _get_raid_controller_attr(controller_xml, attr_name):
    return drac_common.get_xml_attr(controller_xml, attr_name,
                         resource_uris.DCIM_ControllerView)


def _get_virtual_disk_attr(disk_xml, attr_name):
    return drac_common.get_xml_attr(disk_xml, attr_name,
                         resource_uris.DCIM_VirtualDiskView)


def _get_physical_disk_attr(disk_xml, attr_name):
    return drac_common.get_xml_attr(disk_xml, attr_name,
                         resource_uris.DCIM_PhysicalDiskView)


def list_raid_controllers(node):
    """List the RAID controllers of the node.

    :param node: an ironic node object.
    :returns: a dictionary containing:

        :id:
            FQDD of the RAID controller.
        :model:
            Model name of the RAID controller.
    """

    client = drac_client.get_wsman_client(node)

    try:
        doc = client.wsman_enumerate(resource_uris.DCIM_ControllerView)
    except exception.DracClientError as exc:
        with excutils.save_and_reraise_exception():
            LOG.error(_LE('DRAC driver failed to get the list of RAID '
                          'controllers for node %(node_uuid)s. '
                          'Reason: %(error)s.'),
                      {'node_uuid': node.uuid, 'error': exc})

    drac_controllers = drac_common.find_xml(doc, 'DCIM_ControllerView',
                                            resource_uris.DCIM_ControllerView,
                                            find_all=True)

    def _parse_drac_controller(controller):
        fqdd = _get_raid_controller_attr(controller, 'FQDD')
        model = _get_raid_controller_attr(controller, 'ProductName')

        return {'id': fqdd,
                'model': model}

    return drac_common.parse_enumeration_list(drac_controllers,
                                              _parse_drac_controller)


def list_virtual_disks(node):
    """List the virtual disks of the node.

    :param node: an ironic node object.
    :returns: a dictionary containing:

        :controller:
            FQDD of the RAID controller to which the virtual disk is
            attached.
        :id:
            FQDD of the virtual disk.
        :size_gb:
            Size of the virtual disk in gigabytes.
        :raid_level:
            RAID level of the virtual disk.
        :name:
            Name of the virtual disk.
        :state:
            Status of the physical disk, one of 'unknown', 'ok', 'degraded' or
            'error'.
        :raid_state:
            RAID specific status of the physical disk, one of 'unknown',
            'ready', 'online', 'foreign', 'offline', 'blocked', 'failed' or
            'degraded'.
    """

    client = drac_client.get_wsman_client(node)

    try:
        doc = client.wsman_enumerate(resource_uris.DCIM_VirtualDiskView)
    except exception.DracClientError as exc:
        with excutils.save_and_reraise_exception():
            LOG.error(_LE('DRAC driver failed to get the list of virtual '
                          'disks for node %(node_uuid)s. '
                          'Reason: %(error)s.'),
                      {'node_uuid': node.uuid, 'error': exc})

    drac_disks = drac_common.find_xml(doc, 'DCIM_VirtualDiskView',
                                      resource_uris.DCIM_VirtualDiskView,
                                      find_all=True)

    def _parse_drac_disk(disk):
        fqdd = _get_virtual_disk_attr(disk, 'FQDD')
        controller = fqdd.split(':')[1]
        size_b = int(_get_virtual_disk_attr(disk, 'SizeInBytes'))
        drac_raid_types = _get_virtual_disk_attr(disk, 'RAIDTypes')
        name = _get_virtual_disk_attr(disk, 'Name')
        drac_primary_status = _get_virtual_disk_attr(disk, 'PrimaryStatus')
        drac_raid_status = _get_virtual_disk_attr(disk, 'RAIDStatus')

        return {
            'controller': controller,
            'id': fqdd,
            'size_gb': size_b / 2 ** 30,
            'raid_level': REVERSE_RAID_LEVELS[drac_raid_types],
            'name': name,
            'state': DISK_PRIMARY_STATUS[drac_primary_status],
            'raid_state': DISK_RAID_STATUS[drac_raid_status]
        }

    return drac_common.parse_enumeration_list(drac_disks,
                                              _parse_drac_disk)


def list_physical_disks(node):
    """List the physical disks of the node.

    :param node: an ironic node object.
    :returns: a dictionary containing:

        :controller:
            FQDD of the RAID controller to which the physical disk is
            attached.
        :id:
            FQDD of the physical disk.
        :disk_type:
            Disk type of the physical disk, one of 'hdd' or 'ssd'.
        :interface_type:
            Interface type of the physical disk, one of 'unknown', 'scsi',
            'pata', 'fibre', 'usb', 'sata', or 'sas'.
        :size_gb:
            Size of the physical disk in gigabytes.
        :free_size_gb:
            Free space available on the physical disk in gigabytes.
        :vendor:
            Manufacturer of the physical disk.
        :model:
            Model name of the physical disk.
        :serial_number:
            Serial number of the physical disk.
        :firmware_version:
            Firmware version of the physical disk.
        :state:
            Status of the physical disk, one of 'unknown', 'ok', 'degraded' or
            'error'.
        :raid_state:
            RAID specific status of the physical disk, one of 'unknown',
            'ready', 'online', 'foreign', 'offline', 'blocked', 'failed' or
            'degraded'.
    """

    client = drac_client.get_wsman_client(node)

    try:
        doc = client.wsman_enumerate(resource_uris.DCIM_PhysicalDiskView)
    except exception.DracClientError as exc:
        with excutils.save_and_reraise_exception():
            LOG.error(_LE('DRAC driver failed to get the list of physical '
                          'disks for node %(node_uuid)s. '
                          'Reason: %(error)s.'),
                      {'node_uuid': node.uuid, 'error': exc})

    drac_disks = drac_common.find_xml(doc, 'DCIM_PhysicalDiskView',
                                      resource_uris.DCIM_PhysicalDiskView,
                                      find_all=True)

    def _parse_drac_disk(disk):
        fqdd = _get_physical_disk_attr(disk, 'FQDD')
        controller = fqdd.split(':')[2]
        drac_media_type = _get_physical_disk_attr(disk, 'MediaType')
        drac_bus_protocol = _get_physical_disk_attr(disk, 'BusProtocol')
        size_b = int(_get_physical_disk_attr(disk, 'SizeInBytes'))
        free_size_b = int(_get_physical_disk_attr(disk, 'FreeSizeInBytes'))
        manufacturer = _get_physical_disk_attr(disk, 'Manufacturer')
        model = _get_physical_disk_attr(disk, 'Model')
        serial_number = _get_physical_disk_attr(disk, 'SerialNumber')
        revision = _get_physical_disk_attr(disk, 'Revision')
        drac_primary_status = _get_physical_disk_attr(disk, 'PrimaryStatus')
        drac_raid_status = _get_physical_disk_attr(disk, 'RaidStatus')

        return {
            'controller': controller,
            'id': fqdd,
            'disk_type': PHYISICAL_DISK_MEDIA_TYPE[drac_media_type],
            'interface_type': PHYISICAL_DISK_BUS_PROTOCOL[drac_bus_protocol],
            'size_gb': size_b / 2 ** 30,
            'free_size_gb': free_size_b / 2 ** 30,
            'vendor': manufacturer,
            'model': model,
            'serial_number': serial_number,
            'firmware_version': revision,
            'state': DISK_PRIMARY_STATUS[drac_primary_status],
            'raid_state': DISK_RAID_STATUS[drac_raid_status]
        }

    return drac_common.parse_enumeration_list(drac_disks,
                                              _parse_drac_disk)


def create_virtual_disk(node, **kwargs):
    """Creates a single virtual disk on a RAID controller.

    The created virtual disk will be in pending state. The DRAC card will do
    the actual configuration once the changes are applied on the RAID. This
    can be done by calling the apply_pending_config method.
    :param node: an ironic node object.
    :param kwargs: a dictionary holding the virtual disk attributes:

        :raid_controller:
            FQDDs of the RAID controller. (required)
        :physical_disks:
            FQDDs of the physical disks. (required)
        :raid_level:
            RAID level of the virtual disk. (required)
        :size_mb:
            size of the virtual disk. (required)
        :disk_name:
            name of the virtual disk. (optional)
        :span_depth:
            Number of spans in virtual disk. (optional)
        :span_length:
            Number of disks per span. (optional)
    """

    parameters = {}
    parameters['physical_disks'] = []
    parameters['virtual_disk_prop_names'] = []
    parameters['virtual_disk_prop_values'] = []

    error_msgs = []

    # RAID controller validation
    parameters['raid_controller'] = drac_common.validate_required_string(
                                                    kwargs, 'raid_controller',
                                                    error_msgs)

    # Physical disks validation
    try:
        parameters['physical_disks'] = [str(disk) for disk in
                                         kwargs['physical_disks']]
    except KeyError:
        error_msgs.append(_("'physical_disks' is not supplied."))
    except UnicodeEncodeError:
        error_msgs.append(_("'physical_disks' contains non-ASCII symbol."))

    # size_mb validation
    try:
        parameters['virtual_disk_prop_values'].append(
            str(kwargs['size_mb']))
        parameters['virtual_disk_prop_names'].append('Size')
        int(kwargs['size_mb'])
    except KeyError:
        error_msgs.append(_("'size_mb' is not supplied."))
    except UnicodeEncodeError:
        error_msgs.append(_("'size_mb' contains non-ASCII symbol."))
    except ValueError:
        error_msgs.append(_("'size_mb' is not an integer value."))

    # raid_level validation
    parameters['virtual_disk_prop_values'].append(
        drac_common.validate_required_string(
            kwargs, 'raid_level', error_msgs, value_dict=RAID_LEVELS))
    parameters['virtual_disk_prop_names'].append('RAIDLevel')

    # validating optional params
    for param, prop_name in OPTIONAL_VIRTUAL_DISK_PROPS.items():
        if param not in kwargs:
            continue

        try:
            parameters['virtual_disk_prop_values'].append(
                str(kwargs[param]))
            parameters['virtual_disk_prop_names'].append(prop_name)
        except UnicodeEncodeError:
            error_msgs.append(_("'%s' contains non-ASCII symbol.") % param)

    if error_msgs:
        msg = (_('The following errors were encountered while parsing '
                 'the provided parameters:\n%s') % '\n'.join(error_msgs))
        raise exception.InvalidParameterValue(msg)

    client = drac_client.get_wsman_client(node)

    selectors = {'SystemCreationClassName': 'DCIM_ComputerSystem',
                 'CreationClassName': 'DCIM_RAIDService',
                 'SystemName': 'DCIM:ComputerSystem',
                 'Name': 'DCIM:RAIDService'}

    properties = {'Target': parameters['raid_controller'],
                  'PDArray': parameters['physical_disks'],
                  'VDPropNameArray': parameters['virtual_disk_prop_names'],
                  'VDPropValueArray': parameters['virtual_disk_prop_values']}

    try:
        client.wsman_invoke(resource_uris.DCIM_RAIDService,
                            'CreateVirtualDisk', selectors, properties)
    except exception.DracRequestFailed as exc:
        with excutils.save_and_reraise_exception():
            LOG.error(_LE('DRAC driver failed to create virtual disk for node '
                          '%(node_uuid)s. Reason: %(error)s.'),
                      {'node_uuid': node.uuid,
                       'error': exc})


def delete_virtual_disk(node, **kwargs):
    """Deletes a single virtual disk on a RAID controller.

    The deleted virtual disk will be in pending state. The DRAC card will do
    the actual configuration once the changes are applied on the RAID. This
    can be done by calling the ``apply_pending_config`` method.
    :param node: an ironic node object.
    :param kwargs: a dictionary holding the virtual disk attributes:

        :virtual_disk:
            FQDDs of the virtual disk. (required)
    """

    virtual_disk = None
    error_msgs = []

    # Virtual disks validation
    virtual_disk = drac_common.validate_required_string(kwargs, 'virtual_disk',
                                                        error_msgs)

    if error_msgs:
        msg = (_('The following errors were encountered while parsing '
                 'the provided parameters:\n%s') % '\n'.join(error_msgs))
        raise exception.InvalidParameterValue(msg)

    client = drac_client.get_wsman_client(node)

    selectors = {'SystemCreationClassName': 'DCIM_ComputerSystem',
                 'CreationClassName': 'DCIM_RAIDService',
                 'SystemName': 'DCIM:ComputerSystem',
                 'Name': 'DCIM:RAIDService'}

    properties = {'Target': virtual_disk}

    try:
        client.wsman_invoke(resource_uris.DCIM_RAIDService,
                                   'DeleteVirtualDisk', selectors, properties)
    except exception.DracRequestFailed as exc:
        with excutils.save_and_reraise_exception():
            LOG.error(_LE('DRAC driver failed to delete virtual disk '
                          '%(virtual_disk_fqdd)s for node %(node_uuid)s. '
                          'Reason: %(error)s.'),
                      {'virtual_disk_fqdd': virtual_disk,
                       'node_uuid': node.uuid,
                       'error': exc})


def apply_pending_config(node, **kwargs):
    """Applies all pending changes on a RAID controller.

    :param node: an ironic node object.
    :param kwargs: a dictionary holding the virtual disk attributes:

        :raid_controller:
            FQDDs of the RAID controller. (required)
        :reboot:
            Whether or not DRAC should take care of the required reboot.
    """

    raid_controller = None
    error_msgs = []

    # RAID controller validation
    raid_controller = drac_common.validate_required_string(kwargs,
                                                           'raid_controller',
                                                           error_msgs)

    if error_msgs:
        msg = (_('The following errors were encountered while parsing '
                 'the provided parameters:\n%s') % '\n'.join(error_msgs))
        raise exception.InvalidParameterValue(msg)

    client = drac_client.get_wsman_client(node)

    selectors = {'SystemCreationClassName': 'DCIM_ComputerSystem',
                 'CreationClassName': 'DCIM_RAIDService',
                 'SystemName': 'DCIM:ComputerSystem',
                 'Name': 'DCIM:RAIDService'}

    properties = {'Target': raid_controller,
                  'ScheduledStartTime': 'TIME_NOW'}

    if kwargs.get('reboot'):
        # Graceful Reboot with forced shutdown
        properties['RebootJobType'] = '3'

    try:
        root = client.wsman_invoke(resource_uris.DCIM_RAIDService,
                   'CreateTargetedConfigJob', selectors, properties,
                   expected_return=drac_client.RET_CREATED)
    except exception.DracClientError as exc:
        with excutils.save_and_reraise_exception():
            LOG.error(_LE('DRAC driver failed to apply pending RAID config for'
                          ' controller %(raid_controller_fqdd)s on node '
                          '%(node_uuid)s. Reason: %(error)s.'),
                      {'raid_controller_fqdd': raid_controller,
                       'node_uuid': node.uuid,
                       'error': exc})

    namespace = 'http://schemas.dmtf.org/wbem/wsman/1/wsman.xsd'
    item = 'Selector'
    query = ('.//{%(namespace)s}%(item)s[@%(attribute_name)s='
             '"%(attribute_value)s"]' %
             {'namespace': namespace, 'item': item,
              'attribute_name': 'Name',
              'attribute_value': 'InstanceID'})
    job_id = root.find(query).text
    return job_id


def delete_pending_config(node, **kwargs):
    """Deletes all pending changes on a RAID controller.

    :param node: an ironic node object.
    :param kwargs: a dictionary holding the virtual disk attributes:

        :raid_controller:
            FQDDs of the RAID controller. (required)
    """

    raid_controller = None
    error_msgs = []

    # RAID controller validation
    raid_controller = drac_common.validate_required_string(kwargs,
                                                           'raid_controller',
                                                           error_msgs)

    if error_msgs:
        msg = (_('The following errors were encountered while parsing '
                 'the provided parameters:\n%s') % '\n'.join(error_msgs))
        raise exception.InvalidParameterValue(msg)

    client = drac_client.get_wsman_client(node)

    selectors = {'SystemCreationClassName': 'DCIM_ComputerSystem',
                 'CreationClassName': 'DCIM_RAIDService',
                 'SystemName': 'DCIM:ComputerSystem',
                 'Name': 'DCIM:RAIDService'}

    properties = {'Target': raid_controller}

    try:
        client.wsman_invoke(resource_uris.DCIM_RAIDService,
                                   'DeletePendingConfiguration', selectors,
                                   properties)
    except exception.DracRequestFailed as exc:
        with excutils.save_and_reraise_exception():
            LOG.error(_LE('DRAC driver failed to delete pending RAID config '
                          'for controller %(raid_controller_fqdd)s on node '
                          '%(node_uuid)s. Reason: %(error)s.'),
                      {'raid_controller_fqdd': raid_controller,
                       'node_uuid': node.uuid,
                       'error': exc})


def create_configuration(node, **kwargs):
    """Creates the RAID configuration defined on the node.

    Reads the RAID configuration from
    node.extra['target_raid_configuration'] and creates the logical disks,
    applies the changes on the controller and saves to job id created by DRAC
    in node.extra['raid_config_job_ids'].
    The RAID configuration can be defined in 2 ways: either by defining the IDs
    of the physical disks, or letting the driver assign physical disks to the
    logical disks.
    The target_raid_configuration should use the following format:
        {
            'logical_disks': [
                {'controller': 'RAID.Integrated.1-1',
                 'size_gb': 50,
                 'raid_level': '1',
                 'number_of_physical_disks': 2,
                 'disk_type': 'hdd',
                 'interface_type': 'sas',
                 'volume_name': 'root_volume',
                 'is_root_volume': True},
                {'controller': 'RAID.Integrated.1-1',
                 'size_gb': 100,
                 'physical_disks': [
                     'Disk.Bay.0:Enclosure.Internal.0-1:RAID.Integrated.1-1',
                     'Disk.Bay.1:Enclosure.Internal.0-1:RAID.Integrated.1-1',
                     'Disk.Bay.2:Enclosure.Internal.0-1:RAID.Integrated.1-1']
                 'raid_level': '5',
                 'volume_name': 'data_volume1'}
            ]
        }
    The required attributes of the logical disk in the
    target_raid_configuration dictionary are: controller, size_gb, raid_level
    and either the list of physical_disks or the number_of_physical_disks.
    :param node: an ironic node object.
    :param kwargs: additional kwargs passed to the method:

        :create_root_volume:
            indicates whether the root volume should be created or not.
            (required)
        :create_nonroot_volumes:
            indicates whether the  non-root volumes should be created or not.
            (required)
        :reboot:
            Whether or not DRAC should take care of the required reboot.
    """

    if 'target_raid_configuration' not in node.extra:
        LOG.info(_LI('target_raid_configuration is not defined for node '
                     '%(node_uuid)s '), {'node_uuid': node.uuid})
        return

    create_root_volume = kwargs['create_root_volume']
    create_nonroot_volumes = kwargs['create_nonroot_volumes']

    logical_disks = node.extra['target_raid_configuration']['logical_disks']
    physical_disks = list_physical_disks(node)

    logical_disks_to_create = _filter_logical_disks(logical_disks,
                                    create_root_volume, create_nonroot_volumes)
    _match_physical_disks(logical_disks_to_create, physical_disks)
    _add_missing_options(logical_disks_to_create)

    controllers = set()
    for logical_disk in logical_disks_to_create:
        controllers.add(logical_disk['controller'])
        create_virtual_disk(node, **logical_disk)

    driver_internal_info = node.driver_internal_info
    driver_internal_info['raid_config_job_ids'] = []
    controllers = list(controllers)
    for controller in controllers:
        # Do a reboot only for the last controller if requested
        if controller == controllers[-1]:
            reboot = kwargs.get('reboot')
            job_id = apply_pending_config(node, raid_controller=controller,
                                          reboot=reboot)
        else:
            job_id = apply_pending_config(node, raid_controller=controller,
                                          reboot=False)

        driver_internal_info['raid_config_job_ids'].append(job_id)

    node.driver_internal_info = driver_internal_info
    node.save()


def _match_physical_disks(logical_disks, physical_disks):
    used_physical_disks = []

    # find already assigned physical disks - they are not going to be used
    for logical_disk in logical_disks:
        if 'physical_disks' in logical_disk:
            used_disks = ([disk
                for used_disk_id in logical_disk['physical_disks']
                for disk in physical_disks
                if (logical_disk['controller'] == disk['controller'] and
                    disk['id'] == used_disk_id)])
            used_physical_disks.extend(used_disks)

    # assign physical disks
    for logical_disk in logical_disks:
        if 'physical_disks' in logical_disk:
            continue

        candidates = [disk for disk
                      in _filter_physical_disks(physical_disks, logical_disk)
                      if disk not in used_physical_disks]
        selected = candidates[:logical_disk['number_of_physical_disks']]

        if logical_disk['number_of_physical_disks'] != len(selected):
            reason = (_('Cannot find physical disks for %s') % logical_disk)
            raise exception.DracInvalidRaidConfiguration(reason=reason)

        logical_disk['physical_disks'] = [disk['id'] for disk in selected]
        used_physical_disks.extend(selected)

    return logical_disks


def _filter_physical_disks(physical_disks, logical_disk_config):
    filtered_disks = [disk for disk in physical_disks
        if (disk['raid_state'] == 'ready' and
            disk['controller'] == logical_disk_config['controller'])]

    if 'interface_type' in logical_disk_config:
        filtered_disks = [disk for disk in filtered_disks
                          if (disk['interface_type'] ==
                                logical_disk_config['interface_type'])]

    if 'disk_type' in logical_disk_config:
        filtered_disks = [disk for disk in filtered_disks
                          if (disk['disk_type'] ==
                                logical_disk_config['disk_type'])]

    return filtered_disks


def _filter_logical_disks(logical_disks, include_root_volume,
                                         include_nonroot_volumes):
    filtered_disks = []
    for disk in logical_disks:
        if include_root_volume and disk.get('is_root_volume'):
            filtered_disks.append(disk)

        if include_nonroot_volumes and not disk.get('is_root_volume'):
            filtered_disks.append(disk)

    return filtered_disks


def _add_missing_options(logical_disks):
    for disk in logical_disks:
        if 'size_mb' not in disk:
            disk['size_mb'] = disk['size_gb'] * 2 ** 10
            disk.pop('size_gb')

        span_length, span_depth = _calculate_spans(disk['raid_level'],
                                                   len(disk['physical_disks']))
        if 'span_depth' not in disk:
            disk['span_depth'] = span_depth

        if 'span_length' not in disk:
            disk['span_length'] = span_length

        disk['raid_controller'] = 'RAID.Integrated.1-1'


def _calculate_spans(raid_level, disks_count):
    """Calculates span depth and length for a virtual disk

    Calculates the number of spans (span depth) required for the virtual disk
    and the number of disks per span (span length).

    :param raid_level: RAID level of the virtual disk.
    :param disk_count: number of physical disks used for the virtual disk.
    :returns: A tuple containing the span length and the span depth.
    """

    # NOTE(ifarkas): logic as implemented in Crowbar:
    #                https://github.com/opencrowbar/hardware/blob/develop/raid/crowbar_engine/barclamp_raid/app/models/barclamp_raid/driver.rb#L121 # noqa
    if raid_level in ['0', '1', '5', '6']:
        return (disks_count, 1)
    elif raid_level in ['5+0', '6+0']:
        return ((disks_count >> 1) << 1, 2)
    elif raid_level in ['1+0']:
        return ((disks_count >> 1) << 1, disks_count >> 1)
    else:
        reason = (_('Cannot calculate disk spans for RAID level "%s"') %
                  raid_level)
        raise exception.DracInvalidRaidConfiguration(reason=reason)
