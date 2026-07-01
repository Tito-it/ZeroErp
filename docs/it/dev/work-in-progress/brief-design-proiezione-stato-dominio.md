# Brief Design — Proiezione generica dello stato di dominio nelle pratiche

> **Tipo**: brief di design autorevole (modello + piano DB/BE, FE di consumo) · **Data**: 2026-07-01
> **Owner**: Tid · **Stato**: 🟡 in lavorazione — principio validato; increment DB PREVENTIVI
> (D1-D3) in cantiere su `dev/db-tid`, vedi
> [brief-db-proiezione-stato-dominio.md](brief-db-proiezione-stato-dominio.md) §0 per le
> decisioni accettate (A-E: vista union senza `resolver_key`, `is_verdetto`, `risolto` nel
> descrittore, placement `script`, `is_abortito` intatto).
>
> **Origine**: voce **V10** e §2.4 di
> [analisi-pratiche-valutazione-stato.md](analisi-pratiche-valutazione-stato.md) — la
> *radice profonda del Problema 1*: pratica e documenti di dominio sono **due macchine a
> stati sovrapposte**, e la pratica non conosce lo stato del documento in corso.
> Cicli di vita **verificati** sui quattro domini reali (§3).
>
> **Documenti collegati**: [brief-fe-percorso-narrativo-operatore.md](brief-fe-percorso-narrativo-operatore.md)
> (V1, consuma questa proiezione), [analisi-uniformita-pratica-preventivi.md](analisi-uniformita-pratica-preventivi.md)
> (principio "non divergere dallo standalone"), [Guida Gestione Pratiche](../../guide/gestione-pratiche.md).

---

## 1. Problema — due macchine a stati sovrapposte

Le pratiche sono una macchina a stati, ma **anche** preventivo, offerta, contratto e
ordine lo sono, coi propri drawer che *già sanno* avanzare i loro stati. Dentro la
pratica le due si sovrappongono e la pratica è una macchina **grossolana e parallela**
che **non conosce lo stato fine del documento**.

Esempio (pratica PREVENTIVI): il flusso `PREVENTIVAZIONE` si chiude all'**emissione** del
preventivo. Ma da lì il preventivo continua a vivere — comunicato, accettato, magari
revisionato, evaso — e la pratica va **cieca**: l'operatore, per capire *cosa sta
accadendo*, deve **uscire dalla pratica** e aprire il documento. È la causa profonda del
«graficamente non rende» misurato nel brief V1.

## 2. Principio — proiezione, non mirror

- **❌ Mirror** (ogni stato del documento diventa un flusso): duplica la macchina a stati
  su due livelli → **viola la regola #1** (no logica duplicata), le due macchine
  divergono, e l'Anello 2 finisce per conoscere la semantica di dominio. Vietato.
- **✅ Proiezione**: il flusso è un **traguardo (milestone)** che **proietta** lo stato
  vivo del documento. Il **dominio possiede la semantica**; il **motore consuma un
  descrittore normalizzato** e resta agnostico. Read-time, single source of truth = il
  documento (coerente con la risoluzione a read-time già scelta per la versione viva).
- **Regola discriminante** (quali stati diventano milestone): uno stato di documento è un
  **flusso** *solo* se è un punto di **responsabilità o di attesa** (serve
  assegnazione/coda/SLA). Tutto il resto è **status: si mostra, non si trasforma in
  flusso.** Es.: "comunicare al cliente" = responsabilità → milestone; "cliente ha
  visualizzato" = status; "attesa accettazione" = milestone con SLA; "revisione" = loop
  (ripetibilità), mostrato come "rev. N", non nuovo flusso.

## 3. I quattro cicli di vita reali — e la mappa universale

Verificati dai seed `config.stati_doc_*`:

| Dominio | Stati (`codice_interno`) |
|---|---|
| **Preventivo** | DRAFT · EMESSO · ACCETTATO · RIFIUTATO · SCADUTO · EVASO · ANNULLATO *(+ `is_abortito`)* |
| **Offerta** | BOZZA · EMESSA · ACCETTATA · RIFIUTATA · SUPERATA · ANNULLATA |
| **Ordine** | DRAFT · CONFERMATO · EVASO · ALLOCATO · SPEDITO · CONSEGNATO · FATTURATO · ANNULLATO |
| **Contratto** | DRAFT · ATTIVO · CESSATO · ANNULLATO *(+ `is_abortito`)* |

