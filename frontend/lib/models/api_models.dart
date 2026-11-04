class PortfolioSummary {
  final double totalCapital;
  final double availableMargin;
  final double utilizedMargin;
  final double cashReserve;
  final double realizedPnl;
  final double unrealizedPnl;
  final double netEquity;
  final int openPositionsCount;
  final bool isPaper;

  PortfolioSummary({
    required this.totalCapital,
    required this.availableMargin,
    required this.utilizedMargin,
    required this.cashReserve,
    required this.realizedPnl,
    required this.unrealizedPnl,
    required this.netEquity,
    required this.openPositionsCount,
    this.isPaper = true,
  });

  factory PortfolioSummary.fromJson(Map<String, dynamic> json) {
    return PortfolioSummary(
      totalCapital: (json['total_capital'] as num?)?.toDouble() ?? 5000.0,
      availableMargin: (json['available_margin'] as num?)?.toDouble() ?? 4500.0,
      utilizedMargin: (json['utilized_margin'] as num?)?.toDouble() ?? 0.0,
      cashReserve: (json['cash_reserve'] as num?)?.toDouble() ?? 500.0,
      realizedPnl: (json['realized_pnl'] as num?)?.toDouble() ?? 0.0,
      unrealizedPnl: (json['unrealized_pnl'] as num?)?.toDouble() ?? 0.0,
      netEquity: (json['net_equity'] as num?)?.toDouble() ?? 5000.0,
      openPositionsCount: (json['open_positions_count'] as num?)?.toInt() ?? 0,
      isPaper: json['is_paper'] as bool? ?? true,
    );
  }
}

class TradingSessionSummary {
  final int id;
  final String sessionDate;
  final String status;
  final double initialCapital;
  final double realizedPnl;
  final double unrealizedPnl;
  final int totalTrades;
  final int winningTrades;
  final int losingTrades;

  TradingSessionSummary({
    required this.id,
    required this.sessionDate,
    required this.status,
    required this.initialCapital,
    required this.realizedPnl,
    required this.unrealizedPnl,
    required this.totalTrades,
    required this.winningTrades,
    required this.losingTrades,
  });

  factory TradingSessionSummary.fromJson(Map<String, dynamic> json) {
    return TradingSessionSummary(
      id: json['id'] as int? ?? 0,
      sessionDate: json['session_date'] as String? ?? '',
      status: json['status'] as String? ?? 'SCHEDULED',
      initialCapital: (json['initial_capital'] as num?)?.toDouble() ?? 5000.0,
      realizedPnl: (json['realized_pnl'] as num?)?.toDouble() ?? 0.0,
      unrealizedPnl: (json['unrealized_pnl'] as num?)?.toDouble() ?? 0.0,
      totalTrades: json['total_trades'] as int? ?? 0,
      winningTrades: json['winning_trades'] as int? ?? 0,
      losingTrades: json['losing_trades'] as int? ?? 0,
    );
  }
}

class MarketStatusInfo {
  final bool isMarketOpen;
  final String sessionType;
  final String currentTime;
  final String? marketOpenTime;
  final String? marketCloseTime;
  final String? description;

  MarketStatusInfo({
    required this.isMarketOpen,
    required this.sessionType,
    required this.currentTime,
    this.marketOpenTime,
    this.marketCloseTime,
    this.description,
  });

  factory MarketStatusInfo.fromJson(Map<String, dynamic> json) {
    return MarketStatusInfo(
      isMarketOpen: json['is_market_open'] as bool? ?? false,
      sessionType: json['session_type'] as String? ?? 'REGULAR',
      currentTime: json['current_time'] as String? ?? '',
      marketOpenTime: json['market_open_time'] as String?,
      marketCloseTime: json['market_close_time'] as String?,
      description: json['description'] as String?,
    );
  }
}

class ScannerCandidate {
  final String symbol;
  final String status;
  final double currentPrice;
  final double? orbHigh;
  final double? orbLow;
  final double? triggerPrice;
  final double? stopLoss;
  final double? targetPrice;
  final double? estimatedEntry;
  final double? volumeRatio;
  final double? proximityPct;
  final double? riskReward;
  final String reason;
  final String? lastCandleTime;

  ScannerCandidate({
    required this.symbol,
    required this.status,
    required this.currentPrice,
    this.orbHigh,
    this.orbLow,
    this.triggerPrice,
    this.stopLoss,
    this.targetPrice,
    this.estimatedEntry,
    this.volumeRatio,
    this.proximityPct,
    this.riskReward = 1.5,
    required this.reason,
    this.lastCandleTime,
  });

