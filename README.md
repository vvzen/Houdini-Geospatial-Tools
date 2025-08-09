# Houdini Geospatial Tools

This repo is a collection of unordered notebooks, scripts and libraries that I've used in the last years to work with geospatial data in Houdini.
Please don't consider it as structured knowledge: it's just a formalized series of hacks that has proven useful enough to be reused in different dataviz projects.

A recap blog post is available here: http://valerioviperino.me/houdini/dem

## gdal-dtm-exporter

This simple CLI takes a .IMG Digital Terrain Model as input and spits out a 32bit floating point OpenEXR image.
This is written in Rust and uses the `GDAL` bindings, so you'll need both `cargo` and `gdal` installed.
See the `Readme.org` for more info.

## python/notebooks

`ipython` notebooks documenting different workflows.

Each notebook might require different dependencies, but generally you'll always need:
- `numpy==1.19.4`
- `matplotlib==3.3.3`
- `GDAL==3.2.0`

### Save_GeoTIFF_as_ply

Guides you from the loading of a (generally huge) DEM GeoTIFF to exporting samples of the elevation data, so that you don't have to deal with such a high resolution image if you don't need to.
If you're in Europe, a good source of DEM files is Copernicus: https://land.copernicus.eu/imagery-in-situ/eu-dem/eu-dem-v1.1

This can prove useful whenever you are exploring the data and want to do your core processing using numpy instead of houdini.

## python/vv-geojson
A very basic OOP python library than enables you to easily create geometry in Houdini by loading GeoJSON data.
This is just an hobby project (less than 1K LOCs at the time of writing) but I hope it can help someone out there.

Tested under Houdini 17.5 and Python 2.7.
<br>
No additional python packages required.

### Installation

Simply make this module available to your $PYTHONPATH in houdini.

One way to do this is to copy the `python/vv_geojson` folder (which contains the python package) to `$HOUDINI_USER_PREF_DIR/python2.7libs`.

If you're on mac, `$HOUDINI_USER_PREF_DIR/python2.7libs` could become `/Users/$USER/Library/Preferences/houdini/17.5/python2.7libs`.

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
