## 📘 Documentazione Concettuale – Funzione `dbops.fn_apply_automazione_guard_utility_tipo_ruolo`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.automazione_guard_utility_tipo_ruolo](/dbzero/dbops/tabelle/automazione_guard_utility_tipo_ruolo) — il catalogo delle tabelle da proteggere
>
> Approfondimento funzioni:
>
> * [dbops.fn_run_automations_guard_utility](/dbzero/dbops/funzioni/fn_run_automations_guard_utility) — il runner che fa il lavoro
> * [dbops.fn_seed_automazione_guard_utility_tipo_ruolo](/dbzero/dbops/funzioni/fn_seed_automazione_guard_utility_tipo_ruolo) — la diagnosi che la precede nel primo giro di `ci_apply`
> * [script.trgfn_guard_utility_tipo_ruolo_by_cols](/dbzero/script/funzioni/trgfn_guard_utility_tipo_ruolo_by_cols) — la funzione trigger che il runner monta
>
> Guide:
>
> * [Framework di automazione DB](/guide/automazione-db) — l'automazione GUARD utility/tipo ruolo fra le altre
> * [Linee guida Trigger](/linee-guida-trigger#i-trigger-generati) — le regole dei trigger generati

---

### 🎯 Scopo Principale

La **porta storica** del guard **utility → tipo ruolo**: chiama
[fn_run_automations_guard_utility](/dbzero/dbops/funzioni/fn_run_automations_guard_utility) con
il modo e la simulazione che riceve, su tutto l'ambito. Non contiene una seconda copia della
regola: che cosa si crea, si rigenera o si toglie lo decide il runner.

---

### Perché resta

La chiama ancora il primo giro di `ci_apply`, in modo `CI`, subito dopo la diagnosi del catalogo:
quel changeSet è storico e non si riscrive. Il giro programmato e la convergenza del rilascio
passano invece dal processo `automations_guard_utility`, che chiama il runner direttamente.

---

### Codici errore

Quelli del runner: `E_GUARD_UTILITY`, per un guard su una tabella che il registro non nomina o per
un DDL fallito. Il codice del dominio, `E_UTILITY_RUOLO_NON_AMMESSO`, lo solleva il guard montato
sulle scritture delle tabelle protette.

---

### Test

* `db/pgtap/dbops/test-guard-utility-convergenza-v1.sql` — la porta storica fa lo stesso lavoro
  del runner.
* `db/pgtap/dbops/test-automazione-guard-utility-tipo-ruolo.sql` — su
  `anagrafiche.emittenti_fiscali_utilities` c'è un trigger con la funzione del guard, `BEFORE` su
  `INSERT` e `UPDATE`.

---

### Note di migrazione

* 2026-02-16 — nasce, con il catalogo e la funzione trigger generica per colonne.
* 2026-11-08 — diventa una porta verso il runner `fn_run_automations_guard_utility`
  (`20261110-02`, `brief-db-revisione-dbops`, giro 10c). Prima montava il guard da sé: ricreava a
  ogni giro il trigger col nome di oggi, lasciava i guard con un altro nome e quelli delle righe
  spente, scartava in silenzio la colonna `soggetto_ruolo_id` senza prefisso, e il dry run non
  scriveva niente.

---

{% include-markdown "signature-core.md" %}
