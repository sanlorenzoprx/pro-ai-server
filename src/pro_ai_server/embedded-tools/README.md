# Packaged Embedded Platform Tools

Release artifacts can place Android Platform Tools here so installed builds can
resolve bundled ADB without depending on a source checkout:

```text
src/pro_ai_server/embedded-tools/windows/platform-tools/adb.exe
src/pro_ai_server/embedded-tools/windows/platform-tools/AdbWinApi.dll
src/pro_ai_server/embedded-tools/windows/platform-tools/AdbWinUsbApi.dll
```

The MVP uses `adb` only. Do not call `fastboot` from MVP behavior.
