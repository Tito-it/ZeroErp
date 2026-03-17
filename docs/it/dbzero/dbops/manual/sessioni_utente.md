## Documentazione Concettuale -- Tabella `dbops.sessioni_utente`

> **Vedi anche**
>
**Piano di riferimento:**
>
[Audit Sessioni, Request Logging e Sicurezza Token](/dev/work-in-progress/Audit-logging-sessionii-request-token)
>
**Tabelle correlate:**
>
[dbops.request_log](/dbzero/dbops/manual/request_log) -- correlazione via `request_id`
> [dbops.audit_log](/dbzero/dbops/manual/audit_log) -- pattern retention `cleanup_at`
>
Scopo Principale

(latest review 05-03-2026)

`dbops.sessioni_utente` e` la tabella di **audit sessioni JWT**. Traccia il ciclo
di vita completo dei token di autenticazione: emissione (login), rinnovo (refresh),
revoca esplicita, logout e scadenza naturale.

Risponde alle domande:

* Quando un utente ha fatto login?
* Quante volte e da dove ha refreshato il token?
* Il token e` stato revocato? Quando e perche`?

---

### Campi chiave

| Colonna | Ruolo |
|---------|-------|
| `auth_user_id` | Riferimento all'utente Django (`auth_user.id`). |
| `evento` | Tipo evento: `LOGIN`, `REFRESH`, `LOGOUT`, `SCADENZA`, `REVOCA`. Validato da CHECK. |
| `jti` | JWT ID (`jti` claim) -- identifica univocamente il token coinvolto. |
| `ip_address` | IP del client al momento dell'evento. |
| `user_agent` | User-Agent HTTP del client. |
| `request_id` | UUID dalla `RequestContextMiddleware`, consente correlazione 1:1 con `dbops.request_log`. |
| `dettaglio` | JSONB per dati aggiuntivi (es. motivo revoca, errore specifico). |
| `tx_id` | Transaction ID (pattern standard dbops, trigger `trgfn_tx_id_managed`). |
| `cleanup_at` | Timestamp retention per pulizia schedulata (pattern `dbops.audit_log`). |

---

### Caratteristiche tecniche

* **Insert-only**: la tabella non prevede UPDATE. Non ha colonne `data_update` / `user_update`.
* **No storicizzazione**: essendo gia` un log, non necessita di snapshot temporali.
* **Retention**: gestita da `cleanup_at` + job schedulato (pattern `dbops.fn_purge_cleanup_expired`).
* **Grant**: automatici via CI grant dinamico su schema `dbops`.

---

### Indici

| Nome | Colonne | Scopo |
|------|---------|-------|
| `ix_sessioni_utente_auth_user_id` | `auth_user_id` | Ricerca sessioni per utente. |
| `ix_sessioni_utente_data_insert` | `data_insert DESC` | Ordinamento cronologico, query recenti. |
| `ix_sessioni_utente_jti` | `jti` | Lookup per token ID (revoca, correlazione refresh). |
| `ix_sessioni_utente_cleanup_at` | `cleanup_at` | Supporto job pulizia retention. |

---

### Ruolo operativo

1. Le view JWT override (`AuditTokenObtainPairView`, `AuditTokenRefreshView`) inseriscono
   un record ad ogni login e refresh riuscito.
2. La revoca token (Area 3 -- blacklist) inserisce un record `REVOCA`.
3. Il job di pulizia schedulato elimina i record oltre la retention configurata.
4. L'API di consultazione (fase 2) espone i dati filtrati per utente e data.

---

### Correlazione con request_log

Il campo `request_id` condiviso tra `sessioni_utente` e `request_log` consente
di correlare ogni evento sessione alla request HTTP che lo ha generato:

```sql
SELECT s.evento, s.jti, r.method, r.path, r.status_code
  FROM dbops.sessioni_utente s
  JOIN dbops.request_log r USING (request_id)
 WHERE s.auth_user_id = :user_id;
```

---

> **In sintesi**: `sessioni_utente` completa il sistema di audit fornendo visibilita`
> sul ciclo di vita delle sessioni JWT, informazione finora assente nel sistema.

---

{% include-markdown "signature-core.md" %}
