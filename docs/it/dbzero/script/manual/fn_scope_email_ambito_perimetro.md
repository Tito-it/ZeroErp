## 📘 Documentazione Concettuale – Funzione `script.fn_scope_email_ambito_perimetro(...)`

> 👀 **Vedi anche**
>
> [fn_scope_email_ambito](/dbzero/script/funzioni/fn_scope_email_ambito) — la domanda su una mail sola, che la compone
> [fn_scope_ef_perimetro](fn_scope_ef_perimetro.md) — il confronto dell'emittente col perimetro
> [Linee guida SQL — §10 RLS](/linee-guida-sql#10-row-level-security-rls)
>
> **Tabelle correlate:** [config.email_outbox](/dbzero/config/tabelle/email_outbox),
> [config.email_log](/dbzero/config/tabelle/email_log)
>
> Brief: `brief-db-perimetro-una-volta-famiglie-residue` §9 (giro 5)

---

### 🎯 Scopo Principale

(nata il 2026-10-21, `20261021-41`)

**Chi guarda può vedere questa mail?** È la regola dell'**ambito** delle email, e ne è
la sede unica:

| Ambito | Chi la vede |
|---|---|
| `SISTEMA` | il super admin, o l'identità del processo |
| `REPARTO` | il super admin, chi sta nello stesso reparto o il processo — **e** l'emittente nel perimetro di chi guarda |
| `OPERATORE` | il super admin, chi l'ha creata o il processo — **e** l'emittente nel perimetro |
| altro | nessuno |

Le quattro cose che servono di chi guarda non dipendono dalla mail, e la funzione
**non le calcola**: gliele passa la policy di `email_outbox` ed `email_log`, una
volta per istruzione, in quattro sottoquery:

* super admin (`fn_is_super_admin`);
* reparto (`fn_get_uo_id_for_user`);
* identità del processo (`fn_scope_identita_processo` con `send_pending_emails` nel
  log, perché chi spedisce deve poter rileggere; `false` nell'outbox);
* perimetro emittenti (`fn_get_emittenti_scope_pk_ids`: `NULL` = tutti).

Per ogni mail resta questa funzione: pura, senza letture (~4 µs).
[`fn_scope_email_ambito`](/dbzero/script/funzioni/fn_scope_email_ambito) la compone
calcolando da sé le quattro risposte, per chi chiede di una mail sola.

⚠️ Chi guarda senza reparto non vede le mail di reparto: fail-closed, voluto.
⚠️ L'emittente resta in `AND` anche per l'autore e per il processo.

Presidio: `script/test-fn-scope-email-ambito-perimetro-v1` (ogni ramo, nei due versi).

---

{% include-markdown "signature-core.md" %}
