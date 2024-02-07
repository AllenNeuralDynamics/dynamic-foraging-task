cd /d C:\Users\%USERNAME%\Documents\GitHub\dynamic-foraging-task\src\foraging_gui
call conda activate Foraging
start "" C:\Users\%USERNAME%\Documents\GitHub\dynamic-foraging-task\src\desktop_shortcuts\start_popup.bat
start "" pythonw Foraging.py 4
:: Open the GUI, and the Bonsai IDE, no console

