## 📘 Documentazione Concettuale – Funzione `dbops.fn_cleanup_at_params`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.automation_rules_tbl](/dbzero/dbops/tabelle/automation_rules_tbl) — il registro da cui legge la regola
>
> Approfondimento funzioni:
>
> * [dbops.trgfn_cleanup_at_alla_nascita](/dbzero/dbops/funzioni/trgfn_cleanup_at_alla_nascita) — il trigger che scrive la scadenza all'INSERT, il lettore principale
> * [script.fn_registra_tentativo_login](/dbzero/script/funzioni/fn_registra_tentativo_login) — ricalcola la scadenza dei tentativi di login a ogni fallimento
> * [dbops.fn_run_automations_cleanup](/dbzero/dbops/funzioni/fn_run_automations_cleanup) — il job, che legge lo stesso registro per il pregresso
>
> Guide:
>
> * [Audit e tracciabilità](/guide/audit-e-tracciabilita) — §7, manutenzione e retention

---

### 🎯 Scopo Principale

Risponde con quale regola `CLEANUP_AT` scade una tabella: restituisce i parametri (termine in
giorni, colonna di base, colonna di scadenza, ricalcolo) della regola più specifica di
`dbops.automation_rules_tbl` che la copre, o niente se nessuna la copre.

⭐ Esiste perché **il termine sta in una sede sola**: chi scrive la scadenza alla nascita e il job
che la scrive sul pregresso devono leggere lo stesso numero, e lo leggono dal registro.

---

### Quale regola vince

Fra le regole `CLEANUP_AT` abilitate che dichiarano un termine e che coprono schema e tabella
(per nome o con il carattere jolly), vince quella con la priorità più bassa, e a parità di
priorità quella con l'`id` minore. La regola generica su tutte le tabelle ha una priorità più
alta delle regole di tabella, quindi vale solo dove nessuna regola di tabella c'è.

⚠️ La scelta non guarda la modalità di esecuzione della regola, e restituisce i parametri così
come sono scritti, senza controllarli: un termine che non è un numero intero lo scopre chi lo
converte.

⚠️ Il job non sceglie una regola sola: applica, in ordine di priorità, **tutte** le regole che
coprono la tabella. Con le regole che riempiono solo le scadenze vuote il risultato coincide con
questa scelta, perché la prima regola riempie i vuoti e le successive non trovano più niente; una
regola successiva che ricalcola anche le scadenze già scritte darebbe invece al pregresso un
termine diverso da quello delle righe nuove.

---

### Nessuna regola vuol dire «non scade»

La funzione restituisce niente in due casi:

* nessuna regola con un termine copre la tabella;
* schema o tabella sono vuoti.

Il secondo caso non è un errore, di proposito: la funzione è una lettura, chiamata riga per riga
da un trigger, e sollevare con il contratto di progetto scriverebbe una riga di log. Senza quel
ramo la regola generica coprirebbe anche una tabella senza nome, e la risposta sarebbe il termine
di default. Così, invece, «non so di che tabella parli» vale «non scade mai»: in dubbio si
conserva.

---

### Test

* `db/pgtap/vendite/test-registri-fatturazione-scadenza-alla-nascita.sql` — le regole dei
  registri ci sono, una tabella senza regola propria cade sulla generica, schema e tabella vuoti
  restituiscono niente senza errore (test 4-6).
* `db/pgtap/dbops/test-idempotency-prenota-v1.sql` — le chiavi di idempotenza e il registro delle
  richieste nascono con la scadenza della loro regola.
* `db/pgtap/config/test-credenziale-login-v1.sql` — una riga di provenienza nasce con l'ultimo
  fallimento più il termine della sua regola.

---

### Note di migrazione

* 2026-09-18 — nasce generalizzando `vendite.fn_event_log_ttl_days`, che faceva la stessa cosa
  con schema e tabella cablati ed è stata ritirata (passo D di `analisi-osservabilita-log.md`).

---

{% include-markdown "signature-core.md" %}
