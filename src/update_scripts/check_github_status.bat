set "logfile=C:\Users\svc_aind_behavior\Documents\foraging_gui_logs\github_log.txt"
set "repo=C:\Users\svc_aind_behavior\Documents\GitHub\dynamic-foraging-task"
cd %repo%
echo --------------------------- >>%logfile%
echo %date% %time% >>%logfile%
echo status check for testing rig >>%logfile%
git status >>%logfile% 2>&1

