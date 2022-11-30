#! python
# -*- coding: utf-8 -*-
"""
Created on Monday Nov 28 08:54 2022

@author: Malcolm Ross V1
"""

#Heat in Place calculation: Muffler, P., and Raffaele Cataldi. "Methods for regional assessment of geothermal resources." Geothermics 7.2-4 (1978): 53-89.
# and: Garg, S.K. and J. Combs. 2011.  A Reexamination of the USGS Volumetric "Heat in Place" Method.  Stanford University, 36th Workshop on Geothermal Reservoir Engineering; SGP-TR-191, 5 pp.
#build date: December 2022
#github address: https://github.com/malcolm-dsider/GEOPHIRES-X

import os
import sys
import logging
import logging.config
import numpy as np

from GeoPHIRESUtils import read_input_file
#import AdvGeoPHIRESUtils
from Parameter import intParameter, floatParameter, OutputParameter, ReadParameter, CovertUnitsBack, ConvertOutputUnits, LookupUnits
from Units import *

NL="\n"

class HIP_RA():
    #set up logging.
    logging.config.fileConfig('logging.conf')
    logger = logging.getLogger('root')
    logger.info("Init " + str(__name__))
    
    """
    HIP_RA is the container class of the HIP_RA application, giving access to everything else, including the logger
    """

    #define 3 lookup functions for the enthapy (aka "s", kJ/(kg K)) and entropy (aka "h", kJ/kg) of water as a function of T (dec-c) from https://www.engineeringtoolbox.com/water-properties-d_1508.html
    T = [0.01, 10.0, 20.0, 25.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0, 110.0, 120.0, 140.0, 160.0, 180.0, 200.0, 220.0, 240.0, 260.0, 280.0, 300.0, 320.0, 340.0, 360.0, 373.946]
    EntropyH20 = [0.0, 0.15109, 0.29648, 0.36722, 0.43675, 0.5724, 0.70381, 0.83129, 0.95513, 1.0756, 1.1929, 1.3072, 1.4188, 1.5279, 1.7392, 1.9426, 2.1392, 2.3305, 2.5177, 2.702, 2.8849, 3.0685, 3.2552, 3.4494, 3.6601, 3.9167, 4.407]
    EnthalpyH20 = [0.000612, 42.021, 83.914, 104.83, 125.73, 167.53, 209.34, 251.18, 293.07, 335.01, 377.04, 419.17, 461.42, 503.81, 589.16, 675.47, 763.05, 852.27, 943.58, 1037.6, 1135.0, 1236.9, 1345.0, 1462.2, 1594.5, 1761.7, 2084.3]
    UtilEff = [0.0, 0.0, 0.0, 0.0, 0.0057, 0.0337, 0.0617, 0.0897, 0.1177, 0.13, 0.16, 0.19, 0.22, 0.26, 0.29, 0.32, 0.35, 0.38, 0.40, 0.4, 0.4, 0.4, 0.4, 0.4, 0.4, 0.4, 0.4]

    #define 3 lookup functions using polynomial order 3 functions that are a vary as a function of the reservoir temperature in deg-c
    def EntropyH20_func (self, x:float)->float:
        y = np.interp(x, self.T, self.EntropyH20)
        return y

    def EnthalpyH20_func (self, x:float)->float:
        y = np.interp(x, self.T, self.EnthalpyH20)
        return y

    def UtilEff_func (self, x:float)->float:
        y = np.interp(x, self.T, self.UtilEff)
        return y

    def __init__(self):
        """
        The __init__ function is called automatically every time the class is being used to create a new object.
        
        The self parameter is a Python convention. It must be included in each function definition and points to the current instance of the class (the object that is being created). 
        
        :param self: Reference the class instance itself
        :return: Nothing
        :doc-author: Malcolm Ross
        """
        #Initiate the elements of the Model
        #Set up all the Parameters that will be predefined by this class using the different types of parameter classes.  Setting up includes giving it a name, a default value, The Unit Type (length, volume, temperature, etc) and Unit Name of that value, sets it as required (or not), sets allowable range, the error message if that range is exceeded, the ToolTip Text, and the name of teh class that created it.
        #This includes setting up temporary variables that will be available to all the class but noy read in by user, or used for Output
        #This also includes all Parameters that are calculated and then published using the Printouts function.
         
        #These disctionaries contains a list of all the parameters set in this object, stored as "Parameter" and "OutputParameter" Objects.  This will alow us later to access them in a user interface and get that list, along with unit type, preferred units, etc.
        self.ParameterDict = {}
        self.OutputParameterDict = {}
            
        #Inputs
        self.ReservoirTemperature = self.ParameterDict[self.ReservoirTemperature.Name] = floatParameter("Reservoir Temperature", value = 150.0, Min=50, Max = 1000, UnitType = Units.TEMPERATURE, PreferredUnits = TemperatureUnit.CELCIUS, CurrentUnits = TemperatureUnit.CELCIUS, Required=True, ErrMessage = "assume default reservoir temperature (150 deg-C)", ToolTipText="Reservoir Temperature [150 dec-C]")
        self.RejectionTemperature = self.ParameterDict[self.RejectionTemperature.Name] = floatParameter("Rejection Temperature", value = 25.0, Min=0.1, Max = 200, UnitType = Units.TEMPERATURE, PreferredUnits = TemperatureUnit.CELCIUS, CurrentUnits = TemperatureUnit.CELCIUS, Required=True, ErrMessage = "assume default rejection temperature (25 deg-C)", ToolTipText="Rejection Temperature [25 dec-C]")
        self.FormationPorosity = self.ParameterDict[self.FormationPorosity.Name] = floatParameter("Formation Porosity", value = 18.0, Min=0.0, Max = 100.0, UnitType = Units.PERCENT, PreferredUnits = PercentUnit.PERCENT, CurrentUnits = PercentUnit.PERCENT, Required=True, ErrMessage = "assume default formation porosity (18%)", ToolTipText="Formation Porosity [18%]")
        self.ReservoirArea = self.ParameterDict[self.ReservoirArea.Name] = floatParameter("Reservoir Area", value = 81.0, Min=0.0, Max = 10000.0, UnitType = Units.AREA, PreferredUnits = AreaUnit.KILOMETERS2, CurrentUnits = AreaUnit.KILOMETERS2, Required=True, ErrMessage = "assume default reservoir area (81 km2)", ToolTipText="Reservoir Area [81 km2]")
        self.ReservoirThickness = self.ParameterDict[self.ReservoirThickness.Name] = floatParameter("Reservoir Thickness", value = 0.286, Min=0.0, Max = 10000.0, UnitType = Units.LENGTH, PreferredUnits = LengthUnit.KILOMETERS, CurrentUnits = LengthUnit.KILOMETERS, Required=True, ErrMessage = "assume default reservoir thickness (0.286 km2)", ToolTipText="Reservoir Thickness [0.286 km]")
        self.ReservoirLifeCycle = self.ParameterDict[self.ReservoirLifeCycle.Name] = intParameter("Reservoir Life Cycle", value = 30, UnitType=Units.TIME, PreferredUnits = TimeUnit.YEAR, CurrentUnits = TimeUnit.YEAR, AllowableRange=list(range(1,101,1)), Required=True, ErrMessage = "assume default Reservoir Life Cycle (25 years)", ToolTipText="Reservoir Life Cycle [30 years]")

        #user-changeable semi-constants
        self.ReservoirHeatCapacity = self.ParameterDict[self.ReservoirHeatCapacity.Name] = floatParameter("Reservoir Heat Capacity", value = 2.84E+12, Min = 0.0, Max = 1E+14, UnitType=Units.HEAT_CAPACITY, PreferredUnits = HeatCapacityUnit.KJPERKM3C, CurrentUnits = HeatCapacityUnit.KJPERKM3C, Required=True, ErrMessage = "assume default Reservoir Heat Capacity (2.84E+12 kJ/km3C)", ToolTipText="Reservoir Heat Capacity [2.84E+12 kJ/km3C]")
        self.HeatCapacityOfWater = self.ParameterDict[self.HeatCapacityOfWater.Name] = floatParameter("Heat Capacity Of Water", value = 4.18, Min = 3.0, Max = 10.0, UnitType=Units.HEAT_CAPACITY, PreferredUnits = HeatCapacityUnit.kJPERKGC, CurrentUnits = HeatCapacityUnit.kJPERKGC, Required=True, ErrMessage = "assume default Heat Capacity Of Water (4.18 kJ/kgC)", ToolTipText="Heat Capacity Of Water [4.18 kJ/kgC]")
        self.HeatCapacityOfRock = self.ParameterDict[self.HeatCapacityOfRock.Name] = floatParameter("Heat Capacity Of Rock", value = 1.000, Min = 0.0, Max = 10.0, UnitType=Units.HEAT_CAPACITY, PreferredUnits = HeatCapacityUnit.kJPERKGC, CurrentUnits = HeatCapacityUnit.kJPERKGC, Required=True, ErrMessage = "assume default Heat Capacity Of Rock (1.0 kJ/kgC)", ToolTipText="Heat Capacity Of Rock [1.0 kJ/kgC]")
        self.DensityOfWater = self.ParameterDict[self.DensityOfWater.Name] = floatParameter("Density Of Water", value = 1.000E+12, Min = 1.000E+11, Max = 1.000E+13, UnitType=Units.DENSITY, PreferredUnits = DensityUnit.KGPERKILOMETERS3, CurrentUnits = DensityUnit.KGPERKILOMETERS3, Required=True, ErrMessage = "assume default Density Of Water (1.0E+12 kg/km3)", ToolTipText="Heat Density Of Water [1.0E+12 kg/km3]")
        self.DensityOfRock = self.ParameterDict[self.DensityOfRock.Name] = floatParameter("Density Of Rock", value = 2.55E+12, Min = 1.000E+11, Max = 1.000E+13, UnitType=Units.DENSITY, PreferredUnits = DensityUnit.KGPERKILOMETERS3, CurrentUnits = DensityUnit.KGPERKILOMETERS3, Required=True, ErrMessage = "assume default Density Of Water (2.55E+12 kg/km3)", ToolTipText="Heat Density Of Water [2.55E+12 kg/km3]")

        #internal
        self.WaterContent = self.ParameterDict[self.WaterContent.Name] = floatParameter("Water Content", value = 18.0, Min=0.0, Max = 100.0, UnitType = Units.PERCENT, PreferredUnits = PercentUnit.PERCENT, CurrentUnits = PercentUnit.PERCENT, Required=True, ErrMessage = "assume default water content (18%)", ToolTipText="Water Content")
        self.RockContent = self.ParameterDict[self.RockContent.Name] = floatParameter("Rock Content", value = 82.0, Min=0.0, Max = 100.0, UnitType = Units.PERCENT, PreferredUnits = PercentUnit.PERCENT, CurrentUnits = PercentUnit.PERCENT, Required=True, ErrMessage = "assume default rock content (82%)", ToolTipText="Rock Content")
        self.RejectionTemperatureK = self.ParameterDict[self.RejectionTemperatureK.Name] = floatParameter("Rejection Temperature in K", value = 298.15, Min=0.1, Max = 1000.0, UnitType = Units.TEMPERATURE, PreferredUnits = TemperatureUnit.KELVIN, CurrentUnits = TemperatureUnit.KELVIN, Required=True, ErrMessage = "assume default rejection temperature in K (298.15 deg-K)", ToolTipText="Rejection Temperature in K [298.15 deg-K]")
        self.RejectionEntropy = self.ParameterDict[self.RejectionEntropy.Name] = floatParameter("Rejection Entropy", value = 0.3670, Min = 0.0001, Max = 100.0, UnitType=Units.ENTROPY, PreferredUnits = EntropyUnit.KJPERKGK, CurrentUnits = EntropyUnit.KJPERKGK, Required=True, ErrMessage = "assume default Rejection Entropy (0.3670 kJ/kgK @25 deg-C)", ToolTipText="Rejection Entropy [0.3670 kJ/kgK @25 deg-C]")
        self.RejectionEnthalpy = self.ParameterDict[self.RejectionEnthalpy.Name] = floatParameter("Rejection Enthalpy", value = 104.8, Min = 0.0001, Max = 1000.0, UnitType=Units.ENTHALPY, PreferredUnits = EnthalpyUnit.KJPERKG, CurrentUnits = EnthalpyUnit.KJPERKG, Required=True, ErrMessage = "assume default Rejection Enthalpy (104.8 kJ/kg @25 deg-C)", ToolTipText="Rejection Enthalpy [104.8 kJ/kg @25 deg-C]")

        #Outputs
