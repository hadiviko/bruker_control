# Arduino Serial Communication and Config File Generation for Bruker 2P Setup
# Jeremy Delahanty Mar. 2021
# pySerialTransfer written by PowerBroker2
# https://github.com/PowerBroker2/pySerialTransfer

# -----------------------------------------------------------------------------
# Import Packages
# -----------------------------------------------------------------------------
# Import JSON for configuration file
import json
# Import ordered dictionary to ensure order in json file
from collections import OrderedDict
# Import argparse if you want to create a configuration on the fly
import argparse
# Import scipy for statistical distributions
import scipy
# Import scipy.stats truncated normal distribution for ITI Array
from scipy.stats import truncnorm
# Import numpy for trial array generation and manipulation
import numpy as np
# Import numpy default_rng
from numpy.random import default_rng
# Import pySerialTransfer for serial comms with Arduino
from pySerialTransfer import pySerialTransfer as txfer
# Import sys for exiting program safely
import sys

# -----------------------------------------------------------------------------
# Functions
# -----------------------------------------------------------------------------

#### Experiment Metadata Functions ####
# If user wants to set metadata on the fly, use manually_set_metadata()
def manually_set_metadata():

    # Define Total Number of Trials
    totalNumberOfTrials = parser.num_trials

    #### Sound ####
    # Define Noise Duration
    noiseDuration = parser.noise_dur
    # Define Punish Tone in Hz
    punishTone = parser.punish_tone
    # Define Reward Tone in Hz
    rewardTone = parser.reward_tone

    #### Sucrose ####
    # Define Sucrose Delivery Time
    USDeliveryTime_Sucrose = 5 # 5ms, this is not subject to change
    # Define Sucrose Consumption Time
    USConsumptionTime_Sucrose = parser.consumption_dur
    #### Airpuff ####
    # Define Airpuff Delivery Time
    USDeliveryTime_Air = parser.airpuff_dur

    #### Metadata File Creation ####
    # Build metadata dictionary TODO: use dictionary comprehension
    metaData = {"totalNumberOfTrials" : totalNumberOfTrials,
                "trialNumber" : trialNumber,
                "noiseDuration" : noiseDuration,
                "punishTone" :punishTone,
                "rewardTone" : rewardTone,
                "USDeliveryTime_Sucrose" : USDeliveryTime_Sucrose,
                "USDeliveryTime_Air" : USDeliveryTime_Air}
    # Set file path for writing config # # TODO: set this as an argument
    config_file_path = 'C:/Users/jdelahanty/Documents/gitrepos/headfix_control/'
    # TODO: What is our naming convention going to be for configuration files?
    # Add this convention to the file generation for its name
    config_file_name = parser.filename
    # Write out config file as an ordered dictionary
    with open(config_file_path + config_file_name, "w") as outfile:
        json.dump(metaData, outfile, object_pairs_hook=OrderedDict)

    # Return metaData dict for use with send_metadata function
    return metaData

# When metadata is available, send it to the Arduino
def send_metadata(config, packet_id=0):
    # Read JSON file given to the function and obtain contents
    with open(config, 'r') as inFile:
        contents = inFile.read()
    # Convert from JSON to Dictionary using loads()
    config = json.loads(contents, object_pairs_hook=OrderedDict)
    # Give value type override list for sending packets
    # TODO: Add this as part of the configuration file creation and load
    # TODO: Ideally, configuration generation would prohibit user from making
    # config file too big
    # Open transfer link, compile packet, and check packet size
    try:
        # Open comms to Arduino at default baud of 115200 TODO: Grab arduino port automatically
        link.txfer.SerialTransfer('COM12', 115200, debug=True)
        # Stuff TX buffer for packet
        # https://docs.python.org/3/library/struct.html#format-characters
        # Start packet length of 0
        metaData_size = 0
        # For each value in the dictionary and override type
        for key, value in config.items():
            metaData_size = link.txobj(value, metaData_size, val_type_override=byte_type)
        # If the packet is too long, tell experimenter to restructure and exit
        if metaData_size > 244:
            print("Packet is too long to transfer! Restructure config file.")
            print("Exiting")
            sys.exit()
        # Otherwise, send the packet to the Arduino!
        else:
            link.send(metaData_len, packet_id)

        # Transmission is occuring. While the link is unavailable, pass
        while not link.available():
            pass
        # Now, receive the list back from Arduino and confirm its correct
        # Receive metadata from Arduino
        rec_metaData = link.rx_obj(obj_type=type(config),
                                   obj_byte_size=metaData_size,
                                   list_format='i')
        # Check if received metadata is the same as sent metadata
        # If the values in the configuration match received list, move on
        if list(config.values()) == rec_metaData:
            print("Metadata Onboard!")
            # Close link
            link.close()
        # If there's an error, say so and exit program
        ## TODO: Introduce error check that will resend several times
        else:
            print("Error! Transfer Unsuccessful...")
            link.close()
            print("Exiting...")
            sys.exit()

    # Catch exceptions
    # If KeyboardInterrupt, close link and abort the program
    except KeyboardInterrupt:
        try:
            link.close()
            exit(0)
        except:
            pass
    # If there's an error, print the traceback provided and abort the program
    except:
        import traceback
        traceback.print_exc()
        # Close connection and exit the program
        try:
            link.close()
            print("Exiting...")
            exit(0)
        except:
            pass


