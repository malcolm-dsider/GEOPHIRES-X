import sys
import os
import math
import numpy as np
import AdvModel
import SurfacePlant
import AdvGeoPHIRESUtils
from Parameter import floatParameter, intParameter, boolParameter, OutputParameter, ReadParameter
from Units import *
from OptionList import WorkingFluid, Configuration, EndUseOptions

#code from Koenraad
import h5py
import scipy
from scipy.interpolate import interpn
import itertools as iter

class AGSSurfacePlant(SurfacePlant.SurfacePlant, AdvGeoPHIRESUtils.AdvGeoPHIRESUtils):
    """
    AGSSurfacePlant Child class of SurfacePlant; it is the same, but has advanced AGS closed-loop functionality

    Args:
        SurfacePlant (SurfacePlant): The parent class
        AdvGeoPHIRESUtils (AdvGeoPHIRESUtils): the utilities class
    """
    def __init__(self, model:AdvModel):
        """
        The __init__ function is the constructor for a class.  It is called whenever an instance of the class is created.  The __init__ function can take arguments, but self is always the first one. Self refers to the instance of the object that has already been created and it's used to access variables that belong to that object.&quot;
        
        :param self: Reference the class object itself
        :param model: The container class of the application, giving access to everything else, including the logger

        :return: Nothing, and is used to initialize the class
        :doc-author: Malcolm Ross
        """
        model.logger.info("Init " + str(__class__) + ": " + sys._getframe().f_code.co_name)

        #Initialze the superclass first to gain access to those variables
        super().__init__(model)
        sclass = str(__class__).replace("<class \'", "")
        self.MyClass = sclass.replace("\'>","")
        self.MyPath = os.path.abspath(__file__)

        #Set up all the Parameters that will be predefined by this class using the different types of parameter classes.  Setting up includes giving it a name, a default value, The Unit Type (length, volume, temperature, etc) and Unit Name of that value, sets it as required (or not), sets allowable range, the error message if that range is exceeded, the ToolTip Text, and the name of teh class that created it.
        #This includes setting up temporary variables that will be available to all the class but noy read in by user, or used for Output
        #This also includes all Parameters that are calculated and then published using the Printouts function.
        #If you choose to sublass this master class, you can do so before or after you create your own parameters.  If you do, you can also choose to call this method from you class, which will effectively add and set all these parameters to your class.
        #NB: inputs we already have (marked as "already have it") need to be set at ReadParameter time so values are set at the last possible time

        # already have it:surfaceplant.enduseoption        self.End_use = self.ParameterDict[self.End_use.Name] = intParameter("End-use Application", value = 1, DefaultValue=1, AllowableRange=list(range(1,2,1)), UnitType = Units.NONE, Required=True, ErrMessage = "assume default End-use application is heating (1)")
        # already have it:surfaceplant.pumpeff        self.Pump_efficiency = self.ParameterDict[self.Pump_efficiency.Name] = floatParameter("Pump Efficiency", value = 0.8, DefaultValue=0.8, Min=0.5, Max=1.0, UnitType = Units.PERCENT, PreferredUnits = PercentUnit.TENTH, CurrentUnits = PercentUnit.TENTH, Required=True, ErrMessage = "assume default Pump efficiency for cirulcation pump (if required) (0.8)")
        # already have it:surfaceplant.plantlifetime        self.Lifetime = self.ParameterDict[self.Lifetime.Name] = intParameter("System Lifetime", value = 40, DefaultValue=40, AllowableRange=list(range(5,40,1)), UnitType = Units.TIME, PreferredUnits = TimeUnit.YEAR, CurrentUnits = TimeUnit.YEAR, Required=True, ErrMessage = "assume default System lifetime (40 years)")
        # already have it:surfaceplant.Tenv+273.15        self.T0 = self.ParameterDict[self.T0.Name] = floatParameter("Dead-state Temperature", value = 20+273.15, DefaultValue=20+273.15, Min=5+273.15, Max=25+273.15, UnitType = Units.TEMPERATURE, PreferredUnits = TemperatureUnit.KELVIN, CurrentUnits = TemperatureUnit.KELVIN, Required=True, ErrMessage = "assume default Dead-state temperature (20+273.15 K)")
        self.enduseefficiencyfactor = self.ParameterDict[self.enduseefficiencyfactor.Name] = floatParameter("End-Use Efficiency Factor", value = 0.9, DefaultValue=0.9, Min=0.1, Max = 1.0, UnitType = Units.PERCENT, PreferredUnits = PercentUnit.TENTH, CurrentUnits = PercentUnit.TENTH, ErrMessage="assume default end-use efficiency factor (0.9)", ToolTipText="Constant thermal efficiency of the direct-use application")

        self.P0 = self.ParameterDict[self.P0.Name] = floatParameter("Dead-state Pressure", value = 1e5, DefaultValue=1e5, Min=0.8e5, Max=1.1e5, UnitType = Units.PRESSURE, PreferredUnits = PressureUnit.PASCAL, CurrentUnits = PressureUnit.PASCAL, Required=True, ErrMessage = "assume default Dead-state pressure (1e5 Pa)")

        #Input data for electricity generation with CO2
        self.Turbine_isentropic_efficiency = self.ParameterDict[self.Turbine_isentropic_efficiency.Name] = floatParameter("Isentropic Efficiency for CO2 Turbine", value = 0.9, DefaultValue=0.9, Min=0.8, Max=1.0, UnitType = Units.PERCENT, PreferredUnits = PercentUnit.TENTH, CurrentUnits = PercentUnit.TENTH, Required=False, ErrMessage = "assume default Isentropic efficiency for turbine when CO2 is working fluid (0.9)")
        self.Generator_efficiency = self.ParameterDict[self.Generator_efficiency.Name] = floatParameter("Generator Conversion Efficiency", value = 0.98, DefaultValue=0.98, Min=0.8, Max=1.0, UnitType = Units.PERCENT, PreferredUnits = PercentUnit.TENTH, CurrentUnits = PercentUnit.TENTH, Required=False, ErrMessage = "assume default Conversion efficiency from mechanical turbine work to electricity (0.98)")
        self.Compressor_isentropic_efficiency = self.ParameterDict[self.Compressor_isentropic_efficiency.Name] = floatParameter("Isentropic Efficiency for CO2 Compressor", value = 0.9, DefaultValue=0.9, Min=0.8, Max=1.0, UnitType = Units.PERCENT, PreferredUnits = PercentUnit.TENTH, CurrentUnits = PercentUnit.TENTH, Required=False, ErrMessage = "assume default Isentropic efficiency for compressor when CO2 is working fluid (0.9)")
        self.Pre_Cooling_Delta_T = self.ParameterDict[self.Pre_Cooling_Delta_T.Name] = floatParameter("CO2 Temperature Decline with Cooling", value = 12.0, DefaultValue=12.0, Min=0.0, Max=15.0, UnitType = Units.TEMPERATURE, PreferredUnits = TemperatureUnit.CELCIUS, CurrentUnits = TemperatureUnit.CELCIUS, Required=False, ErrMessage = "assume default CO2 temperature decline with cooling after turbine and before compressor (12 degC)")
        self.Turbine_outlet_pressure = self.ParameterDict[self.Turbine_outlet_pressure.Name] = floatParameter("CO2 Turbine Outlet Pressure", value = 81.0, DefaultValue=81.0, Min=75.0, Max=200.0, UnitType = Units.PRESSURE, PreferredUnits = PressureUnit.BAR, CurrentUnits = PressureUnit.BAR, Required=False, ErrMessage = "assume default CO2 turbine outlet pressure (81 bar)")

        #local variable initiation
        self.P_in = 2e7         #Constant Injection pressure [Pa]
        self.Number_of_points_per_year = 4               #Number of time steps per year in database [-] (must be 4)
        #Initialize error code
        self.error_codes = np.zeros(0)  #if error occurs, code will be assigned to this tag

        #outputs
        self.HeatExtracted = self.OutputParameterDict[self.HeatExtracted.Name] = OutputParameter(Name = "Heat Extracted", value=[0.0], UnitType = Units.POWER, PreferredUnits = PowerUnit.MW, CurrentUnits = PowerUnit.MW)
        self.HeatProduced = self.OutputParameterDict[self.HeatProduced.Name] = OutputParameter(Name = "Heat Produced in MW", value=[0.0], UnitType = Units.POWER, PreferredUnits = PowerUnit.MW, CurrentUnits = PowerUnit.MW)
        self.HeatkWhProduced = self.OutputParameterDict[self.HeatkWhProduced.Name] = OutputParameter(Name = "Heat Produced", value=[0.0], UnitType = Units.ENERGY, PreferredUnits = EnergyUnit.KWH, CurrentUnits = EnergyUnit.KWH)
        self.PumpingkWh = self.OutputParameterDict[self.PumpingkWh.Name] = OutputParameter(Name = "pumping power needed", value = [], UnitType = Units.ENERGY, PreferredUnits = EnergyUnit.KWH, CurrentUnits = EnergyUnit.KWH)
        self.HeatkWhExtracted = self.OutputParameterDict[self.HeatkWhExtracted.Name] = OutputParameter(Name = "Heat Extracted", value = [], UnitType = Units.ENERGY, PreferredUnits = EnergyUnit.KWH, CurrentUnits = EnergyUnit.KWH)
        self.FirstYearElectricityProduction = self.OutputParameterDict[self.FirstYearElectricityProduction.Name] = OutputParameter(Name = "Electricity Produced in the First Year", value = -999.0, UnitType = Units.ENERGY, PreferredUnits = EnergyUnit.KWH, CurrentUnits = EnergyUnit.KWH)
        self.AveInstNetElectricityProduction = self.OutputParameterDict[self.AveInstNetElectricityProduction.Name] = OutputParameter(Name = "Average Net Daily Electricity Production", value = -999.0, UnitType = Units.POWER, PreferredUnits = PowerUnit.KW, CurrentUnits = PowerUnit.KW)
        self.FirstYearHeatProduction = self.OutputParameterDict[self.FirstYearHeatProduction.Name] = OutputParameter(Name = "Heat Produced in the First Year", value = -999.0, UnitType = Units.ENERGY, PreferredUnits = EnergyUnit.KWH, CurrentUnits = EnergyUnit.KWH)
        self.AveInstHeatProduction = self.OutputParameterDict[self.AveInstHeatProduction.Name] = OutputParameter(Name = "Average Net Daily Heat Production", value = -999.0, UnitType = Units.POWER, PreferredUnits = PowerUnit.KW, CurrentUnits = PowerUnit.KW)
        self.AveProductionPressure = self.OutputParameterDict[self.AveProductionPressure.Name] = OutputParameter(Name = "Average Production Pressure", value = -999.0, UnitType = Units.PRESSURE, PreferredUnits = PressureUnit.BAR, CurrentUnits = PressureUnit.BAR)
        self.AveProductionTemperature = self.OutputParameterDict[self.AveProductionTemperature.Name] = OutputParameter(Name = "Average Production Temperature", value = -999.0, UnitType = Units.TEMPERATURE, PreferredUnits = TemperatureUnit.CELCIUS, CurrentUnits = TemperatureUnit.CELCIUS)
        model.logger.info("complete "+ str(__class__) + ": " + sys._getframe().f_code.co_name)
 
    def __str__(self):
        return "AGSSurfacePlant"

    def read_parameters(self, model:AdvModel) -> None:
        """
        The read_parameters function reads in the parameters from a dictionary and stores them in the aparmeters.  It also handles special cases that need to be handled after a value has been read in and checked.  If you choose to sublass this master class, you can also choose to override this method (or not), and if you do
        
        :param self: Access variables that belong to a class
        :param model: The container class of the application, giving access to everything else, including the logger

        :return: None
        :doc-author: Malcolm Ross
        """
        model.logger.info("Init " + str(__class__) + ": " + sys._getframe().f_code.co_name)
        super().read_parameters(model)
        #if we call super, we don't need to deal with setting the parameters here, just deal with the special cases for the variables in this class
        #because the call to the super.readparameters will set all the variables, including the ones that are specific to this class

        if len(model.InputParameters) > 0:
            #loop thru all the parameters that the user wishes to set, looking for parameters that match this object
            for item in self.ParameterDict.items():
                ParameterToModify = item[1]
                key = ParameterToModify.Name.strip()
                if key in model.InputParameters:
                    ParameterReadIn = model.InputParameters[key]

                    #handle special cases
                    if ParameterToModify.Name == "End-Use Option":
                        if ParameterReadIn.sValue == str(1): ParameterToModify.value = EndUseOptions.ELECTRICITY
                        elif ParameterReadIn.sValue == str(2): ParameterToModify.value = EndUseOptions.HEAT
        else:
            model.logger.info("No parameters read becuase no content provided")

        #inputs we already have - needs to be set at ReadParameter time so values set at the latest possible time
        self.End_use = model.surfaceplant.enduseoption.value       #same units are GEOPHIRES
        self.Pump_efficiency = model.surfaceplant.pumpeff.value     #same units are GEOPHIRES
        self.Lifetime = int(model.surfaceplant.plantlifetime.value)     #same units are GEOPHIRES
        self.T0 = model.surfaceplant.Tenv.value + 273.15    #convert Celcius to Kelvin
        self.Discount_rate = model.economics.discountrate.value     #same units are GEOPHIRES

        #For reporting, we need to set some values that are not part of the calculation/extraction, but are seen in the report and need to be consistent
        #model.surfaceplant.Tenv.value = self.T0
        #model.surfaceplant.Tenv.CurrentUnits = TemperatureUnit.KELVIN

        #initialize some arrays
        self.HeatkWhProduced.value = [0.0]*model.surfaceplant.plantlifetime.value #intialize the array
        self.HeatkWhExtracted.value = [0.0]*model.surfaceplant.plantlifetime.value #intialize the array
        self.PumpingkWh.value = [0.0]*model.surfaceplant.plantlifetime.value #intialize the array


        model.logger.info("complete "+ str(__class__) + ": " + sys._getframe().f_code.co_name)

    def verify(self, model:AdvModel) -> int:
        """
        The validate function checks that all values provided are within the range expected by AGS modeling system. These values in within a smaller range than the value ranges available to GEOPHIRES-X
        
        :param self: Access variables that belong to a class
        :param model: The container class of the application, giving access to everything else, including the logger

        :return: 0 if all OK, 1 if error.
        :doc-author: Koenraad Beckers
        """
        model.logger.info("Init " + str(__class__) + ": " + sys._getframe().f_code.co_name) #Verify inputs are within allowable bounds
        self.error = 0
        if self.T0 < 278.15 or self.T0 > 303.15:
            print("Error: CLGS model database imposes additional range restrictions: Dead-state temperature must be between 278.15 and 303.15 K. Simulation terminated.")
            model.logger.fatal("Error: CLGS model database imposes additional range restrictions: Dead-state temperature must be between 278.15 and 303.15 K. Simulation terminated.")
            self.error = 1
        if self.P0.value < 0.8e5 or self.P0.value > 1.1e5:
            print("Error: CLGS model database imposes additional range restrictions: Dead state pressure must be between 0.8e5 and 1.1e5 Pa. Simulation terminated.")
            model.logger.fatal("Error: CLGS model database imposes additional range restrictions: Dead state pressure must be between 0.8e5 and 1.1e5 Pa. Simulation terminated.")
            self.error = 1
        if self.Pump_efficiency < 0.5 or self.Pump_efficiency > 1:
            print("Error: CLGS model database imposes additional range restrictions: Pump efficiency must be between 0.5 and 1. Simulation terminated.")
            model.logger.fatal("Error: CLGS model database imposes additional range restrictions: Pump efficiency must be between 0.5 and 1. Simulation terminated.")
            self.error = 1
        if self.Lifetime < 5 or self.Lifetime > 40:
            print("Error: CLGS model database imposes additional range restrictions: System lifetime must be between 5 and 40 years. Simulation terminated.")
            model.logger.fatal("Error: CLGS model database imposes additional range restrictions: System lifetime must be between 5 and 40 years. Simulation terminated.")
            self.error = 1
        if isinstance(self.Lifetime, int) == False:
            print("Error: CLGS model database imposes additional range restrictions: System lifetime must be integer. Simulation terminated.")
            model.logger.fatal("Error: CLGS model database imposes additional range restrictions: System lifetime must be integer. Simulation terminated.")
            self.error = 1
        if self.Turbine_isentropic_efficiency.value < 0.8 or self.Turbine_isentropic_efficiency.value > 1:
            print("Error: CLGS model database imposes additional range restrictions: Turbine isentropic efficiency must be between 0.8 and 1. Simulation terminated.")
            model.logger.fatal("Error: CLGS model database imposes additional range restrictions: Turbine isentropic efficiency must be between 0.8 and 1. Simulation terminated.")
            self.error = 1
        if self.Generator_efficiency.value < 0.8 or self.Generator_efficiency.value > 1:
            print("Error: CLGS model database imposes additional range restrictions: Generator efficiency must be between 0.8 and 1. Simulation terminated.")
            model.logger.fatal("Error: CLGS model database imposes additional range restrictions: Generator efficiency must be between 0.8 and 1. Simulation terminated.")
            self.error = 1
        if self.Compressor_isentropic_efficiency.value < 0.8 or self.Compressor_isentropic_efficiency.value > 1:
            print("Error: CLGS model database imposes additional range restrictions: Compressor isentropic efficiency must be between 0.8 and 1. Simulation terminated.")
            model.logger.fatal("Error: CLGS model database imposes additional range restrictions: Compressor isentropic efficiency must be between 0.8 and 1. Simulation terminated.")
            self.error = 1
        if self.Pre_Cooling_Delta_T.value < 0 or self.Pre_Cooling_Delta_T.value > 15:
            print("Error: CLGS model database imposes additional range restrictions: CO2 temperature decline after turbine and before compressor must be between 0 and 15 degrees C. Simulation terminated.")
            model.logger.fatal("Error: CLGS model database imposes additional range restrictions: CO2 temperature decline after turbine and before compressor must be between 0 and 15 degrees C. Simulation terminated.")
            self.error = 1
        if self.Turbine_outlet_pressure.value < 75 or self.Turbine_outlet_pressure.value > 200:
            print("Error: CLGS model database imposes additional range restrictions: Turbine outlet pressure must be between 75 and 200 bar. Simulation terminated.")
            model.logger.fatal("Error: CLGS model database imposes additional range restrictions: Turbine outlet pressure must be between 75 and 200 bar. Simulation terminated.")
            self.error = 1
            
        if self.error> 0:             
            print("Error: GEOPHIRES failed to Failed to validate CLGS surfaceplant input value.  Exiting....")
            sys.exit()
        model.logger.info("complete "+ str(__class__) + ": " + sys._getframe().f_code.co_name)
        return self.error

    def calculatepumpingpower(self, model):
        #Calculate pumping power
        self.PumpingPower = (self.P_in-self.Linear_production_pressure)*model.wellbores.prodwellflowrate.value/self.Average_fluid_density/self.Pump_efficiency/1e3 #Pumping power [kW]
        self.PumpingPower[self.PumpingPower<0] = 0 #Set negative values to zero (if the production pressure is above the injection pressure, we throttle the fluid)
        self.Annual_pumping_power = 8760/5*(self.PumpingPower[0::4][0:-1]+self.PumpingPower[1::4]+self.PumpingPower[2::4]+self.PumpingPower[3::4]+self.PumpingPower[4::4]) #kWh
 
    def calculateheatproduction(self, model):
        #Calculate instantaneous heat production
        self.Average_fluid_density = interpn((model.wellbores.Pvector,model.wellbores.Tvector),model.wellbores.density,np.dstack((0.5*self.P_in + 0.5*self.Linear_production_pressure,0.5*model.wellbores.Tinj.value + 0.5*self.Linear_production_temperature+273.15))[0])
        self.hprod = interpn((model.wellbores.Pvector,model.wellbores.Tvector),model.wellbores.enthalpy,np.dstack((self.Linear_production_pressure,self.Linear_production_temperature+273.15))[0])
        self.hinj = interpn((model.wellbores.Pvector,model.wellbores.Tvector),model.wellbores.enthalpy,np.array([self.P_in,model.wellbores.Tinj.value+273.15]))
        self.Instantaneous_heat_production = model.wellbores.prodwellflowrate.value*(self.hprod - self.hinj)/1000 #Heat production based on produced minus injected enthalpy [kW]
        
        #Calculate annual heat production (kWh)
        self.Annual_heat_production = 8760/5*(self.Instantaneous_heat_production[0::4][0:-1]+self.Instantaneous_heat_production[1::4]+self.Instantaneous_heat_production[2::4]+self.Instantaneous_heat_production[3::4]+self.Instantaneous_heat_production[4::4])
      
        #Calculate average heat production
        self.AveAnnualHeatProduction = np.average(self.Annual_heat_production) #kWh
        self.AveInstHeatProduction.value = np.average(self.Instantaneous_heat_production) #kWth
        
        #Calculate average heat production and first year heat production
        self.Average_heat_production = np.average(self.Instantaneous_heat_production) #[kW]
        #Average_production_temperature = np.average(Linear_production_temperature) #[deg.C]
        self.FirstYearHeatProduction.value = self.Annual_heat_production[0] #kWh
        
        self.calculatepumpingpower(model)

    def calculateelectricityproduction(self, model):
        #Calculate instantaneous exergy production, exergy extraction, and electricity generation (MW) and annual electricity generation [kWh]
        self.h_prod = self.hprod #produced enthalpy [J/kg]
        self.h_inj = self.hinj #injected enthalpy [J/kg]
        self.s_prod = interpn((model.wellbores.Pvector,model.wellbores.Tvector),model.wellbores.entropy,np.dstack((self.Linear_production_pressure,self.Linear_production_temperature+273.15))[0]) #produced entropy [J/kg/K]
        self.s_inj = interpn((model.wellbores.Pvector,model.wellbores.Tvector),model.wellbores.entropy,np.array([self.P_in,model.wellbores.Tinj.value+273.15])) #injected entropy [J/kg/K]
            
        self.Instantaneous_exergy_production = (model.wellbores.prodwellflowrate.value*(self.h_prod-self.h_0 - model.surfaceplant.T0*(self.s_prod-self.s_0)))/1000 #[kW]
        self.Instantaneous_exergy_extraction = (model.wellbores.prodwellflowrate.value*(self.h_prod-self.h_inj - model.surfaceplant.T0*(self.s_prod-self.s_inj)))/1000 #[kW]     
            
        self.AverageInstNetExergyProduction = np.average(self.Instantaneous_exergy_production) #[kW]
        self.AverageInstNetExergyExtraction = np.average(self.Instantaneous_exergy_extraction) #[kW]
            
        if model.wellbores.Fluid.value == WorkingFluid.WATER:
            if model.wellbores.Tinj.value >= 50 and min(self.Linear_production_temperature) >= 100 and max(self.Linear_production_temperature) <= 385:
                self.Instantaneous_utilization_efficiency_method_1 = np.interp(self.Linear_production_temperature,self.Utilization_efficiency_correlation_temperatures,self.Utilization_efficiency_correlation_conversion,left = 0) #Utilization efficiency based on conversion of produced exergy to electricity
                self.Instantaneous_electricity_production_method_1 = self.Instantaneous_exergy_production*self.Instantaneous_utilization_efficiency_method_1 #[kW]
                self.Instantaneous_themal_efficiency = np.interp(self.Linear_production_temperature,self.Heat_to_power_efficiency_correlation_temperatures,self.Heat_to_power_efficiency_correlation_conversion,left = 0) #Utilization efficiency based on conversion of produced exergy to electricity
                self.Instantaneous_electricity_production_method_3 = self.Instantaneous_heat_production*self.Instantaneous_themal_efficiency #[kW]
                
            else: #Water injection temperature and/or production tempeature fall outside the range used in the correlations
                self.error_codes = np.append(self.error_codes,2000)
                self.Instantaneous_utilization_efficiency_method_1 = np.zeros(len(self.Time_array))
                self.Instantaneous_electricity_production_method_1 = np.zeros(len(self.Time_array))
                self.Instantaneous_themal_efficiency = np.zeros(len(self.Time_array))
                self.Instantaneous_electricity_production_method_3 = np.zeros(len(self.Time_array))
                    
            #based on method 1 for now (could be 50-50)
            self.Annual_electricity_production = 8760/5*(self.Instantaneous_electricity_production_method_1[0::4][0:-1]+self.Instantaneous_electricity_production_method_1[1::4]+self.Instantaneous_electricity_production_method_1[2::4]+self.Instantaneous_electricity_production_method_1[3::4]+self.Instantaneous_electricity_production_method_1[4::4])
            self.Inst_electricity_production = self.Instantaneous_electricity_production_method_1 #[kW]
            self.AveInstElectricityProduction = np.average(self.Instantaneous_electricity_production_method_1) #[kW]
 
        else:
            T_prod = self.Linear_production_temperature #Production temperature [deg.C]
            P_prod = self.Linear_production_pressure    #Production pressure [Pa]
    
            h_turbine_out_ideal = interpn((model.wellbores.Pvector_ap,model.wellbores.svector_ap),model.wellbores.hPs,np.dstack((np.ones(self.TNOP)*self.Turbine_outlet_pressure.value*1e5,self.s_prod))[0])
            self.Instantaneous_turbine_power = model.wellbores.prodwellflowrate.value*(self.h_prod-h_turbine_out_ideal)*self.Turbine_isentropic_efficiency.value/1000 #Turbine output [kW]
            h_turbine_out_actual = self.h_prod-self.Instantaneous_turbine_power/model.wellbores.prodwellflowrate.value*1000 #Actual fluid enthalpy at turbine outlet [J/kg]
            self.T_turbine_out_actual = interpn((model.wellbores.Pvector_ap,model.wellbores.hvector_ap),model.wellbores.TPh,np.dstack((np.ones(self.TNOP)*self.Turbine_outlet_pressure.value*1e5,h_turbine_out_actual))[0])-273.15 
                
            if min(self.T_turbine_out_actual) > 37 and model.wellbores.Tinj.value > 32:
                self.Pre_cooling_temperature = min(self.T_turbine_out_actual) - self.Pre_Cooling_Delta_T.value
                Post_cooling = 2000
                valuefound = 0
                lastrun = 0
                #print('y')
                while valuefound==0:
                    #print('b')
                    Pre_compressor_h = interpn((model.wellbores.Pvector,model.wellbores.Tvector),model.wellbores.enthalpy,np.array([self.Turbine_outlet_pressure.value*1e5,self.Pre_cooling_temperature+273.15])) 
                    
                    Pre_cooling = model.wellbores.prodwellflowrate.value*(h_turbine_out_actual - Pre_compressor_h)/1e3 #Pre-compressor cooling [kWth]
                    Pre_compressor_s = interpn((model.wellbores.Pvector,model.wellbores.Tvector),model.wellbores.entropy,np.array([self.Turbine_outlet_pressure.value*1e5,self.Pre_cooling_temperature+273.15])) 
                    
                    Post_compressor_h_ideal = interpn((model.wellbores.Pvector_ap,model.wellbores.svector_ap),model.wellbores.hPs,np.array([self.P_in,Pre_compressor_s[0]])) 
                    Post_compressor_h_actual = Pre_compressor_h + (Post_compressor_h_ideal-Pre_compressor_h)/self.Compressor_isentropic_efficiency.value #Actual fluid enthalpy at compressor outlet [J/kg]
                    self.Post_compressor_T_actual = interpn((model.wellbores.Pvector_ap,model.wellbores.hvector_ap),model.wellbores.TPh,np.array([self.P_in,Post_compressor_h_actual[0]])) - 273.15
                    Compressor_Work = model.wellbores.prodwellflowrate.value*(Post_compressor_h_actual - Pre_compressor_h)/1e3 #[kWe]
                    Post_cooling = model.wellbores.prodwellflowrate.value*(Post_compressor_h_actual - self.h_inj)/1e3 #Fluid cooling after compression [kWth]
                    #print(str(Post_cooling))
                    #print(str(self.Pre_cooling_temperature))
                    
                    if lastrun == 0:
                        if self.Pre_cooling_temperature < 32:
                            lastrun = 1                        
                            self.Pre_cooling_temperature = self.Pre_cooling_temperature + 0.5
                        elif Post_cooling < 0:
                            self.Pre_cooling_temperature = self.Pre_cooling_temperature + 0.5
                            lastrun = 1
                        elif Post_cooling >0:
                            self.Pre_cooling_temperature = self.Pre_cooling_temperature - 0.5
                    
                    elif lastrun == 1:
                        valuefound = 1
                        print(self.Pre_cooling_temperature - min(self.T_turbine_out_actual))

                    #print(min(self.T_turbine_out_actual))
                    #print(self.Pre_cooling_temperature)

                if Post_cooling<0:
                    ResistiveHeating = -Post_cooling
                    Post_cooling = 0
                else: ResistiveHeating = 0
                   
                Total_cooling = Pre_cooling + Post_cooling #Total CO2 cooling requirements [kWth]
                
                T_air_in_pre_cooler = self.T0-273.15
                T_air_out_pre_cooler = (self.T_turbine_out_actual+self.Pre_cooling_temperature)/2 #Air outlet temperature in pre-cooler [deg.C]
                cp_air = np.interp(0.5*T_air_in_pre_cooler+0.5*T_air_out_pre_cooler,self.Tair_for_cp_array,self.cp_air_array) #Air specific heat capacity in pre-cooler [J/kg/K]
                m_air_pre_cooler = Pre_cooling*1000/(cp_air*(T_air_out_pre_cooler - T_air_in_pre_cooler)) #Air flow rate in pre-cooler [kg/s]
               
                T_air_in_post_cooler = self.T0-273.15
                T_air_out_post_cooler = (self.Post_compressor_T_actual+model.wellbores.Tinj.value)/2 #Air outlet temperature in post-cooler [deg.C]
                cp_air = np.interp(0.5*T_air_in_post_cooler+0.5*T_air_out_post_cooler,self.Tair_for_cp_array,self.cp_air_array) #Air specific heat capacity in post-cooler [J/kg/K]
                    
                m_air_post_cooler = Post_cooling*1000/(cp_air*(T_air_out_post_cooler - T_air_in_post_cooler)) #Air flow rate in post-cooler [kg/s]
                
                Air_cooling_power = (m_air_pre_cooler+m_air_post_cooler)*0.25  #Electricity for air-cooling, assuming 0.25 kWe per kg/s [kWe] 
                #print(self.Instantaneous_turbine_power)
                #print(Compressor_Work)
                self.Instantaneous_electricity_production_method_4 = self.Instantaneous_turbine_power*self.Generator_efficiency.value-Compressor_Work-Air_cooling_power-ResistiveHeating # Net electricity using CO2 direct turbine expansion cycle [kWe]
                self.Inst_electricity_production = self.Instantaneous_electricity_production_method_4 #[kW]
                self.Annual_electricity_production = 8760/5*(self.Instantaneous_electricity_production_method_4[0::4][0:-1]+self.Instantaneous_electricity_production_method_4[1::4]+self.Instantaneous_electricity_production_method_4[2::4]+self.Instantaneous_electricity_production_method_4[3::4]+self.Instantaneous_electricity_production_method_4[4::4])
                self.AveInstElectricityProduction = np.average(self.Instantaneous_electricity_production_method_4) #[kW]
                #check if negative
                if min(self.Instantaneous_electricity_production_method_4)<0:
                    self.error_codes = np.append(self.error_codes,5500) #Calculated electricity generation is negative
                    self.Annual_electricity_production = np.zeros(self.Lifetime)
                    self.Inst_electricity_production = np.zeros(self.TNOP)
                    self.AveInstElectricityProduction = 0
            else: #turbine outlet or reinjection temperature too low
                if (model.wellbores.Tinj.value <= 32): self.error_codes = np.append(self.error_codes,3000)
                if (min(self.T_turbine_out_actual)<=37): self.error_codes = np.append(self.error_codes,4000)
                    
                self.Annual_electricity_production = np.zeros(self.Lifetime)
                self.Inst_electricity_production = np.zeros(self.TNOP)
                self.AveInstElectricityProduction = 0
        
        self.calculatepumpingpower(model)
        
        self.Average_electricity_production = np.average(self.Annual_electricity_production)/8760 #[kW]
        self.AveAnnualElectricityProduction = np.average(self.Annual_electricity_production) #[kWh]
        self.AveInstNetElectricityProduction.value = self.AveInstElectricityProduction - np.average(self.PumpingPower) #[kW]
        if self.AveInstNetElectricityProduction.value < 0: self.AveInstNetElectricityProduction.value = 0
        self.AveAnnualNetElectricityProduction = self.AveAnnualElectricityProduction - np.average(self.Annual_pumping_power) #kWh
        self.FirstYearElectricityProduction.value = self.Annual_electricity_production[0] #kWh
        self.Inst_Net_Electricity_production = self.Inst_electricity_production-self.PumpingPower #[kW]
 
    def initialize(self, model:AdvModel) -> None:
        """
        The initialize function reads values and arrays to be in the format that AGS model systems expects
        
        :param self: Access variables that belong to a class
        :param model: The container class of the application, giving access to everything else, including the logger

        :return: None
        :doc-author: Koenraad Beckers
        """
        model.logger.info("Init " + str(__class__) + ": " + sys._getframe().f_code.co_name)
        
        self.Time_array = np.linspace(0,self.Lifetime*365*24*3600,1+self.Lifetime*self.Number_of_points_per_year) #[s]
        self.Linear_time_distribution = self.Time_array/365/24/3600
        self.TNOP = (self.Lifetime*self.Number_of_points_per_year+1)      #Total number of points for selected lifetime
        #Find closests lifetime
        closestlifetime = model.wellbores.timearray.flat[np.abs(model.wellbores.timearray - self.Lifetime).argmin()]    
        self.indexclosestlifetime = np.where(model.wellbores.timearray == closestlifetime)[0][0]

        #Initialize heat/electricity arrays
        self.Instantaneous_production_enthalpy = np.zeros(len(self.Time_array))
        self.Instantaneous_temperature_after_isenthalpic_throttling = np.zeros(len(self.Time_array))
        self.Instantaneous_heat_production = np.zeros(len(self.Time_array))
        self.Annual_heat_production = np.zeros(self.Lifetime)
        self.Annual_pumping_power = np.zeros(self.Lifetime)
        self.Average_fluid_density = np.zeros(len(self.Time_array))

        if self.End_use == EndUseOptions.ELECTRICITY:
            #Define ORC power plant conversion efficiencies
            self.Utilization_efficiency_correlation_temperatures = np.array([100, 200, 385]) #Linear correlation assumed here based on GEOPHIRES ORC correlation between 100 and 200 deg C [deg.C] plus plateaued above 200 deg. C
            self.Utilization_efficiency_correlation_conversion = np.array([0.2, 0.45, 0.45])  #Efficiency of ORC conversion from production exergy to electricity based on GEOPHIRES correlation [-]
            self.Heat_to_power_efficiency_correlation_temperatures = np.array([100, 200, 385]) #Linear correlation based on Chad Augustine's thesis [deg.C] plus plateaued above 200 deg. C
            self.Heat_to_power_efficiency_correlation_conversion = np.array([0.05, 0.14, 0.14]) #Conversion from enthalpy to electricity [-]

            self.Instantaneous_exergy_production = np.zeros(len(self.Time_array))  #Produced exergy only (independent from injection conditions)
            self.Instantaneous_exergy_extraction = np.zeros(len(self.Time_array))  #Difference between produced exergy and injected exergy
            self.Instantaneous_electricity_production_method_1 = np.zeros(len(self.Time_array)) #based on exergy produced (only for water)
            self.Instantaneous_electricity_production_method_2 = np.zeros(len(self.Time_array)) #based on exergy extracted
            self.Instantaneous_electricity_production_method_3 = np.zeros(len(self.Time_array)) #based on thermal efficiency
            self.Instantaneous_electricity_production_method_4 = np.zeros(len(self.Time_array)) #based on direct turbine expansion (for CO2)
            self.Instantaneous_utilization_efficiency_method_1 = np.zeros(len(self.Time_array)) #conversion from produced exergy to electricity
            self.Instantaneous_utilization_efficiency_method_2 = np.zeros(len(self.Time_array)) #conversion from extracted exergy to electricity
            self.Instantaneous_themal_efficiency = np.zeros(len(self.Time_array)) #conversion from enthalpy to electricity
            self.Annual_electricity_production = np.zeros(self.Lifetime)
        if model.wellbores.Fluid.value == WorkingFluid.SCO2.value:
            self.Instantaneous_turbine_power = np.zeros(len(self.Time_array)) #Direct turbine expansion considered for systems using sCO2
        
        #Calculate dead-state enthalpy and entropy in case of electricity production
        if self.End_use == EndUseOptions.ELECTRICITY:
            self.h_0 = interpn((model.wellbores.Pvector,model.wellbores.Tvector),model.wellbores.enthalpy,np.array([model.surfaceplant.P0.value, model.surfaceplant.T0]))[0] #dead-state enthalpy [J/kg]
            self.s_0 = interpn((model.wellbores.Pvector,model.wellbores.Tvector),model.wellbores.entropy,np.array([model.surfaceplant.P0.value, model.surfaceplant.T0]))[0] #dead-state entropy [J/kg/K]

        #Pre-populate specific heat capacity of air in case of electricity production
        if self.End_use.value == "Electricity":
            self.Tair_for_cp_array = np.linspace(0,100,num=10)
            self.cp_air_array = np.array([1005.65818063, 1005.87727966, 1006.19281999, 1006.60616167, 1007.11890862, 1007.73265999, 1008.44882744, 1009.26850304, 1010.19236691, 1011.2206266])
              
        #Initialize error code
        self.error_codes = np.zeros(0)  #if error occurs, code will be assigned to this tag

        model.logger.info("complete "+ str(__class__) + ": " + sys._getframe().f_code.co_name)

    def Calculate(self, model:AdvModel) -> None:
        """
        The calculate function verifies, initializes, and extracts the values from the AGS model
        
        :param self: Access variables that belong to a class
        :param model: The container class of the application, giving access to everything else, including the logger

        :return: None
        :doc-author: Koenraad Beckers
        """
        model.logger.info("Init " + str(__class__) + ": " + sys._getframe().f_code.co_name)
        if (model.wellbores.Tini > 375.0) or (model.wellbores.numnonverticalsections.value > 1): #must be a multilateral setup or too hot for CLGS, so must try to use the parent code.
               super().Calculate(model)    #run the parent calculation
        else:
            err = self.verify(model)
            if err> 0:
                model.logger.fatal("Error: GEOPHIRES failed to Failed to validate CLGS input value.  Exiting....")
                print("Error: GEOPHIRES failed to Failed to validate CLGS input value.  Exiting....")
                sys.exit()
            self.initialize(model)

            self.Linear_production_temperature = model.wellbores.InterpolatedTemperatureArray
            self.Linear_production_pressure = model.wellbores.InterpolatedPressureArray
            self.AveProductionTemperature.value = np.average(self.Linear_production_temperature)
            self.AveProductionPressure.value = np.average(self.Linear_production_pressure)/1e5  #[bar]
