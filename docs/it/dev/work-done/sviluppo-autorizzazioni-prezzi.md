# Sviluppo Autorizzazioni Prezzi (WIP)

> **ARCHIVIATO il 2026-04-22.**
>
> L1 (permesso `prezzo_override_manuale`) è stato implementato nello sprint
> pricing preventivi del 17-04-2026 ed è in uso.
>
> L2 (limite sconto `VENDITE_MAX_SCONTO_PCT`) e L3 (workflow approvazione
> out-of-policy via pratiche) non erano stati avviati. Lo scope L2+L3 è stato
> **spostato** nel piano unificato in [sviluppo-listini-v5.md](../work-in-progress/sviluppo-listini-v5) §14 "Sprint 22-04-2026 — Completamento v5".
>
> Questo documento resta come specifica tecnica di riferimento per il modello
> a 3 livelli (architettura, flussi, infrastruttura permessi/parametri/pratiche,
> audit in `meta`).
>
> ---
>
> **Stato:** L1 implementato in sprint pricing preventivi (data implementazione nel changelog). L2 + L3 da pianificare.
>
> **Creato:** 17 aprile 2026
>
> **Riferimenti**
>
> * [sviluppo-listini-v5.md](/dev/work-in-progress/sviluppo-listini-v5) — resolver a 3 stadi (promo/contratto/categoria)
> * [pricing_service.md](/backend/vendite/manual/pricing_service) — building block PricingService.resolve_prezzo
> * [catalogo-building-block-backend.md](/dev/backend/catalogo-building-block-backend) §"Vendite — Pricing v5"

---

## 1) Perche'

Il resolver v5 risolve deterministicamente il **prezzo suggerito** per (articolo, uom, BA, utility, data, emittente) attraverso 3 stadi: promo → contratto → categoria. Ma nella realta' operativa ci sono casi legittimi di **override manuale** del prezzo:

- il commerciale negozia con il cliente durante la trattativa su preventivo
- l'amministrativo corregge un errore prima dell'emissione fattura
- il venditore senior applica uno sconto straordinario per fidelizzazione

**Problema**: non tutti gli operatori dovrebbero poter modificare il prezzo suggerito. Un junior dovrebbe usare sempre il resolver; un senior puo' fare override entro certi limiti; un commerciale chiuso in una trattativa grossa puo' chiedere approvazione.

Serve un sistema **a livelli** che:

1. Blocca l'override per chi non e' autorizzato (L1)
2. Limita lo sconto di chi e' autorizzato (L2)
3. Gestisce l'approvazione per override oltre il limite (L3)

Tutto ancorato all'infrastruttura permessi/parametri gia' esistente in ZeroERP: zero nuove tabelle tecniche, solo nuove "regole" a seed + wiring nei service.

---

## 2) Architettura a 3 livelli

```
┌────────────────────────────────────────────────────────────┐
│ Riga preventivo/ordine/fattura                             │
│   payload.prezzo_unitario (opzionale)                      │
└──────────────────────────┬─────────────────────────────────┘
                           │
            ┌──────────────▼──────────────┐
            │  PricingService             │
            │  .resolve_prezzo()          │
            │  → prezzo_suggerito         │
            └──────────────┬──────────────┘
                           │
         payload vuoto     │      payload presente
          ┌────────────────┤────────────────┐
          │                │                │
          ▼                ▼                ▼
   auto-fill dal     uguale al        diverso dal
   resolver → OK    suggerito → OK    suggerito → check
                                             │
                                             ▼
                                     ┌───────────────┐
                                     │ L1 (MVP)      │
                                     │ check_azione  │
                                     │ prezzo_override│
                                     └───────┬───────┘
                                             │
                                 autorizzato? │ si
                                             │
                                             ▼
                                     ┌───────────────┐
                                     │ L2 (futuro)   │
                                     │ check limite  │
                                     │ sconto_max    │
                                     └───────┬───────┘
                                             │
                                             ▼
                                     ┌───────────────┐
                                     │ L3 (futuro)   │
                                     │ approvazione  │
                                     │ out-of-policy │
                                     └───────────────┘
```

---

## 3) Livello 1 — Permesso override prezzo (MVP)

### 3.1 Infrastruttura

Azione di processo nel sistema permessi esistente (livello 2 — `config.azioni_processo`).

**Seed**: aggiungere riga a `db/changelog/migrations_v2/80_data/sql/config/azioni_processo.csv`:

