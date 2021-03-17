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
from shutil import copyfile

import pancam_fns
import hs

logger = logging.getLogger(__name__)
status = logging.getLogger('status')

# Global parameters
swisProcVer = {'swisProcVer': 1.0}


def hk_extract(swis_dir):
    """Generates a Unproc_HKTM.pickle from the given SWIS source

    Arguments:
        swis_dir {Path} -- If using NSVF path is within the Proc directory. Otherwise the instance path is used.

    Generates:
        *_Unproc_HKTM.pickle -- The pandas dataframe containing raw HK and time information within a folder for each instance.
    """

    # Searches for HK files and creates a binary for each file found

    logger.info("Processing SWIS HK")

    # First identify any nsvf files
    hk_files = pancam_fns.Find_Files(swis_dir, 'nsvfHK*.txt', SingleFile=True)
    if hk_files:
        nsvf = True
    # Else look for standard SWIS hk files
    else:
        hk_files = pancam_fns.Find_Files(swis_dir, '*HK.txt', Recursive=False)
        nsvf = False

    if not hk_files:
        logger.warning("No files found - ABORTING")

    for curfile in hk_files:
        dl = pd.DataFrame()
        logger.info("Reading %s", curfile.name)

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
            cur_dir = swis_dir / "PROC"

        dl.to_pickle(cur_dir / "Unproc_HKTM.pickle")


def hs_extract(swis_dir):
    """Extracts the H&S from the SWIS log and puts in a new file

    Arguments:
        swis_dir {Path} -- Dir containing .txt files with simulation data

    Generates:
        _HS.txt -- Simply contains the extracted relevant H&S lines from the log.
        hs_raw.pickle -- Pickle file in ['Time', 'RAW'] format for hs module.
    """

    # Searches through the typescript output .txt file and recreates a simple H&S.txt file

    logger.info("Processing SWIS H&S")

    files_txt = pancam_fns.Find_Files(swis_dir, "*.txt")
    files_HK = pancam_fns.Find_Files(swis_dir, "*_HK*.txt")
    files_sci = pancam_fns.Find_Files(swis_dir, '*_SC.txt')
    files_typ = pancam_fns.Find_Files(swis_dir, "*_typescript.txt")
    files_hs = list(set(files_txt) - set(files_HK) -
                    set(files_sci) - set(files_typ))

    proc_dir = swis_dir / "PROC"

    # Read text file for H&S
    for curfile in files_hs:

        # New file within new folder
        write_file = (proc_dir / "HS.log")
        pancam_fns.exist_unlink(write_file)
        logger.info("Creating HS.log file")
        wf = open(write_file, 'w')

        # Scan through text log and save H&S lines
        consec_skipped = 0  # Counter for number of consecutive lines skipped.
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

                        if len(new_line) == 129:
                            wf.write(new_line)
                            consec_skipped = 0
                        else:
                            consec_skipped += 1
                            if consec_skipped > 15:
                                logger.error(
                                    'Skipping lots of HS entries, count: %s', consec_skipped)
                line = f.readline()
            wf.close()

        # Convert hs.log to pickle file
        hs_head = ['Time', 'RAW']
        hs = pd.read_csv(write_file, sep=';', header=None, names=hs_head)
        hs.to_pickle(proc_dir / "hs_raw.pickle")
        logger.info("PanCam H+S pickled.")