#### Trial Array Functions ####
# Random Trials Array Generation
def gen_trial_array(totalNumberOfTrials):
    # Always initialize trial array with 3 reward trials
    trialArray = [1,1,1]
    # Define number of samples needed from generator
    num_samples = totalNumberOfTrials - len(trialArray)
    # Define probability that the animal will receive sucrose 60% of the time
    sucrose_prob = 0.60
    # Initialize random number generator with default_rng
    rng = np.random.default_rng()
    # Generate a random trial array with Generator.binomial
    # Use n=1 to pull one sample at a time, p=.6 as probability of sucrose
    # Use num_samples to fill out accurate number of trials
    # Use .tolist() to convert random_trials from np.array to list
    random_trials = rng.binomial(
    n=1, p=sucrose_prob, size=num_samples
    ).tolist()
    # Append the two arrays together
    for i in random_trials:
        trialArray.append(i)

    ## TODO: Write out the trial array into JSON as part of experiment config

    # Return trialArray
    return trialArray

# # TODO: If user has a predefined trial set, allow them to import it
def import_trial_array(file):
    # code....
    return


# ITI Array Generation
def gen_iti_array(totalNumberOfTrials):
    # Initialize empty iti trial array
    iti_array = []
    # Define lower and upper limits on ITI values in ms
    iti_lower, iti_upper = 2500, 3500
    # Define mean and variance for ITI values
    mu, sigma = 3000, 1000
    # Upper bound calculation
    upper_bound = (iti_upper - mu)/sigma
    # Lower bound calculation
    lower_bound = (iti_lower - mu)/sigma
    # Generate array by sampling from truncated normal distribution w/scipy
    iti_array = truncnorm.rvs(
    lower_bound, upper_bound, loc=mu, scale=sigma, size=totalNumberOfTrials
    )
    # ITI Array generated with have decimals in it and be float type
    # Use np.round() to round the elements in the array and type them as int
    iti_array = np.round(iti_array).astype(int)
    # Finally, generate ITIArray as a list for pySerialTransfer
    ITIArray = iti_array.tolist()

    ## TODO: Write out the ITI array into JSON as part of experiment config

    # Return ITIArray
    return ITIArray

# # TODO: If user has predefined ITI array, allow them, to import it
def import_iti_array(file):
    # code...
    return

