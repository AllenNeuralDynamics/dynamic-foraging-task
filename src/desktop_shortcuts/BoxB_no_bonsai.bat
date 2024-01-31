cd /d C:\Users\svc_aind_behavior\Documents\GitHub\dynamic-foraging-task\src\foraging_gui
call conda activate Foraging
:: This version starts with a console window
start "" C:\Users\svc_aind_behavior\Documents\GitHub\dynamic-foraging-task\src\desktop_shortcuts\start_popup.bat
python Foraging.py 2 --no-bonsai-ide
timeout 3600 > NUL

