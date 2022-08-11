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
from OptionList import ReservoirModel, FractureShape, ReservoirVolume, EndUseOptions, PowerPlantType, EconomicModel, WellDrillingCostCorrelation

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
                        model.logger.info("Could not restored " + object.MyClass + " using hash =" + KeyAsHash)
                        print("Could not restored " + object.MyClass + " using hash =" + KeyAsHash)
                        KeyAsHash = None    #if it is not found, return none
        except Error as ex:
            print (ex)
            model.logger.error("Error " + str(ex) + "Checking the database for result. Proceeding as if we didn't find one.")
            return None

        #model.logger.info("Complete "+ str(__name__) + ": " + sys._getframe().f_code.co_name)
        return KeyAsHash

    def store_result(self, model, object)->str:
        model.logger.info("Init " + str(__name__))

        #handle encrption stuff
        key = ""
        if exists("key.key"): key = load_key() # Loads the key and stores it in a variable
        else: 
            write_key() # Writes the key to the key file
            key = load_key() # Loads the key and stores it in a variable
        f = Fernet(key)

        #convert the input parwmeters abd code to JSON and hash it
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
        except Error as ex:
            print (ex)
            model.logger.error("Error " + str(ex) + "writing into the database with the result. Proceeding as if we did.")
            return None
        
        model.logger.info("Stored " + object.MyClass + " under hash =" + KeyAsHash)
        print("Stored " + object.MyClass + " under hash =" + KeyAsHash)
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
            if "Reservoir" in sclass: #Try to rehydrate the Reservoir object
                model.reserv.ParameterDict[model.reserv.resoption.Name] = self.PopulateStructureFromDictEntry(model.reserv.resoption, dd["resoption"])
                model.reserv.ParameterDict[model.reserv.depth.Name] = self.PopulateStructureFromDictEntry(model.reserv.depth, dd["depth"])
                model.reserv.ParameterDict[model.reserv.Tmax.Name] = self.PopulateStructureFromDictEntry(model.reserv.Tmax, dd["Tmax"])
                model.reserv.ParameterDict[model.reserv.drawdp.Name] = self.PopulateStructureFromDictEntry(model.reserv.drawdp, dd["drawdp"])
                model.reserv.ParameterDict[model.reserv.numseg.Name] = self.PopulateStructureFromDictEntry(model.reserv.numseg, dd["numseg"])
                model.reserv.ParameterDict[model.reserv.gradient.Name] = self.PopulateStructureFromDictEntry(model.reserv.gradient, dd["gradient"])
                model.reserv.ParameterDict[model.reserv.layerthickness.Name] = self.PopulateStructureFromDictEntry(model.reserv.layerthickness, dd["layerthickness"])
                model.reserv.ParameterDict[model.reserv.resvoloption.Name] = self.PopulateStructureFromDictEntry(model.reserv.resvoloption, dd["resvoloption"])
                model.reserv.ParameterDict[model.reserv.fracshape.Name] = self.PopulateStructureFromDictEntry(model.reserv.fracshape, dd["fracshape"])
                model.reserv.ParameterDict[model.reserv.fracarea.Name] = self.PopulateStructureFromDictEntry(model.reserv.fracarea, dd["fracarea"])
                model.reserv.ParameterDict[model.reserv.fracheight.Name] = self.PopulateStructureFromDictEntry(model.reserv.fracheight, dd["fracheight"])
                model.reserv.ParameterDict[model.reserv.fracwidth.Name] = self.PopulateStructureFromDictEntry(model.reserv.fracwidth, dd["fracwidth"])
                model.reserv.ParameterDict[model.reserv.fracnumb.Name] = self.PopulateStructureFromDictEntry(model.reserv.fracnumb, dd["fracnumb"])
                model.reserv.ParameterDict[model.reserv.fracsep.Name] = self.PopulateStructureFromDictEntry(model.reserv.fracsep, dd["fracsep"])
                model.reserv.ParameterDict[model.reserv.resvol.Name] = self.PopulateStructureFromDictEntry(model.reserv.resvol, dd["resvol"])
                model.reserv.ParameterDict[model.reserv.waterloss.Name] = self.PopulateStructureFromDictEntry(model.reserv.waterloss, dd["waterloss"])
                model.reserv.ParameterDict[model.reserv.cprock.Name] = self.PopulateStructureFromDictEntry(model.reserv.cprock, dd["cprock"])
                model.reserv.ParameterDict[model.reserv.rhorock.Name] = self.PopulateStructureFromDictEntry(model.reserv.rhorock, dd["rhorock"])
                model.reserv.ParameterDict[model.reserv.krock.Name] = self.PopulateStructureFromDictEntry(model.reserv.krock, dd["krock"])
                model.reserv.ParameterDict[model.reserv.permrock.Name] = self.PopulateStructureFromDictEntry(model.reserv.permrock, dd["permrock"])
                model.reserv.ParameterDict[model.reserv.porrock.Name] = self.PopulateStructureFromDictEntry(model.reserv.porrock, dd["porrock"])
                model.reserv.ParameterDict[model.reserv.Tsurf.Name] = self.PopulateStructureFromDictEntry(model.reserv.Tsurf, dd["Tsurf"])

                #Results - used by other objects or printed in output downstream
                model.reserv.OutputParameterDict[model.reserv.fracsepcalc.Name] = self.PopulateStructureFromDictEntry(model.reserv.fracsepcalc, dd["fracsepcalc"])
                model.reserv.OutputParameterDict[model.reserv.fracnumbcalc.Name] = self.PopulateStructureFromDictEntry(model.reserv.fracnumbcalc, dd["fracnumbcalc"])
                model.reserv.OutputParameterDict[model.reserv.fracheightcalc.Name] = self.PopulateStructureFromDictEntry(model.reserv.fracheightcalc, dd["fracheightcalc"])
                model.reserv.OutputParameterDict[model.reserv.fracwidthcalc.Name] = self.PopulateStructureFromDictEntry(model.reserv.fracwidthcalc, dd["fracwidthcalc"])
                model.reserv.OutputParameterDict[model.reserv.fracareacalc.Name] = self.PopulateStructureFromDictEntry(model.reserv.fracareacalc, dd["fracareacalc"])
                model.reserv.OutputParameterDict[model.reserv.resvolcalc.Name] = self.PopulateStructureFromDictEntry(model.reserv.resvolcalc, dd["resvolcalc"])
                model.reserv.OutputParameterDict[model.reserv.Trock.Name] = self.PopulateStructureFromDictEntry(model.reserv.Trock, dd["Trock"])
                model.reserv.OutputParameterDict[model.reserv.cpwater.Name] = self.PopulateStructureFromDictEntry(model.reserv.cpwater, dd["cpwater"])
                model.reserv.OutputParameterDict[model.reserv.rhowater.Name] = self.PopulateStructureFromDictEntry(model.reserv.rhowater, dd["rhowater"])
                model.reserv.OutputParameterDict[model.reserv.averagegradient.Name] = self.PopulateStructureFromDictEntry(model.reserv.averagegradient, dd["averagegradient"])
                model.reserv.OutputParameterDict[model.reserv.InitialReservoirHeatContent.Name] = self.PopulateStructureFromDictEntry(model.reserv.InitialReservoirHeatContent, dd["InitialReservoirHeatContent"])
                model.reserv.OutputParameterDict[model.reserv.timevector.Name] = self.PopulateStructureFromDictEntry(model.reserv.timevector, dd["timevector"])
                model.reserv.OutputParameterDict[model.reserv.Tresoutput.Name] = self.PopulateStructureFromDictEntry(model.reserv.Tresoutput, dd["Tresoutput"])

            elif "WellBores" in sclass: #Try to rehydrate the WellBores object
                model.wellbores.ParameterDict[model.wellbores.nprod.Name] = self.PopulateStructureFromDictEntry(model.wellbores.nprod, dd["nprod"])
                model.wellbores.ParameterDict[model.wellbores.ninj.Name] =  self.PopulateStructureFromDictEntry(model.wellbores.ninj, dd["ninj"])
                model.wellbores.ParameterDict[model.wellbores.prodwelldiam.Name] = self.PopulateStructureFromDictEntry(model.wellbores.prodwelldiam, dd["prodwelldiam"])
                model.wellbores.ParameterDict[model.wellbores.injwelldiam.Name] = self.PopulateStructureFromDictEntry(model.wellbores.injwelldiam, dd["injwelldiam"])
                model.wellbores.ParameterDict[model.wellbores.rameyoptionprod.Name] = self.PopulateStructureFromDictEntry(model.wellbores.rameyoptionprod, dd["rameyoptionprod"])
                model.wellbores.ParameterDict[model.wellbores.tempdropprod.Name] = self.PopulateStructureFromDictEntry(model.wellbores.tempdropprod, dd["tempdropprod"])
                model.wellbores.ParameterDict[model.wellbores.tempgaininj.Name] = self.PopulateStructureFromDictEntry(model.wellbores.tempgaininj, dd["tempgaininj"])
                model.wellbores.ParameterDict[model.wellbores.prodwellflowrate.Name] = self.PopulateStructureFromDictEntry(model.wellbores.prodwellflowrate, dd["prodwellflowrate"])
                model.wellbores.ParameterDict[model.wellbores.impedance.Name] = self.PopulateStructureFromDictEntry(model.wellbores.impedance, dd["impedance"])
                model.wellbores.ParameterDict[model.wellbores.wellsep.Name] = self.PopulateStructureFromDictEntry(model.wellbores.wellsep, dd["wellsep"])
                model.wellbores.ParameterDict[model.wellbores.Tinj.Name] = self.PopulateStructureFromDictEntry(model.wellbores.Tinj, dd["Tinj"])
                model.wellbores.ParameterDict[model.wellbores.Phydrostatic.Name] = self.PopulateStructureFromDictEntry(model.wellbores.Phydrostatic, dd["Phydrostatic"])
                model.wellbores.ParameterDict[model.wellbores.II.Name] = self.PopulateStructureFromDictEntry(model.wellbores.II, dd["II"])
                model.wellbores.ParameterDict[model.wellbores.PI.Name] = self.PopulateStructureFromDictEntry(model.wellbores.PI, dd["PI"])
                model.wellbores.ParameterDict[model.wellbores.maxdrawdown.Name] = self.PopulateStructureFromDictEntry(model.wellbores.maxdrawdown, dd["maxdrawdown"])

                #Results - used by other objects or printed in output downstream
                
                model.wellbores.OutputParameterDict[model.wellbores.Phydrostaticcalc.Name] = self.PopulateStructureFromDictEntry(model.wellbores.Phydrostaticcalc, dd["Phydrostaticcalc"])
                model.wellbores.OutputParameterDict[model.wellbores.redrill.Name] = self.PopulateStructureFromDictEntry(model.wellbores.redrill, dd["redrill"])
                model.wellbores.OutputParameterDict[model.wellbores.PumpingPowerProd.Name] = self.PopulateStructureFromDictEntry(model.wellbores.PumpingPowerProd, dd["PumpingPowerProd"]) 
                model.wellbores.OutputParameterDict[model.wellbores.PumpingPowerInj.Name] = self.PopulateStructureFromDictEntry(model.wellbores.PumpingPowerInj, dd["PumpingPowerInj"]) 
                model.wellbores.OutputParameterDict[model.wellbores.pumpdepth.Name] = self.PopulateStructureFromDictEntry(model.wellbores.pumpdepth, dd["pumpdepth"]) 
                model.wellbores.OutputParameterDict[model.wellbores.impedancemodelallowed.Name] = self.PopulateStructureFromDictEntry(model.wellbores.impedancemodelallowed, dd["impedancemodelallowed"])
                model.wellbores.OutputParameterDict[model.wellbores.productionwellpumping.Name] = self.PopulateStructureFromDictEntry(model.wellbores.productionwellpumping, dd["productionwellpumping"])
                model.wellbores.OutputParameterDict[model.wellbores.impedancemodelused.Name] = self.PopulateStructureFromDictEntry(model.wellbores.impedancemodelused, dd["impedancemodelused"])
                model.wellbores.OutputParameterDict[model.wellbores.ProdTempDrop.Name] = self.PopulateStructureFromDictEntry(model.wellbores.ProdTempDrop, dd["ProdTempDrop"])
                model.wellbores.OutputParameterDict[model.wellbores.DP.Name] = self.PopulateStructureFromDictEntry(model.wellbores.DP, dd["DP"]) 
                model.wellbores.OutputParameterDict[model.wellbores.DP1.Name] = self.PopulateStructureFromDictEntry(model.wellbores.DP1, dd["DP1"])
                model.wellbores.OutputParameterDict[model.wellbores.DP2.Name] = self.PopulateStructureFromDictEntry(model.wellbores.DP2, dd["DP2"])
                model.wellbores.OutputParameterDict[model.wellbores.DP3.Name] = self.PopulateStructureFromDictEntry(model.wellbores.DP3, dd["DP3"])
                model.wellbores.OutputParameterDict[model.wellbores.DP4.Name] = self.PopulateStructureFromDictEntry(model.wellbores.DP4, dd["DP4"]) 
                model.wellbores.OutputParameterDict[model.wellbores.ProducedTemperature.Name] = self.PopulateStructureFromDictEntry(model.wellbores.ProducedTemperature, dd["ProducedTemperature"])
                model.wellbores.OutputParameterDict[model.wellbores.PumpingPower.Name] = self.PopulateStructureFromDictEntry(model.wellbores.PumpingPower, dd["PumpingPower"])
                model.wellbores.OutputParameterDict[model.wellbores.Pprodwellhead.Name] = self.PopulateStructureFromDictEntry(model.wellbores.Pprodwellhead, dd["Pprodwellhead"])

            elif "SurfacePlant" in sclass: #Try to rehydrate the SurfacePlant object
                model.surfaceplant.ParameterDict[model.surfaceplant.enduseoption.Name] = self.PopulateStructureFromDictEntry(model.surfaceplant.enduseoption, dd["enduseoption"])
                model.surfaceplant.ParameterDict[model.surfaceplant.pptype.Name] = self.PopulateStructureFromDictEntry(model.surfaceplant.pptype, dd["pptype"])
                model.surfaceplant.ParameterDict[model.surfaceplant.pumpeff.Name] = self.PopulateStructureFromDictEntry(model.surfaceplant.pumpeff, dd["pumpeff"])
                model.surfaceplant.ParameterDict[model.surfaceplant.utilfactor.Name] = self.PopulateStructureFromDictEntry(model.surfaceplant.utilfactor, dd["utilfactor"])
                model.surfaceplant.ParameterDict[model.surfaceplant.enduseefficiencyfactor.Name] = self.PopulateStructureFromDictEntry(model.surfaceplant.enduseefficiencyfactor, dd["enduseefficiencyfactor"])
                model.surfaceplant.ParameterDict[model.surfaceplant.chpfraction.Name] = self.PopulateStructureFromDictEntry(model.surfaceplant.chpfraction, dd["chpfraction"])
                model.surfaceplant.ParameterDict[model.surfaceplant.Tchpbottom.Name] = self.PopulateStructureFromDictEntry(model.surfaceplant.Tchpbottom, dd["Tchpbottom"])
                model.surfaceplant.ParameterDict[model.surfaceplant.Tenv.Name] = self.PopulateStructureFromDictEntry(model.surfaceplant.Tenv, dd["Tenv"])
                model.surfaceplant.ParameterDict[model.surfaceplant.plantlifetime.Name] = self.PopulateStructureFromDictEntry(model.surfaceplant.plantlifetime, dd["plantlifetime"])
                model.surfaceplant.ParameterDict[model.surfaceplant.pipinglength.Name] = self.PopulateStructureFromDictEntry(model.surfaceplant.pipinglength, dd["pipinglength"])
                model.surfaceplant.ParameterDict[model.surfaceplant.Pplantoutlet.Name] = self.PopulateStructureFromDictEntry(model.surfaceplant.Pplantoutlet, dd["Pplantoutlet"])
                model.surfaceplant.ParameterDict[model.surfaceplant.elecprice.Name] = self.PopulateStructureFromDictEntry(model.surfaceplant.elecprice, dd["elecprice"])
                model.surfaceplant.ParameterDict[model.surfaceplant.heatprice.Name] = self.PopulateStructureFromDictEntry(model.surfaceplant.heatprice, dd["heatprice"])

                #Results - used by other objects or printed in output downstream
                model.surfaceplant.OutputParameterDict[model.surfaceplant.usebuiltinoutletplantcorrelation.Name] = self.PopulateStructureFromDictEntry(model.surfaceplant.usebuiltinoutletplantcorrelation, dd["usebuiltinoutletplantcorrelation"])
                model.surfaceplant.OutputParameterDict[model.surfaceplant.TenteringPP.Name] = self.PopulateStructureFromDictEntry(model.surfaceplant.TenteringPP, dd["TenteringPP"])
                model.surfaceplant.OutputParameterDict[model.surfaceplant.HeatkWhExtracted.Name] = self.PopulateStructureFromDictEntry(model.surfaceplant.HeatkWhExtracted, dd["HeatkWhExtracted"])
                model.surfaceplant.OutputParameterDict[model.surfaceplant.PumpingkWh.Name] = self.PopulateStructureFromDictEntry(model.surfaceplant.PumpingkWh, dd["PumpingkWh"])
                model.surfaceplant.OutputParameterDict[model.surfaceplant.ElectricityProduced.Name] = self.PopulateStructureFromDictEntry(model.surfaceplant.ElectricityProduced, dd["ElectricityProduced"])
                model.surfaceplant.OutputParameterDict[model.surfaceplant.NetElectricityProduced.Name] = self.PopulateStructureFromDictEntry(model.surfaceplant.NetElectricityProduced, dd["NetElectricityProduced"])
                model.surfaceplant.OutputParameterDict[model.surfaceplant.TotalkWhProduced.Name] = self.PopulateStructureFromDictEntry(model.surfaceplant.TotalkWhProduced, dd["TotalkWhProduced"])
                model.surfaceplant.OutputParameterDict[model.surfaceplant.NetkWhProduced.Name] = self.PopulateStructureFromDictEntry(model.surfaceplant.NetkWhProduced, dd["NetkWhProduced"])
                model.surfaceplant.OutputParameterDict[model.surfaceplant.HeatkWhProduced.Name] = self.PopulateStructureFromDictEntry(model.surfaceplant.HeatkWhProduced, dd["HeatkWhProduced"])
                model.surfaceplant.OutputParameterDict[model.surfaceplant.FirstLawEfficiency.Name] = self.PopulateStructureFromDictEntry(model.surfaceplant.FirstLawEfficiency, dd["FirstLawEfficiency"])
                model.surfaceplant.OutputParameterDict[model.surfaceplant.HeatExtracted.Name] = self.PopulateStructureFromDictEntry(model.surfaceplant.HeatExtracted, dd["HeatExtracted"])
                model.surfaceplant.OutputParameterDict[model.surfaceplant.HeatProduced.Name] = self.PopulateStructureFromDictEntry(model.surfaceplant.HeatProduced, dd["HeatProduced"])
                model.surfaceplant.OutputParameterDict[model.surfaceplant.Availability.Name] = self.PopulateStructureFromDictEntry(model.surfaceplant.Availability, dd["Availability"])
                model.surfaceplant.OutputParameterDict[model.surfaceplant.RemainingReservoirHeatContent.Name] = self.PopulateStructureFromDictEntry(model.surfaceplant.RemainingReservoirHeatContent, dd["RemainingReservoirHeatContent"])
                
            elif "<class 'Economics.Economics'>" in sclass:
                model.economics.ParameterDict[model.economics.econmodel.Name] = self.PopulateStructureFromDictEntry(model.economics.econmodel, dd["econmodel"])
                model.economics.ParameterDict[model.economics.ccstimfixed.Name] = self.PopulateStructureFromDictEntry(model.economics.ccstimfixed, dd["ccstimfixed"])
                model.economics.ParameterDict[model.economics.ccstimadjfactor.Name] = self.PopulateStructureFromDictEntry(model.economics.ccstimadjfactor, dd["ccstimadjfactor"])
                model.economics.ParameterDict[model.economics.ccexplfixed.Name] = self.PopulateStructureFromDictEntry(model.economics.ccexplfixed, dd["ccexplfixed"])
                model.economics.ParameterDict[model.economics.ccexpladjfactor.Name] = self.PopulateStructureFromDictEntry(model.economics.ccexpladjfactor, dd["ccexpladjfactor"])
                model.economics.ParameterDict[model.economics.ccwellfixed.Name] = self.PopulateStructureFromDictEntry(model.economics.ccwellfixed, dd["ccwellfixed"])
                model.economics.ParameterDict[model.economics.ccwelladjfactor.Name] = self.PopulateStructureFromDictEntry(model.economics.ccwelladjfactor, dd["ccwelladjfactor"])
                model.economics.ParameterDict[model.economics.oamwellfixed.Name] = self.PopulateStructureFromDictEntry(model.economics.oamwellfixed, dd["oamwellfixed"])
                model.economics.ParameterDict[model.economics.oamwelladjfactor.Name] = self.PopulateStructureFromDictEntry(model.economics.oamwelladjfactor, dd["oamwelladjfactor"])
                model.economics.ParameterDict[model.economics.ccplantfixed.Name] = self.PopulateStructureFromDictEntry(model.economics.ccplantfixed, dd["ccplantfixed"])
                model.economics.ParameterDict[model.economics.ccplantadjfactor.Name] = self.PopulateStructureFromDictEntry(model.economics.ccplantadjfactor, dd["ccplantadjfactor"])
                model.economics.ParameterDict[model.economics.ccgathfixed.Name] = self.PopulateStructureFromDictEntry(model.economics.ccgathfixed, dd["ccgathfixed"])
                model.economics.ParameterDict[model.economics.ccgathadjfactor.Name] = self.PopulateStructureFromDictEntry(model.economics.ccgathadjfactor, dd["ccgathadjfactor"])
                model.economics.ParameterDict[model.economics.oamplantfixed.Name] = self.PopulateStructureFromDictEntry(model.economics.oamplantfixed, dd["oamplantfixed"])
                model.economics.ParameterDict[model.economics.oamplantadjfactor.Name] = self.PopulateStructureFromDictEntry(model.economics.oamplantadjfactor, dd["oamplantadjfactor"])
                model.economics.ParameterDict[model.economics.oamwaterfixed.Name] = self.PopulateStructureFromDictEntry(model.economics.oamwaterfixed, dd["oamwaterfixed"])
                model.economics.ParameterDict[model.economics.oamwateradjfactor.Name] = self.PopulateStructureFromDictEntry(model.economics.oamwateradjfactor, dd["oamwateradjfactor"])
                model.economics.ParameterDict[model.economics.totalcapcost.Name] = self.PopulateStructureFromDictEntry(model.economics.totalcapcost, dd["totalcapcost"])
                model.economics.ParameterDict[model.economics.oamtotalfixed.Name] = self.PopulateStructureFromDictEntry(model.economics.oamtotalfixed, dd["oamtotalfixed"])
                model.economics.ParameterDict[model.economics.timestepsperyear.Name] = self.PopulateStructureFromDictEntry(model.economics.timestepsperyear, dd["timestepsperyear"])
                model.economics.ParameterDict[model.economics.FCR.Name] = self.PopulateStructureFromDictEntry(model.economics.FCR, dd["FCR"])
                model.economics.ParameterDict[model.economics.discountrate.Name] = self.PopulateStructureFromDictEntry(model.economics.discountrate, dd["discountrate"])
                model.economics.ParameterDict[model.economics.FIB.Name] = self.PopulateStructureFromDictEntry(model.economics.FIB, dd["FIB"])
                model.economics.ParameterDict[model.economics.BIR.Name] = self.PopulateStructureFromDictEntry(model.economics.BIR, dd["BIR"])
                model.economics.ParameterDict[model.economics.EIR.Name] = self.PopulateStructureFromDictEntry(model.economics.EIR, dd["EIR"])
                model.economics.ParameterDict[model.economics.RINFL.Name] = self.PopulateStructureFromDictEntry(model.economics.RINFL, dd["RINFL"])
                model.economics.ParameterDict[model.economics.CTR.Name] = self.PopulateStructureFromDictEntry(model.economics.CTR, dd["CTR"])
                model.economics.ParameterDict[model.economics.GTR.Name] = self.PopulateStructureFromDictEntry(model.economics.GTR, dd["GTR"])
                model.economics.ParameterDict[model.economics.RITC.Name] = self.PopulateStructureFromDictEntry(model.economics.RITC, dd["RITC"])
                model.economics.ParameterDict[model.economics.PTR.Name] = self.PopulateStructureFromDictEntry(model.economics.PTR, dd["PTR"])
                model.economics.ParameterDict[model.economics.inflrateconstruction.Name] = self.PopulateStructureFromDictEntry(model.economics.inflrateconstruction, dd["inflrateconstruction"])
                model.economics.ParameterDict[model.economics.wellcorrelation.Name] = self.PopulateStructureFromDictEntry(model.economics.wellcorrelation, dd["wellcorrelation"])

                #results
                model.economics.OutputParameterDict[model.economics.LCOE.Name] = self.PopulateStructureFromDictEntry(model.economics.LCOE, dd["LCOE"])
                model.economics.OutputParameterDict[model.economics.LCOH.Name] = self.PopulateStructureFromDictEntry(model.economics.LCOH, dd["LCOH"])
                model.economics.OutputParameterDict[model.economics.Cstim.Name] = self.PopulateStructureFromDictEntry(model.economics.Cstim, dd["Cstim"])
                model.economics.OutputParameterDict[model.economics.Cexpl.Name] = self.PopulateStructureFromDictEntry(model.economics.Cexpl, dd["Cexpl"])
                model.economics.OutputParameterDict[model.economics.Cwell.Name] = self.PopulateStructureFromDictEntry(model.economics.Cwell, dd["Cwell"])
                model.economics.OutputParameterDict[model.economics.Coamwell.Name] = self.PopulateStructureFromDictEntry(model.economics.Coamwell, dd["Coamwell"])
                model.economics.OutputParameterDict[model.economics.Cplant.Name] = self.PopulateStructureFromDictEntry(model.economics.Cplant, dd["Cplant"])
                model.economics.OutputParameterDict[model.economics.Coamplant.Name] = self.PopulateStructureFromDictEntry(model.economics.Coamplant, dd["Coamplant"])
                model.economics.OutputParameterDict[model.economics.Cgath.Name] = self.PopulateStructureFromDictEntry(model.economics.Cgath, dd["Cgath"])
                model.economics.OutputParameterDict[model.economics.Cpiping.Name] = self.PopulateStructureFromDictEntry(model.economics.Cpiping, dd["Cpiping"])
                model.economics.OutputParameterDict[model.economics.Coamwater.Name] = self.PopulateStructureFromDictEntry(model.economics.Coamwater, dd["Coamwater"])
                model.economics.OutputParameterDict[model.economics.CCap.Name] = self.PopulateStructureFromDictEntry(model.economics.CCap, dd["CCap"])
                model.economics.OutputParameterDict[model.economics.Coam.Name] = self.PopulateStructureFromDictEntry(model.economics.Coam, dd["Coam"])
                model.economics.OutputParameterDict[model.economics.averageannualpumpingcosts.Name] = self.PopulateStructureFromDictEntry(model.economics.averageannualpumpingcosts, dd["averageannualpumpingcosts"])

            elif "EconomicsAddOns" in sclass:
                model.addeconomics.ParameterDict[model.addeconomics.AddOnNickname.Name] = self.PopulateStructureFromDictEntry(model.addeconomics.AddOnNickname, dd["AddOnNickname"])
                model.addeconomics.ParameterDict[model.addeconomics.AddOnCAPEX.Name] = self.PopulateStructureFromDictEntry(model.addeconomics.AddOnCAPEX, dd["AddOnCAPEX"])
                model.addeconomics.ParameterDict[model.addeconomics.AddOnOPEXPerYear.Name] = self.PopulateStructureFromDictEntry(model.addeconomics.AddOnOPEXPerYear, dd["AddOnOPEXPerYear"])
                model.addeconomics.ParameterDict[model.addeconomics.AddOnElecGainedPerYear.Name] = self.PopulateStructureFromDictEntry(model.addeconomics.AddOnElecGainedPerYear, dd["AddOnElecGainedPerYear"])
                model.addeconomics.ParameterDict[model.addeconomics.AddOnHeatGainedPerYear.Name] = self.PopulateStructureFromDictEntry(model.addeconomics.AddOnHeatGainedPerYear, dd["AddOnHeatGainedPerYear"])
                model.addeconomics.ParameterDict[model.addeconomics.AddOnProfitGainedPerYear.Name] = self.PopulateStructureFromDictEntry(model.addeconomics.AddOnProfitGainedPerYear, dd["AddOnProfitGainedPerYear"])
                model.addeconomics.ParameterDict[model.addeconomics.FixedInternalRate.Name] = self.PopulateStructureFromDictEntry(model.addeconomics.FixedInternalRate, dd["FixedInternalRate"])
                model.addeconomics.ParameterDict[model.addeconomics.ConstructionYears.Name]  = self.PopulateStructureFromDictEntry(model.addeconomics.ConstructionYears, dd["ConstructionYears"])
                model.addeconomics.ParameterDict[model.addeconomics.HeatStartPrice.Name] = self.PopulateStructureFromDictEntry(model.addeconomics.HeatStartPrice, dd["HeatStartPrice"])
                model.addeconomics.ParameterDict[model.addeconomics.HeatEndPrice.Name] = self.PopulateStructureFromDictEntry(model.addeconomics.HeatEndPrice, dd["HeatEndPrice"])
                model.addeconomics.ParameterDict[model.addeconomics.HeatEscalationStart.Name] = self.PopulateStructureFromDictEntry(model.addeconomics.HeatEscalationStart, dd["HeatEscalationStart"])
                model.addeconomics.ParameterDict[model.addeconomics.HeatEscalationRate.Name] = self.PopulateStructureFromDictEntry(model.addeconomics.HeatEscalationRate, dd["HeatEscalationRate"])
                model.addeconomics.ParameterDict[model.addeconomics.ElecStartPrice.Name] = self.PopulateStructureFromDictEntry(model.addeconomics.ElecStartPrice, dd["ElecStartPrice"])
                model.addeconomics.ParameterDict[model.addeconomics.ElecEndPrice.Name] = self.PopulateStructureFromDictEntry(model.addeconomics.ElecEndPrice, dd["ElecEndPrice"])
                model.addeconomics.ParameterDict[model.addeconomics.ElecEscalationStart.Name] = self.PopulateStructureFromDictEntry(model.addeconomics.ElecEscalationStart, dd["ElecEscalationStart"])
                model.addeconomics.ParameterDict[model.addeconomics.ElecEscalationRate.Name] = self.PopulateStructureFromDictEntry(model.addeconomics.ElecEscalationRate, dd["ElecEscalationRate"])
                model.addeconomics.ParameterDict[model.addeconomics.AnnualLicenseEtc.Name] = self.PopulateStructureFromDictEntry(model.addeconomics.AnnualLicenseEtc, dd["AnnualLicenseEtc"])
                model.addeconomics.ParameterDict[model.addeconomics.FlatLicenseEtc.Name] = self.PopulateStructureFromDictEntry(model.addeconomics.FlatLicenseEtc, dd["FlatLicenseEtc"])
                model.addeconomics.ParameterDict[model.addeconomics.OtherIncentives.Name] = self.PopulateStructureFromDictEntry(model.addeconomics.OtherIncentives, dd["OtherIncentives"])
                model.addeconomics.ParameterDict[model.addeconomics.TaxRelief.Name] = self.PopulateStructureFromDictEntry(model.addeconomics.TaxRelief, dd["TaxRelief"])
                model.addeconomics.ParameterDict[model.addeconomics.TotalGrant.Name] = self.PopulateStructureFromDictEntry(model.addeconomics.TotalGrant, dd["TotalGrant"])

                #results
                model.addeconomics.OutputParameterDict[model.addeconomics.AddOnCAPEXTotal.Name] = self.PopulateStructureFromDictEntry(model.addeconomics.AddOnCAPEXTotal, dd["AddOnCAPEXTotal"])
                model.addeconomics.OutputParameterDict[model.addeconomics.AddOnOPEXTotalPerYear.Name] = self.PopulateStructureFromDictEntry(model.addeconomics.AddOnOPEXTotalPerYear, dd["AddOnOPEXTotalPerYear"])
                model.addeconomics.OutputParameterDict[model.addeconomics.AddOnElecGainedTotalPerYear.Name] = self.PopulateStructureFromDictEntry(model.addeconomics.AddOnElecGainedTotalPerYear, dd["AddOnElecGainedTotalPerYear"])
                model.addeconomics.OutputParameterDict[model.addeconomics.AddOnHeatGainedTotalPerYear.Name] = self.PopulateStructureFromDictEntry(model.addeconomics.AddOnHeatGainedTotalPerYear, dd["AddOnHeatGainedTotalPerYear"])
                model.addeconomics.OutputParameterDict[model.addeconomics.AddOnProfitGainedTotalPerYear.Name] = self.PopulateStructureFromDictEntry(model.addeconomics.AddOnProfitGainedTotalPerYear, dd["AddOnProfitGainedTotalPerYear"])
                model.addeconomics.OutputParameterDict[model.addeconomics.ProjectNPV.Name] = self.PopulateStructureFromDictEntry(model.addeconomics.ProjectNPV, dd["ProjectNPV"])
                model.addeconomics.OutputParameterDict[model.addeconomics.ProjectIRR.Name] = self.PopulateStructureFromDictEntry(model.addeconomics.ProjectIRR, dd["ProjectIRR"])
                model.addeconomics.OutputParameterDict[model.addeconomics.ProjectVIR.Name] = self.PopulateStructureFromDictEntry(model.addeconomics.ProjectVIR, dd["ProjectVIR"])
                model.addeconomics.OutputParameterDict[model.addeconomics.ProjectPaybackPeriod.Name] = self.PopulateStructureFromDictEntry(model.addeconomics.ProjectPaybackPeriod, dd["ProjectPaybackPeriod"])
                model.addeconomics.OutputParameterDict[model.addeconomics.AddOnPaybackPeriod.Name] = self.PopulateStructureFromDictEntry(model.addeconomics.AddOnPaybackPeriod, dd["AddOnPaybackPeriod"])
                model.addeconomics.OutputParameterDict[model.addeconomics.ProjectMOIC.Name] = self.PopulateStructureFromDictEntry(model.addeconomics.ProjectMOIC, dd["ProjectMOIC"])
                model.addeconomics.OutputParameterDict[model.addeconomics.AddOnElecPrice.Name] = self.PopulateStructureFromDictEntry(model.addeconomics.AddOnElecPrice, dd["AddOnElecPrice"])
                model.addeconomics.OutputParameterDict[model.addeconomics.AddOnHeatPrice.Name] = self.PopulateStructureFromDictEntry(model.addeconomics.AddOnHeatPrice, dd["AddOnHeatPrice"])
                model.addeconomics.OutputParameterDict[model.addeconomics.AdjustedProjectCAPEX.Name] = self.PopulateStructureFromDictEntry(model.addeconomics.AdjustedProjectCAPEX, dd["AdjustedProjectCAPEX"])
                model.addeconomics.OutputParameterDict[model.addeconomics.AdjustedProjectOPEX.Name] = self.PopulateStructureFromDictEntry(model.addeconomics.AdjustedProjectOPEX, dd["AdjustedProjectOPEX"])
                model.addeconomics.OutputParameterDict[model.addeconomics.AddOnCashFlow.Name] = self.PopulateStructureFromDictEntry(model.addeconomics.AddOnCashFlow, dd["AddOnCashFlow"])
                model.addeconomics.OutputParameterDict[model.addeconomics.AddOnCummCashFlow.Name] = self.PopulateStructureFromDictEntry(model.addeconomics.AddOnCummCashFlow, dd["AddOnCummCashFlow"])
                model.addeconomics.OutputParameterDict[model.addeconomics.ProjectCashFlow.Name] = self.PopulateStructureFromDictEntry(model.addeconomics.ProjectCashFlow, dd["ProjectCashFlow"])
                model.addeconomics.OutputParameterDict[model.addeconomics.ProjectCummCashFlow.Name] = self.PopulateStructureFromDictEntry(model.addeconomics.ProjectCummCashFlow, dd["ProjectCummCashFlow"])
                model.addeconomics.OutputParameterDict[model.addeconomics.AddOnElecRevenue.Name] = self.PopulateStructureFromDictEntry(model.addeconomics.AddOnElecRevenue, dd["AddOnElecRevenue"])
                model.addeconomics.OutputParameterDict[model.addeconomics.AddOnHeatRevenue.Name] = self.PopulateStructureFromDictEntry(model.addeconomics.AddOnHeatRevenue, dd["AddOnHeatRevenue"])
                model.addeconomics.OutputParameterDict[model.addeconomics.AddOnRevenue.Name] = self.PopulateStructureFromDictEntry(model.addeconomics.AddOnRevenue, dd["AddOnRevenue"])

            elif "EconomicsCCUS" in sclass:
                model.ccuseconomics.ParameterDict[model.ccuseconomics.FixedInternalRate.Name] = self.PopulateStructureFromDictEntry(model.ccuseconomics.FixedInternalRate, dd["FixedInternalRate"])
                model.ccuseconomics.ParameterDict[model.ccuseconomics.ConstructionYears.Name] = self.PopulateStructureFromDictEntry(model.ccuseconomics.ConstructionYears, dd["ConstructionYears"])
                model.ccuseconomics.ParameterDict[model.ccuseconomics.CCUSEndPrice.Name] = self.PopulateStructureFromDictEntry(model.ccuseconomics.CCUSEndPrice, dd["CCUSEndPrice"])
                model.ccuseconomics.ParameterDict[model.ccuseconomics.CCUSEscalationStart.Name] = self.PopulateStructureFromDictEntry(model.ccuseconomics.CCUSEscalationStart, dd["CCUSEscalationStart"])
                model.ccuseconomics.ParameterDict[model.ccuseconomics.CCUSEscalationRate.Name] = self.PopulateStructureFromDictEntry(model.ccuseconomics.CCUSEscalationRate, dd["CCUSEscalationRate"])
                model.ccuseconomics.ParameterDict[model.ccuseconomics.CCUSStartPrice.Name] = self.PopulateStructureFromDictEntry(model.ccuseconomics.CCUSStartPrice, dd["CCUSStartPrice"])
                model.ccuseconomics.ParameterDict[model.ccuseconomics.CCUSGridCO2.Name] = self.PopulateStructureFromDictEntry(model.ccuseconomics.CCUSGridCO2, dd["CCUSGridCO2"])
                model.ccuseconomics.ParameterDict[model.ccuseconomics.HeatStartPrice.Name] = self.PopulateStructureFromDictEntry(model.ccuseconomics.HeatStartPrice, dd["HeatStartPrice"])
                model.ccuseconomics.ParameterDict[model.ccuseconomics.HeatEndPrice.Name] = self.PopulateStructureFromDictEntry(model.ccuseconomics.HeatEndPrice, dd["HeatEndPrice"])
                model.ccuseconomics.ParameterDict[model.ccuseconomics.HeatEscalationStart.Name]  = self.PopulateStructureFromDictEntry(model.ccuseconomics.HeatEscalationStart, dd["HeatEscalationStart"])
                model.ccuseconomics.ParameterDict[model.ccuseconomics.HeatEscalationRate.Name] = self.PopulateStructureFromDictEntry(model.ccuseconomics.HeatEscalationRate, dd["HeatEscalationRate"])
                model.ccuseconomics.ParameterDict[model.ccuseconomics.ElecStartPrice.Name] = self.PopulateStructureFromDictEntry(model.ccuseconomics.ElecStartPrice, dd["ElecStartPrice"])
                model.ccuseconomics.ParameterDict[model.ccuseconomics.ElecEndPrice.Name] = self.PopulateStructureFromDictEntry(model.ccuseconomics.ElecEndPrice, dd["ElecEndPrice"])
                model.ccuseconomics.ParameterDict[model.ccuseconomics.ElecEscalationStart.Name]  = self.PopulateStructureFromDictEntry(model.ccuseconomics.ElecEscalationStart, dd["ElecEscalationStart"])
                model.ccuseconomics.ParameterDict[model.ccuseconomics.ElecEscalationRate.Name] = self.PopulateStructureFromDictEntry(model.ccuseconomics.ElecEscalationRate, dd["ElecEscalationRate"])

                #results
                model.ccuseconomics.OutputParameterDict[model.ccuseconomics.ProjectNPV.Name] = self.PopulateStructureFromDictEntry(model.ccuseconomics.ProjectNPV, dd["ProjectNPV"])
                model.ccuseconomics.OutputParameterDict[model.ccuseconomics.ProjectIRR.Name] = self.PopulateStructureFromDictEntry(model.ccuseconomics.ProjectIRR, dd["ProjectIRR"])
                model.ccuseconomics.OutputParameterDict[model.ccuseconomics.ProjectVIR.Name] = self.PopulateStructureFromDictEntry(model.ccuseconomics.ProjectVIR, dd["ProjectVIR"])
                model.ccuseconomics.OutputParameterDict[model.ccuseconomics.ProjectPaybackPeriod.Name] = self.PopulateStructureFromDictEntry(model.ccuseconomics.ProjectPaybackPeriod, dd["ProjectPaybackPeriod"])
                model.ccuseconomics.OutputParameterDict[model.ccuseconomics.ProjectMOIC.Name] = self.PopulateStructureFromDictEntry(model.ccuseconomics.ProjectMOIC, dd["ProjectMOIC"])
                model.ccuseconomics.OutputParameterDict[model.ccuseconomics.ProjectCashFlow.Name] = self.PopulateStructureFromDictEntry(model.ccuseconomics.ProjectCashFlow, dd["ProjectCashFlow"])
                model.ccuseconomics.OutputParameterDict[model.ccuseconomics.ProjectCummCashFlow.Name] = self.PopulateStructureFromDictEntry(model.ccuseconomics.ProjectCummCashFlow, dd["ProjectCummCashFlow"])
                model.ccuseconomics.OutputParameterDict[model.ccuseconomics.CCUSPrice.Name] = self.PopulateStructureFromDictEntry(model.ccuseconomics.CCUSPrice, dd["CCUSPrice"])
                model.ccuseconomics.OutputParameterDict[model.ccuseconomics.CCUSRevenue.Name] = self.PopulateStructureFromDictEntry(model.ccuseconomics.CCUSRevenue, dd["CCUSRevenue"])
                model.ccuseconomics.OutputParameterDict[model.ccuseconomics.CCUSCashFlow.Name] = self.PopulateStructureFromDictEntry(model.ccuseconomics.CCUSCashFlow, dd["CCUSCashFlow"])
                model.ccuseconomics.OutputParameterDict[model.ccuseconomics.CCUSCummCashFlow.Name] = self.PopulateStructureFromDictEntry(model.ccuseconomics.CCUSCummCashFlow, dd["CCUSCummCashFlow"])
                model.ccuseconomics.OutputParameterDict[model.ccuseconomics.CarbonThatWouldHaveBeenProducedAnnually.Name] = self.PopulateStructureFromDictEntry(model.ccuseconomics.CarbonThatWouldHaveBeenProducedAnnually, dd["CarbonThatWouldHaveBeenProducedAnnually"])
                model.ccuseconomics.OutputParameterDict[model.ccuseconomics.CarbonThatWouldHaveBeenProducedTotal.Name] = self.PopulateStructureFromDictEntry(model.ccuseconomics.CarbonThatWouldHaveBeenProducedTotal, dd["CarbonThatWouldHaveBeenProducedTotal"])
                model.ccuseconomics.OutputParameterDict[model.ccuseconomics.CCUSOnElecPrice.Name] = self.PopulateStructureFromDictEntry(model.ccuseconomics.CCUSOnElecPrice, dd["CCUSOnElecPrice"])
                model.ccuseconomics.OutputParameterDict[model.ccuseconomics.CCUSOnHeatPrice.Name] = self.PopulateStructureFromDictEntry(model.ccuseconomics.CCUSOnHeatPrice, dd["CCUSOnHeatPrice"])

            return True
        except Error as ex:
            print (ex)
            model.logger.error("Error " + str(ex) + " Restoring the values from the database to the object. Proceeding as if we didn't find the object in the database.")
            return False
        return False

    def PopulateStructureFromDictEntry(self, object, dd:dict)->any:
        #rehydrate the object based on values in the JSON-based dictionary - copy the original values for the object for those that don't change, and use the dictionary values for the ones that might have changed

        if not "value" in dd: return None   #don't do anythin if there isn't something in dd["value"]
        try:
            if isinstance(object, OutputParameter):
                if isinstance(object.value, float): object.value = float(dd["value"])
                elif isinstance(object.value, int): object.value = int(dd["value"])
                elif isinstance(object.value, bool): object.value = bool(dd["value"])
                elif isinstance(object.value, str): object.value = str(dd["value"])
                elif isinstance(object.value, list): object.value = np.array(list(dd["value"]))
                else: object.value = dd["value"]
                return OutputParameter(object.Name, value = object.value, UnitType=object.UnitType, PreferredUnits=object.PreferredUnits, CurrentUnits=object.CurrentUnits, UnitsMatch=object.UnitsMatch)
            else:
                object.Provided = bool(dd["Provided"])
                object.Valid = bool(dd["Valid"])
                #ignore all the other parameters because that can't won't be changed by users.  The only failure here is when the CurrentUnits change...

                #different value types makes it a bit complicated
                if isinstance(object, floatParameter):
                    object.value = float(dd["value"])
                    return floatParameter(object.Name, value = object.value, Required=object.Required, Provided=object.Provided, Valid=object.Valid, ErrMessage=object.ErrMessage, InputComment=object.InputComment, ToolTipText=object.ToolTipText, UnitType=object.UnitType, PreferredUnits=object.PreferredUnits, CurrentUnits=object.CurrentUnits, UnitsMatch=object.UnitsMatch, DefaultValue=object.DefaultValue, Min=object.Min, Max=object.Max)
                elif isinstance(object, intParameter):    # int is complicated becasue it can be a int or an enum
                    if isinstance(object.value, Enum):  #Enums are even more complicated but only exist for input parameters
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
                        elif 'RECTANGULAR' in dd["value"]: object.value = FractureShape.RECTANGULAR
                        elif 'ELECTRICITY' in dd["value"]: object.value = EndUseOptions.ELECTRICITY
                        elif 'HEAT' in dd["value"]: object.value = EndUseOptions.HEAT
                        elif 'COGENERATION_TOPPING_EXTRA_HEAT' in dd["value"]: object.value = EndUseOptions.COGENERATION_TOPPING_EXTRA_HEAT
                        elif 'COGENERATION_TOPPING_EXTRA_ELECTRICTY' in dd["value"]: object.value = EndUseOptions.COGENERATION_TOPPING_EXTRA_ELECTRICTY
                        elif 'COGENERATION_BOTTOMING_EXTRA_ELECTRICTY' in dd["value"]: object.value = EndUseOptions.COGENERATION_BOTTOMING_EXTRA_ELECTRICTY
                        elif 'COGENERATION_BOTTOMING_EXTRA_HEAT' in dd["value"]: object.value = EndUseOptions.COGENERATION_BOTTOMING_EXTRA_HEAT
                        elif 'COGENERATION_PARALLEL_EXTRA_HEAT' in dd["value"]: object.value = EndUseOptions.COGENERATION_PARALLEL_EXTRA_HEAT
                        elif 'COGENERATION_PARALLEL_EXTRA_ELECTRICTY' in dd["value"]: object.value = EndUseOptions.COGENERATION_PARALLEL_EXTRA_ELECTRICTY
                        elif 'SUB_CRITICAL_ORC' in dd["value"]: object.value = PowerPlantType.SUB_CRITICAL_ORC
                        elif 'SUPER_CRITICAL_ORC' in dd["value"]: object.value = PowerPlantType.SUPER_CRITICAL_ORC
                        elif 'SINGLE_FLASH' in dd["value"]: object.value = PowerPlantType.SINGLE_FLASH
                        elif 'DOUBLE_FLASH' in dd["value"]: object.value = PowerPlantType.DOUBLE_FLASH
                        elif 'FCR' in dd["value"]: object.value = EconomicModel.FCR
                        elif 'STANDARDIZED_LEVELIZED_COST' in dd["value"]: object.value = EconomicModel.STANDARDIZED_LEVELIZED_COST
                        elif 'BICYCLE' in dd["value"]: object.value = EconomicModel.BICYCLE
                        elif 'VERTICAL_SMALL' in dd["value"]: object.value = WellDrillingCostCorrelation.VERTICAL_SMALL
                        elif 'DEVIATED_SMALL' in dd["value"]: object.value = WellDrillingCostCorrelation.DEVIATED_SMALL
                        elif 'VERTICAL_LARGE' in dd["value"]: object.value = WellDrillingCostCorrelation.VERTICAL_LARGE
                        elif 'DEVIATED_LARGE' in dd["value"]: object.value = WellDrillingCostCorrelation.DEVIATED_LARGE
                    else: object.value = int(dd["value"])
                    return intParameter(object.Name, value = object.value, Required=object.Required, Provided=object.Provided, Valid=object.Valid, ErrMessage=object.ErrMessage, InputComment=object.InputComment, ToolTipText=object.ToolTipText, UnitType=object.UnitType, PreferredUnits=object.PreferredUnits, CurrentUnits=object.CurrentUnits, UnitsMatch=object.UnitsMatch, DefaultValue=object.DefaultValue, AllowableRange=object.AllowableRange)
                elif isinstance(object, boolParameter):
                    object.value = bool(dd["value"])
                    return boolParameter(object.Name, value = object.value, Required=object.Required, Provided=object.Provided, Valid=object.Valid, ErrMessage=object.ErrMessage, InputComment=object.InputComment, ToolTipText=object.ToolTipText, UnitType=object.UnitType, PreferredUnits=object.PreferredUnits, CurrentUnits=object.CurrentUnits, UnitsMatch=object.UnitsMatch, DefaultValue=object.DefaultValue)
                elif isinstance(object, strParameter):
                    object.value = str(dd["value"])
                    return strParameter(object.Name, value = object.value, Required=object.Required, Provided=object.Provided, Valid=object.Valid, ErrMessage=object.ErrMessage, InputComment=object.InputComment, ToolTipText=object.ToolTipText, UnitType=object.UnitType, PreferredUnits=object.PreferredUnits, CurrentUnits=object.CurrentUnits, UnitsMatch=object.UnitsMatch, DefaultValue=object.DefaultValue)
                elif isinstance(object, listParameter):
                    object.value = list(dd["value"])
                    return listParameter(object.Name, value = object.value, Required=object.Required, Provided=object.Provided, Valid=object.Valid, ErrMessage=object.ErrMessage, InputComment=object.InputComment, ToolTipText=object.ToolTipText, UnitType=object.UnitType, PreferredUnits=object.PreferredUnits, CurrentUnits=object.CurrentUnits, UnitsMatch=object.UnitsMatch, DefaultValue=object.DefaultValue, Min=object.Min, Max=object.Max)
                else:
                    object.value = dd["value"]
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
            
            #store the calculate result and associated object paremeters in the database
            resultkey = self.store_result(model, object)
            if resultkey == None:
                print("Failed To Store "+ str(object.MyClass) + " " + object.MyPath)
                self.logger.warn("Failed To Store "+ str(object.MyClass) + " " + object.MyPath)
            else:
                print("stored " + str(object.MyClass) + " " + object.MyPath + " as: " + resultkey)
                self.logger.info("stored " + str(object.MyClass) + " " + object.MyPath + " as: " + resultkey)