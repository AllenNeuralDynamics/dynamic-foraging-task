import random
import traceback
import math
import time
import sys
from sys import platform as PLATFORM
from datetime import datetime
import logging
import requests

import numpy as np
from itertools import accumulate
from serial.tools.list_ports import comports as list_comports
from PyQt5 import QtWidgets
from PyQt5 import QtCore

from foraging_gui.reward_schedules.uncoupled_block import UncoupledBlocks

if PLATFORM == 'win32':
    from newscale.usbxpress import USBXpressLib, USBXpressDevice
VID_NEWSCALE = 0x10c4
PID_NEWSCALE = 0xea61


class GenerateTrials():
    def __init__(self,win):
        self.win=win
        self.B_LeftLickIntervalPercent = None      # percentage of left lick intervals under 100ms
        self.B_RightLickIntervalPercent = None     # percentage of right lick intervals under 100ms
        self.B_CrossSideIntervalPercent = None     # percentage of cross side lick intervals under 100ms
        self.B_Bias = [0]  # lick bias
        self.B_RewardFamilies=self.win.RewardFamilies
        self.B_CurrentTrialN=-1 # trial number starts from 0; Update when trial starts
        self.B_LickPortN=2
        self.B_ANewBlock=np.array([1,1]).astype(int)
        self.B_RewardProHistory=np.array([[],[]]).astype(int)
        self.BlockLenHistory=[[],[]]
        self.B_BaitHistory=np.array([[],[]]).astype(bool)
        self.B_CurrentRewardProbRandomNumber=[]
        self.B_ITIHistory=[]
        self.B_DelayHistory=[]
        self.B_ResponseTimeHistory=[]
        self.B_CurrentRewardProb=np.empty((2,))
        self.B_AnimalCurrentResponse=[]
        self.B_AnimalResponseHistory=np.array([]).astype(float) # 0 lick left; 1 lick right; 2 no response
        self.B_Baited=np.array([False,False]).astype(bool)
        self.B_CurrentRewarded=np.array([[False],[False]]).astype(bool) # whether to receive reward
        self.B_RewardedHistory=np.array([[],[]]).astype(bool)
        self.B_Time=[]
        self.B_LeftLickTime=np.array([]).astype(float)
        self.B_RightLickTime=np.array([]).astype(float)
        self.B_TrialStartTime=np.array([]).astype(float)
        self.B_DelayStartTime=np.array([]).astype(float)
        self.B_DelayStartTimeComplete=[]
        self.B_TrialEndTime=np.array([]).astype(float)
        self.B_GoCueTime=np.array([]).astype(float)
        self.B_TrialStartTimeHarp=np.array([]).astype(float)
        self.B_DelayStartTimeHarp=np.array([]).astype(float)
        self.B_DelayStartTimeHarpComplete=[]
        self.B_TrialEndTimeHarp=np.array([]).astype(float)
        self.B_GoCueTimeBehaviorBoard=np.array([]).astype(float) # the time from the behavior board
        self.B_GoCueTimeSoundCard=np.array([]).astype(float) # the time from the soundcard
        self.B_DOPort2Output=np.array([]).astype(float)
        self.B_LeftRewardDeliveryTime=np.array([]).astype(float)
        self.B_RightRewardDeliveryTime=np.array([]).astype(float)
        self.B_LeftRewardDeliveryTimeHarp=np.array([]).astype(float)
        self.B_RightRewardDeliveryTimeHarp=np.array([]).astype(float)
        self.B_PhotometryRisingTimeHarp=np.array([]).astype(float)
        self.B_PhotometryFallingTimeHarp=np.array([]).astype(float)
        self.B_OptogeneticsTimeHarp=np.array([]).astype(float)
        self.B_ManualLeftWaterStartTime=np.array([]).astype(float)
        self.B_ManualRightWaterStartTime=np.array([]).astype(float)
        self.B_EarnedLeftWaterStartTime=np.array([]).astype(float)
        self.B_EarnedRightWaterStartTime=np.array([]).astype(float)
        self.B_AutoLeftWaterStartTime=np.array([]).astype(float)
        self.B_AutoRightWaterStartTime=np.array([]).astype(float)
        self.B_RewardOutcomeTime=np.array([]).astype(float)
        self.B_LaserOnTrial=[] # trials with laser on
        self.B_SimulationSession=[]
        self.B_LaserAmplitude=[]
        self.B_LaserDuration=[]
        self.B_SelectedCondition=[]
        self.B_AutoWaterTrial=np.array([[],[]]).astype(bool) # to indicate if it is a trial with outo water.
        self.B_NewscalePositions=[]
        self.B_session_control_state=[]
        self.B_opto_error=[]
        self.NextWaveForm=1 # waveform stored for later use
        self.CurrentWaveForm=1 # the current waveform to trigger the optogenetics
        self.Start_Delay_LeftLicks=[]
        self.Start_Delay_RightLicks=[]
        self.Delay_GoCue_LeftLicks=[]
        self.Delay_GoCue_RightLicks=[]
        self.GoCue_NextStart_LeftLicks=[]
        self.GoCue_NextStart_RightLicks=[]
        self.GoCue_GoCue1_LeftLicks=[]
        self.GoCue_GoCue1_RightLicks=[]
        self.Start_GoCue_LeftLicks=[]
        self.Start_GoCue_RightLicks=[]
        self.Start_GoCue_DD=[]
        self.Start_Delay_DD=[]
        self.Delay_GoCue_DD=[]
        self.GoCue_GoCue1_DD=[]
        self.GoCue_NextStart_DD=[]
        self.B_StartType=[] # 1: normal trials with delay; 3: optogenetics trials without delay
        self.GeneFinish=1
        self.GetResponseFinish=1
        self.Obj={}
        # get all of the training parameters of the current trial
        self._GetTrainingParameters(self.win)

        # create timer to calculate lick intervals every 10 minutes
        #self.lick_interval_time = QtCore.QTimer(timeout=self.calculate_inter_lick_intervals, interval=600000)
        self.lick_interval_time = QtCore.QTimer(timeout=self.calculate_inter_lick_intervals, interval=100)

    def _GenerateATrial(self,Channel4):
        self.finish_select_par=0
        if self.win.UpdateParameters==1:
            # get all of the training parameters of the current trial
            self._GetTrainingParameters(self.win)
        # save all of the parameters in each trial
        self._SaveParameters()
        # get licks information. Starting from the second trial, and counting licks of the last completed trial
        if self.B_CurrentTrialN>=1: 
            self._LickSta([self.B_CurrentTrialN-1])
        # to decide if it's an auto water trial. will give water in _GetAnimalResponse
        self._CheckAutoWater()
        
        # --- Handle reward schedule ---
        if self.TP_Task in ['Coupled Baiting','Coupled Without Baiting','RewardN']:
            # -- Use the old logic --
            # check block transition and set self.B_ANewBlock
            self._check_coupled_block_transition()
            if any(self.B_ANewBlock==1):
                # assign the next block's reward prob to self.B_CurrentRewardProb 
                self._generate_next_coupled_block()
        elif self.TP_Task in ['Uncoupled Baiting','Uncoupled Without Baiting']:
            # -- Use Han's standalone class --
            if self.B_CurrentTrialN == -1 or \
                not hasattr(self, 'uncoupled_blocks'): # Or the user start uncoupled in the midde of the session
                # Get uncoupled task settings
                self.RewardProbPoolUncoupled = self._get_uncoupled_reward_prob_pool()
                
                # Initialize the UncoupledBlocks object and generate the first trial
                self.uncoupled_blocks = UncoupledBlocks(                 
                    rwd_prob_array=self.RewardProbPoolUncoupled,
                    block_min=int(self.TP_BlockMin), 
                    block_max=int(self.TP_BlockMax),
                    persev_add=True,  # Hard-coded to True for now
                    perseverative_limit=4, # Hard-coded to 4 for now
                    max_block_tally=3, # Hard-coded to 3 for now
                )
                _, msg_uncoupled_block = self.uncoupled_blocks.next_trial()
            else:
                # Add animal's last choice and generate the next trial
                self.uncoupled_blocks.add_choice(
                    ['L', 'R', 'ignored'][int(self.B_AnimalResponseHistory[-1])]
                )
                _, msg_uncoupled_block = self.uncoupled_blocks.next_trial()
            
            # Extract parameters from the UncoupledBlocks object
            for i, side in enumerate(['L', 'R']):
                # Update self.B_CurrentRewardProb from trial_rwd_prob
                self.B_CurrentRewardProb[i] = self.uncoupled_blocks.trial_rwd_prob[side][-1]
                
                # Update self.BlockLenHistory from diff(block_ends)
                # Note we don't need override_block_len here since all
                # overrides are handled by the UncoupledBlocks object
                self.BlockLenHistory[i] = list(np.diff(
                    [0] + self.uncoupled_blocks.block_ends[side]
                ))
                
            # Show msg
            self.win.WarningLabel_uncoupled_task.setText(msg_uncoupled_block)
            
        # Append the (updated) current reward probability to the history 
        self.B_RewardProHistory=np.append(
            self.B_RewardProHistory,
            self.B_CurrentRewardProb.reshape(self.B_LickPortN,1),
            axis=1)
        
        # --- Generate other parameters such as ITI, delay, and response time ---
        self._generate_next_trial_other_paras()
        
        # check if bait is permitted at the current trial
        self._CheckBaitPermitted()
        self.finish_select_par=1
        # get basic information
        if self.B_CurrentTrialN>=0:
            self._GetBasic()
        # Show session/trial related information
        if self.win.Start.isChecked():
            self._ShowInformation()
        # to decide if we should stop the session
        self._CheckStop()
        # optogenetics section
        self._PerformOptogenetics(Channel4)
        # check warm up for the next trial
        self._CheckWarmUp()
        # finish to generate the next trial
        self.GeneFinish=1
    def _PerformOptogenetics(self,Channel4):
        '''Optogenetics section to generate optogenetics parameters and send waveform to Bonsai'''
        control_trial=0
        self.opto_error_tag=0
        try:
            if self.TP_OptogeneticsB=='on': # optogenetics is turned on
                # select the current optogenetics condition
                self._SelectOptogeneticsCondition()
                # session control is regarded as off when the optogenetics is turned off
                self.B_session_control_state.append(self.session_control_state)
                if self.SelctedCondition!=0: 
                    self.LaserOn=1
                    self.B_LaserOnTrial.append(self.LaserOn) 
                    # generate the optogenetics waveform of the next trial
                    self._GetLaserWaveForm()
                    self.B_SelectedCondition.append(self.SelctedCondition)
                else:
                    # this is the control trial
                    control_trial=1
            else:
                # optogenetics is turned off
                control_trial=1
                self.B_session_control_state.append(0)
            self.B_opto_error.append(self.opto_error_tag)
        except Exception as e:
            # optogenetics is turned off
            control_trial=1
            self.B_opto_error.append(1)
            self.B_session_control_state.append(0)
            # Catch the exception and print error information
            logging.error(str(e))
        if control_trial==1:
            self.LaserOn=0
            self.B_LaserOnTrial.append(self.LaserOn)
            self.B_LaserAmplitude.append([0,0])
            self.B_LaserDuration.append(0)
            self.B_SelectedCondition.append(0)
            self.CurrentLaserAmplitude=[0,0]

    def _CheckSessionControl(self):
        '''Check if the session control is on'''
        if self.TP_SessionWideControl=='on':
            session_control_block_length=float(self.TP_MaxTrial)*float(self.TP_FractionOfSession)
            if self.TP_SessionStartWith=='on':
                initial_state=1
            elif self.TP_SessionStartWith=='off':
                initial_state=0
            calculated_state=np.zeros(int(self.TP_MaxTrial))
            numbers=np.arange(int(self.TP_MaxTrial))
            numbers_floor=np.floor(numbers/session_control_block_length)
            # Find odd values: A value is odd if value % 2 != 0
            odd_values_mask = (numbers_floor % 2 != 0)
            even_values_mask = (numbers_floor % 2 == 0)
            calculated_state[even_values_mask]=initial_state
            calculated_state[odd_values_mask]=1-initial_state
            self.calculated_state=calculated_state
            # get the session_control_state of the current trial
            self.session_control_state=self.calculated_state[self.B_RewardProHistory.shape[1]-1]
        else:
            self.session_control_state=0
        if self.session_control_state==0:
            state='off'
        else:
            state='on'
        self.win.Opto_dialog.SessionControlWarning.setText('Session control state: '+state)
        self.win.Opto_dialog.SessionControlWarning.setStyleSheet(self.win.default_warning_color)    

    def _get_uncoupled_reward_prob_pool(self):
        # Get reward prob pool from the input string (e.g., ["0.1", "0.5", "0.9"])
        input_string = self.win.UncoupledReward.text()
        # remove any square brackets and spaces from the string
        input_string = input_string.replace('[','').replace(']','').replace(',', ' ')
        # split the remaining string into a list of individual numbers
        num_list = input_string.split()
        # convert each number in the list to a float
        num_list = [float(num) for num in num_list]
        # return a numpy array from the list of numbers
        return np.array(num_list)

    def _CheckWarmUp(self):
        '''Check if we should turn on warm up'''
        if self.win.warmup.currentText()=='off':
            return
        warmup=self._get_warmup_state()
        if warmup==0 and self.TP_warmup=='on':
            # set warm up to off
            index=self.win.warmup.findText('off')
            self.win.warmup.setCurrentIndex(index)
            self.win._warmup()
            self.win.keyPressEvent()
            self.win.NextBlock.setChecked(True)
            self.win._NextBlock()
            self.win.WarmupWarning.setText('Warm up is turned off')

    def _get_warmup_state(self):
        '''calculate the metrics related to the warm up and decide if we should turn on the warm up'''
        TP_warm_windowsize=int(self.TP_warm_windowsize)
        B_AnimalResponseHistory_window=self.B_AnimalResponseHistory[-TP_warm_windowsize:]
        finish_trial=self.B_AnimalResponseHistory.shape[0] # the warmup is only turned on at the beginning of the session, thus the number of finished trials is equal to the number of trials with warmup on
        left_choices = np.count_nonzero(B_AnimalResponseHistory_window == 0)
        right_choices = np.count_nonzero(B_AnimalResponseHistory_window == 1)
        no_responses = np.count_nonzero(B_AnimalResponseHistory_window == 2)
        if left_choices+right_choices+no_responses==0:
            finish_ratio=0
        else:
            finish_ratio=(left_choices+right_choices)/(left_choices+right_choices+no_responses)
        if left_choices+right_choices==0:
            choice_ratio=0
        else:
            choice_ratio=right_choices/(left_choices+right_choices)
        if finish_trial>=float(self.TP_warm_min_trial) and finish_ratio>=float(self.TP_warm_min_finish_ratio) and abs(choice_ratio-0.5)<=float(self.TP_warm_max_choice_ratio_bias):
            # turn off the warm up
            warmup=0
        else:
            # turn on the warm up
            warmup=1
        # show current metrics of the warm up
        self.win.WarmupWarning.setText('Finish trial: '+str(round(finish_trial,2))+ '; Finish ratio: '+str(round(finish_ratio,2))+'; Choice ratio bias: '+str(round(abs(choice_ratio-0.5),2)))
        self.win.WarmupWarning.setStyleSheet(self.win.default_warning_color)
        return warmup
        
    def _CheckBaitPermitted(self):
        '''Check if bait is permitted of the current trial'''
        #For task rewardN, if this is the "initial N trials" of the active side, no bait will be be given.
        if self.TP_Task=='RewardN':
            # get the maximum consecutive selection of the active side of the current block
            MaxCLen=self._GetMaximumConSelection()
            if MaxCLen>=float(self.TP_InitiallyInactiveN):
                self.BaitPermitted=True
            else:
                self.BaitPermitted=False
        else:
            self.BaitPermitted=True
        if self.BaitPermitted==False:
            self.win.WarningLabelRewardN.setText('The active side has no reward due to consecutive \nselections('+str(MaxCLen)+')<'+self.TP_InitiallyInactiveN)
            self.win.WarningLabelRewardN.setStyleSheet(self.win.default_warning_color)
        else:
            self.win.WarningLabelRewardN.setText('')
            self.win.WarningLabelRewardN.setStyleSheet("color: gray;")

    def _GetMaximumConSelection(self):
        '''get the maximum consecutive selection of the active side of the current block'''
        B_RewardProHistory=self.B_RewardProHistory[:,range(len(self.B_AnimalResponseHistory))].copy()
        if B_RewardProHistory.shape[1]==0:
            return 0
        # get the block length and index of the current trial
        index=[[],[]]
        for i in range(B_RewardProHistory.shape[0]): 
            length,indexN=self._consecutive_length(B_RewardProHistory[i], B_RewardProHistory[i][-1])
            self.BS_CurrentBlockTrialN[i]=length[-1]
            index[i]=indexN[-1]
        # get the active side
        max_index = np.argmax(B_RewardProHistory[:,-1])
        # get the consecutive choice of the active side
        length,indexN=self._consecutive_length(self.B_AnimalResponseHistory[index[0][0]:index[0][1]+1],max_index)
        # reset to 0 during the first trial of block transition
        if self.B_RewardProHistory[0,-1]!=self.B_RewardProHistory[0,-2] or self.B_RewardProHistory[1,-1]!=self.B_RewardProHistory[1,-2]:
            return 0
        # Get the maximum number of consecutive selections for the active side
        if len(length)==0:
            return 0
        else:
            return np.max(length)

    def _generate_next_coupled_block(self):
        '''Generate the next block reward probability and block length (coupled task only)'''
        # determine the reward probability of the next trial based on tasks
        self.RewardPairs=self.B_RewardFamilies[int(self.TP_RewardFamily)-1][:int(self.TP_RewardPairsN)]
        self.RewardProb=np.array(self.RewardPairs)/np.expand_dims(np.sum(self.RewardPairs,axis=1),axis=1)*float(self.TP_BaseRewardSum)
        # get the reward probabilities pool
        RewardProbPool=np.append(self.RewardProb,np.fliplr(self.RewardProb),axis=0)
        if self.B_RewardProHistory.size!=0:
            # exclude the previous reward probabilities
            RewardProbPool=RewardProbPool[np.any(RewardProbPool!=self.B_RewardProHistory[:,-1],axis=1)]
            # exclude blocks with the same identity/order (forced change of block identity (L->R; R->L))
            if self.B_RewardProHistory[0,-1]!=self.B_RewardProHistory[1,-1]:
                RewardProbPool=RewardProbPool[(RewardProbPool[:,0]>RewardProbPool[:,1])!=(self.B_RewardProHistory[0,-1]>self.B_RewardProHistory[1,-1])]
        # Remove duplicates
        RewardProbPool = np.unique(RewardProbPool, axis=0)
        # get the reward probabilities of the current block
        self.B_CurrentRewardProb=RewardProbPool[random.choice(range(np.shape(RewardProbPool)[0]))]
        # randomly draw a block length between Min and Max
        if self.TP_Randomness=='Exponential':
            self.BlockLen = np.array(int(np.random.exponential(float(self.TP_BlockBeta),1)+float(self.TP_BlockMin)))
        elif self.TP_Randomness=='Even':
            self.BlockLen=  np.array(np.random.randint(float(self.TP_BlockMin), float(self.TP_BlockMax)+1))
        if self.BlockLen>float(self.TP_BlockMax):
            self.BlockLen=int(self.TP_BlockMax)
        for i in range(len(self.B_ANewBlock)):
            self.BlockLenHistory[i].append(self.BlockLen)
        self.B_ANewBlock=np.array([0,0])
            

    def _generate_next_trial_other_paras(self):
        # get the ITI time and delay time
        if self.TP_Randomness=='Exponential':
            self.CurrentITI = float(np.random.exponential(float(self.TP_ITIBeta),1)+float(self.TP_ITIMin))
        elif self.TP_Randomness=='Even':
            self.CurrentITI = random.uniform(float(self.TP_ITIMin),float(self.TP_ITIMax))
        if self.CurrentITI>float(self.TP_ITIMax):
            self.CurrentITI=float(self.TP_ITIMax)
        if self.TP_Randomness=='Exponential':
            self.CurrentDelay = float(np.random.exponential(float(self.TP_DelayBeta),1)+float(self.TP_DelayMin))
        elif self.TP_Randomness=='Even':
            self.CurrentDelay=random.uniform(float(self.TP_DelayMin),float(self.TP_DelayMax))
        if self.CurrentDelay>float(self.TP_DelayMax):
            self.CurrentDelay=float(self.TP_DelayMax)
        # extremely important. Currently, the shaders timer does not allow delay close to zero. 
        if self.CurrentITI<0.05:
            self.CurrentITI=0.05
        if self.CurrentDelay<0.05:
            self.CurrentDelay=0.05
        self.B_ITIHistory.append(self.CurrentITI)
        self.B_DelayHistory.append(self.CurrentDelay)
        self.B_ResponseTimeHistory.append(float(self.TP_ResponseTime))

    def _check_coupled_block_transition(self):
        '''Check if we should perform a block change for the next trial. 
        If you change the block length parameter, it only takes effect 
        after the current block is completed'''
        # Check advanced block swith
        # and set self.AdvancedBlockSwitchPermitted
        self._check_advanced_block_switch()
        
        # --- Force transition to the next block when NextBlock button is clicked ---
        if self.TP_NextBlock:
            self.B_ANewBlock[:]=1
            self.win.NextBlock.setChecked(False)
            self.win.NextBlock.setStyleSheet("background-color : none")
            self._override_block_len([0,1])
            return  # Early return here
            
        # --- Decide block transition based on this block length ---
        # self.BlockLenHistory is initialized as [[],[]] in __init__
        # So the first block is also generated here
        for i in range(len(self.B_ANewBlock)):
            if self.B_CurrentTrialN+1>=sum(self.BlockLenHistory[i]):
                self.B_ANewBlock[i]=1
                
        # --- Reject block transition decision based on 
        # minimum reward requirement or advanced block switch ---
        
        # Get the number of reward trials in the current block
        if self.B_CurrentTrialN>=0:
            self._get_current_block_reward(1,CountAutoWater=1,UpdateBlockLen=1)
        else:
            # If this is the first trial of the block, set self.AllRewardThisBlock to -1
            self.AllRewardThisBlock=-1
            self.BS_RewardedTrialN_CurrentBlock=[0,0]
            
        # Don't switch if the minimum reward requirement is not met 
        # or advanced block switch is not permitted
        # For the coupled task, hold block switch on both sides       
        if np.all(self.B_ANewBlock==1) and self.AllRewardThisBlock!=-1:
            if self.AllRewardThisBlock < float(self.TP_BlockMinReward) \
                or self.AdvancedBlockSwitchPermitted==0:
                self.B_ANewBlock=np.zeros_like(self.B_ANewBlock)
                self._override_block_len(range(len(self.B_ANewBlock)))
                        
    def _override_block_len(self,ind):
        '''Get the block length and update the block length history'''
        block_len_history = self.BlockLenHistory.copy()
        for i in ind:
            block_len_history[i]=[]
            start_val = self.B_RewardProHistory[i][0]
            count = 0
            for j in range(len(self.B_RewardProHistory[i])):
                if self.B_RewardProHistory[i][j] == start_val:
                    count += 1
                else:
                    block_len_history[i].append(count)
                    start_val = self.B_RewardProHistory[i][j]
                    count = 1
            # Append the count of the last block to block_len_history
            block_len_history[i].append(count)
        self.BlockLenHistory=block_len_history     
        
    def _check_advanced_block_switch(self):
        '''Check if we can switch to a different block'''
        if self.TP_AdvancedBlockAuto=='off':
            self.AdvancedBlockSwitchPermitted=1
            return
        kernel_size=int(self.TP_RunLength)
        if self.B_CurrentTrialN>kernel_size:
            # get the current block length
            self._GetCurrentBlockLen()
            # calculate the choice fraction of current block
            # get the choice fraction
            ChoiceFraction=self._GetChoiceFrac()
            CurrentEffectiveBlockLen=min(self.CurrentBlockLen)# for decoupled task, the block length is different
            if CurrentEffectiveBlockLen>len(ChoiceFraction):
                self.AdvancedBlockSwitchPermitted=1
                return
            ChoiceFractionCurrentBlock=ChoiceFraction[-CurrentEffectiveBlockLen:]
            # decide the current high rewrad side and threshold(for 2 reward probability)
            Delta=abs((self.B_CurrentRewardProb[0]-self.B_CurrentRewardProb[1])*float(self.TP_SwitchThr))
            if self.B_CurrentRewardProb[0]>self.B_CurrentRewardProb[1]:
                # it's the left side with high reward probability
                # decide the threshold 
                Threshold=[0,self.B_CurrentRewardProb[0]-Delta]
            elif self.B_CurrentRewardProb[0]<self.B_CurrentRewardProb[1]:
                # it's the right side with high reward probability
                # decide the threshold 
                Threshold=[self.B_CurrentRewardProb[0]+Delta,1]
            else:
                self.AdvancedBlockSwitchPermitted=1
                return
            # Get consecutive points that exceed a threshold
            OkPoints=np.zeros_like(ChoiceFractionCurrentBlock)
            Ind=np.where(np.logical_and(ChoiceFractionCurrentBlock>=Threshold[0], ChoiceFractionCurrentBlock<=Threshold[1]))
            OkPoints[Ind]=1
            consecutive_lengths,consecutive_indices=self._consecutive_length(OkPoints,1)
            if consecutive_lengths.size==0:
                self.AdvancedBlockSwitchPermitted=0
                return
            # determine if we can switch
            if self.TP_PointsInARow=='':
                self.AdvancedBlockSwitchPermitted=1
                return
            if self.TP_AdvancedBlockAuto=='now':
                # the courrent condition is qualified
                if len(OkPoints) in consecutive_indices[consecutive_lengths>float(self.TP_PointsInARow)][:,1]+1:
                    self.AdvancedBlockSwitchPermitted=1
                else:
                    self.AdvancedBlockSwitchPermitted=0
            elif self.TP_AdvancedBlockAuto=='once':
                # it happens before
                if np.any(consecutive_lengths>float(self.TP_PointsInARow)):
                    self.AdvancedBlockSwitchPermitted=1
                else:
                    self.AdvancedBlockSwitchPermitted=0
            else:
                self.AdvancedBlockSwitchPermitted=1
        else:
            self.AdvancedBlockSwitchPermitted=1

    def _consecutive_length(self,arr, target):
        '''Get the consecutive length and index of a target'''
        consecutive_lengths = []
        consecutive_indices = []
        count = 0
        start_index = None

        for i, num in enumerate(arr):
            if num == target:
                if count == 0:
                    start_index = i
                count += 1
            else:
                if count > 0:
                    consecutive_lengths.append(count)
                    consecutive_indices.append((start_index, i - 1))
                count = 0
                start_index = None

        if count > 0:
            consecutive_lengths.append(count)
            consecutive_indices.append((start_index, len(arr) - 1))
        else:
            if start_index is not None:
                consecutive_lengths.append(count + 1)
                consecutive_indices.append((start_index, start_index))
        return np.array(consecutive_lengths), np.array(consecutive_indices)
    
    def _GetCurrentBlockLen(self):
        '''Get the trial length of the current block'''
        self.CurrentBlockLen=[]
        for i in range(len(self.B_RewardProHistory)):
            if np.all(self.B_RewardProHistory[i]==self.B_CurrentRewardProb[i]):
                self.CurrentBlockLen.append(self.B_RewardProHistory.shape[1])
            else:
                self.CurrentBlockLen.append(self.B_RewardProHistory.shape[1]-1-np.max(np.where(self.B_RewardProHistory[i]!=self.B_CurrentRewardProb[i])))
    
    def _GetChoiceFrac(self):
        '''Get the fraction of right choices with running average'''
        kernel_size=int(self.TP_RunLength)
        ResponseHistoryT=self.B_AnimalResponseHistory.copy()
        ResponseHistoryT[ResponseHistoryT==2]=np.nan
        ResponseHistoryF=ResponseHistoryT.copy()
        # running average of response fraction
        for i in range(len(self.B_AnimalResponseHistory)):
            if i>=kernel_size-1:
                if all(np.isnan(ResponseHistoryT[i+1-kernel_size:i+1])):
                    ResponseHistoryF[i+1-kernel_size]=np.nan
                else:
                    ResponseHistoryF[i+1-kernel_size]=np.nanmean(ResponseHistoryT[i+1-kernel_size:i+1])
        ChoiceFraction=ResponseHistoryF[:-kernel_size+1]
        return ChoiceFraction

    def _get_current_block_reward(self,NewTrialRewardOrder,CountAutoWater=0,UpdateBlockLen=0):
        '''Get the reward length of the current block'''
        self.BS_CurrentBlockTrialN=[[],[]]
        index=[[],[]]
        self.BS_CurrentBlockLen=[self.BlockLenHistory[0][-1], self.BlockLenHistory[1][-1]]
        if self.finish_select_par==1:
            if NewTrialRewardOrder==1:
            # show current finished trial
                B_RewardProHistory=self.B_RewardProHistory[:,:-1].copy() 
            else:
            # show next trial
                B_RewardProHistory=self.B_RewardProHistory.copy() 
        elif self.finish_select_par==0:
            if NewTrialRewardOrder==1:
                # show current finished trial
                B_RewardProHistory=self.B_RewardProHistory.copy() 
            else:
                logging.error('no next trial parameters generated')

        B_RewardedHistory=self.B_RewardedHistory.copy()
        if CountAutoWater==1:
            if self.TP_IncludeAutoReward=='yes':
                # auto reward is considered as reward no matter the animal's choice. B_RewardedHistory and B_AutoWaterTrial cannot both be True
                Ind=range(len(self.B_RewardedHistory[0]))
                for i in range(len(self.B_RewardedHistory)):
                    B_RewardedHistory[i]=np.logical_or(self.B_RewardedHistory[i],self.B_AutoWaterTrial[i][Ind])
            elif self.TP_IncludeAutoReward=='no':
                # auto reward is not considered as reward (auto reward is considered reward only when the animal makes a choice). Reward is determined by the animal's response history and the bait history
                Ind=range(len(self.B_RewardedHistory[0]))
                for i in range(len(self.B_RewardedHistory)): 
                    B_RewardedHistory[i]=np.logical_and(self.B_AnimalResponseHistory[Ind]==i,self.B_BaitHistory[i][Ind])
        # get the block length and index of the current trial
        for i in range(B_RewardProHistory.shape[0]) : 
            length,indexN=self._consecutive_length(B_RewardProHistory[i], B_RewardProHistory[i][-1])
            self.BS_CurrentBlockTrialN[i]=length[-1]
            index[i]=indexN[-1]
        self.BS_RewardedTrialN_CurrentLeftBlock=np.sum(B_RewardedHistory[0][index[0][0]:index[0][1]+1]==True)
        self.BS_RewardedTrialN_CurrentRightBlock=np.sum(B_RewardedHistory[1][index[1][0]:index[1][1]+1]==True)
        self.AllRewardThisBlock=self.BS_RewardedTrialN_CurrentLeftBlock+self.BS_RewardedTrialN_CurrentRightBlock
        self.BS_RewardedTrialN_CurrentBlock=[self.BS_RewardedTrialN_CurrentLeftBlock,self.BS_RewardedTrialN_CurrentRightBlock]
        # for visualization
        self.BS_CurrentBlockTrialNV=self.BS_CurrentBlockTrialN.copy()
        self.BS_CurrentBlockLenV=self.BS_CurrentBlockLen.copy()
        # update block length history
        for i in range(len(self.BS_CurrentBlockLen)):
            if self.BS_CurrentBlockTrialN[i]>self.BS_CurrentBlockLen[i]:
                self.BS_CurrentBlockLenV[i]=self.BS_CurrentBlockTrialNV[i]
                if UpdateBlockLen==1:
                    self._override_block_len([i])
                    self.BS_CurrentBlockLen[i]=self.BlockLenHistory[i][-1]

    def _GetBasic(self):
        '''Get basic session information'''
        if len(self.B_TrialEndTime)>=1:
            self.BS_CurrentRunningTime=self.B_TrialEndTime[-1]-self.B_TrialStartTime[0]# time interval between the recent trial end and first trial start
        else:
            self.BS_CurrentRunningTime=0
        self.BS_AllTrialN=np.shape(self.B_AnimalResponseHistory)[0]
        self.BS_FinisheTrialN=np.sum(self.B_AnimalResponseHistory!=2)
        if self.BS_AllTrialN==0:  
            self.BS_RespondedRate=np.nan
        else:
            self.BS_RespondedRate=self.BS_FinisheTrialN/self.BS_AllTrialN
        self.BS_RewardTrialN=np.sum(self.B_RewardedHistory==True)
        B_RewardedHistory=self.B_RewardedHistory.copy()
        # auto reward is considered as reward
        Ind=range(len(self.B_RewardedHistory[0]))
        for i in range(len(self.B_RewardedHistory)):
            B_RewardedHistory[i]=np.logical_or(self.B_RewardedHistory[i],self.B_AutoWaterTrial[i][Ind])
        self.BS_RewardN=np.sum(B_RewardedHistory[0]==True)+np.sum(B_RewardedHistory[1]==True)

        BS_auto_water_left,BS_earned_reward_left,BS_AutoWater_N_left,BS_EarnedReward_N_left = self._process_values(self.Obj['TP_LeftValue_volume'], self.B_AutoWaterTrial[0], self.Obj['TP_Multiplier'], B_RewardedHistory[0])
        BS_auto_water_right,BS_earned_reward_right,BS_AutoWater_N_right,BS_EarnedReward_N_right = self._process_values(self.Obj['TP_RightValue_volume'], self.B_AutoWaterTrial[1], self.Obj['TP_Multiplier'], B_RewardedHistory[1])
        self.BS_auto_water=[BS_auto_water_left,BS_auto_water_right]
        self.BS_earned_reward=[BS_earned_reward_left,BS_earned_reward_right]
        self.BS_AutoWater_N=[BS_AutoWater_N_left,BS_AutoWater_N_right]
        self.BS_EarnedReward_N=[BS_EarnedReward_N_left,BS_EarnedReward_N_right]

        self.BS_TotalReward=BS_earned_reward_left+BS_earned_reward_right+BS_auto_water_left+BS_auto_water_right
        self.BS_LeftRewardTrialN=np.sum(self.B_RewardedHistory[0]==True)
        self.BS_RightRewardTrialN=np.sum(self.B_RewardedHistory[1]==True)
        self.BS_LeftChoiceN=np.sum(self.B_AnimalResponseHistory==0)
        self.BS_RightChoiceN=np.sum(self.B_AnimalResponseHistory==1)
        self.BS_OverallRewardRate=self.BS_RewardTrialN/(self.B_CurrentTrialN+1)
        if self.BS_LeftChoiceN==0:
            self.BS_LeftChoiceRewardRate=np.nan
        else:
            self.BS_LeftChoiceRewardRate=self.BS_LeftRewardTrialN/self.BS_LeftChoiceN
        if self.BS_RightChoiceN==0:
            self.BS_RightChoiceRewardRate=np.nan
        else:
            self.BS_RightChoiceRewardRate=self.BS_RightRewardTrialN/self.BS_RightChoiceN
        # current trial numbers in the current block; BS_CurrentBlockTrialN
        if self.win.NewTrialRewardOrder==1:
            # show current finished trial
            self._get_current_block_reward(1)
        else:
            # show next trial
            self._get_current_block_reward(0)
        # update suggested reward
        self.win._UpdateSuggestedWater()
        # foraging efficiency
        Len=np.shape(self.B_RewardedHistory)[1]
        if Len>0:
            reward_rate=np.sum(self.B_RewardedHistory)/Len
            p_Ls=self.B_RewardProHistory[0][:Len]
            p_Rs=self.B_RewardProHistory[1][:Len]
            random_number_L= np.concatenate(self.B_CurrentRewardProbRandomNumber,axis=0)[0::2][:Len]
            random_number_R= np.concatenate(self.B_CurrentRewardProbRandomNumber,axis=0)[1::2][:Len]
            if (self.TP_Task in ['Coupled Baiting','Uncoupled Baiting']):
                self.B_for_eff_optimal, self.B_for_eff_optimal_random_seed=self.foraging_eff(reward_rate,p_Ls,p_Rs,random_number_L,random_number_R)
            elif (self.TP_Task in ['Coupled Without Baiting','Uncoupled Without Baiting']):
                self.B_for_eff_optimal, self.B_for_eff_optimal_random_seed=self.foraging_eff_no_baiting(reward_rate,p_Ls,p_Rs,random_number_L,random_number_R)
            else:
                self.B_for_eff_optimal=np.nan
                self.B_for_eff_optimal_random_seed=np.nan
            '''Some complex calculations can be separated from _GenerateATrial using different threads'''
    
    def _process_values(self,values, auto_water_trial, multiplier_values, rewarded_history):
        BS_AutoWater=0
        BS_EarnedReward=0
        BS_AutoWater_N=0
        BS_EarnedReward_N=0
        for i, s in enumerate(values[:len(rewarded_history)]):
            try:
                if auto_water_trial[i] == 1 and rewarded_history[i] == 1:
                    BS_AutoWater+=float(s) * float(multiplier_values[i])
                    BS_AutoWater_N+=1
                elif auto_water_trial[i] == 0 and rewarded_history[i] == 1:
                    BS_EarnedReward+=float(s)
                    BS_EarnedReward_N+=1
            except ValueError as e:
                logging.error(str(e))
        return BS_AutoWater,BS_EarnedReward,BS_AutoWater_N,BS_EarnedReward_N

    def foraging_eff_no_baiting(self,reward_rate, p_Ls, p_Rs, random_number_L=None, random_number_R=None):  # Calculate foraging efficiency (only for 2lp)
        '''Calculating the foraging efficiency of no baiting tasks (Code is from Han)'''    
        # --- Optimal-aver (use optimal expectation as 100% efficiency) ---
        for_eff_optimal = reward_rate / np.nanmean(np.max([p_Ls, p_Rs], axis=0))
        
        if random_number_L is None:
            return for_eff_optimal, np.nan
            
        # --- Optimal-actual (uses the actual random numbers by simulation)
        reward_refills = np.vstack([p_Ls >= random_number_L, p_Rs >= random_number_R])
        optimal_choices = np.argmax([p_Ls, p_Rs], axis=0)  # Greedy choice, assuming the agent knows the groundtruth
        optimal_rewards = reward_refills[0][optimal_choices==0].sum() + reward_refills[1][optimal_choices==1].sum()
        for_eff_optimal_random_seed = reward_rate / (optimal_rewards / len(optimal_choices))
        
        return for_eff_optimal, for_eff_optimal_random_seed

    def foraging_eff(self,reward_rate, p_Ls, p_Rs, random_number_L=None, random_number_R=None):  # Calculate foraging efficiency (only for 2lp)
        '''Calculating the foraging efficiency of baiting tasks (Code is from Han)'''        
        # --- Optimal-aver (use optimal expectation as 100% efficiency) ---
        p_stars = np.zeros_like(p_Ls)
        for i, (p_L, p_R) in enumerate(zip(p_Ls, p_Rs)):   # Sum over all ps 
            p_max = np.max([p_L, p_R])
            p_min = np.min([p_L, p_R])
            if p_min == 0 or p_max >= 1:
                p_stars[i] = p_max
            else:
                m_star = np.floor(np.log(1-p_max)/np.log(1-p_min))
                p_stars[i] = p_max + (1-(1-p_min)**(m_star + 1)-p_max**2)/(m_star+1)

        for_eff_optimal = reward_rate / np.nanmean(p_stars)
        
        if random_number_L is None:
            return for_eff_optimal, np.nan
            
        # --- Optimal-actual (uses the actual random numbers by simulation)
        block_trans = np.where(np.diff(np.hstack([np.inf, p_Ls, np.inf])))[0].tolist()
        reward_refills = [p_Ls >= random_number_L, p_Rs >= random_number_R]
        reward_optimal_random_seed = 0
        
        # Generate optimal choice pattern
        for b_start, b_end in zip(block_trans[:-1], block_trans[1:]):
            p_max = np.max([p_Ls[b_start], p_Rs[b_start]])
            p_min = np.min([p_Ls[b_start], p_Rs[b_start]])
            side_max = np.argmax([p_Ls[b_start], p_Rs[b_start]])
            
            # Get optimal choice pattern and expected optimal rate
            if p_min == 0 or p_max >= 1:
                this_choice = np.array([1] * (b_end-b_start))  # Greedy is obviously optimal
            else:
                m_star = np.floor(np.log(1-p_max)/np.log(1-p_min))
                this_choice = np.array((([1]*int(m_star)+[0]) * (1+int((b_end-b_start)/(m_star+1)))) [:b_end-b_start])
                
            # Do simulation, using optimal choice pattern and actual random numbers
            reward_refill = np.vstack([reward_refills[1 - side_max][b_start:b_end], 
                            reward_refills[side_max][b_start:b_end]]).astype(int)  # Max = 1, Min = 0
            reward_remain = [0,0]
            for t in range(b_end - b_start):
                reward_available = reward_remain | reward_refill[:, t]
                reward_optimal_random_seed += reward_available[this_choice[t]]
                reward_remain = reward_available.copy()
                reward_remain[this_choice[t]] = 0
            
            if reward_optimal_random_seed:                
                for_eff_optimal_random_seed = reward_rate / (reward_optimal_random_seed / len(p_Ls))
            else:
                for_eff_optimal_random_seed = np.nan
        
        return for_eff_optimal, for_eff_optimal_random_seed

    def _LickSta(self,Trials=None):
        '''Perform lick stats for the input trials'''
        if Trials==None: # could receive multiple trials
            Trials=self.B_CurrentTrialN-1
        # combine all of the left and right licks
        self.AllLicksInd=np.concatenate((np.zeros(len(self.B_LeftLickTime)),np.ones(len(self.B_RightLickTime))))
        self.AllLicksTime=np.concatenate((self.B_LeftLickTime,self.B_RightLickTime))
        # get the sort index
        sort_index = np.argsort(self.AllLicksTime)
        # sort the lick times
        self.AllLicksTimeSorted = np.sort(self.AllLicksTime)
        self.AllLicksIndSorted=self.AllLicksInd[sort_index]
        LeftLicksInd=self.AllLicksIndSorted==0
        RightLicksInd=self.AllLicksIndSorted==1
        for i in Trials:
            # this only works when the current trial exceeds 2; the length of GoCue_NextStart_LeftLicks is one less than that of trial length
            if self.B_CurrentTrialN>=2:
                CurrentGoCue_NextStart=(self.B_GoCueTime[i-1],self.B_TrialStartTime[i])
                Ind_GoCue_NextStart=(self.AllLicksTimeSorted >= CurrentGoCue_NextStart[0]) &  (self.AllLicksTimeSorted < CurrentGoCue_NextStart[1])
                Ind_GoCue_NextStart_Left=Ind_GoCue_NextStart & LeftLicksInd
                Ind_GoCue_NextStart_Right=Ind_GoCue_NextStart & RightLicksInd
                self.GoCue_NextStart_LeftLicks.append(sum(Ind_GoCue_NextStart_Left))
                self.GoCue_NextStart_RightLicks.append(sum(Ind_GoCue_NextStart_Right))
                # double dipping
                GoCue_NextStart_DD=self._GetDoubleDipping(self.AllLicksIndSorted[Ind_GoCue_NextStart])
                self.GoCue_NextStart_DD.append(GoCue_NextStart_DD)
                self.DD_TrialsN_GoCue_NextStart=sum(np.array(self.GoCue_NextStart_DD)!=0)
                self.DDRate_GoCue_NextStart=self.DD_TrialsN_GoCue_NextStart/len(self.GoCue_NextStart_DD)
                # double dipping per finish trial
                Len=len(self.GoCue_NextStart_DD)
                RespondedTrial=np.where(self.B_AnimalResponseHistory[:Len]!=2)[0]
                if RespondedTrial.size>0:
                    self.DD_PerTrial_GoCue_NextStart=np.round(sum(np.array(self.GoCue_NextStart_DD)[RespondedTrial])/len(np.array(self.GoCue_NextStart_DD)[RespondedTrial]),2)
                else:
                    self.DD_PerTrial_GoCue_NextStart='nan'
            CurrentStart_GoCue=(self.B_TrialStartTime[i],self.B_GoCueTime[i])
            if self.B_DelayStartTime[i] in [None, -999]:
                CurrentStart_Delay=(self.B_TrialStartTime[i],self.B_GoCueTime[i]) # using the first delay start time
                CurrentDelay_GoCue=(self.B_GoCueTime[i],self.B_GoCueTime[i])
            else:
                CurrentStart_Delay=(self.B_TrialStartTime[i],self.B_DelayStartTime[i]) # using the first delay start time
                CurrentDelay_GoCue=(self.B_DelayStartTime[i],self.B_GoCueTime[i])
            CurrentGoCue_GoCue1=(self.B_GoCueTime[i],self.B_GoCueTime[i]+1)
            # licks in different intervals
            Ind_Start_GoCue=(self.AllLicksTimeSorted >= CurrentStart_GoCue[0]) &  (self.AllLicksTimeSorted < CurrentStart_GoCue[1])
            Ind_Start_Delay=(self.AllLicksTimeSorted >= CurrentStart_Delay[0]) &  (self.AllLicksTimeSorted < CurrentStart_Delay[1])
            Ind_Delay_GoCue=(self.AllLicksTimeSorted >= CurrentDelay_GoCue[0]) &  (self.AllLicksTimeSorted < CurrentDelay_GoCue[1])
            Ind_GoCue_GoCue1=(self.AllLicksTimeSorted >= CurrentGoCue_GoCue1[0]) &  (self.AllLicksTimeSorted < CurrentGoCue_GoCue1[1])
            Ind_Start_GoCue_Left=Ind_Start_GoCue & LeftLicksInd
            Ind_Start_GoCue_Right=Ind_Start_GoCue & RightLicksInd
            Ind_Start_Delay_Left=Ind_Start_Delay & LeftLicksInd # left lick in this interval
            Ind_Start_Delay_Right=Ind_Start_Delay & RightLicksInd # right lick in this interval
            Ind_Delay_GoCue_Left=Ind_Delay_GoCue & LeftLicksInd
            Ind_Delay_GoCue_Right=Ind_Delay_GoCue & RightLicksInd
            Ind_GoCue_GoCue1_Left=Ind_GoCue_GoCue1 & LeftLicksInd
            Ind_GoCue_GoCue1_Right=Ind_GoCue_GoCue1 & RightLicksInd
            # licks in different intervals
            self.Start_GoCue_LeftLicks.append(sum(Ind_Start_GoCue_Left))
            self.Start_GoCue_RightLicks.append(sum(Ind_Start_GoCue_Right))
            self.Start_Delay_LeftLicks.append(sum(Ind_Start_Delay_Left))
            self.Start_Delay_RightLicks.append(sum(Ind_Start_Delay_Right))
            self.Delay_GoCue_LeftLicks.append(sum(Ind_Delay_GoCue_Left))
            self.Delay_GoCue_RightLicks.append(sum(Ind_Delay_GoCue_Right))
            self.GoCue_GoCue1_LeftLicks.append(sum(Ind_GoCue_GoCue1_Left))
            self.GoCue_GoCue1_RightLicks.append(sum(Ind_GoCue_GoCue1_Right))
            # double dipping in different intervals
            Start_GoCue_DD=self._GetDoubleDipping(self.AllLicksIndSorted[Ind_Start_GoCue]) # double dipping numbers
            Start_Delay_DD=self._GetDoubleDipping(self.AllLicksIndSorted[Ind_Start_Delay])
            Delay_GoCue_DD=self._GetDoubleDipping(self.AllLicksIndSorted[Ind_Delay_GoCue])
            GoCue_GoCue1_DD=self._GetDoubleDipping(self.AllLicksIndSorted[Ind_GoCue_GoCue1])
            self.Start_GoCue_DD.append(Start_GoCue_DD)
            self.Start_Delay_DD.append(Start_Delay_DD)
            self.Delay_GoCue_DD.append(Delay_GoCue_DD)
            self.GoCue_GoCue1_DD.append(GoCue_GoCue1_DD)
        # fraction of early licking trials in different time interval
        self.EarlyLickingTrialsN_Start_Delay=sum(np.logical_or(np.array(self.Start_Delay_LeftLicks)!=0, np.array(self.Start_Delay_RightLicks)!=0))
        self.EarlyLickingTrialsN_Delay_GoCue=sum(np.logical_or(np.array(self.Delay_GoCue_LeftLicks)!=0, np.array(self.Delay_GoCue_RightLicks)!=0))
        self.EarlyLickingTrialsN_Start_GoCue=sum(np.logical_or(np.array(self.Start_GoCue_LeftLicks)!=0, np.array(self.Start_GoCue_RightLicks)!=0))
        self.EarlyLickingRate_Start_Delay=self.EarlyLickingTrialsN_Start_Delay/len(self.Start_Delay_LeftLicks)
        self.EarlyLickingRate_Delay_GoCue=self.EarlyLickingTrialsN_Delay_GoCue/len(self.Delay_GoCue_LeftLicks)
        self.EarlyLickingRate_Start_GoCue=self.EarlyLickingTrialsN_Start_GoCue/len(self.Start_GoCue_LeftLicks)
        # fraction of double dipping trials in different time interval
        self.DD_TrialsN_Start_Delay=sum(np.array(self.Start_Delay_DD)!=0)
        self.DD_TrialsN_Delay_GoCue=sum(np.array(self.Delay_GoCue_DD)!=0)
        self.DD_TrialsN_GoCue_GoCue1=sum(np.array(self.GoCue_GoCue1_DD)!=0)
        self.DD_TrialsN_Start_CoCue=sum(np.array(self.Start_GoCue_DD)!=0)

        self.DDRate_Start_Delay=self.DD_TrialsN_Start_Delay/len(self.Start_Delay_DD)
        self.DDRate_Delay_GoCue=self.DD_TrialsN_Delay_GoCue/len(self.Delay_GoCue_DD)
        self.DDRate_GoCue_GoCue1=self.DD_TrialsN_GoCue_GoCue1/len(self.GoCue_GoCue1_DD)
        self.DDRate_Start_CoCue=self.DD_TrialsN_Start_CoCue/len(self.Start_GoCue_DD)

        # double dipping per finish trial
        Len=len(self.Start_GoCue_DD)
        RespondedTrial=np.where(self.B_AnimalResponseHistory[:Len]!=2)[0]
        if RespondedTrial.size>0:
            self.DD_PerTrial_Start_GoCue=np.round(sum(np.array(self.Start_GoCue_DD)[RespondedTrial])/len(np.array(self.Start_GoCue_DD)[RespondedTrial]),2)
            self.DD_PerTrial_GoCue_GoCue1=np.round(sum(np.array(self.GoCue_GoCue1_DD)[RespondedTrial])/len(np.array(self.GoCue_GoCue1_DD)[RespondedTrial]),2)
        else:
            self.DD_PerTrial_Start_GoCue='nan'
            self.DD_PerTrial_GoCue_GoCue1='nan'
        # licks ration
        if sum(self.Start_GoCue_RightLicks)==0:
            self.Start_CoCue_LeftRightRatio=np.nan
        else:
            self.Start_CoCue_LeftRightRatio=np.array(sum(self.Start_GoCue_LeftLicks))/np.array(sum(self.Start_GoCue_RightLicks))

    def calculate_inter_lick_intervals(self):
        """
        Calculate and categorize lick intervals
        """

        right = self.B_RightLickTime
        left = self.B_LeftLickTime
        threshold = .1

        same_side_l = np.diff(left)
        same_side_r = np.diff(right)
        if len(right) > 0:
            # calculate left interval and fraction
            same_side_l_frac = np.mean(same_side_l <= threshold)
            logging.info(f'Percentage of left lick intervals under 100 ms is {same_side_l_frac * 100}%.')
            self.B_LeftLickIntervalPercent = same_side_l_frac * 100

        if len(left) > 0:
            # calculate right interval and fraction
            same_side_r_frac = np.mean(same_side_r <= threshold)
            logging.info(f'Percentage of right lick intervals under 100 ms is {same_side_r_frac * 100}%.')
            self.B_RightLickIntervalPercent = same_side_r_frac * 100

        if len(right) > 0 and len(left) > 0:
            # calculate same side lick interval and fraction for both right and left
            same_side_combined = np.concatenate([same_side_l, same_side_r])
            same_side_frac = np.mean(same_side_combined <= threshold)

            if same_side_frac >= threshold:
                self.win.same_side_lick_interval.setText(f'Percentage of same side lick intervals under 100 ms is '
                                                         f'over 10%: {same_side_frac * 100}%.')
            else:
                self.win.same_side_lick_interval.setText('')

            # calculate cross side interval and frac
            dummy_array = np.ones(right.shape)  # array used to assign lick direction
            # 2d arrays pairing each time with a 1 (right) or -1 (left)
            stacked_right = np.column_stack((dummy_array, right))
            stacked_left = np.column_stack((np.negative(dummy_array), left))
            # concatenate stacked_right and stacked_left then sort based on time element
            # e.g. [[-1, 10], [1, 15], [-1, 20], [1, 25]...]. Ones added to assign lick side to times
            merged_sorted = np.array(sorted(np.concatenate((stacked_right, stacked_left)),
                               key=lambda x: x[1]))

            diffs = np.diff(merged_sorted[:, 0])    # take difference of 1 (right) or -1 (left)
            # take difference of next index with previous at indices where directions are opposite
            cross_sides = np.array([merged_sorted[i + 1, 1] - merged_sorted[i, 1] for i in np.where(diffs != 0)])[0]
            cross_side_frac = np.mean(cross_sides <= threshold)
            logging.info(f'Percentage of cross side lick intervals under 100 ms is {cross_side_frac * 100}%.')
            self.B_CrossSideIntervalPercent = cross_side_frac * 100

            if cross_side_frac >= threshold:
                self.win.cross_side_lick_interval.setText(f'Percentage of cross side lick intervals under 100 ms is '
                                                          f'over 10%: {cross_side_frac * 100}%.')
            else:
                self.win.cross_side_lick_interval.setText('')

    def _GetDoubleDipping(self,LicksIndex):
        '''get the number of double dipping. e.g. 0 1 0 will result in 2 double dipping''' 
        DoubleDipping=np.sum(np.diff(LicksIndex)!=0)
        return DoubleDipping
    def _ForagingEfficiency(self):
        pass

    def _ShowInformation(self):
        '''Show session/trial related information in the information section'''
        # show reward pairs and current reward probability
        try:
            if (self.TP_Task in ['Coupled Baiting','Coupled Without Baiting','RewardN']):
                self.win.ShowRewardPairs.setText('Reward pairs:\n'
                                                + str(np.round(self.RewardProb,2)).replace('\n', ',')
                                                + '\n\n'
                                                + 'Current pair:\n'
                                                + str(np.round(
                                                    self.B_RewardProHistory[:,self.B_CurrentTrialN],2))) 
                if self.win.default_ui=='ForagingGUI.ui': 
                    self.win.ShowRewardPairs_2.setText(self.win.ShowRewardPairs.text())
            elif (self.TP_Task in ['Uncoupled Baiting','Uncoupled Without Baiting']):
                self.win.ShowRewardPairs.setText('Reward pairs:\n'
                                + str(np.round(self.RewardProbPoolUncoupled,2)).replace('\n', ',')
                                + '\n\n'
                                +'Current pair:\n'
                                + str(np.round(self.B_RewardProHistory[:,self.B_CurrentTrialN],2)))
                if self.win.default_ui=='ForagingGUI.ui': 
                    self.win.ShowRewardPairs_2.setText(self.win.ShowRewardPairs.text())
        except Exception as e:
            logging.error(str(e))
            
        # session start time
        SessionStartTime=self.win.SessionStartTime
        self.win.CurrentTime=datetime.now()
        self.win.Other_CurrentTime=str(self.win.CurrentTime)
        tdelta = self.win.CurrentTime - SessionStartTime
        self.win.Other_RunningTime=tdelta.seconds // 60
        SessionStartTimeHM = SessionStartTime.strftime('%H:%M')
        CurrentTimeHM = self.win.CurrentTime.strftime('%H:%M')
        
        if self.win.default_ui=='ForagingGUI.ui':
            # Task info
            self.win.info_task = (f'Session started: {SessionStartTimeHM}\n'
                                f'Current time: {CurrentTimeHM}\n'
                                f'Run time: {str(self.win.Other_RunningTime)} mins\n\n'
                                'Current left block: ' + (f'{self.BS_CurrentBlockTrialNV[0]}/{self.BS_CurrentBlockLenV[0]}' if self.B_CurrentTrialN>=0 else '') + '\n'
                                'Current right block: ' + (f'{self.BS_CurrentBlockTrialNV[1]}/{self.BS_CurrentBlockLenV[1]}' if self.B_CurrentTrialN>=0 else '')
                                )
            self.win.label_info_task.setText(self.win.info_task)
            # Performance info
            # 1. essential info
            # left side in the GUI
            if (self.TP_AutoReward  or int(self.TP_BlockMinReward)>0) and self.win.Start.isChecked():
                # show the next trial
                self.win.info_performance_essential_1 = f'Current trial: {self.B_CurrentTrialN + 2}\n'

            else:
                # show the current trial
                self.win.info_performance_essential_1 = f'Current trial: {self.B_CurrentTrialN + 1}\n'
            
            if self.B_CurrentTrialN >= 0:
                self.win.info_performance_essential_1 += (
                                    f'Responded trial: {self.BS_FinisheTrialN}/{self.BS_AllTrialN} ({self.BS_RespondedRate:.2f})\n'
                                    f'Reward Trial: {self.BS_RewardTrialN}/{self.BS_AllTrialN} ({self.BS_OverallRewardRate:.2f})\n'
                                    f'Earned Reward: {sum(self.BS_earned_reward) / 1000:.3f} mL\n'
                                    f'Water in session: {self.win.water_in_session if self.B_CurrentTrialN>=0 else 0:.3f} mL'   
                )
            self.win.label_info_performance_essential_1.setText(self.win.info_performance_essential_1)
            
            # right side in the GUI
            self.win.info_performance_essential_2 = (
                            'Foraging eff: ' + (f'{self.B_for_eff_optimal:.2f}' if self.B_CurrentTrialN>=2 else '') + '\n'
                            'Foraging eff (r.s.): ' + (f'{self.B_for_eff_optimal_random_seed:.2f}' if self.B_CurrentTrialN>=2 else '') + '\n\n'
            )
            if hasattr(self.win, 'B_Bias_R'):
                bias_side = 'left' if self.win.B_Bias_R <= 0 else 'right'
                self.win.info_performance_essential_2 += (
                    f'Bias: {self.win.B_Bias_R:.2f} ({bias_side})'
                )
            else:
                self.win.info_performance_essential_2 += (
                    'Bias: '
                )
            
            self.win.label_info_performance_essential_2.setText(self.win.info_performance_essential_2)

            # 2. other info
            self.win.info_performance_others = ''
            if self.B_CurrentTrialN >= 0:
                self.win.info_performance_others += (
                            'Left choice rewarded: ' + str(self.BS_LeftRewardTrialN) + '/' + str(self.BS_LeftChoiceN) + ' ('+str(np.round(self.BS_LeftChoiceRewardRate,2))+')' +'\n'
                            'Right choice rewarded: ' + str(self.BS_RightRewardTrialN) + '/' + str(self.BS_RightChoiceN) + ' ('+str(np.round(self.BS_RightChoiceRewardRate,2))+')' +'\n\n'
                )
                
            if self.B_CurrentTrialN >= 1:
                self.win.info_performance_others += (
                            'Early licking (EL)\n'
                            '  Frac of EL trial start_goCue: ' + str(self.EarlyLickingTrialsN_Start_GoCue) + '/' + str(len(self.Start_GoCue_LeftLicks)) + ' ('+str(np.round(self.EarlyLickingRate_Start_GoCue,2))+')' +'\n'
                            '  Frac of EL trial start_delay: ' + str(self.EarlyLickingTrialsN_Start_Delay) + '/' + str(len(self.Start_Delay_LeftLicks)) + ' ('+str(np.round(self.EarlyLickingRate_Start_Delay,2))+')' +'\n'
                            '  Frac of EL trial delay_goCue: ' + str(self.EarlyLickingTrialsN_Delay_GoCue) + '/' + str(len(self.Delay_GoCue_LeftLicks)) + ' ('+str(np.round(self.EarlyLickingRate_Delay_GoCue,2))+')' +'\n'
                            '  Left/Right early licks start_goCue: ' + str(sum(self.Start_GoCue_LeftLicks)) + '/' + str(sum(self.Start_GoCue_RightLicks)) + ' ('+str(np.round(self.Start_CoCue_LeftRightRatio,2))+')' +'\n\n'
                            
                            'Double dipping (DD)\n'
                            '  Frac of DD trial start_goCue: ' + str(self.DD_TrialsN_Start_CoCue) + '/' + str(len(self.Start_GoCue_DD)) + ' ('+str(np.round(self.DDRate_Start_CoCue,2))+')' +'\n'
                            '  Frac of DD trial start_delay: ' + str(self.DD_TrialsN_Start_Delay) + '/' + str(len(self.Start_Delay_DD)) + ' ('+str(np.round(self.DDRate_Start_Delay,2))+')' +'\n'
                            '  Frac of DD trial delay_goCue: ' + str(self.DD_TrialsN_Delay_GoCue) + '/' + str(len(self.Delay_GoCue_DD)) + ' ('+str(np.round(self.DDRate_Delay_GoCue,2))+')' +'\n'
                            '  Frac of DD trial goCue_goCue1: ' + str(self.DD_TrialsN_GoCue_GoCue1) + '/' + str(len(self.GoCue_GoCue1_DD)) + ' ('+str(np.round(self.DDRate_GoCue_GoCue1,2))+')' +'\n'
                            '  DD per finish trial start_goCue: ' + str(self.DD_PerTrial_Start_GoCue)+'\n'
                            '  DD per finish trial goCue_goCue1: ' + str(self.DD_PerTrial_GoCue_GoCue1)+'\n\n'
                )
                
            if self.B_CurrentTrialN >= 2:
                self.win.info_performance_others += (                
                            '  Frac of DD trial goCue_nextStart: ' + str(self.DD_TrialsN_GoCue_NextStart) + '/' + str(len(self.GoCue_NextStart_DD)) + ' ('+str(np.round(self.DDRate_GoCue_NextStart,2))+')' +'\n'
                            '  DD per finish trial goCue_nextStart: ' + str(self.DD_PerTrial_GoCue_NextStart)+'\n'
            )
            self.win.label_info_performance_others.setText(self.win.info_performance_others)
        elif self.win.default_ui=='ForagingGUI_Ephys.ui':
            self.win.Other_inforTitle='Session started: '+SessionStartTimeHM+ '  Current: '+CurrentTimeHM+ '  Run: '+str(self.win.Other_RunningTime)+'m'
            if (self.TP_AutoReward  or int(self.TP_BlockMinReward)>0) and self.win.Start.isChecked():
                # show the next trial
                self.win.Other_BasicTitle='Current trial: ' + str(self.B_CurrentTrialN+2)
            else:
                # show the current trial
                self.win.Other_BasicTitle='Current trial: ' + str(self.B_CurrentTrialN+1)
            self.win.infor.setTitle(self.win.Other_inforTitle)
            self.win.Basic.setTitle(self.win.Other_BasicTitle)
            # show basic session statistics    
            if self.B_CurrentTrialN>=0 and self.B_CurrentTrialN<1:
                Other_BasicText=  ('Current left block: ' + str(self.BS_CurrentBlockTrialNV[0]) + '/' +  str(self.BS_CurrentBlockLenV[0])+'\n'
                            'Current right block: ' + str(self.BS_CurrentBlockTrialNV[1]) + '/' +  str(self.BS_CurrentBlockLenV[1])+'\n\n'
                            'Responded trial: ' + str(self.BS_FinisheTrialN) + '/'+str(self.BS_AllTrialN)+' ('+str(np.round(self.BS_RespondedRate,2))+')'+'\n'
                            'Reward Trial: ' + str(self.BS_RewardTrialN) + '/' + str(self.BS_AllTrialN) + ' ('+str(np.round(self.BS_OverallRewardRate,2))+')' +'\n'
                            'Water in session (ul): '+str(np.round(self.win.water_in_session*1000,2)) +'\n'
                            'Earned Reward (ul): '+ str(sum(self.BS_EarnedReward_N))+' : '+str(np.round(sum(self.BS_earned_reward),3)) +'\n'
                            'Left choice rewarded: ' + str(self.BS_LeftRewardTrialN) + '/' + str(self.BS_LeftChoiceN) + ' ('+str(np.round(self.BS_LeftChoiceRewardRate,2))+')' +'\n'
                            'Right choice rewarded: ' + str(self.BS_RightRewardTrialN) + '/' + str(self.BS_RightChoiceN) + ' ('+str(np.round(self.BS_RightChoiceRewardRate,2))+')' +'\n')
                self.win.ShowBasic.setText(Other_BasicText)
                self.win.Other_BasicText=Other_BasicText
            elif self.B_CurrentTrialN>=1 and self.B_CurrentTrialN<2:
                Other_BasicText=('Current left block: ' + str(self.BS_CurrentBlockTrialNV[0]) + '/' +  str(self.BS_CurrentBlockLenV[0])+'\n'
                            'Current right block: ' + str(self.BS_CurrentBlockTrialNV[1]) + '/' +  str(self.BS_CurrentBlockLenV[1])+'\n\n'
                            'Responded trial: ' + str(self.BS_FinisheTrialN) + '/'+str(self.BS_AllTrialN)+' ('+str(np.round(self.BS_RespondedRate,2))+')'+'\n'
                            'Reward Trial: ' + str(self.BS_RewardTrialN) + '/' + str(self.BS_AllTrialN) + ' ('+str(np.round(self.BS_OverallRewardRate,2))+')' +'\n'
                            'Water in session (ul): '+str(np.round(self.win.water_in_session*1000,2)) +'\n'
                            'Earned Reward (ul): '+ str(sum(self.BS_EarnedReward_N))+' : '+str(np.round(sum(self.BS_earned_reward),3)) +'\n'
                            'Left choice rewarded: ' + str(self.BS_LeftRewardTrialN) + '/' + str(self.BS_LeftChoiceN) + ' ('+str(np.round(self.BS_LeftChoiceRewardRate,2))+')' +'\n'
                            'Right choice rewarded: ' + str(self.BS_RightRewardTrialN) + '/' + str(self.BS_RightChoiceN) + ' ('+str(np.round(self.BS_RightChoiceRewardRate,2))+')' +'\n\n'
                            
                            'Early licking (EL)\n'
                            '  Frac of EL trial start_goCue: ' + str(self.EarlyLickingTrialsN_Start_GoCue) + '/' + str(len(self.Start_GoCue_LeftLicks)) + ' ('+str(np.round(self.EarlyLickingRate_Start_GoCue,2))+')' +'\n'
                            '  Frac of EL trial start_delay: ' + str(self.EarlyLickingTrialsN_Start_Delay) + '/' + str(len(self.Start_Delay_LeftLicks)) + ' ('+str(np.round(self.EarlyLickingRate_Start_Delay,2))+')' +'\n'
                            '  Frac of EL trial delay_goCue: ' + str(self.EarlyLickingTrialsN_Delay_GoCue) + '/' + str(len(self.Delay_GoCue_LeftLicks)) + ' ('+str(np.round(self.EarlyLickingRate_Delay_GoCue,2))+')' +'\n'
                            '  Left/Right early licks start_goCue: ' + str(sum(self.Start_GoCue_LeftLicks)) + '/' + str(sum(self.Start_GoCue_RightLicks)) + ' ('+str(np.round(self.Start_CoCue_LeftRightRatio,2))+')' +'\n\n'
                            
                            'Double dipping (DD)\n'
                            '  Frac of DD trial start_goCue: ' + str(self.DD_TrialsN_Start_CoCue) + '/' + str(len(self.Start_GoCue_DD)) + ' ('+str(np.round(self.DDRate_Start_CoCue,2))+')' +'\n'
                            '  Frac of DD trial start_delay: ' + str(self.DD_TrialsN_Start_Delay) + '/' + str(len(self.Start_Delay_DD)) + ' ('+str(np.round(self.DDRate_Start_Delay,2))+')' +'\n'
                            '  Frac of DD trial delay_goCue: ' + str(self.DD_TrialsN_Delay_GoCue) + '/' + str(len(self.Delay_GoCue_DD)) + ' ('+str(np.round(self.DDRate_Delay_GoCue,2))+')' +'\n'
                            '  Frac of DD trial goCue_goCue1: ' + str(self.DD_TrialsN_GoCue_GoCue1) + '/' + str(len(self.GoCue_GoCue1_DD)) + ' ('+str(np.round(self.DDRate_GoCue_GoCue1,2))+')' +'\n'
                            '  DD per finish trial start_goCue: ' + str(self.DD_PerTrial_Start_GoCue)+'\n'
                            '  DD per finish trial goCue_goCue1: ' + str(self.DD_PerTrial_GoCue_GoCue1)+'\n')
                self.win.ShowBasic.setText(Other_BasicText)
                self.win.Other_BasicText=Other_BasicText
            elif self.B_CurrentTrialN>=2:
                Other_BasicText=('Current left block: ' + str(self.BS_CurrentBlockTrialNV[0]) + '/' +  str(self.BS_CurrentBlockLenV[0])+'\n'
                            'Current right block: ' + str(self.BS_CurrentBlockTrialNV[1]) + '/' +  str(self.BS_CurrentBlockLenV[1])+'\n\n'
                            'Foraging eff optimal: '+str(np.round(self.B_for_eff_optimal,2))+'\n'
                            'Foraging eff optimal random seed: '+ str(np.round(self.B_for_eff_optimal_random_seed,2))+'\n\n'
                            'Responded trial: ' + str(self.BS_FinisheTrialN) + '/'+str(self.BS_AllTrialN)+' ('+str(np.round(self.BS_RespondedRate,2))+')'+'\n'
                            'Reward Trial: ' + str(self.BS_RewardTrialN) + '/' + str(self.BS_AllTrialN) + ' ('+str(np.round(self.BS_OverallRewardRate,2))+')' +'\n'
                            'Water in session (ul): '+str(np.round(self.win.water_in_session*1000,2)) +'\n'
                            'Earned Reward (ul): '+ str(sum(self.BS_EarnedReward_N))+' : '+str(np.round(sum(self.BS_earned_reward),3)) +'\n'
                            'Left choice rewarded: ' + str(self.BS_LeftRewardTrialN) + '/' + str(self.BS_LeftChoiceN) + ' ('+str(np.round(self.BS_LeftChoiceRewardRate,2))+')' +'\n'
                            'Right choice rewarded: ' + str(self.BS_RightRewardTrialN) + '/' + str(self.BS_RightChoiceN) + ' ('+str(np.round(self.BS_RightChoiceRewardRate,2))+')' +'\n\n'
                            'Early licking (EL)\n'
                            '  Frac of EL trial start_goCue: ' + str(self.EarlyLickingTrialsN_Start_GoCue) + '/' + str(len(self.Start_GoCue_LeftLicks)) + ' ('+str(np.round(self.EarlyLickingRate_Start_GoCue,2))+')' +'\n'
                            '  Frac of EL trial start_delay: ' + str(self.EarlyLickingTrialsN_Start_Delay) + '/' + str(len(self.Start_Delay_LeftLicks)) + ' ('+str(np.round(self.EarlyLickingRate_Start_Delay,2))+')' +'\n'
                            '  Frac of EL trial delay_goCue: ' + str(self.EarlyLickingTrialsN_Delay_GoCue) + '/' + str(len(self.Delay_GoCue_LeftLicks)) + ' ('+str(np.round(self.EarlyLickingRate_Delay_GoCue,2))+')' +'\n'
                            '  Left/Right early licks start_goCue: ' + str(sum(self.Start_GoCue_LeftLicks)) + '/' + str(sum(self.Start_GoCue_RightLicks)) + ' ('+str(np.round(self.Start_CoCue_LeftRightRatio,2))+')' +'\n\n'
                            
                            'Double dipping (DD)\n'
                            '  Frac of DD trial start_goCue: ' + str(self.DD_TrialsN_Start_CoCue) + '/' + str(len(self.Start_GoCue_DD)) + ' ('+str(np.round(self.DDRate_Start_CoCue,2))+')' +'\n'
                            '  Frac of DD trial start_delay: ' + str(self.DD_TrialsN_Start_Delay) + '/' + str(len(self.Start_Delay_DD)) + ' ('+str(np.round(self.DDRate_Start_Delay,2))+')' +'\n'
                            '  Frac of DD trial delay_goCue: ' + str(self.DD_TrialsN_Delay_GoCue) + '/' + str(len(self.Delay_GoCue_DD)) + ' ('+str(np.round(self.DDRate_Delay_GoCue,2))+')' +'\n'
                            '  Frac of DD trial goCue_goCue1: ' + str(self.DD_TrialsN_GoCue_GoCue1) + '/' + str(len(self.GoCue_GoCue1_DD)) + ' ('+str(np.round(self.DDRate_GoCue_GoCue1,2))+')' +'\n'
                            '  Frac of DD trial goCue_nextStart: ' + str(self.DD_TrialsN_GoCue_NextStart) + '/' + str(len(self.GoCue_NextStart_DD)) + ' ('+str(np.round(self.DDRate_GoCue_NextStart,2))+')' +'\n'
                            '  DD per finish trial start_goCue: ' + str(self.DD_PerTrial_Start_GoCue)+'\n'
                            '  DD per finish trial goCue_goCue1: ' + str(self.DD_PerTrial_GoCue_GoCue1)+'\n'
                            '  DD per finish trial goCue_nextStart: ' + str(self.DD_PerTrial_GoCue_NextStart)+'\n')
                self.win.ShowBasic.setText(Other_BasicText)
                self.win.Other_BasicText=Other_BasicText
     
    def _CheckStop(self):
        '''Stop if there are many ingoral trials or if the maximam trial is exceeded MaxTrial'''
        StopIgnore=int(self.TP_StopIgnores)-1
        MaxTrial=int(self.TP_MaxTrial)-2 # trial number starts from 0
        MaxTime=float(self.TP_MaxTime)*60 # convert minutes to seconds
        if hasattr(self, 'BS_CurrentRunningTime'): 
            pass
        else:
            self.BS_CurrentRunningTime=0

        # Make message box prompt
        stop = False
        msg =''
        warning_label_text = ''
        warning_label_color = 'color: gray;'        

        # Check for reasons to stop early 
        if (np.shape(self.B_AnimalResponseHistory)[0]>=StopIgnore) and (np.all(self.B_AnimalResponseHistory[-StopIgnore:]==2)):
            stop=True
            msg = 'Stopping the session because the mouse has ignored at least {} consecutive trials'.format(self.TP_StopIgnores)
            warning_label_text = 'Stop because ignore trials exceed or equal: '+self.TP_StopIgnores
            warning_label_color = self.win.default_warning_color
        elif self.B_CurrentTrialN>MaxTrial: 
            stop=True
            msg = 'Stopping the session because the mouse has reached the maximum trial count: {}'.format(self.TP_MaxTrial)
            warning_label_text = 'Stop because maximum trials exceed or equal: '+self.TP_MaxTrial
            warning_label_color = self.win.default_warning_color
        elif self.BS_CurrentRunningTime>MaxTime:
            stop=True
            msg = 'Stopping the session because the session running time has reached {} minutes'.format(self.TP_MaxTime)
            warning_label_text = 'Stop because running time exceeds or equals: '+self.TP_MaxTime+'m'
            warning_label_color = self.win.default_warning_color
        else:
            stop=False

        # Update the warning label text/color
        self.win.WarningLabelStop.setText(warning_label_text)
        self.win.WarningLabelStop.setStyleSheet(warning_label_color)
    
        # If we should stop trials, uncheck the start button
        if stop:           
            self.win.Start.setStyleSheet("background-color : none")
            self.win.Start.setChecked(False)        
            reply = QtWidgets.QMessageBox.question(self.win, 'Box {}'.format(self.win.box_letter), msg, QtWidgets.QMessageBox.Ok)
    
    def _CheckAutoWater(self):
        '''Check if it should be an auto water trial'''
        if self.TP_AutoReward:
            UnrewardedN=int(self.TP_Unrewarded)
            IgnoredN=int(self.TP_Ignored)
            if UnrewardedN<=0:
                self.CurrentAutoReward=1
                self.win.WarningLabelAutoWater.setText('Auto water because unrewarded trials exceed: '+self.TP_Unrewarded)
                self.win.WarningLabelAutoWater.setStyleSheet(self.win.default_warning_color)
            elif  IgnoredN <=0:
                self.win.WarningLabelAutoWater.setText('Auto water because ignored trials exceed: '+self.TP_Ignored)
                self.win.WarningLabelAutoWater.setStyleSheet(self.win.default_warning_color)
                self.CurrentAutoReward=1
            else:
                if np.shape(self.B_AnimalResponseHistory)[0]>=IgnoredN or np.shape(self.B_RewardedHistory[0])[0]>=UnrewardedN:
                    # auto reward is considered as reward
                    B_RewardedHistory=self.B_RewardedHistory.copy()
                    Ind=range(len(self.B_RewardedHistory[0]))
                    for i in range(len(self.B_RewardedHistory)):
                        B_RewardedHistory[i]=np.logical_or(self.B_RewardedHistory[i],self.B_AutoWaterTrial[i][Ind])
                    if np.all(self.B_AnimalResponseHistory[-IgnoredN:]==2) and np.shape(self.B_AnimalResponseHistory)[0]>=IgnoredN:
                        self.CurrentAutoReward=1
                        self.win.WarningLabelAutoWater.setText('Auto water because ignored trials exceed: '+self.TP_Ignored)
                        self.win.WarningLabelAutoWater.setStyleSheet(self.win.default_warning_color)
                    elif (np.all(B_RewardedHistory[0][-UnrewardedN:]==False) and np.all(B_RewardedHistory[1][-UnrewardedN:]==False) and np.shape(B_RewardedHistory[0])[0]>=UnrewardedN):
                        self.CurrentAutoReward=1
                        self.win.WarningLabelAutoWater.setText('Auto water because unrewarded trials exceed: '+self.TP_Unrewarded)
                        self.win.WarningLabelAutoWater.setStyleSheet(self.win.default_warning_color)
                    else:
                        self.CurrentAutoReward=0
                else:
                    self.CurrentAutoReward=0
        else:
            self.CurrentAutoReward=0

    def _GetLaserWaveForm(self):
        '''Get the waveform of the laser. It dependens on color/duration/protocol(frequency/RD/pulse duration)/locations/laser power'''
        N=self.SelctedCondition
        # CLP, current laser parameter
        self.CLP_Color=getattr(self,f"TP_LaserColor_{N}")
        self.CLP_Location=getattr(self,f"TP_Location_{N}")
        self.CLP_Laser1Power=getattr(self,f"TP_Laser1_power_{N}")
        self.CLP_Laser2Power=getattr(self,f"TP_Laser2_power_{N}")
        self.CLP_Duration=float(getattr(self,f"TP_Duration_{N}"))
        self.CLP_Protocol=getattr(self,f"TP_Protocol_{N}")
        if not self.CLP_Protocol=='Constant':
            self.CLP_Frequency=float(getattr(self,f"TP_Frequency_{N}"))
        self.CLP_RampingDown=float(getattr(self,f"TP_RD_{N}"))
        self.CLP_PulseDur=getattr(self,f"TP_PulseDur_{N}")
        self.CLP_LaserStart=getattr(self,f"TP_LaserStart_{N}")
        self.CLP_OffsetStart=float(getattr(self,f"TP_OffsetStart_{N}"))
        self.CLP_LaserEnd=getattr(self,f"TP_LaserEnd_{N}")
        self.CLP_OffsetEnd=float(getattr(self,f"TP_OffsetEnd_{N}"))# negative, backward; positive forward
        self.CLP_SampleFrequency=float(self.TP_SampleFrequency)
        # align to trial start
        if (self.CLP_LaserStart=='Trial start' or self.CLP_LaserStart=='Go cue' or self.CLP_LaserStart=='Reward outcome') and self.CLP_LaserEnd=='NA':
            # the duration is determined by Duration
            self.CLP_CurrentDuration=self.CLP_Duration
        elif self.CLP_LaserStart=='Trial start' and self.CLP_LaserEnd=='Go cue':
            # the duration is determined by CurrentITI, CurrentDelay, self.CLP_OffsetStart, self.CLP_OffsetEnd
            # only positive CLP_OffsetStart is allowed
            if self.CLP_OffsetStart<0:
                self.win.WarningLabel.setText('Please set offset start to be positive!')
                self.win.WarningLabel.setStyleSheet(self.win.default_warning_color)
            # there is no delay for optogenetics trials 
            self.CLP_CurrentDuration=self.CurrentITI-self.CLP_OffsetStart+self.CLP_OffsetEnd
        elif self.CLP_LaserStart=='Go cue' and self.CLP_LaserEnd=='Trial start':
            # The duration is inaccurate as it doesn't account for time outside of bonsai (can be solved in Bonsai)
            # the duration is determined by TP_ResponseTime, self.CLP_OffsetStart, self.CLP_OffsetEnd
            self.CLP_CurrentDuration=float(self.TP_ResponseTime)-self.CLP_OffsetStart+self.CLP_OffsetEnd
        else:
            pass
        self.B_LaserDuration.append(self.CLP_CurrentDuration)
        # generate the waveform based on self.CLP_CurrentDuration and Protocol, Frequency, RampingDown, PulseDur
        self._GetLaserAmplitude()
        # dimension of self.CurrentLaserAmplitude indicates how many locations do we have
        for i in range(len(self.CurrentLaserAmplitude)):
            # in some cases the other paramters except the amplitude could also be different
            self._ProduceWaveForm(self.CurrentLaserAmplitude[i])
            setattr(self, 'WaveFormLocation_' + str(i+1), self.my_wave)
            setattr(self, f"Location{i+1}_Size", getattr(self, f"WaveFormLocation_{i+1}").size)

    def _ProduceWaveForm(self,Amplitude):
        '''generate the waveform based on Duration and Protocol, Laser Power, Frequency, RampingDown, PulseDur and the sample frequency'''
        if self.CLP_Protocol=='Sine':
            resolution=self.CLP_SampleFrequency*self.CLP_CurrentDuration # how many datapoints to generate
            cycles=self.CLP_CurrentDuration*self.CLP_Frequency # how many sine cycles
            length = np.pi * 2 * cycles
            self.my_wave = Amplitude*(1+np.sin(np.arange(0+1.5*math.pi, length+1.5*math.pi, length / resolution)))/2
            # add ramping down
            self._get_ramping_down()
            # add offset
            self._add_offset()
            self.my_wave=np.append(self.my_wave,[0,0])

        elif self.CLP_Protocol=='Pulse':
            if self.CLP_PulseDur=='NA':
                self.win.WarningLabel.setText('Pulse duration is NA!')
                self.win.WarningLabel.setStyleSheet(self.win.default_warning_color)
                self.CLP_PulseDur=0
                self.my_wave=np.empty(0)
                self.opto_error_tag=1
            elif self.CLP_Frequency=='':
                self.win.WarningLabel.setText('Pulse frequency is NA!')
                self.win.WarningLabel.setStyleSheet(self.win.default_warning_color)
                self.CLP_Frequency=0
                self.my_wave=np.empty(0)
                self.opto_error_tag=1
            else:
                self.CLP_PulseDur=float(self.CLP_PulseDur)
                PointsEachPulse=int(self.CLP_SampleFrequency*self.CLP_PulseDur)
                PulseIntervalPoints=int(1/self.CLP_Frequency*self.CLP_SampleFrequency-PointsEachPulse)
                if PulseIntervalPoints<0:
                    self.win.WarningLabel.setText('Pulse frequency and pulse duration are not compatible!')
                    self.win.WarningLabel.setStyleSheet(self.win.default_warning_color)
                TotalPoints=int(self.CLP_SampleFrequency*self.CLP_CurrentDuration)
                PulseNumber=np.floor(self.CLP_CurrentDuration*self.CLP_Frequency) 
                EachPulse=Amplitude*np.ones(PointsEachPulse)
                PulseInterval=np.zeros(PulseIntervalPoints)
                WaveFormEachCycle=np.concatenate((EachPulse, PulseInterval), axis=0)
                self.my_wave=np.empty(0)
                # pulse number should be greater than 0
                if PulseNumber>1:
                    for i in range(int(PulseNumber-1)):
                        self.my_wave=np.concatenate((self.my_wave, WaveFormEachCycle), axis=0)
                else:
                    self.win.WarningLabel.setText('Pulse number is less than 1!')
                    self.win.WarningLabel.setStyleSheet(self.win.default_warning_color)
                    return
                self.my_wave=np.concatenate((self.my_wave, EachPulse), axis=0)
                self.my_wave=np.concatenate((self.my_wave, np.zeros(TotalPoints-np.shape(self.my_wave)[0])), axis=0)
                # add offset
                self._add_offset()
                self.my_wave=np.append(self.my_wave,[0,0])
        elif self.CLP_Protocol=='Constant':
            resolution=self.CLP_SampleFrequency*self.CLP_CurrentDuration # how many datapoints to generate
            self.my_wave=Amplitude*np.ones(int(resolution))
            # add ramping down
            self._get_ramping_down()
            # add offset
            self._add_offset()
            self.my_wave=np.append(self.my_wave,[0,0])
        else:
            self.win.WarningLabel.setText('Unidentified optogenetics protocol!')
            self.win.WarningLabel.setStyleSheet(self.win.default_warning_color)

        '''
        # test
        import matplotlib.pyplot as plt
        plt.plot(np.arange(0, length, length / resolution), self.my_wave)   
        plt.show()
        '''
    def _get_ramping_down(self):
        '''Add ramping down to the waveform'''
        if self.CLP_RampingDown>0:
            if self.CLP_RampingDown>self.CLP_CurrentDuration:
                self.win.WarningLabel.setText('Ramping down is longer than the laser duration!')
                self.win.WarningLabel.setStyleSheet(self.win.default_warning_color)
            else:
                Constant=np.ones(int((self.CLP_CurrentDuration-self.CLP_RampingDown)*self.CLP_SampleFrequency))
                RD=np.arange(1,0, -1/(np.shape(self.my_wave)[0]-np.shape(Constant)[0]))
                RampingDown = np.concatenate((Constant, RD), axis=0)
                self.my_wave=self.my_wave*RampingDown

    def _add_offset(self):
        '''Add offset to the waveform'''            
        if self.CLP_OffsetStart>0:
            OffsetPoints=int(self.CLP_SampleFrequency*self.CLP_OffsetStart)
            Offset=np.zeros(OffsetPoints)
            self.my_wave=np.concatenate((Offset,self.my_wave),axis=0)

    def _GetLaserAmplitude(self):
        '''the voltage amplitude dependens on Protocol, Laser Power, Laser color, and the stimulation locations<>'''
        self.CurrentLaserAmplitude=[0,0]
        if self.CLP_Location=='Laser_1':
            if self.CLP_Laser1Power=='':
                self.win.WarningLabel.setText('No amplitude for Laser_1 defined!')
                self.win.WarningLabel.setStyleSheet(self.win.default_warning_color)
            else:
                Laser1PowerAmp=eval(self.CLP_Laser1Power)
                self.CurrentLaserAmplitude=[Laser1PowerAmp[0],0]
        elif self.CLP_Location=='Laser_2':
            if self.CLP_Laser2Power=='':
                self.win.WarningLabel.setText('No amplitude for Laser_2 defined!')
                self.win.WarningLabel.setStyleSheet(self.win.default_warning_color)
            else:
                Laser2PowerAmp=eval(self.CLP_Laser2Power)
                self.CurrentLaserAmplitude=[0,Laser2PowerAmp[0]]
        elif self.CLP_Location=='Both':
            if  self.CLP_Laser1Power=='' or self.CLP_Location=='':
                self.win.WarningLabel.setText('No amplitude for Laser_1 or Laser_2 laser defined!')
                self.win.WarningLabel.setStyleSheet(self.win.default_warning_color)
            else:
                Laser1PowerAmp=eval(self.CLP_Laser1Power)
                Laser2PowerAmp=eval(self.CLP_Laser2Power)
                self.CurrentLaserAmplitude=[Laser1PowerAmp[0],Laser2PowerAmp[0]]
        else:
            self.win.WarningLabel.setText('No stimulation location defined!')
            self.win.WarningLabel.setStyleSheet(self.win.default_warning_color)
        self.B_LaserAmplitude.append(self.CurrentLaserAmplitude)

    def _SelectOptogeneticsCondition(self):
        '''To decide if this should be an optogenetics trial'''
        # condition should be taken into account in the future
        # check session session
        self._CheckSessionControl()
        if self.session_control_state==0 and self.TP_SessionWideControl=='on':
            self.SelctedCondition=0
            return
        ConditionsOn=[]
        Probabilities=[]
        empty=1
        condition_idx = [1, 2, 3, 4, 5, 6]
        TP_LaserColors = [ f'TP_LaserColor_{i}' for i in condition_idx]
        for attr_name in dir(self):
            if attr_name in TP_LaserColors:
                if getattr(self, attr_name) !='NA':
                    parts = attr_name.split('_')
                    ConditionsOn.append(parts[-1])
                    Probabilities.append(float(getattr(self, 'TP_Probability_' + parts[-1])))
                    empty=0
        if empty==1:
            self.SelctedCondition=0
            return
        self.ConditionsOn=ConditionsOn
        self.Probabilities=Probabilities
        ProAccu=list(accumulate(Probabilities))
        b=random.uniform(0,1)
        for i in range(len(ProAccu)):
            if b <= ProAccu[i]:
                self.SelctedCondition=self.ConditionsOn[i]
                break
            else:
                self.SelctedCondition=0 # control is selected
        # Determine whether the interval between two near trials is larger than the MinOptoInterval
        non_zero_indices=np.nonzero(np.array(self.B_SelectedCondition).astype(int))
        if len(non_zero_indices[0])>0:
            if len(self.B_SelectedCondition)-(non_zero_indices[0][-1]+1)<float(self.TP_MinOptoInterval):
                self.SelctedCondition=0
                
    def _InitiateATrial(self,Channel1,Channel4):
    
        # Indicate that unsaved data exists
        self.win.unsaved_data=True
        self.win.Save.setStyleSheet("color: white;background-color : mediumorchid;")

        # Determine if the current lick port should be baited. self.B_Baited can only be updated after receiving response of the animal, so this part cannot appear in the _GenerateATrial section
        RandomNumber=np.random.random(2)
        self.B_CurrentRewardProbRandomNumber.append(RandomNumber)
        self.CurrentBait=self.B_CurrentRewardProb>RandomNumber
        if (self.TP_Task in ['Coupled Baiting','Uncoupled Baiting']):
             self.CurrentBait= self.CurrentBait | self.B_Baited
        # For task rewardN, if this is the "initial N trials" of the active side, no bait will be be given.
        if self.BaitPermitted is False:
            # no reward in the active side
            max_index = np.argmax(self.B_CurrentRewardProb)
            self.CurrentBait[max_index]=False
        self.B_Baited=  self.CurrentBait.copy()
        self.B_BaitHistory=np.append(self.B_BaitHistory, self.CurrentBait.reshape(2,1),axis=1)
        # determine auto water
        if self.CurrentAutoReward==0:
            self.win.WarningLabelAutoWater.setText('')
            self.win.WarningLabelAutoWater.setStyleSheet("color: gray;")
        if self.CurrentAutoReward==1:
            self.CurrentAutoRewardTrial=[0,0]
            if self.TP_AutoWaterType=='Natural':
                for i in range(len(self.CurrentBait)):
                    if self.CurrentBait[i]==True:
                        self.CurrentAutoRewardTrial[i]=1
            if self.TP_AutoWaterType=='Both':
                self.CurrentAutoRewardTrial=[1,1]
            if self.TP_AutoWaterType=='High pro':
                if self.B_CurrentRewardProb[0]>self.B_CurrentRewardProb[1]:
                    self.CurrentAutoRewardTrial=[1,0]
                elif self.B_CurrentRewardProb[0]<self.B_CurrentRewardProb[1]:
                    self.CurrentAutoRewardTrial=[0,1]
                else:
                    self.CurrentAutoRewardTrial=[1,1]
            # make it no baited reward for auto reward side
            for i in range(len(self.CurrentAutoRewardTrial)):
                if self.CurrentAutoRewardTrial[i]==1:
                    self.CurrentBait[i]=0
                    self.B_Baited[i]=False
        else:
            self.CurrentAutoRewardTrial=[0,0]
        self.B_AutoWaterTrial=np.append(self.B_AutoWaterTrial, np.array(self.CurrentAutoRewardTrial).reshape(2,1),axis=1)

        self._CheckSimulationSession()
        if self.CurrentSimulation==False: # run simulation if it's true
            # send optogenetics waveform of the upcoming trial if this is an optogenetics trial
            if self.B_LaserOnTrial[self.B_CurrentTrialN]==1:     
                if self.CLP_LaserStart=='Trial start':
                    Channel1.TriggerSource('/Dev1/PFI0') # /Dev1/PFI0 corresponding to P2.0 of NIdaq USB6002; Using /Dev1/PFI0 specific for ITI; Using DO0 to trigger NIDaq
                    Channel1.PassGoCue(int(0))
                    Channel1.PassRewardOutcome(int(0))
                elif self.CLP_LaserStart=='Go cue':
                    Channel1.TriggerSource('/Dev1/PFI1') # /Dev1/PFI1 corresponding to P1.1 of NIdaq USB6002; Using /Dev1/PFI1 for optogenetics aligned to non "Trial start" events; Using DO3 to trigger NiDaq
                    Channel1.PassGoCue(int(1))
                    Channel1.PassRewardOutcome(int(0))
                elif self.CLP_LaserStart=='Reward outcome':
                    Channel1.TriggerSource('/Dev1/PFI1')
                    Channel1.PassGoCue(int(0))
                    Channel1.PassRewardOutcome(int(1))
                else:
                    self.win.WarningLabel.setText('Unindentified optogenetics start event!')
                    self.win.WarningLabel.setStyleSheet(self.win.default_warning_color)
                # send the waveform size
                Channel1.Location1_Size(int(self.Location1_Size))
                Channel1.Location2_Size(int(self.Location2_Size))
                for i in range(len(self.CurrentLaserAmplitude)): # locations of these waveforms
                    getattr(Channel4, 'WaveForm' + str(1)+'_'+str(i+1))(str(getattr(self, 'WaveFormLocation_'+str(i+1)).tolist())[1:-1])
                FinishOfWaveForm=Channel4.receive()  
            else:
                Channel1.PassGoCue(int(0))
                Channel1.PassRewardOutcome(int(0))
            Channel1.LeftValue(float(self.TP_LeftValue)*1000)
            Channel1.RightValue(float(self.TP_RightValue)*1000)
            Channel1.RewardConsumeTime(float(self.TP_RewardConsumeTime))
            Channel1.Left_Bait(int(self.CurrentBait[0]))
            Channel1.Right_Bait(int(self.CurrentBait[1]))
            Channel1.ITI(float(self.CurrentITI))
            if self.TP_RewardDelay=='':
                self.TP_RewardDelay=0
            Channel1.RewardDelay(float(self.TP_RewardDelay))
            Channel1.DelayTime(float(self.CurrentDelay))
            Channel1.ResponseTime(float(self.TP_ResponseTime))
            if self.TP_OptogeneticsB=='on':
                Channel1.start(3)
                self.CurrentStartType=3
                self.B_StartType.append(self.CurrentStartType)
            else:
                Channel1.start(1)
                self.CurrentStartType=1
                self.B_StartType.append(self.CurrentStartType)

    def _CheckSimulationSession(self):
        '''To check if this is a simulation session'''
        if self.win.actionWin_stay_lose_switch.isChecked()==True or  self.win.actionRandom_choice.isChecked()==True:
            self.CurrentSimulation=True
            self.B_SimulationSession.append(True)
        else:
            self.CurrentSimulation=False
            self.B_SimulationSession.append(False)
            
    def _SimulateResponse(self):
        '''Simulate animal's response'''

        # win stay, lose switch forager
        if self.win.actionWin_stay_lose_switch.isChecked()==True:
            if self.B_CurrentTrialN>=2:
                if np.random.random(1)<0.1: # no response
                    self.B_AnimalCurrentResponse=2
                else:
                    if np.random.random(1) < 0:  # Introduce a left bias if needed
                        self.B_AnimalCurrentResponse = 0
                    elif any(self.B_RewardedHistory[:,-1]==1):# win
                        self.B_AnimalCurrentResponse=self.B_AnimalResponseHistory[-1]
                    elif any(self.B_RewardedHistory[:,-1]==0) and self.B_AnimalResponseHistory[-1]!=2:# lose
                        self.B_AnimalCurrentResponse=1-self.B_AnimalResponseHistory[-1]
                    else: # no response
                        self.B_AnimalCurrentResponse=random.choice(range(2))
            else:
                self.B_AnimalCurrentResponse=random.choice(range(2))
        # random forager
        elif self.win.actionRandom_choice.isChecked()==True:
            if np.random.random(1)<0.1: # no response
                self.B_AnimalCurrentResponse=2
            else:
                self.B_AnimalCurrentResponse=random.choice(range(2))

        if self.B_AnimalCurrentResponse==2:
            self.B_CurrentRewarded[0]=False
            self.B_CurrentRewarded[1]=False
            self._add_one_trial()
        elif self.B_AnimalCurrentResponse==0 and self.CurrentBait[0]==True:
            self.B_Baited[0]=False
            self.B_CurrentRewarded[1]=False
            self.B_CurrentRewarded[0]=True  
        elif self.B_AnimalCurrentResponse==0 and self.CurrentBait[0]==False:
            self.B_Baited[0]=False
            self.B_CurrentRewarded[0]=False
            self.B_CurrentRewarded[1]=False
        elif self.B_AnimalCurrentResponse==1 and self.CurrentBait[1]==True:
            self.B_Baited[1]=False
            self.B_CurrentRewarded[0]=False
            self.B_CurrentRewarded[1]=True
        elif self.B_AnimalCurrentResponse==1 and self.CurrentBait[1]==False:
            self.B_Baited[1]=False
            self.B_CurrentRewarded[0]=False
            self.B_CurrentRewarded[1]=False

        self.B_AnimalResponseHistory=np.append(self.B_AnimalResponseHistory,self.B_AnimalCurrentResponse)
        self.B_RewardedHistory=np.append(self.B_RewardedHistory,self.B_CurrentRewarded,axis=1)

        TN=np.shape(self.B_TrialStartTimeHarp)[0]
        if TN==0:
            TrialStartTimeHarp=0
        else:
            TrialStartTimeHarp=self.B_TrialStartTimeHarp[TN-1]+self.B_ITIHistory[TN-1]+self.B_DelayHistory[TN-1]+self.B_ResponseTimeHistory[TN-1]+float(self.Obj['TP_RewardConsumeTime'][TN-1])
        
        DelayStartTimeHarp=TrialStartTimeHarp+self.B_ITIHistory[TN]
        GoCueTimeBehaviorBoard=DelayStartTimeHarp+self.B_DelayHistory[TN]
        TrialEndTimeHarp=GoCueTimeBehaviorBoard+self.B_ResponseTimeHistory[TN]+float(self.Obj['TP_RewardConsumeTime'][TN])
        B_DOPort2Output=GoCueTimeBehaviorBoard
        TrialStartTime=TrialStartTimeHarp
        DelayStartTime=DelayStartTimeHarp
        TrialEndTime=TrialEndTimeHarp
        GoCueTime=GoCueTimeBehaviorBoard
        RewardOutcomeTime=TrialEndTimeHarp
        # get the event harp time
        self.B_TrialStartTimeHarp=np.append(self.B_TrialStartTimeHarp,TrialStartTimeHarp)
        self.B_DelayStartTimeHarp=np.append(self.B_DelayStartTimeHarp,DelayStartTimeHarp)
        self.B_DelayStartTimeHarpComplete.append(DelayStartTimeHarp)
        self.B_TrialEndTimeHarp=np.append(self.B_TrialEndTimeHarp,TrialEndTimeHarp)
        self.B_GoCueTimeBehaviorBoard=np.append(self.B_GoCueTimeBehaviorBoard,GoCueTimeBehaviorBoard)
        self.B_GoCueTimeSoundCard=np.append(self.B_GoCueTimeBehaviorBoard,GoCueTimeBehaviorBoard)
        self.B_DOPort2Output=np.append(self.B_DOPort2Output,B_DOPort2Output)
        # get the event time
        self.B_TrialStartTime=np.append(self.B_TrialStartTime,TrialStartTime)
        self.B_DelayStartTime=np.append(self.B_DelayStartTime,DelayStartTime)
        self.B_DelayStartTimeComplete.append(DelayStartTime)
        self.B_TrialEndTime=np.append(self.B_TrialEndTime,TrialEndTime)
        self.B_GoCueTime=np.append(self.B_GoCueTime,GoCueTime)
        self.B_RewardOutcomeTime=np.append(self.B_RewardOutcomeTime,RewardOutcomeTime)
        self.GetResponseFinish=1

    def _add_one_trial(self):
        # to decide if we should add one trial to the block length on both sides
        if self.TP_AddOneTrialForNoresponse=='Yes':
            if self.TP_Task in ['Uncoupled Baiting','Uncoupled Without Baiting']:
                for i, side in enumerate(['L', 'R']):
                    self.uncoupled_blocks.block_ends[side][-1] = self.uncoupled_blocks.block_ends[side][-1]+1
            elif self.TP_Task in ['Coupled Baiting','Coupled Without Baiting']:
                for i, side in enumerate(['L', 'R']):
                    self.BlockLenHistory[i][-1] = self.BlockLenHistory[i][-1]+1

    def _GetAnimalResponse(self,Channel1,Channel3,Channel4):
        '''Get the animal's response'''
        self._CheckSimulationSession()
        if self.CurrentSimulation==True:
            self._SimulateResponse()
            return
        # set the valve time of auto water
        if self.CurrentAutoRewardTrial[0]==1:
            self._set_valve_time_left(Channel3,float(self.win.LeftValue.text()),float(self.win.Multiplier.text()))
        if self.CurrentAutoRewardTrial[1]==1:
            self._set_valve_time_right(Channel3,float(self.win.RightValue.text()),float(self.win.Multiplier.text()))
            
        if self.CurrentStartType==3: # no delay timestamp
            ReceiveN=9
            DelayStartTimeHarp=[None] # -999 means a placeholder
            DelayStartTime=[None]
        elif self.CurrentStartType==1:
            ReceiveN=11
            DelayStartTimeHarp=[]
            DelayStartTime=[]

        current_receiveN=0
        behavior_eventN=0
        in_delay=0 #0, the next /BehaviorEvent is not the delay; 1, the next /BehaviorEvent is the delay following the /TrialStartTime
        first_behavior_event=0
        first_delay_start=0
        while 1:
            Rec=Channel1.receive()
            if Rec[0].address not in ['/BehaviorEvent','/DelayStartTime']:
                current_receiveN+=1
            if Rec[0].address=='/TrialStartTime':
                TrialStartTime=Rec[1][1][0]
                in_delay=1 # the next /BehaviorEvent is the delay
            elif Rec[0].address=='/DelayStartTime':
                DelayStartTime.append(Rec[1][1][0])
                if first_delay_start==0:
                    first_delay_start=1
                    current_receiveN+=1
            elif Rec[0].address=='/GoCueTime':
                GoCueTime=Rec[1][1][0]
                in_delay=0
            elif Rec[0].address=='/RewardOutcomeTime':
                RewardOutcomeTime=Rec[1][1][0]
            elif Rec[0].address=='/RewardOutcome':
                TrialOutcome=Rec[1][1][0]
                if TrialOutcome=='NoResponse':
                    self.B_AnimalCurrentResponse=2
                    self.B_CurrentRewarded[0]=False
                    self.B_CurrentRewarded[1]=False
                    self._add_one_trial()
                elif TrialOutcome=='RewardLeft':
                    self.B_AnimalCurrentResponse=0
                    self.B_Baited[0]=False
                    self.B_CurrentRewarded[1]=False
                    self.B_CurrentRewarded[0]=True  
                elif TrialOutcome=='ErrorLeft':
                    self.B_AnimalCurrentResponse=0
                    self.B_Baited[0]=False
                    self.B_CurrentRewarded[0]=False
                    self.B_CurrentRewarded[1]=False
                elif TrialOutcome=='RewardRight':
                    self.B_AnimalCurrentResponse=1
                    self.B_Baited[1]=False
                    self.B_CurrentRewarded[0]=False
                    self.B_CurrentRewarded[1]=True
                elif TrialOutcome=='ErrorRight':
                    self.B_AnimalCurrentResponse=1
                    self.B_Baited[1]=False
                    self.B_CurrentRewarded[0]=False
                    self.B_CurrentRewarded[1]=False
                B_CurrentRewarded=self.B_CurrentRewarded
                B_AnimalCurrentResponse=self.B_AnimalCurrentResponse
            elif Rec[0].address=='/TrialEndTime':
                TrialEndTime=Rec[1][1][0]
            elif Rec[0].address=='/GoCueTimeSoundCard':
                # give auto water after Co cue
                # Randomlizing the order to avoid potential bias. 
                if np.random.random(1)<0.5:
                    if self.CurrentAutoRewardTrial[0]==1:
                        Channel3.AutoWater_Left(int(1))
                    if self.CurrentAutoRewardTrial[1]==1:
                        Channel3.AutoWater_Right(int(1))
                else:
                    if self.CurrentAutoRewardTrial[1]==1:
                        Channel3.AutoWater_Right(int(1))
                    if self.CurrentAutoRewardTrial[0]==1:
                        Channel3.AutoWater_Left(int(1))
                        
                # give reserved manual water
                if float(self.win.give_left_volume_reserved) > 0 or float(self.win.give_right_volume_reserved) > 0:
                    # Set the text of a label or text widget to show the reserved volumes
                    self.win.ManualWaterWarning.setText(
                        f'Give reserved manual water (ul) left: {self.win.give_left_volume_reserved}; right: {self.win.give_right_volume_reserved}'
                    )
                    # Set the text color of the label or text widget to red
                    self.win.ManualWaterWarning.setStyleSheet(self.win.default_warning_color)

                # The manual water of two sides are given sequentially. Randomlizing the order to avoid bias. 
                if np.random.random(1)<0.5:
                    self.win._give_reserved_water(valve='left')
                    self.win._give_reserved_water(valve='right')
                else:
                    self.win._give_reserved_water(valve='right')
                    self.win._give_reserved_water(valve='left')
                GoCueTimeSoundCard=Rec[1][1][0]
                in_delay=0
            elif Rec[0].address=='/DOPort2Output': #this port is used to trigger optogenetics aligned to Go cue
                B_DOPort2Output=Rec[1][1][0]
                self.B_DOPort2Output=np.append(self.B_DOPort2Output,B_DOPort2Output)
            elif Rec[0].address=='/ITIStartTimeHarp':
                TrialStartTimeHarp=Rec[1][1][0]
            elif Rec[0].address=='/BehaviorEvent':
                if in_delay==1:
                    DelayStartTimeHarp.append(Rec[1][1][0])
                    if first_behavior_event==0:
                        first_behavior_event=1
                        current_receiveN+=1 # only count once
                else:
                    if behavior_eventN==0:
                        GoCueTimeBehaviorBoard=Rec[1][1][0]
                    elif behavior_eventN==1:
                        TrialEndTimeHarp=Rec[1][1][0]
                    behavior_eventN+=1
                    current_receiveN+=1
            if current_receiveN==ReceiveN:
                break
        
        self.B_RewardedHistory=np.append(self.B_RewardedHistory,B_CurrentRewarded,axis=1)
        self.B_AnimalResponseHistory=np.append(self.B_AnimalResponseHistory,B_AnimalCurrentResponse)
        # get the event harp time
        self.B_TrialStartTimeHarp=np.append(self.B_TrialStartTimeHarp,TrialStartTimeHarp)
        self.B_DelayStartTimeHarp=np.append(self.B_DelayStartTimeHarp,DelayStartTimeHarp[0])
        self.B_DelayStartTimeHarpComplete.append(DelayStartTimeHarp)
        self.B_TrialEndTimeHarp=np.append(self.B_TrialEndTimeHarp,TrialEndTimeHarp)
        self.B_GoCueTimeBehaviorBoard=np.append(self.B_GoCueTimeBehaviorBoard,GoCueTimeBehaviorBoard)
        self.B_GoCueTimeSoundCard=np.append(self.B_GoCueTimeSoundCard,GoCueTimeSoundCard)
        # get the event time
        self.B_TrialStartTime=np.append(self.B_TrialStartTime,TrialStartTime)
        self.B_DelayStartTime=np.append(self.B_DelayStartTime,DelayStartTime[0])
        self.B_DelayStartTimeComplete.append(DelayStartTime)
        self.B_TrialEndTime=np.append(self.B_TrialEndTime,TrialEndTime)
        self.B_GoCueTime=np.append(self.B_GoCueTime,GoCueTime)
        self.B_RewardOutcomeTime=np.append(self.B_RewardOutcomeTime,RewardOutcomeTime)
        self.GetResponseFinish=1

    def _set_valve_time_left(self,channel3,LeftValue=0.01,Multiplier=1):
        '''set the left valve time'''
        channel3.LeftValue1(LeftValue*1000*Multiplier) 
    def _set_valve_time_right(self,channel3,RightValue=0.01,Multiplier=1):
        '''set the right valve time'''
        channel3.RightValue1(RightValue*1000*Multiplier)

    def _GiveLeft(self,channel3):
        '''manually give left water'''
        channel3.LeftValue1(float(self.win.LeftValue.text())*1000*float(self.win.Multiplier.text())) 
        time.sleep(0.01) 
        channel3.ManualWater_Left(int(1))
        channel3.LeftValue1(float(self.win.LeftValue.text())*1000)

    def _GiveRight(self,channel3):
        '''manually give right water'''
        channel3.RightValue1(float(self.win.RightValue.text())*1000*float(self.win.Multiplier.text()))
        time.sleep(0.01) 
        channel3.ManualWater_Right(int(1))
        channel3.RightValue1(float(self.win.RightValue.text())*1000)

    def _get_irregular_timestamp(self,Channel2):
        '''Get timestamps occurred irregularly (e.g. licks and reward delivery time)'''
        while not Channel2.msgs.empty():
            Rec=Channel2.receive()
            if Rec[0].address=='/LeftLickTime':
                self.B_LeftLickTime=np.append(self.B_LeftLickTime,Rec[1][1][0])
            elif Rec[0].address=='/RightLickTime':
                self.B_RightLickTime=np.append(self.B_RightLickTime,Rec[1][1][0])
            elif Rec[0].address=='/LeftRewardDeliveryTime':
                self.B_LeftRewardDeliveryTime=np.append(self.B_LeftRewardDeliveryTime,Rec[1][1][0])
            elif Rec[0].address=='/RightRewardDeliveryTime':
                self.B_RightRewardDeliveryTime=np.append(self.B_RightRewardDeliveryTime,Rec[1][1][0])
            elif Rec[0].address=='/LeftRewardDeliveryTimeHarp':
                self.B_LeftRewardDeliveryTimeHarp=np.append(self.B_LeftRewardDeliveryTimeHarp,Rec[1][1][0])
            elif Rec[0].address=='/RightRewardDeliveryTimeHarp':
                self.B_RightRewardDeliveryTimeHarp=np.append(self.B_RightRewardDeliveryTimeHarp,Rec[1][1][0])
            elif Rec[0].address=='/PhotometryRising':
                self.B_PhotometryRisingTimeHarp=np.append(self.B_PhotometryRisingTimeHarp,Rec[1][1][0])
            elif Rec[0].address=='/PhotometryFalling':
                self.B_PhotometryFallingTimeHarp=np.append(self.B_PhotometryFallingTimeHarp,Rec[1][1][0])
            elif Rec[0].address=='/OptogeneticsTimeHarp':
                self.B_OptogeneticsTimeHarp=np.append(self.B_OptogeneticsTimeHarp,Rec[1][1][0])
            elif Rec[0].address=='/ManualLeftWaterStartTime':
                self.B_ManualLeftWaterStartTime=np.append(self.B_ManualLeftWaterStartTime,Rec[1][1][0])
            elif Rec[0].address=='/ManualRightWaterStartTime':
                self.B_ManualRightWaterStartTime=np.append(self.B_ManualRightWaterStartTime,Rec[1][1][0])
            elif Rec[0].address=='/EarnedLeftWaterStartTime':
                self.B_EarnedLeftWaterStartTime=np.append(self.B_EarnedLeftWaterStartTime,Rec[1][1][0])
            elif Rec[0].address=='/EarnedRightWaterStartTime':
                self.B_EarnedRightWaterStartTime=np.append(self.B_EarnedRightWaterStartTime,Rec[1][1][0])
            elif Rec[0].address=='/AutoLeftWaterStartTime':
                self.B_AutoLeftWaterStartTime=np.append(self.B_AutoLeftWaterStartTime,Rec[1][1][0])
            elif Rec[0].address=='/AutoRightWaterStartTime':
                self.B_AutoRightWaterStartTime=np.append(self.B_AutoRightWaterStartTime,Rec[1][1][0])
            

    def _DeletePreviousLicks(self,Channel2):
        '''Delete licks from the previous session'''
        while not Channel2.msgs.empty():
            Rec=Channel2.receive()
    # get training parameters
    def _GetTrainingParameters(self,win):
        '''Get training parameters'''
        # Iterate over each container to find child widgets and store their values in self
        for container in [win.TrainingParameters, win.centralwidget, win.Opto_dialog, win.Camera_dialog, win.Metadata_dialog]:
            # Iterate over each child of the container that is a QLineEdit or QDoubleSpinBox
            for child in container.findChildren((QtWidgets.QLineEdit, QtWidgets.QDoubleSpinBox,QtWidgets.QSpinBox)):
                if child.objectName()=='qt_spinbox_lineedit' or child.objectName()=='':
                    continue
                # Set an attribute in self with the name 'TP_' followed by the child's object name
                # and store the child's text value
                setattr(self, 'TP_'+child.objectName(), child.text())
            # Iterate over each child of the container that is a QComboBox
            for child in container.findChildren(QtWidgets.QComboBox):
                # Set an attribute in self with the name 'TP_' followed by the child's object name
                # and store the child's current text value
                setattr(self, 'TP_'+child.objectName(), child.currentText())
            # Iterate over each child of the container that is a QPushButton
            for child in container.findChildren(QtWidgets.QPushButton):
                # Set an attribute in self with the name 'TP_' followed by the child's object name
                # and store whether the child is checked or not
                setattr(self, 'TP_'+child.objectName(), child.isChecked())
            
        # Manually attach auto training parameters 
        if hasattr(win, 'AutoTrain_dialog') and win.AutoTrain_dialog.auto_train_engaged:
            self.TP_auto_train_engaged = True
            _curr = win.AutoTrain_dialog.curriculum_in_use
            self.TP_auto_train_curriculum_name = _curr.curriculum_name
            self.TP_auto_train_curriculum_version = _curr.curriculum_version
            self.TP_auto_train_curriculum_schema_version = _curr.curriculum_schema_version
            self.TP_auto_train_stage = win.AutoTrain_dialog.stage_in_use
            self.TP_auto_train_stage_overridden = win.AutoTrain_dialog.checkBox_override_stage.isChecked()
        else:
            self.TP_auto_train_engaged = False
            self.TP_auto_train_curriculum_name = None
            self.TP_auto_train_curriculum_version = None
            self.TP_auto_train_curriculum_schema_version = None
            self.TP_auto_train_stage = None
            self.TP_auto_train_stage_overridden = None


    def _SaveParameters(self):
        for attr_name in dir(self):
            if attr_name.startswith('TP_'):
                # Add the field to the dictionary with the 'TP_' prefix removed
                # Check if the attribute exists in self.Obj
                if attr_name in self.Obj:
                    # Check if the attribute value is already a list
                    if isinstance(self.Obj[attr_name], list):
                        self.Obj[attr_name].append(getattr(self, attr_name))
                    else:
                        # If the attribute value is not a list, create a new list and append to it
                        self.Obj[attr_name] = [self.Obj[attr_name], getattr(self, attr_name)]
                else:
                    # If the attribute does not exist in self.Obj, create a new list and append to it
                    self.Obj[attr_name] = [getattr(self, attr_name)]
        # get the newscale positions
        if hasattr(self.win, 'current_stage'):
            self.B_NewscalePositions.append(self.win.current_stage.get_position())


