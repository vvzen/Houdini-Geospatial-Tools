import os
import json
import pprint
import logging
import math
from pathlib import Path
from typing import TypeAlias, Union, Tuple, Optional

if not os.getenv('DEV'):
    import hou

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] - %(message)s",
    handlers=[
        logging.StreamHandler()
    ])

log = logging.getLogger('geo_utils')

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
        self._point_attributes = set()

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
            log.error('No geometry found for current feature')
            return

        if geometry.get('type') != typename:
            log.error(
                'No %s geo found inside %s feature' % (typename, typename))
            return

        return geometry

    def _add_point(
        self,
        coordinates: Tuple[int, int],
        properties: Optional[dict] = None,
    ):
        assert len(coordinates) == 2

        lon, lat = coordinates
        point = self._node_geo.createPoint()
        x, y, z = spherical_to_cartesian(lon, lat, self._radius)
        point.setPosition((x, y, z))

        if properties:
            for key, value in properties.items():
                if key not in self._point_attributes:
                    self._node_geo.addAttrib(hou.attribType.Point, key, "")
                    self._point_attributes.add(key)

                if value:
                    point.setAttribValue(key, value)

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
        log.info('adding MultiPolygon')

        for pi, polygon in enumerate(coordinates):
            log.info('adding polygon %i ' % pi)
            log.info(polygon)
            self._add_polygon(polygon)

    def _parse_geometry(
        self,
        feature_geo_type: str,
        geometry,
        properties: Optional[dict] = None,
    ):
        coordinates = geometry.get('coordinates')

        if not coordinates:
            log.error(
                'No coordinates found for current %s, skipping' % feature_geo_type)
            return

        if feature_geo_type == 'Point':
            self._add_point(coordinates, properties)

        # TODO: Support properties for all feature types, not just on Points
        elif feature_geo_type == 'MultiLineString':
            self.add_multi_line_string(coordinates)

        elif feature_geo_type == 'LineString':
            self.add_line_string(coordinates)

        elif feature_geo_type == 'MultiPoint':
            self._add_multi_point(coordinates)

        elif feature_geo_type == 'Polygon':
            self._add_polygon(coordinates)

        elif feature_geo_type == 'MultiPolygon':
            self._add_multi_polygon(coordinates, )

    def create_geo(self, radius: IntOrFloat = 100):
        features_found_map = {}
        self.set_radius(radius)

        if not self.geojson.get('features'):
            if self.geojson.get('type') == 'GeometryCollection':
                geometries = self.geojson.get('geometries')

                if not geometries:
                    message = 'The given GeoJSON has a GeometryCollection '
                    message += "that doesn't contain anything!"
                    hou.ui.displayMessage(message)
                    return

                for geometry in geometries:
                    feature_geo_type = geometry.get('type')

                    if not feature_geo_type:
                        hou.ui.displayMessage(
                            'The given GeoJSON has no features and ' +
                            'is not a GeometryCollection!'
                        )
                        log.error('Feature <type> field not found.')
                        continue

                    self._parse_geometry(feature_geo_type, geometry)

            return

        for feature in self._yield_features():
            geo = feature.get("geometry")
            if not geo:
                # log.warning("Skipping feature without any geometry: %s", feature)
                continue

            feature_geo_type = feature["geometry"].get('type')
            if not feature_geo_type:
                log.error('Feature type property not found.')
                continue

            if feature_geo_type not in features_found_map:
                features_found_map[feature_geo_type] = 1
            else:
                features_found_map[feature_geo_type] += 1

            geometry = self._get_geometry(feature_geo_type, feature)
            if not geometry:
                continue

            properties = feature.get('properties')
            self._parse_geometry(feature_geo_type, geometry, properties)

        log.info("Finished creating geometry!")
        log.info("Features found: %s", pprint.pformat(features_found_map))
