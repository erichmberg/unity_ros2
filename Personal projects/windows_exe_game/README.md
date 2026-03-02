# Neon Dodge (Windows .exe)

A small Python arcade game you can package as a Windows `.exe`.

## 1) Run from Python (quick test)

```bash
python neon_dodge.py
```

## 2) Build an `.exe` for Windows

### Requirements
- Windows PC
- Python 3.10+ installed

### Steps (PowerShell in this folder)

```powershell
pip install pyinstaller
pyinstaller --onefile --windowed --name NeonDodge neon_dodge.py
```

Your executable will be here:

```text
dist\NeonDodge.exe
```

## 3) Share it

Send only `dist\NeonDodge.exe` to friends.

---

## Controls
- **A / D** or **Left / Right**: Move
- **Space**: Start
- **R**: Restart after game over

## Notes
- No external game libraries are required (uses built-in Tkinter).
- If antivirus warns on a fresh unsigned `.exe`, that can happen with PyInstaller builds.