if __name__ == '__main__':
    trialArray = gen_trial_array(10)
    ITIArray = gen_iti_array(10)
    try:
        # Initialize COM Port for Serial Transfer
        link = txfer.SerialTransfer('COM12', 115200, debug=True)

        #read JSON config file
        with open('C:/Users/jdelahanty/Documents/gitrepos/headfix_control/config.json', 'r') as inFile:
            contents = inFile.read()

        # Convert from JSON to Dictionary
        config = json.loads(contents)

        # stuff TX buffer (https://docs.python.org/3/library/struct.html#format-characters)
        metaData_size = 0
        metaData_size = link.tx_obj(config['metadata']['totalNumberOfTrials']['value'],       metaData_size, val_type_override='B')
        metaData_size = link.tx_obj(config['metadata']['trialNumber']['value'],               metaData_size, val_type_override='I')
        metaData_size = link.tx_obj(config['metadata']['noiseDuration']['value'],             metaData_size, val_type_override='H')
        metaData_size = link.tx_obj(config['metadata']['punishTone']['value'],                metaData_size, val_type_override='H')
        metaData_size = link.tx_obj(config['metadata']['rewardTone']['value'],                metaData_size, val_type_override='H')
        metaData_size = link.tx_obj(config['metadata']['USDeliveryTime_Sucrose']['value'],    metaData_size, val_type_override='B')
        metaData_size = link.tx_obj(config['metadata']['USDeliveryTime_Air']['value'],        metaData_size, val_type_override='B')
        metaData_size = link.tx_obj(config['metadata']['USConsumptionTime_Sucrose']['value'], metaData_size, val_type_override='H')

        link.open()

        link.send(metaData_size, packet_id=0)

        while not link.available():
            pass

        # Receive packet from Arduino
        # Create rxmetaData dictionary
        rxmetaData = {}
        rxmetaData_size = 0

        rxmetaData['totalNumberOfTrials'] = link.rx_obj(obj_type='B', start_pos=rxmetaData_size)
        rxmetaData_size += txfer.ARRAY_FORMAT_LENGTHS['B']
        rxmetaData['trialNumber'] = link.rx_obj(obj_type='I', start_pos=rxmetaData_size)
        rxmetaData_size += txfer.ARRAY_FORMAT_LENGTHS['I']
        rxmetaData['noiseDuration'] = link.rx_obj(obj_type='H', start_pos=rxmetaData_size)
        rxmetaData_size += txfer.ARRAY_FORMAT_LENGTHS['H']
        rxmetaData['punishTone'] = link.rx_obj(obj_type='H', start_pos=rxmetaData_size)
        rxmetaData_size += txfer.ARRAY_FORMAT_LENGTHS['H']
        rxmetaData['rewardTone'] = link.rx_obj(obj_type='H', start_pos=rxmetaData_size)
        rxmetaData_size += txfer.ARRAY_FORMAT_LENGTHS['H']
        rxmetaData['USDeliveryTime_Sucrose'] = link.rx_obj(obj_type='B', start_pos=rxmetaData_size)
        rxmetaData_size += txfer.ARRAY_FORMAT_LENGTHS['B']
        rxmetaData['USDeliveryTime_Air'] = link.rx_obj(obj_type='B', start_pos=rxmetaData_size)
        rxmetaData_size += txfer.ARRAY_FORMAT_LENGTHS['B']
        rxmetaData['USConsumptionTime_Sucrose'] = link.rx_obj(obj_type='H', start_pos=rxmetaData_size)

        # link.close()

        print(rxmetaData)

        # Check if metaData was sent correctly:
        # if config == rxmetaData:
        #     print("Confirmed Metadata!")
        #     metaData_status = True
        # else:
        #     print("Metadata error! Exiting...")
        #     sys.exit()

        # link.open()
        # Now send the trial array:
        trialArray_size = 0
        trialArray_size = link.tx_obj(trialArray)
        link.send(trialArray_size, packet_id=1)

        print(trialArray)

        while not link.available():
            pass

        # Receive trial array:
        rxtrialArray = link.rx_obj(obj_type=type(trialArray),
        obj_byte_size=trialArray_size, list_format='i')

        print(rxtrialArray)
        # else:
        #     print("Trial Array error! Exiting...")
        #     sys.exit()

        # Finally, send ITI array:
        ITIArray_size = 0
        ITIArray_size = link.tx_obj(ITIArray)
        link.send(ITIArray_size, packet_id=2)

        print(ITIArray)

        while not link.available():
            pass

        # Receive ITI Array
        rxITIArray = link.rx_obj(obj_type=type(ITIArray),
        obj_byte_size = ITIArray_size,
        list_format='i')

        print(rxITIArray)

        link.close()


        # Confirm data was sent/received properly:
        # if ITIArray == rxITIArray:
        #     print("Confrimed ITI Array!")
        #     ITIArray_status = True
        # else:
        #     print("ITI Array error! Exiting...")
        #     sys.exit()



    except KeyboardInterrupt:
        try:
            link.close()
        except:
            pass
    except:
        import traceback
        traceback.print_exc()

        try:
            link.close()
        except:
            pass

# Use this for main function later after solving packet transmission...
# if __name__ == "__main__":
#         # Create argument parser
#         parser = argparse.ArgumentParser(description='Manually Set Metadata')
#         # Add number of trials, '-t', argument
#         parser.add_argument('-t',
#                             metavar='--num_trials',
#                             type=int,
#                             help='Number of trials for experiment (required)',
#                             required=True)
#         # Add noise duration, '-n', argument
#         parser.add_argument('-n',
#                             metavar='--noise_dur',
#                             type=int,
#                             help='How long (ms) should tones play',
#                             required=False,
#                             default=2000)
#         # Add punishment tone, '-p', argument
#         parser.add_argument('-p',
#                             metavar='--punish_tone',
#                             type=int,
#                             help='Tone in Hz to play for airpuff',
#                             required=False,
#                             default=2000)
#         # Add reward tone, '-r', argument
#         parser.add_argument('-r',
#                             metavar='--reward_tone',
#                             type=int,
#                             help='Tone in Hz to play for sucrose',
#                             required=False,
#                             default=18000)
#         # Add consumption time for sucrose, '-c', argument
#         parser.add_argument('-c',
#                             metavar='--consumption_dur',
#                             type=int,
#                             help='How long (ms) should sucrose be present',
#                             required=False,
#                             default=1000)
#         # Add airpuff duration, '-a', argument
#         parser.add_argument('-a',
#                             metavar='airpuff_dur',
#                             type=int,
#                             help='How long (ms) should airpuff be delivered',
#                             required=False,
#                             default=10)
#         # Add filename, '-f', argument
#         parser.add_argument('-f',
#                             metavar='--filename',
#                             type=str,
#                             help='Filename for configuration (required)',
#                             required=True)
#         # Parse the arguments and make them available for variable storage
#         parser.parse_args()
