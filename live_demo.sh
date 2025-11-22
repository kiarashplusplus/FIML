#!/bin/bash
# FIML Live System Demo

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║          🚀 FIML LIVE SYSTEM DEMONSTRATION 🚀                  ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Test 1: Health Check
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Test 1: System Health"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
curl -s http://localhost:8000/health | python -m json.tool
echo ""

# Test 2: List MCP Tools
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 Test 2: Available MCP Tools"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
curl -s http://localhost:8000/mcp/tools | python -c "import sys, json; data=json.load(sys.stdin); print('Available tools:'); [print(f\"  • {t['name']}: {t['description'][:60]}...\") for t in data['tools']]"
echo ""

# Test 3: Stock Query - Apple
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📈 Test 3: Real-time Stock Data (AAPL)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
curl -s -X POST http://localhost:8000/mcp/tools/call \
  -H "Content-Type: application/json" \
  -d '{"name":"search-by-symbol","arguments":{"symbol":"AAPL","market":"US","depth":"quick"}}' | \
  python -c "
import sys, json
data = json.load(sys.stdin)
if not data['isError']:
    result = json.loads(data['content'][0]['text'])
    print(f\"  Symbol: {result['symbol']}\")
    print(f\"  Price: \${result['cached']['price']}\")
    print(f\"  Change: {result['cached']['change']} ({result['cached']['change_percent']}%)\")
    print(f\"  Source: {result['cached']['source']}\")
    print(f\"  Confidence: {result['cached']['confidence']*100}%\")
else:
    print('  Error:', data['content'][0]['text'])
"
echo ""

# Test 4: Stock Query - Tesla
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚗 Test 4: Real-time Stock Data (TSLA)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
curl -s -X POST http://localhost:8000/mcp/tools/call \
  -H "Content-Type: application/json" \
  -d '{"name":"search-by-symbol","arguments":{"symbol":"TSLA","market":"US","depth":"quick"}}' | \
  python -c "
import sys, json
data = json.load(sys.stdin)
if not data['isError']:
    result = json.loads(data['content'][0]['text'])
    print(f\"  Symbol: {result['symbol']}\")
    print(f\"  Price: \${result['cached']['price']}\")
    print(f\"  Change: {result['cached']['change']} ({result['cached']['change_percent']}%)\")
    print(f\"  Source: {result['cached']['source']}\")
else:
    print('  Error:', data['content'][0]['text'])
"
echo ""

# Test 5: Crypto Query
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "₿  Test 5: Cryptocurrency Data (BTC)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
curl -s -X POST http://localhost:8000/mcp/tools/call \
  -H "Content-Type: application/json" \
  -d '{"name":"search-by-coin","arguments":{"symbol":"BTC","exchange":"binance","depth":"quick"}}' | \
  python -c "
import sys, json
data = json.load(sys.stdin)
if not data['isError']:
    result = json.loads(data['content'][0]['text'])
    print(f\"  Symbol: {result['symbol']}\")
    print(f\"  Pair: {result['pair']}\")
    print(f\"  Price: \${result['cached']['price']}\")
    print(f\"  Exchange: {result['exchange']}\")
else:
    print('  Error:', data['content'][0]['text'])
"
echo ""

# Test 6: System Stats
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 Test 6: Running Services"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
docker-compose ps --format "  {{.Service}}: {{.Status}}" | grep -E "(fiml-server|redis|postgres)" | head -3
echo ""

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                    ✅ DEMO COMPLETE ✅                          ║"
echo "╚════════════════════════════════════════════════════════════════╝"
