import os
import harp
import json

import pandas as pd

def correct_drop_frames(save_data=None,json_file=None,harp_folder=None,video_folder=None):
    '''correcting drop frames in videos
    
    video_folder: folder containing the videos. Optionally, could be read from the json_file
    harp_folder: folder containing the harp data. Optionally, could be read from the json_file
    json_file: session json file
    output: corrected timestamps of different cameras

    '''
    if (save_data is None) and (json_file is None) and (harp_folder is None or video_folder is None):
        print('json_file or harp_folder and video_folder must be provided')
        return
    
    if harp_folder is not None and video_folder is not None:
        if not os.path.exists(harp_folder):
            print('harp_folder does not exist')
            return
        if not os.path.exists(video_folder):
            print('video_folder does not exist')
            return
    # use the folder from the json file
    elif json_file is not None:
        with open(json_file) as f:
            Obj = json.load(f)
            if 'HarpFolder' in Obj:
                # check the drop frames of the loaded session
                harp_folder=Obj['HarpFolder']
                video_folder=Obj['VideoFolder']
            else:
                print('HarpFolder or VideoFolder not found in the json file')
                return
    elif save_data is not None:
        if hasattr(save_data,'HarpFolder'):
            # check the drop frames of the loaded session
            harp_folder=save_data.HarpFolder
            video_folder=save_data.VideoFolder
        else:
            print('harp_folder or video_folder not found in the save_data')
            return
    else:
        print('json_file or harp_folder and video_folder must be provided')
        return

    # read the video files
    camera_trigger_file=os.path.join(harp_folder,'BehaviorEvents','Event_94.bin')
    if os.path.exists(camera_trigger_file):
        triggers = harp.read(camera_trigger_file)
        trigger_length = len(triggers)
    else:
        trigger_length=0
        print('No camera trigger file found!')
        return
    csv_files = [file for file in os.listdir(video_folder) if file.endswith(".csv")]
    avi_files = [file for file in os.listdir(video_folder) if file.endswith(".avi")]

    video_info = {}
    for avi_file in avi_files:
        csv_file = avi_file.replace('.avi', '.csv')
        if csv_file not in csv_files:
            drop_frames_warning_text+=f'No csv file found for {avi_file}\n'
        else:
            key=csv_file.replace('.csv', '')
            video_info[key]={}
            current_frames = pd.read_csv(os.path.join(video_folder, csv_file), header=None)
            video_info[key]['harp_time_stamps'] = current_frames.iloc[:, 0].values
            video_info[key]['frame_ID'] = current_frames.iloc[:, 1].values
            video_info[key]['camera_time_stamps'] = current_frames.iloc[:, 2].values
            video_info[key]['camera_exposure_time'] =current_frames.iloc[:, 3].values
            video_info[key]['camera_gain'] = current_frames.iloc[:, 4].values
            num_frames = len(current_frames)
            if num_frames < trigger_length:
                # drop frames
                video_info[key]['error_tag']='Drop frames'
                video_info[key]['harp_time_stamps_corrected'] = triggers.index.values[current_frames[1].index]
            elif num_frames > trigger_length:
                video_info[key]['error_tag']='More frames than triggers'
            else:
                video_info[key]['error_tag']='OK'
    return video_info
#video_info=correct_drop_frames(harp_folder=r'Z:\ephys_rig_behavior_transfer\323_EPHYS3\717377\behavior_717377_2024-04-12_10-04-45\behavior\raw.harp',video_folder=r'Z:\ephys_rig_behavior_transfer\323_EPHYS3\717377\behavior_717377_2024-04-12_10-04-45\behavior-videos')