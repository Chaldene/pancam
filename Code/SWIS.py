# -*- coding: utf-8 -*-
"""
swis.py

Barry Whiteside
Mullard Space Science Laboratory - UCL

PanCam Data Processing Tools
Created 12 Dec 2019.
"""

import pandas as pd
from pathlib import Path
import logging
import csv
import re
import json
import filecmp
from bitstruct import unpack_from as upf

import PC_Fns
import hs

logger = logging.getLogger(__name__)

# Global parameters
swisProcVer = {'swisProcVer': 1.0}


def hk_extract(swis_dir: Path):
    """Generates a Unproc_HKTM.pickle from the given SWIS source

    Arguments:
        swis_dir {Path} -- If using NSVF path is within the Proc directory. Otherwise the source path is used.

    Returns:
        Boolean -- Returns true if files found and function completed.

    Generates:
        *_Unproc_HKTM.pickle -- The pandas dataframe containing raw HK and time information within a folder for each instance.
    """

    # Searches for HK files and creates a binary for each file found

    logger.info("Processing SWIS HK")

    # First identify any nsvf files
    hk_files = PC_Fns.Find_Files(swis_dir, "*nsvfHK*.txt", SingleFile=True)
    if hk_files:
        nsvf = True
    # Else look for standard SWIS hk files
    else:
        hk_files = PC_Fns.Find_Files(swis_dir, "*HK.txt")
        nsvf = False

    if not hk_files:
        logger.error("No files found - ABORTING")
        return False

    for curfile in hk_files:
        dl = pd.DataFrame()
        logger.info("Reading %s", curfile.name)
        cur_name = curfile.stem

        if nsvf:
            logger.info("Type is nsvf")
            dtab = pd.read_table(curfile, sep=' : ',
                                 header=None, engine='python')
            dl['SPW_RAW'] = dtab[1].apply(lambda x: x.replace(' ', ''))
            dl['RAW'] = dl.SPW_RAW.apply(lambda x: x[24:-7])
            dl['Source'] = 'SWIS'

            # Extract epoch from filename
            epoch = int(curfile.stem.split('_')[1][4:])

            # Calculate elapsed time
            dtab['ElapLi'] = dtab[0].apply(
                lambda x: x.split(' ')[0][1:-1].split(':'))

            # Ensure elapsed list is expected length
            verify = dtab['ElapLi'].str.len() != 4
            err_df = dtab[verify]
            if err_df.shape[0] != 0:
                logger.error("Some elpased times are not in correct format")
                logger.error(err_df)

            dtab['Elapsed'] = dtab['ElapLi'].apply(
                lambda x: float(x[0] + '.' + ''.join(x[1:])))

            dl['Unix_Time'] = dtab['Elapsed'] + epoch
            cur_dir = curfile.parent

        else:
            logger.info("Type is standard SWIS")
            dtab = pd.read_table(curfile, sep=']', header=None)
            dl['SPW_RAW'] = dtab[1].apply(
                lambda x: x.replace('0x', '').replace(' ', ''))
            dl['RAW'] = dl.SPW_RAW.apply(lambda x: x[108-84:-2])
            dl['Source'] = 'SWIS'
            dl['Unix_Time'] = dtab[0].apply(lambda x: x[11:-12])

            # Create individual folders and save here
            cur_dir = swis_dir / "PROC" / cur_name
            if cur_dir.is_dir():
                logger.info("Instance Processing Directory already exists")
            else:
                logger.info("Generating Instance Processing Directory")
                cur_dir.mkdir()

        dl.to_pickle(cur_dir / (cur_name + "_Unproc_HKTM.pickle"))

    return True


