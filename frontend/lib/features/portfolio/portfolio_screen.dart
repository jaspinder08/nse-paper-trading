import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../../core/theme/app_theme.dart';
import '../../models/api_models.dart';
import '../../services/api_service.dart';
import '../../shared/components/kpi_card.dart';
import '../../shared/components/status_badge.dart';
import '../../shared/components/empty_state_view.dart';

class PortfolioScreen extends StatefulWidget {
  const PortfolioScreen({super.key});

  @override
  State<PortfolioScreen> createState() => _PortfolioScreenState();
}

class _PortfolioScreenState extends State<PortfolioScreen>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;
  bool _isLoading = true;

  PortfolioSummary? _summary;
  List<PositionItem> _positions = [];
  List<PaperOrderItem> _orders = [];
  List<TradeLogItem> _trades = [];
  DateTime? _lastUpdated;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 4, vsync: this);
    _loadData();
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  Future<void> _loadData() async {
    setState(() => _isLoading = true);
    try {
      final results = await Future.wait([
        apiService.getPortfolioSummary(),
        apiService.getPositions(),
        apiService.getOrders(),
        apiService.getTradeLogs(pageSize: 50),
      ]);

      if (mounted) {
        setState(() {
          _summary = results[0] as PortfolioSummary?;
          _positions = results[1] as List<PositionItem>;
          _orders = results[2] as List<PaperOrderItem>;
          _trades = results[3] as List<TradeLogItem>;
          _lastUpdated = DateTime.now();
          _isLoading = false;
        });
      }
    } catch (_) {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.bgCanvas,
      body: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _buildControlHeader(),
          _buildSummaryRibbon(),
          _buildTabBar(),
          Expanded(
            child: _isLoading
                ? const Center(
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                      color: AppTheme.accentCyan,
                    ),
                  )
                : TabBarView(
                    controller: _tabController,
                    children: [
                      _buildPositionsTab(),
                      _buildOrdersTab(),
                      _buildTradeHistoryTab(),
                      _buildChargesAndSlippageTab(),
                    ],
                  ),
          ),
        ],
      ),
    );
  }

  Widget _buildControlHeader() {
    final timeStr = _lastUpdated != null
        ? DateFormat('HH:mm:ss').format(_lastUpdated!)
        : '--:--:--';

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
      decoration: const BoxDecoration(
        color: AppTheme.bgSurface,
        border: Border(bottom: BorderSide(color: AppTheme.borderSubtle)),
      ),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Row(
                  children: [
                    const Text(
                      'SIMULATED PORTFOLIO & AUDIT LEDGER',
                      style: TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.w800,
                        letterSpacing: 0.6,
                        color: AppTheme.textPrimary,
                      ),
                    ),
                    const SizedBox(width: 10),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
                      decoration: BoxDecoration(
                        color: AppTheme.accentAmber.withOpacity(0.12),
                        borderRadius: BorderRadius.circular(4),
                        border: Border.all(color: AppTheme.accentAmber.withOpacity(0.3)),
                      ),
                      child: const Text(
                        '100% PAPER · NO CAPITAL AT RISK',
                        style: TextStyle(
                          fontSize: 10,
                          fontWeight: FontWeight.w700,
                          color: AppTheme.accentAmber,
                          letterSpacing: 0.5,
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 3),
                Text(
                  'Intraday positions, order audit trail, and statutory fee calculations with 10% cash reserve enforcement.',
                  style: TextStyle(
                    fontSize: 11,
                    color: AppTheme.textMuted.withOpacity(0.85),
                  ),
                ),
              ],
            ),
          ),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
            decoration: BoxDecoration(
              color: AppTheme.bgCard,
              borderRadius: BorderRadius.circular(6),
              border: Border.all(color: AppTheme.borderSubtle),
            ),
            child: Row(
              children: [
                const Icon(Icons.access_time, size: 13, color: AppTheme.textMuted),
                const SizedBox(width: 5),
                Text(
                  'Updated: $timeStr',
                  style: AppTheme.monoStyle(
                    fontSize: 11,
                    color: AppTheme.textSecondary,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: 10),
          ElevatedButton.icon(
            onPressed: _isLoading ? null : _loadData,
            icon: const Icon(Icons.refresh, size: 14),
            label: const Text(
              'REFRESH',
              style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700, letterSpacing: 0.5),
            ),
            style: ElevatedButton.styleFrom(
              backgroundColor: AppTheme.accentBlue,
              foregroundColor: Colors.white,
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSummaryRibbon() {
    final s = _summary;
    final totalEquity = s?.netEquity ?? 5000.0;
    final availCash = s?.availableMargin ?? 4500.0;
    final reserve = s?.cashReserve ?? 500.0;
    final realized = s?.realizedPnl ?? 0.0;
    final unrealized = s?.unrealizedPnl ?? 0.0;
    final totalPnl = realized + unrealized;

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
      decoration: const BoxDecoration(
        color: AppTheme.bgCanvas,
        border: Border(bottom: BorderSide(color: AppTheme.borderSubtle)),
      ),
      child: LayoutBuilder(
        builder: (context, constraints) {
          final isCompact = constraints.maxWidth < 900;
          return Wrap(
            spacing: 12,
            runSpacing: 10,
            children: [
              SizedBox(
                width: isCompact ? 160 : 210,
                child: KpiCard(
                  title: 'VIRTUAL EQUITY',
                  value: '₹${totalEquity.toStringAsFixed(2)}',
                  subtitle: 'Initial: ₹5,000.00',
                  icon: Icons.account_balance_wallet_outlined,
                  accentColor: AppTheme.accentCyan,
                ),
              ),
              SizedBox(
                width: isCompact ? 160 : 210,
                child: KpiCard(
                  title: 'AVAILABLE CASH',
                  value: '₹${availCash.toStringAsFixed(2)}',
                  subtitle: 'Unallocated intraday margin',
                  icon: Icons.savings_outlined,
                  accentColor: AppTheme.accentBlue,
                ),
              ),
              SizedBox(
                width: isCompact ? 160 : 210,
                child: KpiCard(
                  title: '10% CASH RESERVE',
                  value: '₹${reserve.toStringAsFixed(2)}',
                  subtitle: 'Locked safety reserve',
                  icon: Icons.lock_outline,
                  accentColor: AppTheme.accentAmber,
                ),
              ),
              SizedBox(
                width: isCompact ? 160 : 210,
                child: KpiCard(
                  title: 'REALIZED P&L',
                  value: '${realized >= 0 ? "+" : ""}₹${realized.toStringAsFixed(2)}',
                  subtitle: 'Closed intraday trades',
                  icon: realized >= 0 ? Icons.trending_up : Icons.trending_down,
                  valueColor: realized >= 0 ? AppTheme.colorProfit : AppTheme.colorLoss,
                  accentColor: realized >= 0 ? AppTheme.colorProfit : AppTheme.colorLoss,
                ),
              ),
              SizedBox(
                width: isCompact ? 160 : 210,
                child: KpiCard(
                  title: 'UNREALIZED P&L',
                  value: '${unrealized >= 0 ? "+" : ""}₹${unrealized.toStringAsFixed(2)}',
                  subtitle: '${_positions.length} active positions',
                  icon: Icons.show_chart,
                  valueColor: unrealized >= 0 ? AppTheme.colorProfit : AppTheme.colorLoss,
                  accentColor: unrealized >= 0 ? AppTheme.colorProfit : AppTheme.colorLoss,
                ),
              ),
              SizedBox(
                width: isCompact ? 160 : 210,
                child: KpiCard(
                  title: 'NET TOTAL P&L',
                  value: '${totalPnl >= 0 ? "+" : ""}₹${totalPnl.toStringAsFixed(2)}',
                  subtitle: '${(totalPnl / 5000.0 * 100).toStringAsFixed(2)}% total return',
                  icon: Icons.pie_chart_outline,
                  valueColor: totalPnl >= 0 ? AppTheme.colorProfit : AppTheme.colorLoss,
                  accentColor: totalPnl >= 0 ? AppTheme.colorProfit : AppTheme.colorLoss,
                ),
              ),
            ],
          );
        },
      ),
    );
  }

  Widget _buildTabBar() {
    return Container(
      decoration: const BoxDecoration(
        color: AppTheme.bgSurface,
        border: Border(bottom: BorderSide(color: AppTheme.borderSubtle)),
      ),
      child: TabBar(
        controller: _tabController,
        isScrollable: true,
        tabAlignment: TabAlignment.start,
        indicatorColor: AppTheme.accentCyan,
        indicatorWeight: 2.5,
        labelColor: AppTheme.accentCyan,
        unselectedLabelColor: AppTheme.textSecondary,
        labelStyle: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700, letterSpacing: 0.4),
        unselectedLabelStyle: const TextStyle(fontSize: 12, fontWeight: FontWeight.w500),
        tabs: [
          Tab(
            child: Row(
              children: [
                const Text('ACTIVE POSITIONS'),
                const SizedBox(width: 6),
                _tabCountBadge(_positions.length),
              ],
            ),
          ),
          Tab(
            child: Row(
              children: [
                const Text('PAPER ORDERS'),
                const SizedBox(width: 6),
                _tabCountBadge(_orders.length),
              ],
            ),
          ),
          Tab(
            child: Row(
              children: [
                const Text('TRADE HISTORY JOURNAL'),
                const SizedBox(width: 6),
                _tabCountBadge(_trades.length),
              ],
            ),
          ),
          const Tab(
            text: 'FEES, SLIPPAGE & STATUTORY CHARGES',
          ),
        ],
      ),
    );
  }

  Widget _tabCountBadge(int count) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
      decoration: BoxDecoration(
        color: AppTheme.bgCard,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: AppTheme.borderSubtle),
      ),
      child: Text(
        '$count',
        style: AppTheme.monoStyle(
          fontSize: 10,
          fontWeight: FontWeight.w700,
          color: AppTheme.textMuted,
        ),
      ),
    );
  }

  Widget _buildPositionsTab() {
    if (_positions.isEmpty) {
      return const Center(
        child: EmptyStateView(
          title: 'No Open Paper Positions',
          description:
              'Simulated positions enter automatically when an Opening Range Breakout occurs with >=1.0x volume confirmation and all risk gatekeepers pass.',
          icon: Icons.inventory_2_outlined,
        ),
      );
    }

    return SingleChildScrollView(
      scrollDirection: Axis.vertical,
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: ConstrainedBox(
          constraints: BoxConstraints(
            minWidth: MediaQuery.of(context).size.width,
          ),
          child: DataTable(
            columnSpacing: 22,
            horizontalMargin: 20,
            headingRowHeight: 40,
            dataRowMinHeight: 46,
            dataRowMaxHeight: 52,
            headingRowColor: WidgetStateProperty.all(AppTheme.bgSurface),
            border: TableBorder(
              horizontalInside: const BorderSide(color: AppTheme.borderSubtle, width: 0.6),
              bottom: const BorderSide(color: AppTheme.borderSubtle, width: 1.0),
            ),
            columns: const [
              DataColumn(label: Text('SYMBOL', style: _columnHeaderStyle)),
              DataColumn(label: Text('SIDE', style: _columnHeaderStyle)),
              DataColumn(label: Text('QTY', style: _columnHeaderStyle), numeric: true),
              DataColumn(label: Text('AVG ENTRY (₹)', style: _columnHeaderStyle), numeric: true),
              DataColumn(label: Text('LTP (₹)', style: _columnHeaderStyle), numeric: true),
              DataColumn(label: Text('STOP-LOSS (₹)', style: _columnHeaderStyle), numeric: true),
              DataColumn(label: Text('TARGET (₹)', style: _columnHeaderStyle), numeric: true),
              DataColumn(label: Text('UNREALIZED P&L', style: _columnHeaderStyle), numeric: true),
              DataColumn(label: Text('RETURN %', style: _columnHeaderStyle), numeric: true),
              DataColumn(label: Text('STATUS', style: _columnHeaderStyle)),
              DataColumn(label: Text('ACTIONS', style: _columnHeaderStyle)),
            ],
            rows: _positions.map((p) {
              final isProfit = p.unrealizedPnl >= 0;
              final color = isProfit ? AppTheme.colorProfit : AppTheme.colorLoss;

              return DataRow(
                color: WidgetStateProperty.resolveWith<Color?>((states) {
                  if (states.contains(WidgetState.hovered)) {
                    return AppTheme.bgCardHover;
                  }
                  return isProfit
                      ? AppTheme.colorProfit.withOpacity(0.02)
                      : AppTheme.colorLoss.withOpacity(0.02);
                }),
                cells: [
                  // Symbol
                  DataCell(
                    Text(
                      p.symbol,
                      style: const TextStyle(
                        fontSize: 13,
                        fontWeight: FontWeight.w700,
                        color: AppTheme.textPrimary,
                      ),
                    ),
                  ),

                  // Side
                  DataCell(
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                      decoration: BoxDecoration(
                        color: (p.side == 'BUY' || p.side == 'LONG'
                                ? AppTheme.colorProfit
                                : AppTheme.colorLoss)
                            .withOpacity(0.12),
                        borderRadius: BorderRadius.circular(4),
                      ),
                      child: Text(
                        p.side,
                        style: TextStyle(
                          fontSize: 10,
                          fontWeight: FontWeight.w700,
                          color: p.side == 'BUY' || p.side == 'LONG'
                              ? AppTheme.colorProfit
                              : AppTheme.colorLoss,
                        ),
                      ),
                    ),
                  ),

                  // Qty
                  DataCell(
                    Text(
                      '${p.quantity}',
                      style: AppTheme.monoStyle(fontSize: 12, fontWeight: FontWeight.w600),
                    ),
                  ),

                  // Avg Entry
                  DataCell(
                    Text(
                      '₹${p.averageEntryPrice.toStringAsFixed(2)}',
                      style: AppTheme.monoStyle(fontSize: 12),
                    ),
                  ),

                  // Current Price
                  DataCell(
                    Text(
                      '₹${p.currentPrice.toStringAsFixed(2)}',
                      style: AppTheme.monoStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                        color: AppTheme.textPrimary,
                      ),
                    ),
                  ),

                  // Stop Loss
                  DataCell(
                    Text(
                      '₹${p.stopLoss.toStringAsFixed(2)}',
                      style: AppTheme.monoStyle(fontSize: 12, color: AppTheme.colorLoss),
                    ),
                  ),

                  // Target
                  DataCell(
                    Text(
                      '₹${p.target.toStringAsFixed(2)}',
                      style: AppTheme.monoStyle(fontSize: 12, color: AppTheme.colorProfit),
                    ),
                  ),

                  // Unrealized P&L
                  DataCell(
                    Text(
                      '${isProfit ? "+" : ""}₹${p.unrealizedPnl.toStringAsFixed(2)}',
                      style: AppTheme.monoStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w700,
                        color: color,
                      ),
                    ),
                  ),

                  // Return %
                  DataCell(
                    Text(
                      '${isProfit ? "+" : ""}${p.returnPct.toStringAsFixed(2)}%',
                      style: AppTheme.monoStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                        color: color,
                      ),
                    ),
                  ),

                  // Status
                  DataCell(
                    StatusBadge(status: p.status),
                  ),

                  // Actions
                  DataCell(
                    IconButton(
                      icon: const Icon(Icons.info_outline, size: 16, color: AppTheme.accentCyan),
                      tooltip: 'Position Details',
                      onPressed: () => _showPositionDetails(p),
                    ),
                  ),
                ],
              );
            }).toList(),
          ),
        ),
      ),
    );
  }

  Widget _buildOrdersTab() {
    if (_orders.isEmpty) {
      return const Center(
        child: EmptyStateView(
          title: 'No Paper Orders Found',
          description: 'Simulated paper orders will appear here once breakout conditions trigger order generation.',
          icon: Icons.receipt_long_outlined,
        ),
      );
    }

    return SingleChildScrollView(
      scrollDirection: Axis.vertical,
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: ConstrainedBox(
          constraints: BoxConstraints(
            minWidth: MediaQuery.of(context).size.width,
          ),
          child: DataTable(
            columnSpacing: 22,
            horizontalMargin: 20,
            headingRowHeight: 40,
            dataRowMinHeight: 46,
            dataRowMaxHeight: 52,
            headingRowColor: WidgetStateProperty.all(AppTheme.bgSurface),
            border: TableBorder(
              horizontalInside: const BorderSide(color: AppTheme.borderSubtle, width: 0.6),
              bottom: const BorderSide(color: AppTheme.borderSubtle, width: 1.0),
            ),
            columns: const [
              DataColumn(label: Text('ORDER ID', style: _columnHeaderStyle)),
              DataColumn(label: Text('TIMESTAMP', style: _columnHeaderStyle)),
              DataColumn(label: Text('SYMBOL', style: _columnHeaderStyle)),
              DataColumn(label: Text('TYPE', style: _columnHeaderStyle)),
              DataColumn(label: Text('SIDE', style: _columnHeaderStyle)),
              DataColumn(label: Text('QTY', style: _columnHeaderStyle), numeric: true),
              DataColumn(label: Text('REQ PRICE (₹)', style: _columnHeaderStyle), numeric: true),
              DataColumn(label: Text('EXEC PRICE (₹)', style: _columnHeaderStyle), numeric: true),
              DataColumn(label: Text('STATUS', style: _columnHeaderStyle)),
            ],
            rows: _orders.map((o) {
              return DataRow(
                cells: [
                  DataCell(
                    Text('#${o.id}', style: AppTheme.monoStyle(fontSize: 11, color: AppTheme.textMuted)),
                  ),
                  DataCell(
                    Text(
                      _formatDate(o.createdAt),
                      style: AppTheme.monoStyle(fontSize: 11, color: AppTheme.textSecondary),
                    ),
                  ),
                  DataCell(
                    Text(
                      o.symbol,
                      style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 12),
                    ),
                  ),
                  DataCell(
                    Text(o.orderType, style: const TextStyle(fontSize: 11, color: AppTheme.textSecondary)),
                  ),
                  DataCell(
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                      decoration: BoxDecoration(
                        color: (o.transactionType == 'BUY'
                                ? AppTheme.colorProfit
                                : AppTheme.colorLoss)
                            .withOpacity(0.12),
                        borderRadius: BorderRadius.circular(4),
                      ),
                      child: Text(
                        o.transactionType,
                        style: TextStyle(
                          fontSize: 10,
                          fontWeight: FontWeight.w700,
                          color: o.transactionType == 'BUY'
                              ? AppTheme.colorProfit
                              : AppTheme.colorLoss,
                        ),
                      ),
                    ),
                  ),
                  DataCell(
                    Text('${o.quantity}', style: AppTheme.monoStyle(fontSize: 12, fontWeight: FontWeight.w600)),
                  ),
                  DataCell(
                    Text('₹${o.requestedPrice.toStringAsFixed(2)}', style: AppTheme.monoStyle(fontSize: 12)),
                  ),
                  DataCell(
                    Text(
                      o.executedPrice != null ? '₹${o.executedPrice!.toStringAsFixed(2)}' : '—',
                      style: AppTheme.monoStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                        color: o.executedPrice != null ? AppTheme.accentCyan : AppTheme.textMuted,
                      ),
                    ),
                  ),
                  DataCell(
                    StatusBadge(status: o.status),
                  ),
                ],
              );
            }).toList(),
          ),
        ),
      ),
    );
  }

  Widget _buildTradeHistoryTab() {
    if (_trades.isEmpty) {
      return const Center(
        child: EmptyStateView(
          title: 'No Trade History Logged',
          description: 'Chronological trade execution events will appear here once simulated trades are logged.',
          icon: Icons.history_edu_outlined,
        ),
      );
    }

    return SingleChildScrollView(
      scrollDirection: Axis.vertical,
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: ConstrainedBox(
          constraints: BoxConstraints(
            minWidth: MediaQuery.of(context).size.width,
          ),
          child: DataTable(
            columnSpacing: 24,
            horizontalMargin: 20,
            headingRowHeight: 40,
            dataRowMinHeight: 46,
            dataRowMaxHeight: 52,
            headingRowColor: WidgetStateProperty.all(AppTheme.bgSurface),
            border: TableBorder(
              horizontalInside: const BorderSide(color: AppTheme.borderSubtle, width: 0.6),
              bottom: const BorderSide(color: AppTheme.borderSubtle, width: 1.0),
            ),
            columns: const [
              DataColumn(label: Text('ID', style: _columnHeaderStyle)),
              DataColumn(label: Text('TIMESTAMP', style: _columnHeaderStyle)),
              DataColumn(label: Text('SYMBOL', style: _columnHeaderStyle)),
              DataColumn(label: Text('ACTION', style: _columnHeaderStyle)),
              DataColumn(label: Text('QUANTITY', style: _columnHeaderStyle), numeric: true),
              DataColumn(label: Text('FILL PRICE (₹)', style: _columnHeaderStyle), numeric: true),
              DataColumn(label: Text('REALIZED P&L', style: _columnHeaderStyle), numeric: true),
              DataColumn(label: Text('MODE', style: _columnHeaderStyle)),
            ],
            rows: _trades.map((t) {
              final isProfit = (t.pnl ?? 0) >= 0;
              final pnlColor = isProfit ? AppTheme.colorProfit : AppTheme.colorLoss;

              return DataRow(
                cells: [
                  DataCell(Text('#${t.id}', style: AppTheme.monoStyle(fontSize: 11, color: AppTheme.textMuted))),
                  DataCell(
                    Text(
                      _formatDate(t.logTimestamp),
                      style: AppTheme.monoStyle(fontSize: 11, color: AppTheme.textSecondary),
                    ),
                  ),
                  DataCell(
                    Text(t.symbol, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 12)),
                  ),
                  DataCell(
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                      decoration: BoxDecoration(
                        color: (t.action.contains('BUY') || t.action.contains('ENTRY')
                                ? AppTheme.colorProfit
                                : AppTheme.colorLoss)
                            .withOpacity(0.12),
                        borderRadius: BorderRadius.circular(4),
                      ),
                      child: Text(
                        t.action,
                        style: TextStyle(
                          fontSize: 10,
                          fontWeight: FontWeight.w700,
                          color: t.action.contains('BUY') || t.action.contains('ENTRY')
                              ? AppTheme.colorProfit
                              : AppTheme.colorLoss,
                        ),
                      ),
                    ),
                  ),
                  DataCell(
                    Text('${t.quantity}', style: AppTheme.monoStyle(fontSize: 12, fontWeight: FontWeight.w600)),
                  ),
                  DataCell(
                    Text('₹${t.price.toStringAsFixed(2)}', style: AppTheme.monoStyle(fontSize: 12)),
                  ),
                  DataCell(
                    Text(
                      t.pnl != null
                          ? '${isProfit ? "+" : ""}₹${t.pnl!.toStringAsFixed(2)}'
                          : '—',
                      style: AppTheme.monoStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w700,
                        color: t.pnl != null ? pnlColor : AppTheme.textMuted,
                      ),
                    ),
                  ),
                  DataCell(
                    Text(
                      t.isPaper ? 'SIMULATED' : 'LIVE',
                      style: TextStyle(
                        fontSize: 10,
                        fontWeight: FontWeight.w700,
                        color: AppTheme.accentAmber,
                      ),
                    ),
                  ),
                ],
              );
            }).toList(),
          ),
        ),
      ),
    );
  }

  Widget _buildChargesAndSlippageTab() {
    // Model statutory fees on sample 5000 capital turnover
    // Indian Intraday Equity Rates:
    // STT: 0.025% on sell side only
    // Exchange Turnover Fee: 0.00345% both sides (NSE)
    // SEBI Charges: ₹10 per crore (0.0001%)
    // GST: 18% on (Brokerage + Exchange turnover fees + SEBI)
    // Stamp Duty: 0.015% or 0.003% on buy side (Intraday: 0.003%)
    // Simulated Slippage: 0.05% modeled execution delay

    final sampleTurnover = 5000.0;
    final stt = sampleTurnover * 0.00025;
    final exchangeFee = sampleTurnover * 0.0000345 * 2;
    final sebi = sampleTurnover * 0.000001 * 2;
    final gst = (exchangeFee + sebi) * 0.18;
    final stampDuty = sampleTurnover * 0.00003;
    final slippage = sampleTurnover * 0.0005;
    final totalCharges = stt + exchangeFee + sebi + gst + stampDuty;

    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Text(
                'STATUTORY TRANSACTION CHARGES & SLIPPAGE AUDIT',
                style: TextStyle(
                  fontSize: 15,
                  fontWeight: FontWeight.w800,
                  letterSpacing: 0.5,
                  color: AppTheme.textPrimary,
                ),
              ),
              const SizedBox(width: 10),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
                decoration: BoxDecoration(
                  color: AppTheme.accentCyan.withOpacity(0.12),
                  borderRadius: BorderRadius.circular(4),
                ),
                child: const Text(
                  'INDIAN EQUITY INTRADAY SCHEDULE',
                  style: TextStyle(
                    fontSize: 10,
                    fontWeight: FontWeight.w700,
                    color: AppTheme.accentCyan,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 6),
          const Text(
            'The paper trading engine accurately computes realistic post-charge intraday net returns, accounting for all statutory levies and modeled execution slippage.',
            style: TextStyle(fontSize: 12, color: AppTheme.textMuted),
          ),
          const SizedBox(height: 20),

          // Charge Breakdown Cards
          LayoutBuilder(
            builder: (context, constraints) {
              final isCompact = constraints.maxWidth < 900;
              return Wrap(
                spacing: 16,
                runSpacing: 16,
                children: [
                  _feeDetailCard(
                    title: 'Securities Transaction Tax (STT)',
                    rate: '0.025% on Sell Side',
                    amount: '₹${stt.toStringAsFixed(2)}',
                    description: 'Levied on the sell turnover of equity intraday transactions.',
                    isCompact: isCompact,
                  ),
                  _feeDetailCard(
                    title: 'NSE Exchange Turnover Fee',
                    rate: '0.00345% Buy & Sell',
                    amount: '₹${exchangeFee.toStringAsFixed(2)}',
                    description: 'Transaction fees charged by the National Stock Exchange.',
                    isCompact: isCompact,
                  ),
                  _feeDetailCard(
                    title: 'SEBI Turnover Charges',
                    rate: '₹10 / Crore (0.0001%)',
                    amount: '₹${sebi.toStringAsFixed(3)}',
                    description: 'Regulatory fees charged by SEBI across all markets.',
                    isCompact: isCompact,
                  ),
                  _feeDetailCard(
                    title: 'Goods & Services Tax (GST)',
                    rate: '18% on Fees',
                    amount: '₹${gst.toStringAsFixed(2)}',
                    description: '18% GST applicable on exchange and brokerage fees.',
                    isCompact: isCompact,
                  ),
                  _feeDetailCard(
                    title: 'Stamp Duty (State Levy)',
                    rate: '0.003% on Buy Side',
                    amount: '₹${stampDuty.toStringAsFixed(2)}',
                    description: 'Government stamp duty charged on delivery & intraday buy turnover.',
                    isCompact: isCompact,
                  ),
                  _feeDetailCard(
                    title: 'Modeled Execution Slippage',
                    rate: '0.05% Conservative Fill',
                    amount: '₹${slippage.toStringAsFixed(2)}',
                    description: 'Simulates realistic bid-ask spread crossing and queue latency.',
                    isCompact: isCompact,
                    accentColor: AppTheme.accentAmber,
                  ),
                ],
              );
            },
          ),
          const SizedBox(height: 24),

          // Summary container
          Container(
            padding: const EdgeInsets.all(18),
            decoration: BoxDecoration(
              color: AppTheme.bgSurface,
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: AppTheme.borderSubtle),
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'Total Estimated Friction per Round-Trip (₹5,000 Capital)',
                      style: TextStyle(
                        fontSize: 13,
                        fontWeight: FontWeight.w700,
                        color: AppTheme.textPrimary,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      'Statutory Charges: ₹${totalCharges.toStringAsFixed(2)} + Modeled Slippage: ₹${slippage.toStringAsFixed(2)}',
                      style: const TextStyle(fontSize: 11, color: AppTheme.textMuted),
                    ),
                  ],
                ),
                Text(
                  '₹${(totalCharges + slippage).toStringAsFixed(2)} (~${((totalCharges + slippage) / sampleTurnover * 100).toStringAsFixed(3)}%)',
                  style: AppTheme.monoStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.w800,
                    color: AppTheme.accentCyan,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _feeDetailCard({
    required String title,
    required String rate,
    required String amount,
    required String description,
    required bool isCompact,
    Color? accentColor,
  }) {
    return Container(
      width: isCompact ? double.infinity : 340,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppTheme.bgSurface,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppTheme.borderSubtle),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Expanded(
                child: Text(
                  title,
                  style: const TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w700,
                    color: AppTheme.textPrimary,
                  ),
                ),
              ),
              Text(
                amount,
                style: AppTheme.monoStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.w700,
                  color: accentColor ?? AppTheme.textPrimary,
                ),
              ),
            ],
          ),
          const SizedBox(height: 6),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
            decoration: BoxDecoration(
              color: AppTheme.bgCard,
              borderRadius: BorderRadius.circular(4),
              border: Border.all(color: AppTheme.borderSubtle),
            ),
            child: Text(
              rate,
              style: AppTheme.monoStyle(
                fontSize: 10,
                color: accentColor ?? AppTheme.accentCyan,
              ),
            ),
          ),
          const SizedBox(height: 8),
          Text(
            description,
            style: const TextStyle(fontSize: 11, color: AppTheme.textMuted),
          ),
        ],
      ),
    );
  }

  void _showPositionDetails(PositionItem p) {
    showDialog(
      context: context,
      builder: (ctx) {
        final isProfit = p.unrealizedPnl >= 0;
        final pnlColor = isProfit ? AppTheme.colorProfit : AppTheme.colorLoss;

        return AlertDialog(
          backgroundColor: AppTheme.bgSurface,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(10),
            side: const BorderSide(color: AppTheme.borderSubtle),
          ),
          title: Row(
            children: [
              Text(
                p.symbol,
                style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w800, color: AppTheme.textPrimary),
              ),
              const SizedBox(width: 10),
              StatusBadge(status: p.status),
            ],
          ),
          content: SizedBox(
            width: 400,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                _detailRow('Side / Direction', p.side),
                _detailRow('Position Quantity', '${p.quantity} shares'),
                _detailRow('Average Entry Price', '₹${p.averageEntryPrice.toStringAsFixed(2)}'),
                _detailRow('Current Market Price (LTP)', '₹${p.currentPrice.toStringAsFixed(2)}'),
                _detailRow('Stop-Loss Trigger', '₹${p.stopLoss.toStringAsFixed(2)}', color: AppTheme.colorLoss),
                _detailRow('Target Price', '₹${p.target.toStringAsFixed(2)}', color: AppTheme.colorProfit),
                _detailRow(
                  'Unrealized P&L',
                  '${isProfit ? "+" : ""}₹${p.unrealizedPnl.toStringAsFixed(2)} (${p.returnPct.toStringAsFixed(2)}%)',
                  color: pnlColor,
                ),
                _detailRow('Entry Timestamp', _formatDate(p.entryTime)),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(ctx),
              child: const Text('CLOSE', style: TextStyle(color: AppTheme.textMuted)),
            ),
          ],
        );
      },
    );
  }

  Widget _detailRow(String label, String value, {Color? color}) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6.0),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: const TextStyle(fontSize: 12, color: AppTheme.textSecondary)),
          Text(
            value,
            style: AppTheme.monoStyle(
              fontSize: 12,
              fontWeight: FontWeight.w700,
              color: color ?? AppTheme.textPrimary,
            ),
          ),
        ],
      ),
    );
  }

  String _formatDate(String isoString) {
    if (isoString.isEmpty) return '—';
    try {
      final dt = DateTime.parse(isoString);
      return DateFormat('dd MMM, HH:mm:ss').format(dt);
    } catch (_) {
      return isoString;
    }
  }

  static const _columnHeaderStyle = TextStyle(
    fontSize: 11,
    fontWeight: FontWeight.w700,
    letterSpacing: 0.5,
    color: AppTheme.textMuted,
  );
}
