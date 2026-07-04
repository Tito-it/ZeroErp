# Brief Design — Definizioni di workflow versionate per emittente (edizioni + fork)

> **✅ CHIUSO (2026-07-04)** — Design implementato: Fasi 0-2 (DB + BE + admin edizioni) e
> Slice 2 anelli 1-3 (editing strutturale BOZZA) in produzione-dev, validati E2E. Le
> decisioni aperte §6 sono state risolte in fase di implementazione (immutabilità «Leggera»
> = lock strutturale + display correggibile; ≤1 BOZZA per scope). **Residuo**: Fase 3
> (editor UI, cantiere V4/V5) + catalogo preset di settore V3 — da riaprire con brief
> dedicato al momento del bisogno.
>
> **Tipo**: brief di design autorevole (modello + piano; il cambio schema sarà delegato
> al team DB con brief dedicato) · **Data**: 2026-07-02
> **Owner**: Tid · **Stato**: 🟢 in corso — **modello deciso** (C «edizioni versionate +
> fork», decisione 2026-07-02). **Fasi 0–2 delegate al DB** in
> [brief-db-step-dominio-e-definizioni-versionate.md](brief-db-step-dominio-e-definizioni-versionate.md)
> (Parte 2); **Fasi 0–1 applicate dal team DB (2026-07-02)**. Questo brief resta il
> **design-of-record**: razionale, modello, **Fase 3** (UI admin V4/V5) e domande aperte.
>
> **Origine**: voce **V2** e §2.2 di
> [analisi-pratiche-valutazione-stato.md](analisi-pratiche-valutazione-stato.md) — il
> *vero buco architetturale*: le definizioni di workflow (`tipi_prestazione`,
> `template_flussi` e figli) sono **globali**, solo l'istanza è per-emittente. Società
> A e B non possono avere due workflow "preventivi" diversi senza clonare il tipo.
> **Assorbe V6** (versionamento / pratiche in volo).
>
> **Documenti collegati**: [Guida Gestione Pratiche](../../guide/gestione-pratiche.md),
> [Gestione Pratiche — Configurazione](../../guide/gestione-pratiche-configurazione.md),
> [brief-design-proiezione-stato-dominio.md](brief-design-proiezione-stato-dominio.md) (V10, indipendente),
> [gestione-pratiche-come-procedere.md](gestione-pratiche-come-procedere.md).

---

## 1. Problema

Due fatti verificati sul modello vivo:

1. **Nessun asse per-azienda sulle definizioni.**
   [`template_flussi`](../../dbzero/pratiche/tabelle/template_flussi.md) pende da
   `tipo_prestazione_id` e non ha `emittente_fiscale_id`;
   [`tipi_prestazione`](../../dbzero/pratiche/tabelle/tipi_prestazione.md) è condiviso.
   L'unica variazione possibile oggi è **clonare il tipo** (`PREVENTIVI_A`,
   `PREVENTIVI_B`): identità di reporting rotta, fix da replicare a mano, esplosione di
   seed e binding.
2. **La pratica non pinna nulla** (V6 già vivo). Il percorso è calcolato *a lettura* dal
   set corrente di `template_flussi` del tipo: modificare un template **cambia
   retroattivamente la roadmap di tutte le pratiche aperte**. Non morde solo perché oggi
   il seed lo tocca una persona sola, a mano.

## 2. Decisione — modello C «edizioni versionate + fork»

Confrontati tre modelli (decisione 2026-07-02, dettaglio in analisi §2.2):

| | A. Clone del tipo | B. Patch per-step | **C. Edizioni + fork (SCELTO)** |
|---|---|---|---|
| Identità condivisa (report per tipo) | ❌ | ✅ | ✅ |
| Fix al preset si propaga | ❌ mai | ✅ vivo (anche troppo) | 🟠 assistito (diff + banner) |
| Grafo prerequisiti / invarianti | ✅ semplici | ❌ scope-aware per sempre | ✅ semplici (per definizione) |
| Pratiche in volo (V6) | ❌ | ❌ | ✅ **pin alla creazione** |
| UI admin futura (V4/V5) | — | ❌ merge mentale | ✅ oggetto naturale (bozza→pubblica) |
| Costo | zero | medio, perpetuo | medio-alto, **una tantum** |

