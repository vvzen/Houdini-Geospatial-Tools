import os
import sys
import pprint
import json
import math

pp = pprint.PrettyPrinter(indent=4)

file_path = hou.evalParm("./geojson_path")
mercator_checked = hou.evalParm("./use_mercator")
#file_path = "rome_streets_simplified.geojson"

map_width = hou.evalParm("./map_width")
map_height = map_width / 2

# houdini vars
node = hou.pwd()
geo = node.geometry()

# see https://en.wikipedia.org/wiki/Spherical_coordinate_system
def spherical_to_cartesian(lon, lat, radius):
    
    latitude = math.radians(lat)
    longitude = math.radians(lon)

    x = radius * math.sin(latitude) * math.cos(longitude)
    y = radius * math.sin(latitude) * math.sin(longitude)
    z = radius * math.cos(latitude)
    return x, y, z

# see https://stackoverflow.com/questions/14329691/convert-latitude-longitude-point-to-a-pixels-x-y-on-mercator-projection
def spherical_to_mercator(lon, lat, mapWidth, mapHeight):
    x = (lon + 180) * (mapWidth/360)
    latitude_radians = lat * math.pi / 180
    mercator_N = math.log(math.tan((math.pi / 4) + (latitude_radians / 2)))
    y = (mapHeight / 2) - (mapWidth * mercator_N / (math.pi * 2))
    
    return x, y, 0    

# grabbed from houdini geospatial tools
def createPrim(coords, openStatus):

    poly = geo.createPolygon()
    poly.setIsClosed(openStatus)

    for coord in coords:
        pt = createPt(coord)
        poly.addVertex(pt)

    return poly

DEBUG = 0

def print_header():
    global DEBUG
    print "\n"*10
    print "-"*60
    print "running main, {}".format(DEBUG)
    print "map width: {}".format(map_width)
    DEBUG += 1

def main():
    
    # load the geojson file
    with open(file_path) as f:
        geojson = json.load(f)
    
    # create the polygon that will host the points
    polygon = hou.Geometry.createPolygon(geo)
    polygon.setIsClosed(False)
    
    print "number of features: {}".format(len(geojson["features"]))
    
    # loop through geojson features in order to add points
    for index, feature in enumerate(geojson["features"][:]):
    
        # check if the user pressed Escape
        if hou.updateProgressAndCheckForInterrupt():
            break
            
        attribs = feature["properties"]
        
        #id = index
        #print "index: {}".format(index)
        
        try:
            feature_type = feature["geometry"]["type"]
        except TypeError:
            #print "type of feature not found, skipping.."
            #print "\tcurrent feature name: {}".format(feature_name)
            #print "\tfeature: {}".format(feature)
            continue
            
        coords_list = []
            
        if feature_type == "MultiLineString":
            coords_list = feature["geometry"]["coordinates"][0]
        elif feature_type == "LineString":
            coords_list = feature["geometry"]["coordinates"]
        else:
            if feature_type == "MultiPolygon":
            
                # create a polygon for each poly inside the multipolygon
                for polygons_array in feature["geometry"]["coordinates"]:
                
                    print "\nlen of polygons_array: "
                    print len(polygons_array)
                    
                    for polygon in polygons_array:
                    
                        print "\nlen of polygon: "
                        print len(polygon)
                        
                        poly = geo.createPolygon()
                        poly.setIsClosed(False)
                    
                        for coord in polygon:
                        
                            pt = geo.createPoint()
            
                            lat = coord[1]
                            lon = coord[0]
                            
                            if mercator_checked:
                                try:
                                    x, y, z = spherical_to_mercator(lon, lat, map_width, map_height)
                                except ValueError:
                                    print "skipping current point!"
                                    print "value error on given coords: {}, {}".format(lon, lat)
                                    continue
                            else:
                                x, y, z = spherical_to_cartesian(lon, lat, 1)
                                
                            pt.setPosition((x, y, z))
                            poly.addVertex(pt)
                        
                            print "lat: {}, lon: {}".format(lat, lon)
            else:
                print "Unrecognized property: {}".format(feature_type)
        
        # using example from http://www.sidefx.com/docs/houdini/hom/hou/Geometry#createPolygons
        
        if len(coords_list) > 0:
        
            print "coords_list: \n"
            print coords_list
        
            poly = geo.createPolygon()
            poly.setIsClosed(False)
    
            for coord in coords_list:
                pt = geo.createPoint()
            
                lat = coord[1]
                lon = coord[0]
            
                if mercator_checked:
                    x, y, z = spherical_to_mercator(lon, lat, map_width, map_height)
                else:
                    x, y, z = spherical_to_cartesian(lon, lat, 1)

                pt.setPosition((x, y, z))
                poly.addVertex(pt)

print_header()
main()
