cd /d C:\Users\svc_aind_behavior\Documents\GitHub\dynamic-foraging-task\src\workflows\Cameras
set "logfile=C:\Users\svc_aind_behavior\Documents\foraging_gui_logs\bonsai_log.txt"
echo --------------------------- >>%logfile%
echo %date% %time% >>%logfile%
start C:\Users\svc_aind_behavior\Documents\GitHub\dynamic-foraging-task\bonsai\bonsai Camera_boxA.bonsai --no-editor >>%logfile% 2>&1


