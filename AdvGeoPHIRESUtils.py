# copyright, 2023, Malcolm I Ross
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
from OptionList import Configuration, ReservoirModel, FractureShape, ReservoirVolume, EndUseOptions, PowerPlantType, EconomicModel, WellDrillingCostCorrelation, WorkingFluid, Configuration
from cryptography.fernet import Fernet
import zlib

def encrypt(message: bytes, key: bytes) -> bytes:
    return Fernet(key).encrypt(message)

def decrypt(token: bytes, key: bytes) -> bytes:
    return Fernet(key).decrypt(token)

def write_key():
    key = Fernet.generate_key() # Generates the key
    with open("key.key", "wb") as key_file: # Opens the file the key is to be written to
        key_file.write(key) # Writes the key

def load_key():
    return open("key.key", "rb").read() #Opens the file, reads and returns the key stored in the file

class AdvGeoPHIRESUtils():
    UseDatabase = False
    def RunStoredProcedure(self, store_procedure_name:str, parameters:list)->list:
        if not self.UseDatabase: return None
        res = details = warnings = obj = None
        with connect(host="localhost", user="malcolm", password=".Carnot.", database="geophiresx") as connection:
            try:
                obj = connection.cursor()
                res = obj.callproc(store_procedure_name, parameters)
                connection.commit()
                for result in obj.stored_results():
                    details = result.fetchall()
                    warnings = result.fetchwarnings() 
                obj.close()
                connection.close()
            except connection.Error as err:
                print("Something went wrong: {}".format(err))
        return (details)

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
        if not self.UseDatabase: return None
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
                        model.logger.info("Restored " + object.MyClass + " using hash =" + KeyAsHash)
                        print("Restored " + object.MyClass + " using hash =" + KeyAsHash)
                    else:
                        model.logger.info("Could not restore " + object.MyClass + " using hash =" + KeyAsHash)
                        print("Could not restore " + object.MyClass + " using hash =" + KeyAsHash)
                        KeyAsHash = None    #if it is not found, return none
        except Error as ex:
            print (ex)
            model.logger.error("Error " + str(ex) + "Checking the database for result. Proceeding as if we didn't find one.")
            return None

        #model.logger.info("Complete "+ str(__name__) + ": " + sys._getframe().f_code.co_name)
        return KeyAsHash

    def store_result(self, model, object)->str:
        if not self.UseDatabase: return None
        model.logger.info("Init " + str(__name__))

        #handle encrption stuff
        key = ""
        if exists("key.key"): key = load_key() # Loads the key and stores it in a variable
        else: 
            write_key() # Writes the key to the key file
            key = load_key() # Loads the key and stores it in a variable
        f = Fernet(key)

        #convert the input parameters abd code to JSON and hash it
        KeyAsHash = self.CaculateHash(object.MyPath, object)

        #Now we have the unique key based on the inputs and the code.  We now need get the object we want to store in a form we can store it
        OutputAsJSON = self.DumpObjectAsJson(object)
        ValueToStore = str(OutputAsJSON)

        encrypted_message = f.encrypt(ValueToStore.encode())
        compressed_message = zlib.compress(encrypted_message, -1)

        #set the other svalues we will store
        now = datetime.now() # current date and time
        sdate_time = str(now.strftime("%Y%m%d%H%M%S%f"))
        suser = str(os.getlogin())

        #now try to write those as a record in the database
        try:
            with connect(host="localhost", user="malcolm", password=".Carnot.", database="geophiresx") as connection:
                SQLCommand = "INSERT INTO geophiresx.objects(uniquekey,class, name, datetime, value, ze_value) VALUES(%s,%s,%s,%s,%s, %s)"
                with connection.cursor() as cursor:
                    cursor.execute(SQLCommand, (KeyAsHash, object.MyClass, suser, sdate_time, ValueToStore, compressed_message))
                    connection.commit()
                    model.logger.info("Stored " + object.MyClass + " under hash =" + KeyAsHash)
                    print("Stored " + object.MyClass + " under hash =" + KeyAsHash)
        except Error as ex:
            print (ex)
            model.logger.error("Error " + str(ex) + "writing into the database with the result. Proceeding as if we did.")
            return -1
        
        model.logger.info("Complete "+ str(__name__) + ": " + sys._getframe().f_code.co_name)
        return KeyAsHash

    def returnDictBtKey(self, model, skey:str)->dict:
        if not self.UseDatabase: return {}
    #called like: key = returnDictByKey(model, key)
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
            return {}

    def RestoreValuesFromDict(self, model,  dd:dict, object)->bool:
        #populate the object with the previously calculated results store in a dictionary that was returned from the database
        sclass = str(object.__class__)
        try:
            if "Reservoir" in sclass: #Try to rehydrate the Reservoir object
                for key in model.reserv.ParameterDict: model.reserv.ParameterDict[key] = self.PopulateStructureFromDict(model.reserv.ParameterDict[key], dd)
                for key in model.reserv.OutputParameterDict: model.reserv.OutputParameterDict[key] = self.PopulateStructureFromDict(model.reserv.OutputParameterDict[key], dd)

            elif "WellBores" in sclass: #Try to rehydrate the WellBores object
                for key in model.wellbores.ParameterDict: model.wellbores.ParameterDict[key] = self.PopulateStructureFromDict(model.wellbores.ParameterDict[key], dd)
                for key in model.wellbores.OutputParameterDict: model.wellbores.OutputParameterDict[key] = self.PopulateStructureFromDict(model.wellbores.OutputParameterDict[key], dd)

            elif "SurfacePlant" in sclass: #Try to rehydrate the SurfacePlant object
                for key in model.surfaceplant.ParameterDict: model.surfaceplant.ParameterDict[key] = self.PopulateStructureFromDict(model.surfaceplant.ParameterDict[key], dd)
                for key in model.surfaceplant.OutputParameterDict: model.surfaceplant.OutputParameterDict[key] = self.PopulateStructureFromDict(model.surfaceplant.OutputParameterDict[key], dd)
                
            elif "<class 'Economics.Economics'>" in sclass:
                for key in model.economics.ParameterDict: model.economics.ParameterDict[key] = self.PopulateStructureFromDict(model.economics.ParameterDict[key], dd)
                for key in model.economics.OutputParameterDict: model.economics.OutputParameterDict[key] = self.PopulateStructureFromDict(model.economics.OutputParameterDict[key], dd)

            elif "EconomicsAddOns" in sclass:
                for key in model.addeconomics.ParameterDict: model.addeconomics.ParameterDict[key] = self.PopulateStructureFromDict(model.addeconomics.ParameterDict[key], dd)
                for key in model.addeconomics.OutputParameterDict: model.addeconomics.OutputParameterDict[key] = self.PopulateStructureFromDict(model.addeconomics.OutputParameterDict[key], dd)

            elif "EconomicsCCUS" in sclass:
                for key in model.ccuseconomics.ParameterDict: model.ccuseconomics.ParameterDict[key] = self.PopulateStructureFromDict(model.ccuseconomics.ParameterDict[key], dd)
                for key in model.ccuseconomics.OutputParameterDict: model.ccuseconomics.OutputParameterDict[key] = self.PopulateStructureFromDict(model.ccuseconomics.OutputParameterDict[key], dd)

            elif "EconomicsS_DAC_GT" in sclass:
                for key in model.sdacgteconomics.ParameterDict: model.sdacgteconomics.ParameterDict[key] = self.PopulateStructureFromDict(model.sdacgteconomics.ParameterDict[key], dd)
                for key in model.sdacgteconomics.OutputParameterDict: model.sdacgteconomics.OutputParameterDict[key] = self.PopulateStructureFromDict(model.sdacgteconomics.OutputParameterDict[key], dd)

            return True
        except Error as ex:
            print (ex)
            model.logger.error("Error " + str(ex) + " Restoring the values from the database to the object. Proceeding as if we didn't find the object in the database.")
            return False
        return False

    def PopulateStructureFromDict(self, object, dd:dict)->any:
        #rehydrate the object based on values in the JSON-based dictionary - copy the original values for the object for those that don't change, and use the dictionary values for the ones that might have changed

        #dd is a dictionary of dictionaries, we need to iterate thru all the entries looking for a match to the one we are looking for, setting dd to the right dictionary once we find it
        for key in dd:
            valdict = dd[key]
            if not isinstance(valdict, dict): continue   #skip it if it is a not a dict
            if not "value" in valdict: continue    #skip is there is a "value" entry - if there isn't, it must not be valid
            if not "Name" in valdict: continue    #skip is there is a "Name" entry - if there isn't, it must not be valid
            if valdict["Name"] == object.Name: 
                ddx = valdict
                break

        try:
            if isinstance(object, OutputParameter):
                if isinstance(object.value, float):
                   if '[' in str(ddx["value"]): object.value = list(ddx["value"])    #if it has "[" it must be a list
                   else: object.value = float(ddx["value"])
                elif isinstance(object.value, int): object.value = int(ddx["value"])
                elif isinstance(object.value, bool): object.value = bool(ddx["value"])
                elif isinstance(object.value, str): object.value = str(ddx["value"])
                elif isinstance(object.value, list): object.value = np.array(list(ddx["value"]))
                else: object.value = ddx["value"]
                return OutputParameter(object.Name, value = object.value, UnitType=object.UnitType, PreferredUnits=object.PreferredUnits, CurrentUnits=object.CurrentUnits, UnitsMatch=object.UnitsMatch)
            else:
                if "Provided" in ddx: object.Provided = bool(ddx["Provided"])
                if "Valid" in ddx:object.Valid = bool(ddx["Valid"])
                #ignore all the other parameters because that can't won't be changed by users.  The only failure here is when the CurrentUnits change...

                #different value types makes it a bit complicated
                if isinstance(object, floatParameter):
                    if not isinstance (ddx["value"], list): object.value = float(ddx["value"])
                    else: object.value = list(ddx["value"])
                    return floatParameter(object.Name, value = object.value, Required=object.Required, Provided=object.Provided, Valid=object.Valid, ErrMessage=object.ErrMessage, InputComment=object.InputComment, ToolTipText=object.ToolTipText, UnitType=object.UnitType, PreferredUnits=object.PreferredUnits, CurrentUnits=object.CurrentUnits, UnitsMatch=object.UnitsMatch, DefaultValue=object.DefaultValue, Min=object.Min, Max=object.Max)

                elif isinstance(object, intParameter):    # int is complicated becasue it can be a int or an enum
                    if isinstance(object.value, Enum):  #Enums are even more complicated but only exist for input parameters
                        if isinstance(object.value, ReservoirModel): object.value = ReservoirModel[object.value.name]
                        elif isinstance(object.value, ReservoirVolume): object.value = ReservoirVolume[object.value.name]
                        elif isinstance(object.value, FractureShape): object.value = FractureShape[object.value.name]
                        elif isinstance(object.value, EndUseOptions): object.value = EndUseOptions[object.value.name]
                        elif isinstance(object.value, PowerPlantType): object.value = PowerPlantType[object.value.name]
                        elif isinstance(object.value, EconomicModel): object.value = EconomicModel[object.value.name]
                        elif isinstance(object.value, WellDrillingCostCorrelation): object.value = WellDrillingCostCorrelation[object.value.name]
                        elif isinstance(object.value, WorkingFluid): object.value = WorkingFluid[object.value.name]
                        elif isinstance(object.value, Configuration):  object.value = Configuration[object.value.name]
                    else: object.value = int(ddx["value"])
                    return intParameter(object.Name, value = object.value, Required=object.Required, Provided=object.Provided, Valid=object.Valid, ErrMessage=object.ErrMessage, InputComment=object.InputComment, ToolTipText=object.ToolTipText, UnitType=object.UnitType, PreferredUnits=object.PreferredUnits, CurrentUnits=object.CurrentUnits, UnitsMatch=object.UnitsMatch, DefaultValue=object.DefaultValue, AllowableRange=object.AllowableRange)

                elif isinstance(object, boolParameter):
                    object.value = bool(ddx["value"])
                    return boolParameter(object.Name, value = object.value, Required=object.Required, Provided=object.Provided, Valid=object.Valid, ErrMessage=object.ErrMessage, InputComment=object.InputComment, ToolTipText=object.ToolTipText, UnitType=object.UnitType, PreferredUnits=object.PreferredUnits, CurrentUnits=object.CurrentUnits, UnitsMatch=object.UnitsMatch, DefaultValue=object.DefaultValue)

                elif isinstance(object, strParameter):
                    object.value = str(ddx["value"])
                    return strParameter(object.Name, value = object.value, Required=object.Required, Provided=object.Provided, Valid=object.Valid, ErrMessage=object.ErrMessage, InputComment=object.InputComment, ToolTipText=object.ToolTipText, UnitType=object.UnitType, PreferredUnits=object.PreferredUnits, CurrentUnits=object.CurrentUnits, UnitsMatch=object.UnitsMatch, DefaultValue=object.DefaultValue)

                elif isinstance(object, listParameter):
                    object.value = list(ddx["value"])
                    return listParameter(object.Name, value = object.value, Required=object.Required, Provided=object.Provided, Valid=object.Valid, ErrMessage=object.ErrMessage, InputComment=object.InputComment, ToolTipText=object.ToolTipText, UnitType=object.UnitType, PreferredUnits=object.PreferredUnits, CurrentUnits=object.CurrentUnits, UnitsMatch=object.UnitsMatch, DefaultValue=object.DefaultValue, Min=object.Min, Max=object.Max)

                else:
                    object.value = ddx["value"]
                    return strParameter(object.Name, value = object.value, Required=object.Required, Provided=object.Provided, Valid=object.Valid, ErrMessage=object.ErrMessage, InputComment=object.InputComment, ToolTipText=object.ToolTipText, UnitType=object.UnitType, PreferredUnits=object.PreferredUnits, CurrentUnits=object.CurrentUnits, UnitsMatch=object.UnitsMatch, DefaultValue=object.DefaultValue)

        except Error as ex:
            print (ex)
            return None

    def CaculateHash(self, code_path:str, object)->str:
        #convert the input parwmeters abd code to JSON and hash it
        OutputAsJSON = self.DumpObjectAsJson(object.ParameterDict)
        KeyAsHash = hashlib.blake2b(OutputAsJSON.encode())
        with open(code_path,'r', encoding='UTF-8') as f: code = f.read()
        KeyAsHash.update(bytes(code, 'utf-8'))
        KeyAsHash = KeyAsHash.hexdigest()
        return KeyAsHash

    def SmartCalculate(self, model, object):
        key = self.CheckForExistingResult(model, object)   #This will rehydrate the object if it is found
        if key == None:
            object.Calculate(model)    #run calculation because there was nothing in the database
            
            #store the calculated result and associated object parameters in the database
            resultkey = self.store_result(model, object)
            if resultkey == -1:
                print("Failed To Store "+ str(object.MyClass) + " " + object.MyPath)
                self.logger.warn("Failed To Store "+ str(object.MyClass) + " " + object.MyPath)
            elif resultkey == None:
                pass #Do nothing - not using database
            else:
                print("stored " + str(object.MyClass) + " " + object.MyPath + " as: " + resultkey)
                self.logger.info("stored " + str(object.MyClass) + " " + object.MyPath + " as: " + resultkey)