  factory ScannerCandidate.fromJson(Map<String, dynamic> json) {
    final signal = json['signal'] as Map<String, dynamic>?;

    final oHigh = (json['orb_high'] as num?)?.toDouble() ??
        (json['trigger_price'] as num?)?.toDouble();
    final oLow = (json['orb_low'] as num?)?.toDouble() ??
        (json['stop_loss'] as num?)?.toDouble();
    final entry = (signal?['entry_price'] as num?)?.toDouble() ?? oHigh;
    final sl = (signal?['stop_loss'] as num?)?.toDouble() ?? oLow;
    final tgt = (signal?['target_price'] as num?)?.toDouble() ??
        (json['target_price'] as num?)?.toDouble();
    final rr = (signal?['risk_reward_ratio'] as num?)?.toDouble() ?? 1.5;

    return ScannerCandidate(
      symbol: json['symbol'] as String? ?? '',
      status: (json['status'] as String? ?? 'PENDING').toUpperCase(),
      currentPrice: (json['current_price'] as num?)?.toDouble() ?? 0.0,
      orbHigh: oHigh,
      orbLow: oLow,
      triggerPrice: oHigh,
      stopLoss: sl,
      targetPrice: tgt,
      estimatedEntry: entry,
      volumeRatio: (json['volume_ratio'] as num?)?.toDouble(),
      proximityPct: (json['distance_to_high_pct'] as num?)?.toDouble() ??
          (json['proximity_pct'] as num?)?.toDouble(),
      riskReward: rr,
      reason: json['reason'] as String? ??
          json['rejection_reason'] as String? ??
          '',
      lastCandleTime: json['last_candle_time'] as String?,
    );
  }
}

class PositionItem {
  final int id;
  final String symbol;
  final String side;
  final int quantity;
  final double averageEntryPrice;
  final double currentPrice;
  final double stopLoss;
  final double target;
  final double realizedPnl;
  final double unrealizedPnl;
  final double returnPct;
  final String status;
  final String entryTime;

  PositionItem({
    required this.id,
    required this.symbol,
    required this.side,
    required this.quantity,
    required this.averageEntryPrice,
    required this.currentPrice,
    required this.stopLoss,
    required this.target,
    required this.realizedPnl,
    required this.unrealizedPnl,
    required this.returnPct,
    required this.status,
    required this.entryTime,
  });

  factory PositionItem.fromJson(Map<String, dynamic> json) {
    final entryP = (json['average_entry_price'] as num?)?.toDouble() ?? 0.0;
    final currentP = (json['current_price'] as num?)?.toDouble() ?? entryP;
    final qty = (json['quantity'] as num?)?.toInt() ?? 0;
    final unrealized = (json['unrealized_pnl'] as num?)?.toDouble() ??
        ((currentP - entryP) * qty);
    final invested = entryP * qty;
    final retPct = invested > 0 ? (unrealized / invested) * 100 : 0.0;

    return PositionItem(
      id: json['id'] as int? ?? 0,
      symbol: json['symbol'] as String? ?? '',
      side: json['side'] as String? ?? 'LONG',
      quantity: qty,
      averageEntryPrice: entryP,
      currentPrice: currentP,
      stopLoss: (json['stop_loss'] as num?)?.toDouble() ?? 0.0,
      target: (json['target'] as num?)?.toDouble() ?? 0.0,
      realizedPnl: (json['realized_pnl'] as num?)?.toDouble() ?? 0.0,
      unrealizedPnl: unrealized,
      returnPct: retPct,
      status: json['status'] as String? ?? 'OPEN',
      entryTime: json['entry_time'] as String? ?? '',
    );
  }
}

class PaperOrderItem {
  final int id;
  final String symbol;
  final String transactionType;
  final int quantity;
  final double requestedPrice;
  final double? executedPrice;
  final String status;
  final String orderType;
  final String? rejectionReason;
  final String createdAt;

  PaperOrderItem({
    required this.id,
    required this.symbol,
    required this.transactionType,
    required this.quantity,
    required this.requestedPrice,
    this.executedPrice,
    required this.status,
    required this.orderType,
    this.rejectionReason,
    required this.createdAt,
  });

