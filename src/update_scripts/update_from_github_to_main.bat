set "logfile=C:\Users\%USERNAME%\Documents\foraging_gui_logs\github_log.txt"
set "repo=C:\Users\%USERNAME%\Documents\GitHub\dynamic-foraging-task"
set "branch=main"
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
echo waiting thirty second for long running processes >>%logfile%
timeout 30>NUL
git status >>%logfile% 2>&1
echo removing old gui logs >>%logfile%
forfiles /p "C:\Users\%USERNAME%\Documents\foraging_gui_logs" /s /m *.* /D -30 "cmd /c del @path"
echo done >>%logfile%