#        self.TRC = self.OutputParameterDict[self.TRC.Name] = OutputParameter(Name = "Reservoir Temperature", value=-999.9, UnitType = Units.TEMPERATURE, PreferredUnits = TemperatureUnit.CELCIUS, CurrentUnits = TemperatureUnit.CELCIUS)
        self.V = self.OutputParameterDict[self.V.Name] = OutputParameter(Name = "Reservoir Volume", value=-999.9, UnitType = Units.VOLUME, PreferredUnits = VolumeUnit.KILOMETERS3, CurrentUnits = VolumeUnit.KILOMETERS3)
        self.qR = self.OutputParameterDict[self.qR.Name] = OutputParameter(Name = "Stored Heat", value=-999.9, UnitType = Units.HEAT, PreferredUnits = HeatUnit.KJ, CurrentUnits = HeatUnit.KJ)
        self.mWH = self.OutputParameterDict[self.mWH.Name] = OutputParameter(Name = "Fluid Produced", value=-999.9, UnitType = Units.MASS, PreferredUnits = MassUnit.KILOGRAM, CurrentUnits = MassUnit.KILOGRAM)
        self.e = self.OutputParameterDict[self.e.Name] = OutputParameter(Name = "Enthalpy", value=-999.9, UnitType = Units.ENTHALPY, PreferredUnits = EnthalpyUnit.KJPERKG, CurrentUnits = EnthalpyUnit.KJPERKG)
        self.qWH = self.OutputParameterDict[self.qWH.Name] = OutputParameter(Name = "Wellhead Heat", value=-999.9, UnitType = Units.HEAT, PreferredUnits = HeatUnit.KJ, CurrentUnits = HeatUnit.KJ)
        self.Rg = self.OutputParameterDict[self.Rg.Name] = OutputParameter(Name = "Recovery Factor", value=-999.9, UnitType = Units.PERCENT, PreferredUnits = PercentUnit.PERCENT, CurrentUnits = PercentUnit.PERCENT)
        self.WA = self.OutputParameterDict[self.WA.Name] = OutputParameter(Name = "Available Heat", value=-999.9, UnitType = Units.HEAT, PreferredUnits = HeatUnit.KJ, CurrentUnits = HeatUnit.KJ)
        self.WE = self.OutputParameterDict[self.WE.Name] = OutputParameter(Name = "Produceable Heat", value=-999.9, UnitType = Units.HEAT, PreferredUnits = HeatUnit.KJ, CurrentUnits = HeatUnit.KJ)
        self.We = self.OutputParameterDict[self.We.Name] = OutputParameter(Name = "Produceable Electricity", value=-999.9, UnitType = Units.ENERGYCOST, PreferredUnits = EnergyUnit.MW, CurrentUnits = EnergyUnit.MW)

        self.logger.info("Complete "+ str(__class__) + ": " + sys._getframe().f_code.co_name)
        
    def read_parameters(self) -> None:
        """
        The read_parameters function reads in the parameters from a dictionary created by reading the user-provided file and updates the parameter values for this object. 
        
        The function reads in all of the parameters that relate to this object, including those that are inherited from other objects. It then updates any of these parameter values that have been changed by the user.  It also handles any special cases.
        
        :param self: Reference the class instance (such as it is) from within the class
        :param model: The container class of the application, giving access to everything else, including the logger
        :return: None
        :doc-author: Malcolm Ross
        """
        self.logger.info("Init " + str(__class__) + ": " + sys._getframe().f_code.co_name)
        
        #declare some dictionaries
        self.InputParameters = {}  #dictionary to hold all the input parameter the user wants to change

        #This should give us a dictionary with all the parameters the user wants to set.  Should be only those value that they want to change from the default.
        #we do this as soon as possible because what we instantiate may depend on settings in this file
        read_input_file(self, self.InputParameters)

        #Deal with all the parameter values that the user has provided.  They should really only provide values that they want to change from the default values, but they can provide a value that is already set because it is a defaulr value set in __init__.  It will ignore those.
        #This also deals with all the special cases that need to be talen care of after a vlaue has been read in and checked.
        #If you choose to sublass this master class, you can also choose to override this method (or not), and if you do, do it before or after you call you own version of this method.  If you do, you can also choose to call this method from you class, which can effectively modify all these superclass parameters in your class.

        if len(self.InputParameters) > 0:
            #loop thru all the parameters that the user wishes to set, looking for parameters that match this object
            for item in self.ParameterDict.items():
                ParameterToModify = item[1]
                key = ParameterToModify.Name.strip()
                if key in self.InputParameters:
                    ParameterReadIn = self.InputParameters[key]
                    ParameterToModify.CurrentUnits = ParameterToModify.PreferredUnits    #Before we change the paremeter, let's assume that the unit preferences will match - if they don't, the later code will fix this.
                    ReadParameter(ParameterReadIn, ParameterToModify, self)   #this should handle all the non-special cases

                    #handle special cases
                    if ParameterToModify.Name == "Formation Porosity":
                        self.WaterContent.value = ParameterToModify.value
                        self.RockContent = 100.0 - ParameterToModify.value

                    elif ParameterToModify.Name == "Rejection Temperature":
                        self.RejectionTemperatureK.value = 273.15 + ParameterToModify.value
                        self.RejectionEntropy.value = self.EntropyH20_func(ParameterToModify.value)
                        self.RejectionEnthalpy.value = self.EnthalpyH20_func(ParameterToModify.value)
        else:
            self.logger.info("No parameters read becuase no content provided")

        #loop thru all the parameters that the user wishes to set, looking for parameters that contain the prefix "Units:" - that means we want to set a special case for converting this output parameter to new units
        for key in self.InputParameters.keys():
            if key.startswith("Units:"):
                #self.ParameterDict[key.replace("Units:", "")] = LookupUnits(self.InputParameters[key].sValue)[0]
                self.OutputParameterDict[key.replace("Units:", "")].CurrentUnits = LookupUnits(self.InputParameters[key].sValue)[0]
                self.OutputParameterDict[key.replace("Units:", "")].UnitsMatch = False

        self.logger.info("complete "+ str(__class__) + ": " + sys._getframe().f_code.co_name)

    def Calculate(self):
        """
        The Calculate function is where all the calculations are made.  This is handled on a class-by-class basis.
        
        The Calculate function does not return anything, but it does store the results for later use by other functions.
        
        :param self: Access the class variables
        :return: None
        :doc-author: Malcolm Ross
        """
        self.logger.info("Init "+ str(__class__) + ": " + sys._getframe().f_code.co_name)
        
        #This is where all the calcualtions are made using all the values that have been set.
        #self.TRC.value = self.ReservoirTemperature.value
        self.V.value = self.ReservoirArea.value * self.ReservoirThickness.value
