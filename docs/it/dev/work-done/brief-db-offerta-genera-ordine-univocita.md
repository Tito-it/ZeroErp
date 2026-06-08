# Brief DB — Univocità `offerta → ordine` (1:1) + azione `genera_ordine` data-driven

> **Stato**: ⛔ **SUPERATO / CHIUSO (2026-06-08)** — questo è il *draft iniziale*.
> Il documento autoritativo, consegnato dal team DB e cablato BE/FE, è
> [brief-db-univocita-offerta-ordine.md](brief-db-univocita-offerta-ordine.md)
> (pgTAP 15/15 + BE/FE verdi). Conservato solo per storico; **non** è la fonte.
>
> ~~**Stato**: 🟡 **APERTO** — pronto per il team DB su `dev/db-tid`.~~
>
> **Owner concettuale**: Tid (Michele Carlo Titini).
> **Data brief**: 2026-06-07.
>
> **Origine**: bug operativo segnalato da Tid. Da un'offerta `ACCETTATA`,
> premendo "Genera ordine" l'ordine viene creato correttamente
> (`documento_origine = ('OFFERTA', id)`), **ma nessun vincolo impedisce di
> rigenerarlo**: ripremendo il bottone nascono ORD duplicati, senza errore e
> senza segnale UI. La radice è un'**asimmetria** col gemello `push_contratto`,
> che è già idempotente e data-driven.
>
> **Decisione di modello ratificata (Tid, 2026-06-07)**: un'offerta commerciale
> genera **al massimo UN ordine** (1:1, a livello testata — niente selezione
> righe in v1). L'invariante più fine "la stessa riga d'offerta non può stare su
> due ordini" è automaticamente soddisfatta da questo 1:1 di testata.
>
> **Modelli di riferimento già implementati**:
>
> - [`script.fn_available_actions_offerta`](../../dbzero/script/funzioni/fn_available_actions_offerta.md) — azione speciale `push_contratto` con guard idempotenza cross-dominio
> - [`vendite.fn_push_offerta_a_contratto`](../../dbzero/vendite/funzioni/fn_push_offerta_a_contratto.md) — idempotenza strutturale (UNIQUE `vendite.contratti.offerta_id`)
>
> **Cosa NON è questo documento**: non ridefinisce la state machine offerta, non
> tocca `PREVENTIVO → ordine` (resta come da A1, vedi §4), non aggiunge tabelle.

---

## 1. Inquadramento

`vendite.ordini` traccia l'origine via `documento_origine_tipo`
(`'PREVENTIVO'`/`'OFFERTA'`) + `documento_origine_id`, **senza UNIQUE** (scelta
A1 in [analisi-ordini-vendita.md](../work-in-progress/analisi-ordini-vendita.md) §1.bis, per
consentire riordini/consegne parziali). Verificato su doc DB
[`vendite/tabelle/ordini.md`](../../dbzero/vendite/tabelle/ordini.md): i due
CHECK presenti sono `chk_ordini_documento_origine_tipo` (vocabolario) e
`chk_ordini_documento_origine_copres` (co-presenza); **nessun UNIQUE** sulla
coppia.

Conseguenza: `script.crea_ordine_da_offerta` (BE) guarda solo che l'offerta sia
`ACCETTATA` e crea l'ordine. Niente impedisce la seconda generazione.

Per contro, `script.fn_available_actions_offerta` espone `push_contratto`
**solo** se nessun contratto esiste già per l'offerta (vedi doc DB, blocco
`can_push_contratto`, righe 140-163), e l'idempotenza è blindata a DB
dall'UNIQUE `vendite.contratti.offerta_id`. `genera_ordine` invece **non esiste
come azione** nella fn: il bottone FE è hardcoded su `stato === ACCETTATA`.

Questo brief chiude l'asimmetria: stesso pattern di `push_contratto`, applicato
a `genera_ordine`, su 2 livelli DB (integrità hard + capability data-driven).

## 2. Cosa serve (DB)

### 2.1 Indice UNIQUE parziale su `vendite.ordini` (integrità hard)

Vincolo 1:1 **solo per origine `OFFERTA`** (l'origine `PREVENTIVO` resta libera,
vedi §4):

```sql
CREATE UNIQUE INDEX uq_ordini_v_documento_origine_offerta
    ON vendite.ordini (documento_origine_tipo, documento_origine_id)
 WHERE documento_origine_tipo = 'OFFERTA';
```

- Naming coerente con gli indici esistenti (`uq_ordini_v_*`).
- Parziale: non vincola `PREVENTIVO` né le righe con `documento_origine_tipo IS
  NULL` (ordini nativi).
