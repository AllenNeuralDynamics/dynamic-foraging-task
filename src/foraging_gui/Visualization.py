import logging

import numpy as np
from scipy import stats
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
        self.WindowSizeSetValue=win.WindowSize.setValue
        self.StepSize=win.StepSize.text
        self.StepSizeSetValue=win.StepSize.setValue
        self.MarkerSize=3
        self.main_win = win

    def _Update(self,GeneratedTrials=None,Channel=None):
        if Channel is not None:
            GeneratedTrials._GetLicks(Channel)
        self.B_AnimalResponseHistory=GeneratedTrials.B_AnimalResponseHistory
        self.B_LickPortN=GeneratedTrials.B_LickPortN
        self.B_RewardProHistory=GeneratedTrials.B_RewardProHistory
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
        self.B_LaserOnTrial=np.array(GeneratedTrials.B_LaserOnTrial)
        self.B_AutoWaterTrial=GeneratedTrials.B_AutoWaterTrial
        self.MarchingType=GeneratedTrials.TP_MartchingType

        if self.B_CurrentTrialN>0:
            self.B_Time=self.B_RewardOutcomeTime-GeneratedTrials.B_TrialStartTime[0]
        else:
            self.B_Time=self.B_RewardOutcomeTime
        self.B_BTime=self.B_Time.copy()
        if self.B_TrialEndTime.size!=0:
            Delta=self.B_TrialEndTime[-1]-self.B_TrialStartTime[0]
            self.B_BTime=np.append(self.B_BTime,Delta+0.02*Delta)
        else:
            self.B_BTime=np.append(self.B_BTime,2)

        try:
            self._PlotBlockStructure()
            self._PlotChoice()
            self._PlotLicks()
        except Exception as e:
            logging.error(str(e))
        try:
            self._PlotMatching()
        except Exception as e:
            logging.error(str(e))
        self.finish=1
    def _PlotBlockStructure(self):
        ax2=self.ax2
        ax2.cla()
        Len=len(self.B_Time)
        ax2.plot(self.B_Time, self.B_RewardProHistory[0][0:Len],color='r', label='p_L',alpha=1)
        ax2.plot(self.B_Time, self.B_RewardProHistory[1][0:Len],color='b', label='p_R',alpha=1)
        Fraction=self.B_RewardProHistory[1]/self.B_RewardProHistory.sum(axis=0)
        ax2.plot(self.B_Time,Fraction[0:Len],linestyle=':',color='y',label='p_R_frac',alpha=0.8)
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
        Optogenetics_On=np.where(self.B_LaserOnTrial[:-1]==1)
        # running average of choice
        if self.RunLength()!='':
            kernel_size = int(self.RunLength())
            if kernel_size==1:
                kernel_size=2
                self.RunLengthSetValue(2)
        else:
            kernel_size=2
            self.RunLengthSetValue(2)
        self.kernel_size=kernel_size
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
                if all(np.isnan(ResponseHistoryT[i+1-kernel_size:i+1])):
                    ResponseHistoryF[i+1-kernel_size]=np.nan
                    RewardedHistoryF[i+1-kernel_size]=np.nan
                    SuccessHistoryF[i+1-kernel_size]=np.nan
                else:
                    ResponseHistoryF[i+1-kernel_size]=np.nanmean(ResponseHistoryT[i+1-kernel_size:i+1])
                    RewardedHistoryF[i+1-kernel_size]=np.nanmean(RewardedHistoryT[i+1-kernel_size:i+1])
                    SuccessHistoryF[i+1-kernel_size]=np.nanmean(SuccessHistoryT[i+1-kernel_size:i+1])
        self.ResponseHistoryF=ResponseHistoryF
        LeftChoice=np.where(self.B_AnimalResponseHistory==0)
        RightChoice=np.where(self.B_AnimalResponseHistory==1)
        NoResponse=np.where(self.B_AnimalResponseHistory==2)

        if self.B_BaitHistory.shape[1]>self.B_AnimalResponseHistory.shape[0]:
            LeftBait=np.where(self.B_BaitHistory[0][:-1]==True)
            RightBait=np.where(self.B_BaitHistory[1][:-1]==True)
            LeftAutoWater=np.where(self.B_AutoWaterTrial[0][:-1]==1)
            RightAutoWater=np.where(self.B_AutoWaterTrial[1][:-1]==1)
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
            if self.B_LaserOnTrial[-1]==1:
                ax1.plot(NewTrialStart2,1.5, 'bo',markersize=MarkerSize,markerfacecolor = (0, 0, 1, 1), alpha=1)
            if self.B_AutoWaterTrial[0][-1]==1:
                ax1.plot(NewTrialStart2,0.4, 'bo',markerfacecolor = (0, 1, 0, 1),markersize=MarkerSize)
            if self.B_AutoWaterTrial[1][-1]==1:
                ax1.plot(NewTrialStart2,0.6, 'bo',markerfacecolor = (0, 1, 0, 1),markersize=MarkerSize)
        else:
            LeftBait=np.where(self.B_BaitHistory[0]==True)
            RightBait=np.where(self.B_BaitHistory[1]==True)
            LeftAutoWater=np.where(self.B_AutoWaterTrial[0]==1)
            RightAutoWater=np.where(self.B_AutoWaterTrial[1]==1)
        
        if np.size(LeftAutoWater) !=0:
            ax1.plot(self.B_BTime[LeftAutoWater], np.zeros(len(self.B_BTime[LeftAutoWater]))+0.4, 'bo',markerfacecolor = (0, 1, 0, 1),markersize=MarkerSize)
        if np.size(RightAutoWater) !=0:
            ax1.plot(self.B_BTime[RightAutoWater], np.zeros(len(self.B_BTime[RightAutoWater]))+0.6, 'bo',markerfacecolor =(0, 1, 0, 1),markersize=MarkerSize,label='AutoWater')

        if np.size(Optogenetics_On) !=0:
            ax1.plot(self.B_BTime[Optogenetics_On], np.zeros(len(self.B_BTime[Optogenetics_On]))+1.5, 'bo',markerfacecolor = (0, 0, 1, 1),label='Optogenetics',markersize=MarkerSize, alpha=1)
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
            ax2.plot(self.B_Time[kernel_size-1:],ResponseHistoryF[:-kernel_size+1],'k',label='Choice_frac',linewidth=2,alpha=0.8)
            ax2.plot(self.B_Time[kernel_size-1:],RewardedHistoryF[:-kernel_size+1],'g',label='reward_frac',linewidth=1,alpha=0.8)
            ax2.plot(self.B_Time[kernel_size-1:],SuccessHistoryF[:-kernel_size+1],'c',label='finish_frac', alpha=0.2)
        self._UpdateAxis()
        self.draw()

    def _PlotMatching(self):
        ax=self.ax3
        ax.cla()
        if self.WindowSize()!='':
            WindowSize=int(self.WindowSize())
            if WindowSize==0 or WindowSize==1:
                WindowSize=100
                self.WindowSizeSetValue(100)
        else:
            WindowSize=100
            self.WindowSizeSetValue(100)
        if self.StepSize()!='': 
            StepSize=int(self.StepSize())
            if StepSize==0 or StepSize==1:
                StepSize=10
                self.StepSizeSetValue(10)
        else:
            StepSize=10
            self.StepSizeSetValue(10)

        if self.B_CurrentTrialN<1:
            return
        NumberOfDots = int((np.ptp(self.B_Time)-WindowSize)/StepSize)
        if NumberOfDots<1:
            return
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
            if LeftRewardN+RightRewardN!=0:
                reward_R_frac[idx]=LeftRewardN/(LeftRewardN+RightRewardN)
            if RightChoiceN and LeftChoiceN and RightRewardN and LeftRewardN:
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
            
            # Save intercept to show bias in performane info
            self.main_win.B_Bias_R=intercept
            
            ax.plot(fit_x, fit_y, 'r', label=f'r = {r_value:.3f}\np = {p_value:.2e}')
            ax.set_title(f'Matching slope = {slope:.2f}, bias_R = {intercept:.2f}', fontsize=10)
            ax.legend(loc='upper left', fontsize=8)
            ax.axis('equal')
            ax.set_xlim([fit_x.min()-2, fit_x.max()+2])
            ax.set_ylim([fit_y.min()-2, fit_y.max()+2])
        except Exception as e:
            logging.error(str(e))
        self.draw()

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
        self.ax2.set_yticks([0,1])
        self.ax2.set_yticklabels(['L', 'R'])
        self.ax2.set_ylim(-0.15, 1.15)
        self.ax2.legend(loc='lower left', fontsize=8)

