@echo off
cd /d %~dp0
set VENV=D:\venv_gpu
set BASEPY=%APPDATA%\uv\python\cpython-3.13-windows-x86_64-none\python.exe
if not exist "%VENV%\Scripts\python.exe" (
  echo Creating GPU environment...
  "%BASEPY%" -m venv "%VENV%"
  "%VENV%\Scripts\python.exe" -m pip install --upgrade pip
  "%VENV%\Scripts\python.exe" -m pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cu126
  "%VENV%\Scripts\python.exe" -m pip install --no-cache-dir transformers pandas numpy datasets
)
"%VENV%\Scripts\python.exe" -c "import torch;print('CUDA:',torch.cuda.is_available(),torch.cuda.get_device_name(0) if torch.cuda.is_available() else '')"
set HF_HOME=D:\hf_cache
set HF_HUB_DISABLE_SYMLINKS_WARNING=1
"%VENV%\Scripts\python.exe" -u domain_bank.py > bank_log.txt 2>&1
echo DONE >> bank_log.txt
echo Finished. You can close this window.
pause
