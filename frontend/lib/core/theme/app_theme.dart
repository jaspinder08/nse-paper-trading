import 'package:flutter/material.dart';

class AppTheme {
  // Institutional Trading Terminal Palette
  static const Color darkCanvas = Color(0xFF0A0E17);
  static const Color darkSurface = Color(0xFF111724);
  static const Color darkCard = Color(0xFF161F2E);
  static const Color darkCardHover = Color(0xFF1C273A);
  static const Color darkBorder = Color(0xFF1F2B3E);
  static const Color darkBorderHover = Color(0xFF2E3F5B);

  // Financial Semantics (TradingView inspired)
  static const Color accentBlue = Color(0xFF2962FF);
  static const Color accentCyan = Color(0xFF00B4D8);
  static const Color gainGreen = Color(0xFF089981);
  static const Color gainGreenSubtle = Color(0x26089981);
  static const Color lossRed = Color(0xFFF23645);
  static const Color lossRedSubtle = Color(0x26F23645);
  static const Color warningAmber = Color(0xFFF59E0B);
  static const Color warningAmberSubtle = Color(0x26F59E0B);

  // Typography Palette
  static const Color textPrimary = Color(0xFFF1F5F9);
  static const Color textSecondary = Color(0xFF94A3B8);
  static const Color textMuted = Color(0xFF64748B);

  // Light Institutional Palette
  static const Color lightCanvas = Color(0xFFF1F5F9);
  static const Color lightSurface = Color(0xFFFFFFFF);
  static const Color lightCard = Color(0xFFFFFFFF);
  static const Color lightBorder = Color(0xFFE2E8F0);

  // Semantic Theme Aliases
  static const Color bgCanvas = darkCanvas;
  static const Color bgSurface = darkSurface;
  static const Color bgCard = darkCard;
  static const Color bgCardHover = darkCardHover;
  static const Color borderSubtle = darkBorder;
  static const Color borderFocus = darkBorderHover;
  static const Color colorProfit = gainGreen;
  static const Color colorLoss = lossRed;
  static const Color accentAmber = warningAmber;

  static TextStyle get monoTextStyle => const TextStyle(
        fontFamily: 'monospace',
        fontFeatures: [FontFeature.tabularFigures()],
      );

  static TextStyle monoStyle({
    double fontSize = 12,
    FontWeight fontWeight = FontWeight.normal,
    Color? color,
    double? letterSpacing,
  }) =>
      TextStyle(
        fontFamily: 'monospace',
        fontFeatures: const [FontFeature.tabularFigures()],
        fontSize: fontSize,
        fontWeight: fontWeight,
        color: color,
        letterSpacing: letterSpacing,
      );

  static ThemeData get darkTheme {
    return ThemeData(
      brightness: Brightness.dark,
      scaffoldBackgroundColor: darkCanvas,
      primaryColor: accentBlue,
      cardColor: darkCard,
      dividerColor: darkBorder,
      colorScheme: const ColorScheme.dark(
        primary: accentBlue,
        secondary: gainGreen,
        surface: darkSurface,
        error: lossRed,
        outline: darkBorder,
      ),
      appBarTheme: const AppBarTheme(
        backgroundColor: darkSurface,
        elevation: 0,
        scrolledUnderElevation: 0,
        centerTitle: false,
        iconTheme: IconThemeData(color: textPrimary, size: 20),
        titleTextStyle: TextStyle(
          fontSize: 16,
          fontWeight: FontWeight.w700,
          color: textPrimary,
          letterSpacing: 0.3,
        ),
      ),
      navigationRailTheme: const NavigationRailThemeData(
        backgroundColor: darkSurface,
        elevation: 0,
        selectedIconTheme: IconThemeData(color: accentBlue, size: 20),
        unselectedIconTheme: IconThemeData(color: textMuted, size: 20),
        selectedLabelTextStyle: TextStyle(
          color: accentBlue,
          fontWeight: FontWeight.w700,
          fontSize: 11,
          letterSpacing: 0.3,
        ),
        unselectedLabelTextStyle: TextStyle(
          color: textSecondary,
          fontSize: 11,
          fontWeight: FontWeight.w500,
        ),
      ),
      cardTheme: CardThemeData(
        color: darkCard,
        elevation: 0,
        margin: EdgeInsets.zero,
        shape: RoundedRectangleBorder(
          side: const BorderSide(color: darkBorder, width: 1),
          borderRadius: BorderRadius.circular(8),
        ),
      ),
      chipTheme: ChipThemeData(
        backgroundColor: darkSurface,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(6),
          side: const BorderSide(color: darkBorder),
        ),
      ),
      useMaterial3: true,
    );
  }

  static ThemeData get lightTheme {
    return ThemeData(
      brightness: Brightness.light,
      scaffoldBackgroundColor: lightCanvas,
      primaryColor: const Color(0xFF1D4ED8),
      cardColor: lightCard,
      dividerColor: lightBorder,
      colorScheme: const ColorScheme.light(
        primary: Color(0xFF1D4ED8),
        secondary: Color(0xFF047857),
        surface: lightSurface,
        error: Color(0xFFDC2626),
        outline: lightBorder,
      ),
      appBarTheme: const AppBarTheme(
        backgroundColor: lightSurface,
        foregroundColor: Color(0xFF0F172A),
        elevation: 0,
        scrolledUnderElevation: 0,
        centerTitle: false,
        titleTextStyle: TextStyle(
          fontSize: 16,
          fontWeight: FontWeight.w700,
          color: Color(0xFF0F172A),
          letterSpacing: 0.3,
        ),
      ),
      navigationRailTheme: const NavigationRailThemeData(
        backgroundColor: lightSurface,
        elevation: 0,
        selectedIconTheme: IconThemeData(color: Color(0xFF1D4ED8), size: 20),
        unselectedIconTheme: IconThemeData(color: Color(0xFF64748B), size: 20),
        selectedLabelTextStyle: TextStyle(
          color: Color(0xFF1D4ED8),
          fontWeight: FontWeight.w700,
          fontSize: 11,
        ),
        unselectedLabelTextStyle: TextStyle(
          color: Color(0xFF64748B),
          fontSize: 11,
          fontWeight: FontWeight.w500,
        ),
      ),
      cardTheme: CardThemeData(
        color: lightCard,
        elevation: 0,
        margin: EdgeInsets.zero,
        shape: RoundedRectangleBorder(
          side: const BorderSide(color: lightBorder, width: 1),
          borderRadius: BorderRadius.circular(8),
        ),
      ),
      useMaterial3: true,
    );
  }
}
