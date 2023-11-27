set "logfile=C:\Users\alex.piet\Documents\foraging_gui_logs\github_log.txt"
set "repo=C:\Users\alex.piet\dynamic-foraging-task"
set "branch=fix_61_v2"
cd %repo%
echo dynamic-foraging-gui update to %branch% >>%logfile%
echo %date% >>%logfile%
git stash >>%logfile% 2>&1
git checkout %branch% >>%logfile% 2>&1
git reset --hard >>%logfile% 2>&1
git pull origin %branch% >>%logfile% 2>&1
echo --------------------------- >>%logfile%
