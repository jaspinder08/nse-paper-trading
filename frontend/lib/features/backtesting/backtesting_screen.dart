import 'package:flutter/material.dart';
import '../../models/api_models.dart';
import '../../services/api_service.dart';

class BacktestingScreen extends StatefulWidget {
  const BacktestingScreen({super.key});

  @override
  State<BacktestingScreen> createState() => _BacktestingScreenState();
}

class _BacktestingScreenState extends State<BacktestingScreen> {
  bool _isLoading = false;
  bool _isRunning = false;
  List<BacktestRunSummary> _pastRuns = [];
  BacktestRunDetail? _selectedDetail;

  final TextEditingController _symbolsController =
      TextEditingController(text: 'RELIANCE, TCS, INFY');
  final TextEditingController _startDateController =
      TextEditingController(text: '2026-11-01');
  final TextEditingController _endDateController =
      TextEditingController(text: '2026-11-03');
  final TextEditingController _capitalController =
      TextEditingController(text: '5000');

  @override
  void initState() {
    super.initState();
    _loadPastRuns();
  }

  Future<void> _loadPastRuns() async {
    setState(() => _isLoading = true);
    final runs = await apiService.getBacktestRuns();
    if (mounted) {
      setState(() {
        _pastRuns = runs;
        _isLoading = false;
      });
      if (runs.isNotEmpty && _selectedDetail == null) {
        _loadRunDetail(runs.first.id);
      }
    }
  }

  Future<void> _loadRunDetail(int runId) async {
    final detail = await apiService.getBacktestRunDetail(runId);
    if (mounted) {
      setState(() {
        _selectedDetail = detail;
      });
    }
  }

