# -*- coding: utf-8 -*-
"""
Created on Thu Nov 21 10:14:24 2019

@author: ucasbwh
"""
from bitstruct import unpack_from as upf
import pandas as pd

def PandUPF(Column, Len, OffBy, OffBi):
    """Extracts the RAW value from a binary pandas data column"""
    Extract = Column.apply(lambda x: upf(Len, x, offset=8*OffBy+OffBi)[0]).astype('Int64')
    return Extract