cd /d C:\Users\svc_aind_behavior\Documents\GitHub\dynamic-foraging-task\src\workflows\Cameras
set "logfile=C:\Users\svc_aind_behavior\Documents\foraging_gui_logs\bonsai_log.txt"
start "" pythonw Foraging.py 1
echo --------------------------- >>%logfile%
echo %date% %time% >>%logfile%
start bonsai Camera_boxA.bonsai --no-editor >>%logfile% 2>&1


