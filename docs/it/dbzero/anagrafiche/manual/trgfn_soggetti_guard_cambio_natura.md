## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_soggetti_guard_cambio_natura`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti) — la tabella su cui è montato
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_check_cambio_natura_soggetto](/dbzero/anagrafiche/funzioni/fn_check_cambio_natura_soggetto) — la regola dei motivi
> * [script.fn_raise_primo_motivo_se_presente](/dbzero/script/funzioni/fn_raise_primo_motivo_se_presente) — solleva il primo motivo, con l'elenco intero nel contesto
> * [anagrafiche.fn_nature_proponibili_soggetto](/dbzero/anagrafiche/funzioni/fn_nature_proponibili_soggetto) — il picker, che legge la stessa regola

---

### 🎯 Scopo Principale

`anagrafiche.trgfn_soggetti_guard_cambio_natura` rifiuta il cambio di natura di un soggetto quando la regola
del cambio ha anche un solo motivo, e solleva il primo. Non decide niente da sé: i motivi li calcola
`anagrafiche.fn_check_cambio_natura_soggetto`.

---

### Quando scatta

Prima di ogni UPDATE di `anagrafiche.soggetti` in cui la natura di dettaglio cambia davvero; un salvataggio
che la riscrive uguale non lo fa scattare. Nella nascita del soggetto non c'è un cambio, e il guard non
c'è.

Per nome viene **prima** degli altri guard immediati della tabella (codice fiscale e partita IVA, identità
fiscale, regime PA, sesso): il motivo del cambio di natura parla per primo, e un'altra macro-tipologia si
rifiuta come tale anche quando la riga avrebbe pure un altro difetto.

---

### I valori della riga che si sta salvando

La regola riceve la natura nuova e, della riga, la partita IVA e i due flag del regime PA **proposti**. Chi
nello stesso salvataggio porta un flag a `N` o svuota la partita IVA non ha quel motivo. Svuotare una partita
IVA già scritta resta però del SUPER_ADMIN: per gli altri lo rifiuta il guard dell'identità fiscale.

Il rifiuto porta il codice del primo motivo, il campo da evidenziare (la natura, o la partita IVA e i flag
quando il motivo è loro) e, nel contesto, l'elenco di **tutti** i motivi, perché l'applicazione li mostri
insieme. Il guard non cambia la riga.

---

{% include-markdown "it/dbzero/anagrafiche/_cambio-di-natura.md" %}

---

### ⚠️ Che cosa oggi non copre

* **Il passaggio per la natura vuota.** Il guard scatta a ogni cambio, ma la regola non guarda né la
  macro-tipologia né i documenti quando la natura di partenza è vuota: un soggetto portato prima a nessuna
  natura e poi a una natura di un'altra famiglia passa i due controlli che dovrebbero essere definitivi.

---

### Codici errore

Il guard solleva il primo dei codici della regola, elencati nel blocco qui sopra. Il testo sta in
`config.messaggi_errore`.

---

### Test

* `db/pgtap/anagrafiche/test-cambio-natura-soggetto-v1.sql` — il montaggio (prima dell'UPDATE, solo quando
  la natura cambia), il guard che parla per primo fra i guard della tabella, il rifiuto con la frase
  dell'altra macro-tipologia e con quella dei documenti.
* `db/pgtap/script/test-rubinetto-primo-motivo-v1.sql` — il passaggio del primo motivo, comune a tutti i guard
  che sollevano da una check.
* `db/pgtap/anagrafiche/test-fornitore-privato-indirizzi-v1.sql` — il rifiuto per gli indirizzi del ruolo.

---

### Note di migrazione

* 2026-11-14 — nasce insieme alla regola dei motivi e ne prende il posto il guard dei titoli IVA al cambio,
  ritirato. Il divieto di cambiare macro-tipologia, che stava nel solo backend, passa al database per ogni
  strada.

---

{% include-markdown "signature-core.md" %}