def hs_extract(swis_dir: Path):
    """Extracts the H&S from the SWIS log and puts in a new file

    Arguments:
        swis_dir {Path} -- Dir containing .txt files with simulation data

    Generates:
        _HS.txt -- Simply contains the extracted relevant H&S lines from the log.
        hs_raw.pickle -- Pickle file in ['Time', 'RAW'] format for hs module.
    """

    # Searches through the typescript output .txt file and recreates a simple H&S.txt file

    logger.info("Processing SWIS H&S")

    files_txt = PC_Fns.Find_Files(swis_dir, "*.txt")
    files_HK = PC_Fns.Find_Files(swis_dir, "*_HK*.txt")
    files_sci = PC_Fns.Find_Files(swis_dir, '*_SC.txt')
    files_typ = PC_Fns.Find_Files(swis_dir, "*_typescript.txt")
    files_hs = list(set(files_txt) - set(files_HK) -
                    set(files_sci) - set(files_typ))

    # Read text file for H&S
    for curfile in files_hs:

        # Create individual folders and save here
        cur_name = curfile.stem
        cur_dir = swis_dir / "PROC" / (cur_name + "_HK")
        if cur_dir.is_dir():
            logger.info("Instance Processing Directory already exists")
        else:
            logger.info("Generating Instance Processing Directory")
            cur_dir.mkdir()

        # New file within new folder
        write_file = (cur_dir / (curfile.stem + "_HS.log"))
        if write_file.exists():
            logger.info("HS.txt file already exists - deleting")
            write_file.unlink()
        logger.info("Creating HS.txt file")
        wf = open(write_file, 'w')

        # Scan through text log and save H&S lines
        with open(curfile, 'r') as f:
            logger.info("Reading %s", curfile.name)
            line = f.readline()
            while line != "":
                if "HS response" in line:
                    if "message with 45 bytes" in line:
                        line_red = line.replace("Timestamp: ", "")
                        line_red = line_red.replace(
                            " - [Informative]HS response message with 45 bytes and content ", "; ")
                        line_red = line_red.replace("-0x", " ")
                        line_red = line_red.replace("0x", "")
                        line_red = line_red.replace("\n", "").replace("\r", "")
                        split_line = line_red.split(" ")
                        new_line = "".join([entry.zfill(2)
                                            for entry in split_line]) + "\n"
                        wf.write(new_line)
                line = f.readline()
            wf.close()

        # Convert hs.log to pickle file
        hs_head = ['Time', 'RAW']
        hs = pd.read_csv(write_file, sep=';', header=None, names=hs_head)
        hs.to_pickle(cur_dir / "hs_raw.pickle")
        logger.info("PanCam H+S pickled.")


def nsvf_parse(swis_dir: Path):
    """Searches through the NSVF generated packet_log and generates new files from any found PanCam telemetry.

    Arguments:
        swis_dir {Path} -- Path of directory to file to search for Router_A_packet.log.

    Returns:
        Boolean -- True if process runs else False

    Generates:
        H+S.txt -- ASCII txt file of all PanCam health and status.
        nsvfHK.txt  -- ASCII file of the PanCam HK telemetry
        Sci.txt -- ASCII file of the PanCam Sci telemetry.
        TC.txt  -- ASCII file of the PanCam TC responses.

        hs.pickle -- Pandas pickle file of H+S in the standard format for this tool.
    """

    # Function Constants
    # Regular expressions for log format
    in_re = re.compile(r"^\[IN=[0-9]+\]$")
    sz_re = re.compile(r"^\[SZ=[0-9]+\]$")

    # PanCam logical address
    pc_log_addr = 0x41
    pc_hs_rowlen = 45

    logger.info("Processing SWIS NSVF log")

    logger.info("Searching for Router_A_packet.log file")
    packet_log = PC_Fns.Find_Files(
        swis_dir, "Router_A_packet.log", SingleFile=True)

    if packet_log == []:
        return False
    else:
        packet_log = packet_log[0]

    # Create a PROC directory if does not already exist
    proc_dir = packet_log.parent / 'PROC'
    if not proc_dir.is_dir():
        proc_dir.mkdir()

    # Next prepare files to be written
    file = {}
    f_acc = {}
    f_wri = {}

    file['hs'] = proc_dir / 'H+S.txt'
    file['hk'] = proc_dir / 'nsvfHK.txt'
    file['tc'] = proc_dir / 'TC.txt'
    file['sc'] = proc_dir / 'Sci.txt'

    for key, value in file.items():
        if value.exists():
            value.unlink()
            logger.info("Deleting file: %s", value.name)
        f_acc[key] = open(value, 'w')
        f_wri[key] = csv.writer(f_acc[key], delimiter=' ', lineterminator='\r')

    # Open file and check format is as expcted
    # Contains ..[IN=..].. and ..[SZ=..].., ..[EOP] at the end of each line

    with open(packet_log, 'r') as logfile:
        reader = csv.reader(logfile, delimiter=' ')
        logger.info("Reading file %s", packet_log.name)
        for row in reader:
            # First check that row ends in [EOP]
            if row[-1] != '[EOP]':
                logger.error("Row does not end in '[EOP]': %s", row)
                continue

            # Verify row contains [IN=..] in correct position
            if not in_re.match(row[1]):
                logger.error("Row no match for '[IN..]': %s", row)
                continue

            # Verify row contains [SZ=..] in correct position
            if not sz_re.match(row[2]):
                logger.error("Row no match for '[SZ..]': %s", row)
                continue

            # Verify row size matches that stated in [SZ=..]
            row_size = int(row[2][4:-1])
            if row_size != len(row[4:-1]):
                logger.error(
                    "Row row does not match expected length %d bytes: %s", row_size, row)
                continue

            # Filter by Logical address
            log_addr = int(row[8], 16)

            if log_addr == pc_log_addr:
                # Assume 45 byte lines are H+S
                if row_size == pc_hs_rowlen:
                    row_red = row
                    row_red[1:4] = []
                    row_red[-1:] = []
                    row_red[0] += ';'
                    f_wri['hs'].writerow(row_red)

                # If 8 byte line assume TC
                elif row_size == 8:
                    f_wri['tc'].writerow(row)

                # If 85 or 101 byte line assume HK
                elif (row_size == 85) | (row_size == 101):
                    f_wri['hk'].writerow(row)

                # Else assume Sci
                else:
                    f_wri['sc'].writerow(row)

    for key, value in f_acc.items():
        value.close()

    # Create a H&S Pickle File
    hs_head = ['Time', 'RAW']
    hs = pd.read_csv(file['hs'], sep=';', header=None, names=hs_head)
    hs.to_pickle(proc_dir / "hs_raw.pickle")
    logger.info("PanCam H+S pickled.")

    # Rename HK file with Unix time
    hk_time = hk_nsvf_epoch(swis_dir)
    hk_unix = proc_dir / ("nsvfHK_Unix" + hk_time + ".txt")
    if hk_unix.exists():
        logger.info("Target file exists -- deleting")
        hk_unix.unlink()
    logger.info("Renaming HK file to %s", hk_unix.name)
    file['hk'].rename(hk_unix)

    logger.info("--Parsing SWIS NSVF log completed.")

    return True


