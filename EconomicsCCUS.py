import sys
import numpy as np
import Economics
import Model
import Economics
from GeoPHIRESUtils import DumpObjectAsJson, ReadParameter
from OptionList import EndUseOptions
from Parameter import boolParameter, intParameter, floatParameter, strParameter, OutputParameter
from Units import *

class EconomicsCCUS(Economics):
    def __init__(self, model:Model):
        """
        The __init__ function is called automatically when a class is instantiated. 
        It initializes the attributes of an object, and sets default values for certain arguments that can be overridden by user input. 
        The __init__ function is used to set up all the parameters in the CCUS Economics.
        
        :param self: Store data that will be used by the class
        :param model: The conatiner class of the application, giving access to everything else, including the logger
        :return: None
        :doc-author: Malcolm Ross
        """
        model.logger.info("Init " + str(__class__) + ": " + sys._getframe(  ).f_code.co_name)
        super().__init__(model)   # initialize the parent parameters and variables

        #Set up all the Parameters that will be predefined by this class using the different types of parameter classes.  Setting up includes giving it a name, a default value, The Unit Type (length, volume, temperature, etc) and Unit Name of that value, sets it as required (or not), sets allowable range, the error message if that range is exceeded, the ToolTip Text, and the name of teh class that created it.
        #This includes setting up temporary variables that will be available to all the class but noy read in by user, or used for Output
        #This also includes all Parameters that are calculated and then published using the Printouts function.
        #If you choose to sublass this master class, you can do so before or after you create your own parameters.  If you do, you can also choose to call this method from you class, which will effectively add and set all these parameters to your class.
         
        #set up the parameters using the Parameter Constructors (intParameter, floatParameter, strParameter, etc); initialize with their name, default value, and valid range (if int or float).  Optionally, you can specify:
        # Required (is it reuired to run? default value = False), ErrMessage (what GEOPHIRES will report if the value provided is invalid, "assume default value (see manual)"), ToolTipText (when there is a GIU, this is the text that the user will see, "This is ToolTip Text"),
        # UnitType (the type of units associated with this parameter (length, temperature, density, etc), Units.NONE), CurrentUnits (what the units are for this parameter (meters, celcius, gm/cc, etc, Units:NONE), and PreferredUnits (ususally equal to CurrentUnits, but these are the units that the calculations assume when running, Units.NONE
        
        self.CCUSEndPrice = self.ParameterDict[self.CCUSEndPrice.Name] = floatParameter("Ending CCUS Credit Value", value = 0, Min=0, Max=1000, UnitType = Units.CURRENCY, PreferredUnits = CurrencyUnit.DOLLARSPERLB, CurrentUnits = CurrencyUnit.DOLLARSPERLB)
        self.CCUSEscalationStart = self.ParameterDict[self.CCUSEscalationStart.Name]  = intParameter("CCUS Escalation Start Year", value = 0, AllowableRange=list(range(0,101,1)), UnitType = Units.TIME, PreferredUnits = TimeUnit.YEAR, CurrentUnits = TimeUnit.YEAR, ErrMessage="assume default CCUS escalation delay time (5 years)", ToolTipText="Number of years after start of project before start of CCUS incentives")
        self.CCUSEscalationRate = self.ParameterDict[self.CCUSEscalationRate.Name] = floatParameter("CCUS Escalation Rate Per Year", value = 0.0, Min=0.0, Max = 100.0, UnitType = Units.CURRENCY, PreferredUnits = CurrencyUnit.DOLLARSPERMT, CurrentUnits = CurrencyUnit.DOLLARSPERMT, ErrMessage="assume no CCUS credit escalation (0.0)", ToolTipText="additional value per year of price after escalation starts")
        self.CCUSStartPrice = self.ParameterDict[self.CCUSStartPrice.Name] = floatParameter("Starting CCUS Credit Value", value = 0.0, Min=0, Max=1000, UnitType = Units.CURRENCY, PreferredUnits = CurrencyUnit.DOLLARSPERMT, CurrentUnits = CurrencyUnit.DOLLARSPERMT)
        self.CCUSGridCO2 = self.ParameterDict[self.CCUSGridCO2.Name] = floatParameter("Current Grid CO2 production", value = 0.0, Min=0, Max=50000, UnitType = Units.CO2PRODUCTION, PreferredUnits = CO2ProductionUnit.LBSPERKWH, CurrentUnits = CO2ProductionUnit.LBSPERKWH)

        #local variables that need initialization        

        #results
        self.CCUSPrice = self.OutputParameterDict[self.CCUSPrice.Name] = OutputParameter("CCUS Incentive Model", value = 0.0, UnitType = Units.CURRENCY, PreferredUnits=CurrencyUnit.DOLLARSPERLB, CurrentUnits=CurrencyUnit.DOLLARSPERLB)
        self.CCUSRevenue = self.OutputParameterDict[self.CCUSRevenue.Name] = OutputParameter("Annual Revenue Generated from CCUS", value = 0.0, UnitType = Units.CURRENCY, PreferredUnits=CurrencyUnit.MDOLLARSPERYEAR, CurrentUnits=CurrencyUnit.MDOLLARSPERYEAR)
        self.CashFlow =  self.OutputParameterDict[self.CashFlow.Name] = OutputParameter("Annual Cash Flow", value = 0.0, UnitType = Units.CURRENCY, PreferredUnits=CurrencyUnit.MDOLLARSPERYEAR, CurrentUnits=CurrencyUnit.MDOLLARSPERYEAR)
        self.CummCashFlow =  self.OutputParameterDict[self.CummCashFlow.Name] = OutputParameter("Cummulative Cash Flow", value = 0.0, UnitType = Units.CURRENCY, PreferredUnits=CurrencyUnit.MDOLLARS, CurrentUnits=CurrencyUnit.MDOLLARS)

        model.logger.info("Complete "+ str(__class__) + ": " + sys._getframe(  ).f_code.co_name)

    def __str__(self):
        return "EconomicsCCUS"

    def dump_self_as_Json(self)->str: return(DumpObjectAsJson(self))

    def read_parameter_from_Json(self, dJson): 
        for item in dJson.items():
            if item[0] in self.ParameterDict:
                if isinstance(self.ParameterDict[item[0]], floatParameter): val = float(item[1]['Value'])
                if isinstance(self.ParameterDict[item[0]], intParameter): val = int(item[1]['Value'])
                if isinstance(self.ParameterDict[item[0]], boolParameter): val = bool(item[1]['Value'])
                if isinstance(self.ParameterDict[item[0]], strParameter): val = str(item[1]['Value'])
                self.ParameterDict[item[0]].value = val

    def read_parameters(self, model:Model) -> None:
        """
        The read_parameters function reads in the parameters from a dictionary and stores them in the aparmeters.  It also handles special cases that need to be handled after a value has been read in and checked.  If you choose to sublass this master class, you can also choose to override this method (or not), and if you do
        
        :param self: Access variables that belong to a class
        :param model: The conatiner class of the application, giving access to everything else, including the logger

        :return: None
        :doc-author: Malcolm Ross
        """
        model.logger.info("Init " + str(__class__) + ": " + sys._getframe(  ).f_code.co_name)
        super().read_parameters(model)    #read the paremeters for the parent.

        #Deal with all the parameter values that the user has provided that relate to this extension.  super,read_parametesr will have already dealt with all the regular values, but anything unusal may not be dealt with, so check.
        # In this case, all the values are array values, and weren't correctly dealt with, so below is where we process them.

        model.logger.info("complete "+ str(__class__) + ": " + sys._getframe(  ).f_code.co_name)

    def Calculate(self, model) -> None:
        """
        The Calculate function is where all the calculations are done.
        This function can be called multiple times, and will only recalculate what has changed each time it is called.
        
        :param self: Access variables that belongs to the class
        :param model: The conatiner class of the application, giving access to everything else, including the logger
        :return: Nothing, but it does make calculations and set values in the model
        :doc-author: Malcolm Ross
        """
        model.logger.info("Init " + str(__class__) + ": " + sys._getframe(  ).f_code.co_name)

        #This is where all the calcualtions are made using all the values that have been set.
        #If you sublcass this class, you can choose to run these calculations before (or after) your calculations, but that assumes you have set all the values that are required for these calculations
        #If you choose to sublass this master class, you can also choose to override this method (or not), and if you do, do it before or after you call you own version of this method.  If you do, you can also choose to call this method from you class, which can effectively run the calculations of the superclass, making all thr values available to your methods. but you had n=betteer have set all the paremeters!
        
        #now we are going to run the calculations for the parent
