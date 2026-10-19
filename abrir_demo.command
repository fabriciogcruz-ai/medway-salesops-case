#!/bin/zsh
# Abre a prévia local do case Medway. Dados brutos e token ficam em input/ (ignorado pelo Git).
set -eu
cd "$(dirname "$0")"
if [[ ! -f input/b2c-demo.csv ]]; then
  print 'CSV de demonstração ausente: input/b2c-demo.csv'
  print 'Copie a exportação fornecida para esta pasta privada antes de continuar.'
  exit 1
fi
if /usr/bin/curl -fsS --max-time 2 http://127.0.0.1:8791/api/local-status >/dev/null 2>&1; then
  open input/b2c-demo.csv
  open http://127.0.0.1:8791/
  print 'Prévia local já estava ativa.'
  exit 0
fi
python3 demo_local.py --port 8791 &
server_pid=$!
trap 'kill "$server_pid" 2>/dev/null || true' EXIT
for attempt in {1..30}; do
  if /usr/bin/curl -fsS --max-time 1 http://127.0.0.1:8791/api/local-status >/dev/null 2>&1; then
    open input/b2c-demo.csv
    open http://127.0.0.1:8791/
    print 'Prévia local ativa. Deixe esta janela aberta durante a demonstração.'
    wait "$server_pid"
    exit $?
  fi
  sleep 0.3
done
print 'O servidor local não iniciou. Verifique a mensagem de erro acima.'
wait "$server_pid"