def hk_nsvf_epoch(swis_dir: Path):
    """Determines the elsapsed time of the first nsvf hk packet and returns the Unix time.

    Arguments:
        swis_dir {swis_dir} -- Parent to the PROC dir where the nsvf logs are.

    Returns:
        epoch_str {str} -- The UNIX time of the first HK packet in seconds.
    """

    logger.info("Renaming HK file with Unix Epoch from logger file")

    nsvf_hk = PC_Fns.Find_Files(swis_dir, "nsvfHK.txt", SingleFile=True)[0]
    log_file = PC_Fns.Find_Files(swis_dir, "logbook.log", SingleFile=True)[0]

    # Determine relative time elapsed for first HK packet
    logger.info("Extracting Elapsed time from first HK")
    with open(nsvf_hk, 'r') as hk:
        reader = csv.reader(hk, delimiter=' ')
        hk_first = next(reader)
        hk_first_time = hk_first[0][1:-1].split(':')
        elapsed = hk_first_time[0] + '.' + hk_first_time[1]

    # Search through logfile for the same elapsed time and get Unix time
    epoch_str = None
    with open(log_file, 'r') as log:
        reader = csv.reader(log, delimiter=' ')
        for row in reader:
            # Some rows are just blank LF
            try:
                if elapsed in row[0]:
                    epoch_str = row[3][6:].split('.')[0]
                    break
            except:
                None

    if epoch_str == None:
        logger.error("No corresponding UNIX time found")

    return epoch_str


