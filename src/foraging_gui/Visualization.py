import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.figure import Figure
from matplotlib.gridspec import GridSpec
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

class PlotV(FigureCanvas):
    def __init__(self,win,GeneratedTrials=None,parent=None,dpi=100,width=5, height=4):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        gs = GridSpec(10, 30, wspace = 3, hspace = 0.1, bottom = 0.1, top = 0.95, left = 0.04, right = 0.98)
        self.ax1 = self.fig.add_subplot(gs[0:4, 0:20])
        self.ax2 = self.fig.add_subplot(gs[4:10, 0:20])
        self.ax3 = self.fig.add_subplot(gs[1:9, 22:])
        self.ax1.get_shared_x_axes().join(self.ax1, self.ax2)
        FigureCanvas.__init__(self, self.fig)
        self.RunLength=win.RunLength.text
        self.RunLengthSetValue=win.RunLength.setValue
        self.WindowSize=win.WindowSize.text
        self.StepSize=win.StepSize.text
        self.MarkerSize=3

    def _Update(self,GeneratedTrials=None,Channel=None):
        if Channel is not None:
            GeneratedTrials._GetLicks(Channel)
        self.B_AnimalResponseHistory=GeneratedTrials.B_AnimalResponseHistory
        self.B_LickPortN=GeneratedTrials.B_LickPortN
        self.B_RewardProHistory=GeneratedTrials.B_RewardProHistory
        self.B_BlockLenHistory=GeneratedTrials.B_BlockLenHistory
        self.B_BaitHistory=GeneratedTrials.B_BaitHistory
        self.B_ITIHistory=GeneratedTrials.B_ITIHistory
        self.B_DelayHistory=GeneratedTrials.B_DelayHistory
        self.B_CurrentRewardProb=GeneratedTrials.B_CurrentRewardProb
        self.B_AnimalCurrentResponse=GeneratedTrials.B_AnimalCurrentResponse
        self.B_CurrentTrialN=GeneratedTrials.B_CurrentTrialN
        self.B_RewardedHistory=GeneratedTrials.B_RewardedHistory
        self.B_CurrentTrialN=GeneratedTrials.B_CurrentTrialN
        self.B_RightLickTime=GeneratedTrials.B_RightLickTime
        self.B_LeftLickTime=GeneratedTrials.B_LeftLickTime
        self.B_TrialStartTime=GeneratedTrials.B_TrialStartTime
        self.B_TrialEndTime=GeneratedTrials.B_TrialEndTime
        self.B_RewardOutcomeTime=GeneratedTrials.B_RewardOutcomeTime
        if self.B_CurrentTrialN>0:
            self.B_Time=self.B_RewardOutcomeTime-GeneratedTrials.B_TrialStartTime[0]
        else:
            self.B_Time=self.B_RewardOutcomeTime
        self.B_BTime=self.B_Time.copy()
        try:
            Delta=self.B_TrialEndTime[-1]-self.B_TrialStartTime[0]
            self.B_BTime=np.append(self.B_BTime,Delta+0.02*Delta)
        except:
            self.B_BTime=np.append(self.B_BTime,2)

        self.MarchingType=GeneratedTrials.TP_MartchingType
        self._PlotBlockStructure()
        self._PlotChoice()
        try:
            self._PlotMatching()
        except:
            pass
        self._PlotLicks()
        self.finish=1
    def _PlotBlockStructure(self):
        ax2=self.ax2
        ax2.cla()
        try:
            ax2.plot(self.B_Time, self.B_RewardProHistory[0],color='r', label='p_L',alpha=1)
            ax2.plot(self.B_Time, self.B_RewardProHistory[1],color='b', label='p_R',alpha=1)
            Fraction=self.B_RewardProHistory[1]/self.B_RewardProHistory.sum(axis=0)
            ax2.plot(self.B_Time,Fraction,color='y',label='p_R_frac',alpha=0.5)
        except:
            Len=len(self.B_Time)
            ax2.plot(self.B_Time, self.B_RewardProHistory[0][0:Len],color='r', label='p_L',alpha=1)
            ax2.plot(self.B_Time, self.B_RewardProHistory[1][0:Len],color='b', label='p_R',alpha=1)
            Fraction=self.B_RewardProHistory[1]/self.B_RewardProHistory.sum(axis=0)
            ax2.plot(self.B_Time,Fraction[0:Len],color='y',label='p_R_frac',alpha=0.5)
        self._UpdateAxis()
        self.draw()
    def _PlotChoice(self):
        MarkerSize=self.MarkerSize
        ax1=self.ax1
        ax2=self.ax2
        ax1.cla()
        LeftChoice_Rewarded=np.where(np.logical_and(self.B_AnimalResponseHistory==0,self.B_RewardedHistory[0]==True))
        LeftChoice_UnRewarded=np.where(np.logical_and(self.B_AnimalResponseHistory==0,self.B_RewardedHistory[0]==False))
        RightChoice_Rewarded=np.where(np.logical_and(self.B_AnimalResponseHistory==1,self.B_RewardedHistory[1]==True))
        RightChoice_UnRewarded=np.where(np.logical_and(self.B_AnimalResponseHistory==1, self.B_RewardedHistory[1]==False))

        # running average of choice
        kernel_size = int(self.RunLength())
        if kernel_size==1:
            kernel_size=2
            self.RunLengthSetValue(2)

        ResponseHistoryT=self.B_AnimalResponseHistory.copy()
        ResponseHistoryT[ResponseHistoryT==2]=np.nan
        ResponseHistoryF=ResponseHistoryT.copy()
        # running average of reward and succuss rate
        RewardedHistoryT=self.B_AnimalResponseHistory.copy()
        LeftRewarded=np.logical_and(self.B_RewardedHistory[0]==1,self.B_RewardedHistory[1]==0)  
        RightRewarded=np.logical_and(self.B_RewardedHistory[1]==1,self.B_RewardedHistory[0]==0)
        NoReward=np.logical_and(self.B_RewardedHistory[1]==0,self.B_RewardedHistory[0]==0)
        RewardedHistoryT[LeftRewarded]=0
        RewardedHistoryT[RightRewarded]=1
        RewardedHistoryT[NoReward]=np.nan
        RewardedHistoryF=RewardedHistoryT.copy()

        SuccessHistoryT=self.B_AnimalResponseHistory.copy()
        SuccessHistoryT[np.logical_or(SuccessHistoryT==1, SuccessHistoryT==0)]=1
        SuccessHistoryT[SuccessHistoryT==2]=0
        SuccessHistoryF=SuccessHistoryT.copy()
        # running average of response fraction
        for i in range(len(self.B_AnimalResponseHistory)):
            if i>=kernel_size-1:
                ResponseHistoryF[i+1-kernel_size]=np.nanmean(ResponseHistoryT[i+1-kernel_size:i+1])
                RewardedHistoryF[i+1-kernel_size]=np.nanmean(RewardedHistoryT[i+1-kernel_size:i+1])
                SuccessHistoryF[i+1-kernel_size]=np.nanmean(SuccessHistoryT[i+1-kernel_size:i+1])

        LeftChoice=np.where(self.B_AnimalResponseHistory==0)
        RightChoice=np.where(self.B_AnimalResponseHistory==1)
        NoResponse=np.where(self.B_AnimalResponseHistory==2)

        if self.B_BaitHistory.shape[1]>self.B_AnimalResponseHistory.shape[0]:
            LeftBait=np.where(self.B_BaitHistory[0][:-1]==True)
            RightBait=np.where(self.B_BaitHistory[1][:-1]==True)
            
            # plot the upcoming trial start time
            if self.B_CurrentTrialN>0:
                NewTrialStart=np.array(self.B_BTime[-1])
                NewTrialStart2=np.array(self.B_BTime[-1]+self.B_BTime[-1]/40)
            else:
                NewTrialStart=np.array(self.B_BTime[-1]+0.1)
                NewTrialStart2=np.array(self.B_BTime[-1])
            ax1.eventplot(NewTrialStart.reshape((1,)), lineoffsets=.5, linelengths=2, linewidth=2, color='k', label='UpcomingTrial', alpha=0.3)
            ax2.eventplot(NewTrialStart.reshape((1,)), lineoffsets=.5, linelengths=2, linewidth=2, color='k', alpha=0.3)
            if self.B_BaitHistory[0][-1]==True:
                ax1.plot(NewTrialStart2,-0.2, 'kD',label='Bait',markersize=MarkerSize, alpha=0.4)
            if self.B_BaitHistory[1][-1]==True:
                ax1.plot(NewTrialStart2,1.2, 'kD',markersize=MarkerSize, alpha=0.4)
        else:
            LeftBait=np.where(self.B_BaitHistory[0]==True)
            RightBait=np.where(self.B_BaitHistory[1]==True)

        if np.size(LeftBait) !=0:
            ax1.plot(self.B_BTime[LeftBait], np.zeros(len(self.B_BTime[LeftBait]))-0.2, 'kD',markersize=MarkerSize, alpha=0.2)
        if np.size(RightBait) !=0:
            ax1.plot(self.B_BTime[RightBait], np.zeros(len(self.B_BTime[RightBait]))+1.2, 'kD',markersize=MarkerSize, alpha=0.2)
        if np.size(LeftChoice) !=0:
            ax1.plot(self.B_Time[LeftChoice], np.zeros(len(self.B_Time[LeftChoice]))+0, 'go',markerfacecolor = (1, 1, 1, 1),label='Choice',markersize=MarkerSize)
        if np.size(LeftChoice_Rewarded) !=0:
            ax1.plot(self.B_Time[LeftChoice_Rewarded], np.zeros(len(self.B_Time[LeftChoice_Rewarded]))+.2, 'go',markerfacecolor = (0, 1, 0, 1),label='Rewarded',markersize=MarkerSize)
        if np.size(RightChoice) !=0:
            ax1.plot(self.B_Time[RightChoice], np.zeros(len(self.B_Time[RightChoice]))+1, 'go',markerfacecolor = (1, 1, 1, 1),markersize=MarkerSize)
        if np.size(RightChoice_Rewarded) !=0:
            ax1.plot(self.B_Time[RightChoice_Rewarded], np.zeros(len(self.B_Time[RightChoice_Rewarded]))+.8, 'go',markerfacecolor = (0, 1, 0, 1),markersize=MarkerSize)
        if np.size(NoResponse) !=0:
            ax1.plot(self.B_Time[NoResponse], np.zeros(len(self.B_Time[NoResponse]))+.5, 'Xk',label='NoResponse',markersize=MarkerSize,alpha=0.2)
        if self.B_CurrentTrialN>kernel_size:
            ax2.plot(self.B_Time[kernel_size-1:],ResponseHistoryF[:-kernel_size+1],'k',label='Choice_frac')
            ax2.plot(self.B_Time[kernel_size-1:],RewardedHistoryF[:-kernel_size+1],'g',label='reward_frac')
            ax2.plot(self.B_Time[kernel_size-1:],SuccessHistoryF[:-kernel_size+1],'c',label='succuss_frac', alpha=0.2)
        self._UpdateAxis()
        self.draw()

    def _PlotMatching(self):
        ax=self.ax3
        ax.cla()
        WindowSize=int(self.WindowSize())
        StepSize=int(self.StepSize())
        if self.B_CurrentTrialN<1:
            return
        NumberOfDots = int((np.ptp(self.B_Time)-WindowSize)/StepSize)
        if NumberOfDots<1:
            return
        #WindowStart=np.linspace(np.min(self.B_Time),np.max(self.B_Time)-WindowSize,num=NumberOfDots)
        choice_R_frac = np.empty(NumberOfDots)
        choice_R_frac[:]=np.nan
        reward_R_frac = choice_R_frac.copy()
        choice_log_ratio = choice_R_frac.copy()
        reward_log_ratio = choice_R_frac.copy()
        WinStartN=np.min(self.B_Time)
        for idx in range(NumberOfDots):
            CuI=np.logical_and(self.B_Time>=WinStartN,self.B_Time<WinStartN+WindowSize)
            LeftChoiceN=sum(self.B_AnimalResponseHistory[CuI]==0)
            RightChoiceN=sum(self.B_AnimalResponseHistory[CuI]==1)
            LeftRewardN=sum(self.B_RewardedHistory[0,CuI]==1)
            RightRewardN=sum(self.B_RewardedHistory[1,CuI]==1)    
            choice_R_frac[idx]=LeftChoiceN/(LeftChoiceN+RightChoiceN)
            reward_R_frac[idx]=LeftRewardN/(LeftRewardN+RightRewardN)
            choice_log_ratio[idx]=np.log(RightChoiceN / LeftChoiceN)
            reward_log_ratio[idx]=np.log(RightRewardN / LeftRewardN)
            WinStartN=WinStartN+StepSize
        if self.MarchingType=='log ratio':
            x=reward_log_ratio
            y=choice_log_ratio
            ax.set(xlabel='Log Reward_R/L',ylabel='Log Choice_R/L')
            ax.plot(x, y, 'ko')
            max_range = max(np.abs(ax.get_xlim()).max(), np.abs(ax.get_ylim()).max())
            ax.plot([-max_range, max_range], [-max_range, max_range], 'k--', lw=1)
        else:
            x=reward_R_frac
            y=choice_R_frac
            ax.set(xlabel='frac Reward_R',ylabel='frac Choice_R')
            ax.plot(x, y, 'ko')
            ax.plot([0, 1], [0, 1], 'k--', lw=1)

        # linear fitting
        try: 
            SeInd=~np.logical_or(np.logical_or(np.isinf(x),np.isinf(y)), np.logical_or(np.isnan(x),np.isnan(y)))
            x=x[SeInd]
            y=y[SeInd]
            slope, intercept, r_value, p_value, _ = stats.linregress(x, y)
            fit_x = x
            fit_y = x * slope + intercept
            ax.plot(fit_x, fit_y, 'r', label=f'r = {r_value:.3f}\np = {p_value:.2e}')
            ax.set_title(f'Matching slope = {slope:.2f}, bias_R = {intercept:.2f}', fontsize=10)
            ax.legend(loc='upper left', fontsize=8)
            ax.axis('equal')
        except:
            pass
        self.draw()
        #range(np.min(self.B_Time),np.max(self.B_Time),periods = numberofpoints * int(self.DotsPerWindow()))
        #win_centers = pd.date_range(start = np.min(self.B_Time), end = np.max(self.B_Time),periods = numberofpoints * int(self.DotsPerWindow()))
    def _PlotLicks(self):
        if self.B_CurrentTrialN<1:
            return
        ax=self.ax1
        ax.plot(self.B_LeftLickTime-self.B_TrialStartTime[0], np.zeros(len(self.B_LeftLickTime))-0.4, 'k|')
        ax.plot(self.B_RightLickTime-self.B_TrialStartTime[0], np.zeros(len(self.B_RightLickTime))+1.4, 'k|')
        self.draw()

    def _UpdateAxis(self):
        self.ax1.set_xticks([])
        self.ax1.set_yticks([0,1])
        self.ax1.set_yticklabels(['L', 'R'])
        self.ax1.set_ylim(-0.6, 1.6)
        self.ax1.legend(loc='lower left', fontsize=8)
        #self.ax1.axis('off')
        self.ax2.set_yticks([0,1])
        self.ax2.set_yticklabels(['L', 'R'])
        self.ax2.set_ylim(-0.15, 1.15)
        self.ax2.legend(loc='lower left', fontsize=8)