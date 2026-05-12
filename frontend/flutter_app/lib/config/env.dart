import 'package:flutter/foundation.dart';

class AppConfig {
  static const String baseUrl = 'http://localhost:57094';
  static const bool useMock = bool.fromEnvironment('USE_MOCK', defaultValue: false);
  static bool get isWeb => kIsWeb;
}