  factory PaperOrderItem.fromJson(Map<String, dynamic> json) {
    return PaperOrderItem(
      id: json['id'] as int? ?? 0,
      symbol: json['symbol'] as String? ?? '',
      transactionType: json['transaction_type'] as String? ?? 'BUY',
      quantity: json['quantity'] as int? ?? 0,
      requestedPrice: (json['requested_price'] as num?)?.toDouble() ?? 0.0,
      executedPrice: (json['executed_price'] as num?)?.toDouble(),
      status: json['status'] as String? ?? 'PENDING',
      orderType: json['order_type'] as String? ?? 'MARKET',
      rejectionReason: json['rejection_reason'] as String?,
      createdAt: json['created_at'] as String? ?? '',
    );
  }
}

class TradeLogItem {
  final int id;
  final String symbol;
  final String action;
  final int quantity;
  final double price;
  final double? pnl;
  final String logTimestamp;
  final bool isPaper;

  TradeLogItem({
    required this.id,
    required this.symbol,
    required this.action,
    required this.quantity,
    required this.price,
    this.pnl,
    required this.logTimestamp,
    this.isPaper = true,
  });

  factory TradeLogItem.fromJson(Map<String, dynamic> json) {
    return TradeLogItem(
      id: json['id'] as int? ?? 0,
      symbol: json['symbol'] as String? ?? '',
      action: json['action'] as String? ?? '',
      quantity: json['quantity'] as int? ?? 0,
      price: (json['price'] as num?)?.toDouble() ?? 0.0,
      pnl: (json['pnl'] as num?)?.toDouble(),
      logTimestamp: json['log_timestamp'] as String? ?? '',
      isPaper: json['is_paper'] as bool? ?? true,
    );
  }
}

class SignalItem {
  final int id;
  final String symbol;
  final String strategyName;
  final String signalType;
  final double triggerPrice;
  final double stopLoss;
  final double targetPrice;
  final String status;
  final String? rejectionReason;
  final String generatedAt;

  SignalItem({
    required this.id,
    required this.symbol,
    required this.strategyName,
    required this.signalType,
    required this.triggerPrice,
    required this.stopLoss,
    required this.targetPrice,
    required this.status,
    this.rejectionReason,
    required this.generatedAt,
  });

  factory SignalItem.fromJson(Map<String, dynamic> json) {
    return SignalItem(
      id: json['id'] as int? ?? 0,
      symbol: json['symbol'] as String? ?? '',
      strategyName: json['strategy_name'] as String? ?? 'ORB_STRATEGY',
      signalType: json['signal_type'] as String? ?? 'BUY',
      triggerPrice: (json['trigger_price'] as num?)?.toDouble() ?? 0.0,
      stopLoss: (json['stop_loss'] as num?)?.toDouble() ?? 0.0,
      targetPrice: (json['target_price'] as num?)?.toDouble() ?? 0.0,
      status: json['status'] as String? ?? 'PENDING',
      rejectionReason: json['rejection_reason'] as String?,
      generatedAt: json['generated_at'] as String? ?? '',
    );
  }
}

class SystemLogItem {
  final int id;
  final String level;
  final String module;
  final String message;
  final String? details;
  final String loggedAt;

  SystemLogItem({
    required this.id,
    required this.level,
    required this.module,
    required this.message,
    this.details,
    required this.loggedAt,
  });

  factory SystemLogItem.fromJson(Map<String, dynamic> json) {
    return SystemLogItem(
      id: json['id'] as int? ?? 0,
      level: json['level'] as String? ?? 'INFO',
      module: json['module'] as String? ?? '',
      message: json['message'] as String? ?? '',
      details: json['details'] as String?,
      loggedAt: json['logged_at'] as String? ?? '',
    );
  }
}

class RiskStatus {
  final bool circuitBreakerActive;
  final double maxDailyLoss;
  final double currentDailyPnl;
  final double dailyLossUtilizationPct;
  final int tradesToday;
  final int maxTradesPerDay;
  final int tradesRemaining;
  final int eventsToday;
  final int maxEventsPerDay;
  final int openPositionsCount;
  final int maxOpenPositions;
  final double plannedOpenRisk;
  final double cashReservePreserved;

  RiskStatus({
    required this.circuitBreakerActive,
    required this.maxDailyLoss,
    required this.currentDailyPnl,
    required this.dailyLossUtilizationPct,
    required this.tradesToday,
    required this.maxTradesPerDay,
    required this.tradesRemaining,
    required this.eventsToday,
    this.maxEventsPerDay = 6,
    this.openPositionsCount = 0,
    this.maxOpenPositions = 3,
    this.plannedOpenRisk = 0.0,
    this.cashReservePreserved = 500.0,
  });

