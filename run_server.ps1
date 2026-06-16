Set-Location "c:\Users\smats\Desktop\ANTIGRAVITY開発\声紋分析システムVOICECODE"
$env:APP_ENV = "production"
& ".\venv\Scripts\uvicorn.exe" src.main:app --host 0.0.0.0 --port 8000
