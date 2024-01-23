cd /d C:\Users\svc_aind_behavior\Documents\GitHub\dynamic-foraging-task\src\foraging_gui
call conda activate Foraging
:: This version starts with a console window
python Foraging.py 1 --no-bonsai-ide
timeout 3600 > NUL

