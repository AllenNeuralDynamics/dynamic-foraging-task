
import random, traceback, math,time
from datetime import datetime
import numpy as np
from itertools import accumulate
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import *
class GenerateTrials():
    def __init__(self,win):
        self.win=win
        self.B_RewardFamilies=self.win.RewardFamilies
        #self.B_RewardFamilies = [[[float(x) for x in y] for y in z] for z in self.B_RewardFamilies]
        #self.B_RewardFamilies = np.array(self.B_RewardFamilies)
        self.B_CurrentTrialN=-1 # trial number starts from 0; Update when trial starts
        self.B_LickPortN=2
        self.B_ANewBlock=np.array([1,1]).astype(int)
        self.B_RewardProHistory=np.array([[],[]]).astype(int)
        self.BlockLenHistory=[[],[]]
        self.B_BaitHistory=np.array([[],[]]).astype(bool)
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
        self.B_LeftRewardDeliveryTime=np.array([]).astype(float)
        self.B_RightRewardDeliveryTime=np.array([]).astype(float)
        self.B_RewardOutcomeTime=np.array([]).astype(float)
        self.B_LaserOnTrial=[] # trials with laser on
        self.B_LaserAmplitude=[]
        self.B_LaserDuration=[]
        self.B_SelectedCondition=[]
        self.B_AutoWaterTrial=[] # to indicate if it is a trial with outo water.
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
        #self.B_LaserTrialNum=[] # B_LaserAmplitude, B_LaserDuration, B_SelectedCondition have values only on laser on trials, so we need to store the laser trial number
        
        self.Obj={}
        # get all of the training parameters of the current trial
        self._GetTrainingParameters(self.win)
    def _GenerateATrial(self,Channel4):
        if self.win.UpdateParameters==1:
            # get all of the training parameters of the current trial
            self._GetTrainingParameters(self.win)
        # save all of the parameters in each trial
        self._SaveParameters()
        # get licks information. Starting from the second trial, and counting licks of the last completed trial
        if self.B_CurrentTrialN>=1: 
            self._LickSta([self.B_CurrentTrialN-1])
        # get basic information
        if self.B_CurrentTrialN>=0: 
            self._GetBasic()
        # check block transition
        self._CheckBlockTransition()
        # Get reward probability and other trial related parameters
        self._SelectTrainingParameter()
        # Show session/trial related information
        self._ShowInformation()
        # to decide if it's an auto water trial. will give water in _GetAnimalResponse
        self._CheckAutoWater()
        # to decide if we should stop the session
        self._CheckStop()
        # optogenetics section
        self._PerformOptogenetics()
        # finish to generate the next trial
        self.GeneFinish=1

    def _PerformOptogenetics(self):
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
                    # send the waveform to Bonsai temporarily stored for using in the next trial
                    #WaveForm_Number_Location
                    for i in range(len(self.CurrentLaserAmplitude)): # locations of these waveforms
                        if self.CurrentLaserAmplitude[i]!=0:
                            #eval('Channel4.WaveForm' + str(self.NextWaveForm)+'_'+str(i+1)+'(np.array('+'self.WaveFormLocation_'+str(i+1)+',\'b\''+'))')
                            #eval('Channel4.WaveForm' + str(self.NextWaveForm)+'_'+str(i+1)+'('+'self.WaveFormLocation_'+str(i+1)+')')
                            eval('Channel4.WaveForm' + str(self.NextWaveForm)+'_'+str(i+1)+'('+'str('+'self.WaveFormLocation_'+str(i+1)+'.tolist()'+')[1:-1]'+')')
                            #FinishOfWaveForm=Channel4.receive()
                            setattr(self, f"Location{i+1}_Size", getattr(self, f"WaveFormLocation_{i+1}").size)
                        else:
                            setattr(self, f"Location{i+1}_Size", 100) # arbitrary number 
                            
                    if self.NextWaveForm==1:
                        self.NextWaveForm=2
                    elif self.NextWaveForm==2:
                        self.NextWaveForm=1
                    # finish of this sectiom
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
            print("An error occurred:")
            print(traceback.format_exc())

    def _SelectTrainingParameter(self):
        '''Select the training parameter of the next trial'''
        # determine the reward probability of the next trial based on tasks
        if (self.TP_Task in ['Coupled Baiting','Coupled Without Baiting']) and any(self.B_ANewBlock==1):
            self.RewardPairs=self.B_RewardFamilies[int(self.TP_RewardFamily)-1][:int(self.TP_RewardPairsN)]
            self.RewardProb=np.array(self.RewardPairs)/np.expand_dims(np.sum(self.RewardPairs,axis=1),axis=1)*float(self.TP_BaseRewardSum)
            # get the reward probabilities pool
            RewardProbPool=np.append(self.RewardProb,np.fliplr(self.RewardProb),axis=0)
            # exclude the previous reward probabilities
            if self.B_RewardProHistory.size!=0:
                RewardProbPool=RewardProbPool[RewardProbPool!=self.B_RewardProHistory[:,-1]]
                RewardProbPool=RewardProbPool.reshape(int(RewardProbPool.size/self.B_LickPortN),self.B_LickPortN)
            # get the reward probabilities of the current block
            self.B_CurrentRewardProb=RewardProbPool[random.choice(range(np.shape(RewardProbPool)[0]))]
            # forced change of block identity (L->R; R->L)
            if self.B_RewardProHistory.shape[1]>0:
                if (self.B_CurrentRewardProb[0]>self.B_CurrentRewardProb[1])==(self.B_RewardProHistory[0,-1]>self.B_RewardProHistory[1,-1]):
                    self.B_CurrentRewardProb=self.B_CurrentRewardProb[::-1]
            # randomly draw a block length between Min and Max
            self.BlockLen = np.array(int(np.random.exponential(float(self.TP_BlockBeta),1)+float(self.TP_BlockMin)))
            if self.BlockLen>float(self.TP_BlockMax):
                self.BlockLen=int(self.TP_BlockMax)
            for i in range(len(self.B_ANewBlock)):
                self.BlockLenHistory[i].append(self.BlockLen)
            self.B_ANewBlock=np.array([0,0])
        elif (self.TP_Task in ['Uncoupled Baiting','Uncoupled Without Baiting'])  and any(self.B_ANewBlock==1):
            # get the reward probabilities pool
            for i in range(len(self.B_ANewBlock)):
                if self.B_ANewBlock[i]==1:
                    #RewardProbPool=np.append(self.RewardProb,np.fliplr(self.RewardProb),axis=0)
                    #RewardProbPool=RewardProbPool[:,i]
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
                    if i==1:
                        if self.B_CurrentRewardProb[0]==0.1:
                            RewardProbPool=RewardProbPool[RewardProbPool!=0.1]
                    # get the reward probabilities of the current block
                    self.B_CurrentRewardProb[i]=RewardProbPool[random.choice(range(np.shape(RewardProbPool)[0]))]
                    # randomly draw a block length between Min and Max
                    self.BlockLen = np.array(int(np.random.exponential(float(self.TP_BlockBeta),1)+float(self.TP_BlockMin)))
                    if self.BlockLen>float(self.TP_BlockMax):
                        self.BlockLen=int(self.TP_BlockMax)
                    self.BlockLenHistory[i].append(self.BlockLen)
                    self.B_ANewBlock[i]=0
        self.B_RewardProHistory=np.append(self.B_RewardProHistory,self.B_CurrentRewardProb.reshape(self.B_LickPortN,1),axis=1)
        # get the ITI time and delay time
        self.CurrentITI = float(np.random.exponential(float(self.TP_ITIBeta),1)+float(self.TP_ITIMin))
        if self.CurrentITI>float(self.TP_ITIMax):
            self.CurrentITI=float(self.TP_ITIMax)
        self.CurrentDelay = float(np.random.exponential(float(self.TP_DelayBeta),1)+float(self.TP_DelayMin))
        if self.CurrentDelay>float(self.TP_DelayMax):
            self.CurrentDelay=float(self.TP_DelayMax)
        self.B_ITIHistory.append(self.CurrentITI)
        self.B_DelayHistory.append(self.CurrentDelay)
        self.B_ResponseTimeHistory.append(float(self.TP_ResponseTime))

    def _CheckBlockTransition(self):
        '''Check if we should perform a block change for the next trial. 
        If you change the block length parameter, it only takes effect 
        after the current block is completed'''
        # transition to the next block when NextBlock button is clicked
        if self.TP_NextBlock:
            self.B_ANewBlock[:]=1
            self.win.NextBlock.setChecked(False)
            self.win.NextBlock.setStyleSheet("background-color : none")
            # update the BlockLenHistory
            for i in range(len(self.B_ANewBlock)):
                if len(self.BlockLenHistory[i])==1:
                    self.BlockLenHistory[i][-1]=self.B_CurrentTrialN+1
                elif len(self.BlockLenHistory[i])>1:
                    self.BlockLenHistory[i][-1]=self.B_CurrentTrialN+1-sum(self.BlockLenHistory[i][:-1])
        # decide if block transition will happen at the next trial
        for i in range(len(self.B_ANewBlock)):
            if self.B_CurrentTrialN+1>=sum(self.BlockLenHistory[i]):
                self.B_ANewBlock[i]=1

    def _GetBasic(self):
        '''Get basic session information'''
        if len(self.B_TrialEndTime)>=1:
            self.BS_CurrentRunningTime=self.B_TrialEndTime[-1]-self.B_TrialStartTime[0]# time interval between the recent trial end and first trial start
        else:
            self.BS_CurrentRunningTime=0
        self.BS_AllTrialN=np.shape(self.B_AnimalResponseHistory)[0]
        self.BS_FinisheTrialN=np.sum(self.B_AnimalResponseHistory!=2)
        self.BS_RespondedRate=self.BS_FinisheTrialN/self.BS_AllTrialN
        self.BS_RewardTrialN=np.sum(self.B_RewardedHistory==True)
        self.BS_TotalReward=float(self.BS_RewardTrialN)*float(self.win.WaterPerRewardedTrial)
        self.BS_LeftRewardTrialN=np.sum(self.B_RewardedHistory[0]==True)
        self.BS_RightRewardTrialN=np.sum(self.B_RewardedHistory[1]==True)
        self.BS_LeftChoiceN=np.sum(self.B_AnimalResponseHistory==0)
        self.BS_RightChoiceN=np.sum(self.B_AnimalResponseHistory==1)
        self.BS_OverallRewardRate=self.BS_RewardTrialN/(self.B_CurrentTrialN+1)
        self.BS_LeftChoiceRewardRate=self.BS_LeftRewardTrialN/self.BS_LeftChoiceN
        self.BS_RightChoiceRewardRate=self.BS_RightRewardTrialN/self.BS_RightChoiceN
        # current trial numbers in the current block; BS_CurrentBlockTrialN
        self.BS_CurrentBlockTrialN=[[],[]]
        self.BS_CurrentBlockLen=[self.BlockLenHistory[0][-1], self.BlockLenHistory[1][-1]]
        for i in range(len(self.B_ANewBlock)):
            if len(self.BlockLenHistory[i])==1:
                self.BS_CurrentBlockTrialN[i]=self.B_CurrentTrialN+1
            elif len(self.BlockLenHistory[i])>1:
                self.BS_CurrentBlockTrialN[i]=self.B_CurrentTrialN+1-sum(self.BlockLenHistory[i][:-1])
        Len=np.shape(self.B_RewardedHistory)[1]
        self.BS_RewardedTrialN_CurrentLeftBlock=np.sum(self.B_RewardedHistory[0][(Len-self.BS_CurrentBlockTrialN[0]+1):]==True)
        self.BS_RewardedTrialN_CurrentRightBlock=np.sum(self.B_RewardedHistory[1][(Len-self.BS_CurrentBlockTrialN[1]+1):]==True)
        # update suggested reward
        if self.win.TotalWater.text()!='':
            self.B_SuggestedWater=float(self.win.TotalWater.text())-float(self.BS_TotalReward)
            self.win.SuggestedWater.setText(str(self.B_SuggestedWater))
        # early licking rate
        # double dipping 
        # foraging efficiency
        '''Some complex calculations can be separated from _GenerateATrial using different threads'''

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
            if (self.TP_Task in ['Coupled Baiting','Coupled Without Baiting']):
                self.win.ShowRewardPairs.setText('Reward pairs: '+str(np.round(self.RewardProb,2))+'\n\n'+'Current pair: '+str(np.round(self.B_RewardProHistory[:,self.B_CurrentTrialN],2)))
            elif (self.TP_Task in ['Uncoupled Baiting','Uncoupled Without Baiting']):
                self.win.ShowRewardPairs.setText('Reward pairs: '+str(np.round(self.RewardProbPoolUncoupled,2))+'\n\n'+'Current pair: '+str(np.round(self.B_RewardProHistory[:,self.B_CurrentTrialN],2)))
        except:
            print('Can not show reward pairs')
        # session start time
        SessionStartTime=self.win.SessionStartTime
        self.win.CurrentTime=datetime.now()
        self.win.Other_CurrentTime=str(self.win.CurrentTime)
        tdelta = self.win.CurrentTime - SessionStartTime
        self.win.Other_RunningTime=tdelta.seconds // 60
        SessionStartTimeHM = SessionStartTime.strftime('%H:%M')
        CurrentTimeHM = self.win.CurrentTime.strftime('%H:%M')
        self.win.Other_inforTitle='Session started: '+SessionStartTimeHM+ '  Current: '+CurrentTimeHM+ '  Run: '+str(self.win.Other_RunningTime)+'m'
        self.win.Other_BasicTitle='Current trial: ' + str(self.B_CurrentTrialN+1)
        self.win.infor.setTitle(self.win.Other_inforTitle)
        self.win.Basic.setTitle(self.win.Other_BasicTitle)

        # show basic session statistics    
        if self.B_CurrentTrialN>=0 and self.B_CurrentTrialN<1:
            self.win.ShowBasic.setText(   
                                        'Current left block: ' + str(self.BS_CurrentBlockTrialN[0]) + '/' +  str(self.BS_CurrentBlockLen[0])+'\n'
                                        'Current right block: ' + str(self.BS_CurrentBlockTrialN[1]) + '/' +  str(self.BS_CurrentBlockLen[1])+'\n\n'
                                        'Responded trial: ' + str(self.BS_FinisheTrialN) + '/'+str(self.BS_AllTrialN)+' ('+str(np.round(self.BS_RespondedRate,2))+')'+'\n'
                                        'Reward Trial: ' + str(self.BS_RewardTrialN) + '/' + str(self.BS_AllTrialN) + ' ('+str(np.round(self.BS_OverallRewardRate,2))+')' +'\n'
                                        'Total Reward (ml): '+ str(self.BS_RewardTrialN) + '*' + str(self.win.WaterPerRewardedTrial) + '='+str(np.round(self.BS_TotalReward,3)) +'\n'
                                        'Left choice rewarded: ' + str(self.BS_LeftRewardTrialN) + '/' + str(self.BS_LeftChoiceN) + ' ('+str(np.round(self.BS_LeftChoiceRewardRate,2))+')' +'\n'
                                        'Right choice rewarded: ' + str(self.BS_RightRewardTrialN) + '/' + str(self.BS_RightChoiceN) + ' ('+str(np.round(self.BS_RightChoiceRewardRate,2))+')' +'\n'
                                        )
        elif self.B_CurrentTrialN>=1 and self.B_CurrentTrialN<2:
            self.win.ShowBasic.setText( 
                                       'Current left block: ' + str(self.BS_CurrentBlockTrialN[0]) + '/' +  str(self.BS_CurrentBlockLen[0])+'\n'
                                       'Current right block: ' + str(self.BS_CurrentBlockTrialN[1]) + '/' +  str(self.BS_CurrentBlockLen[1])+'\n\n'
                                       'Responded trial: ' + str(self.BS_FinisheTrialN) + '/'+str(self.BS_AllTrialN)+' ('+str(np.round(self.BS_RespondedRate,2))+')'+'\n'
                                       'Reward Trial: ' + str(self.BS_RewardTrialN) + '/' + str(self.BS_AllTrialN) + ' ('+str(np.round(self.BS_OverallRewardRate,2))+')' +'\n'
                                       'Total Reward (ml): '+ str(self.BS_RewardTrialN) + '*' + str(self.win.WaterPerRewardedTrial) + '='+str(np.round(self.BS_TotalReward,3)) +'\n'
                                       'Left choice rewarded: ' + str(self.BS_LeftRewardTrialN) + '/' + str(self.BS_LeftChoiceN) + ' ('+str(np.round(self.BS_LeftChoiceRewardRate,2))+')' +'\n'
                                       'Right choice rewarded: ' + str(self.BS_RightRewardTrialN) + '/' + str(self.BS_RightChoiceN) + ' ('+str(np.round(self.BS_RightChoiceRewardRate,2))+')' +'\n\n'
                                       
                                       'Early licking (EL)\n'
                                        '  Frac of EL trial start_goCue: ' + str(self.EarlyLickingTrialsN_Start_GoCue) + '/' + str(len(self.Start_GoCue_LeftLicks)) + ' ('+str(np.round(self.EarlyLickingRate_Start_GoCue,2))+')' +'\n'
                                        '  Frac of EL trial start_delay: ' + str(self.EarlyLickingTrialsN_Start_Delay) + '/' + str(len(self.Start_Delay_LeftLicks)) + ' ('+str(np.round(self.EarlyLickingRate_Start_Delay,2))+')' +'\n'
                                        '  Frac of EL trial delay_goCue: ' + str(self.EarlyLickingTrialsN_Delay_GoCue) + '/' + str(len(self.Delay_GoCue_LeftLicks)) + ' ('+str(np.round(self.EarlyLickingRate_Delay_GoCue,2))+')' +'\n'
                                        '  Left/Right early licks start_goCue: ' + str(sum(self.Start_GoCue_LeftLicks)) + '/' + str(sum(self.Start_GoCue_RightLicks)) + ' ('+str(np.round(np.array(sum(self.Start_GoCue_LeftLicks))/np.array(sum(self.Start_GoCue_RightLicks)),2))+')' +'\n\n'
                                       
                                       'Double dipping (DD)\n'
                                       '  Frac of DD trial start_goCue: ' + str(self.DD_TrialsN_Start_CoCue) + '/' + str(len(self.Start_GoCue_DD)) + ' ('+str(np.round(self.DDRate_Start_CoCue,2))+')' +'\n'
                                       '  Frac of DD trial start_delay: ' + str(self.DD_TrialsN_Start_Delay) + '/' + str(len(self.Start_Delay_DD)) + ' ('+str(np.round(self.DDRate_Start_Delay,2))+')' +'\n'
                                       '  Frac of DD trial delay_goCue: ' + str(self.DD_TrialsN_Delay_GoCue) + '/' + str(len(self.Delay_GoCue_DD)) + ' ('+str(np.round(self.DDRate_Delay_GoCue,2))+')' +'\n'
                                       '  Frac of DD trial goCue_goCue1: ' + str(self.DD_TrialsN_GoCue_GoCue1) + '/' + str(len(self.GoCue_GoCue1_DD)) + ' ('+str(np.round(self.DDRate_GoCue_GoCue1,2))+')' +'\n'
                                       '  DD per finish trial start_goCue: ' + str(self.DD_PerTrial_Start_GoCue)+'\n'
                                       '  DD per finish trial goCue_goCue1: ' + str(self.DD_PerTrial_GoCue_GoCue1)+'\n'
                                       )
        elif self.B_CurrentTrialN>=2:
            self.win.ShowBasic.setText( 
                                       'Current left block: ' + str(self.BS_CurrentBlockTrialN[0]) + '/' +  str(self.BS_CurrentBlockLen[0])+'\n'
                                       'Current right block: ' + str(self.BS_CurrentBlockTrialN[1]) + '/' +  str(self.BS_CurrentBlockLen[1])+'\n\n'
                                       'Responded trial: ' + str(self.BS_FinisheTrialN) + '/'+str(self.BS_AllTrialN)+' ('+str(np.round(self.BS_RespondedRate,2))+')'+'\n'
                                       'Reward Trial: ' + str(self.BS_RewardTrialN) + '/' + str(self.BS_AllTrialN) + ' ('+str(np.round(self.BS_OverallRewardRate,2))+')' +'\n'
                                       'Total Reward (ml): '+ str(self.BS_RewardTrialN) + '*' + str(self.win.WaterPerRewardedTrial) + '='+str(np.round(self.BS_TotalReward,3)) +'\n'
                                       'Left choice rewarded: ' + str(self.BS_LeftRewardTrialN) + '/' + str(self.BS_LeftChoiceN) + ' ('+str(np.round(self.BS_LeftChoiceRewardRate,2))+')' +'\n'
                                       'Right choice rewarded: ' + str(self.BS_RightRewardTrialN) + '/' + str(self.BS_RightChoiceN) + ' ('+str(np.round(self.BS_RightChoiceRewardRate,2))+')' +'\n\n'
                                       
                                       'Early licking (EL)\n'
                                       '  Frac of EL trial start_goCue: ' + str(self.EarlyLickingTrialsN_Start_GoCue) + '/' + str(len(self.Start_GoCue_LeftLicks)) + ' ('+str(np.round(self.EarlyLickingRate_Start_GoCue,2))+')' +'\n'
                                       '  Frac of EL trial start_delay: ' + str(self.EarlyLickingTrialsN_Start_Delay) + '/' + str(len(self.Start_Delay_LeftLicks)) + ' ('+str(np.round(self.EarlyLickingRate_Start_Delay,2))+')' +'\n'
                                       '  Frac of EL trial delay_goCue: ' + str(self.EarlyLickingTrialsN_Delay_GoCue) + '/' + str(len(self.Delay_GoCue_LeftLicks)) + ' ('+str(np.round(self.EarlyLickingRate_Delay_GoCue,2))+')' +'\n'
                                       '  Left/Right early licks start_goCue: ' + str(sum(self.Start_GoCue_LeftLicks)) + '/' + str(sum(self.Start_GoCue_RightLicks)) + ' ('+str(np.round(np.array(sum(self.Start_GoCue_LeftLicks))/np.array(sum(self.Start_GoCue_RightLicks)),2))+')' +'\n\n'
                                       
                                       'Double dipping (DD)\n'
                                       '  Frac of DD trial start_goCue: ' + str(self.DD_TrialsN_Start_CoCue) + '/' + str(len(self.Start_GoCue_DD)) + ' ('+str(np.round(self.DDRate_Start_CoCue,2))+')' +'\n'
                                       '  Frac of DD trial start_delay: ' + str(self.DD_TrialsN_Start_Delay) + '/' + str(len(self.Start_Delay_DD)) + ' ('+str(np.round(self.DDRate_Start_Delay,2))+')' +'\n'
                                       '  Frac of DD trial delay_goCue: ' + str(self.DD_TrialsN_Delay_GoCue) + '/' + str(len(self.Delay_GoCue_DD)) + ' ('+str(np.round(self.DDRate_Delay_GoCue,2))+')' +'\n'
                                       '  Frac of DD trial goCue_goCue1: ' + str(self.DD_TrialsN_GoCue_GoCue1) + '/' + str(len(self.GoCue_GoCue1_DD)) + ' ('+str(np.round(self.DDRate_GoCue_GoCue1,2))+')' +'\n'
                                       '  Frac of DD trial goCue_nextStart: ' + str(self.DD_TrialsN_GoCue_NextStart) + '/' + str(len(self.GoCue_NextStart_DD)) + ' ('+str(np.round(self.DDRate_GoCue_NextStart,2))+')' +'\n'
                                       '  DD per finish trial start_goCue: ' + str(self.DD_PerTrial_Start_GoCue)+'\n'
                                       '  DD per finish trial goCue_goCue1: ' + str(self.DD_PerTrial_GoCue_GoCue1)+'\n'
                                       '  DD per finish trial goCue_nextStart: ' + str(self.DD_PerTrial_GoCue_NextStart)+'\n'
                                       )
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
        if self.B_CurrentTrialN>MaxTrial: 
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
        if self.win.AutoReward.isChecked():
            UnrewardedN=int(self.TP_Unrewarded)
            IgnoredN=int(self.TP_Ignored)
            if np.shape(self.B_AnimalResponseHistory)[0]>=IgnoredN or np.shape(self.B_RewardedHistory[0])[0]>=UnrewardedN:
                if np.all(self.B_AnimalResponseHistory[-IgnoredN:]==2) and np.shape(self.B_AnimalResponseHistory)[0]>=IgnoredN:
                    self.CurrentAutoReward=1
                    self.win.WarningLabelAutoWater.setText('Auto water because ignored trials exceed: '+self.TP_Ignored)
                    self.win.WarningLabelAutoWater.setStyleSheet("color: red;")
                elif (np.all(self.B_RewardedHistory[0][-UnrewardedN:]==False) and np.all(self.B_RewardedHistory[1][-UnrewardedN:]==False) and np.shape(self.B_RewardedHistory[0])[0]>=UnrewardedN):
                    self.CurrentAutoReward=1
                    self.win.WarningLabelAutoWater.setText('Auto water because unrewarded trials exceed: '+self.TP_Unrewarded)
                    self.win.WarningLabelAutoWater.setStyleSheet("color: red;")
                else:
                    self.CurrentAutoReward=0
            else:
                self.CurrentAutoReward=0
        else:
            self.CurrentAutoReward=0

        if self.CurrentAutoReward==0:
            self.win.WarningLabelAutoWater.setText('')
            self.win.WarningLabelAutoWater.setStyleSheet("color: gray;")
        self.B_AutoWaterTrial.append(self.CurrentAutoReward)
    def _GetLaserWaveForm(self):
        '''Get the waveform of the laser. It dependens on color/duration/protocol(frequency/RD/pulse duration)/locations/laser power'''
        N=self.SelctedCondition
        # CLP, current laser parameter
        self.CLP_Color=eval('self.TP_Laser_'+N)
        self.CLP_Location=eval('self.TP_Location_'+N)
        self.CLP_LaserPower=eval('self.TP_LaserPower_'+N)
        self.CLP_Duration=float(eval('self.TP_Duration_'+N))
        self.CLP_Protocol=eval('self.TP_Protocol_'+N)
        self.CLP_Frequency=float(eval('self.TP_Frequency_'+N))
        self.CLP_RampingDown=float(eval('self.TP_RD_'+N))
        self.CLP_PulseDur=eval('self.TP_PulseDur_'+N)
        self.CLP_LaserStart=eval('self.TP_LaserStart_'+N)
        self.CLP_OffsetStart=float(eval('self.TP_OffsetStart_'+N))
        self.CLP_LaserEnd=eval('self.TP_LaserEnd_'+N)
        self.CLP_OffsetEnd=float(eval('self.TP_OffsetEnd_'+N)) # negative, backward; positive forward
        self.CLP_SampleFrequency=float(self.TP_SampleFrequency)
        # align to trial start
        if (self.CLP_LaserStart=='Trial start' or self.CLP_LaserStart=='Go cue') and self.CLP_LaserEnd=='NA':
            # the duration is determined by Duration
            self.CLP_CurrentDuration=self.CLP_Duration
        elif self.CLP_LaserStart=='Trial start' and self.CLP_LaserEnd=='Go cue':
            # the duration is determined by CurrentITI, CurrentDelay, self.CLP_OffsetStart, self.CLP_OffsetEnd
            # only positive CLP_OffsetStart is allowed
            if self.CLP_OffsetStart<0:
                self.win.WarningLabel.setText('Please set offset start to be positive!')
                self.win.WarningLabel.setStyleSheet("color: red;")
            self.CLP_CurrentDuration=self.CurrentITI+self.CurrentDelay-self.CLP_OffsetStart+self.CLP_OffsetEnd
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
            if self.CurrentLaserAmplitude[i]!=0:
                # in some cases the other paramters except the amplitude could also be different
                self._ProduceWaveForm(self.CurrentLaserAmplitude[i])
                setattr(self, 'WaveFormLocation_' + str(i+1), self.my_wave)

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
        if self.CLP_Location=='Left':
            self.CurrentLaserAmplitude=[5,0]
        elif self.CLP_Location=='Right':
            self.CurrentLaserAmplitude=[0,5]
        elif self.CLP_Location=='Both':
            self.CurrentLaserAmplitude=[5,5]
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
        self.CurrentBait=self.B_CurrentRewardProb>np.random.random(2)
        if (self.TP_Task in ['Coupled Baiting','Uncoupled Baiting']):
             self.CurrentBait= self.CurrentBait | self.B_Baited
        self.B_Baited=  self.CurrentBait.copy()
        self.B_BaitHistory=np.append(self.B_BaitHistory, self.CurrentBait.reshape(2,1),axis=1)

        # if this is an optogenetics trial
        if self.B_LaserOnTrial[self.B_CurrentTrialN]==1:
            if self.CurrentWaveForm==1:
                # permit triggering waveform 1 after an event
                # waveform start event
                if self.CLP_LaserStart=='Trial start':
                    Channel1.TriggerITIStart_Wave1(int(1))
                    Channel1.TriggerITIStart_Wave2(int(0))
                    Channel1.TriggerGoCue_Wave1(int(0))
                    Channel1.TriggerGoCue_Wave2(int(0))
                elif self.CLP_LaserStart=='Go cue':
                    Channel1.TriggerGoCue_Wave1(int(1))
                    Channel1.TriggerGoCue_Wave2(int(0))
                    Channel1.TriggerITIStart_Wave1(int(0))
                    Channel1.TriggerITIStart_Wave2(int(0))
                else:
                    self.win.WarningLabel.setText('Unindentified optogenetics start event!')
                    self.win.WarningLabel.setStyleSheet("color: red;")
            elif self.CurrentWaveForm==2:
                # permit triggering waveform 2 after an event
                # waveform start event
                if self.CLP_LaserStart=='Trial start':
                    Channel1.TriggerITIStart_Wave1(int(0))
                    Channel1.TriggerITIStart_Wave2(int(1))
                    Channel1.TriggerGoCue_Wave1(int(0))
                    Channel1.TriggerGoCue_Wave2(int(0))
                elif self.CLP_LaserStart=='Go cue':
                    Channel1.TriggerGoCue_Wave1(int(0))
                    Channel1.TriggerGoCue_Wave2(int(1))
                    Channel1.TriggerITIStart_Wave1(int(0))
                    Channel1.TriggerITIStart_Wave2(int(0))
                else:
                    self.win.WarningLabel.setText('Unindentified optogenetics start event!')
                    self.win.WarningLabel.setStyleSheet("color: gray;")
            # location of optogenetics
            # dimension of self.CurrentLaserAmplitude indicates how many locations do we have
            for i in range(len(self.CurrentLaserAmplitude)):
                if self.CurrentLaserAmplitude[i]!=0:
                    eval('Channel1.Trigger_Location'+str(i+1)+'(int(1))')
                else:
                    eval('Channel1.Trigger_Location'+str(i+1)+'(int(0))')
            # send the waveform size
            Channel1.Location1_Size(int(self.Location1_Size))
            Channel1.Location2_Size(int(self.Location2_Size))
            # change the position of the CurrentWaveForm and the NextWaveForm 
            self.CurrentWaveForm=self.NextWaveForm
        else:
            # 'Do not trigger the waveform'
            Channel1.TriggerGoCue_Wave1(int(0))
            Channel1.TriggerGoCue_Wave2(int(0))
            Channel1.TriggerITIStart_Wave1(int(0))
            Channel1.TriggerITIStart_Wave2(int(0))
            for i in range(len(self.CurrentLaserAmplitude)):
                eval('Channel1.Trigger_Location'+str(i+1)+'(int(0))')
            Channel1.Location1_Size(int(5000))
            Channel1.Location2_Size(int(5000))
        
        Channel1.LeftValue(float(self.TP_LeftValue)*1000)
        Channel1.RightValue(float(self.TP_RightValue)*1000)
        Channel1.RewardConsumeTime(float(self.TP_RewardConsumeTime))
        Channel1.Left_Bait(int(self.CurrentBait[0]))
        Channel1.Right_Bait(int(self.CurrentBait[1]))
        Channel1.ITI(float(self.CurrentITI))
        Channel1.DelayTime(float(self.CurrentDelay))
        Channel1.ResponseTime(float(self.TP_ResponseTime))
        Channel1.start(1)


    def _GetAnimalResponse(self,Channel1,Channel3):
        '''
        # random forager
        self.B_AnimalCurrentResponse=random.choice(range(2))
        # win stay, lose switch forager
        if self.B_CurrentTrialN>=2:
            if any(self.B_RewardedHistory[:,-1]==1):# win
                self.B_AnimalCurrentResponse=self.B_AnimalResponseHistory[-1]
            elif any(self.B_RewardedHistory[:,-1]==0) and self.B_AnimalResponseHistory[-1]!=2:# lose
                self.B_AnimalCurrentResponse=1-self.B_AnimalResponseHistory[-1]
            else: # no response
                self.B_AnimalCurrentResponse=random.choice(range(2))

        if np.random.random(1)<0.1: # no response
            self.B_AnimalCurrentResponse=2
        '''

        for i in range(6):
            Rec=Channel1.receive()
            if Rec[0]=='/TrialStartTime':
                TrialStartTime=Rec[1]
            elif Rec[0]=='/DelayStartTime':
                DelayStartTime=Rec[1]
            elif Rec[0]=='/GoCueTime':
                # give auto water after Co cue
                if self.CurrentAutoReward==1:
                    self._GiveLeft()
                    self._GiveRight()
                self.B_GoCueTime=np.append(self.B_GoCueTime,Rec[1])
            elif Rec[0]=='/RewardOutcomeTime':
                RewardOutcomeTime=Rec[1]
            elif Rec[0]=='/RewardOutcome':
                TrialOutcome=Rec[1]
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
            elif Rec[0]=='/TrialEndTime':
                TrialEndTime=Rec[1]

        # get the trial end time at the end of the trial
        self.B_TrialStartTime=np.append(self.B_TrialStartTime,TrialStartTime)
        self.B_DelayStartTime=np.append(self.B_DelayStartTime,DelayStartTime)
        self.B_TrialEndTime=np.append(self.B_TrialEndTime,TrialEndTime)
        self.B_RewardOutcomeTime=np.append(self.B_RewardOutcomeTime,RewardOutcomeTime)

    def _GiveLeft(self):
        '''manually give left water'''
        self.win.Channel.LeftValue(float(self.win.LeftValue.text())*1000*float(self.win.Multiplier.text())) 
        self.win.Channel3.ManualWater_Left(int(1))
        self.win.Channel.LeftValue(float(self.win.LeftValue.text())*1000)

    def _GiveRight(self):
        '''manually give right water'''
        self.win.Channel.RightValue(float(self.win.RightValue.text())*1000*float(self.win.Multiplier.text()))
        self.win.Channel3.ManualWater_Right(int(1))
        self.win.Channel.RightValue(float(self.win.RightValue.text())*1000)

    def _GetLicks(self,Channel2):
        '''Get licks and reward delivery time'''
        #while self.win.Start.isChecked():
        #    time.sleep(0.01)
        while not Channel2.msgs.empty():
            Rec=Channel2.receive()
            if Rec[0]=='/LeftLickTime':
                self.B_LeftLickTime=np.append(self.B_LeftLickTime,Rec[1])
            elif Rec[0]=='/RightLickTime':
                self.B_RightLickTime=np.append(self.B_RightLickTime,Rec[1])
            elif Rec[0]=='/LeftRewardDeliveryTime':
                self.B_LeftRewardDeliveryTime=np.append(self.B_LeftRewardDeliveryTime,Rec[1])
            elif Rec[0]=='/RightRewardDeliveryTime':
                self.B_RightRewardDeliveryTime=np.append(self.B_RightRewardDeliveryTime,Rec[1])
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
                if child.objectName()=='qt_spinbox_lineedit':
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

class WorkerSignals(QObject):
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
    finished = pyqtSignal()
    error = pyqtSignal(tuple)
    result = pyqtSignal(object)
    progress = pyqtSignal(int)


class Worker(QRunnable):
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
        #self.kwargs['progress_callback'] = self.signals.progress

    @pyqtSlot()
    def run(self):
        '''
        Initialise the runner function with passed args, kwargs.
        '''

        # Retrieve args/kwargs here; and fire processing using them
        try:
            result = self.fn(*self.args, **self.kwargs)
        except:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))
        else:
            self.signals.result.emit(result)  # Return the result of the processing
        finally:
            self.signals.finished.emit()  # Done
