## 📘 Documentazione Concettuale – Vista `config.vw_email_account_seed`

> **Ultimo aggiornamento**: 20 novembre 2026
>
> 👀 **Vedi anche**
>
> [dbops.fn_seed_superficie](/dbzero/dbops/manual/fn_seed_superficie) ·
> [dbops.fn_seed_riga](/dbzero/dbops/manual/fn_seed_riga) ·
> [dbops.fn_seed_colonne_del_software](/dbzero/dbops/manual/fn_seed_colonne_del_software) ·
> [script.trgfn_seed_primo_impianto](/dbzero/script/manual/trgfn_seed_primo_impianto) — il guard ·
> [config.vw_email_template_seed](/dbzero/config/manual/vw_email_template_seed) — la gemella dei template ·
> [Gestione mail](/guide/gestione-mail)

### 🎯 Scopo

**Il segno del seed di primo impianto sugli account di posta**: una riga per account
(`email_account_id`), con ciò che il drawer deve sapere di un account installato dal programma. Il
backend la legge accanto a `config.email_account`, nella lista e nel dettaglio.

| Colonna | Che cosa |
| --- | --- |
| `nata_dal_seed` | l'account l'ha installato il programma (la riga `SISTEMA`), non l'azienda |
| `campi_del_software` | su un account nato dal seed, i campi che l'installazione non modifica. Gli account sono in solo inserimento: il CSV crea la riga e poi non la tocca più, quindi l'elenco è vuoto. Vuoto, mai `NULL` |

### La regola

* ⭐ **Tutto viene dalle funzioni del guard**, come nella gemella dei template: il segno è
  `dbops.fn_seed_riga`, i campi sono gli argomenti del montaggio di
  `script.trgfn_seed_primo_impianto`, e il giudizio sulla riga è `dbops.fn_seed_superficie`, la sede
  comune a tutte le superfici del seed. Se la forma della tabella cambia nel registro della regola, la
  colonna segue senza toccare il backend.
* **Nessuna colonna per «elimina»**: un account non si cancella, nemmeno quello creato dall'azienda.
  Si spegne (`attivo = false`), anche dopo aver spedito: lo storico delle mail non lo tiene acceso
  (`dbops.automation_delete_block`, `dbops.automazione_attivo_eccezioni`).
* ⚠️ `codice_interno` è fermo per un'altra ragione (`script.trgfn_lock_columns`) e non compare in
  `campi_del_software`.
* `security_invoker`.

### Test

* `db/pgtap/config/test-posta-solo-disattivazione-v1.sql` — la riga `SISTEMA`, come applicazione
  (test 7 e 11).

### Note di migrazione

* 2026-11-19 — nasce (`brief-db-seed-primo-impianto-non-si-riscrive` §16.14).

---

{% include-markdown "signature-core.md" %}
