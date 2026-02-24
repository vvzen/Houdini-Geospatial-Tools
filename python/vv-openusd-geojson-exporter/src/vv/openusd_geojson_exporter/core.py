import enum
import json
import math
import logging
import dataclasses
from collections import defaultdict
from pathlib import Path
from typing import Self, Any, Type, TypedDict, TypeAlias

from pxr import Usd, UsdGeom, Gf, Sdf

log = None

# Typed Dicts and aliases to simplify type hints when reading GeoJSON features
# ------------------------------------------------------------------
XYZ: TypeAlias = tuple[float, float, float]  # x,y,z
PropTypesMap: TypeAlias = dict[str, Type]
"""
'prop name => prop type' map
"""

PropValuesMap: TypeAlias = dict[str, list[Any]]
"""
'prop name => prop values' map
where `values` should use the same indexing of the x,y,z 'positions'
"""

# 'prop name => prop type' map


class GeoJSONGeoDict(TypedDict):
    type: str

    # A Point has a single entry,
    # A LineString has a list of entries
    coordinates: XYZ | list[XYZ]


class GeoJSONFeatureDict(TypedDict):
    id: str
    type: str
    properties: dict[str, Any]
    geometry: GeoJSONGeoDict


class GeoJSONObject(TypedDict):
    type: str
    properties: dict[str, Any]
    geometry: GeoJSONGeoDict
    features: list[GeoJSONFeatureDict]
# ------------------------------------------------------------------


def spherical_to_cartesian(
    lon: float,
    lat: float,
    radius: float,
) -> XYZ:
    """Converts from a spherical coordinate system to a cartesian one

    :param lon: longitude
    :param lat: latitude
    :param radius: radius of the final globe
    :return: tuple of resulting x, y, z coordinates
    """

    latitude = math.radians(lat)
    longitude = math.radians(lon)

    x = math.cos(latitude) * math.cos(longitude) * radius
    y = math.cos(latitude) * math.sin(longitude) * radius
    z = math.sin(latitude) * radius  # z is 'up' (..or is it?)

    return x, y, z


class GeoJSONObjectType(enum.Enum):
    # From the official RFC: https://datatracker.ietf.org/doc/html/rfc7946
    # A GeoJSON object may represent:
    # - A region of space (a Geometry)
    # - A spatially bounded entity (a Feature)
    # - A list of a Features (a FeatureCollection)
    Geometry = 'Geometry'
    Feature = 'Feature'
    FeatureCollection = 'FeatureCollection'

    @classmethod
    def from_str(cls, s: str) -> Self:
        for name, entry in cls.__members__.items():
            if name == s:
                return entry

        raise RuntimeError(f"Unsupported GeoJSON Object type: {s}")


class GeoJSONFeatureType(enum.Enum):
    # GeoJSON supports the following geometry types:
    # - Point
    # - LineString
    # - Polygon
    # - MultiPoint
    # - MultiLineString
    # - MultiPolygon
    # - GeometryCollection
    # Ideally I'd need to understand how each one of them maps to OpenUSD concepts

    Point = 'Point'
    LineString = 'LineString'

    @classmethod
    def from_str(cls, s: str) -> Self:
        for name, entry in cls.__members__.items():
            if name == s:
                return entry
        raise RuntimeError(f"Sorry, '{s}' is not a supported GeoJSON feature")


@dataclasses.dataclass
class PointsData:
    positions: list[XYZ]
    properties_values: PropValuesMap
    properties_types: PropTypesMap


@dataclasses.dataclass
class LineStringData:
    positions: list[XYZ]  # The positions of ALL the lines
    lines_lengths: list[int]  # How many points is each line composed of
    properties_values: PropValuesMap
    properties_types: PropTypesMap


@dataclasses.dataclass
class GeometryData:
    points: PointsData
    lines: LineStringData


