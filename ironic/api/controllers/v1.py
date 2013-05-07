# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 Hewlett-Packard Development Company, L.P.
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

"""
Version 1 of the Ironic API

Should maintain feature parity with Nova Baremetal Extension.
Specification in ironic/doc/api/v1.rst
"""


import pecan
from pecan import rest

import wsme
import wsmeext.pecan as wsme_pecan
from wsme import types as wtypes

from ironic import db


class Base(wtypes.Base):
    # TODO: all the db bindings

    @classmethod
    def from_db_model(cls, m):
        return cls(**(m.as_dict()))

    @classmethod
    def from_db_and_links(cls, m, links):
        return cls(links=links, **(m.as_dict()))

    def as_dict(self, db_model):
        valid_keys = inspect.getargspec(db_model.__init__)[0]
        if 'self' in valid_keys:
            valid_keys.remove('self')

        return dict((k, getattr(self, k))
                    for k in valid_keys
                    if hasattr(self, k) and
                    getattr(self, k) != wsme.Unset)


class Interface(Base):
    """A representation of a network interface for a baremetal node"""

    node_id = int
    address = wtypes.text

    def __init__(self, node_id=None, address=None):
        self.node_id = node_id
        self.address = address

    @classmethod
    def sample(cls):
        return cls(node_id=1,
                   address='52:54:00:cf:2d:31',
                   )


class InterfacesController(rest.RestController):
    """REST controller for Interfaces"""

    @wsme_pecan.wsexpose(Interface, unicode) 
    def post(self, iface):
        """Ceate a new interface."""
        return Interface.sample()

    @wsme_pecan.wsexpose()
    def get_all(self):
        """Retrieve a list of all interfaces."""
        ifaces = [Interface.sample()]
        return [(i.node_id, i.address) for i in ifaces]

    @wsme_pecan.wsexpose(Interface, unicode)
    def get_one(self, address):
        """Retrieve information about the given interface."""
        one = Interface.sample()
        one.address = address
        return one

    @wsme_pecan.wsexpose()
    def delete(self, iface_id):
        """Delete an interface"""
        pass

    @wsme_pecan.wsexpose()
    def put(self, iface_id):
        """Update an interface"""
        pass


class Node(Base):
    """A representation of a bare metal node"""

    uuid = wtypes.text
    cpus = int
    memory_mb = int

    def __init__(self, uuid=None, cpus=None, memory_mb=None):
        self.uuid = uuid
        self.cpus = cpus
        self.memory_mb = memory_mb

    @classmethod
    def sample(cls):
        return cls(uuid='1be26c0b-03f2-4d2e-ae87-c02d7f33c123',
                   cpus=2,
                   memory_mb=1024,
                   )

 
class NodesController(rest.RestController):
    """REST controller for Nodes"""

    @wsme_pecan.wsexpose(Node, unicode) 
    def post(self, node):
        """Ceate a new node."""
        return Node.sample()

    @wsme_pecan.wsexpose()
    def get_all(self):
        """Retrieve a list of all nodes."""
        nodes = [Node.sample()]
        return [n.uuid for n in nodes]

    @wsme_pecan.wsexpose(Node, unicode)
    def get_one(self, node_id):
        """Retrieve information about the given node."""
        one = Node.sample()
        one.uuid = node_id
        return one

    @wsme_pecan.wsexpose()
    def delete(self, node_id):
        """Delete a node"""
        pass

    @wsme_pecan.wsexpose()
    def put(self, node_id):
        """Update a node"""
        pass


class Controller(object):
    """Version 1 API controller root."""

    # TODO: _default and index

    nodes = NodesController()
    interfaces = InterfacesController()
