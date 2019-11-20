# -*- coding: utf-8 -*-
"""
Created on Sun Nov 17 20:38 2019

@author: ucasbwh
"""

### File for producing a quick plot of Rover temperatures

import matplotlib.pyplot as plt
from matplotlib import gridspec
import pandas as pd
from pandas.plotting import register_matplotlib_converters
from pathlib import Path

Top_DIR = Path(input("Type the path to the folder where the PROC folder is stored: "))

## Search for Rover Temp Files
FILT_DIR = "*RoverTemps.pickle"
PikFile = sorted(Top_DIR.rglob(FILT_DIR))
RVTM = pd.read_pickle(PikFile[0])

print("Rover Temp File Found")

gs = gridspec.GridSpec(2, 1, height_ratios=[1, 1])
f = plt.figure()
        
a0 = f.add_subplot(gs[0])
a1 = f.add_subplot(gs[1], sharex=a0)

a0.plot(RVTM['DT'], RVTM['PIU_T'], '.', label='PIU')
a1.plot(RVTM['DT'], RVTM['DCDC_T'], '.', label='DCDC')

a0.grid(True)
a1.grid(True)

#remove y axis and spines
plt.setp(a0.get_xticklabels(), visible=False)

plt.show()
print("plot complete")