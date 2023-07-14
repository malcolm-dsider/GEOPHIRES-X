import sys
import os
import math
import numpy as np
import AdvModel
import WellBores
import AdvGeoPHIRESUtils
from Parameter import floatParameter, intParameter, boolParameter, OutputParameter, ReadParameter
from Units import *
from OptionList import WorkingFluid, Configuration, EndUseOptions

#code from Koenraad
import h5py
import scipy
from scipy.interpolate import interpn
import itertools as iter

class data:
  def __init__(self, fname, case, fluid):

    self.fluid = fluid
    self.case = case

    with h5py.File(fname, 'r') as file:
      fixed_loc = "/" + case + "/fixed_params/"
      input_loc = "/" + case + "/" + fluid + "/input/"
      output_loc = "/" + case + "/" + fluid + "/output/"

      # independent vars
      self.mdot = file[input_loc + "mdot"][:]  # i0
      self.L2 = file[input_loc + "L2"][:]  # i1
      self.L1 = file[input_loc + "L1"][:]  # i2
      self.grad = file[input_loc + "grad"][:]  # i3
      self.D = file[input_loc + "D"][:]  # i4
      self.Tinj = file[input_loc + "T_i"][:]  # i5
      self.k = file[input_loc + "k_rock"][:]  # i6
      self.time = file[input_loc + "time"][:]  # i7
      self.ivars = (self.mdot, self.L2, self.L1, self.grad, self.D, self.Tinj, self.k, self.time)

      # fixed vars
      self.Pinj = file[fixed_loc + "Pinj"][()]
      self.Tamb = file[fixed_loc + "Tamb"][()]

      # dim = Mdot x L2 x L1 x grad x D x Tinj x k
      self.Wt = file[output_loc + "Wt"][:]  # int mdot * dh dt
      self.We = file[output_loc + "We"][:]  # int mdot * (dh - Too * ds) dt

      self.GWhr = 1e6 * 3_600_000.0

      self.kWe_avg = self.We * self.GWhr / (1000. * self.time[-1] * 86400. * 365.)
      self.kWt_avg = self.Wt * self.GWhr / (1000. * self.time[-1] * 86400. * 365.)

      # dim = Mdot x L2 x L1 x grad x D x Tinj x k x time
      self.shape = (
          len(self.mdot),
          len(self.L2),
          len(self.L1),
          len(self.grad),
          len(self.D),
          len(self.Tinj),
          len(self.k),
          len(self.time))
      self.Tout = self.__uncompress(file, output_loc, "Tout")
      self.Pout = self.__uncompress(file, output_loc, "Pout")

    self.CP_fluid = "CO2"
    if (fluid == "H2O"):
      self.CP_fluid = "H2O"

  def __uncompress(self, file, output_loc, state):
    U = file[output_loc + state + "/" + "U"][:]
    sigma = file[output_loc + state + "/" + "sigma"][:]
    Vt = file[output_loc + state + "/" + "Vt"][:]
    M_k = np.dot(U, np.dot(np.diag(sigma), Vt))

    shape = self.shape
    valid_runs = np.argwhere(np.isfinite(self.We.flatten()))[:, 0]
    M_k_full = np.full((shape[-1], np.prod(shape[:-1])), np.nan)
    M_k_full[:, valid_runs] = M_k
    return np.reshape(M_k_full.T, shape)

  def interp_outlet_states(self, point):
    points = list(iter.product(
            (point[0],),
            (point[1],),
            (point[2],),
            (point[3],),
            (point[4],),
            (point[5],),
            (point[6],),
            self.time))
    try:
        Tout = interpn(self.ivars, self.Tout, points)
        Pout = interpn(self.ivars, self.Pout, points)
                                    
    except BaseException as ex:
        tb = sys.exc_info()[2]
        print (str(ex))
        print("Error: GEOPHIRES failed to Failed to write the output file.  Exiting....Line %i" % tb.tb_lineno)
        sys.exit()
    return Tout, Pout

  def interp_kWe_avg(self, point):
    ivars = self.ivars[:-1]
    return self.GWhr * interpn(ivars, self.We, point) / (1000. * self.time[-1] * 86400. * 365.)

  def interp_kWt_avg(self, point):
    ivars = self.ivars[:-1]
    return self.GWhr * interpn(ivars, self.Wt, point) / (1000. * self.time[-1] * 86400. * 365.)