#        self.qR.value = self.V.value * (self.ReservoirHeatCapacity.value * (self.TRC.value - self.RejectionTemperature.value))
        self.qR.value = self.V.value * (self.ReservoirHeatCapacity.value * (self.ReservoirTemperature.value - self.RejectionTemperature.value))
        self.mWH.value = (self.V.value * (self.FormationPorosity.value/100.0))*self.DensityOfWater.value
 #       self.e.value = (self.EnthalpyH20_func(self.TRC.value) - self.RejectionEnthalpy.value) - (self.RejectionTemperatureK.value*(self.EntropyH20_func(self.TRC.value) - self.RejectionEntropy.value))
        self.e.value = (self.EnthalpyH20_func(self.ReservoirTemperature.value) - self.RejectionEnthalpy.value) - (self.RejectionTemperatureK.value*(self.EntropyH20_func(self.ReservoirTemperature.value) - self.RejectionEntropy.value))
  #      self.qWH.value = self.mWH.value * (self.EnthalpyH20_func(self.TRC.value)-self.RejectionTemperatureK.value)
        self.qWH.value = self.mWH.value * (self.EnthalpyH20_func(self.ReservoirTemperature.value)-self.RejectionTemperatureK.value)
        self.Rg.value = self.qWH.value / self.qR.value
        self.WA.value = self.mWH.value * self.e.value * self.Rg.value
   #     self.WE.value = self.WA.value * self.UtilEff_func(self.TRC.value)
        self.WE.value = self.WA.value * self.UtilEff_func(self.ReservoirTemperature.value)
        self.We.value =(((self.WE.value*0.27777778)/(8760*self.ReservoirLifeCycle.value))/1000000)*0.66
 
        self.logger.info("complete "+ str(__class__) + ": " + sys._getframe().f_code.co_name)

    def PrintOutputs(self):
        """
        PrintOutputs writes the standard outputs to the output file.

        Args:
            model (Model): The container class of the application, giving access to everything else, including the logger
        """
        self.logger.info("Init " + str(__class__) + ": " + sys._getframe().f_code.co_name)
    
        #Deal with converting Units back to PreferredUnits, if required.
        #before we write the outputs, we go thru all the parameters for all of the objects and set the values back to the units that the user entered the data in
        #We do this because the value may be displayed in the output, and we want the user to recginze their value, not some converted value
        for key in self.ParameterDict:
            param = self.ParameterDict[key]
            if not param.UnitsMatch:
                CovertUnitsBack(param, self)

        #now we need to loop thru all thw output parameters to update their units to whatever units the user has specified.
        #i.e., they may have specified that all LENGTH results must be in feet, so we need to convert those from whatver LENGTH unit they are to feet.
        #same for all the other classes of units (TEMPERATURE, DENSITY, etc).
        for key in self.OutputParameterDict:
            if self.OutputParameterDict[key].UnitsMatch != True:
               ConvertOutputUnits(self.OutputParameterDict[key], self.OutputParameterDict[key].CurrentUnits, self)

        #---------------------------------------
        #write results to output file and screen
        #---------------------------------------
        try:
            outputfile = "HIP.out"
            if len(sys.argv) > 2: outputfile = sys.argv[2]
            with open(outputfile,'w', encoding='UTF-8') as f:    
                f.write('                               *********************\n')
                f.write('                               ***HIP CASE REPORT***\n')
                f.write('                               *********************\n')
                f.write(NL)
                f.write('                           ***SUMMARY OF RESULTS***\n')
                f.write(NL)
