## 📘 Documentazione Funzione – `pratiche.trgfn_tfhe_guard_no_proiezione`

> 👀 **Vedi anche**
>
Funzioni / oggetti collegati:
>
> [pratiche.template_flussi_handler_eventi](/dbzero/pratiche/tabelle/template_flussi_handler_eventi)
> [pratiche.template_flussi_avanzamento_proiezione](/dbzero/pratiche/tabelle/template_flussi_avanzamento_proiezione)
> [pratiche.trgfn_tfap_guard_compatibilita](/dbzero/pratiche/funzioni/trgfn_tfap_guard_compatibilita)

---
### 🎯 Scopo Principale
(review 06-07-2026 — GUIDA D4, brief-db-guida-avanza-esito-proiettato)

Guard **config-time** (`BEFORE INSERT OR UPDATE` su
`pratiche.template_flussi_handler_eventi`) — **lato simmetrico** della mutua-esclusione
GUIDA (D-B10). Vieta di aggiungere/attivare un handler_eventi con `evento='COMPLETATO'`
**attivo** su uno step che ha **già** un binding di avanzamento su proiezione **attivo**.

Insieme a `pratiche.trgfn_tfap_guard_compatibilita` (che presidia il lato del binding),
garantisce che uno step sia **o** projection-driven **o** handler-driven sul COMPLETATO, mai
entrambi: altrimenti l'avanzamento standalone (DB, best-effort) completerebbe il flusso
**saltando** l'handler Python, perdendo l'azione di dominio in silenzio.

---

### Note operative

* Scatta **solo** per `NEW.evento = 'COMPLETATO' AND NEW.attivo`, e solo se esiste un binding
  di avanzamento **attivo** per lo stesso step: un handler disattivato o su altro evento
  (`IN_CORSO`) non è in conflitto.
* Errore `TEMPLATE_FLUSSO_PROIEZIONE_CONFLITTO_HANDLER` (518) via
  `script.fn_log_and_raise_error`.

---

{% include-markdown "signature-core.md" %}
