## 📘 Documentazione Concettuale – Tabella `dbops.automazione_attivo_inclusioni`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> ⛔ **Tabella ritirata** il 2026-11-22 (`90_end/20261121-25`): il motore ATTIVO lega ogni FK,
> qualunque sia il nome della colonna, e chi non si lega sta in
> [dbops.automazione_attivo_eccezioni](/dbzero/dbops/tabelle/automazione_attivo_eccezioni). La pagina
> resta finché la documentazione auto-generata non viene rigenerata, poi si toglie. Quello che segue
> descrive il registro com'era.
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.automazione_attivo_eccezioni](/dbzero/dbops/tabelle/automazione_attivo_eccezioni) — il registro gemello, le FK che il motore non lega; un'eccezione prevale
> * [config.regimi_fiscali](/dbzero/config/tabelle/regimi_fiscali) — il padre delle prime due righe
>
> Approfondimento funzioni:
>
> * [dbops.fn_attivo_fk_esclusa](/dbzero/dbops/funzioni/fn_attivo_fk_esclusa) — la domanda «questa FK si lega?», che legge questo registro
> * [dbops.fn_run_automations_attivo](/dbzero/dbops/funzioni/fn_run_automations_attivo) — il motore che genera la coppia
> * [dbops.fn_ritira_attivo_eccezioni](/dbzero/dbops/funzioni/fn_ritira_attivo_eccezioni) — toglie i trigger di una riga tolta
>
> Guide:
>
> * [Framework di automazione DB](/guide/automazione-db) — §1.3 e §4.2, le inclusioni della regola ATTIVO

---

### 🎯 Scopo Principale

Il registro delle FK **senza il suffisso `_id`** che l'automazione ATTIVO lega comunque. Il motore
salta ogni FK la cui colonna non finisce in `_id`, perché di solito punta a un codice testuale che
non è un legame padre/figlio. Quando lo è, la FK si dichiara qui, e il motore genera la coppia
intera:

* il **block** sul padre: il padre non si spegne finché un figlio acceso lo usa
  (`E_ATTIVO_BLOCK_CHILDREN_ACTIVE`);
* il **require** sul figlio: a un figlio acceso non si assegna un padre spento
  (`E_ATTIVO_PADRE_NON_ATTIVO`, con la colonna FK nel campo `campo` del contesto).

La colonna del padre passata ai trigger è quella che la FK referenzia davvero, anche una UNIQUE
non primaria come `codice_interno`.

---

### Le regole del registro

* **Una FK per riga**: schema e tabella della figlia, colonna FK
  (`uq_automazione_attivo_inclusioni_fk`). Il padre si ricava dalla FK.
* **Il motivo è obbligatorio** (`chk_automazione_attivo_inclusioni_motivo`).
* **Solo colonne senza `_id`** (`chk_automazione_attivo_inclusioni_senza_id`): una FK con `_id` la
  lega già il motore, e qui non avrebbe niente da dire.
* **Un'eccezione prevale**: una FK che sta anche in `dbops.automazione_attivo_eccezioni` non si
  lega. La risposta la dà `dbops.fn_attivo_fk_esclusa`, l'unica sede della domanda.
* **Togliere una riga ritira i trigger** al giro successivo del motore. ⚠️ Per questo un trigger
  ATTIVO montato a mano su una FK senza `_id` va dichiarato qui: altrimenti il ritiro lo toglie.

Si cambia dal CSV `80_data/sql/dbops/automazione_attivo_inclusioni.csv`; una riga si toglie dal
CSV e con un `DELETE` forward-only, perché il mirror non cancella. È un catalogo scritto dal solo
migratore: niente `data_update`, niente `user_update`, niente RLS.

---

### Le righe di oggi

| Figlia · FK | Perché |
| --- | --- |
| `anagrafiche.emittenti_fiscali.regime_fiscale_rf`, `anagrafiche.fornitori.regime_fiscale_rf` | Un **regime fiscale spento non si assegna, e uno in uso non si spegne** (Tid, 2026-11-21). Le due FK puntano a `config.regimi_fiscali(codice_interno)`. Contano i ruoli accesi: un emittente o un fornitore spento tiene il suo regime anche se il regime si spegne, ma riaccenderlo è rifiutato finché non gli si dà un regime acceso |

---

### Test

* `db/pgtap/dbops/test-automazione-attivo-inclusioni-v1.sql` — le righe, la coppia generata per le
  due FK, la risposta di `fn_attivo_fk_esclusa`, e il comportamento costruito su due regimi del test.

---
{% include-markdown "signature-core.md" %}