  Future<void> _executeBacktest() async {
    setState(() => _isRunning = true);
    final symbols = _symbolsController.text
        .split(',')
        .map((s) => s.trim().toUpperCase())
        .where((s) => s.isNotEmpty)
        .toList();
    final capital = double.tryParse(_capitalController.text) ?? 5000.0;

    final run = await apiService.runBacktest(
      strategyName: 'ORB_STRATEGY',
      symbols: symbols,
      startDate: _startDateController.text.trim(),
      endDate: _endDateController.text.trim(),
      initialCapital: capital,
    );

    if (mounted) {
      setState(() => _isRunning = false);
      if (run != null) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Backtest #${run.id} completed successfully!')),
        );
        await _loadPastRuns();
        await _loadRunDetail(run.id);
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Failed to execute backtest.')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Historical Backtesting Engine (FR-10)', style: TextStyle(fontWeight: FontWeight.bold)),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            tooltip: 'Refresh Runs',
            onPressed: _loadPastRuns,
          ),
          const SizedBox(width: 8),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _buildConfigForm(theme),
            const SizedBox(height: 24),
            if (_selectedDetail != null) ...[
              Text('Backtest Run #${_selectedDetail!.id} Performance Results', style: theme.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold)),
              const SizedBox(height: 12),
              _buildMetricsSummary(theme, _selectedDetail!),
              const SizedBox(height: 24),
              Text('Simulated Trade Fills (${_selectedDetail!.trades.length})', style: theme.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold)),
              const SizedBox(height: 12),
              _buildTradesTable(theme, _selectedDetail!.trades),
            ] else if (_isLoading) ...[
              const Center(child: CircularProgressIndicator())
            ],
            const SizedBox(height: 24),
            Text('Previous Simulation Runs', style: theme.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold)),
            const SizedBox(height: 12),
            _buildPastRunsList(theme),
          ],
        ),
      ),
    );
  }

  Widget _buildConfigForm(ThemeData theme) {
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: theme.cardColor,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: theme.dividerColor.withOpacity(0.15)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.tune, color: theme.colorScheme.primary),
              const SizedBox(width: 8),
              const Text('Simulation Parameters', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
            ],
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              Expanded(
                flex: 2,
                child: TextField(
                  controller: _symbolsController,
                  decoration: const InputDecoration(
                    labelText: 'Nifty 50 Symbols (comma-separated)',
                    border: OutlineInputBorder(),
                    isDense: true,
                  ),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: TextField(
                  controller: _capitalController,
                  keyboardType: TextInputType.number,
                  decoration: const InputDecoration(
                    labelText: 'Capital (₹)',
                    border: OutlineInputBorder(),
                    isDense: true,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(
                child: TextField(
                  controller: _startDateController,
                  decoration: const InputDecoration(
                    labelText: 'Start Date (YYYY-MM-DD)',
                    border: OutlineInputBorder(),
                    isDense: true,
                  ),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: TextField(
                  controller: _endDateController,
                  decoration: const InputDecoration(
                    labelText: 'End Date (YYYY-MM-DD)',
                    border: OutlineInputBorder(),
                    isDense: true,
                  ),
                ),
              ),
              const SizedBox(width: 12),
              ElevatedButton.icon(
                style: ElevatedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
                  backgroundColor: theme.colorScheme.primary,
                  foregroundColor: Colors.white,
                ),
                onPressed: _isRunning ? null : _executeBacktest,
                icon: _isRunning
                    ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                    : const Icon(Icons.play_arrow),
                label: Text(_isRunning ? 'Simulating...' : 'Run Simulation'),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildMetricsSummary(ThemeData theme, BacktestRunDetail d) {
    final isProfitable = d.netPnl >= 0;

    return LayoutBuilder(
      builder: (context, constraints) {
        final count = constraints.maxWidth > 900 ? 4 : 2;
        return GridView.count(
          crossAxisCount: count,
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          mainAxisSpacing: 10,
          crossAxisSpacing: 10,
          childAspectRatio: 2.2,
          children: [
            _metricCard(theme, 'Net P&L', '${isProfitable ? "+" : ""}₹${d.netPnl.toStringAsFixed(2)} (${d.returnPct.toStringAsFixed(2)}%)', isProfitable ? Colors.green : Colors.red),
            _metricCard(theme, 'Win Rate', '${d.winRate.toStringAsFixed(1)}% (${d.totalTrades} Trades)', Colors.blueAccent),
            _metricCard(theme, 'Profit Factor', d.profitFactor != null ? d.profitFactor!.toStringAsFixed(2) : '--', Colors.teal),
            _metricCard(theme, 'Max Drawdown', '${d.maxDrawdownPct?.toStringAsFixed(2) ?? "0.00"}% (₹${d.maxDrawdownAmount.toStringAsFixed(2)})', Colors.orange),
            _metricCard(theme, 'Trade Expectancy', '₹${d.expectancy.toStringAsFixed(2)} / trade', Colors.purple),
            _metricCard(theme, 'Payoff Ratio', '${d.payoffRatio.toStringAsFixed(2)}:1', Colors.indigo),
            _metricCard(theme, 'Statutory Charges', '₹${d.totalCharges.toStringAsFixed(2)}', Colors.blueGrey),
            _metricCard(theme, 'Modeled Slippage', '₹${d.totalSlippage.toStringAsFixed(2)}', Colors.blueGrey),
          ],
        );
      },
    );
  }

  Widget _metricCard(ThemeData theme, String title, String val, Color color) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: theme.cardColor,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: theme.dividerColor.withOpacity(0.12)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Text(title, style: TextStyle(fontSize: 11, color: theme.hintColor)),
          const SizedBox(height: 4),
          Text(val, style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold, color: color)),
        ],
      ),
    );
  }

  Widget _buildTradesTable(ThemeData theme, List<BacktestTradeItem> trades) {
    if (trades.isEmpty) {
      return Container(
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          color: theme.cardColor,
          borderRadius: BorderRadius.circular(8),
        ),
        child: Center(
          child: Text('Zero trades triggered during this simulation interval.', style: TextStyle(color: theme.hintColor)),
        ),
      );
    }

    return ListView.separated(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      itemCount: trades.length,
      separatorBuilder: (_, __) => const SizedBox(height: 6),
      itemBuilder: (context, index) {
        final t = trades[index];
        final isProfit = t.netPnl >= 0;

        return Card(
          elevation: 0,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(6),
            side: BorderSide(color: theme.dividerColor.withOpacity(0.1)),
          ),
          child: ListTile(
            dense: true,
            title: Row(
              children: [
                Text(t.symbol, style: const TextStyle(fontWeight: FontWeight.bold)),
                const SizedBox(width: 8),
                Text('Qty: ${t.quantity} • Entry: ₹${t.entryPrice.toStringAsFixed(2)} • Exit: ₹${t.exitPrice.toStringAsFixed(2)}', style: const TextStyle(fontSize: 12)),
              ],
            ),
            subtitle: Text('Reason: ${t.exitReason ?? "EXIT"} | Fees: ₹${t.totalCharges.toStringAsFixed(2)} | Slip: ₹${t.slippageCost.toStringAsFixed(2)}', style: TextStyle(fontSize: 11, color: theme.hintColor)),
            trailing: Text(
              '${isProfit ? "+" : ""}₹${t.netPnl.toStringAsFixed(2)} (${t.returnPct.toStringAsFixed(2)}%)',
              style: TextStyle(fontWeight: FontWeight.bold, color: isProfit ? Colors.green : Colors.red),
            ),
          ),
        );
      },
    );
  }

  Widget _buildPastRunsList(ThemeData theme) {
    if (_pastRuns.isEmpty) {
      return Text('No previous backtest runs recorded.', style: TextStyle(color: theme.hintColor));
    }

    return ListView.separated(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      itemCount: _pastRuns.length,
      separatorBuilder: (_, __) => const SizedBox(height: 6),
      itemBuilder: (context, index) {
        final r = _pastRuns[index];
        final isSelected = _selectedDetail?.id == r.id;

        return Card(
          elevation: 0,
          color: isSelected ? theme.colorScheme.primary.withOpacity(0.08) : theme.cardColor,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(8),
            side: BorderSide(color: isSelected ? theme.colorScheme.primary : theme.dividerColor.withOpacity(0.1)),
          ),
          child: ListTile(
            dense: true,
            onTap: () => _loadRunDetail(r.id),
            title: Text('Run #${r.id} • ${r.strategyName} (${r.startDate} to ${r.endDate})', style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13)),
            subtitle: Text('Trades: ${r.totalTrades} | Win Rate: ${r.winRate.toStringAsFixed(1)}% | Capital: ₹${r.initialCapital.toStringAsFixed(0)} ➔ ₹${r.finalCapital.toStringAsFixed(2)}', style: TextStyle(fontSize: 11, color: theme.hintColor)),
            trailing: const Icon(Icons.chevron_right, size: 18),
          ),
        );
      },
    );
  }
}