#                f.write(f"      Reservoir Temperature:   {self.TRC.value:10.2f} " + self.TRC.CurrentUnits.value + NL)
                f.write(f"      Reservoir Temperature:   {self.ReservoirTemperature.value:10.2f} " + self.ReservoirTemperature.CurrentUnits.value + NL)
                f.write(f"      Reservoir Volume:        {self.V.value:10.2f} " + self.V.CurrentUnits.value + NL)
                f.write(f"      Stored Heat:             {self.qR.value:10.2e} " + self.qR.CurrentUnits.value + NL)
                f.write(f"      Fluid Produced:          {self.mWH.value:10.2e} " + self.mWH.CurrentUnits.value + NL)
                f.write(f"      Enthalpy:                {self.e.value:10.2f} " + self.e.CurrentUnits.value + NL)
                f.write(f"      Wellhead Heat:           {self.qWH.value:10.2e} " + self.qWH.CurrentUnits.value + NL)
                f.write(f"      Recovery Factor:         {(100*self.Rg.value):10.2f} "  + self.Rg.CurrentUnits.value + NL)
                f.write(f"      Available Heat:          {self.WA.value:10.2e} " + self.WA.CurrentUnits.value + NL)
                f.write(f"      Produceable Heat:        {self.WE.value:10.2e} " + self.WE.CurrentUnits.value + NL)
                f.write(f"      Produceable Electricity: {self.We.value:10.2f} " + self.We.CurrentUnits.value + NL)
                f.write(NL)
        except BaseException as ex:
            tb = sys.exc_info()[2]
            print (str(ex))
            print("Error: GEOPHIRES failed to Failed to write the output file.  Exiting....Line %i" % tb.tb_lineno)
            self.logger.critical(str(ex))
            self.logger.critical("Error: GEOPHIRES failed to Failed to write the output file.  Exiting....Line %i" % tb.tb_lineno)
            sys.exit()

    #copy the output file to the screen
        with open(outputfile,'r', encoding='UTF-8') as f:
            content = f.readlines()    #store all output in one long list

            #Now write each line to the screen
            for line in content: sys.stdout.write(line)

    def __str__(self):
        return "HIP_RA"

def main():
    #set up logging.
    logging.config.fileConfig('logging.conf')
    logger = logging.getLogger('root')
    logger.info("Init " + str(__name__))

    #set the starting directory to be the directory that this file is in
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    #initiate the HIP-RA parameters, setting them to their default values
    model = HIP_RA()

    #read the parameters that apply to the model
    model.read_parameters()

    #Calculate the entire model
    model.Calculate()

    #write the outputs
    model.PrintOutputs()
    
    logger.info("Complete "+ str(__name__) + ": " + sys._getframe().f_code.co_name)

if __name__ == "__main__": main()