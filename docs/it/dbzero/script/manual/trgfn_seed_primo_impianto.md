## 📘 Documentazione Concettuale – Funzione `script.trgfn_seed_primo_impianto()`

> **Ultimo aggiornamento**: 19 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.automazione_seed_primo_impianto](/dbzero/dbops/tabelle/automazione_seed_primo_impianto) — dove è montata, e in che forma
> * [dbops.seed_righe](/dbzero/dbops/tabelle/seed_righe) — il registro che scrive e legge
>
> Approfondimento funzioni:
>
> * [dbops.fn_seed_primo_impianto_argomenti](/dbzero/dbops/funzioni/fn_seed_primo_impianto_argomenti) — la grammatica dei suoi argomenti
> * [dbops.fn_sessione_del_migratore](/dbzero/dbops/funzioni/fn_sessione_del_migratore) — chi è il software
> * [script.fn_porta_manutenzione_aperta](/dbzero/script/funzioni/fn_porta_manutenzione_aperta) — la porta di manutenzione
> * [dbops.fn_run_automations_seed_primo_impianto](/dbzero/dbops/funzioni/fn_run_automations_seed_primo_impianto) — il giro che la monta
> * [dbops.fn_seed_riga](/dbzero/dbops/funzioni/fn_seed_riga) — la domanda «nata dal seed», sul registro
> * [script.trgfn_delete_block_by_guc](/dbzero/script/funzioni/trgfn_delete_block_by_guc) — il blocco della `DELETE` sugli account e sui template, che parla dopo
>
> Approfondimento viste:
>
> * [config.vw_email_account_seed](/dbzero/config/views/vw_email_account_seed) e [config.vw_email_template_seed](/dbzero/config/views/vw_email_template_seed) — il segno «nata dal seed» per l'interfaccia, dalle stesse funzioni
>
> Guide:
>
> * [Framework di automazione DB — 4.9 SEED_PRIMO_IMPIANTO](/guide/automazione-db#49-seed_primo_impianto-la-riga-modificata-dallinstallazione-non-si-riscrive) — la regola
> * [Gestione mail](/guide/gestione-mail) — gli account e i template, le due tabelle su cui è montata

---

### 🎯 Scopo Principale

Sulle tabelle del seed di primo impianto il CSV crea la riga, e dopo che l'installazione l'ha
modificata **non la riscrive più**. Senza questo trigger un mirror `loadUpdateData` ricaricato per
qualunque ritocco del CSV riporterebbe i valori di esempio sulla configurazione del cliente,
password compresa.

---

### Chi scrive: il software o l'installazione

Il **software** è la sessione del migratore
([fn_sessione_del_migratore](/dbzero/dbops/funzioni/fn_sessione_del_migratore), su `session_user`):
il migrate, o chi si collega a mano con quell'utente. Tutto il resto è l'**installazione**:
l'applicazione, un verbo `SECURITY DEFINER` chiamato dall'app, un job.

---

### Regole applicate

| Chi | Operazione | Riga | Che cosa succede |
| --- | --- | --- | --- |
| software | `INSERT` | — | passa, e la riga entra nel registro, nata dal seed |
| installazione | `INSERT` | — | passa: la riga è dell'installazione |
| software | `UPDATE` | di seed, intatta | passa: segue il CSV |
| software | `UPDATE` | personalizzata, dell'installazione, o in solo inserimento | le colonne dell'installazione tornano da `OLD`, quelle del software passano, e parte un `WARNING` |
| installazione | `UPDATE` | di seed | una colonna del software cambiata è `E_SEED_COLONNA_DEL_SOFTWARE`; una dell'installazione cambiata fa la riga personalizzata |
| installazione | `UPDATE` | dell'installazione | passa |
| chiunque | `DELETE` | di seed | `E_SEED_RIGA_NON_CANCELLABILE`: la riga si spegne (`attivo = false`) |
| chiunque | `DELETE` | dell'installazione | passa (dove la tabella lo consente: account e template di posta non si cancellano) |

* Su una riga **personalizzata** i valori che il CSV avrebbe scritto vanno nel registro
  (`scartati`). In **solo inserimento** no: la riga è dell'installazione per costruzione. Il
  `WARNING` parte in tutti e due i casi, perché chi scrive a mano con l'utente del migratore sappia
  che la scrittura non è entrata.
* `meta`, le colonne d'audit e `tx_id` non contano per «personalizzata».
* ⭐ **Restituisce sempre la riga, mai `NULL`.** Il mirror su PostgreSQL scrive
  `UPDATE …; IF not found THEN INSERT`: un `UPDATE` annullato con `NULL` farebbe partire l'`INSERT`,
  e la chiave andrebbe duplicata. La riga rimessa a posto fa contare l'`UPDATE` come avvenuto.
* La domanda «nata dal seed» la fa [fn_seed_riga](/dbzero/dbops/funzioni/fn_seed_riga), la stessa
  che leggono le superfici degli account e dei template. Le colonne del software che rifiuta sono
  quelle dei suoi argomenti: le superfici le leggono dal montaggio con la stessa grammatica
  ([fn_seed_colonne_del_software](/dbzero/dbops/funzioni/fn_seed_colonne_del_software)). Il campo
  spento e il rifiuto rispondono alla stessa domanda.
* ⚠️ **Su `config.email_account` e `config.email_template` nessuna riga si cancella**
  (`dbops.automation_delete_block`, dal 2026-11-19): sulla riga di seed parla prima questo trigger
  (`a00`), sulle altre il blocco (`a10`, `E_DELETE_NOT_ALLOWED`). Il migratore che ritira una riga
  di seed apre **due** porte: `zeroerp.allow_seed_primo_impianto_override` e
  `zeroerp.maintenance_email_delete`.
* ⭐ **Scatta per primo** (fase `a00`): i guard e i lucchetti che vengono dopo vedono i valori
  rimessi, non quelli del CSV.

---

### La porta di manutenzione

`zeroerp.allow_seed_primo_impianto_override`, per la sola sessione del migratore
([fn_porta_manutenzione_aperta](/dbzero/script/funzioni/fn_porta_manutenzione_aperta)): lascia
passare la bonifica di una riga personalizzata e il `DELETE` forward-only di una riga di seed, che
toglie anche il suo segno dal registro. Una riga bonificata resta personalizzata.

⚠️ Il migratore che con la porta del lucchetto cambia `codice_interno` su una riga in solo
inserimento lo vede rimesso da `OLD`: deve aprire anche questa porta.

---

### Perché `SECURITY DEFINER`

Scrive il registro, che l'applicazione legge soltanto. Chi scrive si riconosce da `session_user`,
che la `SECURITY DEFINER` non cambia. `search_path` bloccato su `pg_catalog, pg_temp`.

---

### Codici errore

* `E_SEED_RIGA_NON_CANCELLABILE` — `DELETE` di una riga di seed.
* `E_SEED_COLONNA_DEL_SOFTWARE` — l'installazione cambia una colonna del software; `campo` è la
  colonna, per il form.
* `E_TRIGGER_ARGOMENTI_INVALIDI` — trigger montato con argomenti fuori grammatica.

---

### Test

* `db/pgtap/dbops/test-seed-primo-impianto-software-v1.sql` — il lato del software: `INSERT`,
  `UPDATE` su riga intatta e personalizzata, solo inserimento, porta, `DELETE`.
* `db/pgtap/config/test-seed-primo-impianto-installazione-v1.sql` — il lato dell'installazione, come
  applicazione.
* `db/pgtap/dbops/test-seed-primo-impianto-postura-v1.sql` — `SECURITY DEFINER` e `search_path`.
* `db/pgtap/config/test-posta-solo-disattivazione-v1.sql` — sul template di seed parla il guard
  prima del blocco della `DELETE` (test 6), e le superfici che leggono le sue funzioni.

---

### Note di migrazione

* 2026-11-17 — nasce (`brief-db-seed-primo-impianto-non-si-riscrive`).
* 2026-11-18 — in solo inserimento il salto del software alza il `WARNING`, senza scrivere il
  registro (Q22).
* 2026-11-19 — la voce del registro si legge da `fn_seed_riga` (§16.14 del brief).

---

{% include-markdown "signature-core.md" %}
