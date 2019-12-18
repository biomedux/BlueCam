@echo off

set PYTHON_PATH=C:\Users\%USERNAME%\AppData\Local\Programs\Python

if exist %PYTHON_PATH%\Python35 (
	set PYTHON_PATH=%PYTHON_PATH%\Python35
	set PYTHON_SYMBOL=cp35-cp35m
) else if exist %PYTHON_PATH%\Python37 (
	set PYTHON_PATH=%PYTHON_PATH%\Python37
	set PYTHON_SYMBOL=cp37-cp37m
) else (
	echo python not found...
	pause
	exit
)

if exist %windir%\SysWOW64 (
	set OS=64bit
	set PU=win_amd64
) else (
	set OS=32bit
	set PU=win32
)

xcopy %~dp0Package\%OS%\*.dll %~dp0 /y

%PYTHON_PATH%\Scripts\pip install %~dp0Package\%OS%\opencv_python-4.1.2.30-%PYTHON_SYMBOL%-%PU%.whl
%PYTHON_PATH%\Scripts\pip install %~dp0Package\%OS%\Pillow-6.2.1-%PYTHON_SYMBOL%-%PU%.whl
