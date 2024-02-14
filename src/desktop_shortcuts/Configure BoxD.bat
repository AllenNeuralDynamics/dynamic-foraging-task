cd /d C:\Users\%USERNAME%\Documents\GitHub\dynamic-foraging-task\src\foraging_gui
call conda activate Foraging
python Foraging.py 4
timeout 3600 > NUL
:: Open the GUI, the Bonsai IDE, and leave this console open

