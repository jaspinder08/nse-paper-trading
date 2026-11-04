import 'package:flutter/material.dart';
import '../../core/theme/app_theme.dart';

class StatusBadge extends StatelessWidget {
  final String status;
  final double fontSize;

  const StatusBadge({
    super.key,
    required this.status,
    this.fontSize = 11,
  });

  @override
  Widget build(BuildContext context) {
    final cleanStatus = status.trim().toUpperCase();

    Color fgColor = AppTheme.textSecondary;
    Color bgColor = AppTheme.darkBorder.withValues(alpha: 0.3);

    if (cleanStatus == 'TRIGGERED' ||
        cleanStatus == 'ACTIVE' ||
        cleanStatus == 'TARGET_HIT' ||
        cleanStatus == 'PASS' ||
        cleanStatus == 'OPEN' ||
        cleanStatus == 'FILLED') {
      fgColor = AppTheme.gainGreen;
      bgColor = AppTheme.gainGreenSubtle;
    } else if (cleanStatus == 'PENDING_BREAKOUT' ||
        cleanStatus == 'PENDING' ||
        cleanStatus == 'SCHEDULED') {
      fgColor = AppTheme.warningAmber;
      bgColor = AppTheme.warningAmberSubtle;
    } else if (cleanStatus == 'RANGE_FORMING') {
      fgColor = AppTheme.accentCyan;
      bgColor = AppTheme.accentCyan.withValues(alpha: 0.15);
    } else if (cleanStatus.startsWith('REJECTED') ||
        cleanStatus.contains('CIRCUIT_BREAKER') ||
        cleanStatus.contains('STOP_LOSS') ||
        cleanStatus.contains('FAIL') ||
        cleanStatus == 'BLOCKED') {
      fgColor = AppTheme.lossRed;
      bgColor = AppTheme.lossRedSubtle;
    } else if (cleanStatus == 'EOD_SQUARE_OFF' || cleanStatus == 'CLOSED') {
      fgColor = AppTheme.textSecondary;
      bgColor = AppTheme.darkBorder;
    }

    final displayText = cleanStatus.replaceAll('_', ' ');

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
      decoration: BoxDecoration(
        color: bgColor,
        borderRadius: BorderRadius.circular(4),
        border: Border.all(color: fgColor.withValues(alpha: 0.3), width: 1),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 5,
            height: 5,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: fgColor,
            ),
          ),
          const SizedBox(width: 5),
          Text(
            displayText,
            style: TextStyle(
              color: fgColor,
              fontSize: fontSize,
              fontWeight: FontWeight.w700,
              letterSpacing: 0.3,
            ),
          ),
        ],
      ),
    );
  }
}
