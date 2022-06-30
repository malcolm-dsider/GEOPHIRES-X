import math
import sys
import numpy as np
from Economics import Economics
import numpy_financial as npf
import Model
import Economics
from GeoPHIRESUtils import DumpObjectAsJson, ReadParameter
from OptionList import WellDrillingCostCorrelation, EconomicModel, EndUseOptions, PowerPlantType
from Parameter import boolParameter, intParameter, floatParameter, strParameter, listParameter, OutputParameter
from Units import *


class EconomicsAddOns(Economics):
    def __init__(self, model:Model):
        """
        The __init__ function is called automatically when a class is instantiated. 
        It initializes the attributes of an object, and sets default values for certain arguments that can be overridden by user input. 
        The __init__ function is used to set up all the parameters in Eocnomics AddOns.
        
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
        
        self.AddOnNickname = self.ParameterDict[self.AddOnNickname.Name] = listParameter("AddOn Nickname", UnitType = Units.NONE)
        self.AddOnCAPEX = self.ParameterDict[self.AddOnCAPEX.Name] = listParameter("AddOn CAPEX", Min= 0.0, Max = 1000.0, UnitType = Units.CURRENCY, PreferredUnits=CurrencyUnit.MDOLLARS, CurrentUnits=CurrencyUnit.MDOLLARS)
        self.AddOnOPEXPerYear = self.ParameterDict[self.AddOnOPEXPerYear.Name] = listParameter("AddOn OPEX", Min= 0.0, Max = 1000.0, UnitType = Units.CURRENCY, PreferredUnits=CurrencyUnit.MDOLLARSPERYEAR, CurrentUnits=CurrencyUnit.MDOLLARSPERYEAR)
        self.AddOnElecGainedPerYear = self.ParameterDict[self.AddOnElecGainedPerYear.Name] = listParameter("AddOn Electricity Gained", Min= 0.0, Max = 1000.0, UnitType = Units.ELECTRICITY, PreferredUnits=ElectricityUnit.KWPERYEAR, CurrentUnits=ElectricityUnit.KWPERYEAR)
        self.AddOnHeatGainedPerYear = self.ParameterDict[self.AddOnHeatGainedPerYear.Name] = listParameter("AddOn Heat Gained", Min= 0.0, Max = 1000.0, UnitType = Units.HEAT, PreferredUnits=HeatUnit.KWPERYEAR, CurrentUnits=HeatUnit.KWPERYEAR)
        self.AddOnProfitGainedPerYear = self.ParameterDict[self.AddOnProfitGainedPerYear.Name] = listParameter("AddOn Profit Gained", Min= 0.0, Max = 1000.0, UnitType = Units.CURRENCY, PreferredUnits=CurrencyUnit.MDOLLARSPERYEAR, CurrentUnits=CurrencyUnit.MDOLLARSPERYEAR)
        
        self.FixedInternalRate = self.ParameterDict[self.FixedInternalRate.Name] = floatParameter("Fixed Internal Rate", value = 6.25, Min=0.0, Max = 100.0, UnitType = Units.PERCENT, PreferredUnits = PercentUnit.TENTH, CurrentUnits = PercentUnit.TENTH, ErrMessage="assume default for fixed internal rate (6.25%)", ToolTipText="Fixed Internal Rate (used in NPV calculation)")
        self.ConstructionYears = self.ParameterDict[self.ConstructionYears.Name]  = intParameter("Construction Years", value = 1, AllowableRange=list(range(1,15,1)), UnitType = Units.NONE, ErrMessage="assume default number of years in construction (1)", ToolTipText="Number of years spent in construction (assumes whole years, no fractions)")
        self.HeatEndPrice = self.ParameterDict[self.HeatEndPrice.Name] = floatParameter("Ending Heat Sale Price", value = 0.025, Min=0, Max=100, UnitType = Units.CURRENCY, PreferredUnits = CurrencyUnit.DOLLARSPERKWH, CurrentUnits = CurrencyUnit.DOLLARSPERKWH)
        self.HeatEscalationStart = self.ParameterDict[self.HeatEscalationStart.Name]  = intParameter("Heat Escalation Start Year", value = 5, AllowableRange=list(range(0,101,1)), UnitType = Units.TIME, PreferredUnits = TimeUnit.YEAR, CurrentUnits = TimeUnit.YEAR, ErrMessage="assume default heat escalation delay time (5 years)", ToolTipText="Number of years after start of project before start of escalation")
        self.HeatEscalationRate = self.ParameterDict[self.HeatEscalationRate.Name] = floatParameter("Heat Escalation Rate Per Year", value = 0.0, Min=0.0, Max = 100.0, UnitType = Units.CURRENCY, PreferredUnits = CurrencyUnit.DOLLARSPERKWH, CurrentUnits = CurrencyUnit.DOLLARSPERKWH, ErrMessage="assume no heat price escalation (0.0)", ToolTipText="additional cost per year of price after escalation starts")
        self.HeatStartPrice = self.ParameterDict[self.HeatStartPrice.Name] = floatParameter("Starting Heat Sale Price", value = 0.025, Min=0, Max=100, UnitType = Units.CURRENCY, PreferredUnits = CurrencyUnit.DOLLARSPERKWH, CurrentUnits = CurrencyUnit.DOLLARSPERKWH)
        self.ElecEndPrice = self.ParameterDict[self.ElecEndPrice.Name] = floatParameter("Ending Electricity Sale Price", value = 0.055, Min=0, Max=100, UnitType = Units.CURRENCY, PreferredUnits = CurrencyUnit.DOLLARSPERKWH, CurrentUnits = CurrencyUnit.DOLLARSPERKWH)
        self.ElecEscalationStart = self.ParameterDict[self.ElecEscalationStart.Name]  = intParameter("Electricity Escalation Start Year", value = 5, AllowableRange=list(range(0,101,1)), UnitType = Units.TIME, PreferredUnits = TimeUnit.YEAR, CurrentUnits = TimeUnit.YEAR, ErrMessage="assume default electricty escalation delay time (5 years)", ToolTipText="Number of years after start of project before start of escalation")
        self.ElecEscalationRate = self.ParameterDict[self.ElecEscalationRate.Name] = floatParameter("Electricity Escalation Rate Per Year", value = 0.0, Min=0.0, Max = 100.0, UnitType = Units.CURRENCY, PreferredUnits = CurrencyUnit.DOLLARSPERKWH, CurrentUnits = CurrencyUnit.DOLLARSPERKWH, ErrMessage="assume no electricty price escalation (0.0)", ToolTipText="additional cost per year of price after escalation starts")
        self.ElecStartPrice = self.ParameterDict[self.ElecStartPrice.Name] = floatParameter("Starting Electricity Sale Price", value = 0.055, Min=0, Max=100, UnitType = Units.CURRENCY, PreferredUnits = CurrencyUnit.DOLLARSPERKWH, CurrentUnits = CurrencyUnit.DOLLARSPERKWH)
        self.AnnualLicenseEtc = self.ParameterDict[self.AnnualLicenseEtc.Name] = floatParameter("Annual License Fees Etc", value = 0.0, Min= -1000.0, Max = 1000.0, UnitType = Units.CURRENCY, PreferredUnits=CurrencyUnit.MDOLLARS, CurrentUnits=CurrencyUnit.MDOLLARS)
        self.FlatLicenseEtc = self.ParameterDict[self.FlatLicenseEtc.Name] = floatParameter("One-time Flat License Fees Etc", Min= -1000.0, Max = 1000.0, UnitType = Units.CURRENCY, PreferredUnits=CurrencyUnit.MDOLLARS, CurrentUnits=CurrencyUnit.MDOLLARS)
        self.OtherIncentives = self.ParameterDict[self.OtherIncentives.Name] = floatParameter("Other Incentives", Min= -1000.0, Max = 1000.0, UnitType = Units.CURRENCY, PreferredUnits=CurrencyUnit.MDOLLARS, CurrentUnits=CurrencyUnit.MDOLLARS)
        self.TaxRelief = self.ParameterDict[self.TaxRelief.Name] = floatParameter("Tax Relief Per Year", value = 0.0, Min=0.0, Max = 100.0, UnitType = Units.PERCENT, PreferredUnits = PercentUnit.PERCENT, CurrentUnits = PercentUnit.PERCENT, ErrMessage="assume no tax relief (0.0)", ToolTipText="Fixed percent reduction in annual tax rate")
        self.TotalGrant = self.ParameterDict[self.TotalGrant.Name] = floatParameter("One-time Grants Etc", Min= -1000.0, Max = 1000.0, UnitType = Units.CURRENCY, PreferredUnits=CurrencyUnit.MDOLLARS, CurrentUnits=CurrencyUnit.MDOLLARS)

        #local variables that need initialization        

        #results
        self.AddOnCAPEXTotal = self.OutputParameterDict[self.AddOnCAPEXTotal.Name] = OutputParameter("AddOn CAPEX Total", value = 0.0, UnitType = Units.CURRENCY, PreferredUnits=CurrencyUnit.MDOLLARS, CurrentUnits=CurrencyUnit.MDOLLARS)
        self.AddOnOPEXTotalPerYear = self.OutputParameterDict[self.AddOnOPEXTotalPerYear.Name] = OutputParameter("AddOn OPEX Total Per Year", value = 0.0, UnitType = Units.CURRENCY, PreferredUnits=CurrencyUnit.MDOLLARSPERYEAR, CurrentUnits=CurrencyUnit.MDOLLARSPERYEAR)
        self.AddOnElecGainedTotalPerYear = self.OutputParameterDict[self.AddOnElecGainedTotalPerYear.Name] = OutputParameter("AddOn Electricity Gained Total Per Year", value = 0.0, UnitType = Units.ELECTRICITY, PreferredUnits=ElectricityUnit.KWPERYEAR, CurrentUnits=ElectricityUnit.KWPERYEAR)
        self.AddOnHeatGainedTotalPerYear = self.OutputParameterDict[self.AddOnHeatGainedTotalPerYear.Name] = OutputParameter("AddOn Heat Gained Total Per Year", value = 0.0, UnitType = Units.HEAT, PreferredUnits=HeatUnit.KWPERYEAR, CurrentUnits=HeatUnit.KWPERYEAR)
        self.AddOnProfitGainedTotalPerYear= self.OutputParameterDict[self.AddOnProfitGainedTotalPerYear.Name] = OutputParameter("AddOn Profit Gained Total Per Year", value = 0.0, UnitType = Units.CURRENCY, PreferredUnits=CurrencyUnit.MDOLLARSPERYEAR, CurrentUnits=CurrencyUnit.MDOLLARSPERYEAR)
        self.AddOnNPV = self.OutputParameterDict[self.AddOnNPV.Name] = OutputParameter("AddOn Net Present Value", value = 0.0, UnitType = Units.CURRENCY, PreferredUnits=CurrencyUnit.MDOLLARS, CurrentUnits=CurrencyUnit.MDOLLARS)
        self.AddOnIRR = self.OutputParameterDict[self.AddOnIRR.Name] = OutputParameter("AddOn Internal Rate of Return", value = 0.0, UnitType = Units.PERCENT, PreferredUnits=PercentUnit.PERCENT, CurrentUnits=PercentUnit.PERCENT)
        self.AddOnVIR = self.OutputParameterDict[self.AddOnVIR.Name] = OutputParameter("AddOn Value Investment Ratio", value = 0.0, UnitType = Units.PERCENT, PreferredUnits=PercentUnit.TENTH, CurrentUnits=PercentUnit.TENTH)
        self.AddOnPaybackPeriod = self.OutputParameterDict[self.AddOnPaybackPeriod.Name] = OutputParameter("AddOn Payback Period", value = 0.0, UnitType = Units.TIME, PreferredUnits=TimeUnit.YEAR, CurrentUnits=TimeUnit.YEAR)
        self.AddOnMOIC = self.OutputParameterDict[self.AddOnMOIC.Name] = OutputParameter("AddOn Multiple of Invested Capital", value = 0.0, UnitType = Units.PERCENT, PreferredUnits=PercentUnit.TENTH, CurrentUnits=PercentUnit.TENTH)
        self.ElecPrice = self.ParameterDict[self.ElecPrice.Name] = OutputParameter("Electricity Sale Price Model", value = 0.055, UnitType = Units.CURRENCY, PreferredUnits = CurrencyUnit.CENTSSPERKWH, CurrentUnits = CurrencyUnit.CENTSSPERKWH)
        self.HeatPrice = self.ParameterDict[self.HeatPrice.Name] = OutputParameter("Heat Sale Price Model", value = 0.025, UnitType = Units.CURRENCY, PreferredUnits = CurrencyUnit.CENTSSPERKWH, CurrentUnits = CurrencyUnit.CENTSSPERKWH)
        
        self.AdjustedCAPEX = self.OutputParameterDict[self.AdjustedCAPEX.Name] = OutputParameter("Adjusted CAPEX", value = 0.0, UnitType = Units.CURRENCY, PreferredUnits=CurrencyUnit.MDOLLARS, CurrentUnits=CurrencyUnit.MDOLLARS)
        self.AdjustedOPEX = self.OutputParameterDict[self.AdjustedOPEX.Name] = OutputParameter("Adjusted OPEX", value = 0.0, UnitType = Units.CURRENCY, PreferredUnits=CurrencyUnit.MDOLLARS, CurrentUnits=CurrencyUnit.MDOLLARS)
        self.CashFlow =  self.OutputParameterDict[self.CashFlow.Name] = OutputParameter("Annual Cash Flow", value = 0.0, UnitType = Units.CURRENCY, PreferredUnits=CurrencyUnit.MDOLLARSPERYEAR, CurrentUnits=CurrencyUnit.MDOLLARSPERYEAR)
        self.CummCashFlow =  self.OutputParameterDict[self.CummCashFlow.Name] = OutputParameter("Cummulative Cash Flow", value = 0.0, UnitType = Units.CURRENCY, PreferredUnits=CurrencyUnit.MDOLLARS, CurrentUnits=CurrencyUnit.MDOLLARS)
        self.ElecRevenue = self.OutputParameterDict[self.ElecRevenue.Name] = OutputParameter("Annual Revenue Generated from Electrcity Sales", value = 0.0, UnitType = Units.CURRENCY, PreferredUnits=CurrencyUnit.MDOLLARSPERYEAR, CurrentUnits=CurrencyUnit.MDOLLARSPERYEAR)
        self.HeatRevenue = self.OutputParameterDict[self.HeatRevenue.Name] = OutputParameter("Annual Revenue Generated from Heat Sales", value = 0.0, UnitType = Units.CURRENCY, PreferredUnits=CurrencyUnit.MDOLLARSPERYEAR, CurrentUnits=CurrencyUnit.MDOLLARSPERYEAR)
        self.AddOnRevenue = self.OutputParameterDict[self.AddOnRevenue.Name] = OutputParameter("Annual Revenue Generated from AddOns", value = 0.0, UnitType = Units.CURRENCY, PreferredUnits=CurrencyUnit.MDOLLARSPERYEAR, CurrentUnits=CurrencyUnit.MDOLLARSPERYEAR)

        model.logger.info("Complete "+ str(__class__) + ": " + sys._getframe(  ).f_code.co_name)

    def __str__(self):
        return "EconomicsAddOns"

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
        The read_parameters function is called by the model to read in all the parameters that are used for this extension.  The user can create as many or as few paramters
        as needed.  Each parameter is created by a call to the InputParameter class, which is defined below, and then stored in a dictionary with a name assigned to
        
        :param self: Access the class variables
        :param model: The conatiner class of the application, giving access to everything else, including the logger
        :return: None
        :doc-author: M alcolm Ross
        """
        model.logger.info("Init " + str(__class__) + ": " + sys._getframe(  ).f_code.co_name)
        super().read_parameters(model)    #read the paremeters for the parent.

        #Deal with all the parameter values that the user has provided that relate to this extension.  super,read_parametesr will have already dealt with all the regular values, but anything unusal may not be dealt with, so check.
        # In this case, all the values are array values, and weren't correctly dealt with, so below is where we process them.  The problem is that they have a position number i.e., "AddOnCAPEX 1, AddOnCAPEX 2" appended to them, while the
        # Parameter name is jusr "AddOnCAPEX" and the position indicates where in the array the user wants it stored.So we neeed to look for the 5 arrays and position values and insert them into the arrays.

        #this does not deal with units if the user wants to do any conversions... 
        #In this case, the read_aparameters fucntion didn't deal with the arrays of values we wanted, so we will craft that here.
        for key in model.InputParameters.keys():
            if key.startswith("AddOn Nickname"):
                val = str(model.InputParameters[key].sValue)
                self.AddOnNickname.value.append(val)                      #this assumes they put the values in the file in consectutive fashion
            if key.startswith("AddOn CAPEX"):
                val = float(model.InputParameters[key].sValue)
                self.AddOnCAPEX.value.append(val)                      #this assumes they put the values in the file in consectutive fashion
            if key.startswith("AddOn OPEX"):
                val = float(model.InputParameters[key].sValue)
                self.AddOnOPEXPerYear.value.append(val)                      #this assumes they put the values in the file in consectutive fashion
            if key.startswith("AddOn Electricity Gained"):
                val = float(model.InputParameters[key].sValue)
                self.AddOnElecGainedPerYear.value.append(val)                      #this assumes they put the values in the file in consectutive fashion
            if key.startswith("AddOn Heat Gained"):
                val = float(model.InputParameters[key].sValue)
                self.AddOnHeatGainedPerYear.value.append(val)                      #this assumes they put the values in the file in consectutive fashion
            if key.startswith("AddOn Profit Gained"):
                val = float(model.InputParameters[key].sValue)
                self.AddOnProfitGainedPerYear.value.append(val)                      #this assumes they put the values in the file in consectutive fashion
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
        
        if len(self.AddOnCAPEX.value) > 0: self.AddOnCAPEXTotal.value = np.sum(self.AddOnCAPEX.value)
        if len(self.AddOnOPEXPerYear.value) > 0: self.AddOnOPEXTotalPerYear.value = np.sum(self.AddOnOPEXPerYear.value)
        if len(self.AddOnElecGainedPerYear.value) > 0: self.AddOnElecGainedTotalPerYear.value = np.sum(self.AddOnElecGainedPerYear.value)
        if len(self.AddOnHeatGainedPerYear.value) > 0: self.AddOnHeatGainedTotalPerYear.value = np.sum(self.AddOnHeatGainedPerYear.value)
        if len(self.AddOnProfitGainedPerYear.value) > 0: self.AddOnProfitGainedTotalPerYear.value = np.sum(self.AddOnProfitGainedPerYear.value)

        #The amount of electricty and/or heat have already been calculated in SurfacePlant, so we need to update them here so when they get used in the final economic calculation (below), they new values reflect the addition of the AddOns
        for i in range(0,model.surfaceplant.plantlifetime.value):
            if model.surfaceplant.enduseoption.value != EndUseOptions.HEAT: #all these end-use options have an electricity generation component
                model.surfaceplant.TotalkWhProduced.value[i] = model.surfaceplant.TotalkWhProduced.value[i] + self.AddOnElecGainedTotalPerYear.value
                model.surfaceplant.NetkWhProduced.value[i] = model.surfaceplant.NetkWhProduced.value[i] + self.AddOnElecGainedTotalPerYear.value
            if model.surfaceplant.enduseoption.value != EndUseOptions.ELECTRICITY: #all those end-use options have a direct-use component
                model.surfaceplant.HeatkWhProduced.value[i] = model.surfaceplant.HeatkWhProduced.value[i] + self.AddOnHeatGainedTotalPerYear.value

        #we are going to run the calculations for the parent AFTER we make the calculations, so our calculations can be included in the master calculations. AddOnCAPEXTotal and AddOnOPEXTotalPerYear get used here.
        super().Calculate(model)    #run calculate for the parent.

        #Now there are some calculations I want to make AFTER the parent class calculations, like  "NPV", "IRR", "VIR", "Payback Period", and "MOIC", which are based on the results of the parent
        self.AdjustedCAPEX.value = self.CCap.value + self.AddOnCAPEXTotal.value +  self.FlatLicenseEtc.value - self.OtherIncentives.value - self.TotalGrant.value
        self.AdjustedOPEX.value = self.Coam.value + self.AddOnOPEXTotalPerYear.value + self.AnnualLicenseEtc.value
        CapCostPerYear = (self.AdjustedCAPEX.value)/self.ConstructionYears.value
        
        self.ElecPrice.value = [0.0] * model.surfaceplant.plantlifetime.value
        self.HeatPrice.value = [0.0] * model.surfaceplant.plantlifetime.value
        self.ElecRevenue.value = [0.0] * model.surfaceplant.plantlifetime.value
        self.HeatRevenue.value = [0.0] * model.surfaceplant.plantlifetime.value
        self.AddOnRevenue.value = [0.0] * model.surfaceplant.plantlifetime.value
        self.CashFlow.value = [0.0] * model.surfaceplant.plantlifetime.value

        #build the price models
        for i in range(0,model.surfaceplant.plantlifetime.value,1):
            self.ElecPrice.value[i] = self.ElecStartPrice.value
            self.HeatPrice.value[i] = self.HeatStartPrice.value
            if i >= self.ElecEscalationStart.value: self.ElecPrice.value[i] = self.ElecPrice.value[i] + ((i - self.ElecEscalationStart.value) * self.ElecEscalationRate.value)
            if i >= self.HeatEscalationStart.value: self.HeatPrice.value[i] = self.HeatPrice.value[i] + ((i - self.HeatEscalationStart.value) * self.HeatEscalationRate.value)
            if self.ElecPrice.value[i] > self.ElecEndPrice.value: self.ElecPrice.value[i] = self.ElecEndPrice.value
            if self.HeatPrice.value[i] > self.HeatEndPrice.value: self.HeatPrice.value[i] = self.HeatEndPrice.value

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
            self.ElecRevenue.value[i] = (dElectricalEnergy * self.ElecPrice.value[i]) / 1000000.0   #MIR ???Electrcity in $M
            self.HeatRevenue.value[i] = (dHeatEnergy * self.HeatPrice.value[i]) / 1000000.0    #MIR ???Heat in $M
            self.AddOnRevenue.value[i] = self.AddOnProfitGainedTotalPerYear.value - self.AddOnOPEXTotalPerYear.value
            self.CashFlow.value[i] = (self.ElecRevenue.value[i] + self.HeatRevenue.value[i] + self.AddOnRevenue.value[i]) - self.Coam.value

        # now insert the cost of construction into the front of the array that will be used to calculate NPV = the convention is that the upfront CAPEX is negative
        for i in range(0,self.ConstructionYears.value,1):
            self.CashFlow.value.insert(0, -1.0 * CapCostPerYear)

        #Calculate more financial values using nympy financials
        self.AddOnNPV.value = npf.npv(self.FixedInternalRate.value, self.CashFlow.value)
        self.AddOnIRR.value = npf.irr(self.CashFlow.value)
        self.AddOnVIR.value  = math.fabs(self.AddOnNPV.value/(self.AddOnCAPEXTotal.value + self.CCap.value))
        
        #calculate Cummcashflow and payback
        dPaybackYears = -1.0
        i = 0
        self.CummCashFlow.value = [0.0] * len(self.CashFlow.value)
        for val in self.CashFlow.value:
            if i == 0: self.CummCashFlow.value[0] = val
            else:
                self.CummCashFlow.value[i] = self.CummCashFlow.value[i - 1] + val
                if self.CummCashFlow.value[i] > 0 and self.CummCashFlow.value[i - 1] <= 0:   #we just crossed the threshold into positive cummcashflow, so we can calculate payback period
                    dFullDiff = self.CummCashFlow.value[i] + math.fabs(self.CummCashFlow.value[(i - 1)])
                    dPerc = math.fabs(self.CummCashFlow.value[(i - 1)]) / dFullDiff
                    dPaybackYears = i + dPerc
            i = i + 1

        self.AddOnPaybackPeriod.value = dPaybackYears
        self.AddOnMOIC.value = self.CummCashFlow.value[len(self.CummCashFlow.value)-1] / (self.AddOnCAPEXTotal.value + self.CCap.value) + ((self.Coam.value + self.AddOnOPEXTotalPerYear.value) * model.surfaceplant.plantlifetime.value)

        model.logger.info("complete "+ str(__class__) + ": " + sys._getframe(  ).f_code.co_name)