  factory RiskStatus.fromJson(Map<String, dynamic> json) {
    return RiskStatus(
      circuitBreakerActive: json['circuit_breaker_active'] as bool? ?? false,
      maxDailyLoss: (json['max_daily_loss'] as num?)?.toDouble() ?? 75.0,
      currentDailyPnl: (json['current_daily_pnl'] as num?)?.toDouble() ?? 0.0,
      dailyLossUtilizationPct: (json['daily_loss_utilization_pct'] as num?)?.toDouble() ?? 0.0,
      tradesToday: json['trades_today'] as int? ?? 0,
      maxTradesPerDay: json['max_trades_per_day'] as int? ?? 3,
      tradesRemaining: json['trades_remaining'] as int? ?? 3,
      eventsToday: json['events_today'] as int? ?? 0,
      maxEventsPerDay: json['max_events_per_day'] as int? ?? 6,
      openPositionsCount: json['open_positions_count'] as int? ?? 0,
      maxOpenPositions: json['max_open_positions'] as int? ?? 3,
      plannedOpenRisk: (json['planned_open_risk'] as num?)?.toDouble() ?? 0.0,
      cashReservePreserved: (json['cash_reserve_preserved'] as num?)?.toDouble() ?? 500.0,
    );
  }
}

class BacktestRunSummary {
  final int id;
  final String strategyName;
  final String startDate;
  final String endDate;
  final double initialCapital;
  final double finalCapital;
  final int totalTrades;
  final double winRate;
  final double? profitFactor;
  final double? maxDrawdownPct;
  final String status;
  final String createdAt;

  BacktestRunSummary({
    required this.id,
    required this.strategyName,
    required this.startDate,
    required this.endDate,
    required this.initialCapital,
    required this.finalCapital,
    required this.totalTrades,
    required this.winRate,
    this.profitFactor,
    this.maxDrawdownPct,
    required this.status,
    required this.createdAt,
  });

  factory BacktestRunSummary.fromJson(Map<String, dynamic> json) {
    return BacktestRunSummary(
      id: json['id'] as int? ?? 0,
      strategyName: json['strategy_name'] as String? ?? 'ORB_STRATEGY',
      startDate: json['start_date'] as String? ?? '',
      endDate: json['end_date'] as String? ?? '',
      initialCapital: (json['initial_capital'] as num?)?.toDouble() ?? 5000.0,
      finalCapital: (json['final_capital'] as num?)?.toDouble() ?? 5000.0,
      totalTrades: json['total_trades'] as int? ?? 0,
      winRate: (json['win_rate'] as num?)?.toDouble() ?? 0.0,
      profitFactor: (json['profit_factor'] as num?)?.toDouble(),
      maxDrawdownPct: (json['max_drawdown_pct'] as num?)?.toDouble(),
      status: json['status'] as String? ?? 'COMPLETED',
      createdAt: json['created_at'] as String? ?? '',
    );
  }
}

class BacktestTradeItem {
  final int? id;
  final String symbol;
  final String entryTime;
  final String exitTime;
  final String side;
  final int quantity;
  final double entryPrice;
  final double exitPrice;
  final double grossPnl;
  final double totalCharges;
  final double slippageCost;
  final double netPnl;
  final double returnPct;
  final String? exitReason;

  BacktestTradeItem({
    this.id,
    required this.symbol,
    required this.entryTime,
    required this.exitTime,
    required this.side,
    required this.quantity,
    required this.entryPrice,
    required this.exitPrice,
    required this.grossPnl,
    required this.totalCharges,
    required this.slippageCost,
    required this.netPnl,
    required this.returnPct,
    this.exitReason,
  });

  factory BacktestTradeItem.fromJson(Map<String, dynamic> json) {
    return BacktestTradeItem(
      id: json['id'] as int?,
      symbol: json['symbol'] as String? ?? '',
      entryTime: json['entry_time'] as String? ?? '',
      exitTime: json['exit_time'] as String? ?? '',
      side: json['side'] as String? ?? 'LONG',
      quantity: json['quantity'] as int? ?? 0,
      entryPrice: (json['entry_price'] as num?)?.toDouble() ?? 0.0,
      exitPrice: (json['exit_price'] as num?)?.toDouble() ?? 0.0,
      grossPnl: (json['gross_pnl'] as num?)?.toDouble() ?? 0.0,
      totalCharges: (json['total_charges'] as num?)?.toDouble() ?? 0.0,
      slippageCost: (json['slippage_cost'] as num?)?.toDouble() ?? 0.0,
      netPnl: (json['net_pnl'] as num?)?.toDouble() ?? 0.0,
      returnPct: (json['return_pct'] as num?)?.toDouble() ?? 0.0,
      exitReason: json['exit_reason'] as String?,
    );
  }
}

