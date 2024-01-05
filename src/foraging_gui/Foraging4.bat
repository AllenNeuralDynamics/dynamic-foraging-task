cd /d C:\Users\svc_aind_behavior\Documents\GitHub\dynamic-foraging-task\src\foraging_gui
call conda activate Foraging
:: This version starts without a console window
start "" pythonw Foraging.py 4
echo Starting the GUI and Bonsai, please wait. This window will close in 20 seconds
timeout 20 >nul
:: This version starts with a console window
:: start python Foraging.py 4


