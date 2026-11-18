@echo off
rem Keeps the trend bot running on a Windows PC: starts it, and starts it again a minute after it exits.
rem Lecture 24 §10. Memory: a few MB for this loop, against hundreds of MB for Docker.
rem   - A crash, or the PC waking from sleep with the bot gone: restarted within a minute.
rem   - The bot itself refuses to start twice (data\bot.lock), so the loop can never create a second bot.
rem   - To stop for good: create capstone\data\NO_RESTART, then stop the bot (Ctrl+C in its window).
rem   - Start it at log-on with Windows Task Scheduler (see capstone\README.md).
rem Python: set BOT_PYTHON to your environment's python.exe; otherwise the trading-env next to the repository, otherwise "python".
setlocal
cd /d "%~dp0\..\.."
if not defined BOT_PYTHON set "BOT_PYTHON=%~dp0..\..\..\trading-env\Scripts\python.exe"
if not exist "%BOT_PYTHON%" set "BOT_PYTHON=python"

:loop
if exist "capstone\data\NO_RESTART" (
    echo %date% %time% NO_RESTART found: supervisor stops>> "capstone\data\supervisor.log"
    exit /b 0
)
echo %date% %time% starting the bot>> "capstone\data\supervisor.log"
"%BOT_PYTHON%" -X utf8 -m capstone.run_bot >> "capstone\data\bot.out.log" 2>&1
echo %date% %time% the bot exited with code %errorlevel%; restart in 60 s>> "capstone\data\supervisor.log"
timeout /t 60 /nobreak >nul
goto loop
