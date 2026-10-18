## Documentazione Concettuale – Funzione `script.fn_scope_ef_whitelist_via_coppia`

> **Vedi anche**
>
[Linee guida SQL — sezione 10 RLS](/linee-guida-sql#10-row-level-security-rls)
>
**Funzioni correlate:**
>
[script.fn_scope_ef_whitelist_via_efba](/dbzero/script/manual/fn_scope_ef_whitelist_via_efba) (la scope del billing account, a cui delega)
>
**Tabelle correlate:**
>
[anagrafiche.istanze_dati_precontrattuali](/dbzero/anagrafiche/tabelle/istanze_dati_precontrattuali)
> [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account)

---
### 🎯 Scopo Principale
(rev 2026-10-08)

Adapter **via coppia (istanza, utility)** dello scope `EF_WHITELIST`: per le
tabelle che non portano il billing account ma la coppia (istanza, utility),
risale al **billing account della coppia** e delega alla sua scope. L'operatore
vede la riga se vede il billing account.

La coppia individua al massimo un billing account (`uq_billing_instance_utility`):
una utility di un'istanza ha il suo billing account, e i dati che ne dipendono
appartengono al suo cliente.

---

### Parametri di input

| Parametro | Tipo | Descrizione |
|-----------|------|-------------|
| `p_auth_user_id` | `integer` | Utente applicativo (dal GUC `app.current_user_id`). |
| `p_istanza_utility_id` | `bigint` | Istanza della riga. |
| `p_utility_id` | `integer` | Utility della riga. |

---

### Output

`BOOLEAN` — l'esito della scope del billing account. Billing account fuori
perimetro (invisibile sotto la sua RLS) o coppia senza billing account: `false`,
chiuso nel dubbio. Il super amministratore vede tutto.

---

### Chi la usa

* la policy `rls_istanze_dati_precontrattuali_ef_whitelist` su
  `anagrafiche.istanze_dati_precontrattuali` (dal 2026-10-08): i dati
  precontrattuali di un cliente si vedono e si scrivono solo da chi vede il suo
  billing account.

---

### Note di migrazione

* **2026-10-08** (`20261008-74`): nasce. Il presidio del perimetro RLS aveva
  segnalato i dati precontrattuali come figli del billing account (FK
  `fk_idp_billing_account_coppia`) senza RLS; decisione di Tid: la RLS segue il
  billing account. Brief: brief-db-istanza-nasce-col-ba (§6.13).

### ⚠️ 2026-10-18 — l'unico adattatore rimasto in una policy

Le altre policy ef_whitelist calcolano il perimetro una volta per istruzione
(D-3b-2 di `brief-db-plancache-funzioni-con-query-incorporate`). Questa no: la
chiave è una **coppia** di colonne (istanza, utility) e il risolutore
`fn_resolve_emittente_fiscale_id` prende un valore solo. Debito dichiarato nel
presidio `script/test-scope-ef-perimetro-una-volta-per-istruzione-v1` (test 5).
Chiama `via_efba`, che è già nella forma nuova.