class NewScaleSerialY():
    '''modified by Xinxin Yin'''
    """
    Cross-platform abstraction layer for New Scale USB Serial devices
    Usage:
        instances = NewScaleSerial.get_instances()
        -> [newScaleSerial1, newScaleSerial2]
        for instance in instances:
            print('serial number = ', instance.get_serial_number())
    """

    def __init__(self, serial_number, pyserial_device=None, usbxpress_device=None):
        self.sn = serial_number
        if pyserial_device:
            self.t = 'pyserial'
            self.io = pyserial_device
        elif usbxpress_device:
            self.t = 'usbxpress'
            self.io = usbxpress_device

    @classmethod
    def get_instances(cls):
        instances = []
        if PLATFORM == 'linux':
            for comport in list_comports():
                if (comport.vid == VID_NEWSCALE):
                    if (comport.pid == PID_NEWSCALE):
                        hwid = comport.hwid
                        serial_number = hwid.split()[2].split('=')[1]
                        instances.append(cls(serial_number,
                                        pyserial_device=Serial(comport.device)))    # does this work?
        elif PLATFORM== 'win32':
            n = USBXpressLib().get_num_devices()
            for i in range(n):
                device = USBXpressDevice(i)
                if (int(device.get_vid(), 16) == VID_NEWSCALE):
                    if (int(device.get_pid(), 16) == PID_NEWSCALE):
                        serial_number = device.get_serial_number()
                        instances.append(cls(serial_number, usbxpress_device=device))   # does this work?
        return instances

    def get_port_name(self):
        if self.t == 'pyserial':
            return self.io.port
        elif self.t == 'usbxpress':
            return 'USBXpress Device'

    def get_serial_number(self):
        return self.sn

    def set_baudrate(self, baudrate):
        if self.t == 'pyserial':
            self.io.baudrate = baudrate
        elif self.t == 'usbxpress':
            self.io.set_baud_rate(baudrate)

    def set_timeout(self, timeout):
        if self.t == 'pyserial':
            self.io.timeout = timeout
        elif self.t == 'usbxpress':
            timeout_ms = int(timeout*1000)
            self.io.set_timeouts(timeout_ms, timeout_ms)

    def write(self, data):
        self.io.write(data)

    def readLine(self):
        if self.t == 'pyserial':
            data = self.io.read_until(b'\r').decode('utf8')
        elif self.t == 'usbxpress':
            data = ''
            while True:
                c = self.io.read(1).decode()
                data += c
                if (c == '\r'): break
        return data

