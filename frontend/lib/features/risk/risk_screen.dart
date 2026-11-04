import 'package:flutter/material.dart';
import '../../models/api_models.dart';
import '../../services/api_service.dart';

class RiskScreen extends StatefulWidget {
  const RiskScreen({super.key});

  @override
  State<RiskScreen> createState() => _RiskScreenState();
}

class _RiskScreenState extends State<RiskScreen> {
  bool _isLoading = true;
  RiskStatus? _risk;
  PortfolioSummary? _portfolio;

  @override
  void initState() {
    super.initState();
    _loadRiskData();
  }

  Future<void> _loadRiskData() async {
    setState(() => _isLoading = true);
    final risk = await apiService.getRiskStatus();
    final portfolio = await apiService.getPortfolioSummary();
    if (mounted) {
      setState(() {
        _risk = risk;
        _portfolio = portfolio;
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Risk Management & Gatekeepers', style: TextStyle(fontWeight: FontWeight.bold)),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            tooltip: 'Refresh Risk Status',
            onPressed: _loadRiskData,
          ),
          const SizedBox(width: 8),
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : SingleChildScrollView(
              padding: const EdgeInsets.all(20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _buildCircuitBreakerHero(theme),
                  const SizedBox(height: 20),
                  Text('Daily Quotas & Exposure Limits', style: theme.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold)),
                  const SizedBox(height: 12),
                  _buildQuotaGrid(theme),
                  const SizedBox(height: 24),
                  Text('Active Gatekeeper Invariants (PDF Sec. 9)', style: theme.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold)),
                  const SizedBox(height: 12),
                  _buildGatekeeperChecksList(theme),
                ],
              ),
            ),
    );
  }

  Widget _buildCircuitBreakerHero(ThemeData theme) {
    final isTripped = _risk?.circuitBreakerActive ?? false;
    final dailyLoss = _risk?.currentDailyPnl ?? 0.0;
    final maxLoss = _risk?.maxDailyLoss ?? 75.0;
    final progress = (dailyLoss.abs() / maxLoss).clamp(0.0, 1.0);

    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: isTripped ? Colors.red.withOpacity(0.12) : theme.cardColor,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color: isTripped ? Colors.red : theme.dividerColor.withOpacity(0.15),
          width: isTripped ? 2 : 1,
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
                    isTripped ? Icons.cancel : Icons.verified_user_outlined,
                    color: isTripped ? Colors.red : Colors.green,
                    size: 28,
                  ),
                  const SizedBox(width: 10),
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        isTripped ? 'CIRCUIT BREAKER TRIPPED' : 'Daily Circuit Breaker Active & Normal',
                        style: TextStyle(
                          fontSize: 16,
                          fontWeight: FontWeight.bold,
                          color: isTripped ? Colors.red : Colors.green,
                        ),
                      ),
                      Text(
                        'Hard Stop: Intraday Loss Cap ₹${maxLoss.toStringAsFixed(0)}',
                        style: TextStyle(fontSize: 12, color: theme.hintColor),
                      ),
                    ],
                  ),
                ],
              ),
              Text(
                '${(progress * 100).toStringAsFixed(1)}% Used',
                style: TextStyle(
                  fontWeight: FontWeight.bold,
                  fontSize: 14,
                  color: isTripped ? Colors.red : (progress > 0.7 ? Colors.orange : Colors.green),
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          ClipRRect(
            borderRadius: BorderRadius.circular(6),
            child: LinearProgressIndicator(
              value: progress,
              minHeight: 10,
              backgroundColor: theme.dividerColor.withOpacity(0.15),
              color: isTripped ? Colors.red : (progress > 0.7 ? Colors.orange : Colors.green),
            ),
          ),
          const SizedBox(height: 10),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text('Current Realized Daily Loss: ₹${dailyLoss.abs().toStringAsFixed(2)}', style: TextStyle(fontSize: 12, color: theme.hintColor)),
              Text('Remaining Buffer: ₹${(maxLoss - dailyLoss.abs()).clamp(0.0, maxLoss).toStringAsFixed(2)}', style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600)),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildQuotaGrid(ThemeData theme) {
    final tradesToday = _risk?.tradesToday ?? 0;
    final maxTrades = _risk?.maxTradesPerDay ?? 3;
    final eventsToday = _risk?.eventsToday ?? 0;
    final openPos = _portfolio?.openPositionsCount ?? 0;
    final cashReserve = _portfolio?.cashReserve ?? 500.0;

    return LayoutBuilder(
      builder: (context, constraints) {
        final count = constraints.maxWidth > 800 ? 4 : 2;
        return GridView.count(
          crossAxisCount: count,
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          mainAxisSpacing: 12,
          crossAxisSpacing: 12,
          childAspectRatio: 2.0,
          children: [
            _quotaCard(theme, 'Daily Trades', '$tradesToday / $maxTrades', tradesToday < maxTrades ? Colors.green : Colors.red, Icons.swap_horiz),
            _quotaCard(theme, 'Simulated Events', '$eventsToday / 6', eventsToday < 6 ? Colors.green : Colors.red, Icons.history),
            _quotaCard(theme, 'Open Positions', '$openPos / 3', openPos < 3 ? Colors.green : Colors.red, Icons.layers),
            _quotaCard(theme, '10% Cash Reserve', '₹${cashReserve.toStringAsFixed(0)}', Colors.indigo, Icons.lock_outline),
          ],
        );
      },
    );
  }

  Widget _quotaCard(ThemeData theme, String title, String val, Color color, IconData icon) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: theme.cardColor,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: theme.dividerColor.withOpacity(0.12)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(title, style: TextStyle(fontSize: 12, color: theme.hintColor)),
              Icon(icon, size: 16, color: color),
            ],
          ),
          Text(val, style: TextStyle(fontSize: 17, fontWeight: FontWeight.bold, color: color)),
        ],
      ),
    );
  }

  Widget _buildGatekeeperChecksList(ThemeData theme) {
    final checks = [
      {'name': 'Circuit Breaker Gatekeeper', 'desc': 'Rejects entries if realized loss >= ₹75 (exits remain active)', 'icon': Icons.flash_on},
      {'name': 'Trade Count Gatekeeper', 'desc': 'Blocks entries if daily trade count exceeds 3 per session', 'icon': Icons.repeat},
      {'name': 'Order Event Gatekeeper', 'desc': 'Blocks executions if total entry/exit events exceed 6 per session', 'icon': Icons.list_alt},
      {'name': 'Concurrent Position Limit', 'desc': 'Caps portfolio at maximum 3 open positions simultaneously', 'icon': Icons.stacked_bar_chart},
      {'name': 'Duplicate Position Check', 'desc': 'Prevents averaging down; only 1 open position per symbol permitted', 'icon': Icons.content_copy},
      {'name': 'Long-Only Invariant', 'desc': 'Short selling, options, leverage, and margin are permanently rejected', 'icon': Icons.arrow_upward},
      {'name': 'Reward-to-Risk Gatekeeper', 'desc': 'Requires minimum 1.5:1 target to initial stop-loss risk ratio', 'icon': Icons.balance},
      {'name': 'Cash Reserve Preservation', 'desc': 'Guarantees 10% cash remains unallocated as capital buffer', 'icon': Icons.shield},
      {'name': 'Position Sizing Formula', 'desc': 'floor(₹25 max risk / (entry - stop)) capped at 25% max equity', 'icon': Icons.calculate_outlined},
    ];

    return ListView.separated(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      itemCount: checks.length,
      separatorBuilder: (_, __) => const SizedBox(height: 8),
      itemBuilder: (context, index) {
        final c = checks[index];
        return Card(
          elevation: 0,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(8),
            side: BorderSide(color: theme.dividerColor.withOpacity(0.1)),
          ),
          child: ListTile(
            leading: Icon(c['icon'] as IconData, color: Colors.blueAccent),
            title: Text(c['name'] as String, style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13)),
            subtitle: Text(c['desc'] as String, style: TextStyle(fontSize: 11, color: theme.hintColor)),
            trailing: const Icon(Icons.check_circle, color: Colors.green, size: 18),
          ),
        );
      },
    );
  }
}
