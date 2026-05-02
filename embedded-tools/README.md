# Embedded Platform Tools

Release builds of Pro AI Server should include Android Platform Tools here:

embedded-tools/windows/platform-tools/

Expected Windows files:

- adb.exe
- AdbWinApi.dll
- AdbWinUsbApi.dll
- fastboot.exe

The MVP uses adb for:

- phone detection
- hardware scanning
- pushing setup scripts
- creating the USB tunnel with adb reverse tcp:11434 tcp:11434

fastboot is not used in the MVP.
