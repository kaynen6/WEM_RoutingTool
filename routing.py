import json, urllib2, urllib, arcpy, string


def main():

    #fucntion to form a web request and get response with url passed
    def fetch(url):
        try:
            req = urllib2.Request(url)
            openReq = urllib2.urlopen(req)
        except urllib2.HTTPError as e:
            #print "Http Error", e.code
            arcpy.AddMessage("Http Error " + str(e.code))
            return None
        except urllib2.URLError as e:
            #print "URL Error", e.reason
            arcpy.AddMessage("URL Error " + str(e.reason))
            return None
        else:
            response = json.load(openReq)
            return response

        
    #function to grab to user defined points of origin and destination
    #***needs to be implemented. Dummy pts in now****
        
    def getUserPoints():
        # test coordinates
        origin = [-88.989,45.733]
        destination = [-88,42.733]
        
        arcpy.AddMessage(origin,destination)
        return (origin, destination)

    
    ## fucntion gets the 511 incident point data. Process buffer for area to avoid as well
    def get511Points():
        pts511 = []
        fc = arcpy.GetParameterAsText(0)
        with arcpy.da.SearchCursor(fc, ['Longitude','Latitude']) as sCur:
            for item in sCur:
                pts511.append(item)
        return pts511
        #for testing
##        with open('x:\\511pts.json','w') as f:
##            json.dump(pts511,f,indent=4)
            
    ## function to create areas to avoid which will be processed by the HERE API. Using arcpy graphic buffer around 511 incident points
    def bufferPoints():
        # Local variables:
        WEMAPP_WEM_OWN_GetEvents = "Database Connections\\own.WEMAPP.sde\\WEMAPP.WEM$OWN.Feeds_511\\WEMAPP.WEM$OWN.GetEvents"
        GetEvents_GraphicBuffer1 = os.path.join(arcpy.env.scratchWorkspace,"C:\\Users\\$$$$$$$\\Documents\\ArcGIS\\Default.gdb\\GetEvents_GraphicBuffer1")
        # Process: Graphic Buffer
        arcpy.GraphicBuffer_analysis(WEMAPP_WEM_OWN_GetEvents, GetEvents_GraphicBuffer1, "10 Miles", "SQUARE", "MITER", "10", "0 DecimalDegrees")        

    ## use HERE API for directions that avoid given areas from one waypoint to another
    def getHereDirs(waypoints,):
        token =
        url = "https://route.cit.api.here.com/routing/7.2/"
        params = "calculateroute.json?waypoint0=geo!42.500,-88.611&waypoint1=geo!43.65,-88.594&mode=fastest;car;traffic:disabled&avoidareas=43.3667431278,-88.4740263616;42.732875165,-87.606605385&app_id=$$$$$$&app_code=$$$&representation=display"
        arcpy.AddMessage("Retrieving directions from: ", url)
        response = fetch(url)
        arcpy.AddMessage(response)


    arcpy.env.scratchWorkspace = arcpy.GetSystemEnvironment("TEMP")

    bufferDist = arcpy.getParametersAsText(0)
    userCoords = getUserPoints()
    bufferPoints()
    getHereDirs(userCoords,)
      
    with open('x:\\routes', 'w') as f:
        json.dump(goodDirs,f)
    arcpy.JSONToFeatures_conversion('x:\\routes.json', routes)
    
                                 


if __name__ == "__main__":
    main()
