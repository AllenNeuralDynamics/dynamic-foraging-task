import json
import logging


class generate_metadata:
    '''
    
    '''
    def __init__(self,json_file=None,Obj=None):
        if json_file is None and Obj is None:
            logging.info("Both json_file and Obj cannot be None")
            return
        pass

    def ephys_metadata(self):
        pass
    
    def behavior_metadata(self):
        pass

    def ophys_metadata(self):
        pass

    def high_speed_camera_metadata(self):
        pass

    def combined_metadata(self):
        pass