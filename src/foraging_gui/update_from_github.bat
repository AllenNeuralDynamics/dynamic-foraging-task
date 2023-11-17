cd C:\Users\svc_aind_behavior\dynamic-foraging-task
echo dynamic-foraging-gui update >>C:\Users\svc_aind_behavior\foraging_gui_logs\github_log.txt
echo %date% >>C:\Users\svc_aind_behavior\foraging_gui_logs\github_log.txt
git checkout main >>C:\Users\svc_aind_behavior\foraging_gui_logs\github_log.txt 2>&1
git reset --hard >>C:\Users\svc_aind_behavior\foraging_gui_logs\github_log.txt 2>&1
git pull origin main >>C:\Users\svc_aind_behavior\foraging_gui_logs\github_log.txt 2>&1
echo --------------------------- >>C:\Users\svc_aind_behavior\foraging_gui_logs\github_log.txt
