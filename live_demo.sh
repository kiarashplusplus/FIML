#!/bin/bash
# FIML Live System Demo
# Comprehensive demonstration of FIML capabilities with live data
#
# Usage:
#   ./live_demo.sh             # Run full demo
#   ./live_demo.sh --quick     # Run quick demo (skip slow operations)
#   ./live_demo.sh --verbose   # Run with verbose output (show raw JSON)
#   ./live_demo.sh --help      # Show help message
#

set -e

# =============================================================================
# Configuration & Color Variables
# =============================================================================
BASE_URL="${FIML_BASE_URL:-http://localhost:8000}"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
GRAY='\033[0;90m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m' # No Color

# Parse command-line arguments
QUICK_MODE=false
VERBOSE_MODE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --quick|-q)
            QUICK_MODE=true
            shift
            ;;
        --verbose|-v)
            VERBOSE_MODE=true
            shift
            ;;
        --help|-h)
            echo "FIML Live System Demo"
            echo ""
            echo "Usage: ./live_demo.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --quick, -q     Run quick demo (skip slow operations)"
            echo "  --verbose, -v   Show raw JSON responses"
            echo "  --help, -h      Show this help message"
            echo ""
            echo "Environment Variables:"
            echo "  FIML_BASE_URL   Base URL for FIML server (default: http://localhost:8000)"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Timing variables
DEMO_START_TIME=$(date +%s.%N)
declare -A SECTION_TIMES

# Session tracking
SESSION_ID=""

# =============================================================================
# Helper Functions
# =============================================================================

