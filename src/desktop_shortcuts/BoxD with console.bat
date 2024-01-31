cd /d C:\Users\%USERNAME%\Documents\GitHub\dynamic-foraging-task\src\foraging_gui
call conda activate Foraging
:: This version starts with a console window
python Foraging.py 4
timeout 3600 > NUL

