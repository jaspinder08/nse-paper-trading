import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/main.dart';

void main() {
  testWidgets('App initializes and renders navigation shell with paper trading banner', (WidgetTester tester) async {
    await tester.pumpWidget(const NSEPaperTradingApp());
    expect(find.text('PAPER TRADING SIMULATION ONLY'), findsOneWidget);
    expect(find.text('Intraday Dashboard'), findsOneWidget);
  });
}
