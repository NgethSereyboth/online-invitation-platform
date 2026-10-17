# Android app shell

This is a small native Android WebView client for the existing eInvite web platform. It loads the existing server-rendered dashboard from a configured HTTPS site; it does **not** bundle or replace the Python backend. Users still need a reachable deployment, and sign-in data stays in the app's WebView origin storage (separate from Chrome's profile).

## Configure the site

Copy `local.properties.example` to `local.properties` and set `einvite.siteUrl` to the HTTPS origin of the deployment, without a path, query or fragment:

```properties
einvite.siteUrl=https://invite.example.com
```

`local.properties` is ignored by git. The default origin is `https://einvite-platform.onrender.com`.

## Build a debug APK

Requirements: JDK 17+, Android SDK Platform 37, Android Build Tools 36.0.0, and network access for the Gradle wrapper / Android Gradle Plugin / AndroidX downloads.

From the repository root (uses `android/.android-sdk` unless `ANDROID_SDK_ROOT` / `ANDROID_HOME` is set):

```sh
./android/scripts/build-apk.sh
```

Or invoke Gradle directly from the Android directory:

```sh
cd android
./gradlew assembleDebug
```

On Windows:

```powershell
cd android
.\gradlew.bat assembleDebug
```

Artifact: `android/app/build/outputs/apk/debug/app-debug.apk`. The debug APK is signed with the debug key and suitable for local installation/testing, **not** store release. Release builds need a privately held signing key and release signing configuration; never commit keystore files or passwords.

To build for a self-hosted origin, put `einvite.siteUrl=https://your-domain.example` in `local.properties`, or pass `-Peinvite.siteUrl=https://your-domain.example` to the Gradle wrapper. Only HTTPS origins are accepted.

## App behavior and security

- Navigation remains inside the app only for the configured HTTPS origin (scheme, host, and port). External HTTPS, email, and phone links open outside; cleartext HTTP is not loaded.
- JavaScript and DOM storage are enabled for the existing app; file URL access is disabled, mixed/cleartext traffic is blocked, Safe Browsing is retained, and third-party cookies are disabled.
- HTML file uploads use Android's system chooser. Live camera permission is granted only to the configured origin, only for video capture, and only after the Android runtime camera prompt.
- The WebView instance owns sign-in cookies and local storage; it does not inherit a Chrome login. Existing password/passkey site sign-in should be exercised on target devices.
- Third-party OAuth pages are opened outside the embedded app by the origin policy. If the web deployment later adds an external OAuth redirect, test its return into the WebView; no native auth/session bridge is implemented here.
- The application is online-only. The web project's service worker/cache is not a full offline app shell.

## Validation notes

Build with `:app:assembleDebug`. Install and test on an Android device/emulator to verify connectivity, sign-in, back navigation, file upload, and QR camera check-in. The APK build alone does not verify the remote deployment, actual Android WebView camera behavior, or all app flows. The debug APK built in the initial packaging pass was inspected and signature-verified; no Android device or emulator was connected for live runtime testing.
