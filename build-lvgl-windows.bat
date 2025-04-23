@echo off
setlocal enabledelayedexpansion

REM This script is intended to be run on Windows with Git and MSBuild in PATH
REM Usage: build-lvgl-windows.bat <output_dll_path>

REM Set output path from argument
set OUTPUT_DLL=%1

REM Create temp directory
set TMPDIR=%TEMP%\lvgl
if exist "%TMPDIR%" rmdir /s /q "%TMPDIR%"
mkdir "%TMPDIR%"
cd /d "%TMPDIR%"

REM Clone lvgl/lv_port_pc_visual_studio
git clone --single-branch --branch lvgl-python --depth 1 --recurse-submodules --shallow-submodules https://github.com/jbatonnet/lv_port_pc_visual_studio.git
cd lv_port_pc_visual_studio

REM Build the DLL using MSBuild and the provided .sln/.vcxproj
REM Replace 'lvgl.vcxproj' with the actual project file name if different
MSBuild.exe lvgl.vcxproj /p:Configuration=Release /p:Platform=x64

REM Copy the output DLL to the desired location
copy /Y ".\x64\Release\lvgl.dll" "%OUTPUT_DLL%"