```csv
codename,descrizione,area_id,pericolosa
prezzo_override_manuale,"Modifica manuale del prezzo suggerito (override del resolver v5)",2,false
```

Dove `area_id=2` e' l'area `vendite` (da verificare in seed area).

### 3.2 Wiring lato service

Ogni service che gestisce righe con prezzo risolvibile deve:

1. Accettare parametro `auth_user_id` (pattern gia' consolidato in `ClientiService.crea_cliente`)
2. Chiamare `PricingService.resolve_prezzo` per ottenere il prezzo suggerito + metadati
3. Se `payload.prezzo_unitario` non presente → popolare con suggerito
4. Se presente e **uguale** al suggerito → passa come e'
5. Se presente e **diverso** → `PermissionResolver.check_azione(user, 'prezzo_override_manuale')`; se negato `E_PERMESSO_NEGATO`
6. Tracciare in `meta` l'origine: `origine_prezzo` (`MANUALE` vs `PROMO`/`CONTRATTO_*`/`CATEGORIA`) + `prezzo_base_resolver` (valore originale) + `delta_override`

### 3.3 Service candidati all'integrazione

| Service | Priorita' | Note |
|---|---|---|
| `preventivi_service.gestisci_riga` / `aggiorna_riga` | Alta (primo consumer) | Include wiring L1 completo |
| `ordini_vendita_service.*` (quando esistera') | Media | Stesso pattern preventivi |
| `fatture_manuali_service.*` (se esiste) | Media | Override ammessi in edit pre-emissione |
| `commesse_attivita` | N/A | Prezzo gestito dal DB via `fn_upsert_commessa_attivita`, override va gestito prima (nel preventivo/ordine sorgente) |

### 3.4 UI/UX

Nel drawer riga (FE):

- Campo `prezzo_unitario` pre-compilato col suggerito all'apertura (via endpoint `suggerisci_prezzo` Opzione A)
- Badge "prezzo da listino" / "prezzo da contratto" / "prezzo promo" accanto al campo con origine e delta eventuale
- Se operatore non autorizzato (check `PermissionResolver.check_azione` lato FE via endpoint permessi effettivi) → campo **disabled**
- Se override valido → badge "prezzo manuale" con icona ⚠️

### 3.5 Errore

Nuovo codice `E_PREZZO_OVERRIDE_NON_AUTORIZZATO` in `error_policies.py`:

- HTTP 403
- UI action: `show_error_banner`
- Messaggio: "Modifica manuale del prezzo non autorizzata. Usa il prezzo suggerito dal listino o richiedi autorizzazione al tuo responsabile."

---

## 4) Livello 2 — Limite sconto (futuro)

### 4.1 Infrastruttura

Parametro multi-scope via `ParameterService` (pattern gia' esistente):

- **Codice**: `VENDITE_MAX_SCONTO_PCT`
- **Tipo**: `decimal`
- **Default**: `0` (nessun override ammesso se L2 abilitato e operatore non ha override specifico)
- **Scope cascata**: user → group → emittente → default
- **Seed**: `config.parameter_definitions` + `config.parameter_defaults` (da migrare)

### 4.2 Regola

```
sconto_pct = (prezzo_resolver - prezzo_manuale) / prezzo_resolver * 100
SE sconto_pct > VENDITE_MAX_SCONTO_PCT (risolto per l'utente)
  -> E_PREZZO_SCONTO_ECCESSIVO con detail "max ammesso: X%, richiesto: Y%"
```

Gestione override positivo (prezzo manuale > suggerito): parametro gemello `VENDITE_MAX_MAGGIORAZIONE_PCT` oppure sempre ammesso (aumenti ammessi senza limite).

### 4.3 Assegnazione limiti per ruolo

Override personale utente permette di dare a un commerciale senior un limite piu' alto del default:

```
ParameterService.upsert_user_override(
    user=mario_commerciale,
    code='VENDITE_MAX_SCONTO_PCT',
    value='15'
)
```

Junior ha default = 0 → non puo' scontare nemmeno con L1 passato.

---

## 5) Livello 3 — Approvazione out-of-policy (futuro)

### 5.1 Flusso

Quando `sconto_pct > VENDITE_MAX_SCONTO_PCT`:

1. Salvataggio riga messo in **stato bloccato** (nuovo stato `prezzo_in_approvazione` sulla riga o flag `meta.pending_approval=true`)
2. Creazione automatica **pratica** di tipo "Approvazione prezzo" collegata alla riga (via `pratiche_service.crea_pratica` gia' esistente)
3. Notifica al responsabile/reparto approvazioni (via email template in Outbox)
4. Responsabile apre la pratica, vede contesto (cliente, articolo, prezzo resolver, prezzo richiesto, delta%)
5. Approva → riga sbloccata, prezzo confermato
6. Rifiuta → riga resa al prezzo resolver, notifica a chi aveva richiesto

### 5.2 Infrastruttura

Tutto con building block esistenti:

- **Pratiche** per il workflow approvazione (stato BOZZA → APERTA → CHIUSA con esito)
- **Tipo prestazione** nuovo: "Approvazione prezzo commerciale"
- **EmailOutboxService** per le notifiche
- **Azione di processo** `approva_prezzo` (livello 2) per il responsabile

### 5.3 Side effects

- Il preventivo/ordine **non puo' essere confermato** finche' tutte le righe con `pending_approval=true` non sono state chiuse
- Trigger DB di guard su transizione stato preventivo (es. DRAFT → ACCETTATO bloccato se ci sono righe pending)

---

## 6) Audit

Ogni override — anche autorizzato — deve lasciare traccia permanente in `meta` (jsonb) della riga:

```json
{
  "origine_prezzo": "MANUALE",
  "prezzo_base_resolver": "50.00",
  "prezzo_applicato": "45.00",
  "delta_override": "-5.00",
  "delta_override_pct": "-10.00",
  "resolver_context": {
    "origine": "CONTRATTO_LISTINO",
    "listino_id": 100,
    "contratto_id": 42
  },
  "override_user_id": 5,
  "override_timestamp": "2026-04-17T14:30:00Z",
  "approvazione_pratica_id": null
}
```

Cosi' ogni riga e' tracciabile: cosa avrebbe dato il resolver, cosa ha applicato l'operatore, perche', chi, quando.

---

## 7) Roadmap

| Sprint | Contenuto | Stato |
|---|---|---|
| **Pricing preventivi** | Opzione A (suggerisci_prezzo endpoint) + Opzione B (auto-fill `gestisci_riga`) + **L1** (permesso override + seed azione + traccia meta) | In corso |
| **L2 max sconto** | Parametro `VENDITE_MAX_SCONTO_PCT` + check sul delta + UI hint | Da pianificare |
| **L3 approvazione** | Tipo prestazione + workflow pratiche + guard transizione stato preventivo | Da pianificare |

Ogni sprint successivo richiede che il precedente sia stabilizzato in produzione.

---

## 8) Decisioni aperte

### 8.1 Granularita' dei permessi

Un singolo permesso `prezzo_override_manuale` basta, o servono permessi distinti per dominio (preventivi / ordini / fatture)? **Decisione iniziale**: uno solo, per semplicita'. Se in futuro servira' differenziare, si aggiungera' senza breaking.

### 8.2 Override su contratto

Un contratto modalita' B (listino + righe override) e' gia' un "override permanente" del listino via modello dati. Chi crea/modifica contratti passa dall'area `vendite` livello `TUTTO` — quindi e' gia' protetto. Non serve L1 su `contratti_righe`.

### 8.3 Documenti storici

Fatture emesse hanno prezzi congelati (immutabili). Override ammesso solo in bozza/pre-emissione. Il wiring L1 si applica solo ai service che scrivono righe in stato modificabile.

### 8.4 Area applicabile ai compositi (BoM)

Quando un articolo composito espande in N righe `commesse_attivita`, ogni componente ha il suo prezzo risolto da `resolve_prezzo_composito`. L'override su una singola riga componente richiede gli stessi check — ma oggi le commesse sono alimentate dal DB senza passaggio dal service. Da rivedere in F2-BE-12 (pipeline espansione compositi).

---

## 9) Non-obiettivi

Questo documento **non** copre:

- Listini differenziati per canale di vendita (negozio, e-commerce, telefono) — e' un'altra dimensione del resolver, non un permesso
- Prezzi speciali cliente-articolo senza contratto (oggi si fa con matrice categoria + contratto override; non pianifichiamo nuove tabelle)
- Workflow multi-firmatario (approva 1 poi approva 2) — L3 prevede un solo approvatore per semplicita'

---

*Sviluppo Autorizzazioni Prezzi — ZeroERP (17 aprile 2026, WIP)*
