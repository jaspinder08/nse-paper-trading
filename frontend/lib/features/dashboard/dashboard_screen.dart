import 'package:flutter/material.dart';
import '../../core/theme/app_theme.dart';
import '../../models/api_models.dart';
import '../../services/api_service.dart';
import '../../shared/components/kpi_card.dart';
import '../../shared/components/status_badge.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  bool _isLoading = true;
  bool _isBackendConnected = false;
  double? _dbLatencyMs;
  PortfolioSummary? _portfolio;
  TradingSessionSummary? _session;
  RiskStatus? _risk;
  MarketStatusInfo? _marketStatus;
  List<SignalItem> _recentSignals = [];
  List<TradeLogItem> _recentTrades = [];
  List<SystemLogItem> _systemLogs = [];
  DateTime _lastUpdated = DateTime.now();

  @override
  void initState() {
    super.initState();
    _loadDashboardData();
  }

  Future<void> _loadDashboardData() async {
    setState(() => _isLoading = true);

    final health = await apiService.getHealthDetails();
    final connected = health?['status'] == 'healthy';
    final latency = (health?['details']?['db_latency_ms'] as num?)?.toDouble();

    if (!connected) {
      if (mounted) {
        setState(() {
          _isBackendConnected = false;
          _isLoading = false;
        });
      }
      return;
    }

    final portfolio = await apiService.getPortfolioSummary();
    final session = await apiService.getTodaySession();
    final risk = await apiService.getRiskStatus();
    final market = await apiService.getMarketStatus();
    final signals = await apiService.getRecentSignals(pageSize: 5);
    final trades = await apiService.getTradeLogs(pageSize: 5);
    final logs = await apiService.getSystemLogs(pageSize: 5);

    if (mounted) {
      setState(() {
        _isBackendConnected = true;
        _dbLatencyMs = latency;
        _portfolio = portfolio;
        _session = session;
        _risk = risk;
        _marketStatus = market;
        _recentSignals = signals;
        _recentTrades = trades;
        _systemLogs = logs;
        _lastUpdated = DateTime.now();
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Intraday Dashboard'),
        actions: [
          Row(
            children: [
              Container(
                width: 7,
                height: 7,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: _isBackendConnected ? AppTheme.gainGreen : AppTheme.lossRed,
                ),
              ),
              const SizedBox(width: 6),
              Text(
                _isBackendConnected ? 'Active' : 'Offline',
                style: TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w600,
                  color: _isBackendConnected ? AppTheme.gainGreen : AppTheme.lossRed,
                ),
              ),
              const SizedBox(width: 14),
              Text(
                'Updated: ${_lastUpdated.hour.toString().padLeft(2, '0')}:${_lastUpdated.minute.toString().padLeft(2, '0')}:${_lastUpdated.second.toString().padLeft(2, '0')}',
                style: TextStyle(fontSize: 11, color: isDark ? AppTheme.textMuted : const Color(0xFF64748B)),
              ),
              const SizedBox(width: 8),
              IconButton(
                icon: const Icon(Icons.refresh, size: 18),
                tooltip: 'Refresh All',
                onPressed: _loadDashboardData,
              ),
              const SizedBox(width: 8),
            ],
          ),
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _loadDashboardData,
              child: SingleChildScrollView(
                physics: const AlwaysScrollableScrollPhysics(),
                padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 14.0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Section A: Market & Feed Overview
                    _buildMarketOverviewStrip(isDark),
                    const SizedBox(height: 14),

                    // Section B: Portfolio Summary KPIs
                    _buildSectionHeader('PORTFOLIO CAPITAL & MARGIN', isDark),
                    const SizedBox(height: 8),
                    _buildPortfolioKpis(isDark),
                    const SizedBox(height: 14),

                    // Section C: Risk & Gatekeeper Overview
                    _buildSectionHeader('RISK GATEKEEPER & QUOTAS', isDark),
                    const SizedBox(height: 8),
                    _buildRiskOverview(isDark),
                    const SizedBox(height: 14),

                    // Section D: Market Activity & Auditing
                    _buildSectionHeader('RECENT MARKET ACTIVITY & LOGS', isDark),
                    const SizedBox(height: 8),
                    _buildActivityPanels(isDark),
                  ],
                ),
              ),
            ),
    );
  }

  Widget _buildSectionHeader(String title, bool isDark) {
    return Text(
      title,
      style: TextStyle(
        fontSize: 11,
        fontWeight: FontWeight.w700,
        color: isDark ? AppTheme.textMuted : const Color(0xFF64748B),
        letterSpacing: 0.6,
      ),
    );
  }

  Widget _buildMarketOverviewStrip(bool isDark) {
    final isOpen = _marketStatus?.isMarketOpen ?? false;
    final sessionStatus = _session?.status ?? 'SCHEDULED';
    final sessionDate = _session?.sessionDate ?? 'Today';

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: BoxDecoration(
        color: isDark ? AppTheme.darkSurface : AppTheme.lightSurface,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: isDark ? AppTheme.darkBorder : AppTheme.lightBorder),
      ),
      child: Wrap(
        alignment: WrapAlignment.spaceBetween,
        crossAxisAlignment: WrapCrossAlignment.center,
        spacing: 16,
        runSpacing: 10,
        children: [
          Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                isOpen ? Icons.candlestick_chart : Icons.access_time_filled,
                size: 16,
                color: isOpen ? AppTheme.gainGreen : AppTheme.textSecondary,
              ),
              const SizedBox(width: 8),
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(
                        'NSE Regular Equities',
                        style: TextStyle(
                          fontSize: 12,
                          fontWeight: FontWeight.w700,
                          color: isDark ? AppTheme.textPrimary : const Color(0xFF0F172A),
                        ),
                      ),
                      const SizedBox(width: 8),
                      StatusBadge(status: isOpen ? 'OPEN' : 'CLOSED', fontSize: 10),
                    ],
                  ),
                  const SizedBox(height: 2),
                  Text(
                    'Regular Session: 09:15 – 15:30 IST | Nifty 50 Cash Universe',
                    style: TextStyle(fontSize: 11, color: isDark ? AppTheme.textMuted : const Color(0xFF64748B)),
                  ),
                ],
              ),
            ],
          ),
          Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              _metricPill(
                'SESSION',
                sessionDate,
                sessionStatus,
                isDark,
              ),
              const SizedBox(width: 12),
              _metricPill(
                'FEED LATENCY',
                _dbLatencyMs != null ? '${_dbLatencyMs!.toStringAsFixed(1)} ms' : 'Offline',
                _isBackendConnected ? 'HEALTHY' : 'DOWN',
                isDark,
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _metricPill(String label, String value, String status, bool isDark) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.end,
      mainAxisSize: MainAxisSize.min,
      children: [
        Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              '$label: ',
              style: TextStyle(
                fontSize: 10,
                fontWeight: FontWeight.w600,
                color: isDark ? AppTheme.textMuted : const Color(0xFF64748B),
              ),
            ),
            Text(
              value,
              style: TextStyle(
                fontSize: 11,
                fontWeight: FontWeight.w700,
                color: isDark ? AppTheme.textPrimary : const Color(0xFF0F172A),
                fontFamily: 'monospace',
                fontFeatures: const [FontFeature.tabularFigures()],
              ),
            ),
          ],
        ),
        const SizedBox(height: 2),
        StatusBadge(status: status, fontSize: 9),
      ],
    );
  }

  Widget _buildPortfolioKpis(bool isDark) {
    final netEquity = _portfolio?.netEquity ?? 5000.0;
    final availableMargin = _portfolio?.availableMargin ?? 4500.0;
    final cashReserve = _portfolio?.cashReserve ?? 500.0;
    final realizedPnl = _portfolio?.realizedPnl ?? 0.0;
    final unrealizedPnl = _portfolio?.unrealizedPnl ?? 0.0;
    final openCount = _portfolio?.openPositionsCount ?? 0;

    return LayoutBuilder(
      builder: (context, constraints) {
        final count = constraints.maxWidth > 1000
            ? 6
            : (constraints.maxWidth > 700 ? 3 : 2);

        return GridView.count(
          crossAxisCount: count,
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          mainAxisSpacing: 10,
          crossAxisSpacing: 10,
          childAspectRatio: 2.1,
          children: [
            KpiCard(
              title: 'Virtual Equity',
              value: '₹${netEquity.toStringAsFixed(2)}',
              subtitle: 'Capital Base: ₹5,000.00',
              icon: Icons.account_balance,
              valueColor: isDark ? AppTheme.textPrimary : null,
              accentColor: AppTheme.accentBlue,
            ),
            KpiCard(
              title: 'Available Cash',
              value: '₹${availableMargin.toStringAsFixed(2)}',
              subtitle: 'Deployable Margin',
              icon: Icons.account_balance_wallet_outlined,
              valueColor: isDark ? AppTheme.textPrimary : null,
              accentColor: AppTheme.accentCyan,
            ),
            KpiCard(
              title: 'Cash Reserve (10%)',
              value: '₹${cashReserve.toStringAsFixed(2)}',
              subtitle: 'Safety Capital Buffer',
              icon: Icons.shield_outlined,
              valueColor: AppTheme.warningAmber,
              accentColor: AppTheme.warningAmber,
            ),
            KpiCard(
              title: 'Realized P&L',
              value: '${realizedPnl >= 0 ? "+" : ""}₹${realizedPnl.toStringAsFixed(2)}',
              subtitle: 'Modeled Net Fees',
              icon: realizedPnl >= 0 ? Icons.trending_up : Icons.trending_down,
              valueColor: realizedPnl >= 0 ? AppTheme.gainGreen : AppTheme.lossRed,
              accentColor: realizedPnl >= 0 ? AppTheme.gainGreen : AppTheme.lossRed,
            ),
            KpiCard(
              title: 'Unrealized P&L',
              value: '${unrealizedPnl >= 0 ? "+" : ""}₹${unrealizedPnl.toStringAsFixed(2)}',
              subtitle: 'Mark-to-Market',
              icon: Icons.show_chart,
              valueColor: unrealizedPnl >= 0 ? AppTheme.gainGreen : AppTheme.lossRed,
              accentColor: unrealizedPnl >= 0 ? AppTheme.gainGreen : AppTheme.lossRed,
            ),
            KpiCard(
              title: 'Active Positions',
              value: '$openCount / 3',
              subtitle: 'Max 3 Concurrent',
              icon: Icons.layers_outlined,
              valueColor: openCount >= 3 ? AppTheme.warningAmber : null,
              accentColor: AppTheme.accentBlue,
            ),
          ],
        );
      },
    );
  }

  Widget _buildRiskOverview(bool isDark) {
    final dailyLoss = _risk?.currentDailyPnl ?? 0.0;
    final maxLoss = _risk?.maxDailyLoss ?? 75.0;
    final isTripped = _risk?.circuitBreakerActive ?? false;
    final tradesToday = _risk?.tradesToday ?? 0;
    final maxTrades = _risk?.maxTradesPerDay ?? 3;
    final eventsToday = _risk?.eventsToday ?? 0;
    final maxEvents = _risk?.maxEventsPerDay ?? 6;
    final plannedRisk = _risk?.plannedOpenRisk ?? 0.0;

    final lossLossAmt = dailyLoss < 0 ? dailyLoss.abs() : 0.0;
    final lossProgress = (lossLossAmt / maxLoss).clamp(0.0, 1.0);
    final remainingRiskCapacity = (maxLoss - lossLossAmt).clamp(0.0, maxLoss);

    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: isDark ? AppTheme.darkCard : AppTheme.lightCard,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: isTripped
              ? AppTheme.lossRed
              : (isDark ? AppTheme.darkBorder : AppTheme.lightBorder),
          width: isTripped ? 1.5 : 1,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Row(
                children: [
                  Icon(
                    isTripped ? Icons.warning_amber_rounded : Icons.lock_clock,
                    size: 16,
                    color: isTripped ? AppTheme.lossRed : AppTheme.gainGreen,
                  ),
                  const SizedBox(width: 8),
                  Text(
                    isTripped
                        ? 'DAILY CIRCUIT BREAKER TRIPPED (HARD STOP)'
                        : 'Daily Risk Capacity & Loss Circuit Breaker',
                    style: TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w700,
                      color: isTripped ? AppTheme.lossRed : (isDark ? AppTheme.textPrimary : const Color(0xFF0F172A)),
                    ),
                  ),
                ],
              ),
              StatusBadge(
                status: isTripped ? 'CIRCUIT_BREAKER_ACTIVE' : 'PASS',
                fontSize: 10,
              ),
            ],
          ),
          const SizedBox(height: 12),

          // Progress Bar
          ClipRRect(
            borderRadius: BorderRadius.circular(4),
            child: LinearProgressIndicator(
              value: lossProgress,
              minHeight: 8,
              backgroundColor: isDark ? AppTheme.darkSurface : const Color(0xFFE2E8F0),
              color: isTripped
                  ? AppTheme.lossRed
                  : (lossProgress > 0.7 ? AppTheme.warningAmber : AppTheme.gainGreen),
            ),
          ),
          const SizedBox(height: 10),

          // Detailed metrics row
          Wrap(
            alignment: WrapAlignment.spaceBetween,
            spacing: 20,
            runSpacing: 8,
            children: [
              _riskMetricItem('Daily Loss Limit', '₹${maxLoss.toStringAsFixed(0)}', isDark),
              _riskMetricItem('Current Realized Loss', '₹${lossLossAmt.toStringAsFixed(2)}', isDark, isNeg: lossLossAmt > 0),
              _riskMetricItem('Remaining Loss Buffer', '₹${remainingRiskCapacity.toStringAsFixed(2)}', isDark, isPos: remainingRiskCapacity > 0),
              _riskMetricItem('Trades Quota', '$tradesToday / $maxTrades max', isDark),
              _riskMetricItem('Order Events', '$eventsToday / $maxEvents max', isDark),
              _riskMetricItem('Open Planned Risk', '₹${plannedRisk.toStringAsFixed(2)}', isDark),
            ],
          ),
        ],
      ),
    );
  }

  Widget _riskMetricItem(String label, String value, bool isDark, {bool isNeg = false, bool isPos = false}) {
    Color valColor = isDark ? AppTheme.textPrimary : const Color(0xFF0F172A);
    if (isNeg) valColor = AppTheme.lossRed;
    if (isPos) valColor = AppTheme.gainGreen;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label.toUpperCase(),
          style: TextStyle(
            fontSize: 9,
            fontWeight: FontWeight.w600,
            color: isDark ? AppTheme.textMuted : const Color(0xFF64748B),
          ),
        ),
        const SizedBox(height: 2),
        Text(
          value,
          style: TextStyle(
            fontSize: 12,
            fontWeight: FontWeight.w700,
            fontFamily: 'monospace',
            fontFeatures: const [FontFeature.tabularFigures()],
            color: valColor,
          ),
        ),
      ],
    );
  }

  Widget _buildActivityPanels(bool isDark) {
    return LayoutBuilder(
      builder: (context, constraints) {
        if (constraints.maxWidth > 1100) {
          return Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(child: _buildSignalsCard(isDark)),
              const SizedBox(width: 14),
              Expanded(child: _buildTradesCard(isDark)),
              const SizedBox(width: 14),
              Expanded(child: _buildSystemEventsCard(isDark)),
            ],
          );
        } else {
          return Column(
            children: [
              _buildSignalsCard(isDark),
              const SizedBox(height: 14),
              _buildTradesCard(isDark),
              const SizedBox(height: 14),
              _buildSystemEventsCard(isDark),
            ],
          );
        }
      },
    );
  }

  Widget _buildSystemEventsCard(bool isDark) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: isDark ? AppTheme.darkCard : AppTheme.lightCard,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: isDark ? AppTheme.darkBorder : AppTheme.lightBorder),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                'SYSTEM EVENTS & AUDIT',
                style: TextStyle(
                  fontSize: 11,
                  fontWeight: FontWeight.w700,
                  color: isDark ? AppTheme.textSecondary : const Color(0xFF64748B),
                  letterSpacing: 0.5,
                ),
              ),
              Text(
                '${_systemLogs.length} events',
                style: TextStyle(fontSize: 11, color: isDark ? AppTheme.textMuted : const Color(0xFF64748B)),
              ),
            ],
          ),
          const SizedBox(height: 10),
          if (_systemLogs.isEmpty)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 20),
              child: Center(
                child: Text(
                  'No operational warnings or audit events.',
                  style: TextStyle(fontSize: 11, color: isDark ? AppTheme.textMuted : const Color(0xFF64748B)),
                ),
              ),
            )
          else
            ListView.separated(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              itemCount: _systemLogs.length > 4 ? 4 : _systemLogs.length,
              separatorBuilder: (_, __) => Divider(
                height: 12,
                color: isDark ? AppTheme.darkBorder : AppTheme.lightBorder,
              ),
              itemBuilder: (context, index) {
                final log = _systemLogs[index];
                final isWarn = log.level == 'WARNING' || log.level == 'ERROR';
                return Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            log.message,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: TextStyle(
                              fontSize: 11,
                              fontWeight: FontWeight.w600,
                              color: isDark ? AppTheme.textPrimary : const Color(0xFF0F172A),
                            ),
                          ),
                          Text(
                            'Module: ${log.module} • ${log.loggedAt}',
                            style: TextStyle(
                              fontSize: 9,
                              color: isDark ? AppTheme.textMuted : const Color(0xFF64748B),
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(width: 8),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                      decoration: BoxDecoration(
                        color: (isWarn ? AppTheme.warningAmber : AppTheme.accentBlue).withValues(alpha: 0.15),
                        borderRadius: BorderRadius.circular(4),
                      ),
                      child: Text(
                        log.level,
                        style: TextStyle(
                          fontSize: 9,
                          fontWeight: FontWeight.w700,
                          color: isWarn ? AppTheme.warningAmber : AppTheme.accentBlue,
                        ),
                      ),
                    ),
                  ],
                );
              },
            ),
        ],
      ),
    );
  }

  Widget _buildSignalsCard(bool isDark) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: isDark ? AppTheme.darkCard : AppTheme.lightCard,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: isDark ? AppTheme.darkBorder : AppTheme.lightBorder),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                'LATEST ORB SIGNALS',
                style: TextStyle(
                  fontSize: 11,
                  fontWeight: FontWeight.w700,
                  color: isDark ? AppTheme.textSecondary : const Color(0xFF64748B),
                  letterSpacing: 0.5,
                ),
              ),
              Text(
                '${_recentSignals.length} recorded',
                style: TextStyle(fontSize: 11, color: isDark ? AppTheme.textMuted : const Color(0xFF64748B)),
              ),
            ],
          ),
          const SizedBox(height: 10),
          if (_recentSignals.isEmpty)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 20),
              child: Center(
                child: Text(
                  'No strategy signals generated yet today.',
                  style: TextStyle(fontSize: 11, color: isDark ? AppTheme.textMuted : const Color(0xFF64748B)),
                ),
              ),
            )
          else
            ListView.separated(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              itemCount: _recentSignals.length,
              separatorBuilder: (_, __) => Divider(
                height: 12,
                color: isDark ? AppTheme.darkBorder : AppTheme.lightBorder,
              ),
              itemBuilder: (context, index) {
                final sig = _recentSignals[index];
                return Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          sig.symbol,
                          style: TextStyle(
                            fontSize: 12,
                            fontWeight: FontWeight.w700,
                            color: isDark ? AppTheme.textPrimary : const Color(0xFF0F172A),
                          ),
                        ),
                        Text(
                          'Trigger: ₹${sig.triggerPrice.toStringAsFixed(2)} | SL: ₹${sig.stopLoss.toStringAsFixed(2)}',
                          style: TextStyle(
                            fontSize: 10,
                            fontFamily: 'monospace',
                            fontFeatures: const [FontFeature.tabularFigures()],
                            color: isDark ? AppTheme.textMuted : const Color(0xFF64748B),
                          ),
                        ),
                      ],
                    ),
                    StatusBadge(status: sig.status, fontSize: 10),
                  ],
                );
              },
            ),
        ],
      ),
    );
  }

  Widget _buildTradesCard(bool isDark) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: isDark ? AppTheme.darkCard : AppTheme.lightCard,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: isDark ? AppTheme.darkBorder : AppTheme.lightBorder),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                'LATEST PAPER FILLS',
                style: TextStyle(
                  fontSize: 11,
                  fontWeight: FontWeight.w700,
                  color: isDark ? AppTheme.textSecondary : const Color(0xFF64748B),
                  letterSpacing: 0.5,
                ),
              ),
              Text(
                '${_recentTrades.length} recorded',
                style: TextStyle(fontSize: 11, color: isDark ? AppTheme.textMuted : const Color(0xFF64748B)),
              ),
            ],
          ),
          const SizedBox(height: 10),
          if (_recentTrades.isEmpty)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 20),
              child: Center(
                child: Text(
                  'No simulated paper trades recorded yet.',
                  style: TextStyle(fontSize: 11, color: isDark ? AppTheme.textMuted : const Color(0xFF64748B)),
                ),
              ),
            )
          else
            ListView.separated(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              itemCount: _recentTrades.length,
              separatorBuilder: (_, __) => Divider(
                height: 12,
                color: isDark ? AppTheme.darkBorder : AppTheme.lightBorder,
              ),
              itemBuilder: (context, index) {
                final t = _recentTrades[index];
                final pnl = t.pnl;
                return Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          '${t.symbol} • ${t.action} ${t.quantity}',
                          style: TextStyle(
                            fontSize: 12,
                            fontWeight: FontWeight.w700,
                            color: isDark ? AppTheme.textPrimary : const Color(0xFF0F172A),
                          ),
                        ),
                        Text(
                          'Exec: ₹${t.price.toStringAsFixed(2)}',
                          style: TextStyle(
                            fontSize: 10,
                            fontFamily: 'monospace',
                            fontFeatures: const [FontFeature.tabularFigures()],
                            color: isDark ? AppTheme.textMuted : const Color(0xFF64748B),
                          ),
                        ),
                      ],
                    ),
                    if (pnl != null)
                      Text(
                        '${pnl >= 0 ? "+" : ""}₹${pnl.toStringAsFixed(2)}',
                        style: TextStyle(
                          fontSize: 12,
                          fontWeight: FontWeight.w700,
                          fontFamily: 'monospace',
                          fontFeatures: const [FontFeature.tabularFigures()],
                          color: pnl >= 0 ? AppTheme.gainGreen : AppTheme.lossRed,
                        ),
                      )
                    else
                      StatusBadge(status: 'FILLED', fontSize: 10),
                  ],
                );
              },
            ),
        ],
      ),
    );
  }
}
