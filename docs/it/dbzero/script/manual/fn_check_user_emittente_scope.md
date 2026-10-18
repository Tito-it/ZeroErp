## Documentazione Concettuale – Funzione `script.fn_check_user_emittente_scope`

> **Vedi anche**
>
**Tabelle correlate:**
>
[config.user_emittenti_fiscali](/dbzero/config/tabelle/user_emittenti_fiscali)
> [anagrafiche.emittenti_fiscali](/dbzero/anagrafiche/tabelle/emittenti_fiscali)
>
**Funzioni correlate:**
>
[script.fn_is_super_admin](/dbzero/script/funzioni/fn_is_super_admin)
> [script.fn_has_identita_attiva](/dbzero/script/funzioni/fn_has_identita_attiva)
> [script.trgfn_guard_emittente_scope](/dbzero/script/funzioni/trgfn_guard_emittente_scope)

---
### 🎯 Scopo Principale
(latest review 08-03-2026)
La funzione **`script.fn_check_user_emittente_scope`** verifica se un utente ha
accesso a uno specifico emittente fiscale. Pensata per i trigger defense-in-depth
su tabelle operative (fatture, pagamenti).

Funzione `fn_check_*`: puro boolean, no RAISE.

> **Canonica unica read+write (dal 2026-06-01).** Questa è la **sede unica**
> della regola di scope emittente. La delegano sia il **write-guard**
> ([`trgfn_guard_emittente_scope`](/dbzero/script/funzioni/trgfn_guard_emittente_scope))
> sia la **RLS in lettura**, tramite gli adapter
> [`fn_scope_ef_whitelist`](/dbzero/script/funzioni/fn_scope_ef_whitelist) (PK),
> `…_via_sr` e `…_via_fattura`. Modificare la regola qui la propaga a entrambi
> i lati: nessuna duplicazione. Il bypass SUPER_ADMIN vive qui (chiude il bug
> "C7" della vecchia RLS-read che ne era priva).

---

### Parametri di input

| Parametro                | Tipo                                    | Descrizione                                |
| ------------------------ | --------------------------------------- | ------------------------------------------ |
| `p_auth_user_id`         | `integer`                               | ID utente Django (o `NULL` per job batch). |
| `p_emittente_fiscale_id` | `anagrafiche.emittenti_fiscali.id%TYPE` | ID emittente fiscale da verificare.        |

---

### Output

Ritorna `boolean`.

---

### Regole di risoluzione

1. **`p_auth_user_id` NULL** → `false` (dal 2026-10-04, Q-1: era `true`, «job batch»)
2. **Emittente attivo di sessione** (`app.current_emittente_id`) diverso da quello chiesto → `false`, anche per il super admin
3. **SUPER_ADMIN** → `true` (accesso completo a tutti gli emittenti)
4. **Nessuna veste OPERATORE utilizzabile** → `false`
5. **Whitelist vuota** (nessuna riga in `user_emittenti_fiscali`) → `false`: **fail-closed**, la riga mancante e' un errore di configurazione, non un permesso
6. **Whitelist con righe** → `true` solo se l'emittente e presente nella whitelist

### ⭐ rev 2026-10-18 — una regola, due forme

ChangeSet `20261018-18`. Le regole qui sopra stavano scritte **due volte**:
qui (la domanda su un emittente) e in
[`fn_get_emittenti_scope_pk_ids`](fn_get_emittenti_scope_pk_ids.md) (l'insieme
degli emittenti visibili, per il backend). Ora la canonica chiede l'insieme a
`_pk_ids` e lo interroga con
[`fn_scope_ef_perimetro`](fn_scope_ef_perimetro.md), la stessa funzione delle
policy. Stesse risposte: lo provano i pgTAP della canonica e il test di parità
`script/test-fn-get-emittenti-scope-pk-ids-and-parity`.

⚠️ **Rev 2026-10-18 bis (`20261018-23`)**: con un emittente attivo di sessione,
per un emittente diverso risponde `false` **senza** calcolare il perimetro (è
al più `{attivo}`). La canonica si chiama per riga (adattatori, guard): senza
l'uscita anticipata costava fino a 4 volte tanto a chiamata.

⚠️ Le policy ef_whitelist dirette **non passano più di qui**: calcolano il
perimetro una volta per istruzione (vedi `fn_scope_ef_perimetro`). Questa
funzione resta la sede per chi chiede su **un** emittente: write-guard, verbi
DEFINER, adattatori `via_*`.

---

### Regole principali

* Funzione **STABLE**.
* Chiamata internamente da `trgfn_guard_emittente_scope` per i trigger defense-in-depth.
* Puo essere chiamata direttamente dal backend per controlli preventivi.

---

### Esempio d'uso

```sql
-- Job batch (nessun utente)
SELECT script.fn_check_user_emittente_scope(NULL, 1);
-- Ritorna: true

-- ADMIN
SELECT script.fn_check_user_emittente_scope(42, 1);
-- Ritorna: true (se ruolo = ADMIN)

-- OPERATIVO con whitelist
SELECT script.fn_check_user_emittente_scope(42, 99);
-- Ritorna: false (se 99 non e nella whitelist)
```

---

{% include-markdown "signature-core.md" %}
