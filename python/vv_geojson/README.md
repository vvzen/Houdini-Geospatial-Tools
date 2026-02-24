## python/vv-geojson

A basic Python library than enables you to easily create geometry in Houdini by loading GeoJSON data.

### Installation

Simply make this module available to your $PYTHONPATH in houdini.

One way to do this is to copy the `python/vv_geojson` folder (which contains the python package) to `$HOUDINI_USER_PREF_DIR/python3.11libs`.

If you're on macOS, `$HOUDINI_USER_PREF_DIR/python3.11libs` could become `/Users/$USER/Library/Preferences/houdini/20.5/python3.11libs`.

On Linux, it would be `/opt/hfs20.5.654/houdini/python3.11libs`

For more infos, see [https://www.sidefx.com/docs/houdini/hom/locations.html#disk](https://www.sidefx.com/docs/houdini/hom/locations.html#disk)

For example, on a default install of Houdini on Linux, you'd run something like this:

``` shell
cd /opt/hfs20.5
source houdini_setup
export PYTHONPATH=$HOME/dev/dataviz/Houdini-Geospatial-Tools/python:$PYTHONPATH
houdini -foreground
```

### Example usage
Create a Python node while in SOP, then inside it create a `GeoJSONParser` instance like this:

```python
import vv_geojson.geo_utils as vvgeoutils

geo = hou.pwd().geometry()

geojson_path = '~/Downloads/some-file.geojson'
geojson_parser = vvgeoutils.GeoJSONParser(geo, geojson_path)
geojson_parser.create_geo()
```

You can also specify an optional radius of the final geometry:

```
geojson_parser.create_geo(radius=200)
```

### Supported GeoJSON Features
- GeometryCollection
- MultiPolygon
- Polygon
- MultiPoint
- Point
- LineString
- MultiLineString (untested)


### Where to get the data
- https://geojson-maps.ash.ms

### Validate your data
If you're getting weird results inside Houdini, please feel free to open an issue and add the source file that you're trying to import, so that debugging will be easier. If want to double check that you GeoJSON files are written correctly and are using GPS coordinates I would suggest to use this website [http://geojson.io](http://geojson.io)