class PlotWaterCalibration(FigureCanvas):
    def __init__(self,water_win,dpi=100,width=5, height=4):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        gs = GridSpec(10, 30, wspace = 3, hspace = 0.1, bottom = 0.1, top = 0.95, left = 0.04, right = 0.98)
        self.ax1 = self.fig.add_subplot(gs[0:9, 1:30])
        FigureCanvas.__init__(self, self.fig)
        self.water_win=water_win
        self.WaterCalibrationResults=self.water_win.WaterCalibrationResults
        self.FittingResults={}

    def _UpdateKeysSpecificCalibration(self):
        '''update the fields of specific calibration'''
        self.WaterCalibrationResults=self.water_win.WaterCalibrationResults
        current_item = self.water_win.showspecificcali.currentText()
        self.water_win.showspecificcali.clear()
        sorted_dates = sorted(self.WaterCalibrationResults.keys(),reverse=True)
        sorted_dates.insert(0,'NA')
        self.water_win.showspecificcali.addItems(sorted_dates)
        # remain the item unchanged
        for i in range(self.water_win.showspecificcali.count()):
            if current_item==self.water_win.showspecificcali.itemText(i):
                self.water_win.showspecificcali.setCurrentIndex(i)

    def _Update(self):
        '''update the calibration figure'''
        self.WaterCalibrationResults=self.water_win.WaterCalibrationResults
        self._UpdateKeysSpecificCalibration()
        self.ax1.cla()
        if hasattr(self.water_win.MainWindow,'RecentWaterCalibrationDate'):
            self.water_win.VisuCalibration.setTitle('Last calibration date:'+self.water_win.MainWindow.RecentWaterCalibrationDate)
        sorted_dates = sorted(self.WaterCalibrationResults.keys())
        showrecent=int(self.water_win.showrecent.text())
        if showrecent<=0:
            showrecent=1
        if showrecent>len(sorted_dates):
            showrecent=len(sorted_dates)
        all_dates=sorted_dates[-showrecent:]
        # use the selected date if showspecificcali is not NA
        if self.water_win.showspecificcali.currentText()!='NA':
            all_dates=[self.water_win.showspecificcali.currentText()]
        #all_dates represents dates to plot
        for current_date in sorted_dates:
            all_valves=self.WaterCalibrationResults[current_date].keys()
            for current_valve in all_valves:
                sorted_X,sorted_Y=self._GetWaterCalibration(self.WaterCalibrationResults,current_date,current_valve)
                if current_date in all_dates:
                    if current_valve=='Left':
                        line=self.ax1.plot(sorted_X, sorted_Y, 'o-',label=current_date+'_left valve')
                    elif current_valve=='Right':
                        line=self.ax1.plot(sorted_X, sorted_Y, 'o-',label=current_date+'_right valve')
                    # fit the curve
                    color=line[0].get_color()
                    slope, intercept=self._PlotFitting(sorted_X,sorted_Y,color,Plot=1)
                else:
                    slope, intercept=self._PlotFitting(sorted_X,sorted_Y,'r',Plot=0)
                # save fitting results
                if current_date not in self.FittingResults:
                    self.FittingResults[current_date]={}
                if current_valve not in self.FittingResults[current_date]:
                    self.FittingResults[current_date][current_valve]={}
                self.FittingResults[current_date][current_valve]=[slope,intercept]

        self.ax1.set_xlabel('valve open time(s)')
        self.ax1.set_ylabel('water(mg)')
        self.ax1.legend(loc='lower right', fontsize=8)
        self.draw()

    def _PlotFitting(self,x,y,color,Plot):
        '''fit with linear regression and plot'''           
        slope, intercept, r_value, p_value, _ = stats.linregress(x, y)
        fit_x = np.array(x)
        fit_y = np.array(x) * slope + intercept
        if Plot==1:
            self.ax1.plot(fit_x, fit_y,color=color,linestyle='--')
        return slope, intercept
    
    def _GetWaterCalibration(self,WaterCalibrationResults,current_date,current_valve):
        '''Get the water calibration results from a specific date and valve'''
        X=[]
        Y=[]
        all_valve_opentime=WaterCalibrationResults[current_date][current_valve].keys()
        for current_valve_opentime in all_valve_opentime:
            average_water=[]
            X.append(current_valve_opentime)
            all_valve_openinterval=WaterCalibrationResults[current_date][current_valve][current_valve_opentime].keys()
            for current_valve_openinterval in all_valve_openinterval:
                all_cycle=WaterCalibrationResults[current_date][current_valve][current_valve_opentime][current_valve_openinterval].keys()
                for current_cycle in all_cycle:
                    total_water=np.nanmean(WaterCalibrationResults[current_date][current_valve][current_valve_opentime][current_valve_openinterval][current_cycle])
                    if total_water != '':
                        average_water.append(total_water/float(current_cycle))
            Y.append(np.nanmean(average_water))
        sorted_X=sorted(map(float, X))
        sorted_indices = sorted(range(len(X)), key=lambda i: float(X[i]))
        sorted_Y = [Y[i] for i in sorted_indices]
        return sorted_X,sorted_Y

