# Firebase Setup for Flutter

When setting up Firebase in a Flutter project:

1. Ensure Firebase CLI is installed: `npm install -g firebase-tools`
2. Login: `firebase login`
3. Install FlutterFire CLI: `dart pub global activate flutterfire_cli`
4. From project root: `flutterfire configure`
5. Add firebase_core to pubspec.yaml
6. Initialize Firebase in main.dart:
   ```dart
   await Firebase.initializeApp(
     options: DefaultFirebaseOptions.currentPlatform,
   );
   ```
7. Add needed Firebase packages (auth, firestore, storage, etc.)
8. For iOS: ensure minimum deployment target is set in ios/Podfile
9. For Android: ensure minSdkVersion >= 21 in android/app/build.gradle
