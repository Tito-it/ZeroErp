## 📘 Documentazione Concettuale – Funzione `dbops.fn_apply_automazione_guard_utility_tipo_ruolo`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.automazione_guard_utility_tipo_ruolo](/dbzero/dbops/tabelle/automazione_guard_utility_tipo_ruolo) — il catalogo delle tabelle da proteggere
>
> Approfondimento funzioni:
>
> * [script.trgfn_guard_utility_tipo_ruolo_by_cols](/dbzero/script/funzioni/trgfn_guard_utility_tipo_ruolo_by_cols) — la funzione trigger che monta
> * [script.fn_guard_utility_tipo_ruolo](/dbzero/script/funzioni/fn_guard_utility_tipo_ruolo) — la regola che il trigger applica
> * [dbops.fn_seed_automazione_guard_utility_tipo_ruolo](/dbzero/dbops/funzioni/fn_seed_automazione_guard_utility_tipo_ruolo) — la diagnosi che la precede nello stesso passo
> * [dbops.fn_name_from_template](/dbzero/dbops/funzioni/fn_name_from_template) — il nome del trigger dal template, con il troncamento a 63 caratteri
>
> Guide:
>
> * [Framework di automazione DB](/guide/automazione-db) — l'automazione GUARD utility/tipo ruolo fra le altre
> * [Linee guida Trigger](/linee-guida-trigger#i-trigger-generati) — le regole dei trigger generati

---

### 🎯 Scopo Principale

Monta il guard **utility → tipo ruolo** sulle tabelle accese di
`dbops.automazione_guard_utility_tipo_ruolo`: un trigger `BEFORE INSERT OR UPDATE OF` delle due
colonne della riga, che esegue `script.trgfn_guard_utility_tipo_ruolo_by_cols` con i loro nomi
come argomenti.

La chiama soltanto la passata `ci_apply` del rilascio, in modo `CI`, subito dopo la diagnosi del
catalogo. Non ha un giro a orario.

---

### Quali righe monta

Le righe con `enabled` vero, il cui `exec_mode` è `AUTO` o coincide (senza badare a maiuscole e
spazi) con il modo della chiamata, e la cui colonna del ruolo ha la forma
`<prefisso>_soggetto_ruolo_id`. Una riga che nomina una colonna che la tabella non ha si salta.

⚠️ Tutti gli scarti sono **muti**: una colonna senza prefisso, una colonna inesistente, una riga
spenta non lasciano traccia, né nell'audit né in un avviso. La funzione non scrive in
`dbops.audit_log`.

---

### ⭐ Ricrea sempre, a ogni giro

Per ogni riga montabile la funzione toglie il trigger con quel nome, se c'è, e lo crea di nuovo:
non controlla se esiste già. Il risultato converge sempre alla forma del catalogo, ma ogni giro fa
DDL su ogni tabella accesa.

* Il nome è `trigger_name` della riga, o il template `trg_<tabella>_a10_guard_utility_tipo_ruolo_ins_upd`,
  troncato con un hash oltre i 63 caratteri.
* ⚠️ Toglie solo il trigger con il nome di **oggi**: un trigger montato con un nome diverso (un
  `trigger_name` cambiato, un template cambiato) resta, e la tabella si trova due guard uguali.
* ⚠️ Una riga **spenta** non viene guardata: il guard che aveva montato quando era accesa resta
  sulla tabella. Spegnere una riga non toglie la protezione.

---

### ⚠️ Il dry run non fa niente

Con `p_dry_run` vero la funzione percorre le righe e non crea niente, ma non dice nemmeno che cosa
creerebbe: non scrive audit né avvisi.

---

### Codici errore

La funzione non solleva codici suoi: un errore del DDL esce con lo SQLSTATE di PostgreSQL. Il
codice del dominio, `E_UTILITY_RUOLO_NON_AMMESSO`, lo solleva il guard montato, sulle scritture
delle tabelle protette.

---

### Test

* `db/pgtap/dbops/test-automazione-guard-utility-tipo-ruolo.sql` — l'apply monta su
  `anagrafiche.emittenti_fiscali_utilities` un trigger con la funzione del guard, `BEFORE` su
  `INSERT` e `UPDATE`.

---

### Note di migrazione

* 2026-02-16 — nasce, con il catalogo e la funzione trigger generica per colonne.

---

{% include-markdown "signature-core.md" %}
