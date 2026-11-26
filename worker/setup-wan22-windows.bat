@echo off
setlocal
cd /d "%~dp0"
echo RF983 MOTION - Wan 2.2 TI2V-5B setup
echo.
echo This setup does NOT download model weights or install CUDA/PyTorch automatically.
echo Wan TI2V-5B needs a compatible NVIDIA GPU with about 24 GB VRAM.
echo Your existing Intel integrated graphics laptop is not a supported render device.
echo.
where nvidia-smi >nul 2>nul
if errorlevel 1 (
  echo BLOCKED: nvidia-smi was not found. No supported NVIDIA GPU/driver is detected.
  pause
  exit /b 2
)
nvidia-smi
echo.
echo Read docs/WAN22_ENGINE_SETUP.md before installing anything.
echo Run: py -3 wan22_engine.py --check
echo.
pause
