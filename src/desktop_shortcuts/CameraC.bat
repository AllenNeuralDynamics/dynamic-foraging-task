cd /d C:\Users\svc_aind_behavior\Documents\camera_workflows
echo off
mode 50,10
cls
start /B C:\Users\svc_aind_behavior\Documents\GitHub\dynamic-foraging-task\bonsai\bonsai Camera_boxC.bonsai --no-editor 
powershell -window minimized -command ""
timeout 5 > NUL
title CAMERA C
echo This window controls camera C
echo Close this window if camera C is whited out

