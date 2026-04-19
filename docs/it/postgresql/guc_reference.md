## Elenco GUC definite in Zero ERP

>
> (latest review 19-04-2026)
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
| `app.jwt_user`                            | n/d     | sessione | Username Django dell'utente autenticato (set da `JwtAuditAuthentication`).           | middleware audit JWT                        |
| `app.current_user_id`                     | n/d     | sessione | `auth_user.id` (stringa) dell'utente autenticato.                                    | middleware audit JWT, resolver legacy       |
| `app.current_identita_id`                 | n/d     | sessione | `identita_digitali.id` della veste attiva per la richiesta corrente (§4.7).          | policy RLS, `fn_scope_*`, `fn_current_identita_context` |
| `app.ruolo_applicativo`                   | n/d     | sessione | Valore `config.ruolo_applicativo` dell'identità corrente (§4.7).                     | policy RLS, resolver multi-face-auth        |
| `app.soggetto_ruolo_id`                   | n/d     | sessione | `soggetti_ruoli.id` dell'identità corrente (§4.7).                                   | policy `BA_OWNERSHIP`, `FORNITORE_OWNERSHIP` |
| `zeroerp.maintenance_indirizzi_dettaglio` | off     | sessione | Abilita manutenzione controllata per `indirizzi_dettaglio` (bump/riclassificazioni). | `maintenance.proc_bump_indirizzi_dettaglio` |
| `zeroerp.maintenance_toponomastica`       | off     | sessione | Abilita manutenzione controllata per correzioni toponomastiche.                      | `maintenance.proc_bump_toponomastica`       |

---

### Note

* I default indicati come `n/d` dipendono dalla configurazione dell'istanza.
* Le GUC di manutenzione sono **locali di sessione** e si usano solo in procedure controllate.
* Le GUC `app.*` relative al contesto identità (§4.7 WIP multi-face-auth)
  sono popolate dal middleware `JwtAuditAuthentication` al login e resettate
  nella response. Vanno lette sempre con `current_setting('<name>', true)`
  (missing_ok=true) per evitare errori in connessioni senza utente loggato
  (es. job batch, test). La funzione
  [`script.fn_current_identita_context`](/dbzero/script/funzioni/fn_current_identita_context)
  incapsula la lettura tipata dei tre GUC.

---
{% include-markdown "signature-core.md" %}
