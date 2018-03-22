### WEM / HERE API Routing Tool
### Developed by Kayne Neigherbauer 2018 for WEM/WisDMA


import json, urllib2, urllib, arcpy, string, os
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
        return response

        
    #function to grab to user defined points of origin and destination
    #***needs to be implemented. Dummy pts in now****
        
    def getUserPoints():
        # test coordinates
        origin = [-88.989,45.733]
        destination = [-88,42.733]
        
        #arcpy.AddMessage((origin,destination))
        return (origin, destination)

            
    ## function to create areas to avoid which will be processed by the HERE API. Using arcpy graphic buffer around 511 incident points
    def bufferPoints(bufferDist):
        # Local variables:
        in_fc = "Database Connections\\own.WEMAPP.sde\\WEMAPP.WEM$OWN.Feeds_511\\WEMAPP.WEM$OWN.GetEvents"
##       
        with arcpy.da.SearchCursor(in_fc, ["SHAPE@XY","NavteqLinkId"]) as s_cur:
            points = []
            link_ids = []
            out_fc = os.path.join(arcpy.env.scratchWorkspace,"C:\\Users\\kayne.neigherbauer\\Documents\\ArcGIS\\Default.gdb\\GetEvents_GraphicBuffer")
            proj_fc = os.path.join(arcpy.env.scratchWorkspace,"C:\\Users\\kayne.neigherbauer\\Documents\\ArcGIS\\Default.gdb\\GetEvents_GraphicBuffer_proj")
            for row in s_cur:
                # if navteq link ID is present from 511 use it instead of buffered data
                if row[1] :
                    link_ids.append(row[1])
                # otherwise use buffer 
                elif row[0]:
                    # Process: Graphic Buffer
                    arcpy.GraphicBuffer_analysis(in_fc, out_fc, bufferDist, "SQUARE", "MITER", "10", "0 DecimalDegrees")
                    #project the buffer
                    sr = arcpy.SpatialReference(4326)
                    arcpy.Project_management(out_fc, proj_fc, sr)
            arcpy.AddMessage(link_ids)
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
        bound_boxes.pop()
        bound_boxes = string.join(bound_boxes,"")
        arcpy.AddMessage(bound_boxes)
        #return the bounding boxes of buffers
        return bound_boxes
    

    ## use HERE API for directions that avoid given areas from one waypoint to another
    def getHereDirs(waypoints,bound_boxes):
        #token = ""
        url = "https://route.cit.api.here.com/routing/7.2/"
        params = "{0}{1}{2}".format("calculateroute.json?waypoint0=geo!42.500,-88.611&waypoint1=geo!43.65,-88.594&mode=fastest;car;traffic:disabled&avoidareas=",bound_boxes,
        "&app_id=____________&app_code=____________&representation=display")
        arcpy.AddMessage("Retrieving directions from: {0}{1}".format(url,params))
        response = fetch(url,params)
        arcpy.AddMessage(response)


    arcpy.env.scratchWorkspace = arcpy.GetSystemEnvironment("TEMP")
    arcpy.env.overwriteOutput = True
    
    bufferDist = arcpy.GetParameterAsText(0)
    waypoints = getUserPoints()
    bound_boxes = bufferPoints(bufferDist)
    getHereDirs(waypoints,bound_boxes)       


if __name__ == "__main__":
    main()
