## 📘 Documentazione Concettuale – Funzione `dbops.fn_guard_utility_divergenze`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.automazione_guard_utility_tipo_ruolo](/dbzero/dbops/tabelle/automazione_guard_utility_tipo_ruolo) — il registro delle tabelle da proteggere
>
> Approfondimento funzioni:
>
> * [dbops.fn_run_automations_guard_utility](/dbzero/dbops/funzioni/fn_run_automations_guard_utility) — esegue l'azione di ogni riga
> * [script.trgfn_guard_utility_tipo_ruolo_by_cols](/dbzero/script/funzioni/trgfn_guard_utility_tipo_ruolo_by_cols) — la funzione da cui si riconosce il guard vivo
> * [dbops.fn_nome_oggetto_dichiarato](/dbzero/dbops/funzioni/fn_nome_oggetto_dichiarato) — il nome atteso del trigger
> * [dbops.fn_delete_block_divergenze](/dbzero/dbops/funzioni/fn_delete_block_divergenze) — la stessa forma, per il blocco delle cancellazioni
> * [dbops.fn_resolve_scope](/dbzero/dbops/funzioni/fn_resolve_scope) — risolve l'ambito quando non si passano schemi
>
> Guide:
>
> * [Framework di automazione DB](/guide/automazione-db) — l'automazione GUARD utility/tipo ruolo fra le altre

---

### 🎯 Scopo Principale

Risponde a una domanda: **i guard utility/tipo ruolo vivi sono quelli che il registro dichiara?**
Per ogni tabella dell'ambito in cui la risposta è no restituisce una riga, con l'azione che la
riallinea. Non modifica niente.

È il **criterio unico** della convergenza: lo usano il runner, che esegue l'azione di ogni riga, e
il presidio pgTAP, che ne pretende zero su tutto l'ambito.

---

### Atteso e vivo

* **Vivo**: **ogni** trigger della tabella che esegue
  `script.trgfn_guard_utility_tipo_ruolo_by_cols`, qualunque nome abbia: il riconoscimento è per
  funzione, non per nome.
* **Atteso**, per una riga accesa le cui due colonne esistono: **un** trigger solo, `BEFORE INSERT
  OR UPDATE OF` le due colonne, per riga, abilitato, col nome di
  [fn_nome_oggetto_dichiarato](/dbzero/dbops/funzioni/fn_nome_oggetto_dichiarato) (il
  `trigger_name` della riga o il template `trg_<tabella>_a10_guard_utility_tipo_ruolo_ins_upd`) e
  con gli argomenti `utility_column`, `soggetto_ruolo_column` in quest'ordine.

⭐ Nessun filtro sul nome della colonna: il guard è generico e la colonna la dichiara il registro.
Una riga con `soggetto_ruolo_id`, senza prefisso, vale come una con `emittente_soggetto_ruolo_id`.

Il primo parametro è il modo della corsa (`CI`, `SCHEDULED`…): una riga il cui `exec_mode` non è
`AUTO` né il modo della corsa lascia la tabella **fuori dal confronto**, perché la governa l'altra
corsa. Con `p_schemas` vuoto l'ambito è quello di `dbops.fn_resolve_scope`.

---

### Le azioni

| Azione | Quando |
| --- | --- |
| `CREA` | riga accesa, colonne presenti, nessun guard vivo |
| `RIGENERA` | riga accesa, colonne presenti, ma i vivi non sono esattamente l'atteso: un nome diverso, altre colonne o altri argomenti, un trigger disabilitato, più di un trigger |
| `TOGLIE` | riga spenta (`enabled` falso) con un guard vivo |
| `COLONNA_MANCANTE` | riga accesa, ma una delle due colonne non esiste sulla tabella: il guard non si monta |
| `SCONOSCIUTO` | un guard vivo su una tabella che il registro non nomina affatto |

Le tabelle allineate non escono. Ogni riga porta le due colonne del registro e l'elenco dei trigger
vivi; per `CREA` e `RIGENERA` anche il nome atteso.

---

### ⛔ `SCONOSCIUTO` non vuol dire «da togliere»

Un guard senza riga nel registro è nato fuori dal registro: toglierlo cancellerebbe in silenzio una
protezione. Il runner, se ne trova anche uno solo, si ferma e lo nomina. Il rimedio è aggiungere la
riga al CSV del registro, spenta se il guard va tolto.

---

### Test

* `db/pgtap/dbops/test-guard-utility-convergenza-v1.sql` — su tutto l'ambito nessun guard diverge,
  e fuori dall'ambito non c'è nessun trigger della funzione; una riga con la colonna
  `soggetto_ruolo_id` dà `CREA`; una colonna inesistente dà `COLONNA_MANCANTE`; un guard su una
  tabella senza riga dà `SCONOSCIUTO`.

---

### Note di migrazione

* 2026-11-08 — nasce come criterio unico della convergenza del guard utility/tipo ruolo
  (`20261109-99`, `brief-db-revisione-dbops`, giro 10c). Prima l'apply ricreava il guard col nome
  di oggi senza riconoscere gli altri, non toglieva quello di una riga spenta e scartava in
  silenzio la colonna senza prefisso.

---

{% include-markdown "signature-core.md" %}
