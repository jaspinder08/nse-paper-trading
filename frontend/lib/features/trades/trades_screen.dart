import 'package:flutter/material.dart';
import '../../models/api_models.dart';
import '../../services/api_service.dart';

class TradesScreen extends StatefulWidget {
  const TradesScreen({super.key});

  @override
  State<TradesScreen> createState() => _TradesScreenState();
}

class _TradesScreenState extends State<TradesScreen> {
  bool _isLoading = true;
  List<TradeLogItem> _trades = [];

  @override
  void initState() {
    super.initState();
    _loadTrades();
  }

  Future<void> _loadTrades() async {
    setState(() => _isLoading = true);
    final list = await apiService.getTradeLogs();
    if (mounted) {
      setState(() {
        _trades = list;
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Trade Journal & Fills', style: TextStyle(fontWeight: FontWeight.bold)),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            tooltip: 'Refresh Journal',
            onPressed: _loadTrades,
          ),
          const SizedBox(width: 8),
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _trades.isEmpty
              ? Center(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(Icons.history_toggle_off, size: 56, color: theme.hintColor.withOpacity(0.4)),
                      const SizedBox(height: 12),
                      Text('No executed paper trades logged yet', style: TextStyle(color: theme.hintColor)),
                    ],
                  ),
                )
              : ListView.separated(
                  padding: const EdgeInsets.all(16),
                  itemCount: _trades.length,
                  separatorBuilder: (_, __) => const SizedBox(height: 8),
                  itemBuilder: (context, index) {
                    final t = _trades[index];
                    final isBuy = t.action.toUpperCase().contains('BUY');
                    final pnl = t.pnl;
                    final hasPnl = pnl != null;

                    return Card(
                      elevation: 0,
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(8),
                        side: BorderSide(color: theme.dividerColor.withOpacity(0.12)),
                      ),
                      child: ListTile(
                        leading: CircleAvatar(
                          radius: 18,
                          backgroundColor: (isBuy ? Colors.blue : Colors.purple).withOpacity(0.15),
                          child: Icon(
                            isBuy ? Icons.arrow_downward : Icons.arrow_upward,
                            color: isBuy ? Colors.blue : Colors.purple,
                            size: 18,
                          ),
                        ),
                        title: Row(
                          children: [
                            Text(t.symbol, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14)),
                            const SizedBox(width: 8),
                            Text('${t.action} ${t.quantity} @ ₹${t.price.toStringAsFixed(2)}', style: const TextStyle(fontSize: 13)),
                          ],
                        ),
                        subtitle: Text(
                          t.logTimestamp,
                          style: TextStyle(fontSize: 11, color: theme.hintColor),
                        ),
                        trailing: hasPnl
                            ? Text(
                                '${pnl >= 0 ? "+" : ""}₹${pnl.toStringAsFixed(2)}',
                                style: TextStyle(
                                  fontWeight: FontWeight.bold,
                                  fontSize: 14,
                                  color: pnl >= 0 ? Colors.green : Colors.red,
                                ),
                              )
                            : null,
                      ),
                    );
                  },
                ),
    );
  }
}