# Print section header
print_section() {
    local title="$1"
    local icon="${2:-📌}"
    echo ""
    echo -e "${BOLD}${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}${icon} ${WHITE}${title}${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

# Print subsection header
print_subsection() {
    local title="$1"
    local icon="${2:-▸}"
    echo ""
    echo -e "${BOLD}${BLUE}${icon} ${title}${NC}"
    echo -e "${GRAY}────────────────────────────────────────────────────────────${NC}"
}

# Print success message
print_success() {
    echo -e "  ${GREEN}✓${NC} $1"
}

# Print error message
print_error() {
    echo -e "  ${RED}✗${NC} $1"
}

# Print warning message
print_warning() {
    echo -e "  ${YELLOW}⚠${NC} $1"
}

# Print info message
print_info() {
    echo -e "  ${BLUE}ℹ${NC} $1"
}

# Print data value
print_value() {
    local label="$1"
    local value="$2"
    local color="${3:-$WHITE}"
    printf "  ${GRAY}%-20s${NC} ${color}%s${NC}\n" "$label:" "$value"
}

# Pretty print JSON
pretty_json() {
    if command -v python3 &> /dev/null; then
        python3 -m json.tool 2>/dev/null || cat
    elif command -v python &> /dev/null; then
        python -m json.tool 2>/dev/null || cat
    elif command -v jq &> /dev/null; then
        jq . 2>/dev/null || cat
    else
        cat
    fi
}

# Call MCP tool and return result
call_mcp_tool() {
    local tool_name="$1"
    local arguments="$2"
    local result

    result=$(curl -s -X POST "${BASE_URL}/mcp/tools/call" \
        -H "Content-Type: application/json" \
        -d "{\"name\":\"${tool_name}\",\"arguments\":${arguments}}" 2>/dev/null)

    if [ "$VERBOSE_MODE" = true ]; then
        echo "$result" | pretty_json
    fi

    echo "$result"
}

# Make HTTP GET request
http_get() {
    local endpoint="$1"
    local result

    result=$(curl -s "${BASE_URL}${endpoint}" 2>/dev/null)

    if [ "$VERBOSE_MODE" = true ]; then
        echo "$result" | pretty_json
    fi

    echo "$result"
}

# Calculate duration using awk for portability (bc may not be available)
calc_duration() {
    local start="$1"
    local end="$2"
    awk -v s="$start" -v e="$end" 'BEGIN {printf "%.2f", e - s}' 2>/dev/null || echo "N/A"
}

# Start timing a section
start_timing() {
    local section_name="$1"
    SECTION_TIMES["${section_name}_start"]=$(date +%s.%N)
}

# End timing and print duration
end_timing() {
    local section_name="$1"
    local end_time=$(date +%s.%N)
    local start_time="${SECTION_TIMES[${section_name}_start]}"
    local duration
    duration=$(calc_duration "$start_time" "$end_time")
    echo -e "  ${DIM}⏱  Completed in ${duration}s${NC}"
}

# Check if server is running
check_server() {
    if ! curl -s --connect-timeout 5 "${BASE_URL}/health" > /dev/null 2>&1; then
        echo -e "${RED}Error: FIML server is not running at ${BASE_URL}${NC}"
        echo -e "Please start the server with: ${YELLOW}make up${NC}"
        exit 1
    fi
}

# =============================================================================
# Demo Header
# =============================================================================

echo ""
echo -e "${BOLD}${WHITE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${WHITE}║          🚀 ${CYAN}FIML LIVE SYSTEM DEMONSTRATION${WHITE} 🚀                  ║${NC}"
echo -e "${BOLD}${WHITE}║                                                                ║${NC}"
echo -e "${BOLD}${WHITE}║  ${DIM}Financial Intelligence Meta-Layer v0.2.2${WHITE}                     ║${NC}"
if [ "$QUICK_MODE" = true ]; then
echo -e "${BOLD}${WHITE}║  ${YELLOW}Running in QUICK mode${WHITE}                                        ║${NC}"
fi
if [ "$VERBOSE_MODE" = true ]; then
echo -e "${BOLD}${WHITE}║  ${MAGENTA}Running in VERBOSE mode${WHITE}                                      ║${NC}"
fi
echo -e "${BOLD}${WHITE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check server availability
check_server

# =============================================================================
# SECTION 1: Enhanced System & Provider Health
# =============================================================================
print_section "SECTION 1: System & Provider Health" "🏥"
start_timing "section1"

print_subsection "System Health Check" "💚"
health_response=$(http_get "/health")
echo "$health_response" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(f\"  Status:      \033[32m{data.get('status', 'unknown').upper()}\033[0m\")
    print(f\"  Version:     {data.get('version', 'N/A')}\")
    print(f\"  Environment: {data.get('environment', 'N/A')}\")
except Exception as e:
    print(f\"  \033[31mError parsing response: {e}\033[0m\")
"

print_subsection "Database Health" "🗄️"
db_health=$(http_get "/health/db")
echo "$db_health" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    status = data.get('status', 'unknown')
    color = '\033[32m' if status == 'healthy' else '\033[31m'
    print(f\"  Status:   {color}{status.upper()}\033[0m\")
    print(f\"  Service:  {data.get('service', 'N/A')}\")
    print(f\"  Host:     {data.get('host', 'N/A')}:{data.get('port', 'N/A')}\")
    print(f\"  Database: {data.get('database', 'N/A')}\")
except Exception as e:
    print(f\"  \033[33mDatabase not available or response error\033[0m\")
"

print_subsection "Cache Health (Redis)" "📦"
cache_health=$(http_get "/health/cache")
echo "$cache_health" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    status = data.get('status', 'unknown')
    color = '\033[32m' if status == 'healthy' else '\033[31m'
    print(f\"  Status:  {color}{status.upper()}\033[0m\")
    print(f\"  Service: {data.get('service', 'N/A')}\")
    print(f\"  Host:    {data.get('host', 'N/A')}:{data.get('port', 'N/A')}\")
except Exception as e:
    print(f\"  \033[33mCache not available or response error\033[0m\")
"

print_subsection "Provider Health Status" "🔌"
providers_health=$(http_get "/health/providers")
echo "$providers_health" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    status = data.get('status', 'unknown')
    color = '\033[32m' if status == 'healthy' else '\033[33m' if status == 'degraded' else '\033[31m'
    print(f\"  Overall Status: {color}{status.upper()}\033[0m\")
    print(f\"  Total Providers:   {data.get('total_providers', 0)}\")
    print(f\"  Healthy Providers: \033[32m{data.get('healthy_providers', 0)}\033[0m\")
    print()
    providers = data.get('providers', {})
    if providers:
        print(\"  Provider Details:\")
        for name, info in list(providers.items())[:5]:  # Show first 5
            status_icon = '\033[32m●\033[0m' if info.get('is_healthy') else '\033[31m●\033[0m'
            latency = info.get('avg_latency_ms', 0)
            success = info.get('success_rate', 0) * 100
            print(f\"    {status_icon} {name:<15} Latency: {latency:>6.0f}ms  Success: {success:.1f}%\")
except Exception as e:
    print(f\"  \033[33mProvider health not available\033[0m\")
"

print_subsection "Cache Analytics" "📊"
cache_metrics=$(http_get "/api/metrics/cache")
echo "$cache_metrics" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    l1 = data.get('l1_cache', {})
    l2 = data.get('l2_cache', {})
    print(\"  L1 Cache (Redis):\")
    print(f\"    Hit Rate:     {l1.get('hit_rate', 0) * 100:.1f}%\")
    print(f\"    Avg Latency:  {l1.get('avg_latency_ms', 0):.2f}ms\")
    print(f\"    Total Hits:   {l1.get('hits', 0)}\")
    print(f\"    Total Misses: {l1.get('misses', 0)}\")
    print()
    print(\"  L2 Cache (PostgreSQL):\")
    print(f\"    Hit Rate:     {l2.get('hit_rate', 0) * 100:.1f}%\")
    print(f\"    Avg Latency:  {l2.get('avg_latency_ms', 0):.2f}ms\")
except Exception as e:
    print(f\"  \033[33mCache analytics not available\033[0m\")
"

end_timing "section1"

# =============================================================================
# SECTION 2: Basic Queries with Narratives
# =============================================================================
print_section "SECTION 2: Basic Queries with Narratives" "📈"
start_timing "section2"

print_subsection "Stock Query with Narrative (AAPL - Standard Depth)" "🍎"
aapl_response=$(call_mcp_tool "search-by-symbol" '{"symbol":"AAPL","market":"US","depth":"standard"}')
echo "$aapl_response" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if not data.get('isError', False):
        result = json.loads(data['content'][0]['text'])
        cached = result.get('cached', {})
        print(f\"  Symbol:          \033[1m{result.get('symbol', 'N/A')}\033[0m\")
        print(f\"  Market:          {result.get('market', 'N/A')}\")
        print(f\"  Price:           \033[32m\${cached.get('price', 'N/A')}\033[0m\")
        change = cached.get('change', 0)
        change_pct = cached.get('change_percent', 0)
        color = '\033[32m' if change >= 0 else '\033[31m'
        sign = '+' if change >= 0 else ''
        print(f\"  Change:          {color}{sign}{change} ({sign}{change_pct}%)\033[0m\")
        print(f\"  Source:          {cached.get('source', 'N/A')}\")
        print(f\"  Confidence:      {cached.get('confidence', 0) * 100:.0f}%\")
        print(f\"  Analysis Depth:  {result.get('depth', 'N/A')}\")

        narrative = result.get('narrative', {})
        if narrative:
            print()
            print(\"  Narrative Summary:\")
            summary = narrative.get('summary', 'N/A')[:200]
            print(f\"    {summary}...\" if len(summary) >= 200 else f\"    {summary}\")
    else:
        print(f\"  \033[31mError: {data['content'][0]['text']}\033[0m\")
except Exception as e:
    print(f\"  \033[33mQuery error or server not available: {e}\033[0m\")
"

print_subsection "Cryptocurrency Query with Metrics (BTC)" "₿"
btc_response=$(call_mcp_tool "search-by-coin" '{"symbol":"BTC","exchange":"binance","depth":"standard"}')
echo "$btc_response" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if not data.get('isError', False):
        result = json.loads(data['content'][0]['text'])
        cached = result.get('cached', {})
        print(f\"  Symbol:   \033[1m{result.get('symbol', 'N/A')}\033[0m\")
        print(f\"  Pair:     {result.get('pair', 'N/A')}\")
        print(f\"  Exchange: {result.get('exchange', 'N/A')}\")
        price = cached.get('price', 'N/A')
        if isinstance(price, (int, float)):
            print(f\"  Price:    \033[33m\${price:,.2f}\033[0m\")
        else:
            print(f\"  Price:    \${price}\")
        change = cached.get('change', 0)
        change_pct = cached.get('change_percent', 0)
        color = '\033[32m' if change >= 0 else '\033[31m'
        sign = '+' if change >= 0 else ''
        print(f\"  Change:   {color}{sign}{change_pct}%\033[0m\")
        print(f\"  Source:   {cached.get('source', 'N/A')}\")
    else:
        print(f\"  \033[31mError: {data['content'][0]['text']}\033[0m\")
except Exception as e:
    print(f\"  \033[33mQuery error: {e}\033[0m\")
"

if [ "$QUICK_MODE" != true ]; then
    print_subsection "Multi-Depth Comparison Demo" "📊"
    echo -e "  ${DIM}Comparing analysis depths for TSLA...${NC}"

    # Quick depth
    echo -e "\n  ${BOLD}Quick Depth:${NC}"
    tsla_quick=$(call_mcp_tool "search-by-symbol" '{"symbol":"TSLA","market":"US","depth":"quick"}')
    echo "$tsla_quick" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if not data.get('isError', False):
        result = json.loads(data['content'][0]['text'])
        cached = result.get('cached', {})
        print(f\"    Price: \${cached.get('price', 'N/A')}\")
        print(f\"    Fields: Basic price data only\")
except:
    print(\"    Query failed\")
"

    # Standard depth
    echo -e "\n  ${BOLD}Standard Depth:${NC}"
    tsla_standard=$(call_mcp_tool "search-by-symbol" '{"symbol":"TSLA","market":"US","depth":"standard"}')
    echo "$tsla_standard" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if not data.get('isError', False):
        result = json.loads(data['content'][0]['text'])
        cached = result.get('cached', {})
        structural = result.get('structural_data') or {}
        
        print(f\"    Price:      \${cached.get('price', 'N/A')}\")
        if structural:
            mcap = structural.get('market_cap')
            pe = structural.get('pe_ratio')
            print(f\"    Market Cap: \${mcap:,.0f}\" if mcap else \"    Market Cap: N/A\")
            print(f\"    PE Ratio:   {pe:.2f}\" if pe else \"    PE Ratio:   N/A\")
            
        print(f\"    Fields:     Price + Fundamentals + Technicals + Basic narrative\")
        narrative = result.get('narrative')
        sections = narrative.get('sections', []) if narrative else []
        if narrative:
            if len(sections) > 0:
                print(f\"    Narrative:  Yes\")
            else:
                summary = narrative.get('summary', '')
                if \"ERROR\" in summary:
                    print(f\"    Narrative:  Error: {summary}\")
                else:
                    print(f\"    Narrative:  No (LLM not configured)\")
        else:
            disclaimer = result.get('disclaimer', '')
            if \"DEBUG ERROR\" in disclaimer:
                print(f\"    Narrative:  Error: {disclaimer}\")
            else:
                print(f\"    Narrative:  No (LLM not configured)\")
except:
    print(\"    Query failed\")
"

    # Deep depth
    echo -e "\n  ${BOLD}Deep Depth:${NC}"
    tsla_deep=$(call_mcp_tool "search-by-symbol" '{"symbol":"TSLA","market":"US","depth":"deep"}')
    echo "$tsla_deep" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if not data.get('isError', False):
        result = json.loads(data['content'][0]['text'])
        cached = result.get('cached', {})
        structural = result.get('structural_data') or {}
        
        print(f\"    Price:      \${cached.get('price', 'N/A')}\")
        if structural:
            print(f\"    Sector:     {structural.get('sector', 'N/A')}\")
            print(f\"    Beta:       {structural.get('beta', 'N/A')}\")
            
        print(f\"    Fields:     Full analysis + Deep Fundamentals + Sentiment + Comprehensive narrative\")
        
        narrative = result.get('narrative')
        sections = narrative.get('sections', []) if narrative else []
        
        if narrative:
            if len(sections) > 0:
                print(f\"    Narrative:  Yes ({len(sections)} sections)\")
                summary = narrative.get('summary', 'N/A')
                print(f\"    Summary:    {summary[:100]}...\")
            else:
                summary = narrative.get('summary', '')
                if \"ERROR\" in summary:
                    print(f\"    Narrative:  Error: {summary}\")
                else:
                    print(f\"    Narrative:  No (LLM not configured)\")
        else:
             disclaimer = result.get('disclaimer', '')
             if \"DEBUG ERROR\" in disclaimer:
                 print(f\"    Narrative:  Error: {disclaimer}\")
             else:
                 print(f\"    Narrative:  No (LLM not configured)\")
except Exception as e:
    print(f\"    Query failed: {e}\")
"
fi

end_timing "section2"

# =============================================================================
# SECTION 3: FK-DSL Demonstrations
# =============================================================================
print_section "SECTION 3: FK-DSL Query Language" "🔮"
start_timing "section3"

print_subsection "Simple EVALUATE Query" "▶️"
echo -e "  ${DIM}Query: EVALUATE AAPL: PRICE, VOLUME${NC}"
dsl_simple=$(call_mcp_tool "execute-fk-dsl" '{"query":"EVALUATE AAPL: PRICE, VOLUME","async":false}')
echo "$dsl_simple" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if not data.get('isError', False):
        result = json.loads(data['content'][0]['text'])
        status = result.get('status', 'unknown')
        color = '\033[32m' if status == 'completed' else '\033[33m'
        print(f\"  Status: {color}{status}\033[0m\")
        
        # Check for synchronous execution results
        if 'result' in result and result['result']:
            exec_result = result['result']
            print()
            print('  \033[1mExecution Results:\033[0m')
            
            # Handle different result formats
            if isinstance(exec_result, dict):
                # Check for price data
                if 'price' in exec_result or 'PRICE' in exec_result:
                    price_data = exec_result.get('price') or exec_result.get('PRICE', {})
                    if isinstance(price_data, dict):
                        print(f\"    Price:    \033[32m\${price_data.get('price', 'N/A')}\033[0m\")
                        change = price_data.get('change_percent', 0)
                        color = '\033[32m' if change >= 0 else '\033[31m'
                        print(f\"    Change:   {color}{change:+.2f}%\033[0m\")
                        print(f\"    Volume:   {price_data.get('volume', 'N/A'):,}\")
                    else:
                        print(f\"    Price: {price_data}\")
                        
                # Check for volume data
                if 'volume' in exec_result or 'VOLUME' in exec_result:
                    vol_data = exec_result.get('volume') or exec_result.get('VOLUME', {})
                    if isinstance(vol_data, dict) and 'volume' in vol_data:
                        print(f\"    Volume:   {vol_data.get('volume', 'N/A'):,}\")
                        
                # Show any other top-level metrics
                for key, value in list(exec_result.items())[:5]:
                    if key.lower() not in ['price', 'volume']:
                        if isinstance(value, dict):
                            print(f\"    {key}: {json.dumps(value, default=str)[:60]}...\")
                        else:
                            print(f\"    {key}: {value}\")
            else:
                print(f\"    Result: {exec_result}\")
                
        # Fallback to results field (async mode)
        elif 'results' in result:
            results = result['results']
            if isinstance(results, dict):
                for key, value in list(results.items())[:3]:
                    print(f\"  {key}: {value}\")
        elif 'task_id' in result:
            print(f\"  Task ID: {result['task_id']}\")
            print(f\"  Total Steps: {result.get('total_steps', 'N/A')}\")
    else:
        print(f\"  \033[33mDSL execution returned error - this is expected in demo mode\033[0m\")
except Exception as e:
    print(f\"  \033[33mDSL query demonstration (mock data in demo mode): {e}\033[0m\")
"

if [ "$QUICK_MODE" != true ]; then
    print_subsection "Multi-Asset COMPARE Query" "📊"
    echo -e "  ${DIM}Query: COMPARE AAPL, MSFT, GOOGL BY PE, MARKETCAP${NC}"
    dsl_compare=$(call_mcp_tool "execute-fk-dsl" '{"query":"COMPARE AAPL, MSFT, GOOGL BY PE, MARKETCAP","async":false}')
    echo "$dsl_compare" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if not data.get('isError', False):
        result = json.loads(data['content'][0]['text'])
        status = result.get('status', 'unknown')
        color = '\033[32m' if status == 'completed' else '\033[33m'
        print(f\"  Status: {color}{status}\033[0m\")
        
        # Check for synchronous execution results
        if 'result' in result and result['result']:
            exec_result = result['result']
            print()
            print('  \033[1mComparison Results:\033[0m')
            
            # Handle comparison format
            if isinstance(exec_result, dict):
                comparison = exec_result.get('comparison', [])
                if comparison:
                    print('  ' + '-' * 55)
                    print(f\"  {'Symbol':<12} {'P/E Ratio':<15} {'Market Cap':<20}\")
                    print('  ' + '-' * 55)
                    for item in comparison[:5]:
                        symbol = item.get('asset', 'N/A')
                        pe = item.get('pe', item.get('pe_ratio', 'N/A'))
                        mcap = item.get('marketcap', item.get('market_cap', 'N/A'))
                        pe_str = f\"{pe:.2f}\" if isinstance(pe, (int, float)) else str(pe)
                        mcap_str = f\"\${mcap:,.0f}\" if isinstance(mcap, (int, float)) else str(mcap)
                        print(f\"  {symbol:<12} {pe_str:<15} {mcap_str:<20}\")
                    print('  ' + '-' * 55)
                else:
                    # Show raw results
                    for key, value in list(exec_result.items())[:5]:
                        print(f\"    {key}: {value}\")
        elif 'results' in result:
            print(\"  Comparison Results:\")
            for asset, values in result.get('results', {}).items():
                print(f\"    {asset}: {values}\")
    else:
        print(\"  \033[33mMulti-asset comparison demonstration\033[0m\")
except Exception as e:
    print(f\"  \033[33mCOMPARE query demonstration (mock data in demo mode)\033[0m\")
"

    print_subsection "Correlation Analysis" "🔗"
    echo -e "  ${DIM}Query: CORRELATE BTC WITH ETH, SPY WINDOW 30d${NC}"
    dsl_correlate=$(call_mcp_tool "execute-fk-dsl" '{"query":"CORRELATE BTC WITH ETH, SPY WINDOW 30d","async":false}')
    echo "$dsl_correlate" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if not data.get('isError', False):
        result = json.loads(data['content'][0]['text'])
        status = result.get('status', 'unknown')
        color = '\033[32m' if status == 'completed' else '\033[33m'
        print(f\"  Status: {color}{status}\033[0m\")
        
        # Check for synchronous execution results
        if 'result' in result and result['result']:
            exec_result = result['result']
            print()
            print('  \033[1mCorrelation Analysis:\033[0m')
            
            if isinstance(exec_result, dict):
                # Primary asset info
                primary = exec_result.get('primary_asset', {})
                if primary:
                    symbol = primary.get('symbol', 'BTC') if isinstance(primary, dict) else primary
                    print(f\"    Primary Asset: {symbol}\")
                
                # Window info
                window = exec_result.get('window', {})
                if window:
                    window_str = f\"{window.get('value', 30)}{window.get('unit', 'd')}\" if isinstance(window, dict) else str(window)
                    print(f\"    Analysis Window: {window_str}\")
                
                # Correlation results
                correlations = exec_result.get('correlations', {})
                if correlations:
                    print()
                    print('    Correlation Coefficients:')
                    for asset, corr_data in correlations.items():
                        if isinstance(corr_data, dict):
                            coef = corr_data.get('coefficient', 0)
                            strength = corr_data.get('strength', 'N/A')
                            color = '\033[32m' if coef > 0.5 else '\033[33m' if coef > 0 else '\033[31m'
                            print(f\"      {asset}: {color}{coef:+.3f}\033[0m ({strength})\")
                        else:
                            print(f\"      {asset}: {corr_data:.3f}\")
                            
        elif 'correlation_matrix' in result:
            print(\"  Correlation Matrix:\")
            matrix = result['correlation_matrix']
            for pair, value in matrix.items():
                print(f\"    {pair}: {value:.3f}\")
    else:
        print(\"  \033[33mCorrelation analysis demonstration\033[0m\")
except Exception as e:
    print(f\"  \033[33mCORRELATE query demonstration (mock data in demo mode)\033[0m\")
"

    print_subsection "Complex SCAN Query" "🔍"
    echo -e "  ${DIM}Query: SCAN US_TECH WHERE PE < 30 AND VOLUME > 1000000${NC}"
    dsl_scan=$(call_mcp_tool "execute-fk-dsl" '{"query":"SCAN US_TECH WHERE PE < 30 AND VOLUME > 1000000","async":false}')
    echo "$dsl_scan" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if not data.get('isError', False):
        result = json.loads(data['content'][0]['text'])
        status = result.get('status', 'unknown')
        color = '\033[32m' if status == 'completed' else '\033[33m'
        print(f\"  Status: {color}{status}\033[0m\")
        
        # Check for synchronous execution results
        if 'result' in result and result['result']:
            exec_result = result['result']
            print()
            print('  \033[1mMarket Scan Results:\033[0m')
            
            # Handle list of matching assets
            if isinstance(exec_result, list):
                print(f\"    Matches Found: {len(exec_result)}\")
                if exec_result:
                    print()
                    print('  ' + '-' * 55)
                    print(f\"  {'Symbol':<10} {'Matches':<10} {'Conditions Met':<15}\")
                    print('  ' + '-' * 55)
                    for match in exec_result[:5]:
                        symbol = match.get('symbol', 'N/A')
                        matches = '\033[32m✓\033[0m' if match.get('matches', False) else '\033[31m✗\033[0m'
                        conditions = match.get('conditions_met', 0)
                        print(f\"  {symbol:<10} {matches:<10} {conditions:<15}\")
                    print('  ' + '-' * 55)
            elif isinstance(exec_result, dict):
                matches = exec_result.get('matches', [])
                print(f\"    Matches Found: {len(matches)}\")
                for match in matches[:5]:
                    print(f\"    • {match.get('symbol', 'N/A')}: PE={match.get('pe', 'N/A')}, Vol={match.get('volume', 'N/A')}\")
        elif 'matches' in result:
            matches = result.get('matches', [])
            print(f\"  Matches Found: {len(matches)}\")
            for match in matches[:5]:
                print(f\"    • {match.get('symbol', 'N/A')}: PE={match.get('pe', 'N/A')}, Vol={match.get('volume', 'N/A')}\")
    else:
        print(\"  \033[33mSCAN query demonstration\033[0m\")
except Exception as e:
    print(f\"  \033[33mSCAN query demonstration (mock data in demo mode)\033[0m\")
"
fi

end_timing "section3"

# =============================================================================
# SECTION 4: Session Management
# =============================================================================
print_section "SECTION 4: Session Management" "📋"
start_timing "section4"

print_subsection "Create Analysis Session" "➕"
session_response=$(call_mcp_tool "create-analysis-session" '{"assets":["AAPL","TSLA","BTC"],"sessionType":"portfolio","userId":"demo-user","ttlHours":24,"tags":["demo","live-test"]}')
echo "$session_response" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if not data.get('isError', False):
        result = json.loads(data['content'][0]['text'])
        status = result.get('status', 'unknown')
        if status == 'success':
            print(f\"  Status:     \033[32m{status.upper()}\033[0m\")
            session_id = result.get('session_id', 'N/A')
            print(f\"  Session ID: {session_id}\")
            print(f\"  Type:       {result.get('type', 'N/A')}\")
            print(f\"  Assets:     {', '.join(result.get('assets', []))}\")
            print(f\"  TTL:        {result.get('ttl_hours', 'N/A')} hours\")
            print(f\"  Tags:       {', '.join(result.get('tags', []))}\")
            print(f\"  Expires:    {result.get('expires_at', 'N/A')}\")
        else:
            print(f\"  \033[33mSession creation: {result.get('error', 'unknown error')}\033[0m\")
    else:
        print(\"  \033[33mSession management not available in demo mode\033[0m\")
except Exception as e:
    print(f\"  \033[33mSession demonstration (requires database)\033[0m\")
"

# Extract session ID directly from the response without temporary file
SESSION_ID=$(echo "$session_response" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if not data.get('isError', False):
        result = json.loads(data['content'][0]['text'])
        if result.get('status') == 'success':
            print(result.get('session_id', ''), end='')
except:
    pass
" 2>/dev/null)

if [ -n "$SESSION_ID" ] && [ "$SESSION_ID" != "N/A" ]; then
    print_subsection "Query Within Session Context" "🔍"
    echo -e "  ${DIM}Querying AAPL within session context...${NC}"
    # Build JSON safely for session query
    session_query=$(curl -s -X POST "${BASE_URL}/mcp/tools/call" \
        -H "Content-Type: application/json" \
        -d "{\"name\":\"search-by-symbol\",\"arguments\":{\"symbol\":\"AAPL\",\"market\":\"US\",\"depth\":\"quick\",\"sessionId\":\"${SESSION_ID}\"}}" 2>/dev/null)
    echo "$session_query" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if not data.get('isError', False):
        result = json.loads(data['content'][0]['text'])
        print(f\"  Session-aware query completed\")
        print(f\"  Symbol: {result.get('symbol', 'N/A')}\")
        cached = result.get('cached', {})
        print(f\"  Price:  \${cached.get('price', 'N/A')}\")
except:
    print(\"  Session query demonstration\")
"

    print_subsection "Session Analytics" "📊"
    analytics_response=$(call_mcp_tool "get-session-analytics" '{"days":30}')
    echo "$analytics_response" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if not data.get('isError', False):
        result = json.loads(data['content'][0]['text'])
        if result.get('status') == 'success':
            print(f\"  Total Sessions:      {result.get('total_sessions', 0)}\")
            print(f\"  Active Sessions:     {result.get('active_sessions', 0)}\")
            print(f\"  Archived Sessions:   {result.get('archived_sessions', 0)}\")
            print(f\"  Total Queries:       {result.get('total_queries', 0)}\")
            print(f\"  Avg Duration:        {result.get('avg_duration_seconds', 0):.0f}s\")
            print(f\"  Queries/Session:     {result.get('avg_queries_per_session', 0):.1f}\")
        else:
            print(f\"  \033[33m{result.get('message', 'Analytics not available')}\033[0m\")
except:
    print(\"  \033[33mSession analytics demonstration\033[0m\")
"
else
    print_info "Session management requires database connectivity"
fi

end_timing "section4"

# =============================================================================
# SECTION 5: Provider Arbitration
# =============================================================================
print_section "SECTION 5: Provider Arbitration" "⚖️"
start_timing "section5"

print_subsection "Data Lineage Example" "🔍"
echo -e "  ${DIM}Showing data source tracking for AAPL query...${NC}"
lineage_response=$(call_mcp_tool "search-by-symbol" '{"symbol":"AAPL","market":"US","depth":"quick"}')
echo "$lineage_response" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if not data.get('isError', False):
        result = json.loads(data['content'][0]['text'])
        cached = result.get('cached', {})

        print(\"  Data Lineage:\")
        print(f\"    Source Provider:  {cached.get('source', 'N/A')}\")
        print(f\"    Confidence Score: {cached.get('confidence', 0) * 100:.0f}%\")
        print(f\"    Cache Status:     {'HIT' if cached.get('from_cache', False) else 'MISS'}\")
        print(f\"    Timestamp:        {cached.get('timestamp', 'N/A')}\")

        lineage = result.get('lineage', {})
        if lineage:
            print(f\"    Request ID:       {lineage.get('request_id', 'N/A')}\")
            print(f\"    Arbitration:      {lineage.get('arbitration_method', 'N/A')}\")
    else:
        print(\"  Data lineage demonstration\")
except:
    print(\"  \033[33mData lineage tracking demonstration\033[0m\")
"

print_subsection "Provider Selection Demo" "🎯"
echo -e "  ${DIM}Demonstrating intelligent provider selection...${NC}"
providers_health=$(http_get "/health/providers")
echo "$providers_health" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    providers = data.get('providers', {})

    if providers:
        # Sort by success rate * (1 / latency) for simple scoring demo
        scored = []
        for name, info in providers.items():
            latency = info.get('avg_latency_ms', 1000)
            success = info.get('success_rate', 0)
            score = success / max(latency / 1000, 0.1)  # Normalize
            scored.append((name, score, info))

        scored.sort(key=lambda x: x[1], reverse=True)

        print(\"  Provider Selection Ranking:\")
        print(\"  \" + \"-\" * 55)
        print(f\"  {'Provider':<20} {'Score':>8} {'Latency':>10} {'Success':>10}\")
        print(\"  \" + \"-\" * 55)

        for i, (name, score, info) in enumerate(scored[:5], 1):
            latency = info.get('avg_latency_ms', 0)
            success = info.get('success_rate', 0) * 100
            marker = '\033[32m→\033[0m' if i == 1 else ' '
            print(f\"  {marker} {name:<18} {score:>8.2f} {latency:>8.0f}ms {success:>9.1f}%\")

        print(\"  \" + \"-\" * 55)
        print(f\"  \033[32m→\033[0m = Selected as primary provider\")
    else:
        print(\"  Provider selection demonstration\")
except:
    print(\"  \033[33mProvider arbitration demonstration\033[0m\")
"

end_timing "section5"

# =============================================================================
# SECTION 6: Performance Metrics
# =============================================================================
print_section "SECTION 6: Performance Metrics" "⚡"
start_timing "section6"

print_subsection "Cache Performance" "💾"
cache_metrics=$(http_get "/api/metrics/cache")
echo "$cache_metrics" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)

    overall = data.get('overall', {})
    l1 = data.get('l1_cache', {})
    l2 = data.get('l2_cache', {})

    print(\"  Overall Cache Performance:\")
    print(f\"    Combined Hit Rate:    {overall.get('combined_hit_rate', 0) * 100:.1f}%\")
    print(f\"    Total Requests:       {overall.get('total_requests', 0)}\")
    print()

    print(\"  L1 Cache (Redis - Fast):\")
    l1_hit_rate = l1.get('hit_rate', 0) * 100
    color = '\033[32m' if l1_hit_rate > 80 else '\033[33m' if l1_hit_rate > 50 else '\033[31m'
    print(f\"    Hit Rate:    {color}{l1_hit_rate:.1f}%\033[0m\")
    print(f\"    Avg Latency: {l1.get('avg_latency_ms', 0):.2f}ms\")
    print(f\"    P95 Latency: {l1.get('p95_latency_ms', 0):.2f}ms\")
    print()

    print(\"  L2 Cache (PostgreSQL - Durable):\")
    l2_hit_rate = l2.get('hit_rate', 0) * 100
    color = '\033[32m' if l2_hit_rate > 60 else '\033[33m' if l2_hit_rate > 30 else '\033[31m'
    print(f\"    Hit Rate:    {color}{l2_hit_rate:.1f}%\033[0m\")
    print(f\"    Avg Latency: {l2.get('avg_latency_ms', 0):.2f}ms\")
except:
    print(\"  \033[33mCache metrics demonstration\033[0m\")
"

print_subsection "Provider Latency Comparison" "📶"
providers_health=$(http_get "/health/providers")
echo "$providers_health" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    providers = data.get('providers', {})

    if providers:
        # Sort by latency
        by_latency = sorted(
            [(n, p.get('avg_latency_ms', 9999)) for n, p in providers.items()],
            key=lambda x: x[1]
        )

        print(\"  Provider Latency Ranking:\")
        max_latency = max(l for _, l in by_latency) if by_latency else 1

        for name, latency in by_latency[:8]:
            bar_length = int((latency / max_latency) * 30) if max_latency > 0 else 0
            bar = '█' * bar_length
            color = '\033[32m' if latency < 100 else '\033[33m' if latency < 500 else '\033[31m'
            print(f\"    {name:<15} {color}{latency:>6.0f}ms\033[0m {bar}\")
except:
    print(\"  \033[33mLatency comparison demonstration\033[0m\")
"

if [ "$QUICK_MODE" != true ]; then
    print_subsection "Ray Cluster Status" "🔬"
    # Check if Ray is available via docker and capture output in single call
    ray_status_output=$(docker exec fiml-ray-head ray status 2>/dev/null) && {
        echo "$ray_status_output" | head -15 | while read -r line; do
            echo "  $line"
        done
    } || {
        echo -e "  ${GRAY}Ray cluster status (requires docker services):${NC}"
        echo -e "  ${DIM}  Start with: make up${NC}"
    }
fi

print_subsection "Task Registry Status" "📝"
task_metrics=$(http_get "/api/metrics/tasks")
echo "$task_metrics" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)

    print(f\"  Total Tasks:     {data.get('total_tasks', 0)}\")
    print(f\"  Active Tasks:    {data.get('active_tasks', 0)}\")
    print(f\"  Completed:       {data.get('completed_tasks', 0)}\")
    print(f\"  Failed:          {data.get('failed_tasks', 0)}\")

    by_type = data.get('by_type', {})
    if by_type:
        print(\"  By Type:\")
        for task_type, count in list(by_type.items())[:5]:
            print(f\"    {task_type}: {count}\")
except:
    print(\"  \033[33mTask registry demonstration\033[0m\")
"

end_timing "section6"

# =============================================================================
# SECTION 7: v0.2.2 Features - Monitoring & Observability
# =============================================================================
print_section "SECTION 7: v0.2.2 Monitoring & Observability" "🔭"
start_timing "section7"

print_subsection "Watchdog Health Monitor" "👁️"
watchdog_metrics=$(http_get "/api/metrics/watchdog")
echo "$watchdog_metrics" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    
    overall_health = data.get('overall_health', 'unknown')
    color = '\033[32m' if overall_health == 'healthy' else '\033[33m' if overall_health == 'degraded' else '\033[31m'
    print(f\"  Overall Health: {color}{overall_health.upper()}\033[0m\")
    
    components = data.get('components', {})
    if components:
        print()
        print('  Component Health Status:')
        for component, status in components.items():
            if isinstance(status, dict):
                health = status.get('healthy', status.get('status', 'unknown'))
                health_str = str(health).upper()
                icon = '\033[32m●\033[0m' if health in [True, 'healthy', 'HEALTHY'] else '\033[31m●\033[0m'
                latency = status.get('latency_ms', status.get('avg_latency_ms', 'N/A'))
                if isinstance(latency, (int, float)):
                    print(f\"    {icon} {component:<20} Latency: {latency:>6.0f}ms\")
                else:
                    print(f\"    {icon} {component:<20} Status: {health_str}\")
            else:
                print(f\"    • {component}: {status}\")
    
    # Event stream info
    events = data.get('recent_events', data.get('events', []))
    if events:
        print()
        print(f\"  Recent Events: {len(events)}\")
        for event in events[:3]:
            if isinstance(event, dict):
                print(f\"    • {event.get('type', 'event')}: {event.get('message', event.get('details', 'N/A'))}\")
            
except Exception as e:
    print(f\"  \033[33mWatchdog metrics (requires services): {str(e)[:50]}\033[0m\")
"

print_subsection "Performance Monitoring" "📈"
perf_metrics=$(http_get "/api/metrics/performance")
echo "$perf_metrics" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    
    # Request metrics
    requests = data.get('requests', {})
    if requests:
        print('  Request Statistics:')
        print(f\"    Total Requests:    {requests.get('total', 0):,}\")
        print(f\"    Success Rate:      {requests.get('success_rate', 0) * 100:.1f}%\")
        print(f\"    Avg Response Time: {requests.get('avg_response_time_ms', 0):.2f}ms\")
        print(f\"    P95 Response Time: {requests.get('p95_response_time_ms', 0):.2f}ms\")
        print()
    
    # Endpoint breakdown
    endpoints = data.get('endpoints', data.get('by_endpoint', {}))
    if endpoints:
        print('  Top Endpoints:')
        def get_endpoint_count(item):
            stats = item[1]
            return stats.get('count', 0) if isinstance(stats, dict) else 0
        sorted_endpoints = sorted(endpoints.items(), key=get_endpoint_count, reverse=True)[:5]
        for endpoint, stats in sorted_endpoints:
            if isinstance(stats, dict):
                count = stats.get('count', 0)
                avg_time = stats.get('avg_time_ms', 0)
                print(f\"    {endpoint:<30} {count:>6} requests, {avg_time:>6.1f}ms avg\")
    
    # Memory/resource usage if available
    resources = data.get('resources', {})
    if resources:
        print()
        print('  Resource Usage:')
        print(f\"    Memory Usage: {resources.get('memory_mb', 0):.1f} MB\")
        print(f\"    CPU Usage:    {resources.get('cpu_percent', 0):.1f}%\")
        
except Exception as e:
    print(f\"  \033[33mPerformance metrics (requires services): {str(e)[:50]}\033[0m\")
"

if [ "$QUICK_MODE" != true ]; then
    print_subsection "Narrative Generation Capability" "✍️"
    echo -e "  ${DIM}Demonstrating AI-powered narrative generation...${NC}"
    narrative_response=$(call_mcp_tool "search-by-symbol" '{"symbol":"MSFT","market":"US","depth":"deep"}')
    echo "$narrative_response" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if not data.get('isError', False):
        result = json.loads(data['content'][0]['text'])
        narrative = result.get('narrative', {})
        
        if narrative and narrative.get('summary'):
            print('  \033[32m✓ Narrative Engine Active\033[0m')
            print()
            print('  Summary:')
            summary = narrative.get('summary', '')[:300]
            # Word wrap at ~70 chars
            import textwrap
            wrapped = textwrap.fill(summary, width=65, initial_indent='    ', subsequent_indent='    ')
            print(wrapped)
            if len(narrative.get('summary', '')) > 300:
                print('    ...')
            
            sections = narrative.get('sections', [])
            if sections:
                print()
                print(f\"  Sections Generated: {len(sections)}\")
                for section in sections[:3]:
                    title = section.get('title', 'Unknown')
                    sec_type = section.get('type', 'N/A')
                    confidence = section.get('confidence', 0)
                    print(f\"    • {title} ({sec_type}) - Confidence: {confidence:.0%}\")
                    
            insights = narrative.get('key_insights', [])
            if insights:
                print()
                print('  Key Insights:')
                for insight in insights[:3]:
                    print(f\"    • {insight[:70]}{'...' if len(insight) > 70 else ''}\")
        else:
            print('  \033[33mNarrative generation requires LLM configuration (Azure OpenAI)\033[0m')
            print('  \033[33mSet AZURE_OPENAI_API_KEY to enable narratives\033[0m')
    else:
        print('  \033[33mNarrative demonstration\033[0m')
except Exception as e:
    print(f\"  \033[33mNarrative generation demonstration\033[0m\")
"

    print_subsection "MCP Tool Discovery" "🔧"
    echo -e "  ${DIM}Available MCP Tools (v0.2.2):${NC}"
    tools_response=$(http_get "/mcp/tools")
    echo "$tools_response" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    tools = data.get('tools', [])
    
    if tools:
        print(f\"  Total Available Tools: {len(tools)}\")
        print()
        print('  ' + '-' * 60)
        print(f\"  {'Tool Name':<30} {'Description':<28}\")
        print('  ' + '-' * 60)
        
        for tool in tools:
            name = tool.get('name', 'N/A')
            desc = tool.get('description', '')[:45]
            print(f\"  {name:<30} {desc}...\")
            
        print('  ' + '-' * 60)
        print()
        print('  Session Management Tools:')
        session_tools = [t for t in tools if 'session' in t.get('name', '').lower()]
        for tool in session_tools:
            print(f\"    • {tool.get('name')}\")
    else:
        print('  Tool discovery not available')
except:
    print('  \033[33mMCP tool discovery demonstration\033[0m')
"
fi

end_timing "section7"

# =============================================================================
# Demo Summary
# =============================================================================
DEMO_END_TIME=$(date +%s.%N)
TOTAL_DURATION=$(calc_duration "$DEMO_START_TIME" "$DEMO_END_TIME")

echo ""
echo -e "${BOLD}${WHITE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${WHITE}║                    ✅ ${GREEN}DEMO COMPLETE${WHITE} ✅                          ║${NC}"
echo -e "${BOLD}${WHITE}╠════════════════════════════════════════════════════════════════╣${NC}"
echo -e "${BOLD}${WHITE}║                                                                ║${NC}"
echo -e "${BOLD}${WHITE}║  ${CYAN}Total Duration:${WHITE} ${TOTAL_DURATION}s                                       ║${NC}"
echo -e "${BOLD}${WHITE}║                                                                ║${NC}"
echo -e "${BOLD}${WHITE}║  ${DIM}Core Endpoints:${NC}                                              ${BOLD}${WHITE}║${NC}"
echo -e "${BOLD}${WHITE}║    ${BLUE}API Server:${NC}    ${BASE_URL}                         ${BOLD}${WHITE}║${NC}"
echo -e "${BOLD}${WHITE}║    ${BLUE}API Docs:${NC}       ${BASE_URL}/docs                    ${BOLD}${WHITE}║${NC}"
echo -e "${BOLD}${WHITE}║    ${BLUE}Health:${NC}         ${BASE_URL}/health                  ${BOLD}${WHITE}║${NC}"
echo -e "${BOLD}${WHITE}║    ${BLUE}MCP Tools:${NC}      ${BASE_URL}/mcp/tools               ${BOLD}${WHITE}║${NC}"
echo -e "${BOLD}${WHITE}║                                                                ║${NC}"
echo -e "${BOLD}${WHITE}║  ${DIM}v0.2.2 Metrics & Monitoring:${NC}                                 ${BOLD}${WHITE}║${NC}"
echo -e "${BOLD}${WHITE}║    ${BLUE}Prometheus:${NC}     ${BASE_URL}/metrics                 ${BOLD}${WHITE}║${NC}"
echo -e "${BOLD}${WHITE}║    ${BLUE}Cache:${NC}          ${BASE_URL}/api/metrics/cache       ${BOLD}${WHITE}║${NC}"
echo -e "${BOLD}${WHITE}║    ${BLUE}Watchdog:${NC}       ${BASE_URL}/api/metrics/watchdog    ${BOLD}${WHITE}║${NC}"
echo -e "${BOLD}${WHITE}║    ${BLUE}Performance:${NC}    ${BASE_URL}/api/metrics/performance ${BOLD}${WHITE}║${NC}"
echo -e "${BOLD}${WHITE}║    ${BLUE}Tasks:${NC}          ${BASE_URL}/api/metrics/tasks       ${BOLD}${WHITE}║${NC}"
echo -e "${BOLD}${WHITE}║                                                                ║${NC}"
echo -e "${BOLD}${WHITE}║  ${DIM}For comprehensive testing, run:${NC}                              ${BOLD}${WHITE}║${NC}"
echo -e "${BOLD}${WHITE}║    ${YELLOW}./scripts/test_live_system.sh${NC}                               ${BOLD}${WHITE}║${NC}"
echo -e "${BOLD}${WHITE}║                                                                ║${NC}"
echo -e "${BOLD}${WHITE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""
