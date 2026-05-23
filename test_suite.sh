#!/bin/bash
# Nova Platform — Full Test Suite
BASE="http://localhost:8000"
PASS=0; FAIL=0
declare -A RESULT   # TC-01 -> PASS/FAIL
declare -A DETAIL   # TC-01 -> detail string
TMPB=$(mktemp)      # temp file for response body
export TMPB

# ── Helpers ────────────────────────────────────────────────────────
tc() {   # tc ID "name" 1|0 "detail"
  local id="$1" name="$2" ok="$3" det="${4:-}"
  if [ "$ok" = "1" ]; then RESULT[$id]="PASS"; ((PASS++))
  else RESULT[$id]="FAIL"; ((FAIL++)); fi
  DETAIL[$id]="${name}|||${det}"
}

do_req() {
  # usage: do_req [curl-args...]  -> sets $BODY and $CODE
  CODE=$(curl -s -o "$TMPB" -w "%{http_code}" "$@")
  BODY=$(cat "$TMPB")
  export BODY CODE
}

G() {
  local p="$1"
  if [ -n "$TOKEN" ]; then
    do_req -H "Authorization: Bearer $TOKEN" "$BASE$p"
  else
    do_req "$BASE$p"
  fi
}

P() {
  local p="$1" body="$2" ct="${3:-application/json}"
  if [ -n "$TOKEN" ]; then
    do_req -X POST -H "Content-Type: $ct" -H "Authorization: Bearer $TOKEN" -d "$body" "$BASE$p"
  else
    do_req -X POST -H "Content-Type: $ct" -d "$body" "$BASE$p"
  fi
}

PU() {
  do_req -X PUT -H "Content-Type: application/json" -H "Authorization: Bearer $TOKEN" -d "$2" "$BASE$1"
}

DEL() {
  do_req -X DELETE -H "Authorization: Bearer $TOKEN" "$BASE$1"
}

jv() { python -c "import json,sys; d=json.load(open(sys.argv[1])); print(d.get(sys.argv[2],''))" "$TMPB" "$1" 2>/dev/null; }

# ── SETUP ──────────────────────────────────────────────────────────
echo "=== SETUP: Registering fresh test user ==="
RAND=$RANDOM
EMAIL="novatest_${RAND}@nova.com"
TOKEN=""
P "/api/auth/register" \
  "{\"name\":\"Nova Tester\",\"email\":\"$EMAIL\",\"password\":\"Test1234\",\"company_name\":\"NovaCo\",\"role\":\"admin\"}"
