import random
import traceback
import math
import time
import sys
from sys import platform as PLATFORM
from datetime import datetime
import logging

import numpy as np
from itertools import accumulate
from serial.tools.list_ports import comports as list_comports
from PyQt5 import QtWidgets
from PyQt5 import QtCore


if PLATFORM == 'win32':
    from newscale.usbxpress import USBXpressLib, USBXpressDevice
VID_NEWSCALE = 0x10c4
PID_NEWSCALE = 0xea61


class GenerateTrials():
    def __init__(self,win):
        self.win=win
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
        self.B_TrialEndTime=np.array([]).astype(float)
        self.B_GoCueTime=np.array([]).astype(float)
        self.B_TrialStartTimeHarp=np.array([]).astype(float)
        self.B_DelayStartTimeHarp=np.array([]).astype(float)
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
        self.B_RewardOutcomeTime=np.array([]).astype(float)
        self.B_LaserOnTrial=[] # trials with laser on
        self.B_SimulationSession=[]
        self.B_LaserAmplitude=[]
        self.B_LaserDuration=[]
        self.B_SelectedCondition=[]
        self.B_AutoWaterTrial=np.array([[],[]]).astype(bool) # to indicate if it is a trial with outo water.
        self.B_NewscalePositions=[]
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
        # check block transition
        self._CheckBlockTransition()
        # Get reward probability and other trial related parameters
        self._SelectTrainingParameter()
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
        # finish to generate the next trial
        self.GeneFinish=1
    def _PerformOptogenetics(self,Channel4):
        '''Optogenetics section to generate optogenetics parameters and send waveform to Bonsai'''
        try:
            if self.TP_OptogeneticsB=='on': # optogenetics is turned on
                # select the current optogenetics condition
                self._SelectOptogeneticsCondition()
                if self.SelctedCondition!=0: 
                    self.LaserOn=1
                    self.B_LaserOnTrial.append(self.LaserOn) 
                    # generate the optogenetics waveform of the next trial
                    self._GetLaserWaveForm()
                else:
                    # this is the control trial
                    self.LaserOn=0
                    self.B_LaserOnTrial.append(self.LaserOn) 
                    self.B_LaserAmplitude.append([0,0])
                    self.B_LaserDuration.append(0)
                    self.B_SelectedCondition.append(0)
                    self.CurrentLaserAmplitude=[0,0]
            else:
                # optogenetics is turned off
                self.LaserOn=0
                self.B_LaserOnTrial.append(self.LaserOn)
                self.B_LaserAmplitude.append([0,0])
                self.B_LaserDuration.append(0)
                self.B_SelectedCondition.append(0)
                self.CurrentLaserAmplitude=[0,0]
        except Exception as e:
            # optogenetics is turned off
            self.LaserOn=0
            self.B_LaserOnTrial.append(self.LaserOn)
            self.B_LaserAmplitude.append([0,0]) # corresponding to two locations
            self.B_LaserDuration.append(0) # corresponding to two locations
            self.B_SelectedCondition.append(0)
            self.CurrentLaserAmplitude=[0,0]
            # Catch the exception and print error information
            logging.error(str(e))

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
            self.win.WarningLabelRewardN.setStyleSheet("color: red;")
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

    def _SelectTrainingParameter(self):
        '''Select the training parameter of the next trial'''
        # determine the reward probability of the next trial based on tasks
        if (self.TP_Task in ['Coupled Baiting','Coupled Without Baiting','RewardN']) and any(self.B_ANewBlock==1):
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
        elif (self.TP_Task in ['Uncoupled Baiting','Uncoupled Without Baiting'])  and any(self.B_ANewBlock==1):
            # get the reward probabilities pool
            for i in range(len(self.B_ANewBlock)):
                if self.B_ANewBlock[i]==1:
                    input_string=self.win.UncoupledReward.text()
                    # remove any square brackets and spaces from the string
                    input_string = input_string.replace('[','').replace(']','').replace(',', ' ')
                    # split the remaining string into a list of individual numbers
                    num_list = input_string.split()
                    # convert each number in the list to a float
                    num_list = [float(num) for num in num_list]
                    # create a numpy array from the list of numbers
                    RewardProbPool=np.array(num_list)
                    self.RewardProbPoolUncoupled=RewardProbPool.copy()
                    # exclude the previous reward probabilities
                    if self.B_RewardProHistory.size!=0:
                        RewardProbPool=RewardProbPool[RewardProbPool!=self.B_RewardProHistory[i,-1]]
                    # exclude pairs with small reward size (temporarily)
                    if (i==0 and self.B_CurrentRewardProb[1]==0.1) or (i==1 and self.B_CurrentRewardProb[0]==0.1):
                            RewardProbPool=RewardProbPool[RewardProbPool!=0.1]
                    # get the reward probabilities of the current block
                    self.B_CurrentRewardProb[i]=RewardProbPool[random.choice(range(np.shape(RewardProbPool)[0]))]
                    # "if one spout was assigned a reward probability greater than or equal to the reward probability of the other spout for 3 consecutive blocks, the probability of that spout was set to 0.1 to encourage switching behavior and limit the creation of a direction bias"
                    if np.shape(self.BlockLenHistory[i])[0]>=3:
                        total_trial=np.sum(self.BlockLenHistory[i][-3:])
                        if np.all(self.B_RewardProHistory[i][-total_trial:]>self.B_RewardProHistory[1-i][-total_trial:]):
                            self.B_CurrentRewardProb[i]=0.1
                    # randomly draw a block length between Min and Max
                    if self.TP_Randomness=='Exponential':
                        self.BlockLen = np.array(int(np.random.exponential(float(self.TP_BlockBeta),1)+float(self.TP_BlockMin)))
                    elif self.TP_Randomness=='Even':
                        self.BlockLen=  np.array(np.random.randint(float(self.TP_BlockMin), float(self.TP_BlockMax)+1))
                    if self.BlockLen>float(self.TP_BlockMax):
                        self.BlockLen=int(self.TP_BlockMax)
                    self.BlockLenHistory[i].append(self.BlockLen)
                    self.B_ANewBlock[i]=0

                    
        self.B_RewardProHistory=np.append(self.B_RewardProHistory,self.B_CurrentRewardProb.reshape(self.B_LickPortN,1),axis=1)
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

    def _CheckBlockTransition(self):
        '''Check if we should perform a block change for the next trial. 
        If you change the block length parameter, it only takes effect 
        after the current block is completed'''
        # Check advanced block swith
        self._CheckAdvancedBlockSwitch()
        # transition to the next block when NextBlock button is clicked
        if self.TP_NextBlock:
            self.B_ANewBlock[:]=1
            self.win.NextBlock.setChecked(False)
            self.win.NextBlock.setStyleSheet("background-color : none")
            self._update_block_len([0,1])
        # decide if block transition will happen at the next trial
        for i in range(len(self.B_ANewBlock)):
            if self.B_CurrentTrialN+1>=sum(self.BlockLenHistory[i]):
                self.B_ANewBlock[i]=1
        if not self.TP_NextBlock:
            # min rewards to perform transition
            if self.B_CurrentTrialN>=0:
                # get the rewarded trial number of the current finished trial.
                self._GetCurrentBlockReward(1,CountAutoWater=1,UpdateBlockLen=1)
            else:
                self.AllRewardThisBlock=-1
                self.BS_RewardedTrialN_CurrentBlock=[0,0]
            if self.TP_Task in ['Coupled Baiting','Coupled Without Baiting','RewardN']:
                if np.all(self.B_ANewBlock==1) and self.AllRewardThisBlock!=-1:
                    if self.AllRewardThisBlock<float(self.TP_BlockMinReward) or self.AdvancedBlockSwitchPermitted==0:
                        # do not switch
                        self.B_ANewBlock=np.zeros_like(self.B_ANewBlock)
                        self._update_block_len(range(len(self.B_ANewBlock)))
            elif self.TP_Task in ['Uncoupled Baiting','Uncoupled Without Baiting']:
                for i in range(len(self.B_ANewBlock)):
                    if self.B_ANewBlock[i]==1 and (self.BS_RewardedTrialN_CurrentBlock[i]<float(self.TP_BlockMinReward) or self.AdvancedBlockSwitchPermitted==0) and self.AllRewardThisBlock!=-1:
                        # do not switch
                        self.B_ANewBlock[i]=0
                        self._update_block_len([i])
    def _update_block_len(self,ind):
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
        
    def _CheckAdvancedBlockSwitch(self):
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

    def _GetCurrentBlockReward(self,NewTrialRewardOrder,CountAutoWater=0,UpdateBlockLen=0):
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
                    self._update_block_len([i])
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
        
        TP_LeftValue_volume=[]
        n=0
        for s in self.Obj['TP_LeftValue_volume'][0:len(Ind)]:
            try:
                if self.B_AutoWaterTrial[0][n]==1:
                    multiplier=float(self.Obj['TP_Multiplier'][n])
                else:
                    multiplier=1
                float_value = float(s)*multiplier
                TP_LeftValue_volume.append(float_value)
            except ValueError as e:
                logging.error(str(e))
                TP_LeftValue_volume.append(0)
            n=n+1
        TP_LeftValue_volume=np.array(TP_LeftValue_volume)
        TP_LeftValue_volume=TP_LeftValue_volume[0:len(B_RewardedHistory[0])]

        TP_RightValue_volume=[]
        n=0
        for s in self.Obj['TP_RightValue_volume'][0:len(Ind)]:
            try:
                if self.B_AutoWaterTrial[1][n]==1:
                    multiplier=float(self.Obj['TP_Multiplier'][n])
                else:
                    multiplier=1
                float_value = float(s)*multiplier
                TP_RightValue_volume.append(float_value)
            except ValueError as e:
                logging.error(str(e))
                TP_RightValue_volume.append(0)
            n=n+1
        TP_RightValue_volume=np.array(TP_RightValue_volume)
        TP_RightValue_volume=TP_RightValue_volume[0:len(B_RewardedHistory[1])]

        self.BS_TotalReward=np.sum((B_RewardedHistory[0]==True).astype(int)*TP_LeftValue_volume+(B_RewardedHistory[1]==True).astype(int)*TP_RightValue_volume)
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
            self._GetCurrentBlockReward(1)
        else:
            # show next trial
            self._GetCurrentBlockReward(0)
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
            CurrentStart_Delay=(self.B_TrialStartTime[i],self.B_DelayStartTime[i])
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
                self.win.ShowRewardPairs.setText('Reward pairs: '+str(np.round(self.RewardProb,2))+'\n\n'+'Current pair: '+str(np.round(self.B_RewardProHistory[:,self.B_CurrentTrialN],2)))
            elif (self.TP_Task in ['Uncoupled Baiting','Uncoupled Without Baiting']):
                self.win.ShowRewardPairs.setText('Reward pairs: '+str(np.round(self.RewardProbPoolUncoupled,2))+'\n\n'+'Current pair: '+str(np.round(self.B_RewardProHistory[:,self.B_CurrentTrialN],2)))
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
                        'Earned Reward (ul): '+ str(self.BS_RewardN)+' : '+str(np.round(self.BS_TotalReward,3)) +'\n'
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
                        'Earned Reward (ul): '+ str(self.BS_RewardN)+' : '+str(np.round(self.BS_TotalReward,3)) +'\n'
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
                        'Earned Reward (ul): '+ str(self.BS_RewardN)+' : '+str(np.round(self.BS_TotalReward,3)) +'\n'
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
            # newscale positions
            if hasattr(self.win, 'current_stage'):
                self.win._GetPositions()
    def _CheckStop(self):
        '''Stop if there are many ingoral trials or if the maximam trial is exceeded MaxTrial'''
        StopIgnore=int(self.TP_StopIgnores)-1
        MaxTrial=int(self.TP_MaxTrial)-2 # trial number starts from 0
        MaxTime=float(self.TP_MaxTime)*60 # convert minutes to seconds
        if hasattr(self, 'BS_CurrentRunningTime'): 
            pass
        else:
            self.BS_CurrentRunningTime=0

        if np.shape(self.B_AnimalResponseHistory)[0]>=StopIgnore:
            if np.all(self.B_AnimalResponseHistory[-StopIgnore:]==2):
                self.Stop=1
                self.win.WarningLabelStop.setText('Stop because ignore trials exceed or equal: '+self.TP_StopIgnores)
                self.win.WarningLabelStop.setStyleSheet("color: red;")
            else:
                self.Stop=0
                self.win.WarningLabelStop.setText('')
                self.win.WarningLabelStop.setStyleSheet("color: gray;")
        elif self.B_CurrentTrialN>MaxTrial: 
            self.Stop=1
            self.win.WarningLabelStop.setText('Stop because maximum trials exceed or equal: '+self.TP_MaxTrial)
            self.win.WarningLabelStop.setStyleSheet("color: red;")
        elif self.BS_CurrentRunningTime>MaxTime:
            self.Stop=1
            self.win.WarningLabelStop.setText('Stop because running time exceeds or equals: '+self.TP_MaxTime+'m')
            self.win.WarningLabelStop.setStyleSheet("color: red;")
        else:
            self.Stop=0
            self.win.WarningLabelStop.setText('')
            self.win.WarningLabelStop.setStyleSheet("color: gray;")
        if  self.Stop==1:           
            self.win.Start.setStyleSheet("background-color : none")
            self.win.Start.setChecked(False)
    def _CheckAutoWater(self):
        '''Check if it should be an auto water trial'''
        if self.TP_AutoReward:
            UnrewardedN=int(self.TP_Unrewarded)
            IgnoredN=int(self.TP_Ignored)
            if UnrewardedN<=0:
                self.CurrentAutoReward=1
                self.win.WarningLabelAutoWater.setText('Auto water because unrewarded trials exceed: '+self.TP_Unrewarded)
                self.win.WarningLabelAutoWater.setStyleSheet("color: red;")
            elif  IgnoredN <=0:
                self.win.WarningLabelAutoWater.setText('Auto water because ignored trials exceed: '+self.TP_Ignored)
                self.win.WarningLabelAutoWater.setStyleSheet("color: red;")
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
                        self.win.WarningLabelAutoWater.setStyleSheet("color: red;")
                    elif (np.all(B_RewardedHistory[0][-UnrewardedN:]==False) and np.all(B_RewardedHistory[1][-UnrewardedN:]==False) and np.shape(B_RewardedHistory[0])[0]>=UnrewardedN):
                        self.CurrentAutoReward=1
                        self.win.WarningLabelAutoWater.setText('Auto water because unrewarded trials exceed: '+self.TP_Unrewarded)
                        self.win.WarningLabelAutoWater.setStyleSheet("color: red;")
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
        self.CLP_Color=eval('self.TP_Laser_'+N)
        self.CLP_Location=eval('self.TP_Location_'+N)
        self.CLP_LaserPowerLeft=eval('self.TP_LaserPowerLeft_'+N)
        self.CLP_LaserPowerRight=eval('self.TP_LaserPowerRight_'+N)
        self.CLP_Duration=float(eval('self.TP_Duration_'+N))
        self.CLP_Protocol=eval('self.TP_Protocol_'+N)
        if not self.CLP_Protocol=='Constant':
            self.CLP_Frequency=float(eval('self.TP_Frequency_'+N))
        self.CLP_RampingDown=float(eval('self.TP_RD_'+N))
        self.CLP_PulseDur=eval('self.TP_PulseDur_'+N)
        self.CLP_LaserStart=eval('self.TP_LaserStart_'+N)
        self.CLP_OffsetStart=float(eval('self.TP_OffsetStart_'+N))
        self.CLP_LaserEnd=eval('self.TP_LaserEnd_'+N)
        self.CLP_OffsetEnd=float(eval('self.TP_OffsetEnd_'+N)) # negative, backward; positive forward
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
                self.win.WarningLabel.setStyleSheet("color: red;")
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
            if self.CLP_RampingDown>0:
                if self.CLP_RampingDown>self.CLP_CurrentDuration:
                    self.win.WarningLabel.setText('Ramping down is longer than the laser duration!')
                    self.win.WarningLabel.setStyleSheet("color: red;")
                else:
                    Constant=np.ones(int((self.CLP_CurrentDuration-self.CLP_RampingDown)*self.CLP_SampleFrequency))
                    RD=np.arange(1,0, -1/(np.shape(self.my_wave)[0]-np.shape(Constant)[0]))
                    RampingDown = np.concatenate((Constant, RD), axis=0)
                    self.my_wave=self.my_wave*RampingDown
            # add offset
            if self.CLP_OffsetStart>0:
                OffsetPoints=int(self.CLP_SampleFrequency*self.CLP_OffsetStart)
                Offset=np.zeros(OffsetPoints)
                self.my_wave=np.concatenate((Offset,self.my_wave),axis=0)
            self.my_wave=np.append(self.my_wave,[0,0])

        elif self.CLP_Protocol=='Pulse':
            if self.CLP_PulseDur=='NA':
                self.win.WarningLabel.setText('Pulse duration is NA!')
                self.win.WarningLabel.setStyleSheet("color: red;")
                self.CLP_PulseDur=0
            elif self.CLP_Frequency=='':
                self.win.WarningLabel.setText('Pulse frequency is NA!')
                self.win.WarningLabel.setStyleSheet("color: red;")
                self.CLP_Frequency=0
            else:
                self.CLP_PulseDur=float(self.CLP_PulseDur)
                PointsEachPulse=int(self.CLP_SampleFrequency*self.CLP_PulseDur)
                PulseIntervalPoints=int(1/self.CLP_Frequency*self.CLP_SampleFrequency-PointsEachPulse)
                if PulseIntervalPoints<0:
                    self.win.WarningLabel.setText('Pulse frequency and pulse duration are not compatible!')
                    self.win.WarningLabel.setStyleSheet("color: red;")
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
                    self.win.WarningLabel.setStyleSheet("color: red;")
                    return
                self.my_wave=np.concatenate((self.my_wave, EachPulse), axis=0)
                self.my_wave=np.concatenate((self.my_wave, np.zeros(TotalPoints-np.shape(self.my_wave)[0])), axis=0)
                # add offset
                if self.CLP_OffsetStart>0:
                    OffsetPoints=int(self.CLP_SampleFrequency*self.CLP_OffsetStart)
                    Offset=np.zeros(OffsetPoints)
                    self.my_wave=np.concatenate((Offset,self.my_wave),axis=0)
                self.my_wave=np.append(self.my_wave,[0,0])
        elif self.CLP_Protocol=='Constant':
            resolution=self.CLP_SampleFrequency*self.CLP_CurrentDuration # how many datapoints to generate
            self.my_wave=Amplitude*np.ones(int(resolution))
            if self.CLP_RampingDown>0:
            # add ramping down
                if self.CLP_RampingDown>self.CLP_CurrentDuration:
                    self.win.WarningLabel.setText('Ramping down is longer than the laser duration!')
                    self.win.WarningLabel.setStyleSheet("color: red;")
                else:
                    Constant=np.ones(int((self.CLP_CurrentDuration-self.CLP_RampingDown)*self.CLP_SampleFrequency))
                    RD=np.arange(1,0, -1/(np.shape(self.my_wave)[0]-np.shape(Constant)[0]))
                    RampingDown = np.concatenate((Constant, RD), axis=0)
                    self.my_wave=self.my_wave*RampingDown
            # add offset
            if self.CLP_OffsetStart>0:
                OffsetPoints=int(self.CLP_SampleFrequency*self.CLP_OffsetStart)
                Offset=np.zeros(OffsetPoints)
                self.my_wave=np.concatenate((Offset,self.my_wave),axis=0)
            self.my_wave=np.append(self.my_wave,[0,0])
        else:
            self.win.WarningLabel.setText('Unidentified optogenetics protocol!')
            self.win.WarningLabel.setStyleSheet("color: red;")

        '''
        # test
        import matplotlib.pyplot as plt
        plt.plot(np.arange(0, length, length / resolution), self.my_wave)   
        plt.show()
        '''
    def _GetLaserAmplitude(self):
        '''the voltage amplitude dependens on Protocol, Laser Power, Laser color, and the stimulation locations<>'''
        self.CurrentLaserAmplitude=[0,0]
        if self.CLP_Location=='Left':
            if self.CLP_LaserPowerLeft=='':
                self.win.WarningLabel.setText('No amplitude for left laser defined!')
                self.win.WarningLabel.setStyleSheet("color: red;")
            else:
                LaserPowerAmpLeft=eval(self.CLP_LaserPowerLeft)
                self.CurrentLaserAmplitude=[LaserPowerAmpLeft[0],0]
        elif self.CLP_Location=='Right':
            if self.CLP_LaserPowerRight=='':
                self.win.WarningLabel.setText('No amplitude for right laser defined!')
                self.win.WarningLabel.setStyleSheet("color: red;")
            else:
                LaserPowerAmpRight=eval(self.CLP_LaserPowerRight)
                self.CurrentLaserAmplitude=[0,LaserPowerAmpRight[0]]
        elif self.CLP_Location=='Both':
            if  self.CLP_LaserPowerLeft=='' or self.CLP_Location=='Right':
                self.win.WarningLabel.setText('No amplitude for left or right laser defined!')
                self.win.WarningLabel.setStyleSheet("color: red;")
            else:
                LaserPowerAmpLeft=eval(self.CLP_LaserPowerLeft)
                LaserPowerAmpRight=eval(self.CLP_LaserPowerRight)
                self.CurrentLaserAmplitude=[LaserPowerAmpLeft[0],LaserPowerAmpRight[0]]
        else:
            self.win.WarningLabel.setText('No stimulation location defined!')
            self.win.WarningLabel.setStyleSheet("color: red;")
        self.B_LaserAmplitude.append(self.CurrentLaserAmplitude)

    def _SelectOptogeneticsCondition(self):
        '''To decide if this should be an optogenetics trial'''
        # condition should be taken into account in the future
        ConditionsOn=[]
        Probabilities=[]
        for attr_name in dir(self):
            if attr_name.startswith('TP_Laser_'):
                if getattr(self, attr_name) !='NA':
                    parts = attr_name.split('_')
                    ConditionsOn.append(parts[-1])
                    Probabilities.append(float(eval('self.TP_Probability_'+parts[-1])))
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
        self.B_SelectedCondition.append(self.SelctedCondition)

    def _InitiateATrial(self,Channel1,Channel4):
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
                    self.win.WarningLabel.setStyleSheet("color: red;")
                # send the waveform size
                Channel1.Location1_Size(int(self.Location1_Size))
                Channel1.Location2_Size(int(self.Location2_Size))
                for i in range(len(self.CurrentLaserAmplitude)): # locations of these waveforms
                    eval('Channel4.WaveForm' + str(1)+'_'+str(i+1)+'('+'str('+'self.WaveFormLocation_'+str(i+1)+'.tolist()'+')[1:-1]'+')')
                FinishOfWaveForm=Channel4.receive()  
            else:
                Channel1.PassGoCue(int(0))
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
            if self.win.OptogeneticsB.currentText()=='on':
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
                    if any(self.B_RewardedHistory[:,-1]==1):# win
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
        self.B_TrialEndTimeHarp=np.append(self.B_TrialEndTimeHarp,TrialEndTimeHarp)
        self.B_GoCueTimeBehaviorBoard=np.append(self.B_GoCueTimeBehaviorBoard,GoCueTimeBehaviorBoard)
        self.B_GoCueTimeSoundCard=np.append(self.B_GoCueTimeBehaviorBoard,GoCueTimeBehaviorBoard)
        self.B_DOPort2Output=np.append(self.B_DOPort2Output,B_DOPort2Output)
        # get the event time
        self.B_TrialStartTime=np.append(self.B_TrialStartTime,TrialStartTime)
        self.B_DelayStartTime=np.append(self.B_DelayStartTime,DelayStartTime)
        self.B_TrialEndTime=np.append(self.B_TrialEndTime,TrialEndTime)
        self.B_GoCueTime=np.append(self.B_GoCueTime,GoCueTime)
        self.B_RewardOutcomeTime=np.append(self.B_RewardOutcomeTime,RewardOutcomeTime)
        self.GetResponseFinish=1

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
            DelayStartTimeHarp=-999 # -999 means a placeholder
            DelayStartTime=-999
        elif self.CurrentStartType==1:
            ReceiveN=11
        N=0
        for i in range(ReceiveN):
            Rec=Channel1.receive()
            if Rec[0].address=='/TrialStartTime':
                TrialStartTime=Rec[1][1][0]
            elif Rec[0].address=='/DelayStartTime':
                DelayStartTime=Rec[1][1][0]
            elif Rec[0].address=='/GoCueTime':
                GoCueTime=Rec[1][1][0]
            elif Rec[0].address=='/RewardOutcomeTime':
                RewardOutcomeTime=Rec[1][1][0]
            elif Rec[0].address=='/RewardOutcome':
                TrialOutcome=Rec[1][1][0]
                if TrialOutcome=='NoResponse':
                    self.B_AnimalCurrentResponse=2
                    self.B_CurrentRewarded[0]=False
                    self.B_CurrentRewarded[1]=False
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
                self.B_RewardedHistory=np.append(self.B_RewardedHistory,self.B_CurrentRewarded,axis=1)
                self.B_AnimalResponseHistory=np.append(self.B_AnimalResponseHistory,self.B_AnimalCurrentResponse)
            elif Rec[0].address=='/TrialEndTime':
                TrialEndTime=Rec[1][1][0]
            elif Rec[0].address=='/GoCueTimeSoundCard':
                # give auto water after Co cue
                if self.CurrentAutoRewardTrial[0]==1:
                    Channel3.ManualWater_Left(int(1))
                if self.CurrentAutoRewardTrial[1]==1:
                    Channel3.ManualWater_Right(int(1))
                GoCueTimeSoundCard=Rec[1][1][0]
            elif Rec[0].address=='/DOPort2Output': #this port is used to trigger optogenetics aligned to Go cue
                B_DOPort2Output=Rec[1][1][0]
                self.B_DOPort2Output=np.append(self.B_DOPort2Output,B_DOPort2Output)
            elif Rec[0].address=='/ITIStartTimeHarp':
                TrialStartTimeHarp=Rec[1][1][0]
            elif Rec[0].address=='/BehaviorEvent':
                if self.CurrentStartType==1:
                    if N==0:
                        DelayStartTimeHarp=Rec[1][1][0]
                    elif N==1:
                        GoCueTimeBehaviorBoard=Rec[1][1][0]
                    elif N==2:
                        TrialEndTimeHarp=Rec[1][1][0]
                elif self.CurrentStartType==3:
                    if N==0:
                        GoCueTimeBehaviorBoard=Rec[1][1][0]
                    elif N==1:
                        TrialEndTimeHarp=Rec[1][1][0]
                N=N+1
        # get the event harp time
        self.B_TrialStartTimeHarp=np.append(self.B_TrialStartTimeHarp,TrialStartTimeHarp)
        self.B_DelayStartTimeHarp=np.append(self.B_DelayStartTimeHarp,DelayStartTimeHarp)
        self.B_TrialEndTimeHarp=np.append(self.B_TrialEndTimeHarp,TrialEndTimeHarp)
        self.B_GoCueTimeBehaviorBoard=np.append(self.B_GoCueTimeBehaviorBoard,GoCueTimeBehaviorBoard)
        self.B_GoCueTimeSoundCard=np.append(self.B_GoCueTimeSoundCard,GoCueTimeSoundCard)
        # get the event time
        self.B_TrialStartTime=np.append(self.B_TrialStartTime,TrialStartTime)
        self.B_DelayStartTime=np.append(self.B_DelayStartTime,DelayStartTime)
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

    def _GetLicks(self,Channel2):
        '''Get licks and reward delivery time'''
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
    def _DeletePreviousLicks(self,Channel2):
        '''Delete licks from the previous session'''
        while not Channel2.msgs.empty():
            Rec=Channel2.receive()
    # get training parameters
    def _GetTrainingParameters(self,win):
        '''Get training parameters'''
        # Iterate over each container to find child widgets and store their values in self
        for container in [win.TrainingParameters, win.centralwidget, win.Opto_dialog]:
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
        # log folder
        try:
            self.TP_log_folder=win.Ot_log_folder
        except Exception as e:
            logging.error(str(e))

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
