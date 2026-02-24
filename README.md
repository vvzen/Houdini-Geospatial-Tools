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

A simple python library than enables you to easily create geometry in Houdini by loading GeoJSON data.
This is just an hobby project (less than 1K LOCs at the time of writing) but I hope it can help someone out there.

Tested under Houdini 20.5 and Python 3.11.
<br>
No additional python packages required.

Check the project [README](https://github.com/vvzen/Houdini-Geospatial-Tools/blob/main/python/vv_geojson/README.md) for more info.

## python/vv-openusd-geojson-exporter

A library + CLI (`vv-geojson-exporter`) to export GeoJSON files as OpenUSD geometry.

Check the project [README](https://github.com/vvzen/Houdini-Geospatial-Tools/blob/main/python/vv-openusd-geojson-exporter/README.md) for more info.
