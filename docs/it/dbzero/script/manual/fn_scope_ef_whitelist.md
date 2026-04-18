## Documentazione Concettuale – Funzione `script.fn_scope_ef_whitelist`

> **Vedi anche**
>
Architettura di riferimento:
>
[Architettura Multi-Face Auth](/guide/architettura-multi-face-auth)
> [Linee guida SQL — sezione 10 RLS](/linee-guida-sql#10-row-level-security-rls)
>
**Tabelle correlate:**
>
[config.user_emittenti_fiscali](/dbzero/config/tabelle/user_emittenti_fiscali)
> [anagrafiche.emittenti_fiscali](/dbzero/anagrafiche/tabelle/emittenti_fiscali)
> [anagrafiche.identita_digitali](/dbzero/anagrafiche/tabelle/identita_digitali)
> [config.scope_policy](/dbzero/config/tabelle/scope_policy)

---
### 🎯 Scopo Principale
(latest review 18-04-2026)

La funzione **`script.fn_scope_ef_whitelist`** implementa la policy di scope
`EF_WHITELIST`: verifica che un'identità digitale possa vedere dati riferiti
a uno specifico emittente fiscale in base alla whitelist legacy
`config.user_emittenti_fiscali`.

È il **ponte** tra il modello legacy (whitelist di emittenti per `auth_user`)
e il nuovo framework di scope (registro `scope_policy` + binding per identità).
Durante la transizione, la funzione legge direttamente dai dati legacy:
nessuna duplicazione di configurazione.

---

### Parametri di input

| Parametro | Tipo | Descrizione |
|-----------|------|-------------|
| `p_identita_id` | `anagrafiche.identita_digitali.id%TYPE` | Identità corrente (dal GUC `app.current_identita_id`). |
| `p_emittente_sr_id` | `anagrafiche.emittenti_fiscali.soggetto_ruolo_id%TYPE` | `soggetto_ruolo_id` dell'emittente target (colonna presente sulle tabelle operazionali come `emittente_soggetto_ruolo_id`). |

---

### Output

`BOOLEAN` — `true` se l'identità può accedere al target, `false` altrimenti.

---

### Semantica

| Stato identità / whitelist | Risultato |
|----------------------------|-----------|
| Identità **inesistente o non attiva** | `false` (**fail-closed**) |
| Identità attiva, **whitelist vuota** (nessuna riga in `user_emittenti_fiscali`) | `true` (accesso globale — comportamento legacy per operatori senza restrizioni) |
| Identità attiva, whitelist valorizzata, target **in lista** | `true` |
| Identità attiva, whitelist valorizzata, target **non in lista** | `false` |

---

### Regole implementative

* `LANGUAGE sql`, `STABLE`: inlineable dal planner nelle RLS future.
* `%TYPE` su firma per coerenza automatica con le colonne sorgente.
* **Gate attivo esplicito**: un CTE filtra già `id.attivo = true` e il
  risultato finale fa `AND EXISTS(SELECT 1 FROM ctx)` come gate di sicurezza
  per evitare il pattern "vacuous true" su CTE vuote.
* L'identità deve essere `OPERATORE` per avere `auth_user_id` con righe in
  `user_emittenti_fiscali`: per altri ruoli la funzione ritorna `true` solo
  se la whitelist è vuota (comportamento coerente, ma questa policy non è
  tipicamente abbinata a ruoli non-OPERATORE).

---

### Catena JOIN

```
identita_digitali.auth_user_id
    → user_emittenti_fiscali.auth_user_id
    → user_emittenti_fiscali.emittente_fiscale_id
    → emittenti_fiscali.id
    → emittenti_fiscali.soggetto_ruolo_id  (= p_emittente_sr_id)
```

---

### Esempio d'uso

**Da una policy RLS** (§4.9 WIP multi-face-auth):

```sql
CREATE POLICY rls_fatture_ef_whitelist ON vendite.fatture
    FOR SELECT
    USING (
        script.fn_scope_ef_whitelist(
            NULLIF(current_setting('app.current_identita_id', true), '')::bigint,
            emittente_soggetto_ruolo_id
        )
    );
```

**Da codice applicativo** (test pgTAP, backend):

```sql
SELECT script.fn_scope_ef_whitelist(42, 100);
-- Ritorna: true/false
```

---

{% include-markdown "signature-core.md" %}
