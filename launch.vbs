Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "powershell.exe -NoExit -File ""c:\Users\smats\Desktop\ANTIGRAVITY開発\声紋分析システムVOICECODE\run_server.ps1""", 1, False
WScript.Sleep 5000
WshShell.Run "powershell.exe -NoExit -File ""c:\Users\smats\Desktop\ANTIGRAVITY開発\声紋分析システムVOICECODE\run_ngrok.ps1""", 1, False
