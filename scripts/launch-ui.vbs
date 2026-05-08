Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
ps1 = fso.BuildPath(scriptDir, "launch-ui.ps1")
command = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File """ & ps1 & """"
shell.Run command, 0, False
