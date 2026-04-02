# State Management in Flutter

Recommended patterns:

## Riverpod (Recommended)
- Add flutter_riverpod to dependencies
- Use Provider for simple values
- Use StateNotifierProvider for complex state
- Use FutureProvider/StreamProvider for async data
- Scope providers at the widget level

## Bloc
- Add flutter_bloc to dependencies
- Separate Events, States, and Bloc logic
- Use BlocBuilder, BlocListener, BlocConsumer
- Keep blocs feature-scoped

## Provider (Simple apps)
- Add provider to dependencies
- Use ChangeNotifierProvider for mutable state
- Use FutureProvider for async operations
