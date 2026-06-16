start "VOICECODE Server" cmd /k "cd /d C:\Users\smats\Desktop\ANTIGRAVITY開発\声紋分析システムVOICECODE && venv\Scripts\python.exe -m src.main"
timeout /t 5 /nobreak
start "ngrok" cmd /k "C:\Users\smats\AppData\Roaming\npm\node_modules\ngrok\bin\ngrok.exe http 8000"
