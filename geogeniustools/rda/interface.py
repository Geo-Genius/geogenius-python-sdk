import json
import uuid
from collections import OrderedDict
from hashlib import sha256
from itertools import chain

import requests

from geogeniustools.rda.fetch.threaded.libcurl.easy import load_url
from geogeniustools.rda.graph import get_rda_metadata, RDA_ENDPOINT, register_rda_graph
from geogeniustools.session import get_session

NAMESPACE_UUID = uuid.NAMESPACE_DNS


class ContentHashedDict(dict):
    @property
    def _id(self):
        _id = str(uuid.uuid5(NAMESPACE_UUID, self.__hash__()))
        return _id

    def __hash__(self):
        dup = OrderedDict({k: v for k, v in self.items() if k is not "id"})
        return sha256(str(dup).encode('utf-8')).hexdigest()

    def populate_id(self):
        self.update({"id": self._id})


class DaskProps(object):

    def graph(self):
        pass

    @property
    def metadata(self):
        assert self.graph() is not None
        if self._rda_meta is not None:
            return self._rda_meta
        if self._interface is not None:
            self._rda_meta = get_rda_metadata(self._interface, self._rda_id)
        return self._rda_meta

    @property
    def dask(self):
        token = self._interface.get_token()
        _chunks = self.chunks
        _name = self.name
        img_md = self.metadata["image"]
        return {(_name, 0, y - img_md['minTileY'], x - img_md['minTileX']): (load_url, url, token, _chunks)
                for (y, x), url in self._collect_urls().items()}

    @property
    def name(self):
        return "image-{}".format(self._id)

    @property
    def chunks(self):
        img_md = self.metadata["image"]
        return img_md["numBands"], img_md["tileYSize"], img_md["tileXSize"]

    @property
    def dtype(self):
        # TODO add exception
        data_type = self.metadata["image"]["dataType"]
        return data_type

    @property
    def shape(self):
        img_md = self.metadata["image"]
        return (img_md["numBands"],
                (img_md["maxTileY"] - img_md["minTileY"] + 1) * img_md["tileYSize"],
                (img_md["maxTileX"] - img_md["minTileX"] + 1) * img_md["tileXSize"])

    @staticmethod
    def _rda_tile(x, y, rda_id, node_id):
        return "{}/rda/read/{}/{}/{}/{}.TIF".format(RDA_ENDPOINT, rda_id, node_id, x, y)

    def _collect_urls(self):
        img_md = self.metadata["image"]
        rda_id = self._rda_id
        _id = self._id
        return {(y, x): self._rda_tile(x, y, rda_id, _id)
                for y in range(img_md['minTileY'], img_md["maxTileY"] + 1)
                for x in range(img_md['minTileX'], img_md["maxTileX"] + 1)}


class Op(DaskProps):
    def __init__(self, name, interface=None):
        self._operator = name
        self._edges = []
        self._nodes = []

        self._rda_id = None  # The graph ID
        self._rda_graph = None  # the RDA graph
        self._rda_meta = None  # Image metadata
        self._rda_stats = None  # Display Stats

        self._interface = interface

    @property
    def _id(self):
        return self._nodes[0]._id

    def __call__(self, *args, **kwargs):
        self._nodes = [ContentHashedDict({
            "operator": self._operator,
            "_ancestors": [arg._id for arg in args],
            "parameters": OrderedDict({
                k: json.dumps(v, sort_keys=True) if not isinstance(v, str) else v
                for k, v in sorted(kwargs.items(), key=lambda x: x[0])})
        })]
        for arg in args:
            self._nodes.extend(arg._nodes)

        self._edges = [ContentHashedDict({"index": idx + 1, "source": arg._nodes[0]._id,
                                          "destination": self._nodes[0]._id})
                       for idx, arg in enumerate(args)]
        for arg in args:
            self._edges.extend(arg._edges)

        for e in chain(self._nodes, self._edges):
            e.populate_id()
        return self

    def graph(self, conn=None):
        if (self._rda_id is not None and
                self._rda_graph is not None):
            return self._rda_graph

        _nodes = [{k: v for k, v in node.items() if not k.startswith('_')} for node in self._nodes]
        graph = {
            "edges": self._edges,
            "nodes": _nodes
        }

        if self._interface is not None and conn is None:
            # TODO geogenius: self._interface.gbdx_futures_session
            conn = self._interface

        if conn is not None:
            # self._rda_id = "obs://obs-tiff-test/retile_china/ng47_05_41.tif"
            self._rda_id = register_rda_graph(conn, graph)
            self._rda_graph = graph
            # TODO geogenius: should add node id
            self._rda_meta = get_rda_metadata(conn, self._rda_id)
            return self._rda_graph

        return graph


class RDA(object):
    def __getattr__(self, name):
        # TODO geogenius: should use real auth
        return Op(name=name, interface=get_session())
