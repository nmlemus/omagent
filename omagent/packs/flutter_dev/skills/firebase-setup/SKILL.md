---
name: firebase-setup
description: Firebase project setup for Flutter — authentication, Firestore, storage, and messaging configuration
allowed-tools: flutter_cli bash read_file write_file pubspec_manager
metadata:
  pack: flutter_dev
  version: "1.0"
  level: 2
  user-invocable: true
  triggers:
    - firebase
    - firebase setup
    - firebase config
    - flutterfire
    - authentication
    - firestore
    - firebase auth
---

## Firebase Setup for Flutter

### Step 1: Prerequisites
- Ensure Firebase CLI installed: `npm install -g firebase-tools`
- Login: `firebase login`
- Install FlutterFire CLI: `dart pub global activate flutterfire_cli`

### Step 2: Configure Firebase
- From project root: `flutterfire configure`
- Select or create Firebase project
- Enable platforms (Android + iOS)

### Step 3: Add Dependencies
- Always required: `firebase_core`
- Auth: `firebase_auth`
- Database: `cloud_firestore`
- Storage: `firebase_storage`
- Push notifications: `firebase_messaging`

### Step 4: Initialize in Code
```dart
await Firebase.initializeApp(
  options: DefaultFirebaseOptions.currentPlatform,
);
```

### Step 5: Platform-Specific Setup
- iOS: Set minimum deployment target in `ios/Podfile` (13.0+)
- Android: Set `minSdkVersion >= 21` in `android/app/build.gradle`
- Run `cd ios && pod install` after adding Firebase packages

### Step 6: Security Rules
- Set up Firestore security rules
- Configure Storage security rules
- Never use open rules in production
