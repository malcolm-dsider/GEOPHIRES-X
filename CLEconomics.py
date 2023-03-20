import math
import sys
import os
import numpy as np
import Model
import CLWellBores
from OptionList import WellDrillingCostCorrelation, EconomicModel, EndUseOptions, PowerPlantType
from Parameter import intParameter, floatParameter, OutputParameter, ReadParameter, boolParameter
from Units import *

class CLEconomics:
    """
     Class to support the closed-loop economic calculations in GEOPHIRES
    """
    def __init__(self, model:Model):
        """
        The __init__ function is called automatically when a class is instantiated. 
        It initializes the attributes of an object, and sets default values for certain arguments that can be overridden by user input. 
        The __init__ function is used to set up all the parameters in closed loop Economics.
        :param self: Store data that will be used by the class
        :param model: The container class of the application, giving access to everything else, including the logger
        :return: None
        :doc-author: Malcolm Ross
        """
        model.logger.info("Init " + str(__class__) + ": " + sys._getframe().f_code.co_name)

        #Set up all the Parameters that will be predefined by this class using the different types of parameter classes.  Setting up includes giving it a name, a default value, The Unit Type (length, volume, temperature, etc) and Unit Name of that value, sets it as required (or not), sets allowable range, the error message if that range is exceeded, the ToolTip Text, and the name of teh class that created it.
        #This includes setting up temporary variables that will be available to all the class but noy read in by user, or used for Output
        #This also includes all Parameters that are calculated and then published using the Printouts function.
        #If you choose to sublass this master class, you can do so before or after you create your own parameters.  If you do, you can also choose to call this method from you class, which will effectively add and set all these parameters to your class.
         
        #These disctionarie contains a list of all the parameters set in this object, stored as "Parameter" and OutputParameter Objects.  This will alow us later to access them in a user interface and get that list, along with unit type, preferred units, etc. 
        self.ParameterDict = {}
        self.OutputParameterDict = {}
        
        self.horizontalccwellfixed = self.ParameterDict[self.horizontalccwellfixed.Name] = floatParameter("Horizontal Well Drilling and Completion Capital Cost", value = -1.0, DefaultValue=-1.0, Min=0, Max=200, UnitType = Units.CURRENCY, PreferredUnits = CurrencyUnit.MDOLLARS, CurrentUnits = CurrencyUnit.MDOLLARS, Provided = False, Valid = False, ToolTipText = "Horizontal Well Drilling and Completion Capital Cost")
        self.horizontalccwelladjfactor = self.ParameterDict[self.horizontalccwelladjfactor.Name] = floatParameter("Horizontal Well Drilling and Completion Capital Cost Adjustment Factor", value = 1.0, DefaultValue=1.0, Min=0, Max=10, UnitType = Units.PERCENT, PreferredUnits = PercentUnit.TENTH, CurrentUnits = PercentUnit.TENTH, Provided = False, Valid = True, ToolTipText = "Horizontal Well Drilling and Completion Capital Cost Adjustment Factor")
        self.horizontalwellcorrelation = self.ParameterDict[self.horizontalwellcorrelation.Name] = intParameter("Horizontal Well Drilling Cost Correlation", value = WellDrillingCostCorrelation.VERTICAL_SMALL, DefaultValue=WellDrillingCostCorrelation.VERTICAL_SMALL, AllowableRange=[1,2,3,4], UnitType = Units.NONE, ErrMessage="assume default horizontal well drilling cost correlation (1)", ToolTipText="Select the built-in horizontal well drilling and completion cost correlation. 1: vertical open-hole, small diameter; 2: deviated liner, small diameter; 3: vertical open-hole, large diameter; 4: deviated liner, large diameter")

        #local variable initialization
        self.C1well = 0.0
        sclass = str(__class__).replace("<class \'", "")
        self.MyClass = sclass.replace("\'>","")
        self.MyPath = os.path.abspath(__file__)

        #results

        model.logger.info("Complete "+ str(__class__) + ": " + sys._getframe().f_code.co_name)

    def read_parameters(self, model:Model) -> None:
        """
        read_parameters read and update the Economics parmeters and handle the special cases 

        Args:
            model (Model): The container class of the application, giving access to everything else, including the logger
        """
        model.logger.info("Init " + str(__class__) + ": " + sys._getframe().f_code.co_name)

        #Deal with all the parameter values that the user has provided.  They should really only provide values that they want to change from the default values, but they can provide a value that is already set because it is a defaulr value set in __init__.  It will ignore those.
        #This also deals with all the special cases that need to be talen care of after a vlaue has been read in and checked.
        #If you choose to sublass this master class, you can also choose to override this method (or not), and if you do, do it before or after you call you own version of this method.  If you do, you can also choose to call this method from you class, which can effectively modify all these superclass parameters in your class.

        if len(model.InputParameters) > 0:
            #loop thru all the parameters that the user wishes to set, looking for parameters that match this object
            for item in self.ParameterDict.items():
                ParameterToModify = item[1]
                key = ParameterToModify.Name.strip()
                if key in model.InputParameters:
                    ParameterReadIn = model.InputParameters[key]
                    ParameterToModify.CurrentUnits = ParameterToModify.PreferredUnits    #Before we change the paremeter, let's assume that the unit preferences will match - if they don't, the later code will fix this.
                    ReadParameter(ParameterReadIn, ParameterToModify, model)   #this should handle all the non-special cases

                    #handle special cases
                    if ParameterToModify.Name == "Horizontal Well Drilling Cost Correlation":
                        if ParameterReadIn.sValue == '1': ParameterToModify.value = WellDrillingCostCorrelation.VERTICAL_SMALL
                        elif ParameterReadIn.sValue == '2': ParameterToModify.value = WellDrillingCostCorrelation.DEVIATED_SMALL
                        elif ParameterReadIn.sValue == '3': ParameterToModify.value = WellDrillingCostCorrelation.VERTICAL_LARGE
                        else: ParameterToModify.value = WellDrillingCostCorrelation.DEVIATED_LARGE
                    elif ParameterToModify.Name == "Horizontal Well Drilling and Completion Capital Cost Adjustment Factor":
                        if self.horizontalccwellfixed.Valid and ParameterToModify.Valid:
                            print("Warning: Provided horizontal well drilling and completion cost adjustment factor not considered because valid total horizontal well drilling and completion cost provided.")
                            model.logger.warning("Provided horizontal well drilling and completion cost adjustment factor not considered because valid total horizontal well drilling and completion cost provided.")
                        elif not self.horizontalccwellfixed.Provided and not self.horizontalccwelladjfactor.Provided:
                            ParameterToModify.value = 1.0
                            print("Warning: No valid horizontal well drilling and completion total cost or adjustment factor provided. GEOPHIRES will assume default built-in horizontal well drilling and completion cost correlation with adjustment factor = 1.")
                            model.logger.warning("No valid horizontal well drilling and completion total cost or adjustment factor provided. GEOPHIRES will assume default built-in horizontal well drilling and completion cost correlation with adjustment factor = 1.")
                        elif self.horizontalccwellfixed.Provided and not self.horizontalccwellfixed.Valid:
                            print("Warning: Provided horizontal well drilling and completion cost outside of range 0-1000. GEOPHIRES will assume default built-in horizontal well drilling and completion cost correlation with adjustment factor = 1.")
                            model.logger.warning("Provided horizontal well drilling and completion cost outside of range 0-1000. GEOPHIRES will assume default built-in horizontal well horizontal drilling and completion cost correlation with adjustment factor = 1.")
                            self.horizontalccwelladjfactor.value = 1.0
                        elif not self.horizontalccwellfixed.Provided and self.horizontalccwelladjfactor.Provided and not self.horizontalccwelladjfactor.Valid:
                            print("Warning: Provided horizontal well drilling and completion cost adjustment factor outside of range 0-10. GEOPHIRES will assume default built-in horizontal well drilling and completion cost correlation with adjustment factor = 1.")
                            model.logger.warning("Provided horizontal well drilling and completion cost adjustment factor outside of range 0-10. GEOPHIRES will assume default built-in well drilling and completion cost correlation with adjustment factor = 1.")
                            self.ccwelladjfactor.value = 1.0

        else:
            model.logger.info("No parameters read becuase no content provided")
        model.logger.info("complete "+ str(__class__) + ": " + sys._getframe().f_code.co_name)

    def Calculate(self, model:Model) -> None:
        """
        The Calculate function is where all the calculations are done.
        This function can be called multiple times, and will only recalculate what has changed each time it is called.
        
        :param self: Access variables that belongs to the class
        :param model: The container class of the application, giving access to everything else, including the logger
        :return: Nothing, but it does make calculations and set values in the model
        :doc-author: Malcolm Ross
        """
        model.logger.info("Init " + str(__class__) + ": " + sys._getframe().f_code.co_name)

        #This is where all the calcualtions are made using all the values that have been set.
        #If you sublcass this class, you can choose to run these calculations before (or after) your calculations, but that assumes you have set all the values that are required for these calculations
        #If you choose to sublass this master class, you can also choose to override this method (or not), and if you do, do it before or after you call you own version of this method.  If you do, you can also choose to call this method from you class, which can effectively run the calculations of the superclass, making all thr values available to your methods. but you had n=betteer have set all the paremeters!
        
        #-------------
        #capital costs
        #-------------
        #horizontal well costs. These are calculated whether or not totalcapcostvalid = 1  
        if self.horizontalccwellfixed.Valid:  #increment the cost of wells by the cost of the horizontal sections give by user
            model.economics.Cwell.value = model.economics.Cwell.value + self.horizontalccwellfixed.value*model.clwellbores.numhorizontalsections.value
        else:
            if self.horizontalwellcorrelation.value == WellDrillingCostCorrelation.VERTICAL_SMALL:
                self.C1well = (0.3021*model.clwellbores.l_pipe.value**2 + 584.9112*model.clwellbores.l_pipe.value + 751368.)*1E-6 #well drilling and completion cost in M$/well
            elif self.horizontalwellcorrelation.value == WellDrillingCostCorrelation.DEVIATED_SMALL:
                self.C1well = (0.2898*model.clwellbores.l_pipe.value**2 + 822.1507*model.clwellbores.l_pipe.value + 680563.)*1E-6
            elif self.horizontalwellcorrelation.value == WellDrillingCostCorrelation.VERTICAL_LARGE:
                self.C1well = (0.2818*model.clwellbores.l_pipe.value**2 + 1275.5213*model.clwellbores.l_pipe.value + 632315.)*1E-6
            elif self.horizontalwellcorrelation.value == WellDrillingCostCorrelation.DEVIATED_LARGE:
                self.C1well = (0.2553*model.clwellbores.l_pipe.value**2 + 1716.7157*model.clwellbores.l_pipe.value + 500867.)*1E-6

            self.C1well = self.horizontalccwelladjfactor.value*self.C1well
            model.economics.Cwell.value = model.economics.Cwell.value + 1.05*self.C1well*model.clwellbores.numhorizontalsections.value #1.05 for 5% indirect costs
            
        #adjust the CAPEX for the cost of ther horizontals
        if not  model.economics.totalcapcost.Valid:
            model.economics.CCap.value = model.economics.CCap.value + model.economics.Cwell.value
            #ReCalculate LCOE/LCOH
            model.economics.CalculateLCOELCOH(model)

        model.logger.info("complete "+ str(__class__) + ": " + sys._getframe().f_code.co_name)

    def CalculateLCOELCOH(self, model:Model) -> None:
        model.logger.info("Init " + str(__class__) + ": " + sys._getframe().f_code.co_name)
        #---------------------------
        #Calculate LCOE/LCOH
        #---------------------------
        if self.econmodel.value == EconomicModel.FCR:
            if model.surfaceplant.enduseoption.value == EndUseOptions.ELECTRICITY:
                self.LCOE.value = (self.FCR.value*(1+self.inflrateconstruction.value)*self.CCap.value + self.Coam.value)/np.average(model.surfaceplant.NetkWhProduced.value)*1E8 #cents/kWh
            elif model.surfaceplant.enduseoption.value == EndUseOptions.HEAT:
                self.averageannualpumpingcosts.value = np.average(model.surfaceplant.PumpingkWh.value)*model.surfaceplant.elecprice.value/1E6 #M$/year
                self.LCOH.value = (self.FCR.value*(1+self.inflrateconstruction.value)*self.CCap.value + self.Coam.value + self.averageannualpumpingcosts.value)/np.average(model.surfaceplant.HeatkWhProduced.value)*1E8 #cents/kWh
                self.LCOH.value = self.LCOH.value*2.931 #$/Million Btu
            elif model.surfaceplant.enduseoption.value not in [EndUseOptions.ELECTRICITY, EndUseOptions.HEAT]: #cogeneration
                if model.surfaceplant.enduseoption.value in [EndUseOptions.COGENERATION_TOPPING_EXTRA_HEAT, EndUseOptions.COGENERATION_BOTTOMING_EXTRA_HEAT, EndUseOptions.COGENERATION_PARALLEL_EXTRA_HEAT]: #heat sales is additional income revenue stream
                    averageannualheatincome = np.average(self.HeatkWhProduced.value)*self.heatprice.value/1E6 #M$/year ASSUMING heatprice IS IN $/KWH FOR HEAT SALES
                    self.LCOE.value = (self.FCR.value*(1+self.inflrateconstruction.value)*self.CCap.value + self.Coam.value - averageannualheatincome)/np.average(model.surfaceplant.NetkWhProduced.value)*1E8 #cents/kWh   
                elif model.surfaceplant.enduseoption.value in [EndUseOptions.COGENERATION_TOPPING_EXTRA_ELECTRICTY, EndUseOptions.COGENERATION_BOTTOMING_EXTRA_ELECTRICTY, EndUseOptions.COGENERATION_PARALLEL_EXTRA_ELECTRICTY]: #electricity sales is additional income revenue stream
                    averageannualelectricityincome =  np.average(model.surfaceplant.NetkWhProduced.value)*model.surfaceplant.elecprice.value/1E6 #M$/year
                    self.LCOH.value = (self.CCap.value + self.Coam.value - averageannualelectricityincome)/np.average(model.surfaceplant.HeatkWhProduced.value)*1E8 #cents/kWh
                    self.LCOH.value = self.LCOH.value*2.931 #$/MMBTU
        elif self.econmodel.value == EconomicModel.STANDARDIZED_LEVELIZED_COST:
            discountvector = 1./np.power(1+self.discountrate.value,np.linspace(0,model.surfaceplant.plantlifetime.value-1,model.surfaceplant.plantlifetime.value))
            if model.surfaceplant.enduseoption.value == EndUseOptions.ELECTRICITY:
                self.LCOE.value = ((1+self.inflrateconstruction.value)*self.CCap.value + np.sum(self.Coam.value*discountvector))/np.sum(model.surfaceplant.NetkWhProduced.value*discountvector)*1E8 #cents/kWh
            elif model.surfaceplant.enduseoption.value == EndUseOptions.HEAT:
                self.averageannualpumpingcosts.value = np.average(model.surfaceplant.PumpingkWh.value)*model.surfaceplant.elecprice.value/1E6 #M$/year
                self.LCOH.value = ((1+self.inflrateconstruction.value)*self.CCap.value + np.sum((self.Coam.value+model.surfaceplant.PumpingkWh.value*model.surfaceplant.elecprice.value/1E6)*discountvector))/np.sum(model.surfaceplant.HeatkWhProduced.value*discountvector)*1E8 #cents/kWh
                self.LCOH.value = self.LCOH.value*2.931 #$/MMBTU
            elif model.surfaceplant.enduseoption.value not in [EndUseOptions.ELECTRICITY, EndUseOptions.HEAT]:
                if model.surfaceplant.enduseoption.value  in [EndUseOptions.COGENERATION_TOPPING_EXTRA_HEAT, EndUseOptions.COGENERATION_BOTTOMING_EXTRA_HEAT, EndUseOptions.COGENERATION_PARALLEL_EXTRA_HEAT]: #heat sales is additional income revenue stream
                    annualheatincome = model.surfaceplant.HeatkWhProduced.value*model.surfaceplant.heatprice.value/1E6 #M$/year ASSUMING heatprice IS IN $/KWH FOR HEAT SALES
                    self.LCOE.value = ((1+self.inflrateconstruction.value)*self.CCap.value + np.sum((self.Coam.value-annualheatincome)*discountvector))/np.sum(model.surfaceplant.NetkWhProduced.value*discountvector)*1E8 #cents/kWh
                elif model.surfaceplant.enduseoption.value in [EndUseOptions.COGENERATION_TOPPING_EXTRA_ELECTRICTY, EndUseOptions.COGENERATION_BOTTOMING_EXTRA_ELECTRICTY, EndUseOptions.COGENERATION_PARALLEL_EXTRA_ELECTRICTY]: #electricity sales is additional income revenue stream
                    annualelectricityincome = model.surfaceplant.NetkWhProduced.value*self.elecprice.value/1E6 #M$/year
                    self.LCOH.value = ((1+self.inflrateconstruction.value)*self.CCap.value + np.sum((self.Coam.value-annualelectricityincome)*discountvector))/np.sum(model.surfaceplant.HeatkWhProduced.value*discountvector)*1E8 #cents/kWh
                    self.LCOH.value = self.LCOH.value*2.931 #$/MMBTU
        elif self.econmodel.value == EconomicModel.BICYCLE:
            iave = self.FIB.value*self.BIR.value*(1-self.CTR.value) + (1-self.FIB.value)*self.EIR.value #average return on investment (tax and inflation adjusted)
            CRF = iave/(1-np.power(1+iave,-model.surfaceplant.plantlifetime.value)) #capital recovery factor
            inflationvector = np.power(1+self.RINFL.value,np.linspace(1,model.surfaceplant.plantlifetime.value, model.surfaceplant.plantlifetime.value))
            discountvector = 1./np.power(1+iave,np.linspace(1, model.surfaceplant.plantlifetime.value, model.surfaceplant.plantlifetime.value))
            NPVcap = np.sum((1+self.inflrateconstruction.value)*self.CCap.value*CRF*discountvector)
            NPVfc = np.sum((1+self.inflrateconstruction.value)*self.CCap.value*self.PTR.value*inflationvector*discountvector)
            NPVit = np.sum(self.CTR.value/(1-self.CTR.value)*((1+self.inflrateconstruction.value)*self.CCap.value*CRF-self.CCap.value/model.surfaceplant.plantlifetime.value)*discountvector)
            NPVitc = (1+self.inflrateconstruction.value)*self.CCap.value*self.RITC.value/(1-self.CTR.value)
            if model.surfaceplant.enduseoption.value == EndUseOptions.ELECTRICITY:            
                NPVoandm = np.sum(self.Coam.value*inflationvector*discountvector)
                NPVgrt = self.GTR.value/(1-self.GTR.value)*(NPVcap + NPVoandm + NPVfc + NPVit - NPVitc)
                self.LCOE.value  = (NPVcap + NPVoandm + NPVfc + NPVit + NPVgrt - NPVitc)/np.sum(model.surfaceplant.NetkWhProduced.value*inflationvector*discountvector)*1E8
            elif model.surfaceplant.enduseoption.value == EndUseOptions.HEAT:
                PumpingCosts = model.surfaceplant.PumpingkWh.value*model.surfaceplant.elecprice.value/1E6
                self.averageannualpumpingcosts.value = np.average(model.surfaceplant.PumpingkWh.value)*model.surfaceplant.elecprice.value/1E6 #M$/year
                NPVoandm = np.sum((self.Coam.value+PumpingCosts)*inflationvector*discountvector)
                NPVgrt = self.GTR.value/(1-self.GTR.value)*(NPVcap + NPVoandm + NPVfc + NPVit - NPVitc)
                self.LCOH.value  = (NPVcap + NPVoandm + NPVfc + NPVit + NPVgrt - NPVitc)/np.sum(model.surfaceplant.HeatkWhProduced.value*inflationvector*discountvector)*1E8
                self.LCOH.value = self.LCOH.value*2.931 #$/MMBTU
            elif model.surfaceplant.enduseoption.value not in [EndUseOptions.ELECTRICITY, EndUseOptions.HEAT]:
                if model.surfaceplant.enduseoption.value  in [EndUseOptions.COGENERATION_TOPPING_EXTRA_HEAT, EndUseOptions.COGENERATION_BOTTOMING_EXTRA_HEAT, EndUseOptions.COGENERATION_PARALLEL_EXTRA_HEAT]: #heat sales is additional income revenue stream
                    annualheatincome = model.surfaceplant.HeatkWhProduced.value*model.surfaceplant.heatprice.value/1E6 #M$/year ASSUMING ELECPRICE IS IN $/KWH FOR HEAT SALES
                    NPVoandm = np.sum(self.Coam.value*inflationvector*discountvector)            
                    NPVgrt = self.GTR.value/(1-self.GTR.value)*(NPVcap + NPVoandm + NPVfc + NPVit - NPVitc)
                    self.LCOE.value  = (NPVcap + NPVoandm + NPVfc + NPVit + NPVgrt - NPVitc - np.sum(annualheatincome*inflationvector*discountvector))/np.sum(model.surfaceplant.NetkWhProduced.value*inflationvector*discountvector)*1E8 
                elif model.surfaceplant.enduseoption.value  in [EndUseOptions.COGENERATION_TOPPING_EXTRA_ELECTRICTY, EndUseOptions.COGENERATION_BOTTOMING_EXTRA_ELECTRICTY, EndUseOptions.COGENERATION_PARALLEL_EXTRA_ELECTRICTY]: #electricity sales is additional income revenue stream
                    annualelectricityincome = model.surfaceplant.NetkWhProduced.value*model.surfaceplant.elecprice.value/1E6 #M$/year
                    NPVoandm = np.sum(self.Coam.value*inflationvector*discountvector)
                    NPVgrt = self.GTR.value/(1-self.GTR.value)*(NPVcap + NPVoandm + NPVfc + NPVit - NPVitc)
                    self.LCOH.value  = (NPVcap + NPVoandm + NPVfc + NPVit + NPVgrt - NPVitc - np.sum(annualelectricityincome*inflationvector*discountvector))/np.sum(model.surfaceplant.HeatkWhProduced.value*inflationvector*discountvector)*1E8
                    self.LCOH.value = self.LCOELCOHCombined.value*2.931 #$/MMBTU
        
        model.logger.info("complete "+ str(__class__) + ": " + sys._getframe().f_code.co_name)

    def __str__(self): return "CLEconomics"
