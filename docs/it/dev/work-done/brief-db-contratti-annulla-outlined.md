# Brief DB — Allineare meta `annulla` contratto (rimuovere outlined)

> **Status**: 🆕 WIP — 2026-05-30
> **Target team**: DB (`dev/db-tid`)
> **Origine**: incoerenza UX rilevata da Tid 2026-05-30 — bottone "Annulla"
>   nel drawer contratti appare bianco-outline mentre preventivi/offerte
>   mostrano rosso pieno.

---

## Richiesta

Allineare il meta JSON dell'azione `annulla` nella tabella
`config.transizioni_stati_contratti` rimuovendo `outlined: true`
(o impostandolo a `false`).

File: [transizioni_stati_contratti.csv](../../../../db/changelog/migrations_v2/80_data/sql/config/transizioni_stati_contratti.csv)
riga 2 — `id=2, stato_da_id=1 (DRAFT), stato_a_id=8 (ANNULLATO)`.

**Diff atteso**:

```diff
- 2,1,8,t,"{""action_key"":""annulla"",...,""severity"":""danger"",...,""outlined"":true,""manuale"":true}",...
+ 2,1,8,t,"{""action_key"":""annulla"",...,""severity"":""danger"",...,""outlined"":false,""manuale"":true}",...
```

Re-seed via il changelog esistente `20260528-06-seed-transizioni-stati-contratti-mctit.yaml`
(già `runOnChange: true`).

## Motivazione

Preventivi e offerte hanno la stessa azione `annulla` con
`severity=danger` e nessun `outlined` (default false), producendo lato FE
un PrimeVue Button rosso pieno. Contratti ha `outlined=true` →
PrimeVue Button "outlined" (sfondo bianco, bordo rosso).

UX incoerente cross-dominio per la stessa semantica (azione distruttiva
su BOZZA/DRAFT). Allineare al pattern offerte/preventivi rimuove
l'eccezione e centralizza la regola: **azione distruttiva = rosso pieno
ovunque**, indipendentemente dal dominio.

## Fuori scope

- Modifiche all'azione `cessa` (transizione ATTIVO→CESSATO): è una
  transizione diversa, semanticamente meno distruttiva (chiusura
  programmata), mantenere il suo `outlined=false` attuale è coerente.
- Pattern frontend `outlined` pass-through resta invariato:
  `mapAvailableActionsToDrawerActions` legge `action.outlined` dal BE e
  lo passa al Button. La capability resta per usi futuri (es. azioni
  "secondarie pericolose" che potrebbero servire altrove).

---

*Brief sintetico — re-seed file CSV, niente DDL nuovo.*