TOKEN=$(jv "access_token")
if [ ${#TOKEN} -gt 20 ]; then
  echo "Token OK: user registered, token ${#TOKEN} chars"
else
  echo "Register failed (HTTP $CODE): $BODY"; exit 1
fi
echo ""

# ── BLOCK 1: SERVER HEALTH ─────────────────────────────────────────
do_req "$BASE/health"
[ "$CODE" = "200" ] && tc TC-01 "Backend server healthy" 1 "HTTP 200" || tc TC-01 "Backend server healthy" 0 "HTTP $CODE"

do_req "http://localhost:5173"
[ "$CODE" = "200" ] && tc TC-02 "Frontend (Vite) serving app" 1 "HTTP 200" || tc TC-02 "Frontend (Vite) serving app" 0 "HTTP $CODE"

do_req "$BASE/api/docs"
[ "$CODE" = "200" ] && tc TC-03 "Swagger API docs accessible" 1 "HTTP 200" || tc TC-03 "Swagger API docs accessible" 0 "HTTP $CODE"

# ── BLOCK 2: AUTHENTICATION ────────────────────────────────────────
DUP="dup_${RAND}@x.com"
TOKEN_SAVE="$TOKEN"; TOKEN=""
P "/api/auth/register" \
  "{\"name\":\"X\",\"email\":\"$DUP\",\"password\":\"P123\",\"company_name\":\"X\",\"role\":\"operator\"}"
UID=$(jv "user_id")
[ "$CODE" = "201" ] && tc TC-04 "Register new account" 1 "user_id=$UID" || tc TC-04 "Register new account" 0 "HTTP $CODE"
TOKEN="$TOKEN_SAVE"

TOKEN_SAVE2="$TOKEN"; TOKEN=""
P "/api/auth/register" \
  "{\"name\":\"X\",\"email\":\"$DUP\",\"password\":\"P\",\"company_name\":\"X\",\"role\":\"operator\"}"
[ "$CODE" = "400" ] && tc TC-05 "Duplicate email blocked" 1 "HTTP 400" || tc TC-05 "Duplicate email blocked" 0 "HTTP $CODE"
TOKEN="$TOKEN_SAVE2"

do_req -X POST -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=${EMAIL}&password=Test1234" "$BASE/api/auth/login"
LTK=$(jv "access_token")
[ ${#LTK} -gt 10 ] && tc TC-06 "Login correct credentials" 1 "token OK" || tc TC-06 "Login correct credentials" 0 "HTTP $CODE"

do_req -X POST -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=${EMAIL}&password=WRONGPASS" "$BASE/api/auth/login"
[ "$CODE" = "401" ] && tc TC-07 "Login wrong password → 401" 1 "HTTP 401" || tc TC-07 "Login wrong password → 401" 0 "HTTP $CODE"

do_req -X POST -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=nobody@xyz.com&password=abc" "$BASE/api/auth/login"
[ "$CODE" = "401" ] && tc TC-08 "Login unknown email → 401" 1 "HTTP 401" || tc TC-08 "Login unknown email → 401" 0 "HTTP $CODE"

G "/api/auth/me"
ME=$(jv "email")
[ "$ME" = "$EMAIL" ] && tc TC-09 "GET /auth/me returns current user" 1 "email=$ME" || tc TC-09 "GET /auth/me returns current user" 0 "got=$ME HTTP=$CODE"

do_req -H "Authorization: Bearer invalid_jwt_xyz" "$BASE/api/auth/me"
[ "$CODE" = "401" ] && tc TC-10 "Invalid JWT rejected" 1 "HTTP 401" || tc TC-10 "Invalid JWT rejected" 0 "HTTP $CODE"

do_req "$BASE/api/auth/me"
[ "$CODE" = "401" ] && tc TC-11 "No token on protected endpoint → 401" 1 "HTTP 401" || tc TC-11 "No token on protected endpoint → 401" 0 "HTTP $CODE"

P "/api/auth/logout" "{}"
[ "$CODE" = "200" ] && tc TC-12 "Logout endpoint" 1 "HTTP 200" || tc TC-12 "Logout endpoint" 0 "HTTP $CODE"

# ── BLOCK 3: WORKFLOWS ─────────────────────────────────────────────
VY='workflow:\n  name: TestFlow\n  version: 1.0\n  steps:\n    - id: start\n      type: start\n      next: end\n    - id: end\n      type: end'
IY='workflow:\n  name: BadFlow\n  steps:\n    - id: s\n      type: invalid_xyz'

G "/api/workflows"
TOT=$(jv "total")
[ "$CODE" = "200" ] && tc TC-13 "List workflows (paginated)" 1 "total=$TOT" || tc TC-13 "List workflows (paginated)" 0 "HTTP $CODE"

P "/api/workflows/validate" "{\"yaml_config\":\"$VY\"}"
VV=$(jv "valid")
[ "$VV" = "True" ] && tc TC-14 "Validate valid YAML → true" 1 "valid=true" || tc TC-14 "Validate valid YAML → true" 0 "valid=$VV HTTP=$CODE"

P "/api/workflows/validate" "{\"yaml_config\":\"$IY\"}"
VV=$(jv "valid")
[ "$VV" = "False" ] && tc TC-15 "Validate invalid YAML → false+errors" 1 "valid=false" || tc TC-15 "Validate invalid YAML → false+errors" 0 "valid=$VV HTTP=$CODE"

P "/api/workflows" \
  "{\"name\":\"Invoice Flow\",\"description\":\"Test workflow\",\"yaml_config\":\"$VY\"}"
WF_ID=$(jv "id")
[ -n "$WF_ID" ] && [ "$WF_ID" != "None" ] && [ "$WF_ID" != "" ] \
  && tc TC-16 "Create workflow" 1 "id=$WF_ID" \
  || tc TC-16 "Create workflow" 0 "HTTP $CODE body=$BODY"

G "/api/workflows"
TOT2=$(jv "total")
[ "${TOT2:-0}" -ge 1 ] 2>/dev/null \
  && tc TC-17 "List workflows after create (>=1)" 1 "total=$TOT2" \
  || tc TC-17 "List workflows after create (>=1)" 0 "total=$TOT2"

if [ -n "$WF_ID" ] && [ "$WF_ID" != "None" ] && [ "$WF_ID" != "" ]; then
  G "/api/workflows/$WF_ID"
  GID=$(jv "id")
  [ "$GID" = "$WF_ID" ] && tc TC-18 "Get workflow by ID" 1 "id=$WF_ID" || tc TC-18 "Get workflow by ID" 0 "got=$GID HTTP=$CODE"

  PU "/api/workflows/$WF_ID" "{\"description\":\"Updated\"}"
  [ "$CODE" = "200" ] && tc TC-19 "Update workflow" 1 "HTTP 200" || tc TC-19 "Update workflow" 0 "HTTP $CODE"

  P "/api/workflows/$WF_ID/run" "{\"input_data\":{}}"
  RUN_ID=$(jv "run_id")
  [ -n "$RUN_ID" ] && [ "$RUN_ID" != "None" ] \
    && tc TC-20 "Run workflow (async)" 1 "run_id=$RUN_ID" \
    || tc TC-20 "Run workflow (async)" 0 "HTTP $CODE $BODY"

  G "/api/workflows/$WF_ID/runs"
  [ "$CODE" = "200" ] && tc TC-21 "Get workflow run history" 1 "HTTP 200" || tc TC-21 "Get workflow run history" 0 "HTTP $CODE"
else
  for i in TC-18 TC-19 TC-20 TC-21; do tc $i "Workflow sub-test" 0 "no WF_ID (create failed)"; done
fi

do_req -H "Authorization: Bearer $TOKEN" "$BASE/api/workflows/999999"
[ "$CODE" = "404" ] && tc TC-22 "Nonexistent workflow → 404" 1 "HTTP 404" || tc TC-22 "Nonexistent workflow → 404" 0 "HTTP $CODE"

# ── BLOCK 4: DOCUMENTS ─────────────────────────────────────────────
G "/api/documents"
[ "$CODE" = "200" ] && tc TC-23 "List documents" 1 "total=$(jv total)" || tc TC-23 "List documents" 0 "HTTP $CODE"

TMPF=$(mktemp /tmp/invoice_XXXXXX.pdf)
printf '%%PDF-1.4\nInvoice INV-2024-001\nVendor: ACME Corp\nAmount: USD 12500\n' > "$TMPF"
do_req -X POST -H "Authorization: Bearer $TOKEN" \
  -F "file=@${TMPF};type=application/pdf" "$BASE/api/documents/upload"
DOC_ID=$(jv "id")
rm -f "$TMPF"
[ -n "$DOC_ID" ] && [ "$DOC_ID" != "None" ] && [ "$DOC_ID" != "" ] \
  && tc TC-24 "Upload document" 1 "id=$DOC_ID status=$(jv status)" \
  || tc TC-24 "Upload document" 0 "HTTP $CODE"

if [ -n "$DOC_ID" ] && [ "$DOC_ID" != "None" ] && [ "$DOC_ID" != "" ]; then
  G "/api/documents/$DOC_ID"
  [ "$CODE" = "200" ] && tc TC-25 "Get document by ID" 1 "filename=$(jv filename)" || tc TC-25 "Get document by ID" 0 "HTTP $CODE"
  P "/api/documents/$DOC_ID/reprocess" "{}"
  [ "$CODE" = "200" ] && tc TC-26 "Reprocess document" 1 "HTTP 200" || tc TC-26 "Reprocess document" 0 "HTTP $CODE $BODY"
else
  tc TC-25 "Get document by ID" 0 "no DOC_ID (upload failed)"
  tc TC-26 "Reprocess document" 0 "no DOC_ID (upload failed)"
fi

do_req -H "Authorization: Bearer $TOKEN" "$BASE/api/documents/999999"
[ "$CODE" = "404" ] && tc TC-27 "Nonexistent document → 404" 1 "HTTP 404" || tc TC-27 "Nonexistent document → 404" 0 "HTTP $CODE"

# ── BLOCK 5: APPROVALS ─────────────────────────────────────────────
G "/api/approvals"
[ "$CODE" = "200" ] && tc TC-28 "List approvals" 1 "total=$(jv total)" || tc TC-28 "List approvals" 0 "HTTP $CODE"

G "/api/approvals/pending-count"
PC=$(jv "pending")
[ "$CODE" = "200" ] && tc TC-29 "Pending approvals count" 1 "pending=$PC" || tc TC-29 "Pending approvals count" 0 "HTTP $CODE"

P "/api/approvals/create" \
  "{\"title\":\"Invoice 5500\",\"description\":\"High value\",\"assigned_role\":\"Manager\",\"amount\":\"15000\"}"
APP1=$(jv "id")
[ -n "$APP1" ] && [ "$APP1" != "None" ] && [ "$APP1" != "" ] \
  && tc TC-30 "Create approval item" 1 "id=$APP1 status=$(jv status)" \
  || tc TC-30 "Create approval item" 0 "HTTP $CODE $BODY"

P "/api/approvals/create" \
  "{\"title\":\"Vendor Payment\",\"description\":\"Emergency\",\"assigned_role\":\"Admin\",\"amount\":\"50000\"}"
APP2=$(jv "id")
[ -n "$APP2" ] && [ "$APP2" != "None" ] && [ "$APP2" != "" ] \
  && tc TC-31 "Create second approval" 1 "id=$APP2" \
  || tc TC-31 "Create second approval" 0 "HTTP $CODE"

if [ -n "$APP1" ] && [ "$APP1" != "None" ] && [ "$APP1" != "" ]; then
  G "/api/approvals/$APP1"
  [ "$CODE" = "200" ] && tc TC-32 "Get approval by ID" 1 "title=$(jv title)" || tc TC-32 "Get approval by ID" 0 "HTTP $CODE"

  P "/api/approvals/$APP1/action" "{\"action\":\"approve\",\"comment\":\"Looks good\"}"
  NS=$(jv "new_status")
  [ "$CODE" = "200" ] && tc TC-33 "Approve approval" 1 "new_status=$NS" || tc TC-33 "Approve approval" 0 "HTTP $CODE $BODY"

  P "/api/approvals/$APP1/action" "{\"action\":\"approve\",\"comment\":\"again\"}"
  [ "$CODE" = "400" ] && tc TC-34 "Re-action on closed approval blocked" 1 "HTTP 400" || tc TC-34 "Re-action on closed approval blocked" 0 "HTTP $CODE"
else
  for i in TC-32 TC-33 TC-34; do tc $i "Approval sub-test" 0 "no APP1"; done
fi

if [ -n "$APP2" ] && [ "$APP2" != "None" ] && [ "$APP2" != "" ]; then
  P "/api/approvals/$APP2/action" "{\"action\":\"reject\",\"comment\":\"Budget exceeded\"}"
  NS=$(jv "new_status")
  [ "$CODE" = "200" ] && tc TC-35 "Reject approval" 1 "new_status=$NS" || tc TC-35 "Reject approval" 0 "HTTP $CODE"

  P "/api/approvals/$APP2/action" "{\"action\":\"delete\",\"comment\":\"\"}"
  [ "$CODE" = "400" ] && tc TC-36 "Invalid action value blocked" 1 "HTTP 400" || tc TC-36 "Invalid action value blocked" 0 "HTTP $CODE"
else
  tc TC-35 "Reject approval" 0 "no APP2"
  tc TC-36 "Invalid action blocked" 0 "no APP2"
fi

# ── BLOCK 6: EXCEPTIONS ────────────────────────────────────────────
G "/api/exceptions"
[ "$CODE" = "200" ] && tc TC-37 "List exceptions" 1 "total=$(jv total)" || tc TC-37 "List exceptions" 0 "HTTP $CODE"

G "/api/exceptions/stats"
[ "$CODE" = "200" ] && tc TC-38 "Exception stats" 1 "total=$(jv total) critical=$(jv critical)" || tc TC-38 "Exception stats" 0 "HTTP $CODE"

P "/api/exceptions" \
  "{\"exception_type\":\"fraud\",\"reason\":\"Suspicious txn\",\"severity\":\"critical\",\"details\":\"500x avg\"}"
EXC1=$(jv "id")
[ -n "$EXC1" ] && [ "$EXC1" != "None" ] && [ "$EXC1" != "" ] \
  && tc TC-39 "Create critical exception" 1 "id=$EXC1" \
  || tc TC-39 "Create critical exception" 0 "HTTP $CODE $BODY"

P "/api/exceptions" \
  "{\"exception_type\":\"delay\",\"reason\":\"Late shipment\",\"severity\":\"high\",\"details\":\"Customs\"}"
EXC2=$(jv "id")
[ -n "$EXC2" ] && [ "$EXC2" != "None" ] && [ "$EXC2" != "" ] \
  && tc TC-40 "Create high severity exception" 1 "id=$EXC2" \
  || tc TC-40 "Create high severity exception" 0 "HTTP $CODE"

P "/api/exceptions" \
  "{\"exception_type\":\"data_quality\",\"reason\":\"Missing PO\",\"severity\":\"medium\",\"details\":\"PO#\"}"
EXC3=$(jv "id")
[ -n "$EXC3" ] && [ "$EXC3" != "None" ] && [ "$EXC3" != "" ] \
  && tc TC-41 "Create medium severity exception" 1 "id=$EXC3" \
  || tc TC-41 "Create medium severity exception" 0 "HTTP $CODE"

if [ -n "$EXC1" ] && [ "$EXC1" != "None" ] && [ "$EXC1" != "" ]; then
  G "/api/exceptions/$EXC1"
  SEV=$(jv "severity")
  [ "$CODE" = "200" ] && tc TC-42 "Get exception by ID" 1 "severity=$SEV" || tc TC-42 "Get exception by ID" 0 "HTTP $CODE"

  G "/api/exceptions/stats"
  STOT=$(jv "total"); SCRIT=$(jv "critical")
  [ "${STOT:-0}" -ge 3 ] 2>/dev/null \
    && tc TC-43 "Exception stats >=3 total" 1 "total=$STOT critical=$SCRIT" \
    || tc TC-43 "Exception stats >=3 total" 0 "total=$STOT"

  P "/api/exceptions/$EXC1/resolve" "{}"
  [ "$CODE" = "200" ] && tc TC-44 "Resolve exception" 1 "HTTP 200" || tc TC-44 "Resolve exception" 0 "HTTP $CODE $BODY"

  G "/api/exceptions/$EXC1"
  RESOLVED=$(jv "resolved")
  [ "$RESOLVED" = "True" ] \
    && tc TC-45 "Resolved exception has resolved=true" 1 "resolved=true" \
    || tc TC-45 "Resolved exception has resolved=true" 0 "resolved=$RESOLVED"
else
  for i in TC-42 TC-43 TC-44 TC-45; do tc $i "Exception sub-test" 0 "no EXC1"; done
fi

G "/api/exceptions?resolved=false"
[ "$CODE" = "200" ] && tc TC-46 "Filter exceptions (unresolved only)" 1 "HTTP 200 total=$(jv total)" || tc TC-46 "Filter exceptions" 0 "HTTP $CODE"

# ── BLOCK 7: DASHBOARD ─────────────────────────────────────────────
declare -A DASH_NAMES
DASH_NAMES["summary"]="Summary overview"
DASH_NAMES["shipments-over-time?days=30"]="Shipments over time (30d)"
DASH_NAMES["approval-status"]="Approval status chart"
DASH_NAMES["exception-trend?days=14"]="Exception trend (14d)"
DASH_NAMES["category-breakdown"]="Category breakdown chart"
DASH_NAMES["recent-activity"]="Recent activity feed"

TC_NUM=47
for ep in "summary" "shipments-over-time?days=30" "approval-status" "exception-trend?days=14" "category-breakdown" "recent-activity"; do
  G "/api/dashboard/$ep"
  TCID="TC-$(printf '%02d' $TC_NUM)"
  NAME="${DASH_NAMES[$ep]}"
  [ "$CODE" = "200" ] && tc "$TCID" "Dashboard: $NAME" 1 "HTTP 200" || tc "$TCID" "Dashboard: $NAME" 0 "HTTP $CODE"
  ((TC_NUM++))
done

# ── BLOCK 8: AI AGENTS ─────────────────────────────────────────────
G "/api/agents/status"
[ "$CODE" = "200" ] && tc TC-53 "Agents status endpoint" 1 "HTTP 200" || tc TC-53 "Agents status endpoint" 0 "HTTP $CODE"

P "/api/agents/rag-query" \
  "{\"query\":\"supply chain delays\",\"collections\":[\"supply_chain\"]}"
[ "$CODE" = "200" ] \
  && tc TC-54 "RAG query agent" 1 "HTTP 200" \
  || tc TC-54 "RAG query agent" 0 "HTTP $CODE | ${BODY:0:120}"

P "/api/agents/extract" \
  "{\"file_path\":\"\",\"raw_text\":\"Invoice INV-001 Vendor: ACME Amount: 5000 Date: 2024-01-15\"}"
[ "$CODE" = "200" ] \
  && tc TC-55 "Document extraction agent" 1 "HTTP 200" \
  || tc TC-55 "Document extraction agent" 0 "HTTP $CODE | ${BODY:0:120}"

P "/api/agents/validate" \
  "{\"extracted_data\":{\"invoice_number\":\"INV-001\",\"vendor\":\"ACME\",\"amount\":5000}}"
[ "$CODE" = "200" ] \
  && tc TC-56 "Validation agent" 1 "HTTP 200" \
  || tc TC-56 "Validation agent" 0 "HTTP $CODE | ${BODY:0:120}"

P "/api/agents/detect-exception" \
  "{\"transaction_data\":{\"amount\":999999,\"vendor\":\"unknown\",\"frequency\":50}}"
[ "$CODE" = "200" ] \
  && tc TC-57 "Exception detection agent" 1 "HTTP 200" \
  || tc TC-57 "Exception detection agent" 0 "HTTP $CODE | ${BODY:0:120}"

# ── BLOCK 9: SECURITY & EDGE CASES ────────────────────────────────
do_req "$BASE/api/workflows"
[[ "$CODE" = "401" || "$CODE" = "403" ]] \
  && tc TC-58 "No-auth on protected route blocked" 1 "HTTP $CODE" \
  || tc TC-58 "No-auth on protected route blocked" 0 "HTTP $CODE (expected 401/403)"

do_req "$BASE/api/dashboard/summary"
[[ "$CODE" = "401" || "$CODE" = "403" ]] \
  && tc TC-59 "No-auth on dashboard blocked" 1 "HTTP $CODE" \
  || tc TC-59 "No-auth on dashboard blocked" 0 "HTTP $CODE"

do_req "$BASE/api/does_not_exist_xyz"
[ "$CODE" = "404" ] && tc TC-60 "Unknown route → 404" 1 "HTTP 404" || tc TC-60 "Unknown route → 404" 0 "HTTP $CODE"

if [ -n "$WF_ID" ] && [ "$WF_ID" != "None" ] && [ "$WF_ID" != "" ]; then
  DEL "/api/workflows/$WF_ID"
  [ "$CODE" = "200" ] && tc TC-61 "Delete workflow" 1 "HTTP 200" || tc TC-61 "Delete workflow" 0 "HTTP $CODE"
else
  tc TC-61 "Delete workflow" 0 "no WF_ID"
fi

rm -f "$TMPB"

# ══════════════════════════════════════════════════════════════════
# FINAL REPORT
# ══════════════════════════════════════════════════════════════════
TOTAL=$((PASS+FAIL))
SCORE=$(echo "scale=0; $PASS * 100 / $TOTAL" | bc 2>/dev/null || echo "N/A")

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║          NOVA PLATFORM — COMPLETE TEST RESULTS              ║"
echo "╠══════════════════════════════════════════════════════════════╣"
printf "║  Total: %-3s  |  PASSED: %-3s  |  FAILED: %-3s  |  %s%%        ║\n" \
  "$TOTAL" "$PASS" "$FAIL" "$SCORE"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

print_block() {
  local bname="$1"; shift; local ids=("$@")
  local bp=0
  for id in "${ids[@]}"; do [ "${RESULT[$id]}" = "PASS" ] && ((bp++)); done
  echo "━━━ $bname  ($bp/${#ids[@]} passed) ━━━"
  for id in "${ids[@]}"; do
    local st="${RESULT[$id]:-SKIP}"
    local nm="${DETAIL[$id]%%|||*}"
    local dt="${DETAIL[$id]##*|||}"
    if [ "$st" = "PASS" ]; then
      printf "  ✅ %-8s %s\n" "$id" "$nm"
    else
      printf "  ❌ %-8s %s\n" "$id" "$nm"
      [ -n "$dt" ] && printf "             └─ %s\n" "$dt"
    fi
  done
  echo ""
}

print_block "BLOCK 1 — SERVER HEALTH (3)" \
  TC-01 TC-02 TC-03
print_block "BLOCK 2 — AUTHENTICATION (9)" \
  TC-04 TC-05 TC-06 TC-07 TC-08 TC-09 TC-10 TC-11 TC-12
print_block "BLOCK 3 — WORKFLOWS (10)" \
  TC-13 TC-14 TC-15 TC-16 TC-17 TC-18 TC-19 TC-20 TC-21 TC-22
print_block "BLOCK 4 — DOCUMENTS (5)" \
  TC-23 TC-24 TC-25 TC-26 TC-27
print_block "BLOCK 5 — APPROVALS (9)" \
  TC-28 TC-29 TC-30 TC-31 TC-32 TC-33 TC-34 TC-35 TC-36
print_block "BLOCK 6 — EXCEPTIONS (10)" \
  TC-37 TC-38 TC-39 TC-40 TC-41 TC-42 TC-43 TC-44 TC-45 TC-46
print_block "BLOCK 7 — DASHBOARD (6)" \
  TC-47 TC-48 TC-49 TC-50 TC-51 TC-52
print_block "BLOCK 8 — AI AGENTS (5)" \
  TC-53 TC-54 TC-55 TC-56 TC-57
print_block "BLOCK 9 — SECURITY & EDGE CASES (4)" \
  TC-58 TC-59 TC-60 TC-61

echo "━━━ FAILED TESTS ━━━"
ANY=0
for id in $(echo "${!RESULT[@]}" | tr ' ' '\n' | sort -V); do
  if [ "${RESULT[$id]}" = "FAIL" ]; then
    ANY=1
    nm="${DETAIL[$id]%%|||*}"; dt="${DETAIL[$id]##*|||}"
    printf "  ❌ %-8s %s\n" "$id" "$nm"
    [ -n "$dt" ] && printf "             Reason: %s\n" "$dt"
  fi
done
[ "$ANY" = "0" ] && echo "  All tests passed!"
echo ""
echo "Done."