def sanitize_attribute_name(name: str) -> str:
    """
    Ensure that we only create attributes using names supported by USD.

    For example, ":id" is not a valid attribute name, and would later throw a
    pxr.Tf.ErrorException:
            Error in 'pxrInternal_v0_25_11__pxrReserved__::SdfAttributeSpec::New' at line 53 in file /opt/USD/pxr/usd/sdf/attributeSpec.cpp : 'Cannot create attribute spec on </world/points> with invalid name 'primvars::id''

    '@' is also not valid:
            Error in 'pxrInternal_v0_25_11__pxrReserved__::SdfAttributeSpec::New' at line 53 in file /opt/USD/pxr/usd/sdf/attributeSpec.cpp : 'Cannot create attribute spec on </world/points> with invalid name 'primvars:_@computed_region_qgnn_b9vv''
    """

    new_name = name.replace(':', '_')
    new_name = new_name.replace('@', '_')
    return new_name


def _parse_feature_collection(
    data: GeoJSONObject,
    attributes_allowlist: list[str],
    log: logging.Logger,
) -> GeometryData:
    """
    Export the given GeoJSON ``data`` to our own internal representation.
    If ``attributes_allowlist`` is given, properties of 'Feature's that aren't
    included in the list will not be exported.
    """

    points_data = PointsData(
        positions=[],
        properties_values=defaultdict(list),
        properties_types={},
    )
    lines_data = LineStringData(
        positions=[],
        lines_lengths=[],
        properties_values=defaultdict(list),
        properties_types={},
    )

    for feature in data['features']:
        geo = feature.get('geometry')
        if not geo:
            log.debug("Skipping feature with no geometry..")
            log.debug("Skipped feature: %s", feature)
            continue

        data_type = GeoJSONFeatureType.from_str(geo['type'])
        coords = geo['coordinates']

        match data_type:
            case GeoJSONFeatureType.Point:
                # e.g.: 'geometry': {'type': 'Point', 'coordinates': [-122.431196363, 37.767649916]}}
                lon, lat = coords[0], coords[1]
                assert isinstance(lon, float)
                assert isinstance(lat, float)
                x, y, z = spherical_to_cartesian(lon, lat, radius=1)

                points_data.positions.append((x, y, z))

                for key, prop_value in feature.get("properties", {}).items():
                    if attributes_allowlist and key not in attributes_allowlist:
                        continue
                    key = sanitize_attribute_name(key)
                    points_data.properties_types[key] = type(prop_value)
                    points_data.properties_values[key].append(prop_value)

            case GeoJSONFeatureType.LineString:
                assert isinstance(coords, list)
                line_coords = [
                    spherical_to_cartesian(point[0], point[1], radius=1)
                    for point in coords
                ]
                lines_data.positions.extend(line_coords)
                lines_data.lines_lengths.append(len(line_coords))

                for key, prop_value in feature.get("properties", {}).items():
                    if attributes_allowlist and key not in attributes_allowlist:
                        continue
                    key = sanitize_attribute_name(key)
                    lines_data.properties_types[key] = type(prop_value)
                    for _ in line_coords:
                        lines_data.properties_values[key].append(prop_value)

    final_data = GeometryData(points=points_data, lines=lines_data)
    return final_data


def parse_geojson_geometry(
    data: GeoJSONObject,
    attributes_allowlist: list[str],
    log: logging.Logger,
) -> GeometryData:
    geojson_data_type = GeoJSONObjectType.from_str(data['type'])
    log.info("Detected Type: %s", geojson_data_type)

    match geojson_data_type:
        case GeoJSONObjectType.FeatureCollection:
            return _parse_feature_collection(data, attributes_allowlist, log)
        case _:
            raise NotImplementedError(
                f"Sorry, '{geojson_data_type}' is currently "
                "not supported!"
            )


def get_logger() -> logging.Logger:
    global log

    # If things are already setup, skip!
    if log is not None:
        return log

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    stream_handler = logging.StreamHandler()
    logger.addHandler(stream_handler)

    return logger


