# Analisi — Ruolo «agente / venditore» nel ciclo vendite

> **Branch lavoro**: `dev/backend-tid` (analisi) → sviluppo specifico futuro
> (DB su `dev/db-tid`, poi BE/FE).
> **Natura**: documento di analisi. Inquadra in modo **generale** la lacuna del
> concetto «agente» (commerciale/venditore) emersa dal campo
> `vendite.ordini.agente_soggetto_ruolo_id`, e cosa serve lato DB/BE/FE per
> renderlo gestibile. **Non** è un piano esecutivo: sarà oggetto di sviluppo
> dedicato.
> **Origine**: richiesta Tid 2026-06-04 — durante lo scheletro ordini (estensione
> «E — agente», [analisi-ordini-vendita.md §1.bis.E](analisi-ordini-vendita.md))
> si è scoperto che il picker agente non è realizzabile: il dato non è gestibile.
> **Decisione Tid**: la colonna `agente_soggetto_ruolo_id` **resta nullable e non
> gestita** finché questo tema non viene sviluppato a parte.

---

## 0. Sintesi in una frase

Il modello prevede un «agente» sugli ordini (e, in prospettiva, sull'intero ciclo
vendite) ma **non esiste alcun modo di creare, selezionare o validare un agente**:
il *ruolo* c'è (`VENDITORE`), tutto il resto — soggetti con quel ruolo, flusso di
gestione, lookup, guard di integrità, eventuali provvigioni — **manca**.

---

## 1. Il problema in generale

«Agente» (sinonimi nel dominio: **commerciale**, **venditore**, rappresentante) è
un **soggetto** (persona fisica o giuridica) che intermedia/origina una vendita.
Nel modello ZeroErp un soggetto assume un ruolo via `anagrafiche.soggetti_ruoli`
(coppia `soggetto_id` + `tipo_ruolo_id` → `config.tipi_ruoli`). L'agente è quindi,
concettualmente, un `soggetto_ruolo` con ruolo «venditore».

A cosa serve (motivazione originale dell'estensione E): **provvigioni** e
**reporting commerciale** (chi ha portato l'ordine/offerta/preventivo). È un
concetto **trasversale al ciclo vendite**, non specifico dell'ordine: ha senso su
preventivo, offerta, contratto, ordine e a valle in fattura per il calcolo
provvigioni.

**Stato di fatto**: il concetto è stato *agganciato* solo all'ordine (una colonna),
ma **non esiste il sottosistema** che lo rende un dato reale e affidabile.

---

## 2. Stato attuale verificato (2026-06-04)

### ✅ Cosa c'è

| Elemento | Evidenza |
| --- | --- |
| **Ruolo in tassonomia** | `config.tipi_ruoli` ha `VENDITORE` (codice `VENDITORE`, codice_interno `VE`, id=4), visibile, ammesso per nature PF e PG (`tipi_ruoli_nature_ammesse`). **Non** esiste un ruolo chiamato `AGENTE`/`COMMERCIALE`: `VENDITORE` è il candidato naturale. |
| **Struttura `soggetti_ruoli`** | `soggetto_id` + `tipo_ruolo_id` (FK a `config.tipi_ruoli`), `UNIQUE(soggetto_id, tipo_ruolo_id)`, guard natura (`trgfn_soggetti_ruoli_guard_natura_ammessa`). |
| **Colonna sull'ordine** | `vendite.ordini.agente_soggetto_ruolo_id BIGINT NULL`, FK `fk_ordini_v_agente_ruolo` → `anagrafiche.soggetti_ruoli(id)` (migration `20260603-12`). |
| **Display lista** | `vw_ordini_lista.agente_denominazione` (LEFT JOIN, **senza** filtro di ruolo). Colonna catalogo opt-in. |
| **Pass-through BE** | `agente_soggetto_ruolo_id` nelle whitelist `_CREATE_KEYS_ORDINE`/`_UPDATE_KEYS_ORDINE`; il service lo accetta e lo persiste senza validarlo. |

### ❌ Cosa manca

1. **Nessun soggetto con ruolo VENDITORE** esiste (non seeddato) e **nessun flusso
   lo crea** — a differenza di `GESTORE` che ha un'inizializzazione dedicata
   (`dbops.fn_create_gestore`). → oggi un eventuale picker filtrato su `VE`
   tornerebbe **vuoto**.
2. **Nessun endpoint lookup** per «soggetti con ruolo venditore» (esiste un
   generico CRUD `soggetti_ruoli` ma nessun lookup per-ruolo; `list_utilities_per_ruolo`
   è altra cosa).
3. **Nessun guard di integrità** sul FK agente: accetta **qualsiasi**
   `soggetti_ruoli.id` (cliente, fornitore, gestore…). 🔴 Difetto logico del
   modello (`feedback_bug_logici_modello`): un ordine potrebbe avere come «agente»
   un cliente. Va chiuso quando il tema si sviluppa.
4. **Nessun picker FE** nel drawer ordine (omesso deliberatamente,
   [analisi-ordini-vendita.md §6.ter.1](analisi-ordini-vendita.md)).
5. **Nessuna gestione anagrafica** dell'agente come entità (creazione, ricerca,
   eventuale scheda con dati commerciali/provvigioni).
6. **Nessun modulo provvigioni/commissioni** (la parola «provvigioni» compare solo
   nei commenti del modello ordine come *motivazione*, non come funzionalità).

---

## 3. Impatto sull'ordine (perché è emerso qui)

L'ordine è il **primo e unico** documento che ha agganciato l'agente. Conseguenze
dell'attuale stato:

- La colonna `agente_soggetto_ruolo_id` è **predisposta ma non popolabile** in modo
  corretto dall'UI (nessun picker, e comunque nessun agente da scegliere).
- Il FK senza guard rende il campo **semanticamente non affidabile** anche se
  valorizzato via API diretta.
- La colonna lista `agente_denominazione` resta opt-in e di fatto sempre vuota.
- La conversione **preventivo → ordine** (§7.4) **non** propaga l'agente (il
  preventivo non ha il campo): quando l'agente diventerà reale, andrà deciso se
  ereditarlo dall'upstream.

