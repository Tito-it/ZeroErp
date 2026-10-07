## Documentazione Concettuale – Funzione `script.fn_scope_ba_ownership_via_fattura`

> **Vedi anche**
>
Architettura di riferimento:
>
[Architettura Multi-Face Auth](/guide/architettura-multi-face-auth)
> [Linee guida SQL — sezione 10 RLS](/linee-guida-sql#10-row-level-security-rls)
>
**Funzioni correlate:**
>
[script.fn_scope_ba_ownership](/dbzero/script/funzioni/fn_scope_ba_ownership)

---
### 🎯 Scopo Principale
(latest review 19-04-2026)

Helper wrapper per applicare lo scope `BA_OWNERSHIP` a tabelle figlie
di `vendite.fatture` che **non hanno `billing_account_id` diretto** ma
solo `fattura_id` (es. `vendite.fatture_scadenze`). La funzione risolve
il BA tramite JOIN alla fattura e delega a `fn_scope_ba_ownership`.

Evita subquery inline nelle policy RLS (pattern proibito dalle
[linee guida §10.3](/linee-guida-sql#103-logica-di-scope-in-funzioni-scriptfn_scope_)).

---

### Parametri di input

| Parametro | Tipo | Descrizione |
|-----------|------|-------------|
| `p_identita_id` | `anagrafiche.identita_digitali.id%TYPE` | Identità corrente. |
| `p_fattura_id` | `vendite.fatture.id%TYPE` | ID della fattura parent. |

---

### Output

`BOOLEAN` — `true` se il BA della fattura appartiene al soggetto_ruolo
dell'identità, `false` altrimenti.

---

### Semantica (fail-closed)

| Caso | Risultato |
|------|-----------|
| Identità inesistente / non utilizzabile oggi | `false` |
| Fattura inesistente | `false` |
| Fattura con BA di altro cliente | `false` |
| Match completo (SR identità = SR BA della fattura + identità utilizzabile oggi) | `true` |

⭐ **Dal 07-10-2026** (brief `brief-db-veste-utilizzabile`): l'identità deve essere
**utilizzabile oggi** secondo
[script.fn_veste_utilizzabile](/dbzero/script/funzioni/fn_veste_utilizzabile)
(accesa, nelle sue date, soggetto attivo), non solo accesa. Prima una veste
scaduta, ma ancora accesa, continuava a vedere i suoi dati.


---

### Implementazione

```sql
SELECT EXISTS (
    SELECT 1
      FROM vendite.fatture              f
      JOIN anagrafiche.billing_account  ba ON ba.id = f.billing_account_id
      JOIN anagrafiche.identita_digitali id
        ON id.soggetto_ruolo_id = ba.soggetto_ruolo_id
     WHERE f.id      = p_fattura_id
       AND id.id     = p_identita_id
       AND script.fn_veste_utilizzabile(id.id)
);
```

* `LANGUAGE sql STABLE`. ⚠️ Non inlineabile (contiene `EXISTS`): la policy la
  chiama per riga.
* Single `EXISTS` short-circuit.

---

### Uso tipico

```sql
CREATE POLICY rls_fatture_scadenze_ba_ownership
    ON vendite.fatture_scadenze
    FOR SELECT
    USING (
        script.fn_scope_ba_ownership_via_fattura(
            NULLIF(current_setting('app.current_identita_id', true), '')::bigint,
            fattura_id
        )
    );
```

---

### Estensibilità

Lo stesso pattern è replicabile per altre tabelle figlie di `fatture`
(es. `fatture_righe`, `fatture_fondi_fattura`) senza dover modificare
`fn_scope_ba_ownership`.

---

{% include-markdown "signature-core.md" %}
