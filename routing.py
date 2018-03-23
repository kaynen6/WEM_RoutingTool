### WEM / HERE API Routing Tool
### Developed by Kayne Neigherbauer 2018 for WEM/WisDMA

import json, urllib2, urllib, arcpy, string, os, time
import numpy as np


def main():

    #fucntion to form a web request and get response with url passed
    def fetch(url,params):
        try:
            req = urllib2.Request(url+params)
            openReq = urllib2.urlopen(req)
        except urllib2.HTTPError as e:
            #print "Http Error", e.code
            response = "Http Error " + str(e.code)
        except urllib2.URLError as e:
            #print "URL Error", e.reason
            response = "URL Error " + str(e.reason)
        else:
            response = json.load(openReq)
            if "error" in response: arcpy.AddMessage(response)
        return response

        
    #function to grab to user defined points of origin and destination
    #***needs to be implemented. Dummy pts in now****
        
    def getUserPoints():
        start_fc = arcpy.GetParameterAsText(1)
        end_fc = arcpy.GetParameterAsText(2)
        with arcpy.da.SearchCursor(start_fc, "SHAPE@XY") as s_cur:
            for row in s_cur:
                s_x, s_y = row[0]
        with arcpy.da.SearchCursor(end_fc, "SHAPE@XY") as s_cur:
            for row in s_cur:
                e_x, e_y = row[0]
        origin = (float(s_y), float(s_x))
        destination = (float(e_y), float(e_x)) 
        arcpy.AddMessage(origin)
        arcpy.AddMessage(destination)
##      [-88.989,45.733]
##      [-88,42.733]
##      arcpy.AddMessage((origin,destination))
        return (origin, destination)

            
    ## function to create areas to avoid which will be processed by the HERE API. Using arcpy graphic buffer around 511 incident points
    def bufferPoints(bufferDist,df):
        # Local variables:
        in_fc = "Database Connections\\own.WEMAPP.sde\\WEMAPP.WEM$OWN.Feeds_511\\WEMAPP.WEM$OWN.GetEvents"
##       
        with arcpy.da.SearchCursor(in_fc, ["SHAPE@XY","NavteqLinkId"]) as s_cur:
            points = []
            link_ids = []
            out_fc = "GetEvents_GraphicBuffer" ##os.path.join(arcpy.env.scratchWorkspace,
            proj_fc = "GetEvents_GraphicBuffer_proj"
            for row in s_cur:
                # if navteq link ID is present from 511 use it instead of buffered data
                if row[1] :
                    link_ids.append(row[1])
                # otherwise use buffer 
                elif row[0]:
                    pass
        # Process: Graphic Buffer
        arcpy.GraphicBuffer_analysis(in_fc, out_fc, bufferDist, "SQUARE", "MITER", "10", "0 DecimalDegrees")
        #project the buffer
        sr = arcpy.SpatialReference(4326)
        arcpy.Project_management(out_fc, proj_fc, sr)
        #add it to the map for reference
        lyrFile = arcpy.mapping.Layer(proj_fc)
        arcpy.mapping.AddLayer(df, lyrFile)
        arcpy.RefreshTOC()
        # get points of a bounding rectangle for each buffered point
        rects = []
        with arcpy.da.SearchCursor(proj_fc, ["SHAPE@"]) as s_cur:
            for row in s_cur:
                if row[0]:
                    rects.append((row[0].hullRectangle.split(" ")))
                else:
                    arcpy.AddMessage("No Events at this time.")                   
        bound_boxes = []
        #format for HERE API Bounding Box
        for box in rects:
            #new_box = [(float(x)) for x in box]
            bound_boxes.append(box[1]+",")
            bound_boxes.append(box[0])
            bound_boxes.append(";")
            bound_boxes.append(box[5]+",")
            bound_boxes.append(box[4])
            bound_boxes.append("!")
        #remove trailing "!" separator
        if bound_boxes: bound_boxes.pop()
        # join bounding boxes into one string for API consumption
        bound_boxes = string.join(bound_boxes,"")
        #return the bounding boxes of buffers
        return bound_boxes, link_ids
    

    ## use HERE API for directions that avoid given areas from one waypoint to another
    def getHereDirs(waypoints,bound_boxes,link_ids):
        #token = ""
        arcpy.AddMessage(waypoints)
        wp1 = str(waypoints[0][0])+","+str(waypoints[0][1])
        wp2 = str(waypoints[1][0])+","+str(waypoints[1][1])
        url = "https://route.cit.api.here.com/routing/7.2/"
        params = "{0}{1}{2}{3}{4}{5}{6}".format("calculateroute.json?waypoint0=geo!",wp1,"&waypoint1=geo!",wp2,"&mode=fastest;car;traffic:disabled&avoidareas=",bound_boxes,
        "&app_id=____________&app_code=_____________&representation=display")
        arcpy.AddMessage("Retrieving directions from: {0}{1}".format(url,params))
        response = fetch(url,params)
        arcpy.AddMessage(response)
        return response
        
    def processRoute(route):
        
        shape = route["response"]["route"][0]["shape"]
        pt_array = arcpy.Array()
        for pt in shape:
            pts = string.split(pt,",")
            point = arcpy.Point(float(pts[1]),float(pts[0]))
            pt_array.add(point)
        sr = arcpy.SpatialReference(4326)
        route = arcpy.Polyline(pt_array, sr)
        arcpy.CopyFeatures_management(route, "route")
        route_lyr = arcpy.mapping.Layer("route")
        arcpy.mapping.AddLayer(df, route_lyr)
        arcpy.RefreshTOC()
        arcpy.RefreshActiveView()
  
    
    arcpy.env.workspace = "C:\\Users\\Kayne.Neigherbauer\\Documents\\ArcGIS\\Default.gdb"
    mxd = arcpy.mapping.MapDocument("CURRENT")
    arcpy.env.overwriteOutput = True
    df = arcpy.mapping.ListDataFrames(mxd, "Layers")[0]
    
    
    bufferDist = arcpy.GetParameterAsText(0)
    waypoints = getUserPoints()
    avoid_areas = bufferPoints(bufferDist,df)
    route = getHereDirs(waypoints,avoid_areas[0], avoid_areas[1])
    processRoute(route)

    #clear env
    arcpy.ClearEnvironment("workspace")
                                 


if __name__ == "__main__":
    main()
