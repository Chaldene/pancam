# -*- coding: utf-8 -*-
"""
Created on Tue Nov  5 11:01:15 2019

@author: ucasbwh
"""

import matplotlib.pyplot as plt
from matplotlib import gridspec
import matplotlib.dates as mdates
import pandas as pd
import numpy as np
from pandas.plotting import register_matplotlib_converters
import os

def FilterWheel(PROC_DIR):
    
    print("---Producing Filter Wheel Plots")   
    
    TC = pd.read_pickle(os.path.join(PROC_DIR, "TC.pickle"))
    df = pd.read_pickle(os.path.join(PROC_DIR, "TM.pickle"))
    
    gs = gridspec.GridSpec(7, 1, height_ratios=[1, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5])
    gs.update(hspace=0.0)
    fig = plt.figure(figsize=(8.8, 8), constrained_layout=True)
    a0 = fig.add_subplot(gs[0])
    a1 = fig.add_subplot(gs[1], sharex=a0)
    a2 = fig.add_subplot(gs[2], sharex=a0)
    a3 = fig.add_subplot(gs[3], sharex=a0)
    a4 = fig.add_subplot(gs[4], sharex=a0)
    a5 = fig.add_subplot(gs[5], sharex=a0)
    a6 = fig.add_subplot(gs[6], sharex=a0)
    
    # Action List
    size = TC.shape[0]
    TC['LEVEL'] = 1
    
    markerline, stemline, baseline = a0.stem(TC['DT'], TC['LEVEL'], linefmt='C3-', basefmt="k-", use_line_collection=True)
    plt.setp(markerline, mec="k", mfc="w", zorder=3)
    markerline.set_ydata(np.zeros(size))
    a0.text(.99,.9,'Action List', horizontalalignment='right', transform=a0.transAxes)
    a0.grid(True)
    for i in range(0, size):
        a0.annotate(TC.ACTION.iloc[i], xy=(TC.DT.iloc[i], TC.LEVEL.iloc[i]), xytext=(0,-2),
                textcoords="offset points", va="top", ha="right", rotation=90)
    
    
    ## Cam Power and Enable Second dataset
    a1.plot(df['DT'], (df[40]&0x40).values>6, label='FWL')
    a1.plot(df['DT'], (df[41]&0x40).values>6, label='FWR')
    a1.text(.99,.8,'Running', horizontalalignment='right', transform=a1.transAxes)
    a1.grid(True)
    a1.set_ylim([-0.1,1.1])
    plt.setp(a1.get_yticklabels(), visible=False)
    a1.legend(loc='center right', bbox_to_anchor= (1.0, 0.5), ncol=1, borderaxespad=0, frameon=False)
    
    ## Home Effect
    a2.plot(df['DT'], (df[40]&0x20).values>5)
    a2.plot(df['DT'], (df[41]&0x20).values>5)
    a2.text(.99,.8,'Home', horizontalalignment='right', transform=a2.transAxes)
    a2.grid(True)
    a2.set_ylim([-0.1,1.1])
    plt.setp(a2.get_yticklabels(), visible=False)
    
    ## Index Number
    a3.plot(df['DT'], (df[40]&0x10).values>4)
    a3.plot(df['DT'], (df[41]&0x10).values>4)
    a3.text(.99,.8,'Index', horizontalalignment='right', transform=a3.transAxes)
    a3.grid(True)
    a3.set_ylim([-0.1,1.1])
    plt.setp(a3.get_yticklabels(), visible=False)
    
    ## WAC CMD Timeout
    a4.plot(df['DT'], (df[40]&0xF))
    a4.plot(df['DT'], (df[41]&0xF))
    a4.text(.99,.8,'Filter #', horizontalalignment='right', transform=a4.transAxes)
    a4.grid(True)
    
    ## Absolute Steps
    a5.plot(df['DT'], (df[64]*256+df[65]))
    a5.plot(df['DT'], (df[66]*256+df[67]))
    a5.text(.99,.8,'Absolute Steps', horizontalalignment='right', transform=a5.transAxes)
    a5.grid(True)
    a5.yaxis.tick_right()
    a5.yaxis.set_label_position('right')
    
    # Relative Steps
    a6.plot(df['DT'], (df[68]*256+df[69]))
    a6.plot(df['DT'], (df[70]*256+df[71]))
    a6.text(.99,.8,'Relative Steps', horizontalalignment='right', transform=a6.transAxes)
    a6.grid(True)
    a6.yaxis.tick_right()
    a6.yaxis.set_label_position('right')
    
    #remove y axis and spines
    a0.get_yaxis().set_visible(False)
            
    #Re-adjust x-axis so that 
    xlimits = a0.get_xlim()
    new_xlimits = (xlimits[0],(xlimits[1] - xlimits[0])*1.3+xlimits[0]);
    a0.set_xlim(new_xlimits)
    
if __name__ == "__main__":
    Dir =      r'C:\Users\ucasbwh\OneDrive - University College London\PanCam Documents\Rover Level Testing\Data\191022 - PostAcoustic_PreTVAC\ANNEX-2 CCS Logs\20191024_1437_CL\PROC'
    FilterWheel(Dir)