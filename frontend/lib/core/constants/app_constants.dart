class AppConstants {
  static const String appTitle = 'NSE Paper-Trading & Research';
  static const String appVersion = '0.1.0';
  /// Override at build/run time, e.g. `--dart-define=API_BASE_URL=...`.
  static const String apiBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://127.0.0.1:8000/v1',
  );
  static const String wsUrl = String.fromEnvironment(
    'WS_URL',
    defaultValue: 'ws://127.0.0.1:8000/v1/ws',
  );

  // Safety Disclaimers
  static const String paperTradingBanner = 'PAPER TRADING SIMULATION ONLY';
  static const String safetyWarning =
      'Real broker order execution is permanently disabled. All orders and trades are strictly simulated.';
}
