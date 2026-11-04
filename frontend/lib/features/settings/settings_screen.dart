import 'package:flutter/material.dart';

class SettingsScreen extends StatelessWidget {
  final VoidCallback onToggleTheme;
  final bool isDarkMode;

  const SettingsScreen({
    super.key,
    required this.onToggleTheme,
    required this.isDarkMode,
  });

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Padding(
        padding: const EdgeInsets.all(24.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Application Settings',
              style: Theme.of(context).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            Text(
              'Database connections, system appearance, and API configuration.',
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: Colors.grey),
            ),
            const SizedBox(height: 24),
            Card(
              child: ListTile(
                leading: Icon(isDarkMode ? Icons.dark_mode : Icons.light_mode),
                title: const Text('Theme Appearance'),
                subtitle: Text(isDarkMode ? 'Dark Financial Theme' : 'Light Theme'),
                trailing: Switch(
                  value: isDarkMode,
                  onChanged: (_) => onToggleTheme(),
                ),
              ),
            ),
            const SizedBox(height: 12),
            Card(
              child: ListTile(
                leading: const Icon(Icons.storage_outlined),
                title: const Text('Database Engine'),
                subtitle: const Text('SQLite 3 (WAL Mode Enabled) | Local Single-User'),
                trailing: const Chip(label: Text('Connected', style: TextStyle(color: Colors.green))),
              ),
            ),
            const SizedBox(height: 12),
            Card(
              child: ListTile(
                leading: const Icon(Icons.shield_outlined),
                title: const Text('Trading Safeguard Mode'),
                subtitle: const Text('STRICT PAPER TRADING ONLY - Broker APIs detached'),
                trailing: const Chip(label: Text('Active', style: TextStyle(color: Colors.amber))),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
