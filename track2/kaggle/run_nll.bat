@echo off
cd /d %~dp0
"%USERPROFILE%\kev\.venv\Scripts\python.exe" question_nll_embed.py > run_log.txt 2>&1
echo DONE >> run_log.txt
