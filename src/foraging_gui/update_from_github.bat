set "logfile=C:\Users\alex.piet\foraging_gui_logs\github_log.txt"
set "repo=C:\Users\alex.piet\dynamic-foraging-task"
cd %repo%
echo dynamic-foraging-gui update >>%logfile%
echo %date% >>%logfile%
git stash >>%logfile% 2>&1
git checkout fix_61 >>%logfile% 2>&1
git reset --hard >>%logfile% 2>&1
git pull origin fix_61 >>%logfile% 2>&1
echo --------------------------- >>%logfile%
