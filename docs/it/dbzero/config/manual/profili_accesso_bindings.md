## 📘 Documentazione Concettuale – Tabella `config.profili_accesso_bindings`

> 👀 **Vedi anche**
>
Architettura di riferimento:
>
[Architettura Multi-Face Auth](/guide/architettura-multi-face-auth)
> [Architettura Permessi e Autorizzazioni](/guide/architettura-permessi-e-autorizzazioni)
>
Tabelle correlate:
>
[config.profili_accesso](/dbzero/config/tabelle/profili_accesso)
> [config.unita_organizzative](/dbzero/config/tabelle/unita_organizzative)
> [anagrafiche.identita_digitali](/dbzero/anagrafiche/tabelle/identita_digitali)
>
Trigger:
>
[config.trgfn_profili_accesso_bindings_guard_coerenza](/dbzero/config/funzioni/trgfn_profili_accesso_bindings_guard_coerenza)

---
### 🎯 Scopo Principale
(latest revision 18-04-2026)

La tabella **`config.profili_accesso_bindings`** collega un **profilo di accesso**
a una specifica entità di dominio. Ogni riga assegna **un solo profilo** a
**una sola** delle tre possibili entità:

| Entità | Colonna | Semantica del binding |
|--------|---------|-----------------------|
| Reparto | `unita_organizzativa_id` | Profilo valido per tutti gli operatori di quel reparto (pattern storico). |
| Ruolo applicativo | `ruolo_applicativo` | Profilo fallback per tutti gli utenti di quel ruolo (es. tutti i `CLIENTE_PORTALE`). |
| Identità specifica | `identita_digitale_id` | Profilo ad-hoc assegnato a una singola identità (override organico). |

---

### Vincolo "esattamente uno"

Il CHECK `chk_profili_accesso_bindings_xor` garantisce che **una e una sola**
colonna tra `unita_organizzativa_id`, `identita_digitale_id`, `ruolo_applicativo`
sia valorizzata:

```sql
(unita_organizzativa_id IS NOT NULL)::int
+ (identita_digitale_id   IS NOT NULL)::int
+ (ruolo_applicativo      IS NOT NULL)::int
= 1
```

Il CHECK garantisce "quale colonna"; il guard
[`trgfn_profili_accesso_bindings_guard_coerenza`](/dbzero/config/funzioni/trgfn_profili_accesso_bindings_guard_coerenza)
garantisce che sia la colonna **coerente col tipo del profilo**:

| Tipo profilo | Colonna attesa |
|--------------|----------------|
| `REPARTO` | `unita_organizzativa_id` |
| `PORTALE` | `ruolo_applicativo` |
| `AD_HOC` | `identita_digitale_id` |

---

### Unicità per entità

Tre indici parziali UNIQUE impediscono binding duplicati per la stessa entità:

| Indice | Scopo |
|--------|-------|
| `uq_profili_accesso_bindings_uo` (partial `WHERE unita_organizzativa_id IS NOT NULL`) | Un solo profilo per reparto. |
| `uq_profili_accesso_bindings_identita` (partial `WHERE identita_digitale_id IS NOT NULL`) | Un solo profilo per identità (per override ad-hoc). |
| `uq_profili_accesso_bindings_ruolo` (partial `WHERE ruolo_applicativo IS NOT NULL`) | Un solo profilo fallback per ruolo applicativo. |

---

### Flag `attivo`

Permette di **sospendere** un binding senza cancellarlo. Utile durante
riorganizzazioni o test di configurazione. Se `attivo = false` il binding
non partecipa alla risoluzione del profilo.

⭐ **Il binding non segue la veste** (dal 2026-09-25): `attivo` del binding e
`attivo` dell'identità sono due domande diverse — *cosa si può fare dentro* e
*se la porta è aperta* — e l'automazione ATTIVO non le lega più (la FK
`identita_digitale_id` è un'eccezione dichiarata in
[`dbops.automazione_attivo_eccezioni`](/dbzero/dbops/manual/automazione_attivo_eccezioni)).
Un binding attivo può quindi stare su una veste spenta: è l'operatore che
aspetta di accettare l'invito (la veste OPERATORE nasce spenta), o quello
disattivato, che al reinvito ritrova i suoi profili. Chi risolve i permessi
chiede **entrambe** le cose (`fn_is_super_admin`,
`fn_get_profili_accesso_applicabili`, i check anti-lockout).

---

### Uso nella catena di risoluzione

Durante la risoluzione del profilo applicabile a un utente, la catena
consulta i bindings attivi in ordine di specificità:

```
1. Binding AD_HOC per l'identità specifica   → ha priorità
2. Binding REPARTO (se identità OPERATORE)   → ereditato dal reparto
3. Binding PORTALE per il ruolo applicativo  → fallback per portali/shop
4. Nessun binding                            → profilo di default BLOCCATO
```

Questa catena verrà implementata nelle funzioni `fn_resolve_livello_*`
generalizzate al cutover (§4.8 del WIP multi-face-auth).

---

### Seed iniziale

Il seed dei profili PORTALE (`80_data/changelog/20260418-43-upsert-profili-accesso-portale`)
crea 3 bindings, uno per ogni ruolo portale:

| Profilo | `ruolo_applicativo` |
|---------|---------------------|
| `CLIENTE_PORTALE_STANDARD` | `CLIENTE_PORTALE` |
| `FORNITORE_PORTALE_STANDARD` | `FORNITORE_PORTALE` |
| `SHOP_CUSTOMER_STANDARD` | `SHOP_CUSTOMER` |

I bindings `REPARTO` sono invece popolati dalla migrazione dati, un binding
per ogni unità organizzativa con permessi configurati nel modello legacy.

---

{% include-markdown "signature-core.md" %}
