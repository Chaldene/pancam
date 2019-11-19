# -*- coding: utf-8 -*-
"""
Created on Tue Nov  5 10:19:47 2019

@author: ucasbwh
"""
import matplotlib.pyplot as plt
from matplotlib import gridspec
import matplotlib.dates as mdates
import pandas as pd
import numpy as np
from pandas.plotting import register_matplotlib_converters
import os

def Voltages(PROC_DIR):
    
    print("---Producing Voltage Plots")   
    
    TC = pd.read_pickle(os.path.join(PROC_DIR, "*TC.pickle"))
    df = pd.read_pickle(os.path.join(PROC_DIR, "*TM.pickle"))
    
    myFmt = mdates.DateFormatter('%H:%M')

    #Start plot
    p1 = df['DT']
    
    fig = plt.figure(figsize=(15.0, 10.0))
    
    ax1 = fig.add_subplot(3,1,1)
    ax2 = fig.add_subplot(3,1,2)
    ax3 = fig.add_subplot(3,1,3)
    
    ax1.plot(p1, df[12]*256+df[13], 'r-', label='VRef Raw')
    ax1.set_ylabel('VRef Raw [ENG]')
    ax1.grid(True)
    
    ax2.plot(p1, df[14]*256+df[15], 'b-', label='6V RAW')
    ax2.set_ylabel('6V Raw [ENG]')
    ax2.grid(True)
    ax3.plot(p1, df[16]*256+df[17], 'g-', label='1V5 RAW')
    ax3.set_ylabel('1V5 Raw [ENG]')
    ax3.set_xlabel('Date Time')
    ax3.grid(True)
    
    plt.setp(ax1.get_xticklabels(), visible=False)
    plt.setp(ax2.get_xticklabels(), visible=False)
    ax3.xaxis.set_major_formatter(myFmt)
        
    fig.set_figheight(5)
    fig.set_figwidth(9)
    fig.tight_layout()
    fig.show()
    
    
    ##Plot of calibrated values
    ratio = 4096*1.45914
    p2 = ratio /(df[12]*256+df[13])
    p3 = p2 / 4096 * 6.4945 * (df[14]*256+df[15])
    p4 = p2 * (df[16]*256+df[17])/4096
    
    fig = plt.figure()
    
    ax1 = fig.add_subplot(3,1,1)
    ax2 = fig.add_subplot(3,1,2, sharex=ax1)
    ax3 = fig.add_subplot(3,1,3, sharex=ax1)
    
    ax1.plot(p1, p2, 'r-', label='VRef')
    ax1.plot([df['DT'].iloc[0], df['DT'].iloc[-1]], [3.1, 3.1], 'darkred', linestyle='dashed')
    ax1.plot([df['DT'].iloc[0], df['DT'].iloc[-1]], [3.6, 3.6], 'darkred', linestyle='dashed')
    ax1.set_ylabel('VRef [V]')
    ax1.grid(True)
    
    ax2.plot(p1, p3, 'b-', label='6V')
    ax2.set_ylabel('6V [V]')
    ax2.plot([df['DT'].iloc[0], df['DT'].iloc[-1]], [5.5, 5.5], 'darkblue', linestyle='dashed')
    ax2.plot([df['DT'].iloc[0], df['DT'].iloc[-1]], [6.3, 6.3], 'darkblue', linestyle='dashed')
    ax2.grid(True)
    
    ax3.plot(p1, p4, 'g-', label='1V5 RAW')
    ax3.set_ylabel('1V5 Raw [ENG]')
    ax3.plot([df['DT'].iloc[0], df['DT'].iloc[-1]], [1.4, 1.4], 'darkgreen', linestyle='dashed')
    ax3.plot([df['DT'].iloc[0], df['DT'].iloc[-1]], [1.6, 1.6], 'darkgreen', linestyle='dashed')
    ax3.set_xlabel('Date Time')
    ax3.grid(True)
    
    plt.setp(ax1.get_xticklabels(), visible=False)
    plt.setp(ax2.get_xticklabels(), visible=False)
    ax3.xaxis.set_major_formatter(myFmt)
    
    
    #Display Plot
    fig.set_figheight(8)
    fig.set_figwidth(15)
    fig.tight_layout()
    
    fig.set_figheight(5)
    fig.set_figwidth(9)
    fig.tight_layout()
    fig.show()
    
if __name__ == "__main__":
    Dir =      r'C:\Users\ucasbwh\OneDrive - University College London\PanCam Documents\Rover Level Testing\Data\191107 - TVAC TP02 Testing\20191106_1734_ERJPMW_CRUISE_CHECKOUTS\PROC'
    Voltages(Dir)