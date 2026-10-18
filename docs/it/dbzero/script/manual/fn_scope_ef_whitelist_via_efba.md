## Documentazione Concettuale – Funzione `script.fn_scope_ef_whitelist_via_efba`

> **Vedi anche**
>
[Linee guida SQL — sezione 10 RLS](/linee-guida-sql#10-row-level-security-rls)
>
**Funzioni correlate:**
>
[script.fn_get_emittenti_scope_sr_ids](/dbzero/script/funzioni/fn_get_emittenti_scope_sr_ids) (scope SR canonico)
> [script.fn_check_ba_visible_for_emittenti](/dbzero/script/funzioni/fn_check_ba_visible_for_emittenti) (visibilità BA via efba)
> [script.fn_scope_ef_whitelist](/dbzero/script/funzioni/fn_scope_ef_whitelist) (adapter PK / entry-point)
>
**Tabelle correlate:**
>
[anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account)
> [anagrafiche.emittenti_fiscali_billing_account](/dbzero/anagrafiche/tabelle/emittenti_fiscali_billing_account)

---
### 🎯 Scopo Principale
(rev 2026-06-01 — Ondata 2)

Adapter **via_efba** dello scope `EF_WHITELIST` per `anagrafiche.billing_account`,
che **non ha colonna emittente propria**. La visibilità operatore di un BA si
ricava dalla mappatura `emittenti_fiscali_billing_account` (efba,
specifico-o-default): un operatore vede il BA se è raggiungibile da **almeno uno
degli emittenti nel proprio scope**.

Riusa due canonici, **nessuna logica duplicata**:
`script.fn_get_emittenti_scope_sr_ids` (scope dell'operatore) **∩**
`script.fn_check_ba_visible_for_emittenti` (raggiungibilità del BA).
Allinea la RLS al filtro già attivo lato ricerca (`fn_search_soggetti_universale`).

---

### Parametri di input

| Parametro | Tipo | Descrizione |
|-----------|------|-------------|
| `p_auth_user_id` | `integer` | Utente applicativo (dal GUC `app.current_user_id`). |
| `p_billing_account_id` | `anagrafiche.billing_account.id%TYPE` | BA target (la propria `id` della riga, nella policy). |

---

### Output / Semantica

| Stato attore / scope | Risultato |
|----------------------|-----------|
| `auth_user_id` **NULL** (batch) | `true` (nessun filtro) |
| Scope `NULL` (super_admin / whitelist vuota) | `true` (accesso globale) |
| Scope `'{}'` (no identità OPERATORE attiva) | `false` (**fail-closed**) |
| Scope whitelist | `true` solo se il BA è visibile via efba per almeno un emittente in scope |

---

### Regole implementative

* `LANGUAGE plpgsql`, `STABLE`. Lo **scope** è query-constant (dipende solo
  da `auth_user_id`): valutato una volta. Il costo **per-riga** è il lookup
  `efba` dentro `fn_check_ba_visible_for_emittenti`, con indice su `efba`.
  *(Il «benchmark pre-`ENABLE` §12» che questa riga citava è stato ritirato
  il 2026-09-11 — vedi `analisi-attivazione-rls-db.md` §12.)*
* `billing_account` ha già le policy portale/shop: la policy operatore è
  **additiva** (OR), gated su `ruolo_applicativo = 'OPERATORE'`.

---

### Esempio d'uso

```sql
CREATE POLICY rls_billing_account_ef_whitelist ON anagrafiche.billing_account
    AS PERMISSIVE FOR SELECT
    USING (
        current_setting('app.ruolo_applicativo', true) = 'OPERATORE'
        AND script.fn_scope_ef_whitelist_via_efba(
            NULLIF(current_setting('app.current_user_id', true), '')::integer,
            id
        )
    );
```

---

### ⭐ rev 2026-10-18 — non sta più nelle policy

ChangeSet `20261018-49`: da plpgsql a sql, la stessa composizione delle sue policy: `fn_scope_ef_perimetro(fn_get_emittenti_scope_sr_ids(utente), fn_get_ba_emittente_sr_id(ba))`, in convenzione soggetto_ruolo. Stesse risposte. Le policy non la chiamano più (`20261018-50`):
calcolano il perimetro una volta per istruzione con
[`fn_scope_ef_perimetro`](fn_scope_ef_perimetro.md). Resta per la domanda su **un**
emittente. Brief `brief-db-plancache-funzioni-con-query-incorporate` §5quinquies
(ondata 2).

{% include-markdown "signature-core.md" %}
