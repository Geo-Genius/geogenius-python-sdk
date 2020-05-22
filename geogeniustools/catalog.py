"""
Geogenius Catalog Interface.

Contact: zhaoxianwei@huawei.com
"""
from __future__ import absolute_import

import json
from builtins import object

from geogeniustools.rda.env_variable import MANAGER_ENDPOINT

from geogeniustools.auth import Auth
from geogeniustools.rda.error import BadRequest


class Catalog(object):

    def __init__(self, **kwargs):
        """ Construct the Catalog interface class

        Returns:
            An instance of the Catalog interface class.
        """
        interface = Auth(**kwargs)
        self.base_url = '%s/catalog' % MANAGER_ENDPOINT
        self.get_by_id_url = '%(base_url)s/metadata?dataId=%(cat_id)s'
        self.query_url = '%(base_url)s/search'
        self.geogenius_connection = interface.geogenius_connection
        self.logger = interface.logger

    def get(self, cat_id):
        """Retrieves the catalog string given a cat ID.

        Args:
            cat_id (str): The source catalog ID from the platform catalog.

        Returns:
            record (dict): A dict object identical to the json representation of the catalog
        """
        url = self.get_by_id_url % {
            'base_url': self.base_url, 'cat_id': cat_id
        }
        r = self.geogenius_connection.get(url)
        r.raise_for_status()
        return r.json()

    def get_strip_footprint_wkt(self, cat_id):
        """Retrieves the strip footprint WKT string given a cat ID.

        Args:
            cat_id (str): The source catalog ID from the platform catalog.

        Returns:
            footprint (str): A POLYGON of coordinates.
        """

        self.logger.debug('Retrieving catalog strip footprint wkt')
        try:
            result = self.get(cat_id)
            return result['boundary']
        except:
            return None

    def get_strip_metadata(self, cat_id):
        """Retrieves the strip catalog metadata given a cat ID.

        Args:
            cat_id (str): The source catalog ID from the platform catalog.

        Returns:
            metadata (dict): A metadata dictionary .
        """

        self.logger.debug('Retrieving strip catalog metadata')
        try:
            result = self.get(cat_id)
            return result['metadataProperties']
        except:
            return None

    def get_data_location(self, cat_id):
        """
        Find and return the S3 data location given a catalog_id.

        Args:
            cat_id (str): The source catalog ID from the platform catalog.

        Returns:
            A string containing the s3 location of the data associated with a catalog ID.  Returns
            None if the catalog ID is not found, or if there is no data yet associated with it.
        """
        self.logger.debug('Retrieving catalog data location')
        try:
            result = self.get(cat_id)
        except:
            return None
        source_type = result['sourceType'].lower()
        if source_type == 'obs1':
            return result['dataUrl']
        else:
            raise BadRequest("Don't support the source type %s" % result['sourceType'])

    def search_point(self, lat, lng, filters=None, start_resolution=None, end_resolution=None, start_time=None,
                     end_time=None, source_type=None, limit=None):
        """ Perform a catalog search over a specific point, specified by lat,lng

        Args:
            lat: latitude
            lng: longitude
            filters: Array of filters.  Optional. Example:
            [
                "cloudCover < 10",
                "path = 10"
            ]
            start_resolution: float, Optional. Example :10
            end_resolution: float, Optional. Example :20
            start_time: int.  Optional.  Example: 1548713541091
            end_time: int.  Optional.  Example: 1568713541091
            source_type: String, source type to search for, required.
                Example: "S3Tiff", "OBSTiff", "Lansat"
            limit: int. the max length of service return ,default and upper limit is 1000, Optional. Example: "10"

        Returns:
            catalog search resultset
        """
        boundary = "POINT (%s %s)" % (lng, lat)
        return self.search(boundary=boundary, filters=filters, start_resolution=start_resolution,
                           end_resolution=end_resolution, start_time=start_time, end_time=end_time,
                           source_type=source_type, limit=limit)

    def search(self, boundary=None, filters=None, start_resolution=None, end_resolution=None, start_time=None,
               end_time=None, source_type=None, limit=None):
        """ Perform a catalog search

        Args:
            boundary: WKT Polygon of area to search.  Optional.
            filters: Array of filters.  Optional.  Example:
            [
                "cloudCover < 10",
                "offNadirAngle < 10"
            ]
            start_resolution: float, Optional. Example :10
            end_resolution: float, Optional. Example :20
            start_time: int.  Optional.  Example: 1548713541091
            end_time: int.  Optional.  Example: 1568713541091
            source_type: String, source type to search for, required.
                Example: "S3Tiff", "OBSTiff", "Lansat"
            limit: int. the max length of service return ,default and upper limit is 1000, Optional. Example: "10"

        Returns:
            catalog search resultset
        """
        if not source_type:
            raise BadRequest("source_type is required.")

        # validation
        if start_time and end_time:
            if end_time - start_time < 0:
                # TODO: warp the exception or error
                raise BadRequest("start time must come before end time.")

        # TODO: add args , data_owner
        post_data = {
            "boundary": boundary,
            "sourceType": source_type,
            "start_resolution": start_resolution,
            "end_resolution": end_resolution,
            "startTime": start_time,
            "endTime": end_time,
            "filter": filters,
            "limit": limit
        }

        url = self.query_url % {
            'base_url': self.base_url
        }

        headers = {'Content-Type': 'application/json'}
        r = self.geogenius_connection.post(url, headers=headers, data=json.dumps(post_data))
        r.raise_for_status()
        results = r.json()

        return results

    def get_most_recent_images(self, results, source_types=[], N=1):
        """ Return the most recent image

        Args:
            results: a catalog resultset, as returned from a search
            source_types: array of types you want. optional.
            N: number of recent images to return.  defaults to 1.

        Returns:
            single catalog item, or none if not found

        """
        if not len(results):
            return None

        # filter on source_type
        if source_types:
            results = [r for r in results if r['sourceType'] in source_types]

        # sort by date:
        # sorted(results, key=results.__getitem__('properties').get('timestamp'))
        newlist = sorted(results, key=lambda k: k['produceTime'], reverse=True)
        return newlist[:N]
