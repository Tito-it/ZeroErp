## 📘 Documentazione Concettuale – Funzione `anagrafiche.trgfn_fornitori_gen_codice()`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [anagrafiche.fornitori](/dbzero/anagrafiche/tabelle/fornitori)
> • [config.sistema_codici](/dbzero/config/tabelle/sistema_codici)
>
Approfondimento funzioni:
> • [script.fn_generate_codice](/dbzero/script/funzioni/fn_generate_codice)
> • [script.trgfn_lock_columns](/dbzero/script/funzioni/trgfn_lock_columns)

---
### 🎯 Scopo Principale

(rev 2026-08-21)

Assegna il **codice interno** di `anagrafiche.fornitori` quando chi scrive non lo
fornisce. Non calcola niente da sé: delega a `script.fn_generate_codice('fornitori')`,
che legge prefisso, separatore e lunghezza da `config.sistema_codici` e consuma la
sequenza dedicata. È il pattern comune a tutte le anagrafiche con codice generato.

---

### Aggancio

Trigger `trg_fornitori_a10_gen_codice_ins_upd` — fase `_a10_`, `BEFORE INSERT OR UPDATE`
su `anagrafiche.fornitori`.

---

### Regole applicate

1. Se `NEW.codice` è `NULL` **oppure** stringa vuota dopo `btrim`, viene valorizzato
   con `script.fn_generate_codice('fornitori')`.
2. Se `NEW.codice` è già valorizzato, **non viene toccato**: un codice fornito
   dall'applicazione o da un import vince sempre sulla generazione.

La configurazione vive in `config.sistema_codici` alla riga `codice_interno = 'fornitori'`
(prefisso `FORN`, separatore `(nessuno)`, numero a 7 cifre).

---

### ⚠️ Note e trappole

* **La chiave di configurazione è `'fornitori'`, non il nome della tabella.** Rinominare
  quella riga in `config.sistema_codici` senza toccare la funzione fa fallire ogni
  inserimento con `E_SEQUENZA_NON_CONFIGURATA`: il legame è per stringa, non per FK.
* **`usa_sequenza = false` non è un errore: è un `NULL`.** In quel caso
  `fn_generate_codice` **restituisce `NULL`** senza sollevare niente, e la riga prosegue
  senza codice. Qui la colonna è `NOT NULL`, quindi si trasforma subito in una violazione di vincolo (SQLSTATE `23502`) — un errore tecnico, non un errore di dominio: nel log non c'è nessun codice `E_*` che spieghi la causa.
* **In `UPDATE` la generazione è di fatto inerte, ma solo grazie al lock.** Sulla stessa
  tabella agisce `trg_fornitori_a10_lock_columns_upd`
  (`script.trgfn_lock_columns('codice', 'CODICE_NON_MODIFICABILE')`), e i trigger `BEFORE ROW`
  scattano in **ordine alfabetico**: `gen_codice` gira *prima* di `lock_columns`. Chi svuota
  `codice` in un `UPDATE` ottiene quindi un codice nuovo, che il lock intercetta subito dopo
  come modifica e rifiuta.
  ⚠️ Con `SET LOCAL zeroerp.allow_lock_columns_override = 'on'` il lock si spegne e questa
  rete sparisce: in manutenzione, svuotare `codice` **cambia davvero l'identità della riga**
  e consuma un valore di sequenza.

---

### ⚠️ Questa funzione è **generata**, non scritta a mano

Il corpo compresso su una riga sola non è una svista di formattazione. La funzione, la
sequenza e il trigger che la invoca sono creati con DDL dinamico da
`script.trgfn_config_sistema_codici_sync_gen_codice` — il trigger
`AFTER INSERT OR UPDATE OR DELETE` di `config.sistema_codici`. Basta la riga
`codice_interno = 'fornitori'` con `schema_tabella`, `nome_tabella`, `nome_colonna` valorizzati
e `usa_sequenza = true`, e i tre oggetti nascono da soli.

È il motivo per cui **tutte** le `trgfn_*_gen_codice` del progetto hanno corpo identico: non
sono sette funzioni simili, sono la stessa funzione parametrizzata sette volte.

Conseguenze pratiche:

* **Modificarla a mano non serve a niente.** Il loader del CSV `sistema_codici` è
  `runOnChange`, quindi ripassa a ogni migrate: la funzione viene riscritta col template e
  qualunque ritocco locale sparisce senza lasciare traccia.
* **Non si spegne con un `DROP`, si spegne dalla configurazione.** Portando `usa_sequenza`
  a `false` il trigger di sync cancella da sé trigger e funzione; un `DROP` manuale li fa
  ricomparire al primo migrate.
* **Cambiare `schema_tabella`/`nome_tabella`/`nome_colonna` sposta gli oggetti**: il sync
  fa `DROP` di quelli vecchi e ricrea altrove. Nessun errore, nessun avviso.

---

### Codici errore

| Codice | Sollevato da | Quando |
|--------|--------------|--------|
| `E_SEQUENZA_NON_CONFIGURATA` | `script.fn_generate_codice` | Nessuna riga `codice_interno = 'fornitori'` in `config.sistema_codici` |
| `CODICE_NON_MODIFICABILE` | `script.trgfn_lock_columns` | Tentativo di cambiare `codice` in `UPDATE` |

La funzione **non solleva errori propri**: ogni errore viene dalle funzioni che invoca.

---

{% include-markdown "signature-core.md" %}