def create_points_prim(
    stage: Usd.Stage,
    world: UsdGeom.Xform,
    points_data: PointsData,
) -> UsdGeom.Points:

    # Create the points prim
    points = UsdGeom.Points.Define(
        stage,
        world.GetPath().AppendChild("points"),
    )

    # Set the position attr
    points.CreatePointsAttr(points_data.positions)

    # Set all the other custom attrs
    # See https://github.com/PixarAnimationStudios/OpenUSD/issues/2628
    # for tips on the PrimvarAPI
    primvar_api = UsdGeom.PrimvarsAPI(points.GetPrim())
    for prop_name, prop_values in points_data.properties_values.items():
        py_type = points_data.properties_types[prop_name]

        if py_type is int:
            usd_type = Sdf.ValueTypeNames.IntArray
        elif py_type is float:
            usd_type = Sdf.ValueTypeNames.FloatArray
        else:
            usd_type = Sdf.ValueTypeNames.StringArray
            prop_values = [str(e) for e in prop_values]

        primvar_api.CreatePrimvar(
            prop_name,
            usd_type,
            UsdGeom.Tokens.vertex,
        )\
        .Set(prop_values)

    return points


def create_curve_prim(
    stage: Usd.Stage,
    world: UsdGeom.Xform,
    data: LineStringData,
) -> UsdGeom.BasisCurves:

    curve = UsdGeom.BasisCurves.Define(
        stage,
        world.GetPath().AppendChild("lines"),
    )

    curve.CreateTypeAttr("linear")
    curve.CreatePointsAttr(data.positions)
    curve.CreateCurveVertexCountsAttr(data.lines_lengths)

    primvar_api = UsdGeom.PrimvarsAPI(curve.GetPrim())

    # Set all the other custom attrs
    primvar_api = UsdGeom.PrimvarsAPI(curve.GetPrim())
    for prop_name, prop_values in data.properties_values.items():
        py_type = data.properties_types[prop_name]

        if py_type is int:
            usd_type = Sdf.ValueTypeNames.IntArray
        elif py_type is float:
            usd_type = Sdf.ValueTypeNames.FloatArray
        else:
            usd_type = Sdf.ValueTypeNames.StringArray
            prop_values = [str(e) for e in prop_values]

        primvar_api.CreatePrimvar(
            prop_name,
            usd_type,
            UsdGeom.Tokens.vertex,
        )\
        .Set(prop_values)

    return curve


def export_to_openusd(
    geojson_path: Path,
    output_path: Path,
    meters_per_unit: float,
    scale_factor: float,
    attributes_allowlist: list[str],
):
    log = get_logger()

    log.info("Reading GeoJSON data at %s", geojson_path)
    geojson_data = json.loads(geojson_path.read_text())

    final_data = parse_geojson_geometry(geojson_data, attributes_allowlist, log)

    stage: Usd.Stage = Usd.Stage.CreateNew(str(output_path))

    world = UsdGeom.Xform.Define(stage, "/world")

    if final_data.points.positions:
        create_points_prim(stage, world, final_data.points)
        log.info("Created points prim to host %i points", len(final_data.points.positions))

    if final_data.lines.positions:
        create_curve_prim(stage, world, final_data.lines)
        log.info("Created curve prim to host %i lines", len(final_data.lines.positions))

    UsdGeom.SetStageMetersPerUnit(stage, meters_per_unit)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
    stage.SetDefaultPrim(world.GetPrim())

    # Scale everything by the given factor.
    # I thought that setting the stage meters would be enough, but practically
    # speaking, it's not. See also:
    # https://www.sidefx.com/forum/topic/71925/?page=1#post-307752https://www.sidefx.com/forum/topic/71925/?page=1#post-307752
    points_scale_op = world.AddScaleOp()
    points_scale_op.Set(Gf.Vec3f(scale_factor))

    stage.Save()
    log.info("Successfully exported USD stage at %s", output_path)
