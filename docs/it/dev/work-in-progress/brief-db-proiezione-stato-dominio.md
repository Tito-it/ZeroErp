# Brief DB — Proiezione stato di dominio: normalizzazione + resolver

> **Tipo**: brief DB (DDL + seed + funzioni/viste) · **Destinatario**: team DB (`dev/db-tid`)
> **Priorità**: 🟠 media-alta (abilita V1 "vista-racconto" e salda il debito GUIDA)
> **Data**: 2026-07-01 · **Stato**: 🟠 proposto
>
> **Origine / autorevole**: [brief-design-proiezione-stato-dominio.md](brief-design-proiezione-stato-dominio.md)
> (voce **V10**). Qui si estraggono le **sole attività DB** (D1-D4). Modello, principio e
> vincoli sono nel brief di design: leggerlo prima.

---

## 1. Obiettivo

Dare al motore pratiche un **descrittore normalizzato** dello stato del documento di dominio
collegato (preventivo/offerta/ordine/contratto), **read-time**, senza mirror e senza che il
motore nomini mai uno stato di dominio. Il **dominio dichiara la mappa**; il motore consuma.

**Descrittore universale** (contratto §4 del brief design):

| Campo | Origine |
|---|---|
| `stato_codice` + `stato_descrizione` | valori nativi `config.stati_doc_*` (display) |
| `fase` ∈ `APERTO · IN_CORSO · IN_ATTESA · CHIUSO` | mapping dichiarato dal dominio (D1) |
| `esito` → `config.esiti_flussi_pratiche.codice_interno` (`NULL/POSITIVO/NEGATIVO/PARZIALE`) | mapping dominio (D1) |
| `terminale` (bool) | mapping dominio (D1) |

## 2. Vocabolario universale (mappa dichiarata dal dominio)

Verificato sui seed reali (brief design §3). Da seedare nelle colonne D1:

```text
stato di dominio               → fase       esito       terminale
──────────────────────────────────────────────────────────────────
DRAFT / BOZZA                  → APERTO     NULL        false
EMESSO / EMESSA                → IN_ATTESA  NULL        false
CONFERMATO / ATTIVO            → IN_CORSO   NULL        false
ALLOCATO/SPEDITO/CONSEGNATO    → IN_CORSO   NULL        false
ACCETTATO / ACCETTATA          → IN_CORSO   POSITIVO    false
RIFIUTAT* / SCADUTO / SUPERATA → CHIUSO     NEGATIVO    true
EVASO / FATTURATO / CESSATO    → CHIUSO     POSITIVO    true
ANNULLAT* (is_abortito)        → CHIUSO     NEGATIVO    true
```

## 3. Stato di partenza (recon 2026-07-01, docs/it/dbzero)

- `config.stati_doc_{preventivi,offerte,ordini,contratti}`: hanno `codice_interno`, `codice`,
  `descrizione`, `attivo`, `ordine`, `meta`. **`is_abortito` solo su preventivi/contratti**,
  `is_bozza` solo contratti. **Nessuna colonna di normalizzazione** (`fase`/`esito`/`terminale`).
- `config.sorgenti`: registry con `codice_interno`, `codice`, `categoria`, `descrizione`,
  `target_table` (regclass), `key_selector` (`id`\|`uid`), `scope`, `tipo_doc_fiscale_id`.
  **Senza `resolver_key`**.
- `pratiche.pratiche_sorgenti`: `sorgente_tipo_id` (→ `config.sorgenti`), `sorgente_uid`,
  `ruolo_link` (ROOT/COLLEGATO), `flusso_id`, `meta`.
- `config.esiti_flussi_pratiche`: catalogo esiti (target di `esito`).
- Pattern disciplina-chiave di riferimento: `pratiche.handler_flussi.handler_key`
  (UNIQUE, immutabile, dispatch **statico** in Python, **no dynamic SQL**).

## 4. Deliverable DB

> **Roll-out per dominio, additivo.** Consegnare prima **solo per PREVENTIVI**
> (`stati_doc_preventivi` / sorgente preventivo), validare end-to-end con BE+FE (fase MOSTRA),
> poi replicare su offerte/ordini/contratti. Un dominio senza resolver → descrittore
> `UNKNOWN`, milestone manuale come oggi (nessuna regressione).

### D1 — Colonne di normalizzazione sulle `config.stati_doc_*` (dominio-owned)

Aggiungere a **ogni** `config.stati_doc_*` (a partire da `stati_doc_preventivi`):

- `fase_norm` varchar NOT NULL — CHECK in (`APERTO`,`IN_CORSO`,`IN_ATTESA`,`CHIUSO`);
- `esito_norm` varchar NULL — FK/valore verso `config.esiti_flussi_pratiche.codice_interno`
  (NULL ammesso = nessun verdetto);
