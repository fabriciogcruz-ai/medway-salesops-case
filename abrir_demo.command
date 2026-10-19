#!/bin/zsh
# Abre a prévia local do case Medway. Dados brutos e token ficam em input/ (ignorado pelo Git).
set -eu
cd "$(dirname "$0")"
if [[ ! -f input/b2c-demo.csv ]]; then
  print 'CSV de demonstração ausente: input/b2c-demo.csv'
  print 'Copie a exportação fornecida para esta pasta privada antes de continuar.'
  exit 1
fi
document="$HOME/Documents/b2c-demo.numbers"
if [[ ! -f "$document" ]]; then
  print "Documento Numbers não encontrado: $document"
  exit 1
fi
open -a Numbers "$document"
python3 numbers_bridge.py --once || {
  print 'Não foi possível validar a exportação do Numbers. O painel mantém o último CSV válido.'
  exit 1
}
server_pid=''
if ! /usr/bin/curl -fsS --max-time 2 http://127.0.0.1:8791/api/local-status >/dev/null 2>&1; then
  python3 demo_local.py --port 8791 &
  server_pid=$!
fi
trap '[[ -n "$server_pid" ]] && kill "$server_pid" 2>/dev/null || true; [[ -n "${bridge_pid:-}" ]] && kill "$bridge_pid" 2>/dev/null || true' EXIT
python3 numbers_bridge.py &
bridge_pid=$!
for attempt in {1..30}; do
  if /usr/bin/curl -fsS --max-time 1 http://127.0.0.1:8791/api/local-status >/dev/null 2>&1; then
    open http://127.0.0.1:8791/
    print 'Prévia local ativa. Salve no Numbers para atualizar; mantenha esta janela aberta.'
    wait "$bridge_pid"
    exit $?
  fi
  sleep 0.3
done
print 'O servidor local não iniciou. Verifique a mensagem de erro acima.'
exit 1