class PlotLickDistribution(FigureCanvas):
    def __init__(self,GeneratedTrials=None,dpi=100,width=5, height=4):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        gs = GridSpec(10, 51, wspace = 3, hspace = 0.1, bottom = 0.1, top = 0.95, left = 0.04, right = 0.98)
        self.ax1 = self.fig.add_subplot(gs[1:9, 2:11])
        self.ax2 = self.fig.add_subplot(gs[1:9, 12:21])
        self.ax3 = self.fig.add_subplot(gs[1:9, 22:31])
        self.ax4 = self.fig.add_subplot(gs[1:9, 32:41])
        self.ax5 = self.fig.add_subplot(gs[1:9, 42:51])

        self.ax1.get_shared_y_axes().join(self.ax1, self.ax2,self.ax3,self.ax4,self.ax5)
        self.ax1.get_shared_x_axes().join(self.ax1, self.ax2,self.ax3,self.ax4,self.ax5)
        self.ax2.set_yticks([])
        self.ax3.set_yticks([])
        self.ax4.set_yticks([])
        self.ax5.set_yticks([])
        
        FigureCanvas.__init__(self, self.fig)

    def _Update(self,GeneratedTrials=None):
        self.ax1.cla()
        self.ax2.cla()
        self.ax3.cla()
        self.ax4.cla()
        self.ax5.cla()
        self.ax2.set_yticks([])
        self.ax3.set_yticks([])
        self.ax4.set_yticks([])
        self.ax5.set_yticks([]) 
        self.ax1.set_title('Left licks', fontsize=8)
        self.ax2.set_title('Right licks', fontsize=8)
        self.ax3.set_title('Left to right licks', fontsize=8)
        self.ax4.set_title('Right to left licks', fontsize=8)
        self.ax5.set_title('All licks', fontsize=8)
        if GeneratedTrials==None:
            return
        # Custom x-axis values
        custom_x_values = np.linspace(-0.3, 0.3, 100)
        self.ax1.hist(np.diff(GeneratedTrials.B_LeftLickTime), bins=custom_x_values, color='red', alpha=0.7,label='Left licks')
        self.ax2.hist(np.diff(GeneratedTrials.B_RightLickTime), bins=custom_x_values, color='blue', alpha=0.7,label='Right licks')
        LeftLicksIndex=np.zeros_like(GeneratedTrials.B_LeftLickTime)
        RightLicksIndex=np.ones_like(GeneratedTrials.B_RightLickTime)
        AllLicks=np.concatenate((GeneratedTrials.B_LeftLickTime,GeneratedTrials.B_RightLickTime))
        AllLicksIndex=np.concatenate((LeftLicksIndex,RightLicksIndex))
        AllLicksSorted=np.sort(AllLicks)
        AllLicksSortedDiff=np.diff(AllLicksSorted)
        SortedIndex=np.argsort(AllLicks)
        AllLicksIndexSorted=AllLicksIndex[SortedIndex]
        AllLicksIndexSortedDiff=np.diff(AllLicksIndexSorted)
        LeftToRightLicks=AllLicksSortedDiff[AllLicksIndexSortedDiff==1]
        RightToLeftLicks=AllLicksSortedDiff[AllLicksIndexSortedDiff==-1]
        self.ax3.hist(LeftToRightLicks, bins=custom_x_values, color='black', alpha=0.7,label='Left to right licks')
        self.ax4.hist(RightToLeftLicks, bins=custom_x_values, color='black', alpha=0.7,label='Right to left licks')
        self.ax5.hist(AllLicksSortedDiff, bins=custom_x_values, color='black', alpha=0.7,label='All licks')

        self.ax1.set_xlim(-0.01, 0.3)
        self.ax3.set_xlabel('time (s)')
        self.ax1.set_ylabel('counts')
        self.draw() 

