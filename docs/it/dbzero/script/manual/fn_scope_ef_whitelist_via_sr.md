## Documentazione Concettuale – Funzione `script.fn_scope_ef_whitelist_via_sr`

> **Vedi anche**
>
[Linee guida SQL — sezione 10 RLS](/linee-guida-sql#10-row-level-security-rls)
>
**Funzioni correlate:**
>
[script.fn_scope_ef_whitelist](/dbzero/script/funzioni/fn_scope_ef_whitelist) (adapter PK / entry-point)
> [script.fn_check_user_emittente_scope](/dbzero/script/funzioni/fn_check_user_emittente_scope) (canonica)
>
**Tabelle correlate:**
>
[anagrafiche.emittenti_fiscali](/dbzero/anagrafiche/tabelle/emittenti_fiscali)

---
### 🎯 Scopo Principale
(rev 2026-06-01)

Adapter **SR** dello scope `EF_WHITELIST`: per le tabelle che portano
l'emittente con la convenzione **`emittente_soggetto_ruolo_id`**
(`vendite.fatture`, `vendite.fatturazione_lotti`), risolve il `soggetto_ruolo`
emittente alla chiave nativa della whitelist (`emittente_fiscale_id`, PK) e
**delega** alla canonica `script.fn_check_user_emittente_scope`.

Nessuna logica di whitelist è ri-scritta qui: la regola vive una sola volta
nella canonica.

---

### Parametri di input

| Parametro | Tipo | Descrizione |
|-----------|------|-------------|
| `p_auth_user_id` | `integer` | Utente applicativo (dal GUC `app.current_user_id`). |
| `p_emittente_sr_id` | `anagrafiche.emittenti_fiscali.soggetto_ruolo_id%TYPE` | `soggetto_ruolo_id` dell'emittente target (colonna `emittente_soggetto_ruolo_id`). |

---

### Output

`BOOLEAN` — esito della canonica. Vedi
[`fn_scope_ef_whitelist`](/dbzero/script/funzioni/fn_scope_ef_whitelist) per la
tabella di semantica completa.

---

### Risoluzione SR → PK

```
emittente_soggetto_ruolo_id (= p_emittente_sr_id)
    → emittenti_fiscali.soggetto_ruolo_id
    → emittenti_fiscali.id  (= emittente_fiscale_id)
    → fn_check_user_emittente_scope(auth_user_id, emittente_fiscale_id)
```

> **Nota fail-closed**: se l'`emittente_sr_id` non è mappato in
> `emittenti_fiscali` (riga orfana), la risoluzione dà `NULL` e la canonica
> con `emittente_fiscale_id` NULL ritorna `false` per operatori con whitelist
> valorizzata (la riga risulta invisibile). Su whitelist vuota / super_admin
> ritorna `true`.

---

### Regole implementative

* `LANGUAGE sql`, `STABLE`: inlineable nei predicati `USING`.
* Speculare a `fn_scope_ef_whitelist_via_fattura` (che risolve via fattura → SR).

---

{% include-markdown "signature-core.md" %}
