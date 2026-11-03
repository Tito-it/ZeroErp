## 📘 Documentazione Concettuale – Funzione `dbops.fn_pgtap_crea_roster_processo`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento viste:
>
> * [dbops.vw_processi_roster](/dbzero/dbops/views/vw_processi_roster) — il roster in cui la coppia deve comparire
>
> Approfondimento funzioni:
>
> * [dbops.fn_pgtap_crea_emittente_operatore](/dbzero/dbops/funzioni/fn_pgtap_crea_emittente_operatore) — la fixture che fa tutto il lavoro
> * [script.fn_crea_utente_tecnico](/dbzero/script/funzioni/fn_crea_utente_tecnico) — il percorso di produzione dell'utente tecnico
>
> Guide:
>
> * [Come si scrive un test pgTAP](/guide/pgtap-come-si-scrive-un-test) — l'elenco delle fixture

---

### 🎯 Scopo Principale

Dà a un test una coppia (processo, azienda) che compare davvero nel roster dei processi:
crea un'azienda e le aggancia l'utente tecnico del processo indicato. Restituisce l'azienda
(id, sigla, soggetto ruolo) e l'utente tecnico (credenziale e identità).

---

### ⭐ Un caso di fn_pgtap_crea_emittente_operatore

Il lavoro lo fa [fn_pgtap_crea_emittente_operatore](/dbzero/dbops/funzioni/fn_pgtap_crea_emittente_operatore),
che ha già il processo come parametro. Qui il processo è il **soggetto** del test, non un
dettaglio con un default: per questo è obbligatorio, e una chiamata senza processo è
rifiutata prima di costruire. La sigla dell'azienda è facoltativa.

⚠️ Pretende le tabelle delle credenziali di Django, che non nascono da Liquibase ma dalle
migrazioni di Django.

---

### Codici errore

Un processo mancante o vuoto è un'eccezione senza codice, sollevata dalla fixture. Gli altri
rifiuti sono quelli di [fn_pgtap_crea_emittente_operatore](/dbzero/dbops/funzioni/fn_pgtap_crea_emittente_operatore),
per esempio un processo che non ammette un utente tecnico.

---

### Test

Nessun pgTAP dedicato: la usano i test del roster e del perimetro dei processi, per esempio
`db/pgtap/dbops/test-vw-processi-roster.sql` e `db/pgtap/script/test-fn-scope-identita-processo.sql`.

---

### Note di migrazione

* 2026-09-09 — nasce; lo stesso giorno il corpo, identico a quello della fixture
  dell'emittente con l'operatore tranne il processo, passa a chiamarla.

---

{% include-markdown "it/dbzero/dbops/_fixture-pgtap.md" %}

---

{% include-markdown "signature-core.md" %}
