import 'dart:convert';
import 'package:http/http.dart' as http;
import '../models/api_models.dart';

class ApiService {
  static const String defaultBaseUrl = 'http://127.0.0.1:8000/v1';
  final String baseUrl;

  ApiService({this.baseUrl = defaultBaseUrl});

  Future<bool> checkHealth() async {
    try {
      final response = await http
          .get(Uri.parse('$baseUrl/health'))
          .timeout(const Duration(seconds: 4));
      return response.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  Future<Map<String, dynamic>?> getHealthDetails() async {
    try {
      final response = await http
          .get(Uri.parse('$baseUrl/health'))
          .timeout(const Duration(seconds: 4));
      if (response.statusCode == 200) {
        return json.decode(response.body) as Map<String, dynamic>?;
      }
    } catch (_) {}
    return null;
  }

  Future<MarketStatusInfo?> getMarketStatus() async {
    try {
      final response = await http
          .get(Uri.parse('$baseUrl/market/status'))
          .timeout(const Duration(seconds: 4));
      if (response.statusCode == 200) {
        final body = json.decode(response.body);
        if (body['success'] == true && body['data'] != null) {
          return MarketStatusInfo.fromJson(body['data']);
        }
      }
    } catch (_) {}
    return null;
  }

  Future<PortfolioSummary?> getPortfolioSummary() async {
    try {
      final response = await http
          .get(Uri.parse('$baseUrl/portfolio/summary'))
          .timeout(const Duration(seconds: 4));
      if (response.statusCode == 200) {
        final body = json.decode(response.body);
        if (body['success'] == true && body['data'] != null) {
          return PortfolioSummary.fromJson(body['data']);
        }
      }
    } catch (_) {}
    return null;
  }

  Future<TradingSessionSummary?> getTodaySession() async {
    try {
      final response = await http
          .get(Uri.parse('$baseUrl/sessions/today'))
          .timeout(const Duration(seconds: 4));
      if (response.statusCode == 200) {
        final body = json.decode(response.body);
        if (body['success'] == true && body['data'] != null) {
          return TradingSessionSummary.fromJson(body['data']);
        }
      }
    } catch (_) {}
    return null;
  }

  Future<List<ScannerCandidate>> getScannerCandidates() async {
    try {
      final response = await http
          .get(Uri.parse('$baseUrl/scanner/candidates'))
          .timeout(const Duration(seconds: 4));
      if (response.statusCode == 200) {
        final body = json.decode(response.body);
        if (body['success'] == true && body['data'] != null) {
          final data = body['data'];
          final list = (data is Map && data['candidates'] is List)
              ? data['candidates'] as List<dynamic>
              : (data is List ? data : <dynamic>[]);
          return list
              .map((e) => ScannerCandidate.fromJson(e as Map<String, dynamic>))
              .toList();
        }
      }
    } catch (_) {}
    return [];
  }

  Future<List<PositionItem>> getPositions() async {
    try {
      final response = await http
          .get(Uri.parse('$baseUrl/portfolio/positions'))
          .timeout(const Duration(seconds: 4));
      if (response.statusCode == 200) {
        final body = json.decode(response.body);
        if (body['success'] == true && body['data'] != null) {
          final data = body['data'];
          final list = (data is Map && data['items'] is List)
              ? data['items'] as List<dynamic>
              : (data is List ? data : <dynamic>[]);
          return list
              .map((e) => PositionItem.fromJson(e as Map<String, dynamic>))
              .toList();
        }
      }
    } catch (_) {}
    return [];
  }

  Future<List<PaperOrderItem>> getOrders() async {
    try {
      final response = await http
          .get(Uri.parse('$baseUrl/orders'))
          .timeout(const Duration(seconds: 4));
      if (response.statusCode == 200) {
        final body = json.decode(response.body);
        if (body['success'] == true && body['data'] != null) {
          final data = body['data'];
          final list = (data is Map && data['items'] is List)
              ? data['items'] as List<dynamic>
              : (data is List ? data : <dynamic>[]);
          return list
              .map((e) => PaperOrderItem.fromJson(e as Map<String, dynamic>))
              .toList();
        }
      }
    } catch (_) {}
    return [];
  }

  Future<List<TradeLogItem>> getTradeLogs({int page = 1, int pageSize = 50}) async {
    try {
      final response = await http
          .get(Uri.parse('$baseUrl/journal/trades?page=$page&page_size=$pageSize'))
          .timeout(const Duration(seconds: 4));
      if (response.statusCode == 200) {
        final body = json.decode(response.body);
        if (body['success'] == true && body['data'] != null) {
          final list = body['data']['items'] as List<dynamic>? ?? [];
          return list
              .map((e) => TradeLogItem.fromJson(e as Map<String, dynamic>))
              .toList();
        }
      }
    } catch (_) {}
    return [];
  }

  Future<List<SignalItem>> getRecentSignals({int page = 1, int pageSize = 10}) async {
    try {
      final response = await http
          .get(Uri.parse('$baseUrl/scanner/signals?page=$page&page_size=$pageSize'))
          .timeout(const Duration(seconds: 4));
      if (response.statusCode == 200) {
        final body = json.decode(response.body);
        if (body['success'] == true && body['data'] != null) {
          final list = body['data']['items'] as List<dynamic>? ?? [];
          return list
              .map((e) => SignalItem.fromJson(e as Map<String, dynamic>))
              .toList();
        }
      }
    } catch (_) {}
    return [];
  }

  Future<List<SystemLogItem>> getSystemLogs({int page = 1, int pageSize = 10}) async {
    try {
      final response = await http
          .get(Uri.parse('$baseUrl/logs/system?page=$page&page_size=$pageSize'))
          .timeout(const Duration(seconds: 4));
      if (response.statusCode == 200) {
        final body = json.decode(response.body);
        if (body['success'] == true && body['data'] != null) {
          final list = body['data']['items'] as List<dynamic>? ?? [];
          return list
              .map((e) => SystemLogItem.fromJson(e as Map<String, dynamic>))
              .toList();
        }
      }
    } catch (_) {}
    return [];
  }

  Future<RiskStatus?> getRiskStatus() async {
    try {
      final response = await http
          .get(Uri.parse('$baseUrl/risk/status'))
          .timeout(const Duration(seconds: 4));
      if (response.statusCode == 200) {
        final body = json.decode(response.body);
        if (body['success'] == true && body['data'] != null) {
          return RiskStatus.fromJson(body['data']);
        }
      }
    } catch (_) {}
    return null;
  }

  Future<List<BacktestRunSummary>> getBacktestRuns() async {
    try {
      final response = await http
          .get(Uri.parse('$baseUrl/backtest/runs'))
          .timeout(const Duration(seconds: 4));
      if (response.statusCode == 200) {
        final body = json.decode(response.body);
        if (body['success'] == true && body['data'] != null) {
          final list = body['data']['items'] as List<dynamic>? ?? [];
          return list
              .map((e) => BacktestRunSummary.fromJson(e as Map<String, dynamic>))
              .toList();
        }
      }
    } catch (_) {}
    return [];
  }

  Future<BacktestRunDetail?> getBacktestRunDetail(int runId) async {
    try {
      final response = await http
          .get(Uri.parse('$baseUrl/backtest/runs/$runId'))
          .timeout(const Duration(seconds: 6));
      if (response.statusCode == 200) {
        final body = json.decode(response.body);
        if (body['success'] == true && body['data'] != null) {
          return BacktestRunDetail.fromJson(body['data']);
        }
      }
    } catch (_) {}
    return null;
  }

  Future<BacktestRunSummary?> runBacktest({
    required String strategyName,
    required List<String> symbols,
    required String startDate,
    required String endDate,
    required double initialCapital,
    String timeframe = '5m',
  }) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/backtest/run'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({
          'strategy_name': strategyName,
          'symbols': symbols,
          'start_date': startDate,
          'end_date': endDate,
          'initial_capital': initialCapital,
          'timeframe': timeframe,
        }),
      ).timeout(const Duration(seconds: 25));

      if (response.statusCode == 202 || response.statusCode == 200) {
        final body = json.decode(response.body);
        if (body['success'] == true && body['data'] != null) {
          return BacktestRunSummary.fromJson(body['data']);
        }
      }
    } catch (_) {}
    return null;
  }
}

final apiService = ApiService();