#            self.Flow_rate = self.prodwellflowrate.value #Total flow rate [kg/s]
            if min(self.Linear_production_temperature) > model.wellbores.Tinj.value:
                self.calculateheatproduction(model)
                if self.End_use == EndUseOptions.ELECTRICITY: self.calculateelectricityproduction(model)
            else: self.error_codes = np.append(self.error_codes,1000) #Production temperature went below injection temperature

            #Now transfer the results to the GEOPHIRES-X arrays: Deep Copy the Arrays 
            model.wellbores.ProducedTemperature.value = self.Linear_production_temperature.copy()
            self.TenteringPP.value = model.wellbores.ProducedTemperature.value
            model.wellbores.PumpingPower.value = self.Annual_pumping_power.copy()
            self.HeatExtracted.value = self.Instantaneous_heat_production.copy()
            self.HeatExtracted.value = self.HeatExtracted.value / 1000.0    #convert to MW because that is what GEOPHIRES expects
            self.HeatProduced.value = self.HeatExtracted.value*self.enduseefficiencyfactor.value #useful direct-use heat provided to application [MWth]
            for i in range(0,self.plantlifetime.value):
                self.HeatkWhExtracted.value[i] = np.trapz(self.HeatExtracted.value[(0+i*model.economics.timestepsperyear.value):((i+1)*model.economics.timestepsperyear.value)+1],dx = 1./model.economics.timestepsperyear.value*365.*24.)*1000.*self.utilfactor.value
                self.PumpingkWh.value[i] = np.trapz(model.wellbores.PumpingPower.value[(0+i*model.economics.timestepsperyear.value):((i+1)*model.economics.timestepsperyear.value)+1],dx = 1./model.economics.timestepsperyear.value*365.*24.)*1000.*self.utilfactor.value

            self.RemainingReservoirHeatContent.value = model.reserv.InitialReservoirHeatContent.value-np.cumsum(self.HeatkWhExtracted.value)*3600*1E3/1E15

            if self.End_use != EndUseOptions.ELECTRICITY:
                self.HeatkWhProduced.value = np.zeros(self.plantlifetime.value)
                for i in range(0,self.plantlifetime.value):
                    self.HeatkWhProduced.value[i] = np.trapz(self.HeatProduced.value[(0+i*model.economics.timestepsperyear.value):((i+1)*model.economics.timestepsperyear.value)+1],dx = 1./model.economics.timestepsperyear.value*365.*24.)*1000.*self.utilfactor.value
            else:
                self.TotalkWhProduced.value = self.Annual_electricity_production.copy()
                self.ElectricityProduced.value = self.Annual_electricity_production.copy() / 8760.0 / 1000.0   #copy the array so we have a GEOPHIRES equivilent (in MW)
                f = scipy.interpolate.interp1d(np.arange(0, len(self.ElectricityProduced.value)), self.ElectricityProduced.value, fill_value="extrapolate")
                self.ElectricityProduced.value = f(np.arange(0, 40, 1.0))   # use interpolation function returned by `interp1d` - interpolate down to report for reporting

                self.NetElectricityProduced.value = self.Inst_Net_Electricity_production.copy()   #copy the array so we have a GEOPHIRES equivilent
                self.NetElectricityProduced.value = self.NetElectricityProduced.value/1000.0     #covert to MW, which is what GEOPHIRES expects
                f = scipy.interpolate.interp1d(np.arange(0, len(self.NetElectricityProduced.value)), self.NetElectricityProduced.value, fill_value="extrapolate")
                self.NetElectricityProduced.value = f(np.arange(0, 40, 1.0))   # use interpolation function returned by `interp1d` - interpolate down to report for reporting
                self.NetkWhProduced.value = (self.NetElectricityProduced.value*1000.0) * 8760.0

                self.FirstLawEfficiency.value = (self.NetElectricityProduced.value*1000.0)/self.AveInstHeatProduction.value

        #handle errors
        if len(self.error_codes) > 0:
            model.logger.fatal("failed with the following error codes: " + str(self.error_codes[0:]) +" in "+ str(__class__) + " " + os.path.abspath(__file__))
            print("Error: failed with the following error codes" + str(self.error_codes[0:]) +" in "+ str(__class__) + " " + os.path.abspath(__file__) +".  Exiting....")
            sys.exit()
        #store the calculate result and associated object paremeters in the database
        resultkey = self.store_result(model, self)
        if resultkey == None: pass
        elif resultkey == -1: model.logger.warn("Failed To Store "+ str(__class__) + " " + os.path.abspath(__file__))
        else:
            model.logger.info("complete "+ str(__class__) + ": " + sys._getframe().f_code.co_name)
        
    def __str__(self):
        return "AGSSurfacePlant"