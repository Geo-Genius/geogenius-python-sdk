import json

from geogeniustools.rda.env_variable import RDA_ENDPOINT, MANAGER_ENDPOINT
from geogeniustools.rda.error import BadRequest, NotFound


def get_rda_metadata(conn, rda_id):
    md_response = conn.get("{}/rda/meta/{}".format(RDA_ENDPOINT, rda_id))
    if md_response.status_code != 200:
        md_json = md_response.json()
        if 'message' in md_json:
            raise BadRequest("RDA error: {}. RDA Graph: {}".format(md_json['message'], rda_id))
        raise BadRequest("Problem fetching image metadata: status {} {}, graph_id: {}".format(md_response.status_code,
                                                                                              md_response.reason,
                                                                                              rda_id))
    else:
        md_json = md_response.json()
        return {
            "image": md_json["image"],
            "georef": md_json.get("georef", None)
        }


def get_rda_graph(conn, graph_id):
    url = "{}/graph/{}".format(MANAGER_ENDPOINT, graph_id)
    md_response = conn.get(url)
    if md_response.status_code == 200:
        return md_response.json()
    else:
        raise NotFound("No RDA graph found matching id: {}".format(graph_id))


def register_rda_graph(conn, rda_graph):
    url = "{}/graph".format(MANAGER_ENDPOINT)
    md_response = conn.post(url, json.dumps(rda_graph, sort_keys=True), headers={'Content-Type': 'application/json'})
    if md_response.status_code == 201:
        return json.loads(md_response.text)['graphId']
    else:
        raise BadRequest("Problem registering graph: {}".format(json.loads(md_response.text)['message']))
