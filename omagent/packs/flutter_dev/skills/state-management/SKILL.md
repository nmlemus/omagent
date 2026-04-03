---
name: state-management
description: State management patterns for Flutter — Riverpod, Bloc, and Provider with best practices
triggers:
  - state management
  - riverpod
  - bloc
  - provider
  - state
  - notifier
allowed-tools: flutter_cli read_file write_file pubspec_manager dart_analyze
user-invocable: true
level: 2
metadata:
  pack: flutter_dev
  version: "1.0"
---

## State Management in Flutter

### Riverpod (Recommended)
- Add `flutter_riverpod` to dependencies
- Wrap app with `ProviderScope`
- Use `Provider` for simple computed values
- Use `StateNotifierProvider` for complex mutable state
- Use `FutureProvider` / `StreamProvider` for async data
- Scope providers at the feature level

### Bloc Pattern
- Add `flutter_bloc` to dependencies
- Define Events (input), States (output), and Bloc (logic)
- Use `BlocBuilder` for UI rendering
- Use `BlocListener` for side effects (navigation, snackbars)
- Use `BlocConsumer` when you need both
- Keep blocs feature-scoped, not global

### Provider (Simple Apps)
- Add `provider` to dependencies
- Use `ChangeNotifierProvider` for mutable state
- Use `FutureProvider` for async operations
- Use `MultiProvider` at app root for multiple providers

### When to Use What
- **Riverpod**: Most projects, best testability, no BuildContext dependency
- **Bloc**: Large teams, strict separation of concerns, event-driven
- **Provider**: Simple apps, quick prototypes, familiar with ChangeNotifier
