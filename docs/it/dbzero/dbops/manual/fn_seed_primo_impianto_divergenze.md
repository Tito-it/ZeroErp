## 📘 Documentazione Concettuale – Funzione `dbops.fn_seed_primo_impianto_divergenze`

> **Ultimo aggiornamento**: 18 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento funzioni:
>
> * [dbops.fn_run_automations_seed_primo_impianto](/dbzero/dbops/funzioni/fn_run_automations_seed_primo_impianto) — chiamante: il giro che corregge ciò che diverge
> * [dbops.fn_seed_primo_impianto_argomenti](/dbzero/dbops/funzioni/fn_seed_primo_impianto_argomenti) — la grammatica con cui confronta gli argomenti
> * [dbops.fn_delete_block_divergenze](/dbzero/dbops/funzioni/fn_delete_block_divergenze) — lo stesso confronto, per i blocchi delle cancellazioni
>
> Approfondimento tabelle:
>
> * [dbops.automazione_seed_primo_impianto](/dbzero/dbops/tabelle/automazione_seed_primo_impianto) — lo stato atteso

---

### 🎯 Scopo Principale

Confronta il trigger del seed di primo impianto **atteso**, quello che
[automazione_seed_primo_impianto](/dbzero/dbops/tabelle/automazione_seed_primo_impianto) dichiara,
con quello **vivo**. Restituisce una riga per ogni tabella dell'ambito che diverge; nessuna riga
vuol dire che tutto è allineato.

Il trigger vivo si riconosce dalla funzione che esegue,
[trgfn_seed_primo_impianto](/dbzero/script/funzioni/trgfn_seed_primo_impianto), non dal nome.

---

### Le azioni

| Azione | Quando |
| --- | --- |
| `CREA` | riga accesa, nessun trigger |
| `RIGENERA` | nome, momento, argomenti o abilitazione diversi dall'atteso, o più di un trigger |
| `TOGLIE` | riga spenta, trigger vivo |
| `SCONOSCIUTO` | trigger vivo su una tabella che il registro non nomina: il runner si ferma |
| `NON_CLASSIFICATA` | forma per colonna con una colonna non libera in nessuno dei due elenchi, o con una colonna elencata che la tabella non ha |
| `SENZA_ID` | la tabella non ha la colonna `id`: il registro non saprebbe nominare la riga |

`NON_CLASSIFICATA` e `SENZA_ID` sono difetti della dichiarazione: il runner non monta e non
rigenera, e il trigger di prima resta.

Il momento atteso è `BEFORE INSERT OR UPDATE OR DELETE FOR EACH ROW` (`tgtype` 31), il nome quello
del template `trg_<tabella>_a00_seed_primo_impianto_ins_upd_dlt` o quello dichiarato.

---

### L'ambito

`p_schemas` `NULL` vuol dire l'ambito di `dbops.fn_resolve_scope`. Le tabelle fuori dall'ambito non
si confrontano.

---

### Chi la legge

Il runner, la rete di convergenza in `90_end` (che si ferma se restano `CREA`, `RIGENERA`, `TOGLIE`
o `SCONOSCIUTO`) e il presidio, che è un'asserzione pgTAP: vuota dopo ogni giro.

---

### Test

* `db/pgtap/config/test-seed-primo-impianto-installazione-v1.sql`, asserzione 3 — il presidio a
  zero.
* `db/pgtap/dbops/test-seed-primo-impianto-software-v1.sql`, asserzioni 21-22 — `NON_CLASSIFICATA`
  su una colonna aggiunta.

---

### Note di migrazione

* 2026-11-17 — nasce (`brief-db-seed-primo-impianto-non-si-riscrive`).

---

{% include-markdown "signature-core.md" %}
