#ifndef UNICODE
#define UNICODE
#endif
#ifndef _UNICODE
#define _UNICODE
#endif
#include <windows.h>
#include <shellapi.h>
#include <algorithm>
#include <cwchar>
#include <string>
#include <vector>

static void enableHighDpi() {
    using SetDpiContext = BOOL (WINAPI *)(HANDLE);
    auto function = reinterpret_cast<SetDpiContext>(
        GetProcAddress(GetModuleHandleW(L"user32.dll"), "SetProcessDpiAwarenessContext"));
    if (!function || !function(reinterpret_cast<HANDLE>(-4))) SetProcessDPIAware();
    SetEnvironmentVariableW(L"SDL_WINDOWS_DPI_AWARENESS", L"permonitorv2");
}

static unsigned automaticScale(bool fullscreen) {
    MONITORINFO monitor{sizeof(MONITORINFO)};
    GetMonitorInfoW(MonitorFromPoint(POINT{0, 0}, MONITOR_DEFAULTTOPRIMARY), &monitor);
    RECT area = fullscreen ? monitor.rcMonitor : monitor.rcWork;
    unsigned height = std::max(480L, area.bottom - area.top - (fullscreen ? 0 : 48));
    unsigned width = std::max(320L, area.right - area.left - (fullscreen ? 0 : 32));
    unsigned scale = fullscreen ? (height + 479) / 480 : std::min(height / 480, width / 320);
    return std::clamp(scale, 1u, 6u);
}

int WINAPI wWinMain(HINSTANCE, HINSTANCE, PWSTR, int) {
    enableHighDpi();
    std::vector<wchar_t> path(32768);
    DWORD length = GetModuleFileNameW(nullptr, path.data(), static_cast<DWORD>(path.size()));
    if (!length || length >= path.size()) return 1;
    std::wstring root(path.data(), length);
    root.resize(root.find_last_of(L"\\/"));
    std::wstring runtime = root + L"\\runtime";
    std::wstring executable = runtime + L"\\touchHLE.exe";
    std::wstring game = root + L"\\game\\MachDefense.app";
    std::wstring settings = root + L"\\Display.ini";
    bool fullscreen = GetPrivateProfileIntW(L"Display", L"Fullscreen", 0, settings.c_str()) != 0;
    unsigned scale = GetPrivateProfileIntW(L"Display", L"Scale", 0, settings.c_str());
    if (scale > 6) scale = 0;
    int argumentCount = 0;
    LPWSTR *arguments = CommandLineToArgvW(GetCommandLineW(), &argumentCount);
    bool valid = arguments != nullptr;
    for (int i = 1; valid && i < argumentCount; ++i) {
        std::wstring argument = arguments[i];
        if (argument == L"--fullscreen") fullscreen = true;
        else if (argument == L"--windowed") fullscreen = false;
        else if (argument.rfind(L"--scale=", 0) == 0) {
            const wchar_t *value = arguments[i] + 8;
            wchar_t *end = nullptr;
            unsigned long parsed = std::wcstoul(value, &end, 10);
            valid = end != value && *end == L'\0' && parsed <= 6;
            if (valid) scale = static_cast<unsigned>(parsed);
        } else valid = false;
    }
    if (arguments) LocalFree(arguments);
    if (!valid) {
        MessageBoxW(nullptr, L"启动参数无效。可用参数：\n--fullscreen：全屏\n--windowed：窗口\n--scale=0..6：渲染倍数，0 为自动", L"Heavy MACH: Defense", MB_OK | MB_ICONERROR);
        return 2;
    }
    if (scale == 0) scale = automaticScale(fullscreen);

    HANDLE mutex = CreateMutexW(nullptr, TRUE, L"Local\\HeavyMachDefenseWindowsPlayer");
    if (mutex && GetLastError() == ERROR_ALREADY_EXISTS) {
        MessageBoxW(nullptr, L"游戏已经在运行，请切换到游戏窗口。", L"Heavy MACH: Defense", MB_OK);
        CloseHandle(mutex);
        return 0;
    }
    std::wstring command = L"\"" + executable + L"\" \"" + game +
        L"\" --device-family=iphone --preferred-languages=en --no-error-popup --scale-hack=" +
        std::to_wstring(scale);
    if (fullscreen) command += L" --fullscreen";

    STARTUPINFOW startup{};
    startup.cb = sizeof(startup);
    SECURITY_ATTRIBUTES security{sizeof(SECURITY_ATTRIBUTES), nullptr, TRUE};
    MoveFileExW((runtime + L"\\launcher.log").c_str(),
                (runtime + L"\\launcher.previous.log").c_str(), MOVEFILE_REPLACE_EXISTING);
    HANDLE log = CreateFileW((runtime + L"\\launcher.log").c_str(), GENERIC_WRITE,
                             FILE_SHARE_READ | FILE_SHARE_WRITE, &security, CREATE_ALWAYS,
                             FILE_ATTRIBUTE_NORMAL, nullptr);
    HANDLE input = CreateFileW(L"NUL", GENERIC_READ, FILE_SHARE_READ | FILE_SHARE_WRITE,
                               &security, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, nullptr);
    if (log != INVALID_HANDLE_VALUE) {
        std::string display = std::string("Windows display: ") + (fullscreen ? "fullscreen" : "windowed") +
            ", render_scale=" + std::to_string(scale) + ", internal_resolution=" +
            std::to_string(320 * scale) + "x" + std::to_string(480 * scale) +
            ", DPI=permonitorv2\n";
        DWORD written = 0;
        WriteFile(log, display.data(), static_cast<DWORD>(display.size()), &written, nullptr);
    }
    if (log != INVALID_HANDLE_VALUE && input != INVALID_HANDLE_VALUE) {
        startup.dwFlags = STARTF_USESTDHANDLES;
        startup.hStdOutput = log;
        startup.hStdError = log;
        startup.hStdInput = input;
    }
    PROCESS_INFORMATION process{};
    if (!CreateProcessW(executable.c_str(), &command[0], nullptr, nullptr, TRUE,
                        CREATE_NO_WINDOW, nullptr, runtime.c_str(), &startup, &process)) {
        std::wstring message = L"无法启动游戏。请保留完整的 windows 文件夹。\nWindows 错误代码：" +
            std::to_wstring(GetLastError());
        MessageBoxW(nullptr, message.c_str(), L"Heavy MACH: Defense", MB_OK | MB_ICONERROR);
        if (log != INVALID_HANDLE_VALUE) CloseHandle(log);
        if (input != INVALID_HANDLE_VALUE) CloseHandle(input);
        if (mutex) { ReleaseMutex(mutex); CloseHandle(mutex); }
        return 1;
    }
    if (log != INVALID_HANDLE_VALUE) CloseHandle(log);
    if (input != INVALID_HANDLE_VALUE) CloseHandle(input);
    CloseHandle(process.hThread);
    WaitForSingleObject(process.hProcess, INFINITE);
    DWORD result = 0;
    GetExitCodeProcess(process.hProcess, &result);
    CloseHandle(process.hProcess);
    if (mutex) { ReleaseMutex(mutex); CloseHandle(mutex); }
    if (result != 0) {
        std::wstring message = L"游戏运行中遇到错误。日志位于：\n" + runtime + L"\\launcher.log";
        MessageBoxW(nullptr, message.c_str(), L"Heavy MACH: Defense", MB_OK | MB_ICONERROR);
    }
    return static_cast<int>(result);
}
