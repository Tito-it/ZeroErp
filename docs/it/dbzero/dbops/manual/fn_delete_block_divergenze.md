## 📘 Documentazione Concettuale – Funzione `dbops.fn_delete_block_divergenze`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.automation_delete_block](/dbzero/dbops/tabelle/automation_delete_block) — il registro dei blocchi di cancellazione
>
> Approfondimento funzioni:
>
> * [dbops.fn_run_automations_delete_block](/dbzero/dbops/funzioni/fn_run_automations_delete_block) — esegue l'azione di ogni riga
> * [script.trgfn_delete_block_by_guc](/dbzero/script/funzioni/trgfn_delete_block_by_guc) — la funzione da cui si riconosce il blocco vivo
> * [dbops.fn_nome_oggetto_dichiarato](/dbzero/dbops/funzioni/fn_nome_oggetto_dichiarato) — il nome atteso del trigger
> * [dbops.fn_lock_columns_divergenze](/dbzero/dbops/funzioni/fn_lock_columns_divergenze) — la stessa forma, per i lock di colonna
> * [dbops.fn_resolve_scope](/dbzero/dbops/funzioni/fn_resolve_scope) — risolve l'ambito quando non si passano schemi
>
> Guide:
>
> * [Framework di automazione DB, §4.4](/guide/automazione-db#44-delete_block-blocco-delete-con-guc) — la regola DELETE_BLOCK

---

### 🎯 Scopo Principale

Risponde a una domanda: **i blocchi di cancellazione vivi sono quelli che il registro dichiara?**
Per ogni tabella dell'ambito in cui la risposta è no restituisce una riga, con l'azione che la
riallinea. Non modifica niente.

È il **criterio unico** della convergenza: lo usano il runner, che esegue l'azione di ogni riga, e
il presidio pgTAP, che ne pretende zero su tutto l'ambito. Ha la stessa forma di
[fn_lock_columns_divergenze](/dbzero/dbops/funzioni/fn_lock_columns_divergenze).

---

### Atteso e vivo

* **Vivo**: **ogni** trigger della tabella che esegue `script.trgfn_delete_block_by_guc`,
  qualunque nome abbia. ⭐ Il riconoscimento è per funzione, non per nome: un blocco scritto a
  mano con un altro nome deve essere visto.
* **Atteso**, per una riga accesa di `dbops.automation_delete_block`: **un** trigger solo,
  `BEFORE DELETE` per riga, abilitato, col nome di
  [fn_nome_oggetto_dichiarato](/dbzero/dbops/funzioni/fn_nome_oggetto_dichiarato) (il
  `trigger_name` della riga o il template `trg_<tabella>_a10_delete_block_dlt`) e con la
  `guc_key` della riga come unico argomento.

Con `p_schemas` vuoto l'ambito è quello di `dbops.fn_resolve_scope`; le tabelle escluse
dall'ambito non si confrontano, perché il runner non ci arriva.

---

### Le azioni

| Azione | Quando |
| --- | --- |
| `CREA` | la riga è accesa e sulla tabella non c'è nessun blocco vivo |
| `RIGENERA` | la riga è accesa, ma i vivi non sono esattamente l'atteso: un nome diverso, il momento `AFTER` invece di `BEFORE`, un'altra `guc_key`, un trigger disabilitato, più di un trigger |
| `TOGLIE` | la riga è spenta (`enabled` falso) e c'è un blocco vivo: spegnere la riga è la decisione di togliere il blocco |
| `SCONOSCIUTO` | c'è un blocco vivo su una tabella che il registro non nomina affatto |

Le tabelle allineate non escono. Per `CREA` e `RIGENERA` la riga porta il nome e la `guc_key`
attesi; per tutte, l'elenco dei trigger vivi.

---

### ⛔ `SCONOSCIUTO` non vuol dire «da togliere»

Un blocco senza riga nel registro è nato fuori dal registro, e togliendolo si cancellerebbe in
silenzio una protezione che qualcuno ha voluto. Per questo non è un `TOGLIE`: il runner, se ne
trova anche uno solo, si ferma e lo nomina. Il rimedio è aggiungere la riga, accesa se il blocco va
tenuto, spenta se va tolto.

Una riga spenta e una riga che manca non sono la stessa cosa: la prima è una decisione, la seconda
no. Per togliere un blocco si spegne la riga, non la si cancella.

---

### Test

* `db/pgtap/dbops/test-delete-block-convergenza-v1.sql` — su tutto l'ambito nessun blocco diverge,
  e fuori dall'ambito non c'è nessun trigger della funzione; un blocco `AFTER` scritto a mano col
  nome atteso dà `RIGENERA`; una `guc_key` o un `trigger_name` cambiati danno `RIGENERA`; una riga
  spenta dà `TOGLIE`; un blocco su una tabella senza riga dà `SCONOSCIUTO`.

---

### Note di migrazione

* 2026-11-08 — nasce come criterio unico della convergenza dei blocchi di cancellazione
  (`20261109-96`, `brief-db-revisione-dbops`, giro 10c). Prima il runner riconosceva il blocco
  solo per nome e lo creava dove mancava, senza mai rigenerarlo né toglierlo.

---

{% include-markdown "signature-core.md" %}