**Decisione confermata (Tid)**: la colonna **resta `NULL` e non gestita**; nessun
campo nel drawer; nessun tentativo di popolarla. Lo scheletro ordini non dipende
dall'agente.

---

## 4. Cosa serve — per layer (quando si svilupperà)

> Livello di dettaglio: *cosa*, non *come*. Le azioni DB passano per il team DB
> (`feedback_db_actions_passaggio_team`); BE/FE attendono i prerequisiti DB
> (`feedback_be_fe_attende_prerequisiti_db`).

### 4.1 DB

- **Guard di integrità FK agente** (chiude il difetto §2.3): l'ordine accetta come
  agente **solo** un `soggetti_ruoli` con `tipo_ruolo_id = VE`. Forma a scelta DB
  (trigger di validazione, o FK composita verso una vista/colonna di ruolo).
  Pattern di riferimento: i guard `child_requires_active_parent` / natura ammessa
  già presenti su `soggetti_ruoli`.
- **Eventuale seed/flow di creazione** agenti: decidere se gli agenti nascono come
  normali `soggetti_ruoli` VENDITORE (CRUD generico) o se serve un'inizializzazione
  dedicata (come `fn_create_gestore`).
- **(Provvigioni, fase successiva)**: se/quando si modellano le provvigioni,
  servirà struttura dedicata (aliquote/regole per agente, basi di calcolo,
  competenze) — fuori da questa analisi, da analizzare a parte.

### 4.2 BE

- **Lookup filtrato**: endpoint per «soggetti_ruoli con ruolo VENDITORE» per
  alimentare il picker. Valutare il pattern lookup giusto (memoria
  `feedback_lookup_whitelist_first` / `feedback_lookup_skip_area_check` per
  letture cross-dominio anagrafiche↔vendite). Forma payload `{id, denominazione,…}`.
- **Validazione service**: in `ordini_service` (create/update), validare che
  `agente_soggetto_ruolo_id`, se valorizzato, sia un VENDITORE (defense-in-depth
  applicativa speculare al guard DB).
- **Conversione upstream**: decidere l'eredità dell'agente quando arriverà sui
  documenti a monte (oggi preventivo non ha il campo).

### 4.3 FE

- **Picker agente** nel drawer ordine (e, se esteso, negli altri drawer vendite):
  autocomplete server-side sul lookup VENDITORE, con pattern restore `_obj`
  (`feedback_autocomplete_restore`). Opzionale/nullable.
- **Gestione anagrafica agenti** (se si sceglie un flusso dedicato): UI per
  creare/cercare soggetti con ruolo venditore.
- La colonna `agente_denominazione` in lista diventa significativa.

---

## 5. Decisioni di dominio aperte (da chiudere all'avvio dello sviluppo)

1. **`agente` == ruolo `VENDITORE` (VE)?** (presunto sì; in alternativa introdurre
   un ruolo dedicato `AGENTE` — ma `VENDITORE` esiste già: evitare duplicazione,
   `feedback_regola_del_2_estrai_bb`).
2. **Dove vive l'agente nel ciclo**: solo ordine, o anche preventivo/offerta/
   contratto/fattura? (impatta colonne + provvigioni + reporting).
3. **Come nasce un agente**: CRUD `soggetti_ruoli` generico vs flusso dedicato.
4. **Provvigioni in scope?** Se sì, è un modulo a sé (analisi separata): regole,
   basi, competenze, liquidazione.
5. **Cardinalità**: un solo agente per documento (oggi 1 colonna) o più
   (co-intermediazione)? Oggi 1; se servisse N, sarebbe tabella ponte.

---

## 6. Approccio consigliato (concentrico, no YAGNI)

Sviluppo incrementale quando il tema verrà ripreso (`feedback_concentrico_no_yagni`):

1. **Ratifica decisioni §5** (almeno #1 e #2).
2. **Guard DB** sul FK agente (chiude subito il difetto logico, anche prima del
   picker) — brief DB.
3. **Lookup BE VENDITORE** + validazione service.
4. **Picker FE** sul drawer ordine (nullable, opzionale).
5. **Estensione** ad altri documenti + **provvigioni** = analisi/sviluppi separati.

Finché tutto ciò non parte: **colonna nullable, non gestita** (stato attuale,
nessun debito bloccante sullo scheletro ordini).

---

## 7. Riferimenti

- Origine + decisione nullable: [analisi-ordini-vendita.md](analisi-ordini-vendita.md)
  (§1.bis.E agente, §6.ter.1 picker omesso, §9.bis #3).
- Tassonomia ruoli: `config.tipi_ruoli` (VENDITORE id=4) +
  [soggetti_ruoli](../../dbzero/anagrafiche/tabelle/soggetti_ruoli.md).
- Colonna ordine: `vendite.ordini.agente_soggetto_ruolo_id` (migration `20260603-12`),
  [ordini.md](../../dbzero/vendite/tabelle/ordini.md).
- Precedente flusso ruolo dedicato: `dbops.fn_create_gestore` (ruolo GESTORE).
