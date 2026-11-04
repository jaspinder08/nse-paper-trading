import 'package:flutter/material.dart';
import 'core/constants/app_constants.dart';
import 'core/theme/app_theme.dart';
import 'features/backtesting/backtesting_screen.dart';
import 'features/dashboard/dashboard_screen.dart';
import 'features/portfolio/portfolio_screen.dart';
import 'features/risk/risk_screen.dart';
import 'features/scanner/scanner_screen.dart';
import 'features/settings/settings_screen.dart';
import 'features/trades/trades_screen.dart';
import 'shared/components/terminal_header.dart';

void main() {
  runApp(const NSEPaperTradingApp());
}

class NSEPaperTradingApp extends StatefulWidget {
  const NSEPaperTradingApp({super.key});

  @override
  State<NSEPaperTradingApp> createState() => _NSEPaperTradingAppState();
}

class _NSEPaperTradingAppState extends State<NSEPaperTradingApp> {
  ThemeMode _themeMode = ThemeMode.dark;

  void _toggleTheme() {
    setState(() {
      _themeMode =
          _themeMode == ThemeMode.dark ? ThemeMode.light : ThemeMode.dark;
    });
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: AppConstants.appTitle,
      debugShowCheckedModeBanner: false,
      theme: AppTheme.lightTheme,
      darkTheme: AppTheme.darkTheme,
      themeMode: _themeMode,
      home: MainNavigationShell(
        onToggleTheme: _toggleTheme,
        isDarkMode: _themeMode == ThemeMode.dark,
      ),
    );
  }
}

class MainNavigationShell extends StatefulWidget {
  final VoidCallback onToggleTheme;
  final bool isDarkMode;

  const MainNavigationShell({
    super.key,
    required this.onToggleTheme,
    required this.isDarkMode,
  });

  @override
  State<MainNavigationShell> createState() => _MainNavigationShellState();
}

class _MainNavigationShellState extends State<MainNavigationShell> {
  int _selectedIndex = 0;

  @override
  Widget build(BuildContext context) {
    final screens = [
      const DashboardScreen(),
      const ScannerScreen(),
      const PortfolioScreen(),
      const TradesScreen(),
      const BacktestingScreen(),
      const RiskScreen(),
      SettingsScreen(
        onToggleTheme: widget.onToggleTheme,
        isDarkMode: widget.isDarkMode,
      ),
    ];

    final isWideScreen = MediaQuery.of(context).size.width >= 800;

    return Scaffold(
      backgroundColor: AppTheme.bgCanvas,
      body: SafeArea(
        child: Column(
          children: [
            const TerminalHeader(),
            Expanded(
              child: isWideScreen
                  ? Row(
                      children: [
                        NavigationRail(
                          backgroundColor: AppTheme.bgSurface,
                          selectedIndex: _selectedIndex,
                          onDestinationSelected: (index) {
                            setState(() {
                              _selectedIndex = index;
                            });
                          },
                          labelType: NavigationRailLabelType.all,
                          indicatorColor: AppTheme.accentCyan.withOpacity(0.15),
                          selectedIconTheme: const IconThemeData(color: AppTheme.accentCyan, size: 20),
                          unselectedIconTheme: const IconThemeData(color: AppTheme.textMuted, size: 20),
                          selectedLabelTextStyle: const TextStyle(
                            fontSize: 10,
                            fontWeight: FontWeight.w700,
                            color: AppTheme.accentCyan,
                            letterSpacing: 0.4,
                          ),
                          unselectedLabelTextStyle: const TextStyle(
                            fontSize: 10,
                            fontWeight: FontWeight.w500,
                            color: AppTheme.textMuted,
                            letterSpacing: 0.2,
                          ),
                          destinations: const [
                            NavigationRailDestination(
                              icon: Icon(Icons.dashboard_outlined),
                              selectedIcon: Icon(Icons.dashboard),
                              label: Text('Dashboard'),
                            ),
                            NavigationRailDestination(
                              icon: Icon(Icons.filter_alt_outlined),
                              selectedIcon: Icon(Icons.filter_alt),
                              label: Text('Scanner'),
                            ),
                            NavigationRailDestination(
                              icon: Icon(Icons.account_balance_wallet_outlined),
                              selectedIcon: Icon(Icons.account_balance_wallet),
                              label: Text('Portfolio'),
                            ),
                            NavigationRailDestination(
                              icon: Icon(Icons.history_outlined),
                              selectedIcon: Icon(Icons.history),
                              label: Text('Trades'),
                            ),
                            NavigationRailDestination(
                              icon: Icon(Icons.analytics_outlined),
                              selectedIcon: Icon(Icons.analytics),
                              label: Text('Backtest'),
                            ),
                            NavigationRailDestination(
                              icon: Icon(Icons.security_outlined),
                              selectedIcon: Icon(Icons.security),
                              label: Text('Risk'),
                            ),
                            NavigationRailDestination(
                              icon: Icon(Icons.settings_outlined),
                              selectedIcon: Icon(Icons.settings),
                              label: Text('Settings'),
                            ),
                          ],
                        ),
                        VerticalDivider(thickness: 1, width: 1, color: AppTheme.borderSubtle),
                        Expanded(child: screens[_selectedIndex]),
                      ],
                    )
                  : screens[_selectedIndex],
            ),
          ],
        ),
      ),
      bottomNavigationBar: isWideScreen
          ? null
          : BottomNavigationBar(
              currentIndex: _selectedIndex,
              onTap: (index) {
                setState(() {
                  _selectedIndex = index;
                });
              },
              type: BottomNavigationBarType.fixed,
              selectedItemColor: Theme.of(context).primaryColor,
              unselectedItemColor: Colors.grey,
              items: const [
                BottomNavigationBarItem(
                  icon: Icon(Icons.dashboard_outlined),
                  label: 'Dashboard',
                ),
                BottomNavigationBarItem(
                  icon: Icon(Icons.filter_alt_outlined),
                  label: 'Scanner',
                ),
                BottomNavigationBarItem(
                  icon: Icon(Icons.account_balance_wallet_outlined),
                  label: 'Portfolio',
                ),
                BottomNavigationBarItem(
                  icon: Icon(Icons.history_outlined),
                  label: 'Trades',
                ),
                BottomNavigationBarItem(
                  icon: Icon(Icons.analytics_outlined),
                  label: 'Backtest',
                ),
                BottomNavigationBarItem(
                  icon: Icon(Icons.security_outlined),
                  label: 'Risk',
                ),
                BottomNavigationBarItem(
                  icon: Icon(Icons.settings_outlined),
                  label: 'Settings',
                ),
              ],
            ),
    );
  }
}