Tutti mappano su un **vocabolario universale** piccolo e stabile (la prova che «funziona
sempre»):

```text
stato di dominio             → fase        esito        terminale
─────────────────────────────────────────────────────────────────
DRAFT / BOZZA                → APERTO      —            no
EMESSO / EMESSA              → IN_ATTESA   —            no   (si aspetta il cliente)
CONFERMATO / ATTIVO          → IN_CORSO    —            no
ALLOCATO/SPEDITO/CONSEGNATO  → IN_CORSO    —            no   (fulfillment)
ACCETTATO / ACCETTATA        → IN_CORSO    POSITIVO     no
RIFIUTAT* / SCADUTO / SUPERATA → CHIUSO    NEGATIVO     sì
EVASO / FATTURATO / CESSATO  → CHIUSO      POSITIVO     sì
ANNULLAT*                    → CHIUSO      NEGATIVO     sì   (is_abortito)
```

> Nota: `is_abortito` esiste **solo** su preventivi/contratti, non su offerte/ordini →
> proprio per questo serve un **asse di normalizzazione uniforme** (§4), non un flag
> sparso.

## 4. Il contratto normalizzato — "lo stato dello stato"

Ogni dominio sa produrre, e la pratica sa consumare, un descrittore **sempre uguale**:

| Campo | Dominio | A cosa serve |
|---|---|---|
| `stato_codice` + `stato_descrizione` | valori nativi del dominio | **Display**: "Emesso", "Accettato" (alimenta la vista-racconto V1) |
| `fase` ∈ `APERTO · IN_CORSO · IN_ATTESA · CHIUSO` | mapping dichiarato dal dominio | **Routing/colore**: il motore ragiona su questo, mai sui nomi di dominio |
| `esito` → `config.esiti_flussi_pratiche` (`—/POSITIVO/NEGATIVO/PARZIALE`) | mapping dichiarato dal dominio | **Verdetto**: fa avanzare il milestone (§6). **Riusa il vocabolario esiti di oggi** |
| `terminale` (bool) | dominio | il documento non evolverà più (auto-chiusura milestone) |
| `azioni` (jsonb, opzionale) | `fn_available_actions_*` | la **prossima azione** suggerita nel documento |

**Punto architetturale**: è il **dominio a dichiarare la mappa** (vendite *sa* che
ACCETTATO=POSITIVO); il motore consuma solo il risultato. Concretamente: un piccolo set
di colonne di normalizzazione (`fase_norm`, `esito_norm`, `terminale`) sulle
`config.stati_doc_*` **owned dal dominio** — `is_abortito` ne è già l'abbozzo.

## 5. Architettura di aggancio (pulita rispetto agli anelli)

```text
pratiche.pratiche_sorgenti  (link pratica↔documento — GIÀ ESISTE)
   │  (sorgente_tipo_id, sorgente_uid)
   ▼
config.sorgenti             (registry per tipo sorgente — GIÀ ESISTE)
   │  resolver_key  (chiave controllata, no dynamic — pattern implementation_key)
   ▼
resolver del dominio        (vendite: vista/funzione normalizzata sui stati_doc_*)
   │
   ▼
descrittore universale (§4) →  la pratica lo MOSTRA / ci ROUTA sopra
```

- Il motore chiama il resolver **per chiave** (come handler / `implementation_key`), a
  **read-time**. Non nomina **mai** uno stato di dominio.
- **Degrada con grazia**: `sorgente_tipo` senza resolver → descrittore `UNKNOWN`, il
  milestone resta un flusso manuale come oggi. **Additivo**, roll-out per dominio (pattern
  `attivo=false`).
- **Layering**: l'Anello 2 non legge `vendite.stati_doc_*`; interroga il resolver che il
  dominio espone. Nessuna dipendenza inversa.

## 6. Le due direzioni (una sola meccanica, tutti i domini)

- **MOSTRA** (il bisogno primario): la pratica proietta `stato_descrizione` + `fase` del
  documento vivo → l'operatore vede *cosa sta accadendo* senza uscire dalla pratica.
