set "logfile=C:\Users\alex.piet\foraging_gui_logs\github_log.txt"
set "repo=C:\Users\alex.piet\dynamic-foraging-task"
cd %repo%
echo dynamic-foraging-gui update >>%logfile%
echo %date% >>%logfile%
::git checkout main >>C:\Users\svc_aind_behavior\foraging_gui_logs\github_log.txt 2>&1
::git reset --hard >>C:\Users\svc_aind_behavior\foraging_gui_logs\github_log.txt 2>&1
::git pull origin main >>C:\Users\svc_aind_behavior\foraging_gui_logs\github_log.txt 2>&1
echo --------------------------- >>%logfile%
