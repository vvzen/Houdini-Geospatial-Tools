# Readme

This project allows you to take GeoJSON files in input and convert them to OpenUSD geometry.

## State

The library is currently pretty barebone (alpha state) and lacks support for many GeoJSON features, however the core architecture is set and allows to do basic exports from simple .geojson files.

I have created this CLI when working on a Data Visualization of the Car Crashes in San Francisco: [Through the Streets of San Francisco](https://valerioviperino.me/through-the-streets-of-sf). In that article you'll also find wider context of how useful it can be!

## Examples

The main CLI offered is `vv-geojson-exporter`.
Run `vv-geojson-exporter -h` to get a feeling of the current supported features.

To export a `my-file.geojson` into a `my-scene.usdc`, you can run:
```bash
vv-geojson-exporter \
    -i my-file.geojson \
    -o my-scene.usdc \
    -m 1 \
    -s 1000
```

The equivalent command using the full flags would be:
```bash
vv-geojson-exporter \
    --input my-file.geojson \
    --output my-scene.usdc \
    --meters-per-unit 1 \
    --scale-factor 1000
```

## Supported features

As of 2026-02-24, the GeoJSON features supported are:
- Point
- LineString
