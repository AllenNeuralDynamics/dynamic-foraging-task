set "logfile=C:\Users\%USERNAME%\Documents\foraging_gui_logs\github_log.txt"
set "repo=C:\Users\%USERNAME%\Documents\GitHub\dynamic-foraging-task"
set "branch=production_testing"
cd %repo%
echo --------------------------- >>%logfile%
echo %date% %time% >>%logfile%
echo dynamic-foraging-gui update to %branch% >>%logfile%
echo running git fetch >>%logfile%
git fetch origin main >>%logfile% 2>&1
git fetch origin %branch% >>%logfile% 2>&1
echo running git stash, and changing branch >>%logfile%
git stash >>%logfile% 2>&1
git checkout %branch% >>%logfile% 2>&1
git reset --hard >>%logfile% 2>&1
git pull origin %branch% >>%logfile% 2>&1
echo waiting thirty seconds for logging to finish >>%logfile%
timeout 30 >NUL
git status >>%logfile% 2>&1
