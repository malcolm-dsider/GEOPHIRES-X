# copyright, 2023, Malcolm I Ross
from enum import IntEnum, Enum, auto
class Units(IntEnum):
    """All possible systems of measure"""
    NONE = auto()
    CHOICE = auto()
    LENGTH = auto()
    AREA = auto()
    VOLUME = auto()
    MASS = auto()
    DENSITY = auto()
    TEMPERATURE = auto()
    PRESSURE = auto()
    TIME = auto()
    FLOWRATE = auto()
    TEMP_GRADIENT = auto()
    DRAWDOWN = auto()
    IMPEDANCE = auto()
    PRODUCTIVITY_INDEX = auto()
    INJECTIVITY_INDEX = auto()
    HEAT = auto()
    HEAT_CAPACITY = auto()
    ENTROPY = auto()
    ENTHALPY = auto()
    THERMAL_CONDUCTIVITY = auto()
    POROSITY = auto()
    PERMEABILITY = auto()
    CURRENCY = auto()
    CURRENCYFREQUENCY = auto()
    ENERGYCOST = auto()
    ENERGYDENSITY = auto()
    COSTPERMASS = auto()
    MASSPERTIME = auto()
    COSTPERDISTANCE = auto()
    PERCENT = auto()
    ENERGY = auto()
    POWER = auto()
    ENERGYFREQUENCY = auto()
    AVAILABILITY = auto()
    CO2PRODUCTION = auto()
    ENERGYPERCO2 = auto()

class  TemperatureUnit(Enum):
    """Temperature Units"""
    CELCIUS = "degC"
    FARENHEIT = "degF"
    KELVIN = "degK"

class TemperatureGradientUnit(Enum):
    """Temperature Gradient Units"""
    DEGREESCPERKM = "degC/km"
    DEGREESFPERMILE = "degF/mi"
    DEGREESCPERM = "degC/m"

class PercentUnit(Enum):
    """Percent Units"""
    PERCENT = "%"
    TENTH = ""

class LengthUnit(Enum):
    """Length Units"""
    METERS = "meter"
    CENTIMETERS = "centimeter"
    KILOMETERS = "kilometer"
    FEET = "ft"
    INCHES = "in"
    MILES = "mile"

class AreaUnit(Enum):
    """Area Units"""
    METERS2 = "m**2"
    CENTIMETERS2 = "cm**2"
    KILOMETERS2 = "km**2"
    FEET2 = "ft**2"
    INCHES2 = "in**2"
    MILES2 = "mi**2"

class VolumeUnit(Enum):
    """Volume Units"""
    METERS3 = "m**3"
    CENTIMETERS3 = "cm**3"
    KILOMETERS3 = "km**3"
    FEET3 = "ft**3"
    INCHES3 = "in**3"
    MILES3 = "mi**3"

class DensityUnit(Enum):
    """Density Units"""
    KGPERMETERS3 = "kg/m**3"
    GRPERCENTIMETERS3 = "gr/cm**3"
    KGPERKILOMETERS3 = "kg/km**3"
    LBSPERFEET3 = "lbs/ft**3"
    OZPERINCHES3 = "oz/in**3"
    LBSPERMILES3 = "lbs/mi**3"

class EnergyUnit(Enum):
    """Energy (electrcity or heat) Units"""
    WH = "Wh"
    KWH = "kWh"
    MWH = "MWh"
    GWH = "GWh"

class PowerUnit(Enum):
    """Power (electrcity or heat) Units"""
    W = "W"
    KW = "kW"
    MW = "MW"
    GW = "GW"

class EnergyFrequencyUnit(Enum):
    """Energy per interval Units"""
    WPERYEAR = "W/yr"
    KWPERYEAR = "kW/yr"
    MWPERYEAR = "MW/yr"
    GWPERYEAR = "GW/yr"

class CurrencyUnit(Enum):
    """Currency Units"""
    MDOLLARS = "MUSD"
    KDOLLARS = "KUSD"
    DOLLARS = "USD"
    MEUR = "MEUR"
    KEUR = "KEUR"
    EUR = "EUR"
    MMXN = "MMXN"
    KMXN = "KMXN"
    MXN = "MXN"

