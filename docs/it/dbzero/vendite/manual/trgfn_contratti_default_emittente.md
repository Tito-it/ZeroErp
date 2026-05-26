## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_contratti_default_emittente()`

> 👀 **Vedi anche**
>
> Tabelle:
> [vendite.contratti](/dbzero/vendite/tabelle/contratti)
> [anagrafiche.emittenti_fiscali](/dbzero/anagrafiche/tabelle/emittenti_fiscali)
> [config.user_emittenti_fiscali](/dbzero/config/tabelle/user_emittenti_fiscali)
>
> Funzioni correlate:
> [script.fn_resolve_emittente_for_user](/dbzero/script/funzioni/fn_resolve_emittente_for_user)
> [anagrafiche.fn_get_emittente_fiscale_pk](/dbzero/anagrafiche/funzioni/fn_get_emittente_fiscale_pk)
> [vendite.trgfn_contratti_guard_emittente_ba](/dbzero/vendite/funzioni/trgfn_contratti_guard_emittente_ba)
>
> Pattern simmetrico:
> [vendite.trgfn_preventivi_default_emittente](/dbzero/vendite/funzioni/trgfn_preventivi_default_emittente)

---

### 🎯 Scopo Principale

(rev 2026-05-26)

Valorizza automaticamente `vendite.contratti.emittente_fiscale_id` a
**INSERT-time**, leggendo l'operatore loggato dalla GUC
`app.current_user_id` (popolata da `JwtAuditAuthentication` su ogni
richiesta API autenticata) e risolvendone l'emittente fiscale tramite
`script.fn_resolve_emittente_for_user`.

**Modello user-derived**: l'emittente di un contratto è lo snapshot
dell'emittente dell'operatore che ha creato il record, non del BA.
Questo garantisce che il contratto rimanga nell'emittente corretto anche
se il BA viene successivamente riassegnato.

Applicata dal trigger `trg_contratti_a10_default_emittente_ins`
(fase `_a10_`, `BEFORE INSERT`).

---

### Regola skip — payload esplicito

Se `NEW.emittente_fiscale_id IS NOT NULL` la funzione restituisce
`NEW` senza modifiche. Questo consente:

- **Push da offerta** (`fn_push_offerta_a_contratto`, rev2): copia
  `v_offerta.emittente_fiscale_id` esplicitamente nell'INSERT — il
  trigger salta, il guard `trgfn_contratti_guard_emittente_ba` valida
  la coerenza.
- **Admin globale** (operatore senza riga in `user_emittenti_fiscali`):
  può specificare `emittente_fiscale_id` nel payload.
- **Seed / migration data / pgAgent**: il chiamante deve valorizzare il
  campo esplicitamente, altrimenti l'assenza della GUC causa errore.

---

### Firing order nella fase `_a10_`

I trigger BEFORE INSERT su `vendite.contratti` si ordinano
alfabeticamente per nome. L'ordine per l'emittente è:

| Trigger | Fase/ordine | Evento | Effetto |
|---|---|---|---|
| `trg_contratti_a10_default_emittente_ins` | `_a10_default_*` | INSERT | Setta `emittente_fiscale_id` da GUC |
| `trg_contratti_a10_guard_emittente_ba_ins_upd` | `_a10_guard_*` | INSERT, UPDATE OF | Valida BA↔emittente (vede già il valore settato dal default) |

---

### Errori sollevati

| Codice | id | Quando |
|---|---|---|
| `E_CONTRATTO_EMITTENTE_NON_RISOLTO` | 463 | GUC `app.current_user_id` vuota e payload senza `emittente_fiscale_id` |
| `E_CONTRATTO_EMITTENTE_NON_RISOLTO` | 463 | Operatore admin globale senza riga in `user_emittenti_fiscali` e senza `emittente_fiscale_id` esplicito nel payload |

---

### Contract GUC per chiamanti non-API

| Contesto | Comportamento |
|---|---|
| API Django (`JwtAuditAuthentication`) | GUC `app.current_user_id` sempre settata — il trigger risolve automaticamente |
| pgAgent / Liquibase / DBA | GUC non settata — **il chiamante DEVE valorizzare `emittente_fiscale_id` nel payload** |
| Push da offerta (`fn_push_offerta_a_contratto`) | Valore propagato esplicitamente dall'offerta — skip automatico |

---

### Note operative

- Il trigger AFTER INSERT `trg_contratti_a10_emittenti_fiscali_require_attivo_ins_upd`
  garantisce che `emittente_fiscale_id` non possa puntare a un EF con
  `attivo = false` (definito nella stessa migration 20260526-03).
- Il campo `emittente_fiscale_id` diventa NOT NULL dopo il backfill
  (migration 90_end/20260526-08).

---

{% include-markdown "signature-core.md" %}
