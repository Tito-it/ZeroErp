## Documentazione Concettuale – Funzione `script.fn_scope_cliente_ownership`

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
> [script.fn_scope_fornitore_ownership](/dbzero/script/funzioni/fn_scope_fornitore_ownership)

---
### 🎯 Scopo Principale
(latest review 19-04-2026)

La funzione **`script.fn_scope_cliente_ownership`** implementa la policy
di scope `CLIENTE_OWNERSHIP`: verifica che un'identità digitale di tipo
cliente (CLIENTE_PORTALE o SHOP_CUSTOMER) possa vedere i dati il cui
`soggetto_ruolo_id` coincide con il proprio.

È la simmetrica di `fn_scope_fornitore_ownership` per il lato vendite, e
si usa dove la tabella ha `soggetto_ruolo_id` NOT NULL direttamente e
**non** dipende da `billing_account` (che per alcune tabelle come
`vendite.ordini` è nullable by design).

---

### Parametri di input

| Parametro | Tipo | Descrizione |
|-----------|------|-------------|
| `p_identita_id` | `anagrafiche.identita_digitali.id%TYPE` | Identità corrente. |
| `p_cliente_sr_id` | `anagrafiche.soggetti_ruoli.id%TYPE` | Soggetto ruolo cliente target da verificare. |

---

### Output

`BOOLEAN` — `true` se il cliente target coincide col SR dell'identità,
`false` altrimenti.

---

### Semantica (fail-closed)

| Caso | Risultato |
|------|-----------|
| Identità inesistente / non utilizzabile oggi | `false` |
| Identità in veste diversa da `CLIENTE_PORTALE` o `SHOP_CUSTOMER` | `false` |
| SR target diverso dal SR dell'identità | `false` |
| Match completo (SR uguale + veste CL/SHOP + utilizzabile oggi) | `true` |

⭐ **Dal 07-10-2026** (brief `brief-db-veste-utilizzabile`): l'identità deve essere
**utilizzabile oggi** secondo
[script.fn_veste_utilizzabile](/dbzero/script/funzioni/fn_veste_utilizzabile)
(accesa, nelle sue date, soggetto attivo), non solo accesa. Prima una veste
scaduta, ma ancora accesa, continuava a vedere i suoi dati.


---

### Regole implementative

* `LANGUAGE sql`, `STABLE`.
* `%TYPE` su firma per allineamento alle colonne sorgente.
* Gate `script.fn_veste_utilizzabile(id.id)` + `ruolo_applicativo IN (CLIENTE_PORTALE, SHOP_CUSTOMER)`.
* Single `EXISTS`: short-circuit alla prima corrispondenza.

---

### Uso tipico

Policy RLS su tabelle con `soggetto_ruolo_id` cliente diretto:

```sql
CREATE POLICY rls_ordini_cliente_ownership ON vendite.ordini
    AS PERMISSIVE
    FOR SELECT
    USING (
        current_setting('app.ruolo_applicativo', true)
            IN ('CLIENTE_PORTALE', 'SHOP_CUSTOMER')
        AND script.fn_scope_cliente_ownership(
            NULLIF(current_setting('app.current_identita_id', true), '')::bigint,
            soggetto_ruolo_id
        )
    );
```

---

### Rapporto con `fn_scope_ba_ownership`

Non è un duplicato: le due funzioni risolvono scope diversi.

| Funzione | Input target | Quando usarla |
|---|---|---|
| `fn_scope_ba_ownership` | `billing_account_id` | Tabelle con BA diretto (es. `vendite.fatture`, `anagrafiche.billing_account` self) |
| `fn_scope_cliente_ownership` | `soggetto_ruolo_id` (cliente) | Tabelle con SR cliente diretto e BA nullable/assente (es. `vendite.ordini`) |

Entrambe ammettono sia `CLIENTE_PORTALE` sia `SHOP_CUSTOMER` perché il
ruolo anagrafico (`CL`) è comune.

---

{% include-markdown "signature-core.md" %}