- È la rete di sicurezza strutturale (anche contro race concorrenti). Il BE
  mapperà la violazione di questo indice a `E_ORD_OFFERTA_GIA_CONVERTITA`
  (vedi §3).
- Coerente con la filosofia di progetto "trigger/vincoli restrittivi attivi da
  subito" (no produzione, no gradiente di staging).

### 2.2 `script.fn_available_actions_offerta` — nuova azione speciale `genera_ordine`

Aggiungere `genera_ordine` come **azione speciale hardcoded non-cambio-stato**,
mirror esatto di `push_contratto`:

**Costante azione** (accanto a `c_action_push_contratto`):

```sql
c_action_genera_ordine CONSTANT jsonb := jsonb_build_object(
    'key',                  'genera_ordine',
    'target_state',         NULL,                                  -- azione speciale, non cambio stato
    'label_key',            'vendite.offerte.azione_genera_ordine', -- i18n già esistente
    'severity',             'info',
    'icon',                 'pi pi-shopping-cart',                  -- NAV_ICONS.ORDINI
    'requires_confirm',     true,
    'requires_motivazione', false
);
```

**Guard idempotenza** (mirror del blocco `can_push_contratto`, dentro il ramo
`v_stato_cod = 'ACCETTATA'`): l'azione appare **solo** se nessun ordine è già
nato da questa offerta.

```sql
-- can_genera_ordine: ACCETTATA + nessun ordine già generato.
-- Check cross-dominio su vendite.ordini.documento_origine_* (1:1 idempotenza,
-- stesso pattern di can_push_contratto). Specchio dell'UNIQUE parziale §2.1.
IF v_stato_cod = 'ACCETTATA' THEN
    IF NOT EXISTS (
        SELECT 1 FROM vendite.ordini
         WHERE documento_origine_tipo = 'OFFERTA'
           AND documento_origine_id   = p_offerta_id
    ) THEN
        v_can_ordine        := true;
        v_ordine_reason     := NULL;
        v_ordine_reason_key := NULL;
        v_actions := v_actions || jsonb_build_array(c_action_genera_ordine);
    ELSE
        v_can_ordine        := false;
        v_ordine_reason     := 'OFFERTA_ORDINE_GIA_GENERATO';
        v_ordine_reason_key := 'offerte.push_reason.ordine_gia_generato';
    END IF;
ELSE
    v_can_ordine        := false;
    v_ordine_reason     := 'OFFERTA_NON_ACCETTATA';
    v_ordine_reason_key := 'offerte.push_reason.non_accettata';  -- riuso chiave esistente
END IF;
```

> Nota: `push_contratto` e `genera_ordine` sono **indipendenti** — un'offerta
> ACCETTATA può esporre entrambe (genera contratto *e* genera ordine), ognuna
> con la propria idempotenza. Nessuna mutua esclusione richiesta.

**Estendere l'output `jsonb`** con i tre flag (mirror dei `can_push_contratto*`):

```jsonc
{
  // ... campi esistenti invariati ...
  "can_genera_ordine":            false,  // true solo in ACCETTATA + nessun ordine generato
  "can_genera_ordine_reason":     null,   // reason machine-readable se can=false
  "can_genera_ordine_reason_key": null    // chiave i18n associata se can=false
}
```

### 2.3 Matrice reason `can_genera_ordine`

| Caso | `can_genera_ordine` | `_reason` | `_reason_key` |
|------|---------------------|-----------|---------------|
| `ACCETTATA` **e** nessun ordine da questa offerta | `true` | `null` | `null` |
| `ACCETTATA` **ma** esiste già `vendite.ordini` con `documento_origine = ('OFFERTA', id)` | `false` | `'OFFERTA_ORDINE_GIA_GENERATO'` | `'offerte.push_reason.ordine_gia_generato'` |
| stato ≠ `ACCETTATA` | `false` | `'OFFERTA_NON_ACCETTATA'` | `'offerte.push_reason.non_accettata'` |

### 2.4 Convenzione `target_state`

`genera_ordine` ritorna `target_state: null` come `push_contratto`/`crea_revisione`:
è routing speciale (genera un secondo oggetto), non una transizione di stato.
L'offerta **resta `ACCETTATA`**. Il FE distingue l'azione dal `key`.

## 3. Cosa NON cambia a DB

- **State machine offerta**: i 6 stati e il guard di transizione
  (`trgfn_offerte_commerciali_guard_transizione`) restano invariati. L'offerta
  **non** acquisisce uno stato "CONVERTITA"/"EVASA": la generazione ordine è un
  effetto, non un cambio stato (coerente con `push_contratto`).
