#!/usr/bin/env bash
# Scopo: stampare l'indirizzo su cui la documentazione e' DAVVERO raggiungibile.
#
# ⚠️ Esiste perche' i due script di serve legavano interfacce DIVERSE e
#    stampavano lo STESSO messaggio: `serve_docs.sh` lega 127.0.0.1 (solo
#    locale), `serve_docs_static.sh` non passava `--bind` e quindi legava
#    0.0.0.0 (tutte le interfacce). Entrambi dicevano «Serve su
#    http://127.0.0.1:8010».
#    Su una macchina di sviluppo remota quel messaggio manda fuori strada: da
#    un browser 127.0.0.1 e' il PROPRIO computer, non il server — e la
#    documentazione sembra irraggiungibile mentre sta rispondendo.
#
# ⭐ E si punta a `/it/`, non alla radice: la radice e' una paginetta che
#    rimbalza con `meta refresh` + JavaScript, non con un redirect HTTP. Con
#    JS bloccato si resta fermi li' a guardare una pagina vuota.

# Scopo: banner di avvio del server docs.
#   $1 = indirizzo di bind (127.0.0.1 | 0.0.0.0)   $2 = porta
docs_serve_banner() {
  local bind="$1" porta="$2" ip

  echo "=== Documentazione in ascolto su ${bind}:${porta} ==="

  if [ "$bind" = "0.0.0.0" ]; then
    ip="$(hostname -I 2>/dev/null | awk '{print $1}')"
    echo "    dalla macchina stessa : http://127.0.0.1:${porta}/it/"
    if [ -n "$ip" ]; then
      echo "    da un altro computer  : http://${ip}:${porta}/it/   <-- di solito e' questo"
    fi
    echo "    ⚠️  Nota: bind 0.0.0.0 = la documentazione e' esposta su TUTTA la rete locale."
  else
    echo "    dalla macchina stessa : http://${bind}:${porta}/it/"
    echo "    ⚠️  Bind LOCALE: da un altro computer NON si raggiunge."
    echo "        Serve l'inoltro di porta (VS Code: pannello «Ports» -> Forward a Port -> ${porta})."
  fi

  echo "    (Ctrl+C per fermare)"
}
