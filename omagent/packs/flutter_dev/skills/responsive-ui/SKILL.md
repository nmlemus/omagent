---
name: responsive-ui
description: Responsive UI design for Flutter — adaptive layouts for phones, tablets, Android, and iOS
allowed-tools: flutter_cli read_file write_file dart_analyze
metadata:
  pack: flutter_dev
  version: "1.0"
  level: 1
  user-invocable: true
  triggers:
    - responsive
    - layout
    - screen size
    - tablet
    - adaptive
    - material design
    - cupertino
---

## Responsive UI for Flutter

### Layout Strategies
- Use `LayoutBuilder` and `MediaQuery` for responsive layouts
- Use `Flex`, `Expanded`, and `Flexible` for proportional sizing
- Use `ConstrainedBox` for min/max sizes
- Wrap content with `SafeArea` for notches and system bars

### Platform Adaptive Widgets
- `Switch.adaptive`, `Slider.adaptive` for platform-native feel
- Check `Platform.isIOS` / `Platform.isAndroid` for platform logic
- Use `CupertinoPageRoute` on iOS, `MaterialPageRoute` on Android

### Breakpoints
- Phone portrait: < 600dp
- Phone landscape / small tablet: 600-840dp
- Tablet: 840-1200dp
- Desktop: > 1200dp

### Best Practices
- Test on multiple screen sizes with Device Preview
- Support both portrait and landscape
- Use `FractionallySizedBox` for percentage-based sizing
- Never use fixed pixel widths for layout containers