class CurrencyFrequencyUnit(Enum):
    MDOLLARSPERYEAR = "MUSD/yr"
    KDOLLARSPERYEAR = "KUSD/yr"
    DOLLARSPERYEAR = "USD/yr"
    MEURPERYEAR = "MEUR/yr"
    KEURPERYEAR = "KEUR/yr"
    EURPERYEAR = "EUR/yr"
    MMXNPERYEAR = "MXN/yr"
    KMXNPERYEAR = "KMXN/yr"
    MXNPERYEAR = "MXN/yr"
    
class EnergyCostUnit(Enum):
    DOLLARSPERKWH = "USD/kWh"
    DOLLARSPERMWH = "USD/MWh"
    CENTSSPERKWH = "cents/kWh"
    DOLLARSPERKW = "USD/kW"
    CENTSSPERKW = "cents/kW"
    DOLLARSPERMMBTU = "USD/MMBTU"
    DOLLARSPERMCF = "USD/MCF"
    
class EnergyDensityUnit(Enum):
    KWHPERMCF = "kWh/MCF"
    
class MassPerTimeUnit(Enum):
    TONNEPERYEAR = "tonne/yr"
    
class CostPerMassUnit(Enum):
    CENTSSPERMT = "cents/mt"
    DOLLARSPERMT = "USD/mt"
    DOLLARSPERTONNE = "USD/tonne"
    CENTSSPERLB = "cents/lb"
    DOLLARSPERLB = "USD/lb"
    
class CostPerDistanceUnit(Enum):
    DOLLARSPERM = "USD/m"

class PressureUnit(Enum):
    """Pressure Units"""
    KPASCAL = "kPa"
    PASCAL = "Pa"
    BAR = "bar"
    KBAR = "kbar"

class AvailabilityUnit(Enum):
    """Availability Units"""
    MWPERKGPERSEC = "MW/(kg/s)"

class DrawdownUnit(Enum):
    """Drawdown Units"""
    KGPERSECPERSQMETER = "kg/s/m**2"
    PERYEAR = "1/year"

class HeatUnit(Enum):
    """Heat Units"""
    J = "J"
    KJ = "kJ"

class HeatCapacityUnit(Enum):
    """Heat Capacity Units"""
    JPERKGPERK = "J/kg/kelvin"
    KJPERKM3C = "kJ/km**3C"
    kJPERKGC = "kJ/kgC"

class EntropyUnit(Enum):
    """Entropy Units"""
    KJPERKGK = "kJ/kgK"

class EnthalpyUnit(Enum):
    """Enthalpy Units"""
    KJPERKG = "kJ/kg"
    
class ThermalConductivityUnit(Enum):
    """Thermal Conductivity Units"""
    WPERMPERK = "watt/m/kelvin"
    
class TimeUnit(Enum):
    """Time Units"""
    MSECOND = "msec"
    SECOND = "sec"
    MINUTE = "min"
    HOUR = "hr"
    DAY = "day"
    WEEK = "week"
    YEAR = "yr"
    
class FlowRateUnit(Enum):
    """Flow Rate Units"""
    KGPERSEC = "kg/sec"
    
class ImpedanceUnit(Enum):
    """Impedance Units"""
    GPASPERM3= "GPa.s/m**3"
    
class ProductivityIndexUnit(Enum):
    """Productivity IndexUnits"""
    KGPERSECPERBAR= "kg/sec/bar"
    
class InjectivityIndexUnit(Enum):
    """Injectivity IndexUnits"""
    KGPERSECPERBAR= "kg/sec/bar"
    
class PorosityUnit(Enum):
    """Porosity Units"""
    PERCENT= "%"
    
class PermeabilityUnit(Enum):
    """Permeability Units"""
    SQUAREMETERS= "m**2"
    
class CO2ProductionUnit(Enum):
    """CO2 Production Units"""
    LBSPERKWH= "lbs/kWh"
    KPERKWH= "k/kWh"
    TONNEPERMWH = "t/MWh"
    
class EnergyPerCO2Unit(Enum):
    """Energy cost per toone of CO2 extracted Units"""
    KWHEPERTONNE = "kWh/t"
    KWTHPERTONNE = "kW/t"

class MassUnit(Enum):
    """Mass Units"""
    GRAM = "gram"
    KILOGRAM = "kilogram"
    TONNE = "tonne"
    TON = "ton"
    LB = "pound"
    OZ = "ounce"