- **GUIDA**: quando il documento proietta `esito = POSITIVO` (o `terminale`), il milestone
  avanza. È la **generalizzazione** dell'handler `vendita.accetta_preventivo` (oggi
  per-pratica PREVENTIVI): un solo meccanismo "avanza-su-esito-proiettato" per tutti i
  domini, config-driven. Salda il debito noto in `gestione-pratiche-come-procedere.md §5.3`.

## 7. Cosa esiste già — è *normalizzare*, non greenfield

| Pezzo | Stato | Nota |
|---|---|---|
| `pratiche.pratiche_sorgenti` | ✅ esiste | link pratica↔documento (ROOT/COLLEGATO, `meta`) |
| `config.sorgenti` | ✅ esiste | registry dei tipi sorgente (da estendere con `resolver_key`) |
| `config.stati_doc_*` con `descrizione` | ✅ esiste | display già pronto; `is_abortito` = abbozzo di normalizzazione |
| `fn_available_actions_*` | ✅ preventivo/offerta (ordini parziale) | la "prossima azione" per stato |
| `vw_preventivi_pratiche` | ✅ esiste | **prima** proiezione preventivo↔pratiche già in casa |
| `config.esiti_flussi_pratiche` | ✅ 2026-07-01 | il target normalizzato dell'`esito` |
| `template_flussi_handler_eventi` | ✅ esiste | la direzione GUIDA in embrione |

## 8. Deliverable

**DB (brief → team DB):**
- **D1** — colonne di normalizzazione (`fase_norm`, `esito_norm`, `terminale`) sulle
  `config.stati_doc_*` **di ciascun dominio** (il dominio dichiara la mappa §3).
- **D2** — resolver normalizzato per dominio (vendite): vista/funzione che, dato
  `sorgente_uid`, ritorna il descrittore §4 leggendo lo stato corrente + il mapping D1.
- **D3** — `config.sorgenti.resolver_key` + funzione generica di motore
  `pratiche.fn_stato_sorgente(sorgente_tipo_id, sorgente_uid)` che dispatcha per chiave
  (controllata, no dynamic) e ritorna il descrittore.
- **D4** *(GUIDA, fase 2)* — generalizzare "avanza-su-esito-proiettato" (config su
  `template_flussi_handler_eventi` o binding dedicato), sostituendo l'handler accetta
  per-pratica.

**BE:**
- esporre il descrittore nei payload pratica/percorso/coda (display fields) → **alimenta
  V1**. Nessuna logica: solo campi.

**FE:**
- consumo nella vista-racconto (brief V1): "sei qui nella vita del documento".

## 9. Vincoli e non-obiettivi

- **Il motore non nomina stati di dominio**: ragiona su `fase`/`esito` normalizzati.
- **Niente mirror**: non si copiano gli stati del documento in flussi.
- **Read-time**: nessuna duplicazione dello stato (il documento resta l'unica verità).
- **Additivo**: senza resolver, comportamento di oggi. Roll-out per dominio.
- **Non è l'ispettore di configurazione** (V4) né la UI admin: qui è la proiezione
  *runtime* di uno stato che esiste già.

## 10. Domande aperte (decisioni)

1. **Read-time (pull) vs materializzato (push) per le LISTE?** Per il dettaglio pratica la
   `fn` read-time basta; per liste con molte pratiche valutare una **vista** normalizzata
   per dominio (join), o materializzare solo se il profiling lo impone. *Proposta:
   read-time + vista; materializzare solo su evidenza di performance.*
2. **Dove vive il mapping** `fase_norm`/`esito_norm`? Colonne sulle `stati_doc_*`
   (dominio-owned, minimale) vs tabella-mapping centrale. *Proposta: colonne sulle
   `stati_doc_*`.*
3. **`azioni` nel descrittore** subito (riuso `fn_available_actions_*`) o dopo la fase
   MOSTRA? *Proposta: dopo — prima "cosa sta accadendo", poi "cosa fare".*
4. **Struttura esatta di `config.sorgenti`** come registry: verificare colonne prima di
   aggiungere `resolver_key`.

---

*Brief vivo: aggiornare lo stato in testa e la riga V10 di
[analisi-pratiche-valutazione-stato.md](analisi-pratiche-valutazione-stato.md) a chiusura.*