def sci_extract(proc_dir: Path):
    """Creates pci_raw files from the generated Sci.txt file. HS must be decoded and verified first

    Arguments:
        proc_dir {Path} -- Path to Sci.txt file generated by nsvf_parse

    Generates:
        Multiple pci.raw -- For each sci image found
        Multiple .json   -- For each sci image found
    """

    logger.info("Extracting Science Images from SpW Packets")

    sci_file = PC_Fns.Find_Files(proc_dir, 'Sci.txt', SingleFile=True)[0]

    # Calculate number of lines in text file and ensure matches expected
    num_pkts = sum(1 for line in open(sci_file))
    num_imgs = num_pkts // 7
    num_expt = hs.sci_cnt(proc_dir)
    if num_imgs != num_expt:
        logger.error("Missing Sci Parts Detected!")

    # Create directory for binary image files
    img_raw_dir = proc_dir / "IMG_RAW"
    if not img_raw_dir.is_dir():
        logger.info("Generating 'IMG_RAW' directory")
        img_raw_dir.mkdir()

    # Create empty files for each image
    img_lst = list(range(num_imgs))
    f = img_lst
    for item in img_lst:
        write_file = img_raw_dir / (str(item).zfill(2) + ".pci_raw")
        logger.info("Creating binary file %s", write_file.name)
        f[item] = open(write_file, 'w+b')
        create_json(write_file)

    # Read txt file and write to each binary file
    pkts = 7
    cur_img = 0
    cur_pkt = 1
    with open(sci_file) as sci:
        reader = csv.reader(sci, delimiter=' ')
        for row in reader:
            data = row[16:-2]
            binary_format = bytes.fromhex(''.join(data))
            f[cur_img].write(binary_format)
            # Limit to writing 7 packets to each binary file
            if cur_pkt == pkts:
                cur_img += 1
                cur_pkt = 1
            else:
                cur_pkt += 1

    # Close all files
    for file in f:
        file.close()

    logger.info("--Extracting Science Images completed.")


def create_json(img_file: Path):
    """Creates a json file to accompany .pci_raw image.

    Arguments:
        img_file {Path} -- Path to .pci_raw image

    Generates:
        img_name.json -- json file containing processor information.
    """

    json_file = img_file.with_suffix(".json")
    top_lev_dic = {"Processing Info": swisProcVer}

    if json_file.exists():
        logger.info("Deleting file: %s", json_file.name)
    with open(json_file, 'w') as f:
        json.dump(top_lev_dic, f, indent=4)


def sci_compare(proc_dir: Path):
    """Compares the contents of the generated images to the references.

    Reference image used depends on cam type stated in the generated 
    header. Function requires SWIS Reference images to be available. With
    relative path "../data/SWIS_Reference"

    Arguments:
        proc_dir {Path} -- Path to .pci_raw file generated by nsvf_parse

    Generates:
        .tmp -- This file is the .pci_raw without the header but is removed when compared.
    """

    logger.info("Comparing science images")

    # Constants
    ref_dir = Path().parent.absolute() / "data" / "SWIS_Reference"

    # Find PanCam images
    sci_files = PC_Fns.Find_Files(proc_dir, '*.pci_raw')

    for sci in sci_files:
        # First read header and determine cam
        gen = open(sci, 'rb')
        header = gen.read(48)
        cam = upf('u2', header, offset=130)[0]

        if cam == 1:
            # WACL
            ref = ref_dir / "pfm_wacl.raw"
        elif cam == 2:
            # WACR
            ref = ref_dir / "pfm_wacr.raw"
        elif cam == 3:
            # HRC
            ref = ref_dir / "pfm_hrc.raw"
        else:
            # Invalid
            logger.error("Invalid cam type for %s", sci.name)
            continue

        # Store rest of data in a temporary file
        tmp_file = sci.with_suffix(".tmp")
        tmp = open(tmp_file, 'wb')
        tmp.write(gen.read())
        tmp.close()
        logger.info("Generated img tmp file %s", tmp_file.name)

        # Compare files
        logger.info("Comparing: %s", sci.name)
        if filecmp.cmp(tmp_file, ref, shallow=False):
            logger.info("Files match")
        else:
            logger.error("Files do not match!")

        # Clean up tmp file and close read file
        tmp_file.unlink()
        gen.close()


if __name__ == "__main__":
    dir = Path(
        input("Type the path to the folder where the SWIS files are stored: "))

    proc_dir = dir / "PROC"
    if proc_dir.is_dir():
        logger.info("Processing' Directory already exists")
    else:
        logger.info("Generating 'Processing' directory")
        proc_dir.mkdir()

    logging.basicConfig(filename=(proc_dir / 'processing.log'),
                        level=logging.INFO,
                        format='%(asctime)s - %(funcName)s - %(levelname)s - %(message)s')
    logger.info('\n\n\n\n')
    logger.info("Running SIWS.py as main")
    logger.info("Reading directory: %s", dir)

    # routeA = PC_Fns.Find_Files(dir, 'Router_A_packet.log', SingleFile=True)[0]
    # nsvf_parse(routeA)

    hs_extract(dir)
