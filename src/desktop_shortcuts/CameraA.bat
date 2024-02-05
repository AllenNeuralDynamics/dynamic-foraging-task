cd /d C:\Users\svc_aind_behavior\Documents\camera_workflows
echo off
mode 50,10
cls
start /B C:\Users\svc_aind_behavior\Documents\GitHub\dynamic-foraging-task\bonsai\bonsai Camera_boxA.bonsai --no-editor 
powershell -window minimized -command ""
timeout 5 > NUL
title CAMERA A
echo This window controls camera A
echo Close this window if camera A is whited out

