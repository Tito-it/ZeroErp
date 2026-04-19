## Documentazione Concettuale – Funzione `script.fn_scope_ba_ownership`

> **Vedi anche**
>
Architettura di riferimento:
>
[Architettura Multi-Face Auth](/guide/architettura-multi-face-auth)
> [Linee guida SQL — sezione 10 RLS](/linee-guida-sql#10-row-level-security-rls)
>
**Tabelle correlate:**
>
[anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account)
> [anagrafiche.identita_digitali](/dbzero/anagrafiche/tabelle/identita_digitali)
> [config.scope_policy](/dbzero/config/tabelle/scope_policy)

---
### 🎯 Scopo Principale
(latest review 18-04-2026)

La funzione **`script.fn_scope_ba_ownership`** implementa la policy di scope
`BA_OWNERSHIP`: verifica che un'identità digitale di tipo cliente possa
vedere uno specifico `billing_account`.

Regola: il BA appartiene all'identità se e solo se condividono il
**soggetto_ruolo** (ovvero il cliente). La stessa policy copre sia
`CLIENTE_PORTALE` (portale B2B) sia `SHOP_CUSTOMER` (shop online) perché
condividono il ruolo anagrafico `CL`.

---

### Parametri di input

| Parametro | Tipo | Descrizione |
|-----------|------|-------------|
| `p_identita_id` | `anagrafiche.identita_digitali.id%TYPE` | Identità corrente. |
| `p_billing_account_id` | `anagrafiche.billing_account.id%TYPE` | BA target da verificare. |

---

### Output

`BOOLEAN` — `true` se il BA appartiene all'identità, `false` altrimenti.

---

### Semantica (fail-closed)

| Caso | Risultato |
|------|-----------|
| Identità inesistente / non attiva | `false` |
| BA inesistente | `false` |
| BA appartiene a un altro `soggetto_ruolo` | `false` |
| BA appartiene al `soggetto_ruolo` dell'identità | `true` |

---

### Regole implementative

* `LANGUAGE sql`, `STABLE`: inlineable dal planner.
* `%TYPE` su firma per allineamento alle colonne sorgente.
* Gate `id.attivo = true` nel WHERE per defense-in-depth.
* Single `EXISTS`: short-circuit alla prima corrispondenza.

---

### Catena JOIN

```
identita_digitali.soggetto_ruolo_id
    = billing_account.soggetto_ruolo_id  (join diretto)
AND identita_digitali.id = p_identita_id
AND billing_account.id   = p_billing_account_id
AND identita_digitali.attivo = true
```

`billing_account` ha FK diretta a `soggetti_ruoli` (colonna
`soggetto_ruolo_id`), quindi non serve passare da `anagrafiche.clienti`.

---

### Uso tipico

Policy RLS su tabelle figlie di `billing_account` (fatture, ordini, scadenze,
ecc.) oppure sulla tabella `billing_account` stessa:

```sql
CREATE POLICY rls_fatture_ba_ownership ON vendite.fatture
    FOR SELECT
    USING (
        script.fn_scope_ba_ownership(
            NULLIF(current_setting('app.current_identita_id', true), '')::bigint,
            billing_account_id
        )
    );
```

---

### Perché non serve una policy `SELF_OWNERSHIP` separata per shop

La guida architetturale inizialmente prevedeva una policy `SELF_OWNERSHIP`
distinta per `SHOP_CUSTOMER`. In fase di design (18-04-2026) si è deciso di
unificarla con `BA_OWNERSHIP` perché:

* Il ruolo anagrafico è lo stesso (`CL`) per entrambi: la differenza è solo
  nel namespace API e nel profilo capability.
* Lo scope dati è identico: "vedi solo i BA del tuo soggetto_ruolo".
* Meno policy da mantenere, meno rischio di divergenza.

---

{% include-markdown "signature-core.md" %}
