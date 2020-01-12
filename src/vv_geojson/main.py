import os

import geo_utils


def main():
    geo = node.geometry()

    # geojson_path = '/Users/vvzen/Downloads/open-data-exploration/resources-390e24e5-c818-4967-b42c-29f343fb21c8-ancient-trees.geojson'
    geojson_path = os.path.join(
        os.path.abspath(os.path.dirname(__file__)), '..', 'test',
        'sample_files', 'continents.json')

    geojson_parser = geo_utils.GeoJSONParser(geo, geojson_path)

    geojson_parser.create_geo()


if __name__ == '__main__':
    main()
