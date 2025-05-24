@echo off
setlocal

:: Create a temporary PowerShell script
set "tempPSScript=%temp%\temp_delete_desktop_ini.ps1"

:: Write the PowerShell script to the temporary file
(
echo # PowerShell script to delete all desktop.ini files recursively
echo # Get the current directory
echo $CurrentDirectory = Get-Location
echo # Find and delete all desktop.ini files
echo Get-ChildItem -Path $CurrentDirectory -Recurse -Force -Filter "desktop.ini" ^| ForEach-Object {
echo     Remove-Item $_.FullName -Force
echo     Write-Output "Deleted: $($_.FullName)"
echo }
echo Write-Output "Done!"
) > "%tempPSScript%"

:: Run the PowerShell script
powershell.exe -ExecutionPolicy Bypass -File "%tempPSScript%"

:: Clean up the temporary PowerShell script
del "%tempPSScript%"

pause
endlocal
