## Documentazione Concettuale – Funzione `script.fn_scope_ef_whitelist`

> **Vedi anche**
>
Architettura di riferimento:
>
[Architettura Multi-Face Auth](/guide/architettura-multi-face-auth)
> [Linee guida SQL — sezione 10 RLS](/linee-guida-sql#10-row-level-security-rls)
>
**Funzioni correlate:**
>
[script.fn_check_user_emittente_scope](/dbzero/script/funzioni/fn_check_user_emittente_scope) (canonica)
> [script.fn_scope_ef_whitelist_via_sr](/dbzero/script/funzioni/fn_scope_ef_whitelist_via_sr) (adapter SR)
> [script.fn_scope_ef_whitelist_via_fattura](/dbzero/script/funzioni/fn_scope_ef_whitelist_via_fattura) (adapter via fattura)
>
**Tabelle correlate:**
>
[config.user_emittenti_fiscali](/dbzero/config/tabelle/user_emittenti_fiscali)
> [anagrafiche.emittenti_fiscali](/dbzero/anagrafiche/tabelle/emittenti_fiscali)

---
### 🎯 Scopo Principale
(rev 2026-06-01 — refactor RLS: delega alla canonica)

La funzione **`script.fn_scope_ef_whitelist`** è l'**adapter PK** (entry-point
delle policy RLS) dello scope `EF_WHITELIST` per le tabelle che portano
l'emittente con la convenzione **`emittente_fiscale_id`** (preventivi,
contratti, offerte_commerciali, documenti_generati, pratiche, ordini).

> ⚠️ **Cambio firma (2026-06-01).** Prima la funzione prendeva
> `(identita_id, emittente_sr_id)` e **ri-implementava** la logica di whitelist
> (senza bypass SUPER_ADMIN). Ora prende **`(auth_user_id, emittente_fiscale_id)`**
> e **delega** alla canonica `script.fn_check_user_emittente_scope`: una sola
> sede della regola, condivisa con il write-guard (read e write unificati,
> bypass SUPER_ADMIN ereditato — chiude il bug "C7" della RLS-read).

---

### Parametri di input

| Parametro | Tipo | Descrizione |
|-----------|------|-------------|
| `p_auth_user_id` | `integer` | Utente applicativo (dal GUC `app.current_user_id`, `auth_user.id` Django). |
| `p_emittente_fiscale_id` | `anagrafiche.emittenti_fiscali.id%TYPE` | PK dell'emittente target (colonna `emittente_fiscale_id` sulle tabelle PK). |

---

### Output

`BOOLEAN` — `true` se l'utente può accedere al target, `false` altrimenti.

---

### Semantica (ereditata dalla canonica)

| Stato attore / whitelist | Risultato |
|--------------------------|-----------|
| `auth_user_id` **NULL** (job batch/sistema) | `true` (nessun filtro) |
| **SUPER_ADMIN** | `true` (bypass totale) |
| Nessuna **identità OPERATORE attiva** | `false` (**fail-closed**) |
| Identità OPERATORE attiva, **whitelist vuota** | `true` (accesso globale legacy) |
| Whitelist valorizzata, target **in lista** | `true` |
| Whitelist valorizzata, target **non in lista** | `false` |

La regola vive una sola volta in
[`fn_check_user_emittente_scope`](/dbzero/script/funzioni/fn_check_user_emittente_scope):
questa funzione è un wrapper thin che si limita a delegare.

---

### Le tre varianti dello scope

| Funzione | Convenzione | Quando |
|---|---|---|
| `fn_scope_ef_whitelist(auth_user_id, emittente_fiscale_id)` | **PK** | tabelle con `emittente_fiscale_id` |
| `fn_scope_ef_whitelist_via_sr(auth_user_id, emittente_sr_id)` | **SR** | tabelle con `emittente_soggetto_ruolo_id` (fatture, fatturazione_lotti) |
| `fn_scope_ef_whitelist_via_fattura(auth_user_id, fattura_id)` | **via fattura** | tabelle figlie senza colonna emittente (fatture_scadenze) |

Gli adapter SR / via_fattura **risolvono** l'emittente alla convenzione PK e poi
chiamano la canonica: la logica di whitelist non è duplicata in nessuno di essi.

---

### Regole implementative

* `LANGUAGE sql`, `STABLE`: il planner la incorpora, e nel predicato resta la
  chiamata alla canonica.
* `%TYPE` sul parametro emittente per coerenza con la colonna sorgente.
* ⛔ **Il perimetro si calcola per riga.** Fino al 2026-10-18 questa pagina
  diceva che super admin e veste «dipendono solo dall'attore → valutati una
  volta sola dal planner». Non era vero: la canonica è plpgsql, opaca, e una
  policy che chiama questa funzione ricalcola **a ogni riga** super admin,
  veste utilizzabile, giorno operativo e whitelist.

### ⭐ rev 2026-10-18 — le policy dirette non la chiamano più

Le policy ef_whitelist con la colonna emittente (13 scritte a mano e quelle
dello storico, generate da `dbops.fn_storico_arma_scope`) usano ora
[`fn_scope_ef_perimetro`](fn_scope_ef_perimetro.md). Il perimetro
([`fn_get_emittenti_scope_pk_ids`](fn_get_emittenti_scope_pk_ids.md)) arriva in
una sottoquery non correlata, che PostgreSQL valuta **una volta per
istruzione**. ChangeSet `20261018-16…-29`, brief
`brief-db-plancache-funzioni-con-query-incorporate` §5quinquies.

Questa funzione resta per chi chiede su **un** emittente: gli adattatori
`via_*`, `fn_scope_email_ambito`, il repository dei titoli IVA. Stesse
risposte di prima.

---

### Esempio d'uso

**Da una policy RLS** (convenzione PK):

```sql
CREATE POLICY rls_preventivi_ef_whitelist ON vendite.preventivi
    AS PERMISSIVE FOR SELECT
    USING (
        current_setting('app.ruolo_applicativo', true) = 'OPERATORE'
        AND script.fn_scope_ef_whitelist(
            NULLIF(current_setting('app.current_user_id', true), '')::integer,
            emittente_fiscale_id
        )
    );
```

---

{% include-markdown "signature-core.md" %}
