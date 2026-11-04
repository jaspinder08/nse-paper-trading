import 'dart:async';
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../../core/constants/app_constants.dart';
import '../../core/theme/app_theme.dart';
import '../../models/api_models.dart';
import '../../services/api_service.dart';

class TerminalHeader extends StatefulWidget {
  final VoidCallback? onRefresh;

  const TerminalHeader({super.key, this.onRefresh});

  @override
  State<TerminalHeader> createState() => _TerminalHeaderState();
}

class _TerminalHeaderState extends State<TerminalHeader> {
  late Timer _clockTimer;
  DateTime _currentIst = DateTime.now().toUtc().add(const Duration(hours: 5, minutes: 30));
  bool _isConnected = false;
  double? _dbLatency;
  MarketStatusInfo? _marketStatus;

  @override
  void initState() {
    super.initState();
    _clockTimer = Timer.periodic(const Duration(seconds: 1), (_) {
      if (mounted) {
        setState(() {
          _currentIst = DateTime.now().toUtc().add(const Duration(hours: 5, minutes: 30));
        });
      }
    });
    _fetchHeaderData();
  }

  @override
  void dispose() {
    _clockTimer.cancel();
    super.dispose();
  }

  Future<void> _fetchHeaderData() async {
    final healthDetails = await apiService.getHealthDetails();
    final market = await apiService.getMarketStatus();
    if (mounted) {
      setState(() {
        _isConnected = healthDetails?['status'] == 'healthy';
        _dbLatency = (healthDetails?['details']?['db_latency_ms'] as num?)?.toDouble();
        _marketStatus = market;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;

    final bgColor = isDark ? AppTheme.darkSurface : AppTheme.lightSurface;
    final borderColor = isDark ? AppTheme.darkBorder : AppTheme.lightBorder;
    final primaryTextColor = isDark ? AppTheme.textPrimary : const Color(0xFF0F172A);
    final secondaryTextColor = isDark ? AppTheme.textSecondary : const Color(0xFF64748B);

    final isMarketOpen = _marketStatus?.isMarketOpen ?? false;
    final timeStr = DateFormat('HH:mm:ss').format(_currentIst);

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      decoration: BoxDecoration(
        color: bgColor,
        border: Border(bottom: BorderSide(color: borderColor, width: 1)),
      ),
      child: Wrap(
        alignment: WrapAlignment.spaceBetween,
        crossAxisAlignment: WrapCrossAlignment.center,
        spacing: 12,
        runSpacing: 8,
        children: [
          // Branding & Simulation Badge
          Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: AppTheme.accentBlue.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(4),
                  border: Border.all(color: AppTheme.accentBlue.withValues(alpha: 0.4)),
                ),
                child: const Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(Icons.terminal, size: 14, color: AppTheme.accentBlue),
                    SizedBox(width: 6),
                    Text(
                      'NSE TERMINAL',
                      style: TextStyle(
                        fontSize: 11,
                        fontWeight: FontWeight.w800,
                        letterSpacing: 0.8,
                        color: AppTheme.accentBlue,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 8),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: AppTheme.warningAmberSubtle,
                  borderRadius: BorderRadius.circular(4),
                  border: Border.all(color: AppTheme.warningAmber.withValues(alpha: 0.4)),
                ),
                child: const Text(
                  AppConstants.paperTradingBanner,
                  style: TextStyle(
                    fontSize: 10,
                    fontWeight: FontWeight.w800,
                    letterSpacing: 0.6,
                    color: AppTheme.warningAmber,
                  ),
                ),
              ),
            ],
          ),

          // Market Time, Status, Feed Health & Actions
          Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              // Clock
              Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(Icons.schedule, size: 14, color: secondaryTextColor),
                  const SizedBox(width: 5),
                  Text(
                    '$timeStr IST',
                    style: TextStyle(
                      fontFamily: 'monospace',
                      fontFeatures: const [FontFeature.tabularFigures()],
                      fontWeight: FontWeight.w700,
                      fontSize: 12,
                      color: primaryTextColor,
                    ),
                  ),
                ],
              ),
              const SizedBox(width: 12),

              // Market Open/Close Pill
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: (isMarketOpen ? AppTheme.gainGreen : AppTheme.darkBorder).withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(4),
                  border: Border.all(
                    color: (isMarketOpen ? AppTheme.gainGreen : secondaryTextColor).withValues(alpha: 0.4),
                  ),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Container(
                      width: 6,
                      height: 6,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        color: isMarketOpen ? AppTheme.gainGreen : secondaryTextColor,
                      ),
                    ),
                    const SizedBox(width: 5),
                    Text(
                      isMarketOpen ? 'NSE: OPEN' : 'NSE: CLOSED',
                      style: TextStyle(
                        fontSize: 10,
                        fontWeight: FontWeight.w700,
                        letterSpacing: 0.4,
                        color: isMarketOpen ? AppTheme.gainGreen : secondaryTextColor,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 10),

              // Backend Connectivity Pill
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: (_isConnected ? AppTheme.gainGreen : AppTheme.lossRed).withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(4),
                  border: Border.all(
                    color: (_isConnected ? AppTheme.gainGreen : AppTheme.lossRed).withValues(alpha: 0.4),
                  ),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Container(
                      width: 6,
                      height: 6,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        color: _isConnected ? AppTheme.gainGreen : AppTheme.lossRed,
                      ),
                    ),
                    const SizedBox(width: 5),
                    Text(
                      _isConnected
                          ? 'FEED ACTIVE${_dbLatency != null ? " • ${_dbLatency!.toStringAsFixed(1)}ms" : ""}'
                          : 'OFFLINE',
                      style: TextStyle(
                        fontSize: 10,
                        fontWeight: FontWeight.w700,
                        letterSpacing: 0.4,
                        color: _isConnected ? AppTheme.gainGreen : AppTheme.lossRed,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 8),

              // Manual Refresh
              IconButton(
                visualDensity: VisualDensity.compact,
                padding: EdgeInsets.zero,
                constraints: const BoxConstraints(minWidth: 28, minHeight: 28),
                icon: Icon(Icons.refresh, size: 16, color: secondaryTextColor),
                tooltip: 'Refresh Feed Data',
                onPressed: () {
                  _fetchHeaderData();
                  widget.onRefresh?.call();
                },
              ),
            ],
          ),
        ],
      ),
    );
  }
}
