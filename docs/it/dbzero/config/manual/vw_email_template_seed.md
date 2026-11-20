## 📘 Documentazione Concettuale – Vista `config.vw_email_template_seed`

> **Ultimo aggiornamento**: 20 novembre 2026
>
> 👀 **Vedi anche**
>
> [dbops.fn_seed_superficie](/dbzero/dbops/manual/fn_seed_superficie) ·
> [dbops.fn_seed_riga](/dbzero/dbops/manual/fn_seed_riga) ·
> [dbops.fn_seed_colonne_del_software](/dbzero/dbops/manual/fn_seed_colonne_del_software) ·
> [script.trgfn_seed_primo_impianto](/dbzero/script/manual/trgfn_seed_primo_impianto) — il guard ·
> [config.vw_email_account_seed](/dbzero/config/manual/vw_email_account_seed) — la gemella degli account ·
> [Gestione mail](/guide/gestione-mail)

### 🎯 Scopo

**Il segno del seed di primo impianto sui template delle mail**: una riga per template
(`email_template_id`), con ciò che il drawer deve sapere di un template installato dal programma.
Il backend la legge accanto a `config.email_template`, nella lista e nel dettaglio.

| Colonna | Che cosa |
| --- | --- |
| `nata_dal_seed` | il template l'ha installato il programma, non l'azienda |
| `campi_del_software` | su un template nato dal seed, i campi che l'installazione non modifica: oggi il codice, il reparto, il tipo di prestazione, la lingua e le variabili disponibili, cioè ciò con cui `config.fn_resolve_email_template` trova il template e ciò che decide il codice che compone la mail. Vuoto, mai `NULL`, su un template creato dall'installazione |

### La regola

* ⭐ **Tutto viene dalle funzioni del guard.** Il segno è `dbops.fn_seed_riga`, la stessa domanda
  che fa `script.trgfn_seed_primo_impianto`; i campi sono gli argomenti del suo montaggio, letti con
  la stessa grammatica. Il giudizio sulla riga è `dbops.fn_seed_superficie`, la sede comune a tutte le
  superfici del seed. Il campo spento e il rifiuto non possono divergere, e il backend non tiene
  nessun elenco di colonne.
* **Nessuna colonna per «elimina»**: un template non si cancella, nemmeno quello creato
  dall'azienda. Si spegne (`attivo = false`), anche dopo aver spedito
  (`dbops.automation_delete_block`, `dbops.automazione_attivo_eccezioni`).
* `campi_del_software` non elenca i campi fermi per altre ragioni.
* `security_invoker`: chi guarda vede i template che vede nella tabella.

### Test

* `db/pgtap/config/test-posta-solo-disattivazione-v1.sql` — template di seed e dell'installazione,
  come applicazione.

### Note di migrazione

* 2026-11-19 — nasce (`brief-db-seed-primo-impianto-non-si-riscrive` §16.14).

---

{% include-markdown "signature-core.md" %}
