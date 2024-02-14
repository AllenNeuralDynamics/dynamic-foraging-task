cd /d C:\Users\%USERNAME%\Documents\GitHub\dynamic-foraging-task\src\foraging_gui
call conda activate Foraging
start "" C:\Users\%USERNAME%\Documents\GitHub\dynamic-foraging-task\src\desktop_shortcuts\start_popup.bat
powershell -window minimized -command ""
python Foraging.py 1 --no-bonsai-ide
timeout 3600 > NUL
:: Open the GUI, minimize the console
