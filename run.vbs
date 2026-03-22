' Запускает GUI без консольного окна.
' Для создания ярлыка: ПКМ на файле → Создать ярлык.
Set sh = CreateObject("WScript.Shell")
sh.CurrentDirectory = Left(WScript.ScriptFullName, InStrRev(WScript.ScriptFullName, "\") - 1)
sh.Run "uv run pythonw gui.py", 0
