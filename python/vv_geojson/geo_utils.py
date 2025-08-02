import os
import json
import pprint
import logging
import math
from pathlib import Path
from typing import TypeAlias, Union

if not os.getenv('DEV'):
    import hou

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] - %(message)s",
    handlers=[
        logging.StreamHandler()
    ])

logger = logging.getLogger('geo_utils')

IntOrFloat: TypeAlias = Union[int, float]

def spherical_to_cartesian(
    lon: IntOrFloat,
    lat: IntOrFloat,
    radius: IntOrFloat
):
    """Converts from a spherical coordinate system to a cartesian one

    :param lon: longitude
    :type lon: float

    :param lat: latitude
    :type lat: float

    :param radius: radius of the final globe
    :type radius: float

    :return: tuple of resulting x, y, z coordinates
    :rtype: tuple
    """

    latitude = math.radians(lat)
    longitude = math.radians(lon)

    x = math.cos(latitude) * math.cos(longitude) * radius
    y = math.cos(latitude) * math.sin(longitude) * radius
    z = math.sin(latitude) * radius  # z is 'up'

    return x, y, z


# see https://stackoverflow.com/questions/14329691/convert-latitude-longitude-point-to-a-pixels-x-y-on-mercator-projection
def spherical_to_mercator(lon, lat, mapwidth, mapheight):
    x = (lon + 180) * (mapwidth / 360)
    latitude_radians = lat * math.pi / 180
    mercator_N = math.log(math.tan((math.pi / 4) + (latitude_radians / 2)))
    y = (mapheight / 2) - (mapwidth * mercator_N / (math.pi * 2))

    return x, y, 0


class GeoJSONParser:

    def __init__(self, geo, geojsonpath: os.PathLike):
        self._node_geo = geo
        self._geojson_path: os.PathLike = geojsonpath
        self._radius: IntOrFloat = 100

        if not os.path.isfile(geojsonpath):
            hou.ui.displayMessage('Please provide a path to an existing file,'
                                  'not a directory!')
            return

        if not os.path.exists(geojsonpath):
            hou.ui.displayMessage('Please provide a path to an existing file!')
            return

        data_ser = Path(geojsonpath).read_text()
        data_de = json.loads(data_ser)
        self.geojson = data_de

    def set_radius(self, value: IntOrFloat):
        if not isinstance(value, (float, int)):
            hou.ui.displayMessage('Please provide a float or an '
                                  'integer for the radius!')
            return

        self._radius = value

    def _yield_features(self):
        for feature in self.geojson['features']:
            yield feature

    def _get_geometry(self, typename, feature):
        geometry = feature.get('geometry')
        if not geometry:
            logger.error('No geometry found for current feature')
            return

        if geometry.get('type') != typename:
            logger.error(
                'No %s geo found inside %s feature' % (typename, typename))
            return

        return geometry

    def _add_point(self, coordinates):

        assert len(coordinates) == 2

        lon, lat = coordinates

        point = self._node_geo.createPoint()
        x, y, z = spherical_to_cartesian(lon, lat, self._radius)
        point.setPosition((x, y, z))

        return point

    def _add_multi_point(self, coordinates):

        for coordinate in coordinates:
            self._add_point(coordinate)

    def add_line_string(self, coordinates):
        poly = self._node_geo.createPolygon()
        poly.setIsClosed(False)

        for coordinate in coordinates:
            pt = self._add_point(coordinate)

            poly.addVertex(pt)

    def add_multi_line_string(self, coordinates):
        for coordinate in coordinates:
            self.add_line_string(coordinate)

    def _add_polygon(self, poly):

        # create the polygon that will host the points
        hou_polygon = self._node_geo.createPolygon()
        # hou_polygon.setIsClosed(False)
        hou_polygon.setIsClosed(True)

        for ri, ring in enumerate(poly):
            for coordinates in ring:
                point = self._add_point(coordinates)
                hou_polygon.addVertex(point)

    def _add_multi_polygon(self, coordinates):

        # TODO: check for inner holes
        logger.info('adding MultiPolygon')

        for pi, polygon in enumerate(coordinates):
            logger.info('adding polygon %i ' % pi)
            logger.info(polygon)
            self._add_polygon(polygon)

    def _parse_geometry(self, featuretype: str, geometry):
        coordinates = geometry.get('coordinates')

        if not coordinates:
            logger.error(
                'No coordinates found for current %s, skipping' % featuretype)
            return

        if featuretype == 'Point':
            self._add_point(coordinates)

        elif featuretype == 'MultiLineString':
            self.add_multi_line_string(coordinates)

        elif featuretype == 'LineString':
            self.add_line_string(coordinates)

        elif featuretype == 'MultiPoint':
            self._add_multi_point(coordinates)

        elif featuretype == 'Polygon':
            self._add_polygon(coordinates)

        elif featuretype == 'MultiPolygon':
            self._add_multi_polygon(coordinates)

    def create_geo(self, radius: IntOrFloat = 100):
        features_found_map = {}
        self.set_radius(radius)

        _features = self.geojson.get('features')
        if not _features:

            if self.geojson.get('type') == 'GeometryCollection':
                geometries = self.geojson.get('geometries')

                if not geometries:
                    message = 'The given GeoJSON has a GeometryCollection '
                    message += "that doesn't contain anything!"
                    hou.ui.displayMessage(message)
                    return

                for geometry in geometries:
                    feature_type = geometry.get('type')

                    if not feature_type:
                        hou.ui.displayMessage(
                            'The given GeoJSON has no features and ' +
                            'is not a GeometryCollection!'
                        )
                        logger.error('Feature <type> field not found.')
                        continue

                    self._parse_geometry(feature_type, geometry)

            return

        for feature in self._yield_features():
            geo = feature.get("geometry")
            if not geo:
                logger.warning("Skipping feature without any geometry: %s", feature)
                continue

            feature_type = feature["geometry"].get('type')
            if not feature_type:
                logger.error('Feature type property not found.')
                continue

            if feature_type not in features_found_map:
                features_found_map[feature_type] = 1
            else:
                features_found_map[feature_type] += 1

            geometry = self._get_geometry(feature_type, feature)
            if not geometry:
                continue

            self._parse_geometry(feature_type, geometry)

        logger.info("Finished creating geometry!")
        logger.info("Features found: %s", pprint.pformat(features_found_map))
