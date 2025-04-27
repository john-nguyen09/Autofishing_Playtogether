# Autofishing_Playtogether
## 1. Overview
Autofishing is a tool that was made by me. It will help you fishing in Play together.

## 2. How to use
### 1. Installation
- LDPlayer emulator
- Python version 3.9.6
- Install dependencies:
```
pip install -r requirements.txt
```

### 2. Getting the code
You need to clone the repository using Git (if Git is already installed) or you can download the zip file.
```
git clone https://github.com/john-nguyen09/Autofishing_Playtogether.git
```

### 3. Setup in emulator
* Resolution: 960x540 (dpi 160)

### 4. Running the application
```
python AutofishingGUI.py
```

## 3. Building executable
```
pyinstaller --hiddenimport win32timezone .\Autofishing.py
pyinstaller --hiddenimport win32timezone .\AutofishingGUI.py
```