class WorkerSignals(QtCore.QObject):
    '''
    Defines the signals available from a running worker thread.

    Supported signals are:

    finished
        No data

    error
        tuple (exctype, value, traceback.format_exc() )

    result
        object data returned from processing, anything

    progress
        int indicating % progress

    '''
    finished = QtCore.pyqtSignal()
    error = QtCore.pyqtSignal(tuple)
    result = QtCore.pyqtSignal(object)
    progress = QtCore.pyqtSignal(int)


class Worker(QtCore.QRunnable):
    '''
    Worker thread

    Inherits from QRunnable to handler worker thread setup, signals and wrap-up.

    :param callback: The function callback to run on this worker thread. Supplied args and
                     kwargs will be passed through to the runner.
    :type callback: function
    :param args: Arguments to pass to the callback function
    :param kwargs: Keywords to pass to the callback function

    '''
    def __init__(self, fn, *args, **kwargs):
        super(Worker, self).__init__()

        # Store constructor arguments (re-used for processing)
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()
        self.setAutoDelete(False) 
        # Add the callback to our kwargs

    @QtCore.pyqtSlot()
    def run(self):
        '''
        Initialise the runner function with passed args, kwargs.
        '''

        # Retrieve args/kwargs here; and fire processing using them
        try:
            result = self.fn(*self.args, **self.kwargs)
        except ValueError as e:
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))
            logging.error(str(e))
        else:
            self.signals.result.emit(result)  # Return the result of the processing
        finally:
            self.signals.finished.emit()  # Done



