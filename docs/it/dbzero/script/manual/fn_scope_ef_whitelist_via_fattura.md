## Documentazione Concettuale – Funzione `script.fn_scope_ef_whitelist_via_fattura`

> **Vedi anche**
>
[Linee guida SQL — sezione 10 RLS](/linee-guida-sql#10-row-level-security-rls)
>
**Funzioni correlate:**
>
[script.fn_scope_ef_whitelist_via_sr](/dbzero/script/funzioni/fn_scope_ef_whitelist_via_sr) (adapter SR)
> [script.fn_scope_ef_whitelist](/dbzero/script/funzioni/fn_scope_ef_whitelist) (adapter PK / entry-point)
> [script.fn_resolve_controparte_sr_id](/dbzero/script/manual/fn_resolve_controparte_sr_id) (lo scope BA: il cliente della fattura, modo `fattura`)
>
**Tabelle correlate:**
>
[vendite.fatture](/dbzero/vendite/tabelle/fatture)
> [vendite.fatture_scadenze](/dbzero/vendite/tabelle/fatture_scadenze)

---
### 🎯 Scopo Principale
(rev 2026-06-01)

Adapter **via fattura** dello scope `EF_WHITELIST`: per le tabelle **figlie**
di `vendite.fatture` che non hanno una colonna emittente propria (es.
`vendite.fatture_scadenze`), risolve l'emittente **attraverso la fattura
collegata** e delega all'adapter SR.

Per lo scope del cliente portale la stessa domanda la fa il modo `fattura` di
`fn_resolve_controparte_sr_id` (dal 21-10-2026; `fn_scope_ba_ownership_via_fattura`
è ritirata).

---

### Parametri di input

| Parametro | Tipo | Descrizione |
|-----------|------|-------------|
| `p_auth_user_id` | `integer` | Utente applicativo (dal GUC `app.current_user_id`). |
| `p_fattura_id` | `vendite.fatture.id%TYPE` | Fattura collegata alla riga figlia (colonna `fattura_id`). |

---

### Output

`BOOLEAN` — esito della canonica. Vedi
[`fn_scope_ef_whitelist`](/dbzero/script/funzioni/fn_scope_ef_whitelist) per la
semantica completa.

---

### Catena di risoluzione

```
fattura_id (= p_fattura_id)
    → vendite.fatture.emittente_soggetto_ruolo_id
    → fn_scope_ef_whitelist_via_sr(auth_user_id, emittente_sr_id)
    → fn_check_user_emittente_scope(auth_user_id, emittente_fiscale_id)
```

Fattura inesistente → SR `NULL` → `false` se whitelist valorizzata (fail-closed).

---

### Regole implementative

* `LANGUAGE sql`, `STABLE`: inlineable nei predicati `USING`.
* Evita subquery inline nelle policy RLS (§10.3 linee-guida-sql).

---

### Esempio d'uso

```sql
CREATE POLICY rls_fatture_scadenze_ef_whitelist ON vendite.fatture_scadenze
    AS PERMISSIVE FOR SELECT
    USING (
        current_setting('app.ruolo_applicativo', true) = 'OPERATORE'
        AND script.fn_scope_ef_whitelist_via_fattura(
            NULLIF(current_setting('app.current_user_id', true), '')::integer,
            fattura_id
        )
    );
```

---

### ⭐ rev 2026-10-18 — chiede l'emittente al risolutore, e non sta più nelle policy

ChangeSet `20261018-32`: l'emittente lo chiede a
[`fn_resolve_emittente_fiscale_id`](fn_resolve_emittente_fiscale_id.md) (modo
`fattura`, `SECURITY DEFINER`) invece di leggere il padre sotto la sua RLS: la
strada documento → emittente è scritta una volta, e una chiamata non riesegue la
policy del padre. Stesse risposte. Resta per la domanda su **un** emittente
(verbi, guard, backend); le policy non la chiamano più (`20261018-33`): calcolano
il perimetro una volta per istruzione con
[`fn_scope_ef_perimetro`](fn_scope_ef_perimetro.md). Brief
`brief-db-plancache-funzioni-con-query-incorporate` §5quinquies (giro 1b).

{% include-markdown "signature-core.md" %}
