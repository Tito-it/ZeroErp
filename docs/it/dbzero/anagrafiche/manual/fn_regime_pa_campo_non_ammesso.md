## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_regime_pa_campo_non_ammesso`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [config.tipi_soggetto_dettaglio](/dbzero/config/tabelle/tipi_soggetto_dettaglio) — la natura, con `cliente_pa_ammesso` e `split_payment_ammesso`
> * [anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti) — i due flag del regime
>
> Approfondimento funzioni:
>
> * [anagrafiche.trgfn_soggetti_guard_regime_pa](/dbzero/anagrafiche/funzioni/trgfn_soggetti_guard_regime_pa) — il guard che la chiede a ogni scrittura
> * [anagrafiche.fn_check_cambio_natura_soggetto](/dbzero/anagrafiche/funzioni/fn_check_cambio_natura_soggetto) — il cambio di natura, che la chiede flag per flag

---

### 🎯 Scopo Principale

`anagrafiche.fn_regime_pa_campo_non_ammesso` dice quale dei due flag del regime (`cliente_pa`, `split_payment`)
una natura non ammette, dati la natura e i due valori: restituisce il nome del flag, o niente se la natura li
ammette entrambi.

---

### Una regola, due lettori

Un flag è fuori regola quando vale `S` e la natura non lo ammette. La regola sta qui perché la leggono in due, e
devono dire la stessa cosa:

* il guard `anagrafiche.trgfn_soggetti_guard_regime_pa`, a ogni scrittura che tocca i flag o la natura;
* `anagrafiche.fn_check_cambio_natura_soggetto`, che elenca i motivi per cui un cambio di natura è rifiutato.

La risposta è un nome solo: con tutti e due i flag fuori regola vince `cliente_pa`. Chi vuole sapere di ogni flag
la chiede due volte, passando `N` all'altro: è ciò che fa il controllo del cambio di natura, che ha un motivo per
flag.

---

### Che cosa non giudica

* **Senza natura**, o con una natura che non esiste, non c'è niente da leggere, e la risposta è vuota: il rifiuto
  del flag senza natura è del guard.
* **Il valore** dei flag (`S` o `N`) lo dicono i vincoli della tabella, non questa funzione.

---

### Codici errore

Nessuno: risponde col nome del flag o con niente. I rifiuti li sollevano i suoi lettori.

---

### Test

* `db/pgtap/anagrafiche/test-soggetti-regime-pa-v1.sql` — il guard che la chiede: le nature che ammettono i
  flag, i rifiuti col campo giusto, l'ente PA che cambia natura (rifiutato, e ammesso col flag riportato a `N`).
  La funzione non ha un test suo che la chiami direttamente.

---

### Note di migrazione

* 2026-11-14 — nasce col cambio di natura del soggetto, per dare al guard e al controllo del cambio la stessa
  regola.

---

{% include-markdown "signature-core.md" %}
