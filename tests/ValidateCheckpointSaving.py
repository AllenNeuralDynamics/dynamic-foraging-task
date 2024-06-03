import json
import os
import numpy as np

def load_json(file):
    """Load a json file and return the data as a dictionary"""
    with open(file, 'r') as f:
        data = json.load(f)
    return data

def load_end_of_session_style(testfile):
    """Load the end_of_session style file and return the data as a dictionary"""
    splt = os.path.basename(testfile).split('_')
    fl = os.path.join(testfile,'behavior', f'{splt[1]}_{splt[2]}_{splt[3]}.json')
    return load_json(fl)

def load_all_settings_files(checkpoint_folder):
    """Load all the settings files and return the data as a dictionary"""
    checkpoint_files = os.listdir(checkpoint_folder)

    ### read the settings file first ###
    settings_files = [ii for ii in checkpoint_files if 'settings' in ii]
    trial_number = []
    for ii in settings_files:
        if 'init' in ii:
            trial_number.append(-1)
        else:
            trial_number.append(int(ii.split('_')[1].split('.')[0]))
    order = np.argsort(trial_number)
    settings_files = [settings_files[ii] for ii in order]
    # Actual file reading.
    with open(os.path.join(checkpoint_folder, settings_files[0]), 'r') as f:
        settings = json.load(f)

    # Override any start settings with the end settings
    for ii in settings_files[1:]:
        with open(os.path.join(checkpoint_folder, ii), 'r') as f:
            this_settings = json.load(f)
        for key in this_settings.keys():
            settings[key] = this_settings[key]

    return settings

def load_all_trial_files(checkpoint_folder):
    """Load all the trial files and return the data as a dictionary"""
    checkpoint_files = os.listdir(checkpoint_folder)
    trial_files = [ii for ii in checkpoint_files if 'trial' in ii]
    # Sort so that they are in the right order
    trial_number = np.array([int(ii.split('_')[1].split('.')[0]) for ii in trial_files])
    order = np.argsort(trial_number)
    trial_files = [trial_files[ii] for ii in order]


    # Combine all files into a single dictionary
    for ii in trial_files:
        if trial_files.index(ii) == 0:
            with open(os.path.join(checkpoint_folder, ii), 'r') as f:
                trial_data = json.load(f)
            for key in trial_data.keys():
                trial_data[key] = list([trial_data[key]])

        else:
            with open(os.path.join(checkpoint_folder, ii), 'r') as f:
                this_trial_data = json.load(f)
            for key in this_trial_data.keys():
                if key in trial_data.keys():
                    trial_data[key].append(this_trial_data[key])
                else:
                    trial_data[key] = list([None]*trial_files.index(ii)).append(this_trial_data[key])
    trial_data.pop('_whoami')
    trial_data.pop('_whenami')

    return trial_data


if __name__ == "__main__":
    testfile = r"C:\Users\yoni.browning\Documents\ForagingOutData\TestBox\0\behavior_0_2024-05-30_13-33-07"

    ### Load the end_of_session style file ###
    end_of_session_data = load_end_of_session_style(testfile)


    # Load and combine all the checkpoint files into a single dictionary
    checkpoint_folder = os.path.join(testfile,'behavior','per_trial_checkpoints')
    checkpoint_files = os.listdir(checkpoint_folder)
    
    ### read the settings file first ###
    settings = load_all_settings_files(checkpoint_folder)
    
    ### read the trial files ###
    trial_data = load_all_trial_files(checkpoint_folder)

    ### read the state files ##
    state_files = [ii for ii in checkpoint_files if 'state' in ii]
    # Sort so that they are in the right order
    state_files = sorted(state_files, key=lambda x: int(x.split('_')[1].split('.')[0]))
    print(state_files)

    # 'B_' keys that do not have a history
    no_history = ['B_ANewBlock',
                  'B_AnimalCurrentResponse',
                  'B_AnimalCurrentStimulus',
                  'B_Baited',
                  'B_CurrentRewardProb',
                  'B_CurrentRewarded',
                  'B_CurrentTrialN',
                  'B_for_eff_optimal',
                  'B_for_eff_optimal_random_seed',
                  'B_Time',
                  'B_LickPortN',
                  'B_RewardFamilies',
                  ]

    state_data = {}
    state_data_read_axis = {}
    for ii in state_files:
        with open(os.path.join(checkpoint_folder, ii), 'r') as f:
            this_state_data = json.load(f)
        for key in this_state_data.keys():
            if ('BS_' in key) or (key in no_history):
                state_data[key] = this_state_data[key]
            elif (key in ['_whoami', '_whenami']):
                continue    
            else:
                # Update keys without history
                if len(np.array(this_state_data[key]))==0:
                    state_data[key] = []
                elif key not in state_data_read_axis.keys():
                    state_data_read_axis[key] = np.argmin(np.array(this_state_data[key]).shape)
                    state_data[key] = this_state_data[key]
                else:
                    state_data[key] = np.concatenate((state_data[key], this_state_data[key]), axis=state_data_read_axis[key])


    # Combine all files into a single dictionary
    checkpoint_data = {**state_data, **trial_data, **settings}


    # Check that the two dictionaries are the same
    checkpoint_data_keys = list(checkpoint_data.keys())
    end_of_session_data_keys = list(end_of_session_data.keys())
    print(f'There are {len(checkpoint_data_keys)} keys in the checkpoint data' )
    print(f'There are {len(end_of_session_data_keys)} keys in the end_of_session data' )
    print(f'There are {len(set(checkpoint_data_keys).intersection(set(end_of_session_data_keys)))} shared keys between the two files.')


    shared_keys = [key for key in checkpoint_data_keys if key in end_of_session_data_keys]

    # Check that elements are the same 
    fails = [] 
    for key in shared_keys:
        if isinstance(checkpoint_data[key],np.ndarray) or isinstance(end_of_session_data[key],np.ndarray):
            if np.array(checkpoint_data[key]).shape != np.array(end_of_session_data[key]).shape:
                fails.append(key)
                continue
            if not np.allclose(np.array(checkpoint_data[key]), np.array(end_of_session_data[key])):
                fails.append(key)
        elif not (checkpoint_data[key] == end_of_session_data[key]):
            fails.append(key)

    print('Of these shared keys, there are ', len(fails), ' keys that cannot be reconciled between the two files.')
    if len(fails)>0:
        print(fails)
        print('You should fix this before deploying.')
    else:
        print('Data shared across the two files is the same!')

    unique_checkpoint_keys = [key for key in checkpoint_data_keys if key not in end_of_session_data_keys]
    unique_end_of_session_keys = [key for key in end_of_session_data_keys if key not in checkpoint_data_keys]
    print('\n')
    print('There are ', len(unique_checkpoint_keys), ' keys in the checkpoint data that are not in the end_of_session data.')
    print('The expect number is 2; _whoami and _whenami')
    if len(unique_checkpoint_keys)>2:
        print('We found: ')
        print(unique_checkpoint_keys)
        print('You should fix this before deploying.')
    else:
        print('The unique keys in the checkpoint data are _whoami and _whenami. This is expected.')


    print('There are ', len(unique_end_of_session_keys), ' keys in the end_of_session data that are not in the checkpoint data.')
    print('The expected number is 0.')
    if len(unique_end_of_session_keys)>0:
        print('We found: ')
        print(unique_end_of_session_keys)
        print('You should fix this before deploying.')




