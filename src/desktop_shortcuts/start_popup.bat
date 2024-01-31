echo off
mode 70,19
title Hello!
Set /a num=(%Random% %%9)+1
color %num%
cls
echo.
echo.
echo                   .--,       .--,
echo                  ( (  \.---./  ) )
echo                   '.__/o   o\__.'
echo                      {=  ^^  =}
echo                       ^>  -  ^<
echo        ___________.""`-------`"".____________
echo       /  Hi, the GUI is starting!     O      \
echo       \                      o               /
echo       /  .    O       Please wait!       o   \
echo       \                                      /         __
echo       /        You can close this window!    \     _.-'  `.
echo       \______________o__________o____________/ .-~^^        `~--'
echo                     ___)( )(___        `-.___.'
echo                    (((__) (__)))

timeout 30 >nul
exit

