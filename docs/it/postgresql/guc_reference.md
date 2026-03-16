## Elenco GUC definite in Zero ERP

>
> (latest review 02-01-26)
>
> **Vedi anche**
>
> * [Parametri personalizzati (GUC)](/postgresql/parametri-personalizzati-(GUC))

---

### Tabella di riferimento

| GUC                                       | Default | Ambito   | Descrizione                                                                          | Usata da                                    |
| ----------------------------------------- | ------- | -------- | ------------------------------------------------------------------------------------ | ------------------------------------------- |
| `myapp.dblink_log_connection`             | n/d     | sistema  | Connessione per logging remoto via dblink.                                           | `dblink` / logging remoto                   |
| `myapp.user_language`                     | n/d     | sistema  | Lingua di default per funzioni applicative.                                          | funzioni applicative                        |
| `myapp.bypass_tx_id_check`                | off     | sistema  | Bypass controllo `tx_id` nei trigger.                                                | trigger `dbops.trgfn_tx_id_managed`         |
| `dbops.tx_id`                             | n/d     | sessione | Identificativo transazionale logico per audit/log.                                   | trigger audit/log                           |
| `zeroerp.maintenance_indirizzi_dettaglio` | off     | sessione | Abilita manutenzione controllata per `indirizzi_dettaglio` (bump/riclassificazioni). | `maintenance.proc_bump_indirizzi_dettaglio` |
| `zeroerp.maintenance_toponomastica`       | off     | sessione | Abilita manutenzione controllata per correzioni toponomastiche.                      | `maintenance.proc_bump_toponomastica`       |

---

### Note

* I default indicati come `n/d` dipendono dalla configurazione dell'istanza.
* Le GUC di manutenzione sono **locali di sessione** e si usano solo in procedure controllate.

---
{% include-markdown "signature-core.md" %}
