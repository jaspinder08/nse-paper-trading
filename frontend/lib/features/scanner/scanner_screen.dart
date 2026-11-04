import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../../core/theme/app_theme.dart';
import '../../models/api_models.dart';
import '../../services/api_service.dart';
import '../../shared/components/status_badge.dart';
import '../../shared/components/empty_state_view.dart';

class ScannerScreen extends StatefulWidget {
  const ScannerScreen({super.key});

  @override
  State<ScannerScreen> createState() => _ScannerScreenState();
}

class _ScannerScreenState extends State<ScannerScreen> {
  bool _isLoading = true;
  List<ScannerCandidate> _candidates = [];
  MarketStatusInfo? _marketStatus;
  DateTime? _lastUpdated;
  String _selectedFilter = 'ALL';
  String _searchQuery = '';
  final TextEditingController _searchController = TextEditingController();

  // Sorting
  int _sortColumnIndex = 0;
  bool _sortAscending = true;

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  Future<void> _loadData() async {
    setState(() => _isLoading = true);
    try {
      final results = await Future.wait([
        apiService.getScannerCandidates(),
        apiService.getMarketStatus(),
      ]);

      if (mounted) {
        setState(() {
          _candidates = results[0] as List<ScannerCandidate>;
          _marketStatus = results[1] as MarketStatusInfo;
          _lastUpdated = DateTime.now();
          _isLoading = false;
        });
        _applySort();
      }
    } catch (_) {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  List<ScannerCandidate> get _filteredCandidates {
    return _candidates.where((c) {
      // Filter by search query
      if (_searchQuery.isNotEmpty) {
        if (!c.symbol.toUpperCase().contains(_searchQuery.toUpperCase())) {
          return false;
        }
      }

      // Filter by status pill
      if (_selectedFilter == 'ALL') return true;
      final normStatus = c.status.toUpperCase().replaceAll(' ', '_');
      final normFilter = _selectedFilter.toUpperCase().replaceAll(' ', '_');

      if (normFilter == 'REJECTED') {
        return normStatus.contains('REJECTED');
      }
      if (normFilter == 'BLOCKED') {
        return normStatus.contains('BLOCK');
      }
      return normStatus == normFilter;
    }).toList();
  }

  void _onSort(int columnIndex, bool ascending) {
    setState(() {
      _sortColumnIndex = columnIndex;
      _sortAscending = ascending;
      _applySort();
    });
  }

  void _applySort() {
    _candidates.sort((a, b) {
      int comparison = 0;
      switch (_sortColumnIndex) {
        case 0: // Symbol
          comparison = a.symbol.compareTo(b.symbol);
          break;
        case 1: // LTP
          comparison = a.currentPrice.compareTo(b.currentPrice);
          break;
        case 2: // ORH
          comparison = (a.orbHigh ?? 0).compareTo(b.orbHigh ?? 0);
          break;
        case 3: // ORL
          comparison = (a.orbLow ?? 0).compareTo(b.orbLow ?? 0);
          break;
        case 4: // Breakout Price
          comparison = (a.triggerPrice ?? 0).compareTo(b.triggerPrice ?? 0);
          break;
        case 5: // Volume Ratio
          comparison = (a.volumeRatio ?? 0).compareTo(b.volumeRatio ?? 0);
          break;
        case 6: // Status
          comparison = a.status.compareTo(b.status);
          break;
        case 7: // Est Entry
          comparison = (a.estimatedEntry ?? 0).compareTo(b.estimatedEntry ?? 0);
          break;
        case 8: // Stop Loss
          comparison = (a.stopLoss ?? 0).compareTo(b.stopLoss ?? 0);
          break;
        case 9: // Target
          comparison = (a.targetPrice ?? 0).compareTo(b.targetPrice ?? 0);
          break;
        case 10: // Risk/Reward
          comparison = (a.riskReward ?? 0).compareTo(b.riskReward ?? 0);
          break;
      }
      return _sortAscending ? comparison : -comparison;
    });
  }

  @override
  Widget build(BuildContext context) {
    final filtered = _filteredCandidates;

    return Scaffold(
      backgroundColor: AppTheme.bgCanvas,
      body: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _buildControlHeader(),
          _buildFilterBar(),
          Expanded(
            child: _isLoading
                ? const Center(
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                      color: AppTheme.accentCyan,
                    ),
                  )
                : filtered.isEmpty
                    ? _buildEmptyState()
                    : _buildCandidatesTable(filtered),
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
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
      decoration: const BoxDecoration(
        color: AppTheme.bgSurface,
        border: Border(bottom: BorderSide(color: AppTheme.borderSubtle)),
      ),
      child: Row(
        children: [
          // Title & Strategy
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Row(
                  children: [
                    const Text(
                      'ORB BREAKOUT SCANNER',
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
                        color: AppTheme.accentCyan.withOpacity(0.12),
                        borderRadius: BorderRadius.circular(4),
                        border: Border.all(color: AppTheme.accentCyan.withOpacity(0.3)),
                      ),
                      child: const Text(
                        '15M ORB · 5M EXECUTION',
                        style: TextStyle(
                          fontSize: 10,
                          fontWeight: FontWeight.w700,
                          color: AppTheme.accentCyan,
                          letterSpacing: 0.5,
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 3),
                Text(
                  'Automated intraday candidate qualification across Nifty 50 universe with volume confirmation.',
                  style: TextStyle(
                    fontSize: 11,
                    color: AppTheme.textMuted.withOpacity(0.85),
                  ),
                ),
              ],
            ),
          ),

          // Symbol search input
          SizedBox(
            width: 240,
            height: 36,
            child: TextField(
              controller: _searchController,
              style: const TextStyle(fontSize: 12, color: AppTheme.textPrimary),
              onChanged: (val) => setState(() => _searchQuery = val),
              decoration: InputDecoration(
                hintText: 'Search symbol (e.g. RELIANCE)',
                hintStyle: const TextStyle(fontSize: 11, color: AppTheme.textMuted),
                prefixIcon: const Icon(Icons.search, size: 16, color: AppTheme.textMuted),
                suffixIcon: _searchQuery.isNotEmpty
                    ? IconButton(
                        icon: const Icon(Icons.close, size: 14, color: AppTheme.textMuted),
                        onPressed: () {
                          _searchController.clear();
                          setState(() => _searchQuery = '');
                        },
                      )
                    : null,
                contentPadding: const EdgeInsets.symmetric(horizontal: 10, vertical: 0),
                filled: true,
                fillColor: AppTheme.bgCard,
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(6),
                  borderSide: const BorderSide(color: AppTheme.borderSubtle),
                ),
                enabledBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(6),
                  borderSide: const BorderSide(color: AppTheme.borderSubtle),
                ),
                focusedBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(6),
                  borderSide: const BorderSide(color: AppTheme.accentCyan),
                ),
              ),
            ),
          ),
          const SizedBox(width: 14),

          // Last updated
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

          // Refresh button
          ElevatedButton.icon(
            onPressed: _isLoading ? null : _loadData,
            icon: const Icon(Icons.refresh, size: 14),
            label: const Text('SCAN', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700, letterSpacing: 0.5)),
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

  Widget _buildFilterBar() {
    final filters = [
      'ALL',
      'TRIGGERED',
      'PENDING BREAKOUT',
      'RANGE FORMING',
      'REJECTED VOLUME',
      'BLOCKED BY RISK',
      'NO DATA',
    ];

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 10),
      decoration: const BoxDecoration(
        color: AppTheme.bgCanvas,
        border: Border(bottom: BorderSide(color: AppTheme.borderSubtle)),
      ),
      child: Row(
        children: [
          Expanded(
            child: SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: Row(
                children: filters.map((f) {
                  final isSelected = _selectedFilter == f;
                  final count = _getFilterCount(f);

                  return Padding(
                    padding: const EdgeInsets.only(right: 8.0),
                    child: InkWell(
                      onTap: () => setState(() => _selectedFilter = f),
                      borderRadius: BorderRadius.circular(6),
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                        decoration: BoxDecoration(
                          color: isSelected
                              ? AppTheme.accentCyan.withOpacity(0.16)
                              : AppTheme.bgCard,
                          borderRadius: BorderRadius.circular(6),
                          border: Border.all(
                            color: isSelected
                                ? AppTheme.accentCyan
                                : AppTheme.borderSubtle,
                            width: isSelected ? 1.2 : 1.0,
                          ),
                        ),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Text(
                              f,
                              style: TextStyle(
                                fontSize: 11,
                                fontWeight: isSelected ? FontWeight.w700 : FontWeight.w500,
                                color: isSelected
                                    ? AppTheme.accentCyan
                                    : AppTheme.textSecondary,
                                letterSpacing: 0.3,
                              ),
                            ),
                            if (count > 0) ...[
                              const SizedBox(width: 6),
                              Container(
                                padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1),
                                decoration: BoxDecoration(
                                  color: isSelected
                                      ? AppTheme.accentCyan.withOpacity(0.3)
                                      : AppTheme.bgSurface,
                                  borderRadius: BorderRadius.circular(10),
                                ),
                                child: Text(
                                  '$count',
                                  style: AppTheme.monoStyle(
                                    fontSize: 9,
                                    fontWeight: FontWeight.w700,
                                    color: isSelected ? Colors.white : AppTheme.textMuted,
                                  ),
                                ),
                              ),
                            ],
                          ],
                        ),
                      ),
                    ),
                  );
                }).toList(),
              ),
            ),
          ),
          const SizedBox(width: 12),
          Text(
            'Showing ${_filteredCandidates.length} of ${_candidates.length} symbols',
            style: const TextStyle(
              fontSize: 11,
              color: AppTheme.textMuted,
            ),
          ),
        ],
      ),
    );
  }

  int _getFilterCount(String filter) {
    if (filter == 'ALL') return _candidates.length;
    final normFilter = filter.toUpperCase().replaceAll(' ', '_');
    return _candidates.where((c) {
      final normStatus = c.status.toUpperCase().replaceAll(' ', '_');
      if (normFilter == 'REJECTED_VOLUME') {
        return normStatus.contains('REJECTED');
      }
      if (normFilter == 'BLOCKED_BY_RISK') {
        return normStatus.contains('BLOCK');
      }
      return normStatus == normFilter;
    }).length;
  }

  Widget _buildEmptyState() {
    String title = 'No Candidates Found';
    String message = 'No ORB candidate setups currently qualify under the selected criteria.';
    IconData icon = Icons.candlestick_chart_outlined;

    if (_searchQuery.isNotEmpty) {
      title = 'No Matching Symbols';
      message = 'No candidate symbol found matching "$_searchQuery".';
      icon = Icons.search_off;
    } else if (_marketStatus != null && !_marketStatus!.isMarketOpen) {
      title = 'NSE Market Closed';
      message = 'NSE equity regular market hours are 09:15 - 15:30 IST. 15-minute Opening Range forms between 09:15 and 09:30 IST.';
      icon = Icons.schedule;
    } else if (_selectedFilter != 'ALL') {
      title = 'No $_selectedFilter Setups';
      message = 'None of the monitored universe symbols have the status "$_selectedFilter" at this moment.';
    }

    return Center(
      child: EmptyStateView(
        title: title,
        description: message,
        icon: icon,
        actionLabel: 'REFRESH SCANNER',
        onAction: _loadData,
      ),
    );
  }

  Widget _buildCandidatesTable(List<ScannerCandidate> items) {
    return SingleChildScrollView(
      scrollDirection: Axis.vertical,
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: ConstrainedBox(
          constraints: BoxConstraints(
            minWidth: MediaQuery.of(context).size.width,
          ),
          child: DataTable(
            sortColumnIndex: _sortColumnIndex,
            sortAscending: _sortAscending,
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
            columns: [
              _buildDataColumn('SYMBOL', 0),
              _buildDataColumn('LTP (₹)', 1, numeric: true),
              _buildDataColumn('ORH (₹)', 2, numeric: true),
              _buildDataColumn('ORL (₹)', 3, numeric: true),
              _buildDataColumn('BREAKOUT (₹)', 4, numeric: true),
              _buildDataColumn('VOL RATIO', 5, numeric: true),
              _buildDataColumn('SIGNAL STATE', 6),
              _buildDataColumn('EST. ENTRY (₹)', 7, numeric: true),
              _buildDataColumn('STOP-LOSS (₹)', 8, numeric: true),
              _buildDataColumn('TARGET (₹)', 9, numeric: true),
              _buildDataColumn('R : R', 10, numeric: true),
              const DataColumn(
                label: Text(
                  'NOTES / REASON',
                  style: TextStyle(
                    fontSize: 11,
                    fontWeight: FontWeight.w700,
                    letterSpacing: 0.5,
                    color: AppTheme.textMuted,
                  ),
                ),
              ),
            ],
            rows: items.map((c) {
              final isTriggered = c.status.contains('TRIGGERED');
              final isPending = c.status.contains('PENDING');

              return DataRow(
                color: WidgetStateProperty.resolveWith<Color?>((states) {
                  if (states.contains(WidgetState.hovered)) {
                    return AppTheme.bgCardHover;
                  }
                  if (isTriggered) {
                    return AppTheme.colorProfit.withOpacity(0.04);
                  }
                  if (isPending) {
                    return AppTheme.accentAmber.withOpacity(0.03);
                  }
                  return null;
                }),
                cells: [
                  // Symbol
                  DataCell(
                    Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Container(
                          width: 3,
                          height: 20,
                          decoration: BoxDecoration(
                            color: isTriggered
                                ? AppTheme.colorProfit
                                : isPending
                                    ? AppTheme.accentAmber
                                    : AppTheme.borderSubtle,
                            borderRadius: BorderRadius.circular(2),
                          ),
                        ),
                        const SizedBox(width: 8),
                        Text(
                          c.symbol,
                          style: const TextStyle(
                            fontSize: 13,
                            fontWeight: FontWeight.w700,
                            letterSpacing: 0.4,
                            color: AppTheme.textPrimary,
                          ),
                        ),
                      ],
                    ),
                  ),

                  // LTP
                  DataCell(
                    Text(
                      c.currentPrice > 0
                          ? '₹${c.currentPrice.toStringAsFixed(2)}'
                          : '—',
                      style: AppTheme.monoStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                        color: AppTheme.textPrimary,
                      ),
                    ),
                  ),

                  // ORH
                  DataCell(
                    Text(
                      c.orbHigh != null ? '₹${c.orbHigh!.toStringAsFixed(2)}' : '—',
                      style: AppTheme.monoStyle(
                        fontSize: 12,
                        color: AppTheme.colorProfit,
                      ),
                    ),
                  ),

                  // ORL
                  DataCell(
                    Text(
                      c.orbLow != null ? '₹${c.orbLow!.toStringAsFixed(2)}' : '—',
                      style: AppTheme.monoStyle(
                        fontSize: 12,
                        color: AppTheme.colorLoss,
                      ),
                    ),
                  ),

                  // Breakout Price
                  DataCell(
                    Text(
                      c.triggerPrice != null
                          ? '₹${c.triggerPrice!.toStringAsFixed(2)}'
                          : '—',
                      style: AppTheme.monoStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w700,
                        color: AppTheme.accentCyan,
                      ),
                    ),
                  ),

                  // Volume Ratio
                  DataCell(
                    c.volumeRatio != null
                        ? Container(
                            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                            decoration: BoxDecoration(
                              color: (c.volumeRatio! >= 1.0
                                      ? AppTheme.colorProfit
                                      : AppTheme.accentAmber)
                                  .withValues(alpha: 0.12),
                              borderRadius: BorderRadius.circular(4),
                            ),
                            child: Text(
                              '${c.volumeRatio!.toStringAsFixed(2)}x',
                              style: AppTheme.monoStyle(
                                fontSize: 11,
                                fontWeight: FontWeight.w700,
                                color: c.volumeRatio! >= 1.0
                                    ? AppTheme.colorProfit
                                    : AppTheme.accentAmber,
                              ),
                            ),
                          )
                        : const Text('—', style: TextStyle(color: AppTheme.textMuted)),
                  ),

                  // Signal State
                  DataCell(
                    StatusBadge(status: c.status),
                  ),

                  // Estimated Entry
                  DataCell(
                    Text(
                      c.estimatedEntry != null
                          ? '₹${c.estimatedEntry!.toStringAsFixed(2)}'
                          : '—',
                      style: AppTheme.monoStyle(
                        fontSize: 12,
                        color: AppTheme.textSecondary,
                      ),
                    ),
                  ),

                  // Stop Loss
                  DataCell(
                    Text(
                      c.stopLoss != null ? '₹${c.stopLoss!.toStringAsFixed(2)}' : '—',
                      style: AppTheme.monoStyle(
                        fontSize: 12,
                        color: AppTheme.colorLoss,
                      ),
                    ),
                  ),

                  // Target
                  DataCell(
                    Text(
                      c.targetPrice != null
                          ? '₹${c.targetPrice!.toStringAsFixed(2)}'
                          : '—',
                      style: AppTheme.monoStyle(
                        fontSize: 12,
                        color: AppTheme.colorProfit,
                      ),
                    ),
                  ),

                  // Risk / Reward
                  DataCell(
                    Text(
                      '1 : ${(c.riskReward ?? 1.5).toStringAsFixed(1)}',
                      style: AppTheme.monoStyle(
                        fontSize: 11,
                        color: AppTheme.textSecondary,
                      ),
                    ),
                  ),

                  // Reason / Notes
                  DataCell(
                    ConstrainedBox(
                      constraints: const BoxConstraints(maxWidth: 220),
                      child: Text(
                        c.reason.isNotEmpty ? c.reason : '—',
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(
                          fontSize: 11,
                          color: c.status.contains('REJECT') || c.status.contains('BLOCK')
                              ? AppTheme.colorLoss
                              : AppTheme.textMuted,
                        ),
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

  DataColumn _buildDataColumn(String label, int index, {bool numeric = false}) {
    return DataColumn(
      numeric: numeric,
      onSort: _onSort,
      label: Text(
        label,
        style: const TextStyle(
          fontSize: 11,
          fontWeight: FontWeight.w700,
          letterSpacing: 0.5,
          color: AppTheme.textMuted,
        ),
      ),
    );
  }
}
