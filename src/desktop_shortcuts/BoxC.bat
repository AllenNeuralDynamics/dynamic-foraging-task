cd /d C:\Users\svc_aind_behavior\Documents\GitHub\dynamic-foraging-task\src\foraging_gui
call conda activate Foraging
start "" C:\Users\svc_aind_behavior\Documents\GitHub\dynamic-foraging-task\src\desktop_shortcuts\start_popup.bat
powershell -window minimized -command ""
python Foraging.py 3 --no-bonsai-ide
timeout 3600 > NUL