def nsvf_parse(swis_dir):
    """Searches through the NSVF generated packet_log and generates new files from any found PanCam telemetry.

    Arguments:
        swis_dir {Path} -- Path of directory to file to search for Router_A_packet.log.

    Returns:
        Boolean -- True if process runs else False

    Generates:
        H+S.txt -- ASCII txt file of all PanCam health and status.
        nsvfHK.txt  -- ASCII file of the PanCam HK telemetry
        Sci.txt -- ASCII file of the PanCam Sci telemetry.
        TC_Responses.txt  -- ASCII file of the PanCam TC responses.

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
    packet_log = pancam_fns.Find_Files(
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
    file['tc'] = proc_dir / 'TC_Responses.txt'
    file['sc'] = proc_dir / 'Sci.txt'

    for key, value in file.items():
        pancam_fns.exist_unlink(value)
        f_acc[key] = open(value, 'w')
        f_wri[key] = csv.writer(f_acc[key], delimiter=' ',
                                lineterminator='\r')

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
    pancam_fns.exist_unlink(hk_unix)
    logger.info("Renaming HK file to %s", hk_unix.name)
    file['hk'].rename(hk_unix)

    logger.info("--Parsing SWIS NSVF log completed.")

    return True


def nsvf_lb_extract(swis_dir):
    """Extracts all payload lines from the NSVF generated logbook.log.

    Arguments:
        swis_dir {Path} -- Path of directory to file to search for logbook.log


    Generates:
        payloadIf.log -- ASCII txt file of all payload entries in logbook.
    """

    # Function Constants
    # Filter value
    FILT_VAL = 'exo.payloadIf'
    FILT_IGNORE = ['[INFO] Scheduling method PancamDelayedSpwTx with offset',
                   'txSpw : Successful spacewire transmission on link']

    logger.info('Processing SWIS NSVF logbook.log')

    logger.info('Searching for logbook.log file')
    logbook = pancam_fns.Find_Files(
        swis_dir, 'logbook.log', SingleFile=True)

    if logbook == []:
        return
    else:
        logbook = logbook[0]

    # Create a PROC directory if does not already exist
    proc_dir = logbook.parent / 'PROC'
    if not proc_dir.is_dir():
        proc_dir.mkdir()

    # File to write too
    f_pat = proc_dir / 'payloadIf.log'

    pancam_fns.exist_unlink(f_pat)
    f_acc = open(f_pat, 'w')
    f_wri = csv.writer(f_acc, delimiter='\t',
                       lineterminator='\r')

    # Open file and check format is as expcted
    # Contains ..[IN=..].. and ..[SZ=..].., ..[EOP] at the end of each line

    with open(logbook, 'r') as log:
        reader = csv.reader(log, delimiter='\t')
        logger.info("Reading file %s", log.name)
        for row in reader:
            if len(row) < 6:
                continue

            if row[4] == FILT_VAL:
                if row[5].startswith(FILT_IGNORE[0]):
                    continue

                elif row[5].startswith(FILT_IGNORE[1]):
                    continue

                else:
                    f_wri.writerow(row)

    f_acc.close()

    logger.info("--Parsing SWIS NSVF logbook completed.")

    return


def nsvf_tc_extract(swis_dir):
    """Locates sent TCs from the contents of the TC_Responses.txt file.

    Arguments:
        swis_dir {Path} -- Path of directory to file to search for Router_A_packet.log

    Requires:
        TC_Responses.txt -- File generated by nsvf_parse of PanCam responses.

    Generates:
        TC.txt -- ASCII txt file of all TCs sent to PanCam.
    """

    logger.info('Extracting SWIS NSVF TCs')

    logger.info('Searching for TC_Responses.txt file')
    file_responses = pancam_fns.Find_Files(
        swis_dir, 'TC_Responses.txt', SingleFile=True)

    if file_responses == []:
        return
    else:
        file_responses = file_responses[0]

    logger.info('Searching for Router_A_packet.log')
    file_logbook = pancam_fns.Find_Files(
        swis_dir, 'Router_A_packet.log', SingleFile=True)

    if file_logbook == []:
        return
    else:
        file_logbook = file_logbook[0]

    # Create a PROC directory if does not already exist
    proc_dir = file_logbook.parent / 'PROC'
    if not proc_dir.is_dir():
        proc_dir.mkdir()

    # Create a list of all relevant packets from packet.log
    tc_list = []
    with open(file_logbook, 'r') as packets:
        log_reader = csv.reader(packets, delimiter=' ')
        logger.info("Extracting potential TCs from packet log %s",
                    file_logbook.name)
        for row in log_reader:
            if row[1] != '[IN=08]':
                continue
            if len(row) < 32:  # Minimum PanCam command is Spw header and 5 bytes
                continue
            tc_list.append(row)

    # File to write too
    f_tc = proc_dir / 'TC.txt'

    pancam_fns.exist_unlink(f_tc)
    f_acc = open(f_tc, 'w')
    f_wri = csv.writer(f_acc, delimiter=' ',
                       lineterminator='\r')

    with open(file_responses, 'r') as resp:
        reader = csv.reader(resp, delimiter=' ')
        for tc_resp in reader:
            trans_id = tc_resp[10]
            trans_time = tc_resp[0][:2]
            count = 0
            for tc in tc_list:
                if tc[10] != trans_id:
                    continue
                if tc[0][:2] != trans_time:
                    continue
                count += 1
                f_wri.writerow(tc)

                if count != 1:
                    logger.error("Multiple potential TC matches found!")

    f_acc.close()

    logger.info("--Extracting SWIS NSVF TCs completed.")

    return


def hk_nsvf_epoch(swis_dir):
    """Determines the elsapsed time of the first nsvf hk packet and returns the Unix time.

    Arguments:
        swis_dir {swis_dir} -- Parent to the PROC dir where the nsvf logs are.

    Returns:
        epoch_str {str} -- The UNIX time of the first HK packet in seconds.
    """

    logger.info("Renaming HK file with Unix Epoch from logger file")

    nsvf_hk = pancam_fns.Find_Files(swis_dir, "nsvfHK.txt", SingleFile=True)[0]
    log_file = pancam_fns.Find_Files(
        swis_dir, "logbook.log", SingleFile=True)[0]

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


def sci_extract(swis_dir, nsvf=False):
    """Creates pci_raw files from the generated Sci.txt file. HS must be decoded and verified first

    Arguments:
        swis_dir {Path} -- If using NSVF path is within the Proc directory. Otherwise the source path is used.
        nsvf {bool} -- Set to true if from nsvf log (default: {False})

    Generates:
        Multiple pci.raw -- For each sci image found
        Multiple .json   -- For each sci image found
    """

    logger.info("Extracting Science Images from SpW Packets")

    if nsvf:
        sci_file = pancam_fns.Find_Files(swis_dir, 'Sci.txt', SingleFile=True)
    else:
        sci_file = pancam_fns.Find_Files(
            swis_dir, '*SC.txt', SingleFile=True, Recursive=False)

    if not sci_file:
        logger.warning("No Science Image files found")
        return

    sci_file = sci_file[0]

    # Create individual folders and save here
    if nsvf:
        cur_dir = swis_dir
    else:
        cur_dir = swis_dir / "PROC"

    # Calculate number of lines in text file and ensure matches expected
    num_pkts = sum(1 for line in open(sci_file))
    num_imgs = num_pkts // 7
    num_expt = hs.sci_cnt(cur_dir)
    if num_imgs != num_expt:
        logger.error("Missing Sci Parts Detected! %s", sci_file.name)

    # Create directory for binary image files
    img_raw_dir = cur_dir / "IMG_RAW"
    if not img_raw_dir.is_dir():
        logger.info("Generating 'IMG_RAW' directory %s", sci_file.name)
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
    blank_file = False
    with open(sci_file) as sci:
        if nsvf:
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

        else:
            # Create temporary file to compare to *SC.bin
            tmp_file = img_raw_dir / "sc_bin_comp.bin"
            f_tmp = open(tmp_file, 'w+b')

            line = sci.readline()
            while line != "":
                # Remove TimeStamp and [Informative]
                line_red = line.replace("Timestamp: ", "")
                line_red = line_red[26:]
                line_red = line_red.replace("0x", "")
                line_red = line_red.replace("\n", "").replace("\r", "")
                binary_format = bytes.fromhex(line_red)

                # Write binary_format to tmp file
                f_tmp.write(binary_format)

                # Remove spacewire 12 byte header and 1 byte footer
                data = binary_format[12:-1]

                if (cur_pkt < 7) and (len(data) != 307200):
                    logger.error(
                        "Incorrect LDT Length. Image: %d, Cur_pkt: %d", cur_img, cur_pkt)
                    logger.info("Expected: 307200")
                    logger.info("Got: %d", len(data))

                elif (cur_pkt == 7) and (len(data) != 254000):
                    logger.error(
                        "Incorrect final LDT Length. Image: %d", cur_img)
                    logger.info("Expected: 254000")
                    logger.info("Got: %d", len(data))

                # Check if ancillary data is empty
                if (cur_pkt == 1):
                    blank_file = (data[:49] == bytes(49))

                f[cur_img].write(data)

                # Limit to writing 7 packets to each binary file
                if cur_pkt == pkts:
                    f[cur_img].close()

                    if blank_file:
                        logger.error(
                            'Image #%d is a blank image, ignoring', cur_img)
                        filename = Path(f[cur_img].name)
                        filename.rename(filename.with_suffix('.pci_blank'))
                        logger.info(
                            'Deleting blank image json: %s', filename.stem)
                        filename.with_suffix('.json').unlink()

                    cur_img += 1
                    cur_pkt = 1

                else:
                    cur_pkt += 1

                line = sci.readline()

            f_tmp.close()

            # Compare temp file to original bin file
            ref = sci_file.with_suffix(".bin")
            if filecmp.cmp(tmp_file, ref, shallow=False):
                logger.info(
                    "Temporary file matches output .bin %s", sci_file.name)
            else:
                logger.error(
                    "Temporary file does not match output .bin %s", sci_file.name)

            tmp_file.unlink()

    logger.info("--Extracting Science Images completed.")


def create_json(img_file):
    """Creates a json file to accompany .pci_raw image.

    Arguments:
        img_file {Path} -- Path to .pci_raw image

    Generates:
        img_name.json -- json file containing processor information.
    """

    json_file = img_file.with_suffix(".json")
    top_lev_dic = {"Processing Info": swisProcVer}

    pancam_fns.exist_unlink(json_file)

    with open(json_file, 'w') as f:
        json.dump(top_lev_dic, f, indent=4)


def sci_compare(proc_dir):
    """Compares the contents of the generated images to the references.

    Reference image used depends on cam type stated in the generated
    header. Function requires SWIS Reference images to be available. With
    relative path "../resources/SWIS_Reference"

    Arguments:
        proc_dir {Path} -- Path to .pci_raw file generated by nsvf_parse

    Generates:
        .tmp -- This file is the .pci_raw without the header but is removed when compared.
    """

    logger.info("Comparing science images")

    # Constants
    ref_dir = Path().parent.absolute() / "resources" / "swis_reference_images"

    # Find PanCam images
    sci_files = pancam_fns.Find_Files(proc_dir, '*.pci_raw')

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
            status.info("Science Files match")
        else:
            logger.error("Science Files do not match!")

        # Clean up tmp file and close read file
        tmp_file.unlink()
        gen.close()


def create_instances(swis_dir):
    """Used for SWIS TB. Creates a folder for each HK file found and copies all corresponding files to that folder.

    Arguments:
        swis_dir {Path} -- Source path to TB output, usual "Bin" folder.

    Returns:
        instances {List of Paths} -- Returns a list of generated instance folders.
    """

    # Creates a folder for each HK file found and moves all corresponding files to that folder.
    logger.info("Creating Instances for SWIS TB")

    # Else look for standard SWIS hk files
    hk_files = pancam_fns.Find_Files(swis_dir, "*HK.txt", Recursive=False)

    # If only 1 hk_files assume no need to create instances.
    if len(hk_files) == 0:
        return []

    elif len(hk_files) == 1:
        logger.info("One instances found so aborting")
        return [swis_dir]

    instances = []

    if not hk_files:
        logger.warning("No files found - ABORTING")
        return instances

    for curfile in hk_files:
        instance_name = curfile.stem[:-3]

        # Create instance dir
        logger.info("Creating instance %s", instance_name)
        inst_dir = swis_dir / "PROC" / instance_name
        if inst_dir.is_dir():
            logger.info("Instance Directory already exists")
        else:
            logger.info("Generating 'Processing' directory")
            inst_dir.mkdir()
        instances.append(inst_dir)

        # Create instance proc dir
        proc_dir = inst_dir / "PROC"
        if proc_dir.is_dir():
            logger.info("Instance Proc Directory already exists")
        else:
            logger.info("Generating Instance 'Processing' directory")
            proc_dir.mkdir()

        # Move all files
        inst_files = ['.txt', '_HK.bin', "_HK.txt", "_SC.bin", "_SC.txt"]
        for suffix in inst_files:
            ref = (instance_name + suffix)
            orig = swis_dir / ref
            if orig.exists():
                copyfile(orig, inst_dir / ref)
                orig.unlink()

    return instances


def get_instances(swis_dir: Path):
    """Used for SWIS TB to get a list of all test directories to itterate through. 

   Arguments:
        swis_dir {Path} -- Source path to TB output, usual "Bin" folder.

    Returns:
        instances {List of Paths} -- Returns a list of generated instance folders.
    """
    # Creates a folder for each HK file found and moves all corresponding files to that folder.
    logger.info("Looking for Instances of SWIS TB")

    hk_files = pancam_fns.Find_Files(swis_dir, "*HK.txt", Recursive=False)

    if hk_files:
        logger.info("HK Files found in this directory assuming working folder")
        return [swis_dir]

    if swis_dir.stem != "PROC":
        swis_dir = swis_dir.joinpath('PROC')

        if not swis_dir.exists:
            logger.error("No Proc folder found for SWIS instances.")
            raise ValueError('No Proc folder found for SWIS instances')

    return [inst for inst in swis_dir.iterdir() if inst.is_dir()]


if __name__ == "__main__":
    dir = Path(
        input("Type the path to the folder where the SWIS files are stored: "))

    proc_dir = dir / "PROC"
    if proc_dir.is_dir():
        status.info("Processing' Directory already exists")
    else:
        status.info("Generating 'Processing' directory")
        proc_dir.mkdir()

    logger, status = pancam_fns.setup_logging()
    pancam_fns.setup_proc_logging(logger, proc_dir)

    logger.info('\n\n\n\n')
    logger.info("Running swis.py as main")
    logger.info("Reading directory: %s", proc_dir)

    # routeA = PC_Fns.Find_Files(dir, 'Router_A_packet.log', SingleFile=True)[0]
    # nsvf_parse(routeA)
    # nsvf_lb_extract(dir)
    # nsvf_tc_extract(dir)

    # instances = create_instances(dir)
    instances = [dir]
    if instances:
        for instance in instances:
            print("Reading Instance: ", instance)
            hk_extract(instance)
            hs_extract(instance)
            hs.decode(instance / "PROC", True)
            hs.verify(instance)
            sci_extract(instance)
            sci_compare(instance)