#        super().Calculate(reserv, wellbores, surfaceplant, model)    #run calculate for the parent.#MIR No need to do this, because it has already been run

        #Now there are some calculations I want to make AFTER the parent class calculations
        self.CCUSPrice.value = [0.0] * model.surfaceplant.plantlifetime.value
        self.CCUSRevenue.value = [0.0] * model.surfaceplant.plantlifetime.value
        self.CashFlow.value = [0.0] * model.surfaceplant.plantlifetime.value
        self.CummCashFlow.value = [0.0] * model.surfaceplant.plantlifetime.value

        #build the price model
        for i in range(0,model.surfaceplant.plantlifetime.value,1):
            self.CCUSPrice.value[i] = self.CCUSStartPrice.value
            if i >= self.CCUSEscalationStart.value: self.CCUSPrice.value[i] = self.CCUSPrice.value[i] + ((i - self.CCUSEscalationStart.value) * self.CCUSEscalationRate.value)
            if self.CCUSPrice.value[i] > self.CCUSEndPrice.value: self.CCUSPrice.value[i] = self.CCUSEndPrice.value

        for i in range(0,model.surfaceplant.plantlifetime.value,1):
            dElectricalEnergy = 0.0
            dHeatEnergy = 0.0
            dBothEnergy = 0.0
            if model.surfaceplant.enduseoption.value == EndUseOptions.ELECTRICITY: #This option has no heat component
                dElectricalEnergy = model.surfaceplant.NetkWhProduced.value[i]
            elif model.surfaceplant.enduseoption.value == EndUseOptions.HEAT: #has heat component but no electricty
                dHeatEnergy = model.surfaceplant.HeatkWhProduced.value[i]
            else: #everything else has a component of both
                dElectricalEnergy = model.surfaceplant.NetkWhProduced.value[i]
                dHeatEnergy = model.surfaceplant.HeatkWhProduced.value[i]
            
            dBothEnergy = dElectricalEnergy +  dHeatEnergy
            CarbonThatWouldHaveBeenProduced = dBothEnergy * self.CCUSGridCO2.value
            self.CCUSRevenue.value[i] = (CarbonThatWouldHaveBeenProduced * self.CCUSPrice.value[i]) / 1000000.0    #CCUS (from both heat and elec) based on total, not net energy; in $M
            self.CashFlow.value[i] = (self.CCUSRevenue.value[i]) - self.Coam.value

        i = 0
        for val in self.CashFlow.value:
            if i == 0: self.CummCashFlow.value[0] = val
            else: self.CummCashFlow.value[i] = self.CummCashFlow.value[i - 1] + val
            i = i + 1

        model.logger.info("complete "+ str(__class__) + ": " + sys._getframe(  ).f_code.co_name)