- `terminale` boolean NOT NULL DEFAULT false.

+ **seed** dei valori per ogni stato secondo la mappa §2 (idempotente, re-seed-safe:
`UPDATE ... WHERE ... IS DISTINCT FROM`). Nota: `terminale` è ridondante con parte di
`is_abortito` ma **uniforme su tutti i domini** — è proprio il punto (is_abortito manca su
offerte/ordini).

### D2 — Resolver per dominio (vista/funzione normalizzata)

Per il dominio (vendite/preventivi): una **vista** (preferita, join-abile per le liste) o
funzione che, dato lo stato corrente del documento, espone il **descrittore §1**:
`(stato_codice, stato_descrizione, fase, esito, terminale)` leggendo lo stato del documento
+ il mapping D1. Chiave d'accesso coerente con `config.sorgenti.key_selector` del tipo
sorgente (`id` o `uid`).

### D3 — `resolver_key` + dispatch di motore

- Colonna **`config.sorgenti.resolver_key`** varchar NULL — **chiave controllata** (stessa
  disciplina di `handler_key`): identifica il resolver del tipo sorgente. NULL = nessun
  resolver → `UNKNOWN`.
- **`pratiche.fn_stato_sorgente(p_sorgente_tipo_id, p_sorgente_uid)`** → ritorna il
  descrittore §1. Dispatch **a CASE statico** su `resolver_key` verso il resolver D2 del
  dominio (**no dynamic SQL**; additivo: nuovi resolver = nuovo ramo CASE). Tipo senza
  `resolver_key` → riga `UNKNOWN` (fase `APERTO`, esito NULL, terminale false, descrizione
  "n/d").
- Per le **liste** (§10.1 read-time + vista): una **vista normalizzata** `vw_stato_sorgente`
  (UNION dei resolver per dominio, chiave `sorgente_tipo_id`+uid) join-abile a
  `pratiche_sorgenti` → evita l'N+1 del dispatch per-riga.

### D4 — GUIDA "avanza-su-esito-proiettato" *(fase 2, dopo MOSTRA)*

Generalizzare l'attuale handler per-pratica `vendita.accetta_preventivo` in un meccanismo
**config-driven** "quando il documento proietta `esito=POSITIVO` (o `terminale`) → il
milestone avanza", riusando `pratiche.template_flussi_handler_eventi` (o binding dedicato).
Salda il debito in `gestione-pratiche-come-procedere.md §5.3`. **Non prima** che MOSTRA
(D1-D3 + BE + FE) sia validato su PREVENTIVI.

## 5. Vincoli (dal brief design §9)

- **No dynamic SQL**: dispatch a CASE statico su chiave controllata (come `handler_key`).
- **No mirror / read-time**: il documento resta l'unica verità; niente copia di stato.
- **Additivo, roll-out per dominio**: senza resolver → `UNKNOWN`, comportamento odierno.
- **Il motore non nomina stati di dominio**: ragiona su `fase`/`esito` normalizzati.
- Ogni oggetto con firma in `%TYPE` come da convenzione; aggiornare doc `docs/it/dbzero/`,
  rollback, e pgTAP (resolver + `fn_stato_sorgente` + seed mapping).

## 6. Criteri di accettazione (PREVENTIVI, prima consegna)

- `config.stati_doc_preventivi` ha `fase_norm`/`esito_norm`/`terminale` seedati per ogni
  stato secondo §2.
- `config.sorgenti` per il tipo "preventivo" ha `resolver_key` valorizzato.
- `fn_stato_sorgente(tipo_preventivo, uid)` su un preventivo **EMESSO** ritorna
  `fase=IN_ATTESA, esito=NULL, terminale=false, stato_descrizione='Emesso'`; su **ACCETTATO**
  `fase=IN_CORSO, esito=POSITIVO`; su **ANNULLATO** `fase=CHIUSO, esito=NEGATIVO, terminale=true`.
- Un `sorgente_tipo` senza `resolver_key` → `fn_stato_sorgente` ritorna `UNKNOWN` senza errore.
- `vw_stato_sorgente` join-abile a `pratiche_sorgenti` restituisce il descrittore per riga.

## 7. Decisioni da confermare col team DB

1. **Resolver = vista o funzione?** Proposta: **vista** per dominio (join-abile per le liste)
   + `fn_stato_sorgente` come wrapper scalare per il dettaglio singolo.
2. **`esito_norm`: FK o valore libero** verso `config.esiti_flussi_pratiche`? Proposta: FK per
   integrità (gli esiti sono un catalogo).
3. **`terminale` vs `is_abortito`**: `terminale` è il campo uniforme; `is_abortito` resta
   com'è (semantica di fallimento specifica). Confermare che non si tocca `is_abortito`.

---

*Alla presa in carico: aggiornare lo stato in testa e il §11 (Fase 0) del brief design.*