Ragioni della scelta: (1) è lo **standard dei workflow engine** (Camunda/Flowable/
Temporal versionano la process definition e pinnano le istanze); (2) scioglie **V2+V6
con un solo gesto** e dà a V4/V5 il loro oggetto; (3) la variazione fra aziende è
**strutturale** (step in più/in meno, bivi), non solo scalare — e per gli scalari
esiste già `config.parameter_overrides`; (4) il fork con provenance è un **pattern già
in casa** (`ui.lista_preset` + banner "preset aggiornato" DEF-2).

## 3. Il modello dati

### 3.1 Header: `pratiche.workflow_definizioni`

Una riga = **una edizione** di un workflow, per un tipo prestazione e uno scope.

| Colonna | Tipo | Note |
|---|---|---|
| `id` | IDENTITY | PK tecnica |
| `tipo_prestazione_id` | FK `tipi_prestazione` | l'identità condivisa resta il tipo |
| `emittente_fiscale_id` | FK, **nullable** | `NULL` = **preset** (vale per chi non ha un'edizione propria) |
| `versione` | integer | progressivo per (tipo, emittente) |
| `stato` | `BOZZA` / `PUBBLICATA` / `RITIRATA` | ciclo di vita §3.3 |
| `preset_origine_id` | FK self, nullable | **provenance**: da quale definizione è nato il fork |
| `versione_origine` | integer, nullable | snapshot della versione del preset al momento del fork (per il diff/banner) |
| `descrizione`, `meta`, audit std | — | convenzioni di casa (tx_id, storicizza, …) |

Vincoli chiave:

- `UNIQUE (tipo_prestazione_id, emittente_fiscale_id, versione)` (NULLS NOT DISTINCT);
- **una sola PUBBLICATA per scope**: unique parziale su
  `(tipo_prestazione_id, emittente_fiscale_id) WHERE stato = 'PUBBLICATA'`.

### 3.2 Re-parent dei template + pin sulle pratiche

- `template_flussi.definizione_id` (NOT NULL dopo backfill). Gli unique migrano:
  `uq (tipo, codice)` → `uq (definizione_id, codice)`;
  `uq_template_flussi_chiusura (tipo) WHERE chiude_pratica` → `(definizione_id) WHERE chiude_pratica`.
- **I figli non cambiano**: `template_flussi_prerequisiti`, `template_flussi_canali`,
  `template_flussi_handler_eventi`, `competenze_flussi` referenziano righe di
  `template_flussi` e **seguono la definizione** per costruzione. `formule_tempo`
  aggancia coppie di template della stessa definizione (guard di coerenza).
- `pratiche.definizione_id` (NOT NULL dopo backfill): **pinnata alla creazione**, mai
  aggiornata. Nuova guard su `flussi` (INSERT): `template_flusso_id` deve appartenere
  alla definizione pinnata della pratica (errore parlante).

### 3.3 Ciclo di vita dell'edizione

```text
BOZZA ──(pubblica)──> PUBBLICATA ──(sostituita da nuova versione)──> RITIRATA
  ^ editabile            ^ IMMUTABILE strutturalmente                  ^ non istanziabile;
    liberamente            (unica per scope)                             le pratiche in volo
                                                                         continuano sul pin
```

- Modificare una PUBBLICATA = **creare una nuova versione** (copia in BOZZA →
  modifica → pubblica; la precedente passa a RITIRATA). Guard DB sull'immutabilità.
- Le pratiche in volo **non si toccano**: finiscono con l'edizione con cui sono nate.
  (Analogo di `obsoleto_dal`: asse "istanziabile per il nuovo" separato dall'esistenza.)

### 3.4 Risoluzione (un solo punto, alla creazione)

`pratiche.fn_risolvi_definizione(p_tipo_prestazione_id, p_emittente_fiscale_id)`:

1. definizione **PUBBLICATA dell'emittente**, se esiste;
2. altrimenti il **preset** (PUBBLICATA con `emittente_fiscale_id IS NULL`);
3. altrimenti errore parlante (codice registrato, es. `E_DEFINIZIONE_NON_TROVATA`).

Usata da `crea_pratica` (pin) e da `fn_genera_pratica_da_flusso` (la generazione
cross-pratica risolve la definizione **dell'emittente della pratica sorgente** →
il cross-pratica diventa emittente-aware gratis).

### 3.5 Fork e drift

- `fn_fork_definizione(p_definizione_id, p_emittente_fiscale_id)`: copia header +
  template + figli in una nuova definizione BOZZA con `preset_origine_id` +
  `versione_origine`.
- **Drift**: quando il preset d'origine ha una PUBBLICATA con versione >
  `versione_origine` → banner "preset aggiornato" (pattern `ui.lista_preset` DEF-2),
  con diff informativo. L'allineamento è **una scelta**, mai automatico.

## 4. Cosa NON cambia

- **Runtime del motore intatto**: macchina a stati, giornale, sospensioni, tempi,
  handler dispatch — nessun cambio. L'asse tocca solo *quale set di template* governa
  una pratica.
- **Anello 2 resta agnostico**: `emittente_fiscale_id` è *meccanismo* di scoping (già
  presente su `pratiche.pratiche`), non semantica di dominio.
- **`config.parameter_overrides` resta** il posto dei parametri scalari di business:
  qui si versionano le *strutture* (step, grafo, automazioni), non i numeri.
- **`tipi_prestazione` resta l'identità condivisa** (reporting cross-emittente sano).

## 5. Piano a fasi (ogni fase rilasciabile da sola)

| Fase | Contenuto | Comportamento visibile |
|---|---|---|
| **0 — DB fondazione** | `workflow_definizioni` + seed "v1 preset PUBBLICATA" per ogni tipo esistente; `definizione_id` su `template_flussi` e `pratiche` (backfill + NOT NULL); swap unique | **Nessuno** (una definizione per tipo ≡ oggi) |
| **1 — Pin + guard** | `fn_risolvi_definizione`, pin in `crea_pratica`/generazione, guard flusso↔definizione, guard immutabilità PUBBLICATA | Le pratiche nuove pinnano; le definizioni pubblicate diventano immutabili |
| **2 — Fork + drift** | `fn_fork_definizione`, provenance, versioning (`fn_pubblica_definizione`), BE/FE banner drift | La prima azienda può avere il **suo** workflow |
| **3 — Aggancio V4/V5** | L'ispettore/editor lavora su BOZZA e pubblica | UI admin (cantiere separato) |

## 6. Domande aperte (decisioni per l'owner)

1. **Visibilità dei tipi per emittente**: un emittente può istanziare un tipo se esiste
   una definizione risolvibile (derivata) — serve anche un **opt-out esplicito** ("questa
   azienda non fa contratti")? *Proposta: derivare dall'esistenza; opt-out solo al
   bisogno reale (regola del 2).*
2. **Granularità dello scope**: solo `emittente_fiscale` per ora? *Proposta: sì; il
   "settore" vive come catalogo di preset (V3), non come livello di risoluzione.*
3. **Perimetro dell'immutabilità** su PUBBLICATA: lock totale o campi display
   (`descrizione`, etichette) correggibili? *Proposta: lock strutturale (step, grafo,
   automazioni, esiti); display correggibile.*
4. **Catalogo preset di settore (V3)**: più preset per tipo come *libreria da cui
   forkare*, fuori dalla risoluzione runtime (che vede un solo preset attivo per tipo).
   *Da progettare nel brief V3.*
5. **Migrazione dei 2 tipi PREVENTIVI esistenti** (`PREVENTIVI_IMMEDIATA`/`_DIFFERITA`):
   restano due tipi (differenza di *policy*, già decisa) o diventano un tipo con due
   edizioni? *Proposta: restano due tipi — la distinzione è di dominio (handler_params),
   non di scope aziendale. Rivalutare quando arriva il secondo emittente reale.*

---

*Brief vivo: aggiornare lo stato in testa e la riga V2 di
[analisi-pratiche-valutazione-stato.md](analisi-pratiche-valutazione-stato.md) a chiusura.
Il cambio schema di Fase 0/1 sarà delegato al team DB con `brief-db-*` dedicato.*
