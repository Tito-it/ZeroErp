## 📘 Documentazione Concettuale – Tabella `config.identita_scope_bindings`

> 👀 **Vedi anche**
>
Architettura di riferimento:
>
[Architettura Multi-Face Auth](/guide/architettura-multi-face-auth)
>
Tabelle correlate:
>
[config.scope_policy](/dbzero/config/tabelle/scope_policy)
> [anagrafiche.identita_digitali](/dbzero/anagrafiche/tabelle/identita_digitali)

---
### 🎯 Scopo Principale
(latest revision 18-04-2026)

La tabella **`config.identita_scope_bindings`** associa **un'identità digitale**
a **una o più policy di scope**, attivando il filtro dati corrispondente.

Ogni riga dice: "l'identità X è soggetta alla policy Y (con eventuali parametri
Z)". Un'identità può avere più binding concorrenti (es. un operatore con
`EF_WHITELIST` su emittenti + in futuro una policy aggiuntiva per tenant).

---

### Colonne chiave

| Colonna | Scopo |
|---------|-------|
| `identita_digitale_id` | FK a `anagrafiche.identita_digitali` — identità a cui applicare la policy. |
| `scope_policy_id` | FK a `config.scope_policy` — policy da applicare. |
| `parametri` | JSONB libero. Default `{}` vuoto: le policy standard risolvono i parametri dai riferimenti anagrafici (es. `BA_OWNERSHIP` risolve il cliente via `identita.soggetto_ruolo_id`). Uso previsto: policy future che richiedono configurazione esplicita. |
| `attivo` | Se `false`, il binding non partecipa alla risoluzione. Permette di sospendere una policy per un'identità senza cancellare la riga. |

---

### Unicità

Vincolo `UNIQUE (identita_digitale_id, scope_policy_id)`: una sola riga per
coppia (identità, policy). Una policy non può essere attivata più volte per
la stessa identità.

---

### Uso in runtime

Durante una query filtrata da una RLS o da un check applicativo, il flusso è:

```
1. Ricava identita_digitale_id corrente dai GUC app.current_identita_id.
2. Lookup dei binding attivi su config.identita_scope_bindings.
3. Per ciascun binding: chiama la funzione_db della scope_policy referenziata
   passando (identita_digitale_id, target_id).
4. La riga passa se TUTTI i binding rilevanti ritornano true (AND logico).
```

L'AND significa che le policy sono **ristrettive** e cumulative. Se serve
semantica OR (es. un'identità ammessa da almeno una policy), la si modella
combinando condizioni **dentro la singola funzione**, non con più binding.

---

### Backfill iniziale

Il changeset `80_data/changelog/20260418-71-backfill-identita-scope-bindings-ef-whitelist`
crea un binding `EF_WHITELIST` per ogni identità `OPERATORE` attiva che ha
righe in `config.user_emittenti_fiscali`. Il backfill è idempotente
(`ON CONFLICT DO NOTHING`) e `runOnChange: true`: si riapplica quando nuove
identità operatore vengono migrate (es. al cutover §4.6).

Per le identità di portali e shop, i binding `BA_OWNERSHIP` e
`FORNITORE_OWNERSHIP` verranno creati al momento dell'attivazione
dell'identità (flusso di invito portale / registrazione shop) oppure via
seed successivi quando ci saranno utenti pilota.

---

{% include-markdown "signature-core.md" %}