- `fn_available_actions_offerta` resta **pura lettura**: non solleva, ritorna
  `NULL` su offerta inesistente.
- Nessuna modifica a `vendite.ordini_righe` né tracciamento riga-per-riga: il
  1:1 di testata rende superflua l'identità persistente di riga in v1.

## 4. Punto di modello da ratificare in doc — reversal parziale di A1

L'UNIQUE §2.1 **inverte, per la sola origine `OFFERTA`**, la scelta A1
"`documento_origine` senza UNIQUE → più ordini da una stessa origine". È
voluto e ratificato da Tid (2026-06-07): per le offerte vale 1:1 di testata.
`PREVENTIVO` **non** è toccato (resta multi-ordine come da A1: riordini/consegne
parziali).

→ L'agente BE aggiornerà [analisi-ordini-vendita.md](../work-in-progress/analisi-ordini-vendita.md)
§1.bis con un addendum che documenta l'asimmetria `OFFERTA` (1:1) vs
`PREVENTIVO` (1:N). Non è competenza del team DB.

## 5. Test pgTAP (suggeriti)

Estendere la suite di `fn_available_actions_offerta`:

- offerta `ACCETTATA` **senza** ordine →
  `available_actions` contiene `genera_ordine`, `can_genera_ordine = true`,
  `can_genera_ordine_reason IS NULL`.
- offerta `ACCETTATA` **con** ordine `documento_origine = ('OFFERTA', id)` →
  `genera_ordine` **assente** da `available_actions`,
  `can_genera_ordine = false`, `_reason = 'OFFERTA_ORDINE_GIA_GENERATO'`.
- offerta non `ACCETTATA` → `can_genera_ordine = false`,
  `_reason = 'OFFERTA_NON_ACCETTATA'`.

Più un test sull'indice §2.1:

- inserire due `vendite.ordini` con `documento_origine = ('OFFERTA', X)` →
  il secondo INSERT viola `uq_ordini_v_documento_origine_offerta`.
- due ordini con `documento_origine = ('PREVENTIVO', Y)` → **consentiti**
  (l'indice non li vincola).

## 6. Integrazione lato BE/FE (post-consegna — competenza agente BE)

Dopo che indice + fn sono su `dev/db-tid`, l'agente BE cabla (additivo):

- **BE guard** in `crea_ordine_da_offerta`
  ([ordini_service.py](../../../backend/apps/vendite/services/ordini_service.py)):
  nuovo metodo `OrdiniRepository.get_ordine_by_documento_origine('OFFERTA', id)`
  + `ErrorManager.require(... is None ...)` → nuovo codice
  `E_ORD_OFFERTA_GIA_CONVERTITA` (409) registrato in
  [error_policies.py](../../../backend/apps/core/services/error_policies.py).
  Mappare anche la violazione dell'UNIQUE §2.1 allo stesso codice nel blocco
  `_db_errors` (rete per la race).
- **FE data-driven**: `OffertaDrawer.vue` smette di costruire l'azione
  `genera-ordine` da `stato === ACCETTATA` hardcoded e la prende da
  `available_actions` (come già fa per `push_contratto`), così sparisce a
  conversione avvenuta. Dialog parlante su `E_ORD_OFFERTA_GIA_CONVERTITA` con
  deep-link all'ordine esistente (mirror del dialog
  `E_OFFERTA_CONTRATTO_GIA_GENERATO`).
- **i18n**: aggiungere la chiave `offerte.push_reason.ordine_gia_generato`
  ("Un ordine è già stato generato da questa offerta."). `azione_genera_ordine`
  e `push_reason.non_accettata` esistono già.

## 7. Sequenza (team DB)

1. Indice UNIQUE parziale §2.1. Migration nuova, numerazione successiva.
2. `script.fn_available_actions_offerta` (`runOnChange: true`) con azione +
   flag `can_genera_ordine*` §2.2. Migration nuova.
3. Test pgTAP §5.
4. Verifica `make db-migrate` locale.
5. Push su `dev/db-tid` + PR verso `Tito-dev`.

I due punti DB sono indipendenti tra loro; il cablaggio BE/FE §6 è **bloccato**
finché entrambi non sono su `dev/db-tid`.

---

*Brief DB — univocità offerta→ordine + azione `genera_ordine` data-driven.
Pronto per il team DB su `dev/db-tid`. A consegna avvenuta, l'agente BE cabla in
giornata (guard BE + error policy + drop del computed FE hardcoded).*
