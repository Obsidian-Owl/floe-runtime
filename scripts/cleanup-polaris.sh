#!/bin/bash
# cleanup-polaris.sh - Clean Polaris catalog metadata before fresh deployment
#
# This script removes all catalog metadata to prevent stale state issues.

set -e

echo "🧹 Cleaning Polaris catalog metadata..."

# Get Polaris pod
POLARIS_POD=$(kubectl get pods -n floe -l app.kubernetes.io/component=polaris -o name 2>/dev/null | head -1)

if [ -z "$POLARIS_POD" ]; then
    echo "⚠️  Polaris pod not found - skipping catalog cleanup"
    exit 0
fi

echo "  Getting OAuth token..."
TOKEN=$(kubectl exec -n floe "$POLARIS_POD" -- python3 -c "
import urllib.request, json
url = 'http://localhost:8181/api/catalog/v1/oauth/tokens'
data = 'grant_type=client_credentials&client_id=demo_client&client_secret=demo_secret_k8s&scope=PRINCIPAL_ROLE:ALL'.encode()
req = urllib.request.Request(url, data=data, method='POST')
req.add_header('Content-Type', 'application/x-www-form-urlencoded')
try:
    with urllib.request.urlopen(req) as resp:
        print(json.loads(resp.read().decode())['access_token'])
except:
    pass
" 2>/dev/null)

if [ -z "$TOKEN" ]; then
    echo "⚠️  Could not get OAuth token - skipping catalog cleanup"
    exit 0
fi

echo "  Deleting all tables and namespaces..."
kubectl exec -n floe "$POLARIS_POD" -- python3 -c "
import urllib.request, json

TOKEN = '$TOKEN'

def api_request(method, path):
    url = f'http://localhost:8181{path}'
    req = urllib.request.Request(url, method=method)
    req.add_header('Authorization', f'Bearer {TOKEN}')
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode()) if resp.read() else {}
    except Exception as e:
        return None

# List all namespaces
namespaces_resp = api_request('GET', '/api/catalog/v1/demo_catalog/namespaces')
if namespaces_resp and 'namespaces' in namespaces_resp:
    for ns in namespaces_resp['namespaces']:
        ns_name = '.'.join(ns)
        print(f'Deleting namespace: {ns_name}')

        # Delete all tables in namespace
        tables_resp = api_request('GET', f'/api/catalog/v1/demo_catalog/namespaces/{ns_name}/tables')
        if tables_resp and 'identifiers' in tables_resp:
            for table in tables_resp['identifiers']:
                table_name = table['name']
                api_request('DELETE', f'/api/catalog/v1/demo_catalog/namespaces/{ns_name}/tables/{table_name}')
                print(f'  Deleted table: {ns_name}.{table_name}')

        # Delete namespace
        api_request('DELETE', f'/api/catalog/v1/demo_catalog/namespaces/{ns_name}')

print('Polaris catalog cleaned')
" 2>/dev/null || echo "⚠️  Catalog cleanup failed (continuing anyway)"

echo "✅ Polaris catalog metadata cleaned"
