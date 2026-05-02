class Env {
  static const bool useMock =
  bool.fromEnvironment('USE_MOCK', defaultValue: true);

  static const String apiBaseUrl =
  String.fromEnvironment('API_BASE_URL', defaultValue: 'http://localhost:8000');
}