# houdini-geojson
A OOP python library than enables you to easily create geometry in Houdini using GeoJSON data.

Tested under 17.5 and Python 2.7.
<br>
No additional python packages required.

# Installation
Simply make this module available to your $PYTHONPATH in houdini.

One way to do this is to copy the `src/vv_geojson` folder (which contains the python package) to `$HOUDINI_USER_PREF_DIR/python2.7libs`.

If you're on mac, `$HOUDINI_USER_PREF_DIR/python2.7libs` could become `/Users/$USER/Library/Preferences/houdini/17.5/python2.7libs`.

For more infos, see [https://www.sidefx.com/docs/houdini/hom/locations.html#disk](https://www.sidefx.com/docs/houdini/hom/locations.html#disk)

# Example usage
Create a Python node while in SOP,
 then create a `GeoJSONParser` instance like this:
 
```
import vv_geojson.geo_utils as vvgeoutils
reload(vvgeoutils)

geojson_path = '~/Downloads/my_geographical_data.geojson'
geojson_parser = vvgeoutils.GeoJSONParser(node.geometry(), geojson_path)
geojson_parser.create_geo()
```

# Supported Features
- GeometryCollection
- MultiPolygon
- Polygon
- MultiPoint
- Point