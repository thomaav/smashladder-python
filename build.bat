@echo off
pyinstaller --onefile --noconsole --icon=static\smashladder.ico slapp.pyw
mkdir dist\conf\
xcopy /S /E static dist\static\
@RD /S /Q build
del slapp.spec
