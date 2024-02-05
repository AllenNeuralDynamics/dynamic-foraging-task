cd /d C:\Users\svc_aind_behavior\Documents\camera_workflows
echo off
mode 50,10
cls
start /B C:\Users\svc_aind_behavior\Documents\GitHub\dynamic-foraging-task\bonsai\bonsai Camera_boxB.bonsai --no-editor 
powershell -window minimized -command ""
timeout 5 > NUL
title CAMERA B
echo This window controls camera B
echo Close this window if camera B is whited out

