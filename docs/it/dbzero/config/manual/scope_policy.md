## 📘 Documentazione Concettuale – Tabella `config.scope_policy`

> 👀 **Vedi anche**
>
Architettura di riferimento:
>
[Architettura Multi-Face Auth](/guide/architettura-multi-face-auth)
> [Linee guida SQL — sezione 10 Row Level Security](/linee-guida-sql#10-row-level-security-rls)
>
Tabelle correlate:
>
[config.identita_scope_bindings](/dbzero/config/tabelle/identita_scope_bindings)
> [anagrafiche.identita_digitali](/dbzero/anagrafiche/tabelle/identita_digitali)
> [config.user_emittenti_fiscali](/dbzero/config/tabelle/user_emittenti_fiscali) (sorgente EF_WHITELIST)
>
Funzioni scope installate:
>
[script.fn_scope_ef_whitelist](/dbzero/script/funzioni/fn_scope_ef_whitelist)
> [script.fn_scope_ba_ownership](/dbzero/script/funzioni/fn_scope_ba_ownership)
> [script.fn_scope_fornitore_ownership](/dbzero/script/funzioni/fn_scope_fornitore_ownership)

---
### 🎯 Scopo Principale
(latest revision 18-04-2026)

La tabella **`config.scope_policy`** è il **registro delle policy di scope**
disponibili nel modello multi-face auth. Ogni policy è una strategia di
scoping dati implementata da una funzione PL/pgSQL; il campo `funzione_db`
contiene il riferimento alla funzione nel formato `schema.nome_funzione`.

Le policy sono il meccanismo unificato per limitare cosa vede un'identità
digitale nelle query. Sono anche la base su cui poggeranno le Row Level
Security (§4.9 WIP multi-face-auth) sulle tabelle dati sensibili.

---

### Colonne chiave

| Colonna | Scopo |
|---------|-------|
| `codice` | Identificativo univoco della policy (es. `EF_WHITELIST`, `BA_OWNERSHIP`, `FORNITORE_OWNERSHIP`). |
| `descrizione` | Descrizione human-readable del comportamento (usata da UI admin e documentazione). |
| `funzione_db` | `schema.nome` della funzione che implementa la policy. **Firma fissa**: `(p_identita_id BIGINT, p_target_id BIGINT) RETURNS BOOLEAN`. |
| `attivo` | Se `false`, la policy non è più applicata. |

---

### Firma contrattuale delle funzioni

Tutte le funzioni referenziate da `funzione_db` devono rispettare la stessa
firma per essere intercambiabili in contesti generici (es. risoluzione
dinamica nelle RLS):

```sql
schema.fn_scope_xxx(
    p_identita_id BIGINT,  -- anagrafiche.identita_digitali.id
    p_target_id   BIGINT   -- id del target da verificare (BA, fornitore_sr, ...)
) RETURNS BOOLEAN
```

Convenzioni:

* Marcata `STABLE` (legge DB, non modifica) per favorire inlining nel planner.
* `LANGUAGE sql` dove possibile (inlineable più aggressivamente di plpgsql).
* **Fail-closed**: identità inesistente / non attiva → `false`.

---

### Policy seed (18-04-2026)

| id | codice | funzione_db | Semantica |
|----|--------|-------------|-----------|
| 1 | `EF_WHITELIST` | `script.fn_scope_ef_whitelist` | Whitelist emittenti fiscali (legacy). Whitelist vuota = accesso globale. |
| 2 | `BA_OWNERSHIP` | `script.fn_scope_ba_ownership` | Identità cliente (CLIENTE_PORTALE / SHOP_CUSTOMER) vede solo i billing_account del proprio soggetto_ruolo. |
| 3 | `FORNITORE_OWNERSHIP` | `script.fn_scope_fornitore_ownership` | Identità FORNITORE_PORTALE vede solo i dati del proprio soggetto_ruolo fornitore. |

---

### Evoluzioni future

Il modello supporta l'aggiunta di nuove policy senza modifiche strutturali:

* `AGENTE_OWNERSHIP` — agente di vendita vede solo i propri clienti
* `MULTI_TENANT` — filtro per gestore (se in futuro il DB diventa multi-tenant)
* `API_CLIENT_SCOPE` — per identità `API_CLIENT` con scope per tenant

Ogni nuova policy richiede: una funzione `script.fn_scope_*` + una riga qui
+ eventuali binding in `identita_scope_bindings`.

---

{% include-markdown "signature-core.md" %}
