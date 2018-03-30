### WEM / HERE API Routing Tool
### Developed by Kayne Neigherbauer 2018 for WEM/WisDMA

import json, arcpy, string, os, time, requests
import numpy as np

def main():
    ### define functions first, calls below ###
    
    #fucntion to form a web request and get response with url passed
    def fetch(url,payload):
        try:
            arcpy.AddMessage("Request Status from HERE API:")
            r = requests.get(url, params = payload, timeout=5, verify=False)
            arcpy.AddMessage(r.url)
##            req = urllib2.Request(url+params)
##            openReq = urllib2.urlopen(req)
            if r.status_code == 200:
                response = r.json()
                arcpy.AddMessage(r.reason)
                return response
            else:
                r.raise_for_status()
                arcpy.AddMessage(r.reason)
        except requests.exceptions.HTTPError as e:
            error = "Http Error" 
            arcpy.AddMessage(error)
        except requests.exceptions.URLRequired as e:
            error = "URL Error" 
            arcpy.AddMessage(error)
        except requests.exceptions.ConnectionError as e:
            error = "Connection Error" 
            arcpy.AddMessage(error)
            arcpy.AddMessage(e.text)
        except requests.exceptions.RequestException as e:
            error = "Other Request Error" 
            arcpy.AddMessage(error)
        else:
            response = r.json()
            if "error" in response:
                arcpy.AddMessage(response["Error"])
            return response

        
    #function to grab to user defined points of origin and destination
    def getUserPoints():
        #get file info from tool dialog
        waypoints_fc = arcpy.GetParameterAsText(1)
        wp_list = []
        #cursor to get user points.
        #check for no values/multiple values and message user
        with arcpy.da.SearchCursor(waypoints_fc, "SHAPE@XY") as s_cur:
            for row in s_cur:
                s_x, s_y = row[0]
                wp_list.append((float(s_y), float(s_x)))
        if len(wp_list) < 2:
            arcpy.AddError("{0} has no features; Cannot calculate route.".format(waypoints_fc))
            return None
        else:
            arcpy.AddMessage(wp_list)
            return wp_list

    
    ## function to create areas to avoid which will be processed by the HERE API. Using arcpy graphic buffer around 511 incident points
    def bufferPoints(bufferDist,df):
        # Local variables:
        in_fc = "Database Connections\\own.WEMAPP.sde\\WEMAPP.WEM$OWN.Feeds_511\\WEMAPP.WEM$OWN.GetEvents"
        out_fc = "GetEvents_GraphicBuffer" 
        proj_fc = "GetEvents_GraphicBuffer_proj"
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
            bound_boxes.append(box[1]+",")
            bound_boxes.append(box[0])
            bound_boxes.append(";")
            bound_boxes.append(box[5]+",")
            bound_boxes.append(box[4])
            bound_boxes.append("!")
        #remove trailing "!" separator
        if bound_boxes:
            bound_boxes.pop()
        # join bounding boxes into one string for API consumption
        bound_boxes = string.join(bound_boxes,"")
        #return the bounding boxes of buffers
        return bound_boxes
    

    ## use HERE API for directions that avoid given areas from one waypoint to another
    def getHereDirs(waypoints,bound_boxes):
        # parse waypoints and HERE API url and parameters
        params = {"mode":"fastest;car;traffic:disabled",
                  "avoidAreas": bound_boxes,
                  "representation": "display",
                  "instructionformat": "text",
                  "metricSystem": "imperial",
                  "avoidseasonalclosures" : "true"
                  }
        for i in range(0,len(waypoints)):
            params["waypoint"+str(i)] = "geo!{0},{1}".format(waypoints[i][0],waypoints[i][1])
        params["app_id"] = " "
        params["app_code"] = " "
        
        url = "https://route.cit.api.here.com/routing/7.2/calculateroute.json"
        arcpy.AddMessage(params)
        # fetch via web request
        response = fetch(url,params)
        return response

    # process and display the route
    def processRoute(route):
        # JSON shape data
        shape = route["response"]["route"][0]["shape"]
        parts = route["response"]["route"][0]["leg"][0]["maneuver"]
        
        #get and save text of route directions
        text = ""
        for part in parts:
            inst = part["instruction"]
            text = text + inst + "\n"
        with open("directions.txt", "w") as f:
            f.write(text)
        # arcpy array
        pt_array = arcpy.Array()
        for pt in shape:
            pts = string.split(pt,",")
            point = arcpy.Point(float(pts[1]),float(pts[0]))
            pt_array.add(point)
        #set spatial reference and create a polyline
        sr = arcpy.SpatialReference(4326)
        route = arcpy.Polyline(pt_array, sr)
        # save polyline feature
        arcpy.CopyFeatures_management(route, "route")
        # make it a layer
        route_lyr = arcpy.mapping.Layer("route")
        # add to map dataframe
        arcpy.mapping.AddLayer(df, route_lyr)
        # refesh the map view and table of contents to display route
        arcpy.RefreshTOC()
        arcpy.RefreshActiveView()

        arcpy.SetProgressorLabel("Writing Directions to file...")

        
    ## begin main function calls and variables ##
  
    #set environment workspace and other settings
    arcpy.env.workspace = "C:\\Users\\Kayne.Neigherbauer\\Documents\\ArcGIS\\Default.gdb"
    arcpy.env.overwriteOutput = True
    
    # current mxd
    mxd = arcpy.mapping.MapDocument("CURRENT")
    #mxd dataframe
    df = arcpy.mapping.ListDataFrames(mxd, "Layers")[0]
    # user specified buffer distance around 511 points
    bufferDist = arcpy.GetParameterAsText(0)
    
    # calls function that retrieves user origin and destination points
    #set progressor for some context
    arcpy.SetProgressorLabel("Gathering and Processing User Points...")
    waypoints = getUserPoints()

    #buffer 511 points
    arcpy.SetProgressorLabel("Buffering 511 Points...")
    avoid_areas = bufferPoints(bufferDist,df)

    # fetch route from HERE API if waypoints exist
    arcpy.SetProgressorLabel("Retrieving Route from HERE API...")
    if waypoints:
        route = getHereDirs(waypoints,avoid_areas)
        
    #process route and display on the map
    if route:
        arcpy.SetProgressorLabel("Processing and Displaying Route...")
        processRoute(route)

    #cleanup and clear env
    arcpy.ClearEnvironment("workspace")
                                 


if __name__ == "__main__":
    main()