class PlotTimeDistribution(FigureCanvas):
    '''Plot the simulated distribution of ITI/Delay/Block length'''
    def __init__(self,GeneratedTrials=None,dpi=100,width=5, height=4):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        gs = GridSpec(10, 31, wspace = 3, hspace = 0.1, bottom = 0.1, top = 0.95, left = 0.04, right = 0.98)
        self.ax1 = self.fig.add_subplot(gs[1:9, 2:11])
        self.ax2 = self.fig.add_subplot(gs[1:9, 12:21])
        self.ax3 = self.fig.add_subplot(gs[1:9, 22:31])
        FigureCanvas.__init__(self, self.fig)
    def _Update(self,win):
        # randomly draw a block length between Min and Max
        SampleMethods=win.Randomness.currentText()
        # block length
        Min=float(win.BlockMin.text())
        Max=float(win.BlockMax.text())
        Beta=float(win.BlockBeta.text())
        DataType='int'
        SampledBlockLen=self._Sample(Min=Min,Max=Max,SampleMethods=SampleMethods,Beta=Beta,DataType=DataType)
        # ITI 
        Min=float(win.ITIMin.text())
        Max=float(win.ITIMax.text())
        Beta=float(win.ITIBeta.text())
        DataType='float'
        SampledITI=self._Sample(Min=Min,Max=Max,SampleMethods=SampleMethods,Beta=Beta,DataType=DataType)
        # Delay
        Min=float(win.DelayMin.text())
        Max=float(win.DelayMax.text())
        Beta=float(win.DelayBeta.text())
        DataType='float'
        SampledDelay=self._Sample(Min=Min,Max=Max,SampleMethods=SampleMethods,Beta=Beta,DataType=DataType)
        self.ax1.cla()
        self.ax2.cla()
        self.ax3.cla()
        Re1=self.ax1.hist(SampledBlockLen,bins=100)
        Re2=self.ax2.hist(SampledITI,bins=100)
        Re3=self.ax3.hist(SampledDelay,bins=100)
        self.ax1.set_xlabel('Block length (trial)')
        self.ax1.set_ylabel('counts')
        self.ax1.set_title('block length \n(average='+str(np.round(np.nanmean(SampledBlockLen),2))+')',fontsize=10)
        self.ax2.set_title('ITI time \n(average='+str(np.round(np.nanmean(SampledITI),2))+')',fontsize=10)
        self.ax3.set_title('Delay time \n(average='+str(np.round(np.nanmean(SampledDelay),2))+')',fontsize=10)
        self.ax1.plot([np.nanmean(SampledBlockLen),np.nanmean(SampledBlockLen)],[0,np.max(Re1[0])],label='Average')
        self.ax2.plot([np.nanmean(SampledITI),np.nanmean(SampledITI)],[0,np.max(Re2[0])])
        self.ax3.plot([np.nanmean(SampledDelay),np.nanmean(SampledDelay)],[0,np.max(Re3[0])])
        self.ax1.legend(loc='upper right', fontsize=8)
        self.ax2.set_xlabel('time (s)')
        self.ax3.set_xlabel('time (s)')
        self.draw() 

    def _Sample(self,Min,Max,SampleMethods,SampleTime=100000,Beta=None,DataType='float'):
        if SampleMethods=='Exponential':
            Sampled = np.random.exponential(Beta,SampleTime)+Min
        elif SampleMethods=='Even':
            Sampled = np.random.uniform(Min,Max,SampleTime)
        Sampled[Sampled>Max]=Max
        if DataType=='int':
            Sampled=Sampled.astype(int)
        return Sampled
