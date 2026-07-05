@echo off
setlocal enabledelayedexpansion
:: Define LF (Line Feed) at the start of your script
set ^"LF=^

^" The empty line above is critical - do not remove

:: Function to load .env file
call :load_env_file || exit /b

endlocal

:: Function to activate the virtual environment if it exists
call :activate_virtual_environment
call :set_env_vars

exit /b


:load_env_file
    if not exist .env (
        echo Error: .env file not found.
        echo Please create a .env file with VAR_NAME=value pairs.
        exit /b 1
    )
    if exist set_env_vars.bat del set_env_vars.bat
    for /f "usebackq eol=# tokens=1,* delims==" %%A in (".env") do (
        if not "%%A"=="" echo set "%%A=%%~B" >> set_env_vars.bat
    )
    exit /b 0

:activate_virtual_environment
    if exist .venv\Scripts\activate.bat (
        echo Activated virtual environment found at .venv\Scripts\activate.bat
        call .venv\Scripts\activate.bat
    )
    exit /b 0

:set_env_vars
    endlocal
    call set_env_vars.bat
    del set_env_vars.bat
    echo Environment variables have been set.
    exit /b 0
