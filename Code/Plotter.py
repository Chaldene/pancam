# Plotter.py
#
# Barry Whiteside
# Mullard Space Science Laboratory - UCL
#
# PanCam Data Processing Tools


import matplotlib.pyplot as plt
from matplotlib import gridspec
import matplotlib.dates as mdates
import pandas as pd 
from pandas.plotting import register_matplotlib_converters
import numpy as np 
from pathlib import Path

register_matplotlib_converters()

class plotter_Error(Exception):
    """error for unexpected things"""
    pass

def Voltages(PROC_DIR):
    """"Produces a calibrated and uncalibrated voltage plots from pickle files"""
    print(pd.__version__)

    print("---Producing Voltage Plots")

    ## Search for PanCam Processed Files
    FILT_DIR = "*RAW_HKTM.pickle"
    RawPikFile = sorted(PROC_DIR.rglob(FILT_DIR))

    if len(RawPikFile) == 0:
        print("**No RAW HKTM Files Found**")
        print("Plotting TM HK Voltages Aborted")
        return
    elif len(RawPikFile) > 1:
        plotter_Error("Warning more than one 'RAW_TM.pickle' found") 

    RAW = pd.read_pickle(RawPikFile[0])
    myFmt = mdates.DateFormatter('%H:%M')

    fig, axs = plt.subplots(3, 1)
    RAW.plot(x='DT', y='Volt_Ref')
    #axs[0].plot(RAW['DT'], RAW['Volt_Ref'], 'r-', label='VRef Raw')
    #axs[0].set_ylabel('VRef RAW [ENG]')
    #axs[0].grid(True)

    #axs[1].plot(RAW['DT'], RAW['Volt_6V0'], 'b-', label='6V Raw')
    #axs[1].set_ylabel('6V RAW [ENG]')
    #axs[1].grid(True)

    #axs[2].plot(RAW['DT'], RAW['Volt_1V5'], 'g-', label='1V5 Raw')
    #axs[2].set_ylabel('1V5 RAW [ENG]')
    #axs[2].set_xlabel('Data Time')
    #axs[2].grid(True)

    #plt.setp(ax1.get_xticklabels(), visible=False)
    #plt.setp(ax2.get_xticklabels(), visible=False)
    #ax3.xaxis.set_major_formatter(myFmt)

    fig.show()
    print("Test")

if __name__ == "__main__":
    #DIR = Path(input("Type the path to the PROC folder where the processed files are stored: "))
    DIR = Path(r"C:\Users\ucasbwh\OneDrive - University College London\PanCam Documents\Rover Level Testing\Data\191107 - TVAC TP02 Testing\20191106_1734_ERJPMW_CRUISE_CHECKOUTS\PROC")


    Voltages(DIR)
