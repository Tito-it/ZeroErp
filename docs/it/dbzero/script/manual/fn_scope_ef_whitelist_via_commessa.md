## Documentazione Concettuale – Funzione `script.fn_scope_ef_whitelist_via_commessa`

> **Vedi anche**
>
[Linee guida SQL — sezione 10 RLS](/linee-guida-sql#10-row-level-security-rls)
>
**Funzioni correlate:**
>
[script.fn_scope_ef_whitelist_via_sr](/dbzero/script/funzioni/fn_scope_ef_whitelist_via_sr) (adapter SR a cui delega)
> [script.fn_scope_ef_whitelist_via_fattura](/dbzero/script/funzioni/fn_scope_ef_whitelist_via_fattura) (adapter satellite gemello, via fattura)
> [script.fn_scope_ef_whitelist](/dbzero/script/funzioni/fn_scope_ef_whitelist) (adapter PK / entry-point)
>
**Tabelle correlate:**
>
[vendite.commesse](/dbzero/vendite/tabelle/commesse)
> [vendite.commesse_attivita](/dbzero/vendite/tabelle/commesse_attivita)

---
### 🎯 Scopo Principale
(rev 2026-07-20)

Adapter **via commessa** dello scope `EF_WHITELIST`: per le tabelle **figlie**
di `vendite.commesse` che non hanno una colonna emittente propria (es.
`vendite.commesse_attivita`, con `commessa_id` NOT NULL), risolve l'emittente
**attraverso la commessa collegata** e delega all'adapter SR.

È il gemello di `fn_scope_ef_whitelist_via_fattura` (stesso pattern satellite
usato dalla famiglia fatture).

---

### Parametri di input

| Parametro | Tipo | Descrizione |
|-----------|------|-------------|
| `p_auth_user_id` | `integer` | Utente applicativo (dal GUC `app.current_user_id`). Resta `integer` (riferimento a `django.auth_user`: `%TYPE` non ammesso). |
| `p_commessa_id` | `vendite.commesse.id%TYPE` | Commessa collegata alla riga figlia (colonna `commessa_id`). |

---

### Output

`BOOLEAN` — esito della canonica. Vedi
[`fn_scope_ef_whitelist`](/dbzero/script/funzioni/fn_scope_ef_whitelist) per la
semantica completa.

---

### Catena di risoluzione

```
commessa_id (= p_commessa_id)
    → vendite.commesse.emittente_soggetto_ruolo_id
    → fn_scope_ef_whitelist_via_sr(auth_user_id, emittente_sr_id)
    → fn_check_user_emittente_scope(auth_user_id, emittente_fiscale_id)
```

Commessa inesistente / emittente `NULL` → SR `NULL` → `false` se whitelist
valorizzata (fail-closed). Semantica: una commessa senza emittente (legacy) è
visibile/scrivibile solo ad admin globale.

---

### Regole implementative

* `LANGUAGE sql`, `STABLE`: inlineable nei predicati `USING`/`WITH CHECK`.
* Evita subquery inline nelle policy RLS (§10.3 linee-guida-sql).
* Nessuna logica whitelist duplicata: delega interamente all'adapter SR.

---

### Esempio d'uso

```sql
CREATE POLICY rls_commesse_attivita_ef_whitelist ON vendite.commesse_attivita
    AS PERMISSIVE FOR ALL
    USING (
        current_setting('app.ruolo_applicativo', true) = 'OPERATORE'
        AND script.fn_scope_ef_whitelist_via_commessa(
            NULLIF(current_setting('app.current_user_id', true), '')::integer,
            commessa_id
        )
    );
```

---

### ⭐ rev 2026-10-18 — chiede l'emittente al risolutore, e non sta più nelle policy

ChangeSet `20261018-32`: l'emittente lo chiede a
[`fn_resolve_emittente_fiscale_id`](fn_resolve_emittente_fiscale_id.md) (modo
`commessa`, `SECURITY DEFINER`) invece di leggere il padre sotto la sua RLS: la
strada documento → emittente è scritta una volta, e una chiamata non riesegue la
policy del padre. Stesse risposte. Resta per la domanda su **un** emittente
(verbi, guard, backend); le policy non la chiamano più (`20261018-33`): calcolano
il perimetro una volta per istruzione con
[`fn_scope_ef_perimetro`](fn_scope_ef_perimetro.md). Brief
`brief-db-plancache-funzioni-con-query-incorporate` §5quinquies (giro 1b).

{% include-markdown "signature-core.md" %}