class TimerWorker(QtCore.QObject):
    '''
        Worker for photometry timer
    '''
    finished = QtCore.pyqtSignal()
    progress = QtCore.pyqtSignal(int)

    def __init__(self):
        super(TimerWorker, self).__init__()
        self._isRunning=True

    @QtCore.pyqtSlot(int)
    def _Timer(self,Time):
        '''sleep some time'''
        # Emit initial status
        self._isRunning=True
        interval = 1
        num_updates = int(np.floor(Time/interval))
        self.progress.emit(int(Time))

        # Iterate through intervals 
        while num_updates >0:
            time.sleep(interval)
            if not self._isRunning:
                return 
            Time -=interval
            self.progress.emit(int(Time))
            num_updates -= 1
        
        # Sleep the remainder of the time and finish
        time.sleep(Time)
        self.finished.emit()

    def _stop(self):
        # Will halt the timer at the next interval
        self._isRunning=False


class EphysRecording:

    def __init__(self,
                 open_ephys_machine_ip_address,
                 mouse_id):

        """
        Runs an experiment with Open Ephys GUI,

        Parameters
        ----------

        open_ephys_machine_ip_address : str
            IP address of the machine running Open Ephys GUI
        mouse_id : str
            ID of the mouse for this experiment

        Returns
        -------
        None.

        """
        self.open_ephys_machine_ip_address = open_ephys_machine_ip_address
        self.api_endpoint = "http://" + self.open_ephys_machine_ip_address + ":37497/api/"
        self.mouse_id = mouse_id

    def get_status(self):
        '''
        Get the status of the Open Ephys GUI

        '''
        r = requests.get(self.api_endpoint+"status")

        return r.json()
    
    def start_open_ephys_recording(self):
        '''
        Starts recording in Open Ephys GUI
        
        '''
        r1 = requests.put(
		        self.api_endpoint + "recording",
		        json={"prepend_text" : self.mouse_id+ "_"})
        
        r2 = requests.put(
    		    self.api_endpoint + "status",
    		    json={"mode" : "RECORD"}
    		    )
        return r1.json(), r2.json()
    
    def stop_open_ephys_recording(self):
        '''
        Stops recording in Open Ephys GUI
        
        '''

        r = requests.put(
    		self.api_endpoint + "status",
    		json={"mode" : "ACQUIRE"}
    		)

        return r.json()
    
    def get_open_ephys_recording_configuration(self):
        '''
        Get the recording configuration from Open Ephys GUI
        
        '''
        r = requests.get(self.api_endpoint+"recording")

        return r.json()
