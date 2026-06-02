## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_ordini_default_emittente()`

> 👀 **Vedi anche**
>
> Tabelle:
> [vendite.ordini](/dbzero/vendite/tabelle/ordini)
> [anagrafiche.emittenti_fiscali](/dbzero/anagrafiche/tabelle/emittenti_fiscali)
> [config.user_emittenti_fiscali](/dbzero/config/tabelle/user_emittenti_fiscali)
>
> Funzioni correlate:
> [script.fn_resolve_emittente_for_user](/dbzero/script/funzioni/fn_resolve_emittente_for_user)
> [vendite.trgfn_ordini_guard_emittente_ba](/dbzero/vendite/funzioni/trgfn_ordini_guard_emittente_ba)
>
> Pattern simmetrico:
> [vendite.trgfn_contratti_default_emittente](/dbzero/vendite/funzioni/trgfn_contratti_default_emittente)

---

### 🎯 Scopo Principale

(rev 2026-06-01)

Valorizza automaticamente `vendite.ordini.emittente_fiscale_id` a
**INSERT-time**, leggendo l'operatore loggato dalla GUC
`app.current_user_id` (popolata da `JwtAuditAuthentication` su ogni
richiesta API autenticata) e risolvendone l'emittente fiscale tramite
`script.fn_resolve_emittente_for_user`.

**Modello user-derived**: l'emittente di un ordine è lo snapshot
dell'emittente dell'operatore che ha creato il record, **non del BA**
(coerente con preventivi/contratti). La colonna serve allo scope RLS
operatore (convenzione PK).

Applicata dal trigger `trg_ordini_a10_default_emittente_ins`
(fase `_a10_`, `BEFORE INSERT`).

---

### Regola skip — payload esplicito

Se `NEW.emittente_fiscale_id IS NOT NULL` la funzione restituisce `NEW`
senza modifiche. Consente:

- **Admin globale** (operatore senza riga in `user_emittenti_fiscali`):
  specifica `emittente_fiscale_id` nel payload.
- **Push da documento sorgente** che propaga l'emittente.
- **Seed / migration data / pgAgent**: il chiamante deve valorizzare il
  campo esplicitamente, altrimenti l'assenza della GUC causa errore.

---

### Firing order nella fase `_a10_`

I trigger BEFORE INSERT si ordinano alfabeticamente per nome:

| Trigger | Evento | Effetto |
|---|---|---|
| `trg_ordini_a10_default_emittente_ins` | INSERT | Setta `emittente_fiscale_id` da GUC |
| `trg_ordini_a10_guard_emittente_ba_ins_upd` | INSERT, UPDATE OF | Valida BA↔emittente (skip se BA NULL) |
| `trg_ordini_a10_guard_emittente_scope_ins_upd` | INSERT, UPDATE | Write-guard RLS: scope operatore sull'emittente |
| `trg_ordini_a10_emittenti_fiscali_require_attivo_ins_upd` | INSERT, UPDATE OF (AFTER) | Emittente deve essere `attivo` |

---

### Errori sollevati

| Codice | id | Quando |
|---|---|---|
| `E_ORDINE_EMITTENTE_NON_RISOLTO` | 467 | GUC `app.current_user_id` vuota e payload senza `emittente_fiscale_id` |
| `E_ORDINE_EMITTENTE_NON_RISOLTO` | 467 | Operatore admin globale senza riga in `user_emittenti_fiscali` e senza payload esplicito |

---

### Note operative

- Il trigger AFTER `trg_ordini_a10_emittenti_fiscali_require_attivo_ins_upd`
  impedisce che `emittente_fiscale_id` punti a un EF `attivo = false`.
- Il campo diventa NOT NULL dopo il backfill 3-livelli
  (user-derived → BA-derived → gestore globale; migration
  `80_data/20260601-24`, `SET NOT NULL` in `90_end/20260601-25`).

---

{% include-markdown "signature-core.md" %}
