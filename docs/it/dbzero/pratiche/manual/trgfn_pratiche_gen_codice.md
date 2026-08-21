## 📘 Documentazione Concettuale – Funzione `pratiche.trgfn_pratiche_gen_codice()`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [pratiche.pratiche](/dbzero/pratiche/tabelle/pratiche)
> • [config.sistema_codici](/dbzero/config/tabelle/sistema_codici)
>
Approfondimento funzioni:
> • [script.fn_generate_codice](/dbzero/script/funzioni/fn_generate_codice)
> • [script.trgfn_lock_columns](/dbzero/script/funzioni/trgfn_lock_columns)

---
### 🎯 Scopo Principale

(rev 2026-08-21)

Assegna il **codice della pratica** quando chi la crea non lo fornisce, delegando a
`script.fn_generate_codice('pratica')`. È lo stesso pattern delle anagrafiche
(`trgfn_soggetti_gen_codice` e famiglia): la funzione non calcola nulla, si limita a
riconoscere il campo vuoto e a chiedere il codice al generatore centrale.

---

### Aggancio

Trigger `trg_pratiche_a10_gen_codice_ins_upd` — fase `_a10_`, `BEFORE INSERT OR UPDATE`
su `pratiche.pratiche`.

---

### Regole applicate

1. Se `NEW.codice` è `NULL` o vuoto dopo `btrim`, viene valorizzato con
   `script.fn_generate_codice('pratica')`.
2. Un codice già presente non viene mai sovrascritto.

Configurazione in `config.sistema_codici`, riga `codice_interno = 'pratica'`:
prefisso `PRA`, separatore `-`, numero a 7 cifre (`PRA-0000123`).

---

### ⚠️ Note e trappole

* **La chiave è `'pratica'` al singolare**, mentre lo schema e la tabella sono al plurale.
  Il legame con `config.sistema_codici` è per stringa: rinominare quella riga fa fallire
  ogni inserimento con `E_SEQUENZA_NON_CONFIGURATA`.
* **`usa_sequenza = false` restituisce `NULL`, non un errore.** Se un giorno quella riga
  venisse spenta, le pratiche nascerebbero senza codice e il difetto emergerebbe a valle,
  non qui.
* **In `UPDATE` la generazione è trattenuta dal lock.** La tabella ha anche
  `script.trgfn_lock_columns` sul codice; i `BEFORE ROW` scattano in ordine alfabetico, quindi
  `gen_codice` gira prima di `lock_columns`: chi svuota `codice` in un `UPDATE` ne ottiene uno
  nuovo, che il lock rifiuta subito dopo come modifica. Con
  `SET LOCAL zeroerp.allow_lock_columns_override = 'on'` la rete sparisce e il codice cambia
  davvero.

---

### ⚠️ Questa funzione è **generata**, non scritta a mano

Il corpo compresso su una riga sola non è una svista di formattazione. La funzione, la
sequenza e il trigger che la invoca sono creati con DDL dinamico da
`script.trgfn_config_sistema_codici_sync_gen_codice` — il trigger
`AFTER INSERT OR UPDATE OR DELETE` di `config.sistema_codici`. Basta la riga
`codice_interno = 'pratica'` con `schema_tabella`, `nome_tabella`, `nome_colonna` valorizzati
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
| `E_SEQUENZA_NON_CONFIGURATA` | `script.fn_generate_codice` | Nessuna riga `codice_interno = 'pratica'` in `config.sistema_codici` |

La funzione non solleva errori propri.

---

{% include-markdown "signature-core.md" %}