class CLGSWellBores(WellBores.WellBores, AdvGeoPHIRESUtils.AdvGeoPHIRESUtils):
    """
    CLGSWellBores Child class of WellBores; it is the same, but has advanced CLGS closed-loop functionality

    Args:
        WellBores (WellBores): The parent class
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
        
        self.Fluid = self.ParameterDict[self.Fluid.Name] = intParameter("Heat Transfer Fluid", value = WorkingFluid.WATER, DefaultValue=WorkingFluid.WATER, AllowableRange=list(range(1,2,1)), UnitType = Units.NONE, Required=True, ErrMessage = "assume default Heat transfer fluid is water (1)")
        self.Configuration = self.ParameterDict[self.Configuration.Name] = intParameter("Closed-loop Configuration", value = Configuration.COAXIAL, DefaultValue=Configuration.COAXIAL, AllowableRange=list(range(1,2,1)), UnitType = Units.NONE, Required=True, ErrMessage = "assume default closed-loop configuration is co-axial with injection in annulus (2)")
        # already have it:surfaceplant.enduseoption        self.End_use = self.ParameterDict[self.End_use.Name] = intParameter("End-use Application", value = 1, DefaultValue=1, AllowableRange=list(range(1,2,1)), UnitType = Units.NONE, Required=True, ErrMessage = "assume default End-use application is heating (1)")

        #Input data for subsurface condition
        self.Hor_length = self.ParameterDict[self.Hor_length.Name] = floatParameter("Total Horizontal Length", value = 1000.0, DefaultValue=1000.0, Min=1000.0, Max=20000.0, UnitType = Units.LENGTH, PreferredUnits = LengthUnit.METERS, CurrentUnits = LengthUnit.METERS, Required=True, ErrMessage = "assume default Total horizontal length (1000 m)")
        self.Drilling_cost_per_m = self.ParameterDict[self.Drilling_cost_per_m.Name] = floatParameter("Drilling Cost per Meter of Measured Depth", value = 1000.0, DefaultValue=1000.0, Min=0.0, Max=10000.0, UnitType = Units.COSTPERDISTANCE, PreferredUnits = CostPerDistanceUnit.DOLLARSPERM, CurrentUnits = CostPerDistanceUnit.DOLLARSPERM, Required=True, ErrMessage = "assume default Drilling cost per meter of measured depth (1000 USD/m)")
        self.O_and_M_cost_plant = self.ParameterDict[self.O_and_M_cost_plant.Name] = floatParameter("Operation & Maintenance Cost of Surface Plant", value = 0.015, DefaultValue=0.015, Min=0.0, Max=0.2, UnitType = Units.PERCENT, PreferredUnits = PercentUnit.TENTH, CurrentUnits = PercentUnit.TENTH, Required=True, ErrMessage = "assume default Operation & Maintenance cost of surface plant expressed as fraction of total surface plant capital cost (0.015)")
        # already have it:wellbores.prodwellflowrate        self.Flow = self.ParameterDict[self.Flow.Name] = floatParameter("Total Mass Flow Rate", value = 69.6, DefaultValue=69.6, Min=5.0, Max=100.0, UnitType = Units.FLOWRATE, PreferredUnits = FlowRateUnit.KGPERSEC, CurrentUnits = FlowRateUnit.KGPERSEC, Required=True, ErrMessage = "assume default Total mass flow rate (69.6 g/s)")
        # already have it:reserv.depth        self.Depth = self.ParameterDict[self.Depth.Name] = floatParameter("Vertical Depth", value = 5000.0, DefaultValue=5000.0, Min=1000.0, Max=5000.0, UnitType = Units.LENGTH, PreferredUnits = LengthUnit.METERS, CurrentUnits = LengthUnit.METERS, Required=True, ErrMessage = "assume default Vertical depth (5000 m)")
        # already have it:reserv.gradient[0]        self.Gradient = self.ParameterDict[self.Gradient.Name] = floatParameter("Geothermal Gradient", value = 0.07, DefaultValue=0.07, Min=0.03, Max=0.07, UnitType = Units.TEMP_GRADIENT, PreferredUnits = TemperatureGradientUnit.DEGREESCPERM, CurrentUnits = TemperatureGradientUnit.DEGREESCPERM, Required=True, ErrMessage = "assume default Geothermal gradient (0.07 DegC/m)")
        # already have it:model.wellbores.prodwelldiam/39.37        self.Diameter = self.ParameterDict[self.Diameter.Name] = floatParameter("Well Diameter", value = 0.4445, DefaultValue=0.4445, Min=0.2159, Max=0.4445, UnitType = Units.LENGTH, PreferredUnits = LengthUnit.METERS, CurrentUnits = LengthUnit.METERS, Required=True, ErrMessage = "assume default Well diameter (.4445 m)")
        # already have it:wellbores.Tinj+273.15        self.Tin = self.ParameterDict[self.Tin.Name] = floatParameter("Injection Temperature", value = 60+273.15, DefaultValue=60+273.15, Min=30+273.15, Max=60+273.15, UnitType = Units.TEMPERATURE, PreferredUnits = TemperatureUnit.KELVIN, CurrentUnits = TemperatureUnit.KELVIN, Required=True, ErrMessage = "assume default Injection temperature (60+273.15 K)")
        # already have it:reserv.krock        self.krock = self.ParameterDict[self.krock.Name] = floatParameter("Rock Thermal Conductivity", value = 4.5, DefaultValue=4.5, Min=1.5, Max=4.5, UnitType = Units.THERMAL_CONDUCTIVITY, PreferredUnits = ThermalConductivityUnit.WPERMPERK, CurrentUnits = ThermalConductivityUnit.WPERMPERK, Required=True, ErrMessage = "assume default Rock thermal conductivity (4.5 W/m/K)")
        # already have it:economics.discountrate        self.Discount_rate = self.ParameterDict[self.Discount_rate.Name] = floatParameter("Discount Rate", value = 0.07, DefaultValue=0.07, Min=0.0, Max=0.2, UnitType = Units.PERCENT, PreferredUnits = PercentUnit.TENTH, CurrentUnits = PercentUnit.TENTH, Required=True, ErrMessage = "assume default Discount rate for discounting future expenses and income to today's dollars (0.015)")
        # already have it:surfaceplant.pumpeff        self.Pump_efficiency = self.ParameterDict[self.Pump_efficiency.Name] = floatParameter("Pump Efficiency", value = 0.8, DefaultValue=0.8, Min=0.5, Max=1.0, UnitType = Units.PERCENT, PreferredUnits = PercentUnit.TENTH, CurrentUnits = PercentUnit.TENTH, Required=True, ErrMessage = "assume default Pump efficiency for cirulcation pump (if required) (0.8)")
        # already have it:surfaceplant.plantlifetime        self.Lifetime = self.ParameterDict[self.Lifetime.Name] = intParameter("System Lifetime", value = 40, DefaultValue=40, AllowableRange=list(range(5,40,1)), UnitType = Units.TIME, PreferredUnits = TimeUnit.YEAR, CurrentUnits = TimeUnit.YEAR, Required=True, ErrMessage = "assume default System lifetime (40 years)")

        #Input data for direct-use
        self.Direct_use_heat_cost_per_kWth = self.ParameterDict[self.Direct_use_heat_cost_per_kWth.Name] = floatParameter("Capital Cost for Surface Plant for Direct-use System", value = 100.0, DefaultValue=100.0, Min=0.0, Max=10000.0, UnitType = Units.ENERGYCOST, PreferredUnits = EnergyCostUnit.DOLLARSPERKW, CurrentUnits = EnergyCostUnit.DOLLARSPERKW, Required=False, ErrMessage = "assume default Capital cost for surface plant for direct-use system (100 $/kWth)")
        # already have it:surfaceplant.elecprice        self.Electricity_rate = self.ParameterDict[self.Electricity_rate.Name] = floatParameter("Electricity Rate in Direct-use System", value = 0.1, DefaultValue=0.1, Min=0.0, Max=0.5, UnitType = Units.ENERGYCOST, PreferredUnits = EnergyCostUnit.DOLLARSPERKW, CurrentUnits = EnergyCostUnit.DOLLARSPERKW, Required=False, ErrMessage = "assume default Electricity rate in direct-use for pumping power (if pumping is required) 0.1 USD/kWh)")

        #Input data for electricity generation (water and CO2)
        self.Power_plant_cost_per_kWe = self.ParameterDict[self.Power_plant_cost_per_kWe.Name] = floatParameter("Capital Cost for Power Plant for Electricity Generation", value = 3000.0, DefaultValue=3000.0, Min=0.0, Max=10000.0, UnitType = Units.ENERGYCOST, PreferredUnits = EnergyCostUnit.DOLLARSPERKW, CurrentUnits = EnergyCostUnit.DOLLARSPERKW, Required=True, ErrMessage = "assume default Power plant capital cost per kWe (3000 USD/kWe)")
        self.P0 = self.ParameterDict[self.P0.Name] = floatParameter("Dead-state Pressure", value = 1e5, DefaultValue=1e5, Min=0.8e5, Max=1.1e5, UnitType = Units.PRESSURE, PreferredUnits = PressureUnit.PASCAL, CurrentUnits = PressureUnit.PASCAL, Required=True, ErrMessage = "assume default Dead-state pressure (1e5 Pa)")
        # already have it:surfaceplant.Tenv+273.15        self.T0 = self.ParameterDict[self.T0.Name] = floatParameter("Dead-state Temperature", value = 20+273.15, DefaultValue=20+273.15, Min=5+273.15, Max=25+273.15, UnitType = Units.TEMPERATURE, PreferredUnits = TemperatureUnit.KELVIN, CurrentUnits = TemperatureUnit.KELVIN, Required=True, ErrMessage = "assume default Dead-state temperature (20+273.15 K)")

        #Input data for electricity generation with CO2
        self.Turbine_isentropic_efficiency = self.ParameterDict[self.Turbine_isentropic_efficiency.Name] = floatParameter("Isentropic Efficiency for CO2 Turbine", value = 0.9, DefaultValue=0.9, Min=0.8, Max=1.0, UnitType = Units.PERCENT, PreferredUnits = PercentUnit.TENTH, CurrentUnits = PercentUnit.TENTH, Required=False, ErrMessage = "assume default Isentropic efficiency for turbine when CO2 is working fluid (0.9)")
        self.Generator_efficiency = self.ParameterDict[self.Generator_efficiency.Name] = floatParameter("Generator Conversion Efficiency", value = 0.98, DefaultValue=0.98, Min=0.8, Max=1.0, UnitType = Units.PERCENT, PreferredUnits = PercentUnit.TENTH, CurrentUnits = PercentUnit.TENTH, Required=False, ErrMessage = "assume default Conversion efficiency from mechanical turbine work to electricity (0.98)")
        self.Compressor_isentropic_efficiency = self.ParameterDict[self.Compressor_isentropic_efficiency.Name] = floatParameter("Isentropic Efficiency for CO2 Compressor", value = 0.9, DefaultValue=0.9, Min=0.8, Max=1.0, UnitType = Units.PERCENT, PreferredUnits = PercentUnit.TENTH, CurrentUnits = PercentUnit.TENTH, Required=False, ErrMessage = "assume default Isentropic efficiency for compressor when CO2 is working fluid (0.9)")
        self.Pre_Cooling_Delta_T = self.ParameterDict[self.Pre_Cooling_Delta_T.Name] = floatParameter("CO2 Temperature Decline with Cooling", value = 12.0, DefaultValue=12.0, Min=0.0, Max=15.0, UnitType = Units.TEMPERATURE, PreferredUnits = TemperatureUnit.CELCIUS, CurrentUnits = TemperatureUnit.CELCIUS, Required=False, ErrMessage = "assume default CO2 temperature decline with cooling after turbine and before compressor (12 degC)")
        self.Turbine_outlet_pressure = self.ParameterDict[self.Turbine_outlet_pressure.Name] = floatParameter("CO2 Turbine Outlet Pressure", value = 81.0, DefaultValue=81.0, Min=75.0, Max=200.0, UnitType = Units.PRESSURE, PreferredUnits = PressureUnit.BAR, CurrentUnits = PressureUnit.BAR, Required=False, ErrMessage = "assume default CO2 turbine outlet pressure (81 bar)")

        #NB: inputs we already have ("already have it") need to be set at ReadParameter time so values are set at the last possible time

        #local variable initiation
        #code from Koenraad
        self.filename = self.MyPath.replace(self.__str__()+".py", '') + 'CLG Simulator\clgs_results_final.h5'                #Filename of h5 database with simulation results [-]
        if self.Fluid.value == WorkingFluid.WATER:
            self.mat = scipy.io.loadmat(self.MyPath.replace(self.__str__()+".py", '') + 'CLG Simulator\\properties_H2O.mat')
        else:
            self.mat = scipy.io.loadmat(self.MyPath.replace(self.__str__()+".py", '') + 'CLG Simulator\\properties_CO2v2.mat')
            self.additional_mat = scipy.io.loadmat(self.MyPath.replace(self.__str__()+".py", '') + 'CLG Simulator\\additional_properties_CO2v2.mat')

        self.Number_of_points_per_year = 4               #Number of time steps per year in database [-] (must be 4)
        self.P_in = 2e7         #Constant Injection pressure [Pa]

        #results are stored here and in the parent ProducedTemperature array
        self.CLGSProducedTemperature = self.OutputParameterDict[self.ProducedTemperature.Name] = OutputParameter(Name = "CLGSial Produced Temperature", value=[0.0], UnitType = Units.TEMPERATURE, PreferredUnits = TemperatureUnit.CELCIUS, CurrentUnits = TemperatureUnit.CELCIUS)
        self.CLGSProducedTemperature.value = [0.0]*model.surfaceplant.plantlifetime.value #intialize the array
        self.CLGSPressureDrop = self.OutputParameterDict[self.CLGSPressureDrop.Name] = OutputParameter(Name = "CLGSial Pressure Drop", value=[0.0], UnitType = Units.PRESSURE, PreferredUnits = PressureUnit.KPASCAL, CurrentUnits = PressureUnit.KPASCAL)
        self.CLGSPressureDrop.value = [0.0]*model.surfaceplant.plantlifetime.value #intialize the array
 
        model.logger.info("complete "+ str(__class__) + ": " + sys._getframe().f_code.co_name)

    def __str__(self):
        return "CLGSWellBores"

    def read_parameters(self, model:AdvModel) -> None:
        """
        The read_parameters function reads in the parameters from a dictionary and stores them in the aparmeters.  It also handles special cases that need to be handled after a value has been read in and checked.  If you choose to sublass this master class, you can also choose to override this method (or not), and if you do
        
        :param self: Access variables that belong to a class
        :param model: The container class of the application, giving access to everything else, including the logger

        :return: None
        :doc-author: Malcolm Ross
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
                    if ParameterToModify.Name == "Heat Transfer Fluid":
                        if ParameterReadIn.sValue == str(1): ParameterToModify.value = WorkingFluid.WATER
                        else: ParameterToModify.value = WorkingFluid.SCO2
                    if ParameterToModify.Name == "Closed-loop Configuration":
                        if ParameterReadIn.sValue == str(1): ParameterToModify.value = Configuration.ULOOP
                        else: ParameterToModify.value = Configuration.COAXIAL
        else:
            model.logger.info("No parameters read becuase no content provided")

        #handle error checking and special cases:
        if model.reserv.numseg.value > 1:
            print("Warning: CLGS model can only handle a single layer gradient segment. Number of Segments set to 1, Gradient set to Gradient[0], and Depth set to Reservoir Depth.")    
            model.logger.warning("Warning: CLGS model can only handle a single layer gradient segment. Number of Segments set to 1, Gradient set to Gradient[0], and Depth set to Reservoir Depth.")
            model.reserv.numseg.value = 1

        if model.wellbores.ninj.value > 0:
            print("Warning: CLGS model considers the only the production wellbore paremeters. Anything related to the injection wellbore is ignored.")    
            model.logger.warning("Warning: CLGS model considers the only the production well bore paremeters. Anything related to the injection wellbore is ignored.")

        if model.wellbores.nprod.value != 1:
            print("Warning: CLGS model considers the only a single production wellbore (coaxial or uloop). Number of production wellboreset set 1.")    
            model.logger.warning("Warning: CLGS model considers the only a single production wellbore (coaxial or uloop). Number of production wellboreset set 1.")

        #inputs we already have - needs to be set at ReadParameter time so values set at the latest possible time
        self.krock = model.reserv.krock.value   #same units are GEOPHIRES
        self.Gradient = model.reserv.gradient.value[0]*1000     #convert to deg.C/m
        self.Depth = model.reserv.depth.value     #same units are GEOPHIRES
        self.Flow = model.wellbores.prodwellflowrate.value   #same units are GEOPHIRES
        self.Diameter = model.wellbores.prodwelldiam.value /  39.37   #covert inches to meters
        self.Tin = model.wellbores.Tinj.value + 273.15    #convert Celcius to Kelvin
        self.End_use = model.surfaceplant.enduseoption.value       #same units are GEOPHIRES
        self.Pump_efficiency = model.surfaceplant.pumpeff.value     #same units are GEOPHIRES
        self.Lifetime = int(model.surfaceplant.plantlifetime.value)     #same units are GEOPHIRES
        self.Electricity_rate = model.surfaceplant.elecprice.value      #same units are GEOPHIRES
        self.T0 = model.surfaceplant.Tenv.value + 273.15    #convert Celcius to Kelvin
        self.Discount_rate = model.economics.discountrate.value     #same units are GEOPHIRES

        #For reporting, we need to set some values that are not part of the calculation/extraction, but are seen in the report and need to be consistent
        model.reserv.depth.value = self.Depth
        #model.reserv.depth.PreferredUnits = LengthUnit.METERS
        model.reserv.depth.CurrentUnits = LengthUnit.METERS
        model.wellbores.prodwelldiam.value = self.Diameter
        model.wellbores.prodwelldiam.PreferredUnits = LengthUnit.METERS
        model.wellbores.prodwelldiam.CurrentUnits = LengthUnit.METERS
        model.wellbores.Tinj.value = self.Tin
        model.wellbores.Tinj.PreferredUnits = TemperatureUnit.KELVIN
        model.wellbores.Tinj.CurrentUnits = TemperatureUnit.KELVIN
        model.surfaceplant.Tenv.value = self.T0
        model.surfaceplant.Tenv.PreferredUnits = TemperatureUnit.KELVIN
        model.surfaceplant.Tenv.CurrentUnits = TemperatureUnit.KELVIN
        model.reserv.gradient.value[0] = self.Gradient
        model.reserv.gradient.PreferredUnits = TemperatureGradientUnit.DEGREESCPERM
        model.reserv.gradient.CurrentUnits = TemperatureGradientUnit.DEGREESCPERM

        #code from Koenraad
        self.point = (self.Flow, self.Hor_length.value, self.Depth, self.Gradient, self.Diameter, self.Tin, self.krock)

        model.logger.info("complete "+ str(__class__) + ": " + sys._getframe().f_code.co_name)
    
    #code from Koenraad
    def initialize(self, model:AdvModel) -> None:
        """
        The initialize function reads values and arrays to be in the format that CLGS model systems expects
        
        :param self: Access variables that belong to a class
        :param model: The container class of the application, giving access to everything else, including the logger

        :return: None
        :doc-author: Koenraad Beckers
        """
        model.logger.info("Init " + str(__class__) + ": " + sys._getframe().f_code.co_name)

        if self.Fluid.value == WorkingFluid.WATER:
            if self.Configuration.value == Configuration.ULOOP: self.u_H2O = data(self.filename, Configuration.ULOOP.value, "H2O")
            elif self.Configuration.value == Configuration.COAXIAL: self.u_H2O = data(self.filename, Configuration.COAXIAL.value, "H2O")
            self.timearray = self.u_H2O.time
            self.FlowRateVector = self.u_H2O.mdot #length of 26
            self.HorizontalLengthVector = self.u_H2O.L2 #length of 20
            self.DepthVector = self.u_H2O.L1 #length of 9
            self.GradientVector = self.u_H2O.grad #length of 5
            self.DiameterVector = self.u_H2O.D #length of 3
            self.TinVector = self.u_H2O.Tinj #length of 3
            self.KrockVector = self.u_H2O.k #length of 3
            self.Fluid_name = 'Water'
        elif self.Fluid.value == WorkingFluid.SCO2:
            if self.Configuration.value == Configuration.ULOOP: self.u_sCO2 = data(self.filename, Configuration.ULOOP.value, "sCO2")
            elif self.Configuration.value == Configuration.COAXIAL: self.u_sCO2 = data(self.filename, Configuration.COAXIAL.value, "sCO2")
            self.timearray = self.u_sCO2.time
            self.FlowRateVector = self.u_sCO2.mdot #length of 26
            self.HorizontalLengthVector = self.u_sCO2.L2 #length of 20
            self.DepthVector = self.u_sCO2.L1 #length of 9
            self.GradientVector = self.u_sCO2.grad #length of 5
            self.DiameterVector = self.u_sCO2.D #length of 3
            self.TinVector = self.u_sCO2.Tinj #length of 3
            self.KrockVector = self.u_sCO2.k #length of 3   
            self.Fluid_name = 'CarbonDioxide'            
            
        self.numberofcases = len(self.FlowRateVector)*len(self.HorizontalLengthVector)*len(self.DepthVector)*len(self.GradientVector)*len(self.DiameterVector)*len(self.TinVector)*len(self.KrockVector)
        
        self.Time_array = np.linspace(0,self.Lifetime*365*24*3600,1+self.Lifetime*self.Number_of_points_per_year) #[s]
        self.Linear_time_distribution = self.Time_array/365/24/3600
        self.TNOP = (self.Lifetime*self.Number_of_points_per_year+1)      #Total number of points for selected lifetime
        #Find closests lifetime
        closestlifetime = self.timearray.flat[np.abs(self.timearray - self.Lifetime).argmin()]    
        self.indexclosestlifetime = np.where(self.timearray == closestlifetime)[0][0]

        #load property data
        if self.Fluid.value == WorkingFluid.WATER:
            self.mat = scipy.io.loadmat('D:/Work/GEOPHIRES3-master/CLG Simulator/properties_H2O.mat')
        else:
            self.mat = scipy.io.loadmat('D:/Work/GEOPHIRES3-master/CLG Simulator/properties_CO2v2.mat')
            self.additional_mat = scipy.io.loadmat('D:/Work/GEOPHIRES3-master/CLG Simulator/additional_properties_CO2v2.mat')
        self.Pvector = self.mat['Pvector'][0]
        self.Tvector = self.mat['Tvector'][0]
        self.density = self.mat['density']
        self.enthalpy = self.mat['enthalpy']
        self.entropy = self.mat['entropy']
        if self.Fluid.value == WorkingFluid.SCO2:
            self.Pvector_ap = self.additional_mat['Pvector_ap'][0]
            self.hvector_ap = self.additional_mat['hvector_ap'][0]
            self.svector_ap = self.additional_mat['svector_ap'][0]
            self.TPh = self.additional_mat['TPh']
            self.hPs = self.additional_mat['hPs']
    
        #Define ORC power plant conversion efficiencies
        self.Utilization_efficiency_correlation_temperatures = np.array([100, 200, 385]) #Linear correlation assumed here based on GEOPHIRES ORC correlation between 100 and 200 deg C [deg.C] plus plateaued above 200 deg. C
        self.Utilization_efficiency_correlation_conversion = np.array([0.2, 0.45, 0.45])  #Efficiency of ORC conversion from production exergy to electricity based on GEOPHIRES correlation [-]
        self.Heat_to_power_efficiency_correlation_temperatures = np.array([100, 200, 385]) #Linear correlation based on Chad Augustine's thesis [deg.C] plus plateaued above 200 deg. C
        self.Heat_to_power_efficiency_correlation_conversion = np.array([0.05, 0.14, 0.14]) #Conversion from enthalpy to electricity [-]

        #Calculate dead-state enthalpy and entropy in case of electricity production
        if self.End_use.value == "Electricity":   
            self.h_0 = interpn((self.Pvector,self.Tvector),self.enthalpy,np.array([self.P0.value,self.T0]))[0] #dead-state enthalpy [J/kg]
            self.s_0 = interpn((self.Pvector,self.Tvector),self.entropy,np.array([self.P0.value,self.T0]))[0] #dead-state entropy [J/kg/K]

        #Pre-populate specific heat capacity of air in case of electricity production
        if self.End_use.value == "Electricity":
            self.Tair_for_cp_array = np.linspace(0,100,num=10)
            #self.cp_air_array = CP.PropsSI('C','P',self.P0,'T',self.Tair_for_cp_array+273.15,'air')
            self.cp_air_array = np.array([1005.65818063, 1005.87727966, 1006.19281999, 1006.60616167, 1007.11890862, 1007.73265999, 1008.44882744, 1009.26850304, 1010.19236691, 1011.2206266])
              
        #Initialize heat/electricity arrays
        self.Instantaneous_production_enthalpy = np.zeros(len(self.Time_array))
        self.Instantaneous_temperature_after_isenthalpic_throttling = np.zeros(len(self.Time_array))
        self.Instantaneous_heat_production = np.zeros(len(self.Time_array))
        self.Annual_heat_production = np.zeros(self.Lifetime)
        self.Annual_pumping_power = np.zeros(self.Lifetime)
        self.Average_fluid_density = np.zeros(len(self.Time_array))
        if self.End_use.value == "Electricity": #electricity generation
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
        if self.Fluid.value == WorkingFluid.SCO2.value:
            self.Instantaneous_turbine_power = np.zeros(len(self.Time_array)) #Direct turbine expansion considered for systems using sCO2

        #Initialize error code
        self.error_codes = np.zeros(0)  #if error occurs, code will be assigned to this tag

        model.logger.info("complete "+ str(__class__) + ": " + sys._getframe().f_code.co_name)

    def getTandP(self, model:AdvModel) -> None:
        """
        The getTandP function reads and prepares Temperature and Pressure values from the CLGS database
        
        :param self: Access variables that belong to a class
        :param model: The container class of the application, giving access to everything else, including the logger

        :return: None
        :doc-author: Koenraad Beckers
        """
        model.logger.info("Init " + str(__class__) + ": " + sys._getframe().f_code.co_name)
        
        if self.Fluid.value == WorkingFluid.WATER: self.Tout, self.Pout = self.u_H2O.interp_outlet_states(self.point)
        elif self.Fluid.value == WorkingFluid.SCO2: self.Tout, self.Pout = self.u_sCO2.interp_outlet_states(self.point)

        #Initial time correction (Correct production temperature and pressure at time 0 (the value at time 0 [=initial condition] is not a good representation for the first few months)
        self.Tout[0] = self.Tout[1]
        self.Pout[0] = self.Pout[1]
        
        #Extract Tout and Pout over lifetime
        self.InterpolatedTemperatureArray = self.Tout[0:self.indexclosestlifetime+1]-273.15
        self.InterpolatedPressureArray = self.Pout[0:self.indexclosestlifetime+1]

        model.logger.info("complete "+ str(__class__) + ": " + sys._getframe().f_code.co_name)

    def verify(self, model:AdvModel) -> int:
        """
        The validate function checks that all values provided are within the range expected by CLGS modeling system. These values in within a smaller range than the value ranges available to GEOPHIRES-X
        
        :param self: Access variables that belong to a class
        :param model: The container class of the application, giving access to everything else, including the logger

        :return: 0 if all OK, 1 if error.
        :doc-author: Koenraad Beckers
        """
        model.logger.info("Init " + str(__class__) + ": " + sys._getframe().f_code.co_name) #Verify inputs are within allowable bounds
        self.error = 0
        if self.Flow < 5 or self.Flow > 100:
            print("Error: CLGS model database imposes additional range restrictions: Flow rate must be between 5 and 100 kg/s. Simulation terminated.")
            model.logger.fatal("Error: CLGS model database imposes additional range restrictions: Flow rate must be between 5 and 100 kg/s. Simulation terminated.")
            self.error = 1
        if self.Hor_length.value < 1000 or self.Hor_length.value > 20000:
            print("Error: CLGS model database imposes additional range restrictions: Horizontal length must be between 1,000 and 20,000 m. Simulation terminated.")
            model.logger.fatal("Error: CLGS model database imposes additional range restrictions: Horizontal length must be between 1,000 and 20,000 m. Simulation terminated.")
            self.error = 1
        if self.Depth < 1000 or self.Depth > 5000:
            print("Error: CLGS model database imposes additional range restrictions: Vertical depth must be between 1,000 and 5,000 m. Simulation terminated.")
            model.logger.fatal("Error: CLGS model database imposes additional range restrictions: Vertical depth must be between 1,000 and 5,000 m. Simulation terminated.")
            self.error = 1
        if self.Gradient < 0.03 or self.Gradient > 0.07:
            print("Error: CLGS model database imposes additional range restrictions: Geothermal gradient must be between 0.03 and 0.07 degrees C per m. Simulation terminated.")
            model.logger.fatal("Error: CLGS model database imposes additional range restrictions: Geothermal gradient must be between 0.03 and 0.07 degrees C per m. Simulation terminated.")
            self.error = 1
        if self.Diameter < 0.2159 or self.Diameter > 0.4445:
            print("Error: CLGS model database imposes additional range restrictions: Wellbore diameter must be between 0.2159 and 0.4445 m. Simulation terminated.")
            model.logger.fatal("Error: CLGS model database imposes additional range restrictions: Wellbore diameter must be between 0.2159 and 0.4445 m. Simulation terminated.")
            self.error = 1
        if self.Tin < 303.15 or self.Tin > 333.15:
            print("Error: CLGS model database imposes additional range restrictions: Injection temperature must be between 303.15 and 333.15 K. Simulation terminated.")
            model.logger.fatal("Error: CLGS model database imposes additional range restrictions: Injection temperature must be between 303.15 and 333.15 K. Simulation terminated.")
            self.error = 1
        if self.krock < 1.5 or self.krock > 4.5:
            print("Error: CLGS model database imposes additional range restrictions: Rock thermal conductivity must be between 1.5 and 4.5 W/m/K. Simulation terminated.")
            model.logger.fatal("Error: CLGS model database imposes additional range restrictions: Rock thermal conductivity must be between 1.5 and 4.5 W/m/K. Simulation terminated.")
            self.error = 1
        if self.Drilling_cost_per_m.value < 0 or self.Drilling_cost_per_m.value > 10_000:
            print("Error: CLGS model database imposes additional range restrictions: Drilling costs per m of measured depth must be between 0 and 10,000 $/m. Simulation terminated.")
            model.logger.fatal("Error: CLGS model database imposes additional range restrictions: Drilling costs per m of measured depth must be between 0 and 10,000 $/m. Simulation terminated.")
            self.error = 1
        if self.O_and_M_cost_plant.value < 0 or self.O_and_M_cost_plant.value > 0.2:
            print("Error: CLGS model database imposes additional range restrictions: Operation & maintance cost of surface plant (expressed as fraction of total surface plant capital cost) must be between 0 and 0.2. Simulation terminated.")
            model.logger.fatal("Error: CLGS model database imposes additional range restrictions: Operation & maintance cost of surface plant (expressed as fraction of total surface plant capital cost) must be between 0 and 0.2. Simulation terminated.")
            self.error = 1
        if self.Discount_rate < 0 or self.Discount_rate > 0.2:
            print("Error: CLGS model database imposes additional range restrictions: Discount rate must be between 0 and 0.2. Simulation terminated.")
            model.logger.fatal("Error: CLGS model database imposes additional range restrictions: Discount rate must be between 0 and 0.2. Simulation terminated.")
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
        if self.Direct_use_heat_cost_per_kWth.value < 0 or self.Direct_use_heat_cost_per_kWth.value > 10_000:
            print("Error: CLGS model database imposes additional range restrictions: Capital cost for direct-use surface plant must be between 0 and 10,000 $/kWth. Simulation terminated.")
            model.logger.fatal("Error: CLGS model database imposes additional range restrictions: Capital cost for direct-use surface plant must be between 0 and 10,000 $/kWth. Simulation terminated.")
            self.error = 1
        if self.Electricity_rate < 0 or self.Electricity_rate > 0.5:
            print("Error: CLGS model database imposes additional range restrictions: Electricity rate in direct-use for pumping power must be between 0 and 0.5 $/kWh. Simulation terminated.")
            model.logger.fatal("Error: CLGS model database imposes additional range restrictions: Electricity rate in direct-use for pumping power must be between 0 and 0.5 $/kWh. Simulation terminated.")
            self.error = 1
        if self.Power_plant_cost_per_kWe.value < 0 or self.Power_plant_cost_per_kWe.value > 10_000:
            print("Error: CLGS model database imposes additional range restrictions: Power plant capital cost must be between 0 and 10,000 $/kWe. Simulation terminated.")
            model.logger.fatal("Error: CLGS model database imposes additional range restrictions: Power plant capital cost must be between 0 and 10,000 $/kWe. Simulation terminated.")
            self.error = 1
        if self.T0 < 278.15 or self.T0 > 303.15:
            print("Error: CLGS model database imposes additional range restrictions: Dead-state temperature must be between 278.15 and 303.15 K. Simulation terminated.")
            model.logger.fatal("Error: CLGS model database imposes additional range restrictions: Dead-state temperature must be between 278.15 and 303.15 K. Simulation terminated.")
            self.error = 1
        if self.P0.value < 0.8e5 or self.P0.value > 1.1e5:
            print("Error: CLGS model database imposes additional range restrictions: Dead state pressure must be between 0.8e5 and 1.1e5 Pa. Simulation terminated.")
            model.logger.fatal("Error: CLGS model database imposes additional range restrictions: Dead state pressure must be between 0.8e5 and 1.1e5 Pa. Simulation terminated.")
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

        model.logger.info("complete "+ str(__class__) + ": " + sys._getframe().f_code.co_name)
        return self.error
 
    def Calculate(self, model:AdvModel) -> None:
        """
        The calculate function verifies, initializes, and extracts the values from the CLGS model
        
        :param self: Access variables that belong to a class
        :param model: The container class of the application, giving access to everything else, including the logger

        :return: None
        :doc-author: Koenraad Beckers
        """
        model.logger.info("Init " + str(__class__) + ": " + sys._getframe().f_code.co_name)

        err = self.verify(model)
        if err> 0:             
            print("Error: GEOPHIRES failed to Failed to validate CLGS input value.  Exiting....")
            sys.exit()
        self.initialize(model)
        self.getTandP(model)

        #Deep Copy the Arrays 
        self.CLGSPressureDrop.value = self.InterpolatedPressureArray.copy()
        self.CLGSProducedTemperature.value = self.InterpolatedTemperatureArray.copy()

        # getTandP results must be rejiggered to match wellbores expected output. Once done, the surfaceplant and economics models should just work            #overall pressure drop  = previous pressure drop (as calculated from the verticals) + horizontal section pressure drop
        #interpolation is required because CLGSPressureDrop is sampled slightly differently, and DPOverall is sampled more frequently
        f = scipy.interpolate.interp1d(np.arange(0, len(self.CLGSPressureDrop.value)), self.CLGSPressureDrop.value, fill_value="extrapolate")
        self.CLGSPressureDrop.value = f(np.arange(0, len(self.CLGSPressureDrop.value), 1))   # use interpolation function returned by `interp1d`
        model.wellbores.DPOverall.value = self.CLGSPressureDrop.value

        rhowater = model.reserv.densitywater(self.Tout[0])
        model.reserv.cpwater.value = model.reserv.heatcapacitywater(self.Tout[0])     #Need this for surface plant output calculation

        #set pumping power to zero for all times, assuming that the thermosiphon wil always make pumping of working fluid unnesececary
        model.wellbores.PumpingPower.value = [0.0]*(len(self.CLGSPressureDrop.value))
        #model.wellbores.PumpingPower.value = model.wellbores.DPOverall.value*self.Flow/rhowater/model.surfaceplant.pumpeff.value/1E3   
        #in GEOPHIRES v1.2, negative pumping power values become zero (b/c we are not generating electricity) = thermosiphon is happening!
        #model.wellbores.PumpingPower.value = [0. if x<0. else x for x in self.PumpingPower.value]

#done with calculations. Now overlay the HorizontalProducedTemperature onto WellBores.ProducedTemperatures - interpolation is required because HorizontalProducedTemperature is sampled yearly, and ProducedTemperature is sampled more frequently
        f = scipy.interpolate.interp1d(np.arange(0, len(self.CLGSProducedTemperature.value)), self.CLGSProducedTemperature.value, fill_value="extrapolate")
        model.wellbores.ProducedTemperature.value = f(np.arange(0, len(self.CLGSProducedTemperature.value)-1, 1.0))   # use interpolation function returned by `interp1d`

        #store the calculate result and associated object paremeters in the database
        resultkey = self.store_result(model, self)
        if resultkey == None: model.logger.warn("Failed To Store "+ str(__class__) + " " + os.path.abspath(__file__))

        model.logger.info("complete "+ str(__class__) + ": " + sys._getframe().f_code.co_name)
        
    def __str__(self):
        return "CLGSWellBores"