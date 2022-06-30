from dataclasses import dataclass
from enum import IntEnum, Enum
#from OptionList import *

@dataclass
class Result():
    """description of class"""
    FromObject = Enum
    UnitType: IntEnum
    PreferredUnits: Enum
    CurrentUnits: Enum
    Description: str = ""
    Valid: bool = False
    ErrMessage: str = ""

@dataclass
class boolResult(Result):
    """description of class"""
    value: bool = True

@dataclass
class intResult(Result):
    """description of class"""
    value: int = 0

@dataclass
class floatResult(Result):
    """description of class"""
    value: float = 0.0

@dataclass
class strResult(Result):
    """description of class"""
    value: str = ""

@dataclass
class listResult(Result):
    """description of class"""
    value = []
