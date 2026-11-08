## 📘 Documentazione Concettuale – Trigger function `pratiche.trgfn_calcoli_tempo_set_periodo`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pratiche.calcoli_tempo](/dbzero/pratiche/tabelle/calcoli_tempo) — la tabella su cui è montata
>
> Approfondimento funzioni:
>
> * [pratiche.trgfn_sospensioni_set_periodo](/dbzero/pratiche/funzioni/trgfn_sospensioni_set_periodo) — il gemello sulle sospensioni

---

### 🎯 Scopo Principale

`pratiche.trgfn_calcoli_tempo_set_periodo` mantiene `periodo_calcolo` come proiezione derivata di
`data_inizio_calcolo` e `data_fine_calcolo`: le date sono la sorgente di verità, il range è la
superficie su cui PostgreSQL ragiona per contenimento e sovrapposizione.

Serve alla domanda ricorrente del dominio pratiche, «quanto tempo è passato fra due fasi, al netto
delle sospensioni», che con due colonne separate chiederebbe confronti a mano in ogni query. È il gemello
di `pratiche.trgfn_sospensioni_set_periodo`: stessa forma, stessa convenzione degli estremi.

---

### Le regole

* Il range va da `data_inizio_calcolo` (obbligatoria, quindi l'estremo inferiore c'è sempre) a
  `data_fine_calcolo`, inizio incluso e fine esclusa, come per le sospensioni.
* `data_fine_calcolo` vuota vuol dire calcolo ancora in corso: il range è aperto verso l'infinito.
* Il valore passato dal chiamante in `periodo_calcolo` viene sovrascritto.

È montata `BEFORE INSERT OR UPDATE OF data_inizio_calcolo, data_fine_calcolo`, riga per riga, nella
fase `_a20_`.

---

### ⚠️ Differenza dal gemello: qui non c'è anti-sovrapposizione

Su `pratiche.sospensioni` il range alimenta un vincolo di esclusione. Su `pratiche.calcoli_tempo` un
vincolo analogo non c'è: l'unicità è per chiave logica (pratica, flusso di partenza, flusso di arrivo,
formula). Due calcoli sulla stessa pratica possono avere periodi sovrapposti, purché differiscano per
coppia di flussi o per formula.

---

### ⚠️ Date incoerenti: parla il trigger, non il CHECK

Il trigger `BEFORE` gira prima dei CHECK di tabella:

* con la fine **prima** dell'inizio è il costruttore del range a fallire, con l'errore interno di
  PostgreSQL sui range (SQLSTATE `22000`): non nomina il calcolo né le date, e non porta a
  `chk_calcoli_tempo_data_fine`, che sembrerebbe il colpevole naturale;
* con la fine **uguale** all'inizio il range si costruisce, e a rifiutare la riga è
  `chk_calcoli_tempo_data_fine`, che chiede la fine strettamente successiva.

---

### ⚠️ L'aggiornamento della sola colonna derivata non risincronizza

Il trigger scatta solo quando cambiano le date: scrivere direttamente `periodo_calcolo` lo lascia
divergere dalle date, in silenzio. In bonifica si aggiornano le date.

---

### Codici errore

Nessuno di dominio: la funzione non chiama `script.fn_log_and_raise_error`.

---

### Note di migrazione

* 2026-04-12 — nasce `periodo_calcolo` con il trigger che lo deriva dalle date.

---

{% include-markdown "signature-core.md" %}
