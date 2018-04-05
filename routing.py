### WEM / HERE API Routing Tool
### Developed by Kayne Neigherbauer 2018 for WEM/WisDMA

import json, arcpy, string, os, time, requests
from datetime import datetime, timedelta
import numpy as np

def main():
    ### define functions first, calls below ###


    #fucntion to form a web request and get response with url passed
    def fetch(url,payload):
        try:
            arcpy.AddMessage("Request Status from HERE API:")
            r = requests.get(url, params = payload, timeout=5, verify=False)
            #arcpy.AddMessage(r.url)
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
            #arcpy.AddMessage(wp_list)
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

    def processDateTime(dTime):
        arcpy.AddMessage("Input:")
        arcpy.AddMessage(dTime)
        arcpy.AddMessage("Processed:")
        dTFmt = datetime.strptime(dTime, "%m/%d/%Y %I:%M:%S %p")
        startTime = dTFmt
        dT = dTFmt.isoformat()
        arcpy.AddMessage(dT)
        return dT, startTime
        
        
    

    ## use HERE API for directions that avoid given areas from one waypoint to another
    def getHereDirs(waypoints,bound_boxes, dT):
            # parse waypoints and HERE API url and parameters
        params = {"mode":"fastest;car;traffic:enabled",
                  "avoidAreas": bound_boxes,
                  "representation": "display",
                  "instructionformat": "text",
                  "metricSystem": "imperial",
                  "avoidseasonalclosures" : "true",
                  "departure" : dT
                  }
        for i in range(0,len(waypoints)):
            params["waypoint"+str(i)] = "geo!{0},{1}".format(waypoints[i][0],waypoints[i][1])
        params["app_id"] = " "
        params["app_code"] = " "
        
        url = "https://route.cit.api.here.com/routing/7.2/calculateroute.json"
            # fetch via web request
        response = fetch(url,params)
        return response


    # process and display the route
    def processRoute(route,dT,startTime):
            # JSON shape data
        shape = route["response"]["route"][0]["shape"]
        parts = route["response"]["route"][0]["leg"][0]["maneuver"]
            #get and save text of route directions
        arcpy.SetProgressorLabel("Writing Directions to file...")
        text = "Depart at {0}\n".format(dT.replace("T"," "))
        totalSecs = 0
        for part in parts:
            travelTime = str(timedelta(seconds = part["travelTime"]))
            totalSecs += int(part["travelTime"])
            time = part["time"]
            newtime = time.rpartition("-")[0]
            timeStamp = datetime.strptime(newtime,"%Y-%m-%dT%H:%M:%S")
            inst = part["instruction"]
            text = "{0}Approximate Time: {1}\n".format(text,timeStamp.strftime("%H:%M"))
            text = "{0}{1} {2}{3}\n\n".format(text,inst,"Travel Time for Leg: ",travelTime)
        totalTime = timedelta(seconds = totalSecs)
        eta = startTime + totalTime
        text = "{0}\nEstimate Time of Arrival: {1}\nTotal Travel Time: {2}".format(text, eta,str(totalTime))
        
        with open("directions.txt", "w") as f:
            f.write(text)
        arcpy.SetProgressorLabel("Processing and Displaying Route...")
        pt_array = arcpy.Array()
        for pt in shape:
            pts = string.split(pt,",")
            point = arcpy.Point(float(pts[1]),float(pts[0]))
            pt_array.add(point)
            #set spatial reference and create a polyline
        sr = arcpy.SpatialReference(4326)
        route = arcpy.Polyline(pt_array, sr)
            # save polyline feature
        arcpy.CopyFeatures_management(route, "Route")
            # make it a layer
        route_lyr = arcpy.mapping.Layer("Route")
            # add to map dataframe
        arcpy.mapping.AddLayer(df, route_lyr)
            #style the layers based on a source layer files with same geom types
            #route lines
        updateLayer = arcpy.mapping.ListLayers(mxd, "Route", df)[0]
        styleLayer = arcpy.mapping.Layer("line.lyr")
        arcpy.mapping.UpdateLayer(df, updateLayer, styleLayer, True)
            #waypoints
        updateLayer = arcpy.mapping.ListLayers(mxd, "Waypoints", df)[0]
        styleLayer = arcpy.mapping.Layer("point.lyr")
        arcpy.mapping.UpdateLayer(df, updateLayer, styleLayer, True)
            #buffer polygons, just so it looks decent if needed
        updateLayer = arcpy.mapping.ListLayers(mxd, "GetEvents_GraphicBuffer_proj", df)[0]
        styleLayer = arcpy.mapping.Layer("polygon.lyr")
        arcpy.mapping.UpdateLayer(df, updateLayer, styleLayer, True)
            # refesh the map view and table of contents to display route
        arcpy.RefreshTOC()
        arcpy.RefreshActiveView()

        
    ## begin main function calls and variables ##
  
        #set environment workspace and other settings
    arcpy.env.workspace = "C:\\Users\\Kayne.Neigherbauer\\Documents\\ArcGIS\\Default.gdb"
    arcpy.env.overwriteOutput = True
    
        # current mxd
    mxd = arcpy.mapping.MapDocument("CURRENT")
        #mxd dataframe
    df = arcpy.mapping.ListDataFrames(mxd, "Layers")[0]
        # use inpute params
        # user specified buffer distance around 511 points
    bufferDist = arcpy.GetParameterAsText(0)
        # user input parameters for departure time and date
    dTime = arcpy.GetParameterAsText(2)
    
        # calls function that retrieves user origin and destination points
        #set progressor for some context
    arcpy.SetProgressorLabel("Gathering and Processing User Points...")
    waypoints = getUserPoints()

        #buffer 511 points
    arcpy.SetProgressorLabel("Buffering 511 Points...")
    avoid_areas = bufferPoints(bufferDist,df)

    dT, startTime = processDateTime(dTime)
    
        # fetch route from HERE API if waypoints exist
    arcpy.SetProgressorLabel("Retrieving Route from HERE API...")
    if waypoints:
        route = getHereDirs(waypoints,avoid_areas,dT)
        
        #process route and display on the map
    if route:
        processRoute(route,dT,startTime)

        #cleanup and clear env
    arcpy.ClearEnvironment("workspace")
                                 


if __name__ == "__main__":
    main()