class BacktestRunDetail extends BacktestRunSummary {
  final double netPnl;
  final double returnPct;
  final double grossProfit;
  final double grossLoss;
  final double totalCharges;
  final double totalSlippage;
  final double averageWin;
  final double averageLoss;
  final double payoffRatio;
  final double expectancy;
  final double maxDrawdownAmount;
  final double largestWin;
  final double largestLoss;
  final int maxConsecutiveWins;
  final int maxConsecutiveLosses;
  final List<BacktestTradeItem> trades;

  BacktestRunDetail({
    required super.id,
    required super.strategyName,
    required super.startDate,
    required super.endDate,
    required super.initialCapital,
    required super.finalCapital,
    required super.totalTrades,
    required super.winRate,
    super.profitFactor,
    super.maxDrawdownPct,
    required super.status,
    required super.createdAt,
    required this.netPnl,
    required this.returnPct,
    required this.grossProfit,
    required this.grossLoss,
    required this.totalCharges,
    required this.totalSlippage,
    required this.averageWin,
    required this.averageLoss,
    required this.payoffRatio,
    required this.expectancy,
    required this.maxDrawdownAmount,
    required this.largestWin,
    required this.largestLoss,
    required this.maxConsecutiveWins,
    required this.maxConsecutiveLosses,
    required this.trades,
  });

  factory BacktestRunDetail.fromJson(Map<String, dynamic> json) {
    final tradesJson = json['trades'] as List<dynamic>? ?? [];
    return BacktestRunDetail(
      id: json['id'] as int? ?? 0,
      strategyName: json['strategy_name'] as String? ?? 'ORB_STRATEGY',
      startDate: json['start_date'] as String? ?? '',
      endDate: json['end_date'] as String? ?? '',
      initialCapital: (json['initial_capital'] as num?)?.toDouble() ?? 5000.0,
      finalCapital: (json['final_capital'] as num?)?.toDouble() ?? 5000.0,
      totalTrades: json['total_trades'] as int? ?? 0,
      winRate: (json['win_rate'] as num?)?.toDouble() ?? 0.0,
      profitFactor: (json['profit_factor'] as num?)?.toDouble(),
      maxDrawdownPct: (json['max_drawdown_pct'] as num?)?.toDouble(),
      status: json['status'] as String? ?? 'COMPLETED',
      createdAt: json['created_at'] as String? ?? '',
      netPnl: (json['net_pnl'] as num?)?.toDouble() ?? 0.0,
      returnPct: (json['return_pct'] as num?)?.toDouble() ?? 0.0,
      grossProfit: (json['gross_profit'] as num?)?.toDouble() ?? 0.0,
      grossLoss: (json['gross_loss'] as num?)?.toDouble() ?? 0.0,
      totalCharges: (json['total_charges'] as num?)?.toDouble() ?? 0.0,
      totalSlippage: (json['total_slippage'] as num?)?.toDouble() ?? 0.0,
      averageWin: (json['average_win'] as num?)?.toDouble() ?? 0.0,
      averageLoss: (json['average_loss'] as num?)?.toDouble() ?? 0.0,
      payoffRatio: (json['payoff_ratio'] as num?)?.toDouble() ?? 0.0,
      expectancy: (json['expectancy'] as num?)?.toDouble() ?? 0.0,
      maxDrawdownAmount: (json['max_drawdown_amount'] as num?)?.toDouble() ?? 0.0,
      largestWin: (json['largest_win'] as num?)?.toDouble() ?? 0.0,
      largestLoss: (json['largest_loss'] as num?)?.toDouble() ?? 0.0,
      maxConsecutiveWins: json['max_consecutive_wins'] as int? ?? 0,
      maxConsecutiveLosses: json['max_consecutive_losses'] as int? ?? 0,
      trades: tradesJson.map((t) => BacktestTradeItem.fromJson(t as Map<String, dynamic>)).toList(),
    );
  }
}
