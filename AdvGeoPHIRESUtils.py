import sys
import os
from os.path import exists
import hashlib
import numpy as np
from pprint import pprint
from datetime import datetime
import json
import jsons
from mysql.connector import connect, Error
from Parameter import Parameter, intParameter, boolParameter, floatParameter, strParameter, listParameter, OutputParameter, ReadParameter
from enum import Enum
from OptionList import ReservoirModel, FractureShape, ReservoirVolume

class AdvGeoPHIRESUtils():

    def DumpObjectAsJson(self, MyObject)->str:
        """
        The DumpObjectAsJson function accepts a Python object and returns a JSON string representation of that object.
        The function is useful for debugging purposes, as it allows you to dump an object's contents to the console in 
        a human-readable format.
    
        :param MyObject: Pass in the object that you want to convert into a json string
        :return: A string of the object in json format
        :doc-author: Malcolm Ross
        """
        jsons.suppress_warnings(True)
        return(jsons.dumps(MyObject, indent=4, sort_keys = True, supress_warnings=True))

    def  ReadParameterFromJson(self, dJson:dict):
        """
        The ReadParameterFromJson function reads a JSON string and updates the parameters of this class accordingly.
            
        Args: 
            dJson (dictionary): dictionary derived from encoding a JSON string. 
    
        :param self: Reference the class object itself
        :param dJson:dict: Pass the dictionary that is derived from encoding a json string to the function
        :return: The value of the parameter that is passed in
        :doc-author: Malcolm Ross
        """
        for item in dJson.items():
            if item[0] in self.ParameterDict:
                if isinstance(self.ParameterDict[item[0]], Parameter.floatParameter): val = float(item[1]['Value'])
                if isinstance(self.ParameterDict[item[0]], Parameter.intParameter): val = int(item[1]['Value'])
                if isinstance(self.ParameterDict[item[0]], Parameter.boolParameter): val = bool(item[1]['Value'])
                if isinstance(self.ParameterDict[item[0]], Parameter.strParameter): val = str(item[1]['Value'])
                self.ParameterDict[item[0]].value = val

    def read_JSONinput_file(self, fname:str, model, ReturnDict1):
        """
        The read_JSONinput_file function reads a JSON input file and returns a dictionary of parameters.  The function is called by the run_model function to read in the JSON input file.
        :param fname:str: Pass the name of the json file that contains the input parameters
        :param model: The container class of the application, giving access to everything else, including the logger
        :param ReturnDict1: Return the dictionary of parameters to the main function
        :return: A dictionary of parameterentry objects
        :doc-author: Malcolm Ross
        """
        model.logger.info("Init " + str(__name__))

        #read input data
        try:
            if exists(fname):
                content = []
                model.logger.info("Found filename: " + fname + " Proceeding with run using JSON input parameters from that file")
                with open(fname, encoding='UTF-8') as f:
                    if fname.upper().endswith('.JSON'):
                        dJson = json.load(f)
            else:
                model.logger.warn("File: "+  fname + "  not found - proceeding with default parameter run...")
                return

        except BaseException as ex:
            print (ex)
            model.logger.error("Error " + str(ex) + "using JSON filename:" + fname + " proceeding with default parameter run...")
            return

        if fname.upper().endswith('.JSON'):
            for item in dJson.items():
                PEntry = Parameter.ParameterEntry(item[0], str(item[1]['Value']), item[1]['Comment'])
                ReturnDict1[item[0]] = PEntry     #make the dictionary element with the key set to lowercase without spaces.  This should help the algorithm br more forgiving about finding thingsin the dictionary
    
        model.logger.info("Complete "+ str(__name__) + ": " + sys._getframe().f_code.co_name)

    def CheckForExistingResult(self, model, object)->str:
        model.logger.info("Init " + str(__name__))
        #convert the input parwmeters abd code to JSON and hash it
        KeyAsHash = self.CaculateHash(object.MyPath, object)

        #Now search the database for something that already has that hash.
        try:
            with connect(host="localhost", user="malcolm", password=".Carnot.", database="geophiresx") as connection:
                SQLCommand = ("SELECT value FROM geophiresx.objects where uniquekey = \'" + KeyAsHash + "\'")
                with connection.cursor() as cursor:
                    cursor.execute(SQLCommand)
                    row = cursor.fetchone()
                    if row != None: #we have a key, let's use it to populate the object then return the hash
                        dd = self.returnDictBtKey(model, KeyAsHash)
                        if not self.RestoreValuesFromDict(model, dd, object): return None    #try to restore the object - if it fails, make it seem like there was no object so the calculation will run again
                    else: KeyAsHash = None    #if it is not found, return none
        except Error as ex:
            print (ex)
            model.logger.error("Error " + str(ex) + "Checking the database for result. Proceeding as if we didn't find one.")
            return None

        #model.logger.info("Complete "+ str(__name__) + ": " + sys._getframe().f_code.co_name)
        return KeyAsHash

    def store_result(self, model, object)->str:
        model.logger.info("Init " + str(__name__))

        #convert the input parwmeters abd code to JSON and hash it
        KeyAsHash = self.CaculateHash(object.MyPath, object)

        #Now we have the unique key based on the inputs and the code.  We now need get the object we want to store in a form we can store it
        OutputAsJSON = self.DumpObjectAsJson(object)
        ValueToStore = str(OutputAsJSON)

        #set the other svalues we will store
        now = datetime.now() # current date and time
        sdate_time = str(now.strftime("%Y%m%d%H%M%S%f"))
        suser = str(os.getlogin())

        #now try to write those as a record in the database
        try:
            with connect(host="localhost", user="malcolm", password=".Carnot.", database="geophiresx") as connection:
                SQLCommand = "INSERT INTO geophiresx.objects(uniquekey,class, name, datetime, value) VALUES(%s,%s,%s,%s,%s)"
                Values = [KeyAsHash, object.MyClass, suser, sdate_time, ValueToStore]
                with connection.cursor() as cursor:
                    cursor.execute(SQLCommand, (KeyAsHash, object.MyClass, suser, sdate_time, ValueToStore))
                    connection.commit()
        except Error as ex:
            print (ex)
            model.logger.error("Error " + str(ex) + "writing into the database with the result. Proceeding as if we did.")
            return None
        
        model.logger.info("Complete "+ str(__name__) + ": " + sys._getframe().f_code.co_name)
        return KeyAsHash

    def returnDictBtKey(self, model, skey:str)->dict:
    #called like: key = returnDictBtKey(model, key)
        model.logger.info("Init " + str(__name__))
        #now try to read the record in the database
        try:
            with connect(host="localhost", user="malcolm", password=".Carnot.", database="geophiresx") as connection:
                SQLCommand = ("SELECT value FROM geophiresx.objects where uniquekey = \'" + skey + "\'")
                with connection.cursor() as cursor:
                    cursor.execute(SQLCommand)
                    row = cursor.fetchone()
                    if row != None:
                        dd = json.loads(row[0])
                        return dd      #if it is found, retun the key
                    else:
                        return {}            #if it is not found, return none
        except Error as ex:
            print (ex)
            model.logger.error("Error " + str(ex) + " getting the database for result. Proceeding as if we didn't find one.")
            return None

    def RestoreValuesFromDict(self, model,  dd:dict, object)->bool:
        #populate the object with the previously calculated results store in a dictionary that was returned from the database
        sclass = str(object.__class__)
        try:
            if "Reservoir" in sclass:
                model.reserv.ParameterDict[model.reserv.resoption.Name] = self.PopulateStructureFromDictEntry(model.reserv.resoption, dd["resoption"], True)
                model.reserv.ParameterDict[model.reserv.depth.Name] = self.PopulateStructureFromDictEntry(model.reserv.depth, dd["depth"], True)
                model.reserv.ParameterDict[model.reserv.Tmax.Name] = self.PopulateStructureFromDictEntry(model.reserv.Tmax, dd["Tmax"], True)
                model.reserv.ParameterDict[model.reserv.drawdp.Name] = self.PopulateStructureFromDictEntry(model.reserv.drawdp, dd["drawdp"], True)
                model.reserv.ParameterDict[model.reserv.numseg.Name] = self.PopulateStructureFromDictEntry(model.reserv.numseg, dd["numseg"], True)
                model.reserv.ParameterDict[model.reserv.gradient.Name] = self.PopulateStructureFromDictEntry(model.reserv.gradient, dd["gradient"], True)
                model.reserv.ParameterDict[model.reserv.layerthickness.Name] = self.PopulateStructureFromDictEntry(model.reserv.layerthickness, dd["layerthickness"], True)
                model.reserv.ParameterDict[model.reserv.resvoloption.Name] = self.PopulateStructureFromDictEntry(model.reserv.resvoloption, dd["resvoloption"], True)
                model.reserv.ParameterDict[model.reserv.fracshape.Name] = self.PopulateStructureFromDictEntry(model.reserv.fracshape, dd["fracshape"], True)
                model.reserv.ParameterDict[model.reserv.fracarea.Name] = self.PopulateStructureFromDictEntry(model.reserv.fracarea, dd["fracarea"], True)
                model.reserv.ParameterDict[model.reserv.fracheight.Name] = self.PopulateStructureFromDictEntry(model.reserv.fracheight, dd["fracheight"], True)
                model.reserv.ParameterDict[model.reserv.fracwidth.Name] = self.PopulateStructureFromDictEntry(model.reserv.fracwidth, dd["fracwidth"], True)
                model.reserv.ParameterDict[model.reserv.fracnumb.Name] = self.PopulateStructureFromDictEntry(model.reserv.fracnumb, dd["fracnumb"], True)
                model.reserv.ParameterDict[model.reserv.fracsep.Name] = self.PopulateStructureFromDictEntry(model.reserv.fracsep, dd["fracsep"], True)
                model.reserv.ParameterDict[model.reserv.resvol.Name] = self.PopulateStructureFromDictEntry(model.reserv.resvol, dd["resvol"], True)
                model.reserv.ParameterDict[model.reserv.waterloss.Name] = self.PopulateStructureFromDictEntry(model.reserv.waterloss, dd["waterloss"], True)
                model.reserv.ParameterDict[model.reserv.cprock.Name] = self.PopulateStructureFromDictEntry(model.reserv.cprock, dd["cprock"], True)
                model.reserv.ParameterDict[model.reserv.rhorock.Name] = self.PopulateStructureFromDictEntry(model.reserv.rhorock, dd["rhorock"], True)
                model.reserv.ParameterDict[model.reserv.krock.Name] = self.PopulateStructureFromDictEntry(model.reserv.krock, dd["krock"], True)
                model.reserv.ParameterDict[model.reserv.permrock.Name] = self.PopulateStructureFromDictEntry(model.reserv.permrock, dd["permrock"], True)
                model.reserv.ParameterDict[model.reserv.porrock.Name] = self.PopulateStructureFromDictEntry(model.reserv.porrock, dd["porrock"], True)
                model.reserv.ParameterDict[model.reserv.Tsurf.Name] = self.PopulateStructureFromDictEntry(model.reserv.Tsurf, dd["Tsurf"], True)

                #Results
                model.reserv.OutputParameterDict[model.reserv.fracsepcalc.Name] = self.PopulateStructureFromDictEntry(model.reserv.fracsepcalc, dd["fracsepcalc"], False)
                model.reserv.OutputParameterDict[model.reserv.fracnumbcalc.Name] = self.PopulateStructureFromDictEntry(model.reserv.fracnumbcalc, dd["fracnumbcalc"], False)
                model.reserv.OutputParameterDict[model.reserv.fracheightcalc.Name] = self.PopulateStructureFromDictEntry(model.reserv.fracheightcalc, dd["fracheightcalc"], False)
                model.reserv.OutputParameterDict[model.reserv.fracwidthcalc.Name] = self.PopulateStructureFromDictEntry(model.reserv.fracwidthcalc, dd["fracwidthcalc"], False)
                model.reserv.OutputParameterDict[model.reserv.fracareacalc.Name] = self.PopulateStructureFromDictEntry(model.reserv.fracareacalc, dd["fracareacalc"], False)
                model.reserv.OutputParameterDict[model.reserv.resvolcalc.Name] = self.PopulateStructureFromDictEntry(model.reserv.resvolcalc, dd["resvolcalc"], False)
                model.reserv.OutputParameterDict[model.reserv.Trock.Name] = self.PopulateStructureFromDictEntry(model.reserv.Trock, dd["Trock"], False)
                model.reserv.OutputParameterDict[model.reserv.InitialReservoirHeatContent.Name] = self.PopulateStructureFromDictEntry(model.reserv.InitialReservoirHeatContent, dd["InitialReservoirHeatContent"], False)
                model.reserv.OutputParameterDict[model.reserv.timevector.Name] = self.PopulateStructureFromDictEntry(model.reserv.timevector, dd["timevector"], False)
                model.reserv.OutputParameterDict[model.reserv.Tresoutput.Name] = self.PopulateStructureFromDictEntry(model.reserv.Tresoutput, dd["Tresoutput"], False)

                return True
        except Error as ex:
            print (ex)
            model.logger.error("Error " + str(ex) + " Restoring the values from the database to the object. Proceeding as if we didn't find the object in the database.")
            return False
        return False

    def PopulateStructureFromDictEntry(self, object, dd:dict, Input:bool)->any:
        #rehydrate the object based on values in the JSON-based dictionary - copy the original values for the object for those that don't change, and use the dictionary values for the ones that might have changed
        try:
            if Input:
                object.Provided = bool(dd["Provided"])
                object.Valid = bool(dd["Valid"])
                #ignore all the other parameters because that can't won't be changed by users.  The only failure here is when the CurrentUnits change...

            #different value types makes it a bit complicated
            if isinstance(object.value, float):
                object.value = float(dd["value"])
                if Input: return floatParameter(object.Name, value = object.value, Required=object.Required, Provided=object.Provided, Valid=object.Valid, ErrMessage=object.ErrMessage, InputComment=object.InputComment, ToolTipText=object.ToolTipText, UnitType=object.UnitType, PreferredUnits=object.PreferredUnits, CurrentUnits=object.CurrentUnits, UnitsMatch=object.UnitsMatch, DefaultValue=object.DefaultValue, Min=object.Min, Max=object.Max)
                else: return OutputParameter(object.Name, value = object.value, UnitType=object.UnitType, PreferredUnits=object.PreferredUnits, CurrentUnits=object.CurrentUnits, UnitsMatch=object.UnitsMatch)
            elif isinstance(object.value, int):
                object.value = int(dd["value"])
                if Input: return intParameter(object.Name, value = object.value, Required=object.Required, Provided=object.Provided, Valid=object.Valid, ErrMessage=object.ErrMessage, InputComment=object.InputComment, ToolTipText=object.ToolTipText, UnitType=object.UnitType, PreferredUnits=object.PreferredUnits, CurrentUnits=object.CurrentUnits, UnitsMatch=object.UnitsMatch, DefaultValue=object.DefaultValue, AllowableRange=object.AllowableRange)
                else: return OutputParameter(object.Name, value = object.value, UnitType=object.UnitType, PreferredUnits=object.PreferredUnits, CurrentUnits=object.CurrentUnits, UnitsMatch=object.UnitsMatch)
            elif isinstance(object.value, bool):
                object.value = bool(dd["value"])
                if Input: return boolParameter(object.Name, value = object.value, Required=object.Required, Provided=object.Provided, Valid=object.Valid, ErrMessage=object.ErrMessage, InputComment=object.InputComment, ToolTipText=object.ToolTipText, UnitType=object.UnitType, PreferredUnits=object.PreferredUnits, CurrentUnits=object.CurrentUnits, UnitsMatch=object.UnitsMatch, DefaultValue=object.DefaultValue)
                else: return OutputParameter(object.Name, value = object.value, UnitType=object.UnitType, PreferredUnits=object.PreferredUnits, CurrentUnits=object.CurrentUnits, UnitsMatch=object.UnitsMatch)
            elif isinstance(object.value, str):
                object.value = str(dd["value"])
                if Input: return strParameter(object.Name, value = object.value, Required=object.Required, Provided=object.Provided, Valid=object.Valid, ErrMessage=object.ErrMessage, InputComment=object.InputComment, ToolTipText=object.ToolTipText, UnitType=object.UnitType, PreferredUnits=object.PreferredUnits, CurrentUnits=object.CurrentUnits, UnitsMatch=object.UnitsMatch, DefaultValue=object.DefaultValue)
                else: return OutputParameter(object.Name, value = object.value, UnitType=object.UnitType, PreferredUnits=object.PreferredUnits, CurrentUnits=object.CurrentUnits, UnitsMatch=object.UnitsMatch)
            elif isinstance(object.value, list):
                object.value = list(dd["value"])
                if Input: return listParameter(object.Name, value = object.value, Required=object.Required, Provided=object.Provided, Valid=object.Valid, ErrMessage=object.ErrMessage, InputComment=object.InputComment, ToolTipText=object.ToolTipText, UnitType=object.UnitType, PreferredUnits=object.PreferredUnits, CurrentUnits=object.CurrentUnits, UnitsMatch=object.UnitsMatch, DefaultValue=object.DefaultValue, Min=object.Min, Max=object.Max)
                else: 
                    object.value = np.array(object.value)
                    return OutputParameter(object.Name, value = object.value, UnitType=object.UnitType, PreferredUnits=object.PreferredUnits, CurrentUnits=object.CurrentUnits, UnitsMatch=object.UnitsMatch)
            elif isinstance(object.value, Enum):  #Enums are even more complicated but only exist for input parameters
                if 'MULTIPLE_PARALLEL_FRACTURES' in dd["value"]: object.value = ReservoirModel.MULTIPLE_PARALLEL_FRACTURES
                elif 'LINEAR_HEAT_SWEEP' in dd["value"]: object.value = ReservoirModel.LINEAR_HEAT_SWEEP
                elif 'SINGLE_FRACTURE' in dd["value"]: object.value = ReservoirModel.SINGLE_FRACTURE
                elif 'ANNUAL_PERCENTAGE' in dd["value"]: object.value = ReservoirModel.ANNUAL_PERCENTAGE
                elif 'USER_PROVIDED_PROFILE' in dd["value"]: object.value = ReservoirModel.USER_PROVIDED_PROFILE
                elif 'TOUGH2_SIMULATOR' in dd["value"]: object.value = ReservoirModel.TOUGH2_SIMULATOR
                elif 'FRAC_NUM_SEP' in dd["value"]: object.value = ReservoirVolume.FRAC_NUM_SEP
                elif 'RES_VOL_FRAC_SEP' in dd["value"]: object.value = ReservoirVolume.RES_VOL_FRAC_SEP
                elif 'RES_VOL_FRAC_NUM' in dd["value"]: object.value = ReservoirVolume.RES_VOL_FRAC_NUM
                elif 'RES_VOL_ONLY' in dd["value"]: object.value = ReservoirVolume.RES_VOL_ONLY
                elif 'CIRCULAR_AREA' in dd["value"]: object.value = FractureShape.CIRCULAR_AREA
                elif 'CIRCULAR_DIAMETER' in dd["value"]: object.value = FractureShape.CIRCULAR_DIAMETER
                elif 'SQUARE' in dd["value"]: object.value = FractureShape.SQUARE
                else: object.value = FractureShape.RECTANGULAR
                return intParameter(object.Name, value = object.value, Required=object.Required, Provided=object.Provided, Valid=object.Valid, ErrMessage=object.ErrMessage, InputComment=object.InputComment, ToolTipText=object.ToolTipText, UnitType=object.UnitType, PreferredUnits=object.PreferredUnits, CurrentUnits=object.CurrentUnits, UnitsMatch=object.UnitsMatch, DefaultValue=object.DefaultValue, AllowableRange=object.AllowableRange) 
            else:
                object.value = dd["value"]
                if Input: return strParameter(object.Name, value = object.value, Required=object.Required, Provided=object.Provided, Valid=object.Valid, ErrMessage=object.ErrMessage, InputComment=object.InputComment, ToolTipText=object.ToolTipText, UnitType=object.UnitType, PreferredUnits=object.PreferredUnits, CurrentUnits=object.CurrentUnits, UnitsMatch=object.UnitsMatch, DefaultValue=object.DefaultValue)
                else: return OutputParameter(object.Name, value = object.value, UnitType=object.UnitType, PreferredUnits=object.PreferredUnits, CurrentUnits=object.CurrentUnits, UnitsMatch=object.UnitsMatch)
        except Error as ex:
            print (ex)
            return None
        return None

    def CaculateHash(self, code_path:str, object)->str:
        #convert the input parwmeters abd code to JSON and hash it
        OutputAsJSON = self.DumpObjectAsJson(object.ParameterDict)
        KeyAsHash = hashlib.blake2b(OutputAsJSON.encode())
        with open(code_path,'r', encoding='UTF-8') as f: code = f.read()
        KeyAsHash.update(bytes(code, 'utf-8'))
        KeyAsHash = KeyAsHash.hexdigest()
        return KeyAsHash