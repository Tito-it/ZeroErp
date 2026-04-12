# Sviluppo Listini — Pricing ZeroERP (WIP v3)

> Stato: **BACKEND E FRONTEND IMPLEMENTATI, DA TESTARE SU UI REALE. FIX CRITICI IN SPRINT A.**
>
> Ultima revisione: aprile 2026 (v3 — consolidato da sviluppo-listini.md + sviluppo-listini-v2.md
> + integrazioni critiche da analisi esterna)
>
> Questo documento consolida:
> * analisi architetturale DB (ex `gestione-listini.md`, 24-02-2026)
> * stato backend + frontend listini (ex `gestione-articoli-listini.md`, parti §4, §6)
> * analisi ciclo di vita versione e decisioni operative D1-D7 (ex `sviluppo-listini-v2.md`)
> * **[INTEGRAZIONI v3]** gap e raccomandazioni emersi da analisi critica — evidenziati
>   con il tag `[NUOVO v3]` in tutto il documento
>
> **Fuori scope di questo documento:**
> * Rettifiche prezzi (DB-L4) → [sviluppo-rettifiche.md](sviluppo-rettifiche.md)
> * Listini fornitori e derivazione → documento separato `sviluppo-listini-fornitori.md`
>
> Prerequisiti già disponibili:
> * Schema `catalogo` completo (articoli, UoM, BoM, note)
> * Schema `vendite.listini*` operativo fino a DB-L3
> * Funzione DB: `vendite.fn_resolve_prezzo_listino`, `vendite.fn_resolve_commessa_prezzi`
> * Backend + frontend listini implementati (§10 e §11)
>
> Riferimenti:
> * [docs/it/dbzero/vendite/tabelle/listini.md] — schema listini
> * [docs/it/dev/work-done/gestione-articoli.md] — dominio catalogo (completato)
> * [docs/it/dev/work-in-progress/gestione-commesse-v2.md] — integrazione commessa
> * [docs/it/dev/api.md] — linee guida API

---

## 1) Obiettivo

Definire un modello listini/prezzi scalabile che supporta:

1. pricing standard (prezzo fisso/versionato),
2. pricing utilities (gas/energia/idrico) con evoluzione futura a formule/scaglioni,
3. integrazione piena con modello commessa v2,
4. rettifiche prezzi sia manuali che automatiche.

La logica è la stessa sia per il dominio utility sia per il dominio commercio.

---

## 2) Stato attuale e gap

### Stato attuale

1. Schema `vendite.listini*` completo e operativo fino a DB-L3.
2. Backend e frontend listini **implementati e verdi sui test unitari**.
3. Refactor invariante univocità (2026-04-09) completato: drop `priorita` da versioni e associazioni, nuovo constraint GIST cross-listino.
4. Manca: verifica su UI reale, fix critici backend, operazioni di convenienza, motore rettifiche.

### Gap chiusi (DB-L1, L2, L3)

1. Struttura listini/versioni/righe/associazioni operativa
2. Resolver prezzo deterministico con 7 livelli di precedenza
3. Refactor invariante univocità associazioni (2026-04-09)
4. Integrazione commessa v2 (snapshot pricing, `prezzo_bloccato`, `pricing_mode`)
5. Base dati estensibile per formule/scaglioni v2

### Gap aperti — master table

| ID      | Tipo             | Descrizione                                                                        | Priorità  | Sprint            |
| ------- | ---------------- | ---------------------------------------------------------------------------------- | --------- | ----------------- |
| F1      | Bug critico      | Guard stato versione su CRUD righe mancante nel backend                            | BLOCCANTE | A                 |
| F2      | Bug critico      | Whitelist PATCH versione per stato non implementata                                | BLOCCANTE | A                 |
| F3      | Test             | Smoke + unit test per i guard F1/F2                                                | Alta      | A                 |
| O1      | Convenienza      | Clone versione                                                                     | Alta      | B                 |
| O2      | Convenienza      | DELETE versione BOZZA                                                              | Alta      | B                 |
| O3      | Convenienza      | DELETE listino mai usato                                                           | Media     | B                 |
| UI      | Test             | Permessi, readonly mode, drawer pattern su UI reale                                | Alta      | A                 |
| DOC     | Documentazione   | API listini in `docs/it/backend/vendite/manual/`                                   | Media     | B                 |
| **N1**  | **[NUOVO v3]**   | **Valutare `daterange` nativo PostgreSQL al posto di due colonne date**            | Media     | roadmap v2        |
| **N2**  | **[NUOVO v3]**   | **Job monitor scadenza versioni attive**                                           | Alta      | B                 |
| **N3**  | **[NUOVO v3]**   | **Flusso prezzo-documento → commessa: gap definizione preventivo**                 | Alta      | A                 |
| **N4**  | **[NUOVO v3]**   | **Match_level 3: documentare come rilevante solo in contesti multi-emittente**     | Bassa     | DOC               |
| **N5**  | **[NUOVO v3]**   | **Rettifica su prezzo non ancora fatturato: gap parziale rispetto a DB-L4**        | Media     | analisi           |
| **N6**  | **[NUOVO v3]**   | **Rettifica controllata riga ATTIVA non ancora propagata in commessa/fatturabile** | Alta      | B                 |
| **N7**  | **[NUOVO v3]**   | **Variazione prezzo eccezionale su commessa in stato LIBERO o CONFERMATO**         | Alta      | B                 |
| **N8a** | **[NUOVO v3]**   | **Variazione percentuale massa su versione BOZZA (aumento/riduzione prezzi)**      | Alta      | B                 |
| **N8b** | **[NUOVO v3]**   | **Documentazione operativa "listino post-it": perimetro e limiti**                 | Alta      | DOC               |
| DB-L4   | Dominio separato | Motore rettifiche prezzi post-emissione                                            | —         | schedulare dopo B |

---

## 3) Principi architetturali

1. Modello commessa v2 invariato: nessun bypass.
2. Prezzo risolto in modo deterministico e auditabile.
3. Emittente fiscale dimensione attiva già in v1.
4. UoM non forzata unica per articolo in listino.
5. Rettifiche possibili sia manuali che automatiche, con stesso motore delta.
6. Formule/scaglioni previste ma non obbligatorie in v1.
7. **[NUOVO v3] DB-first esteso**: ogni guard di coerenza deve esistere sia nel service Python (messaggi leggibili) sia come vincolo/trigger DB (defense-in-depth contro chiamate dirette all'API o a psql). La protezione solo-service non è sufficiente. I bug F1/F2 violano esattamente questo principio.

---

## 4) Decisioni chiave

### 4.1 Emittente fiscale attiva in v1

`emittente_soggetto_ruolo_id` entra subito tra le dimensioni prezzo. È già centrale nei flussi fatturazione; escluderla crea ambiguità e richiede rework su resolver e migrazioni successive.

### 4.2 UoM non unica per articolo

La chiave prezzo include `articolo_id + uom_id`. `catalogo.articoli_uom_operativa` prevede più UoM operative per articolo; forzare UoM unica romperebbe casi reali (ore, confezioni, conversioni operative).

### 4.3 Rettifiche: doppio canale, motore unico

`MANUALE` e `AUTOMATICA` usano la stessa pipeline delta. Un solo motore evita divergenze tra processi umani e batch.

### 4.4 Formule/scaglioni in v2

v1: prezzi fissi/versionati. Schema predisposto per `FORMULA` e `SCAGLIONI` senza DDL aggiuntivo.

### 4.5 Contesto non-utility esplicito

`utility_id = NULL` è un caso di primo livello, non un'eccezione. Il resolver copre esplicitamente i casi commercio.

### 4.6 Modello operativo C ridotto — PARZIALMENTE RIVISTO (D1 + N6/N7)

* Fix bug guard stato (F1, F2, F3)
* Operazioni di convenienza (O1, O2, O3)
* **[NUOVO v3]** Rettifica controllata su riga ATTIVA non ancora propagata — ammessa con guard esplicito (N6)
* **[NUOVO v3]** Variazione prezzo eccezionale su commessa LIBERA o CONFERMATA — ammessa con audit obbligatorio (N7)
* Rettifiche su fatture già emesse → DB-L4 separato (D4 sospeso)

### 4.7 Auto-close alla attivazione — CONFERMATO (D3, D6)

L'attivazione di una nuova versione chiude automaticamente la precedente (`valido_al = nuova.valido_dal - 1`) nella stessa transazione. Dialog di conferma in UI mostra le versioni che verranno chiuse. Niente job pgAgent per questa operazione.

### 4.8 Tre azioni separate, no wizard (D5)

1. **Clona** — genera nuova versione BOZZA copiando le righe della sorgente
2. **Modifica** — editing libero in BOZZA
3. **Attiva** — transizione BOZZA → ATTIVA che innesca l'auto-close della precedente

### 4.9 Clone retroattivo ammesso con vincolo (D2)

`nuova.valido_dal >= precedente.valido_dal`. Dialog di avviso se retroattivo: i documenti pregressi non vengono corretti automaticamente.

### 4.10 Audit righe BOZZA: sandbox totale (D7)

Nessun tracciamento history su righe BOZZA. `data_update/user_update` standard sufficiente. Se in futuro servirà storicizzazione completa, si aggiunge colonna `storico boolean` sulla versione.

---

## 5) Modello dati (v1)

### 5.1 Tabelle core

1. **`vendite.listini`** — anagrafica (codice, descrizione, dominio, attivo). Domini v1: `UTILITY`, `COMMERCIO`. Domini futuri possibili: `INDUSTRIA`.
2. **`vendite.listini_versioni`** — versionamento temporale (`valido_dal`, `valido_al`, stato). Stati: `BOZZA` → `ATTIVA` → `CHIUSA`.
3. **`vendite.listini_righe`** — prezzo per contesto dimensionale. Precisione `numeric(22,10)`. Nessuna data sulla riga: la finestra temporale è esclusivamente sulla versione padre.
4. **`vendite.listini_associazioni`** — primo filtro del resolver: quali listini sono candidati per un dato contesto.

> **Post-refactor 2026-04-09**: i campi `priorita` su `listini_versioni` e `listini_associazioni`
> sono stati **droppati fisicamente** (migration `20260409-04/-05`). Il resolver aggiornato
> (`20260409-04` in `20_code/vendite`) non li referenzia più. Qualsiasi documentazione
> precedente che cita `priorita` come colonna attiva su queste tabelle è obsoleta.

### 5.2 Dimensioni riga listino (v1 attive)

| Dimensione                    | Obbligatorio |
| ----------------------------- | ------------ |
| `articolo_id`                 | sì           |
| `uom_id`                      | sì           |
| `billing_account_id`          | no           |
| `utility_id`                  | no           |
| `emittente_soggetto_ruolo_id` | no           |

Il periodo di validità è sulla versione, non sulla riga.

### 5.3 Vincoli chiave

| Vincolo                              | Tabella                | Tipo                       | Semantica                                                                         |
| ------------------------------------ | ---------------------- | -------------------------- | --------------------------------------------------------------------------------- |
| `ex_listini_versioni_no_overlap`     | `listini_versioni`     | GIST EXCLUDE               | No overlap temporale tra versioni ATTIVE dello stesso listino                     |
| `ex_listini_associazioni_no_overlap` | `listini_associazioni` | GIST EXCLUDE cross-listino | Per ogni triple (BA, utility, emittente) una sola associazione attiva per periodo |
| `uq_listini_righe_key_attiva`        | `listini_righe`        | UNIQUE parziale            | Una sola riga attiva per combinazione dimensionale completa in una versione       |
| `chk_listini_versioni_date`          | `listini_versioni`     | CHECK                      | `valido_al > valido_dal` se valorizzato                                           |
| `chk_listini_versioni_stato`         | `listini_versioni`     | CHECK                      | `stato IN ('BOZZA', 'ATTIVA', 'CHIUSA')`                                          |

### 5.4 Policy precisione prezzo

| Layer                  | Precisione     | Note                                             |
| ---------------------- | -------------- | ------------------------------------------------ |
| `listini_righe`        | numeric(22,10) | Massima precisione                               |
| `commesse_attivita`    | numeric(22,10) | Snapshot senza arrotondamento                    |
| `attivita_fatturabili` | numeric(22,10) | Propagazione fedele                              |
| `fatture_righe`        | numeric(22,6)  | Arrotondamento solo qui, per esposizione fiscale |

Nessuna funzione intermedia introduce arrotondamenti anticipati.

---

## [NUOVO v3] 5.5 Considerazione architetturale: `daterange` nativo PostgreSQL (N1)

> Tag: **N1** — Roadmap v2, non bloccante per v1.

Le colonne `valido_dal date + valido_al date NULL` con `COALESCE(valido_al, 'infinity'::date)` funzionano correttamente. Tuttavia il pattern NULL-come-infinito si replica in ogni query che filtra per data: il resolver, i report, i job di monitoraggio devono tutti replicare la stessa logica di gestione NULL.

**Alternativa**: usare il tipo nativo `daterange` di PostgreSQL come colonna singola su `listini_versioni` e `listini_associazioni`.

Vantaggi concreti:
* Il confronto `@>` gestisce l'infinito nativamente (`[2026-01-01,)` = open-ended, senza COALESCE)
* L'indice GIST è più diretto; il codice dei vincoli di overlap diventa più leggibile
* Elimina un'intera classe di bug potenziali su query con NULL

Svantaggi:
* Refactor DDL non banale su tabelle già in produzione
* Il backend Django deve gestire la serializzazione/deserializzazione del tipo range

**Raccomandazione**: non blocca v1. Valutare obbligatoriamente prima di v2 (formule/scaglioni moltiplicano le query su range e amplificano il problema). Aprire ticket tecnico e inserire nella roadmap v2 come prerequisito architetturale.

---

## 6) Ciclo di vita versione

### 6.1 Stati e transizioni

```
BOZZA ──────→ ATTIVA ──────→ CHIUSA
(sandbox)    (operativa)    (storica)
```

| Da     | A      | Ammessa | Guard                                 |
| ------ | ------ | ------- | ------------------------------------- |
| BOZZA  | ATTIVA | sì      | almeno 1 riga attiva + listino attivo |
| BOZZA  | CHIUSA | no      | transizione non logica                |
| ATTIVA | BOZZA  | no      | no rollback                           |
| ATTIVA | CHIUSA | sì      | sempre ammesso                        |
| CHIUSA | *      | no      | stato terminale                       |

### 6.2 Regola di immutabilità righe in ATTIVA

Quando il resolver risolve un prezzo per un'attività di commessa, il valore viene congelato in `commesse_attivita.prezzo_snapshot`. La pipeline di fatturazione legge da `attivita_fatturabili`, non ricalcola dal listino.

Se una riga in versione ATTIVA fosse modificabile, le fatture già emesse non cambierebbero (non rileggono il listino), ma il prezzo "ufficiale" cambierebbe: drift silenzioso tra documento storico e listino, audit incoerente.

**Per questo le righe in versione ATTIVA sono immutabili.** Per cambiare un prezzo si crea una nuova versione con `valido_dal` futuro.

### 6.3 Operazioni ammesse per stato

| Stato      | Righe                           | Testata versione                                 | Cambio stato          |
| ---------- | ------------------------------- | ------------------------------------------------ | --------------------- |
| **BOZZA**  | Create / Update / Delete liberi | PATCH liberi su tutti i campi                    | → ATTIVA (se ≥1 riga) |
| **ATTIVA** | Nessuna operazione              | PATCH solo `valido_al` (programmazione chiusura) | → CHIUSA              |
| **CHIUSA** | Nessuna operazione              | Nessuna operazione                               | (terminale)           |

> **[NUOVO v3 — BUG F1/F2]**: lo stato attuale del backend **non rispetta questa tabella**. Vedi §7.

### 6.4 Workflow operativo "cambio prezzi"

1. V001 ATTIVA, valida `2026-01-01..NULL`, contiene N righe
2. L'utente clona V001 in V002 BOZZA con `valido_dal = 2026-04-01`
3. Modifica liberamente le righe cambiate in V002
4. Attiva V002 → il backend in transazione chiude automaticamente V001 con `valido_al = 2026-03-31`
5. Dialog di conferma in UI mostra la versione che verrà chiusa prima di procedere
6. V001 transita formalmente a CHIUSA (manuale, per pulizia visiva; il resolver la esclude già dal filtro temporale)

---

## 7) Bug critici — Sprint A (F1, F2, F3)

### F1 — Guard stato versione su CRUD righe (BLOCCANTE)

**File**: `apps/vendite/services/listini_service.py`

**Problema**: `fn_create_riga`, `fn_update_riga`, `fn_delete_riga` non verificano lo stato della versione padre. Il frontend nasconde i pulsanti se `stato != BOZZA` (flag `isBozza`), ma il backend non ha guard. Qualsiasi chiamata API diretta (curl, Postman, test automatici) può modificare righe in versione ATTIVA o CHIUSA, causando drift tra listino e snapshot in commessa.

**Fix**:

```python
versione = _get_versione_or_raise(listino_id, versione_id, function_name=function_name)
ErrorManager.require(
    versione["stato"] == "BOZZA",
    code="E_VENDITE_VALIDATION",
    message="Operazione non consentita.",
    detail=f"Le righe sono modificabili solo su versioni in stato BOZZA. "
           f"Stato corrente: {versione['stato']}.",
    context={"versione_id": versione_id, "stato": versione["stato"]},
    function_name=function_name,
    log_to_db=True,
)
```

Da aggiungere come guard early-fail in tutte e tre le funzioni.

**[NUOVO v3 — defense-in-depth]**: valutare l'aggiunta di un trigger DB `trgfn_listini_righe_guard_stato` che rifiuta INSERT/UPDATE/DELETE su righe la cui versione non è in stato BOZZA. Il trigger è il secondo livello di protezione; il service rimane il primo. Senza il trigger, la protezione è bypassabile da connessioni psql dirette o da migration errate.

### F2 — Whitelist PATCH versione per stato (BLOCCANTE)

**File**: `apps/vendite/services/listini_service.py:fn_update_versione`

**Problema**: oggi PATCH versione accetta qualsiasi campo su qualsiasi stato.

**Fix — whitelist per stato**:

| Stato  | Campi PATCH ammessi                                                 |
| ------ | ------------------------------------------------------------------- |
| BOZZA  | `codice_versione`, `valido_dal`, `valido_al`, `attivo`, `meta`      |
| ATTIVA | solo `valido_al` (programmazione chiusura)                          |
| CHIUSA | nessun campo — rifiuta con 400                                      |

> **Nota post-refactor 2026-04-09**: il campo `priorita` e` stato **droppato fisicamente**
> (migration `20260409-04/-05`). Qualsiasi riferimento a `priorita` come campo PATCH ammesso
> e` obsoleto.

Implementazione: dopo `_get_versione_or_raise`, verificare `versione["stato"]` e validare i campi presenti nel payload contro la whitelist corrispondente.

### F3 — Test per i guard F1/F2

* Unit test service: tentare create/update/delete riga su versione ATTIVA e CHIUSA → atteso `E_VENDITE_VALIDATION`
* Unit test service: tentare PATCH versione ATTIVA con campo non in whitelist → atteso `E_VENDITE_VALIDATION`
* Smoke test bash (`smoke-test-listini.sh`): aggiungere casi negativi corrispondenti
* pgTAP (se il trigger defense-in-depth viene aggiunto): test INSERT diretto su riga con versione ATTIVA → atteso errore DB

---

## 8) Operazioni di convenienza — Sprint B (O1, O2, O3)

### O1 — Clone versione

**Backend**:

Nuovo metodo repository `clone_versione(listino_id, src_versione_id, payload)`:

```sql
-- In transazione atomica
INSERT INTO vendite.listini_versioni
    (listino_id, codice_versione, valido_dal, valido_al, stato)
    SELECT listino_id, %(target_codice)s, %(valido_dal)s, %(valido_al)s, 'BOZZA'
    FROM vendite.listini_versioni WHERE id = %(src_id)s
RETURNING id;

INSERT INTO vendite.listini_righe
    (listino_versione_id, articolo_id, uom_id,
     billing_account_id, utility_id, emittente_soggetto_ruolo_id,
     prezzo, attivo, meta)
    SELECT %(target_id)s, articolo_id, uom_id,
           billing_account_id, utility_id, emittente_soggetto_ruolo_id,
           prezzo, true, meta
    FROM vendite.listini_righe
    WHERE listino_versione_id = %(src_id)s AND attivo IS TRUE;
```

Nuovo service `fn_clone_versione(listino_id, src_versione_id, payload)`:
* valida `codice_versione` non vuoto e univoco per listino
* valida `valido_dal >= src.valido_dal` (regola D2: retroattivo ammesso solo fino all'inizio della sorgente)
* se `valido_dal < oggi`: dialog warning in UI ("stai creando una versione retroattiva, i documenti pregressi non verranno corretti")
* valida coerenza `valido_al > valido_dal` se entrambe presenti
* chiama repository in transazione
* restituisce dettaglio versione target

Nuova view `ApiListinoVersioneClona(DomainAPIView)`:
`POST /api/v1/vendite/listini/{id}/versioni/{src_id}/clona/`

**Frontend**:
* Pulsante "Clona" sulla riga versione, disponibile per qualsiasi stato sorgente
* Dialog `CloneVersioneDialog.vue`: campi `codice_versione`, `valido_dal`, `valido_al`. Suggerimenti pre-compilati (codice = src + suffisso, `valido_dal` = oggi+1)
* Se `valido_dal < oggi`: banner warning nel dialog
* Dopo conferma: POST → invalida cache versioni → mostra la nuova versione nell'elenco

### O2 — DELETE versione BOZZA

**Backend**:

Repository `delete_versione(listino_id, versione_id)`:
* DELETE CASCADE righe + versione in transazione

Service `fn_delete_versione(listino_id, versione_id)`:
* guard `stato == 'BOZZA'` — rifiuta con 400 se ATTIVA o CHIUSA (con messaggio esplicito)
* DELETE in transazione
* restituisce `{"deleted": true, "id": versione_id}`

View `ApiListinoVersioneDetail`: aggiungere metodo `delete()`.

**Frontend**:
* Pulsante "Elimina" sulla riga versione, **visibile solo se `stato == BOZZA`**
* Conferma modale: "Eliminare definitivamente la versione X? Tutte le N righe verranno eliminate."

### O3 — DELETE listino mai usato

**Backend**:

Service `fn_delete_listino(listino_id)`:
* guard `versioni_count == 0 AND associazioni_count == 0`
* se fallisce: 400 con messaggio "Per disattivare un listino con figli usa PATCH `attivo=false`"
* DELETE in transazione

View `ApiListinoDetail`: aggiungere metodo `delete()`.

**Frontend**:
* Pulsante "Elimina" sulla riga listino, **visibile solo se entrambi i conteggi sono 0** (già disponibili nella SELECT lista)
* Conferma modale chiara

---

## [NUOVO v3] 9) Integrazioni critiche — gap non presenti nei documenti precedenti

> Questa sezione raccoglie tutti i gap identificati nell'analisi esterna (v3).
> Ogni punto ha un ID dalla master table del §2 e indica il perimetro di intervento.

### N1 — `daterange` nativo PostgreSQL

Vedi §5.5. Roadmap v2, aprire ticket tecnico.

---

### N2 — Job monitor scadenza versioni attive (Alta)

**Gap**: nessun meccanismo preventivo segnala che una versione ATTIVA sta per scadere senza successore. Il sistema scopre il problema solo quando il resolver restituisce `E_PREZZO_LISTINO_NON_TROVATO` durante l'emissione di un documento.

**Impatto operativo**: blocco silenzioso in produzione. Un listino che scade il 31 marzo blocca tutti i documenti del 1 aprile.

**Proposta**:

Job pgAgent (o Django management command schedulato) `job_monitor_versioni_in_scadenza`:
* Query: versioni ATTIVE con `valido_al IS NOT NULL AND valido_al <= oggi + N giorni`
  per le quali non esiste già una versione ATTIVA o BOZZA con `valido_dal > valido_al`
* N configurabile (suggerito: 15 giorni)
* Output: notifica operatore (inizialmente: log su tabella `dbops.alert_log` o equivalente; in futuro: email/notifica UI)

Alternativa più leggera senza job: endpoint API `GET /api/v1/vendite/listini/alert-scadenze/?giorni=15`
che restituisce l'elenco dei listini a rischio. Il frontend mostra un badge di avviso nel menu vendite o nella dashboard.

**Raccomandazione**: implementare prima la versione API (costo basso, impatto alto), poi il job schedulato se il volume lo richiede.

**[NUOVO v3 — nota daterange]**: la query di N2 filtra su `valido_al IS NOT NULL AND valido_al <= oggi + N giorni`. Quando la migrazione a `daterange` nativo sara` completata (N1), il filtro diventera` `upper(validita) IS NOT NULL AND upper(validita) <= oggi + N giorni`. Per facilitare la transizione, isolare il filtro temporale in un metodo dedicato del repository (`_filter_versioni_in_scadenza`) cosi` il refactor daterange tocca un solo punto.

---

### N3 — Flusso prezzo documento → commessa: gap definizione preventivo (Alta)

**Gap**: il documento descrive la gerarchia "prezzo override manuale su documento prevale su listino" e il flag `prezzo_bloccato = TRUE`, ma non definisce chiaramente il flusso completo nei casi:

* Chi imposta `prezzo_bloccato`? Il service di creazione commessa, o un'azione esplicita dell'operatore?
* Quando un preventivo viene modificato dopo il push in commessa, la riga `commesse_attivita` viene marcata `prezzo_da_riallineare = TRUE` (già in schema). Ma chi scatena il riallineamento? Come si propaga verso `attivita_fatturabili`?
* Se il preventivo viene convertito in ordine senza riallineare, cosa succede? Il prezzo vecchio rimane, il flag rimane visibile?

**Proposta**: prima di chiudere Sprint A, documentare esplicitamente in `gestione-commesse-v2.md` (o in una sezione dedicata di questo documento) il lifecycle completo:

```
Creazione preventivo
  → push in commessa (resolver o prezzo manuale?)
  → modifica preventivo post-push (flag prezzo_da_riallineare)
  → riallineamento su conferma esplicita (chi, quando, come)
  → conversione in ordine (cosa succede al flag se non riallineato?)
  → emissione fattura (lettura da attivita_fatturabili, non da listino)
```

Senza questo chiarimento, il comportamento in produzione è imprevedibile e i test UI (già aperti) non possono coprire i casi limite.

---

### N4 — Match_level 3: documentare come non-utility only (Bassa)

**Gap**: il match_level 3 (BA + emittente senza utility) è tecnicamente corretto ma genera confusione in chi configura il sistema in un contesto commercio puro, dove l'emittente coincide quasi sempre con l'azienda stessa e il livello 3 è di fatto equivalente al livello 4 (BA da solo).

**Proposta**: aggiungere una nota esplicita nella documentazione del resolver e nella guida funzionale:

> "Il match_level 3 (BA + emittente senza utility) è rilevante esclusivamente in contesti
> multi-emittente (tipicamente utility) dove l'emittente fiscale è un soggetto distinto
> dall'azienda erogante. In contesti commercio con emittente unico, questo livello non
> produce mai un match differente dal livello 4 (BA da solo) e può essere ignorato in fase
> di configurazione."

Nessuna modifica al codice.

---

### N5 — Rettifica su prezzo non ancora fatturato: gap parziale rispetto a DB-L4 (Media)

**Gap**: il documento DB-L4 (rettifiche) è interamente orientato al caso "prezzo già in fattura emessa → NDC/NDD". Ma esiste un caso intermedio più semplice e frequente: prezzo snapshot in `commesses_attivita` o `attivita_fatturabili` che è errato, ma la riga **non è ancora stata fatturata**.

In questo caso non serve emettere un NDC/NDD — basta aggiornare lo snapshot con il prezzo corretto. Ma oggi non esiste un'operazione dedicata per farlo: il flag `prezzo_da_riallineare` è in schema ma il flusso di riallineamento non è implementato.

**Proposta**: definire come parte di Sprint A (o prima di DB-L4) un'operazione limitata:

`POST /api/v1/vendite/commesse/{id}/attivita/{att_id}/riallinea-prezzo/`

Guard:
* `attivita_fatturabili.fattura_riga_id IS NULL` (non ancora fatturata)
* `prezzo_bloccato == FALSE` (non override manuale)

Comportamento:
* Esegue `fn_resolve_prezzo_listino` alla data originale dell'attività
* Aggiorna `prezzo_snapshot` su `commesse_attivita` e `attivita_fatturabili`
* Azzera `prezzo_da_riallineare`
* Audit in `meta` con prezzo precedente, prezzo nuovo, operatore, timestamp

Questo non è il motore rettifiche completo (DB-L4), ma risolve il 90% dei casi operativi quotidiani con complessità minima.

#### Caso critico: versione listino cambiata dopo lo snapshot originale

Se tra il momento dello snapshot originale e il riallineamento la versione del listino e` cambiata (auto-close + nuova versione attivata), il resolver alla data originale dell'attivita` potrebbe restituire un prezzo diverso da quello atteso — oppure fallire con `E_PREZZO_LISTINO_NON_TROVATO` se la vecchia versione e` stata chiusa con `valido_al` anteriore alla data dell'attivita`.

**Guard obbligatorio**: prima di eseguire il riallineamento, confrontare `listino_versione_id` salvato nello snapshot con la versione che il resolver risolve ora. Se sono diversi, restituire un warning esplicito nel response (`versione_cambiata: true`, `versione_originale_id`, `versione_attuale_id`) e richiedere conferma esplicita dell'operatore (`conferma_versione_diversa: true` nel payload). Senza conferma, rifiutare con `E_VENDITE_RIALLINEAMENTO_VERSIONE_CAMBIATA`.

---

### N6 — Rettifica controllata su riga ATTIVA non ancora propagata (Alta)

> **[NUOVO v3]** — Sprint B

**Contesto**: il principio di immutabilità delle righe in versione ATTIVA protegge la coerenza tra listino e snapshot già propagati in commessa. Tuttavia obbligare sempre la creazione di una nuova versione — anche per un semplice errore di battitura su un listino con centinaia di righe — è operativamente pesante e genera rumore nella storia delle versioni.

**Proposta**: ammettere la modifica di una riga in versione ATTIVA **solo se il prezzo non è ancora stato propagato** in nessuna commessa o attività fatturabile.

#### Guard (triplo livello obbligatorio)

**Livello 1 — Lock pessimistico nel service Python**:

Prima di qualsiasi check, bloccare la riga con `FOR UPDATE` per prevenire race condition (una commessa creata in concorrenza che referenzia la stessa riga):

```sql
SELECT id FROM vendite.listini_righe
WHERE id = %(riga_id)s
FOR UPDATE;
```

**Livello 2 — Check non-propagazione nella stessa transazione**:

```sql
SELECT COUNT(*) FROM vendite.commesse_attivita
WHERE listino_riga_id = %(riga_id)s
UNION ALL
SELECT COUNT(*) FROM vendite.attivita_fatturabili
WHERE listino_riga_id = %(riga_id)s;
```

Se entrambi i conteggi sono zero → modifica ammessa.
Se almeno uno è maggiore di zero → modifica bloccata con errore `E_VENDITE_RIGA_GIA_PROPAGATA`.

Il `FOR UPDATE` + check nella stessa transazione garantisce che nessuna commessa possa inserire un riferimento alla riga tra il check e l'UPDATE.

**Livello 3 — Trigger DB defense-in-depth** (`trgfn_listini_righe_guard_stato`):

Estendere il trigger gia` previsto da F1 con la stessa logica di non-propagazione. Il trigger e` il guard definitivo: protegge anche da UPDATE via `psql` diretto, migration errate, o future integrazioni che bypassano il service Python.

**[NUOVO v3 — nota concentrica]**: il check di non-propagazione deve essere progettato per l'espansione concentrica del modello. Oggi le tabelle che referenziano `listino_riga_id` sono `commesse_attivita` e `attivita_fatturabili`. Nei cerchi successivi potrebbero arrivare altre tabelle (es. `preventivi_righe`, `ordini_righe`, integrazioni esterne). Il trigger DB deve essere strutturato in modo che l'aggiunta di una nuova tabella al check sia una modifica localizzata (aggiungere un `UNION ALL`), non un redesign. Documentare nel commento del trigger l'elenco esplicito delle tabelle controllate, cosi` l'aggiunta futura e` guidata.

#### Audit obbligatorio

Ogni modifica ammessa deve tracciare in `listini_righe.meta`:

```json
{
  "rettifiche_controllate": [
    {
      "data": "2026-04-15T10:22:00Z",
      "operatore": "mario.rossi",
      "prezzo_precedente": "12.5000000000",
      "prezzo_nuovo": "12.2500000000",
      "motivo": "errore di battitura al momento del caricamento"
    }
  ]
}
```

Il campo `motivo` è obbligatorio: il service rifiuta la richiesta se assente o vuoto.

#### API

`PATCH /api/v1/vendite/listini/{id}/versioni/{ver_id}/righe/{riga_id}/rettifica-controllata/`

Payload: `{ "prezzo": 12.25, "motivo": "..." }`

Endpoint separato rispetto al PATCH standard della riga (che resta bloccato in ATTIVA da F1). La distinzione è intenzionale: l'operazione eccezionale deve essere esplicita, non mascherata dal PATCH ordinario.

#### Cosa NON copre

* Righe già usate in `commesse_attivita` o `attivita_fatturabili` → bloccate, usare clone versione
* Correzione retroattiva di fatture già emesse → DB-L4

---

### N7 — Variazione prezzo eccezionale su commessa (Alta)

> **[NUOVO v3]** — Sprint B

**Contesto**: capitano situazioni eccezionali in cui il prezzo di un'attività già in commessa deve essere modificato dopo la creazione — un accordo commerciale post-ordine, una revisione concordata con il cliente, un errore di configurazione del listino scoperto tardi.

**Perimetro ammesso**: commesse in stato `LIBERO` o `CONFERMATO`. Righe già fatturate → bloccate per quelle specifiche righe; le altre righe della stessa commessa possono comunque essere modificate.

#### Guard

* `commessa.stato IN ('LIBERO', 'CONFERMATO')` — rifiuta altrimenti
* Per ogni attività coinvolta: `attivita_fatturabili.fattura_riga_id IS NULL` — rifiuta le righe già fatturate con errore esplicito, procede sulle altre
* `prezzo_bloccato` viene impostato a `TRUE` dopo la modifica — il prezzo non sarà più ricalcolato dal resolver

#### Comportamento

1. L'operatore specifica il nuovo prezzo e un motivo obbligatorio
2. Il service aggiorna `commesse_attivita.prezzo_snapshot` e `attivita_fatturabili.prezzo_snapshot`
3. Imposta `prezzo_bloccato = TRUE` su entrambe le righe
4. Registra l'audit in `commesse_attivita.meta`:

```json
{
  "variazioni_eccezionali": [
    {
      "data": "2026-04-15T14:10:00Z",
      "operatore": "mario.rossi",
      "prezzo_precedente": "45.0000000000",
      "prezzo_nuovo": "42.0000000000",
      "motivo": "sconto eccezionale concordato con cliente per ordine annuale",
      "stato_commessa": "CONFERMATO",
      "listino_versione_id_riferimento": "uuid-versione"
    }
  ]
}
```

5. Il riferimento `listino_versione_id` originale viene conservato per audit comparativo anche dopo la variazione.

#### Differenza rispetto a N5 (riallineamento automatico)

| Aspetto                | N5 — Riallineamento                   | N7 — Variazione eccezionale     |
| ---------------------- | ------------------------------------- | ------------------------------- |
| Chi imposta il prezzo  | Il resolver (ricalcola dal listino)   | L'operatore (prezzo manuale)    |
| `prezzo_bloccato` dopo | Rimane FALSE                          | Diventa TRUE                    |
| Motivo obbligatorio    | No                                    | Sì                              |
| Caso d'uso             | Correzione tecnica (listino cambiato) | Accordo commerciale eccezionale |

#### API

`POST /api/v1/vendite/commesse/{id}/attivita/{att_id}/variazione-prezzo-eccezionale/`

Payload: `{ "prezzo": 42.00, "motivo": "..." }`

Endpoint dedicato e separato dal PATCH standard dell'attività, per rendere esplicita la natura eccezionale dell'operazione.

#### Reversibilita`: sblocco `prezzo_bloccato`

Nel design attuale `prezzo_bloccato = TRUE` e` irreversibile: se l'operatore sbaglia la variazione eccezionale, non c'e` modo di tornare al prezzo del resolver. Serve un'operazione complementare:

`POST /api/v1/vendite/commesse/{id}/attivita/{att_id}/sblocca-prezzo/`

Payload: `{ "motivo": "..." }`

Comportamento:
1. Guard: `prezzo_bloccato == TRUE` — rifiuta se gia` sbloccato
2. Guard: `attivita_fatturabili.fattura_riga_id IS NULL` — rifiuta se gia` fatturata
3. Esegue `fn_resolve_prezzo_listino` alla data originale dell'attivita`
4. Aggiorna `prezzo_snapshot` con il prezzo ricalcolato
5. Imposta `prezzo_bloccato = FALSE`
6. Audit in `meta`:

```json
{
  "sblocchi_prezzo": [
    {
      "data": "2026-04-16T09:00:00Z",
      "operatore": "mario.rossi",
      "prezzo_bloccato_precedente": "42.0000000000",
      "prezzo_ricalcolato": "45.0000000000",
      "motivo": "variazione eccezionale errata, ripristino prezzo da listino"
    }
  ]
}
```

L'operazione di sblocco e` il complemento naturale della variazione eccezionale: senza di essa, un errore sulla variazione richiede interventi manuali sul DB.

#### Nota autorizzativa

In futuro — quando il sistema di permessi sara` maturo — sia la variazione eccezionale sia lo sblocco dovrebbero richiedere un permesso specifico (`vendite.variazione_prezzo_eccezionale`) distinto dal permesso ordinario di modifica commessa. Per v1 la traccia audit nel `meta` e` il meccanismo di controllo sufficiente.

---

### N8 — Listino post-it e variazioni percentuali in BOZZA (Alta)

> **[NUOVO v3]** — Sprint B

Questa sezione copre due esigenze operative distinte ma collegate:
1. Correggere il prezzo di un singolo articolo senza toccare il listino base (**listino post-it**)
2. Applicare aumenti o riduzioni percentuali a un intero listino clonato in BOZZA

---

#### ⚠️ Il listino post-it — quando funziona e quando no

> Questa è la parte più importante da capire prima di usare il sistema.

L'idea intuitiva è: creo un secondo listino piccolo con solo l'articolo corretto, e il sistema usa quello. Come un post-it attaccato sopra il cartellone grande.

**Funziona** quando il prezzo corretto vale per un **contesto specifico** — un cliente preciso, una utility precisa. In quel caso metti la riga nel listino post-it con il BA valorizzato (match_level 4) o BA+utility (match_level 2). Il resolver trova quella riga prima della riga generica del listino base, perché è più specifica. Il listino base non viene toccato.

**Non funziona** quando il prezzo corretto deve valere per **tutti i clienti** (riga generica, match_level 7). In quel caso entrambi i listini avrebbero un'associazione generica (NULL, NULL, NULL) per lo stesso periodo, e il constraint `ex_listini_associazioni_no_overlap` lo impedisce a livello DB: non possono esistere due associazioni con lo stesso scope nello stesso periodo, indipendentemente dal listino.

**La tabella della verità:**

| Situazione                                                               | Soluzione corretta                                   |
| ------------------------------------------------------------------------ | ---------------------------------------------------- |
| Prezzo sbagliato per un cliente specifico, articolo non ancora fatturato | N6 — rettifica controllata sulla riga                |
| Prezzo sbagliato per un cliente specifico, articolo già fatturato        | Listino post-it con BA valorizzato sulla riga        |
| Prezzo sbagliato per tutti i clienti, articolo non ancora fatturato      | N6 — rettifica controllata sulla riga                |
| Prezzo sbagliato per tutti i clienti, articolo già fatturato             | Clone listino + correggi la riga + attiva (O1)       |
| Aumento prezzi annuale su tutto il listino                               | Clone + variazione % massa (questa sezione) + attiva |

Il listino post-it è uno strumento potente ma ha un perimetro preciso: funziona solo per correzioni su contesti specifici (cliente, utility, emittente). Per correzioni generiche, il clone è la via maestra.

---

#### Operazione massa: variazione percentuale su versione BOZZA

Caso d'uso tipico: il fornitore comunica un aumento del 3% su tutta la gamma. Hai clonato il listino attivo in una nuova versione BOZZA. Invece di modificare 500 righe una per una, applichi la variazione in un colpo solo.

**API**

`POST /api/v1/vendite/listini/{id}/versioni/{ver_id}/applica-variazione/`

Guard obbligatorio: `stato == 'BOZZA'` — rifiuta su ATTIVA o CHIUSA.

Payload:

```json
{
  "variazione_percentuale": 3.0,
  "arrotondamento_decimali": 4,
  "filtro_articoli": null,
  "dry_run": false
}
```

Campi:

| Campo                     | Tipo              | Note                                                                                      |
| ------------------------- | ----------------- | ----------------------------------------------------------------------------------------- |
| `variazione_percentuale`  | numeric           | Positivo = aumento, negativo = riduzione. Es. `3.0` = +3%, `-5.0` = -5%. **Range ammesso: -99.0 a +1000.0** (guard esplicito — rifiuta con 400 fuori range) |
| `arrotondamento_decimali` | integer           | Decimali da mantenere dopo il calcolo. Default 4. Range 0-10                              |
| `filtro_articoli`         | array uuid o null | Se valorizzato, applica solo agli articoli nell'elenco. Se null, applica a tutte le righe |
| `dry_run`                 | boolean           | Se `true`, calcola e restituisce la preview senza applicare modifiche. Default `false`     |

**Guard su percentuale**: il service rifiuta con 400 (`E_VENDITE_VALIDATION`) se `variazione_percentuale` produce prezzi negativi (`<= -100.0`) o e` fuori dal range ragionevole (`> 1000.0`). Questo previene errori umani (es. digitare `300` intendendo `3.0`).

**Modalita` dry_run**: quando `dry_run = true`, il service esegue la query di calcolo senza UPDATE e restituisce un array di preview:

```json
{
  "dry_run": true,
  "righe_coinvolte": 500,
  "preview": [
    {"riga_id": "uuid", "articolo_codice": "ART001", "prezzo_attuale": "12.5000", "prezzo_calcolato": "12.8750"},
    ...
  ],
  "variazione_percentuale": 3.0,
  "arrotondamento_decimali": 4
}
```

Il frontend usa il dry_run per mostrare la preview nel dialog prima della conferma. Il calcolo avviene lato DB (`ROUND(prezzo * (1 + pct / 100.0), decimali)`) per avere valori esatti coerenti con `numeric(22,10)`.

Comportamento (quando `dry_run = false`):

```sql
UPDATE vendite.listini_righe
SET prezzo = ROUND(prezzo * (1 + %(variazione_pct)s / 100.0), %(decimali)s),
    data_update = now(),
    user_update = %(operatore)s
WHERE listino_versione_id = %(versione_id)s
  AND attivo IS TRUE
  AND (%(filtro_articoli)s IS NULL OR articolo_id = ANY(%(filtro_articoli)s));
```

Response: `{ "righe_aggiornate": 500, "variazione_percentuale": 3.0, "arrotondamento_decimali": 4 }`

#### Operazione singola riga in BOZZA

Nessuna novità: è il PATCH ordinario già esistente. L'operatore apre la riga nella `VersioneDrawer`, modifica il prezzo manualmente, salva. Funziona già oggi (guard BOZZA garantito da F1 post-fix).

Il flusso tipico è: applica variazione massa → rivedi le righe che escono fuori dalle aspettative → correggi manualmente quelle singole → attiva.

#### Nota sull'arrotondamento

`12.50 * 1.03 = 12.875` — il risultato ha più decimali del prezzo originale. Il parametro `arrotondamento_decimali` controlla quanti decimali mantenere:

* Dominio utility: usare 10 (massima precisione, coerente con `numeric(22,10)`)
* Dominio commercio: usare tipicamente 2 o 4 (prezzi leggibili in fattura)

E` l'operatore che decide al momento dell'applicazione. Il sistema non impone un default di dominio: la configurazione esplicita evita arrotondamenti silenziosi inattesi.

**Nota arrotondamento composto**: ogni applicazione di variazione e` un'operazione atomica con arrotondamento immediato. Se si applicano due variazioni successive (+3% e poi +2%), il risultato finale dipende dall'arrotondamento intermedio e potrebbe differire da un'applicazione singola di +5.06%. Questo e` il comportamento atteso e corretto: ogni variazione e` un atto operativo distinto, non componibile matematicamente. Documentare questo comportamento nella guida operativa (N8b) per evitare aspettative errate.

#### Frontend

Pulsante "Applica variazione %" nel toolbar della `VersioneDrawer`, visibile solo se `stato == 'BOZZA'`.

Dialog `ApplicaVariazioneDialog.vue`:
* Campo `variazione_percentuale` con segno (InputNumber, può essere negativo)
* Campo `arrotondamento_decimali` (InputNumber, default 4, range 0-10)
* Lookup articoli opzionale per limitare il perimetro (autocomplete multi-selezione)
* Preview: "Verranno aggiornate N righe. Esempio: articolo X passa da 12,50 a 12,88"
* Conferma → POST → refresh righe nella tabella

#### Aggiornamenti alla master table e al tracking

Da aggiungere in Sprint B:

| ID      | Tipo           | Descrizione                                                               | Priorità | Sprint |
| ------- | -------------- | ------------------------------------------------------------------------- | -------- | ------ |
| **N8a** | **[NUOVO v3]** | **Variazione % massa su versione BOZZA**                                  | Alta     | B      |
| **N8b** | **[NUOVO v3]** | **Documentazione operativa "listino post-it": quando usarlo e quando no** | Alta     | DOC    |

Nuovi endpoint:

| #      | Metodo   | Path                                                                     | Note                            |
| ------ | -------- | ------------------------------------------------------------------------ | ------------------------------- |
| **27** | **POST** | **`/api/v1/vendite/listini/{id}/versioni/{ver_id}/applica-variazione/`** | **[NUOVO v3 — N8a]** Solo BOZZA |

Nuovo componente frontend: `ApplicaVariazioneDialog.vue`

Test da aggiungere:

| Test                                                                    | Tipo               | Sprint |
| ----------------------------------------------------------------------- | ------------------ | ------ |
| Variazione +3% su versione BOZZA: verifica calcolo e arrotondamento     | Unit service + API | B      |
| Variazione su versione ATTIVA → atteso 400                              | Unit service + API | B      |
| Variazione con filtro articoli: verifica solo righe filtrate aggiornate | Unit service       | B      |
| Variazione -100% → atteso 400 (prezzo non può diventare negativo)       | Unit service       | B      |
| Variazione +1500% → atteso 400 (fuori range ammesso)                   | Unit service       | B      |
| Variazione dry_run: verifica preview senza modifica dati               | Unit service + API | B      |

---

## 10) Resolver prezzo (deterministico)

### 10.1 Ordine di precedenza (7 livelli)

| match_level | Dimensioni matchate      | Contesto tipico                                     |
| ----------- | ------------------------ | --------------------------------------------------- |
| 1           | BA + utility + emittente | Utility multi-emittente                             |
| 2           | BA + utility             | Utility standard                                    |
| 3           | BA + emittente           | Multi-emittente non-utility **[NUOVO v3: vedi N4]** |
| 4           | BA                       | Cliente specifico, commercio                        |
| 5           | utility + emittente      | Servizio + emittente, no cliente                    |
| 6           | utility                  | Servizio specifico                                  |
| 7           | articolo + UoM           | Fallback generico                                   |

### 10.2 Flusso a 4 fasi

1. **Associazioni**: filtra listini candidati per contesto + finestra temporale dell'associazione
2. **Versioni**: per ogni candidato seleziona versioni `ATTIVA + attivo + data ∈ [valido_dal, valido_al]`
3. **Righe**: cerca match per `articolo_id + uom_id`, assegna `match_level`
4. **Tie-break**: con l'invariante univocità stretta (refactor 2026-04-09), il caso di parità è strutturalmente impossibile. Il tie-break residuo è `match_level, valido_dal DESC, valido_al ASC, id` per determinismo assoluto.

### 10.3 Cosa il resolver NON vede

* Versioni BOZZA — sandbox invisibile
* Versioni CHIUSE — storico invisibile
* Versioni con `attivo = false`
* Righe con `attivo = false`
* Date fuori dalla finestra `[valido_dal, valido_al]` di versione e associazione

### 10.4 Output

`(listino_id, listino_versione_id, listino_riga_id, listino_associazione_id, prezzo, match_level)`

### 10.5 Comportamento errori

| Codice                         | Significato                                                   |
| ------------------------------ | ------------------------------------------------------------- |
| `E_PREZZO_LISTINO_NON_TROVATO` | Nessun match per contesto e data                              |
| `E_PREZZO_LISTINO_AMBIGUO`     | Match equivalenti (impossibile per costruzione, safety check) |
| `E_PARAMETRO_INVALIDO`         | Input mancante o non valido                                   |

Nessun fallback silenzioso.

---

## 11) Integrazione con commessa v2

### 11.1 Snapshot su `commesse_attivita`

Campi salvati al momento della risoluzione:

| Campo                 | Contenuto                                               |
| --------------------- | ------------------------------------------------------- |
| `listino_versione_id` | quale versione era attiva                               |
| `prezzo_snapshot`     | prezzo congelato                                        |
| `prezzo_bloccato`     | se TRUE, non ricalcolare dal resolver                   |
| `pricing_mode`        | `FIXED` in v1; `FORMULA`/`SCAGLIONI` predisposti per v2 |

### 11.2 Gerarchia prezzo

1. Override manuale su documento → `prezzo_snapshot = prezzo_documento`, `prezzo_bloccato = TRUE`, `listino_versione_id` salvato per audit comparativo
2. Nessun override → prezzo dal resolver

### 11.3 Propagazione `prezzo_bloccato` verso `attivita_fatturabili`

Il flag viene propagato da `commesse_attivita` a `attivita_fatturabili` tramite la funzione di emissione. Lo step 1 della pipeline fatturazione legge il flag direttamente su `attivita_fatturabili`, evitando join sul dominio commessa durante la fase fiscale.

### 11.4 Caso preventivo LIBERO modificato dopo push

* La riga `commesse_attivita` viene marcata `prezzo_da_riallineare = TRUE`
* Il prezzo non viene aggiornato silenziosamente
* Riallineamento su conferma esplicita (vedi **[NUOVO v3 — N5]**)
* Se il documento non è più LIBERO, il prezzo documento non può alterare la commessa già consolidata

---

## 12) Backend — Listini (vendite)

### 12.1 Repository: `apps/vendite/db/listini_repository.py`

| #      | Metodo                            | Note                                                                      |
| ------ | --------------------------------- | ------------------------------------------------------------------------- |
| 1      | `list_listini()`                  | Filtri: `dominio`, `attivo`, `search`. Conta versioni e associazioni      |
| 2      | `get_listino()`                   | Dettaglio + count versioni + count associazioni                           |
| 3      | `create_listino()`                | INSERT                                                                    |
| 4      | `update_listino()`                | UPDATE                                                                    |
| 5      | `list_versioni()`                 | ORDER BY `valido_dal DESC`, con count righe                               |
| 6      | `get_versione()`                  | Singola versione                                                          |
| 7      | `create_versione()`               | INSERT, stato=BOZZA. No-overlap gestito da GIST                           |
| 8      | `update_versione()`               | UPDATE                                                                    |
| 9      | `cambia_stato_versione()`         | Solo BOZZA→ATTIVA, ATTIVA→CHIUSA                                          |
| 10     | `list_righe()`                    | JOIN articoli + UoM per display fields                                    |
| 11     | `create_riga()`                   | INSERT                                                                    |
| 12     | `update_riga()`                   | UPDATE                                                                    |
| 13     | `delete_riga()`                   | DELETE                                                                    |
| 14     | `list_associazioni()`             | JOIN BA, utility, emittente per display fields                            |
| 15     | `create_associazione()`           | INSERT                                                                    |
| 16     | `update_associazione()`           | UPDATE                                                                    |
| 17     | `delete_associazione()`           | DELETE                                                                    |
| 18     | `get_articolo_uom_validation()`   | Validazione articolo + UoM in un round-trip                               |
| 19     | `test_resolver()`                 | Wrapper `fn_resolve_prezzo_listino`                                       |
| **20** | **`clone_versione()`**            | **[NUOVO v3 — O1]** Clone versione in BOZZA                               |
| **21** | **`delete_versione()`**           | **[NUOVO v3 — O2]** DELETE versione BOZZA + righe in cascade              |
| **22** | **`delete_listino()`**            | **[NUOVO v3 — O3]** DELETE listino senza figli                            |
| **23** | **`listini_in_scadenza(giorni)`** | **[NUOVO v3 — N2]** Query versioni ATTIVE senza successore entro N giorni |

### 12.2 Service: `apps/vendite/services/listini_service.py`

| #      | Metodo                          | Note                                                          |
| ------ | ------------------------------- | ------------------------------------------------------------- |
| 1-9    | (esistenti)                     | Vedi documento v2 §10.2                                       |
| **10** | **`fn_clone_versione()`**       | **[NUOVO v3 — O1]** Validazione payload + chiamata repository |
| **11** | **`fn_delete_versione()`**      | **[NUOVO v3 — O2]** Guard stato BOZZA + DELETE                |
| **12** | **`fn_delete_listino()`**       | **[NUOVO v3 — O3]** Guard zero figli + DELETE                 |
| **13** | **`fn_alert_scadenze(giorni)`** | **[NUOVO v3 — N2]** Lista listini a rischio scadenza          |

**Fix obbligatori su metodi esistenti**:
* `fn_create_riga`, `fn_update_riga`, `fn_delete_riga` → aggiungere guard F1
* `fn_update_versione` → aggiungere whitelist F2

### 12.3 API: `apps/vendite/api/views_listini.py`

| #      | Metodo      | Path                                                                                        | Note                |
| ------ | ----------- | ------------------------------------------------------------------------------------------- | ------------------- |
| 1-18   | (esistenti) | Vedi documento v2 §10.3                                                                     |                     |
| **19** | **POST**    | **`/api/v1/vendite/listini/{id}/versioni/{src_id}/clona/`**                                 | **[NUOVO v3 — O1]** |
| **20** | **DELETE**  | **`/api/v1/vendite/listini/{id}/versioni/{ver_id}/`**                                       | **[NUOVO v3 — O2]** |
| **21** | **DELETE**  | **`/api/v1/vendite/listini/{id}/`**                                                         | **[NUOVO v3 — O3]** |
| **22** | **GET**     | **`/api/v1/vendite/listini/alert-scadenze/?giorni=15`**                                     | **[NUOVO v3 — N2]** |
| **23** | **PATCH**   | **`/api/v1/vendite/listini/{id}/versioni/{ver_id}/righe/{riga_id}/rettifica-controllata/`** | **[NUOVO v3 — N6]** |
| **24** | **POST**    | **`/api/v1/vendite/commesse/{id}/attivita/{att_id}/riallinea-prezzo/`**                     | **[NUOVO v3 — N5]** |
| **25** | **POST**    | **`/api/v1/vendite/commesse/{id}/attivita/{att_id}/variazione-prezzo-eccezionale/`**        | **[NUOVO v3 — N7]** |
| **26** | **POST**    | **`/api/v1/vendite/commesse/{id}/attivita/{att_id}/sblocca-prezzo/`**                       | **[NUOVO v3 — N7 sblocco]** |

### 12.4 Errori applicativi

Codici esistenti in `error_policies.py`:
* `E_VENDITE_VALIDATION`
* `E_VENDITE_LISTINO_NOT_FOUND`
* `E_VENDITE_VERSIONE_NOT_FOUND`
* `E_VENDITE_RIGA_NOT_FOUND`
* `E_VENDITE_ASSOCIAZIONE_NOT_FOUND`
* `E_PREZZO_LISTINO_NON_TROVATO` (dal DB)
* `E_PREZZO_LISTINO_AMBIGUO` (dal DB)

**[NUOVO v3]** Nuovi codici da registrare:
* `E_VENDITE_VERSIONE_NOT_BOZZA` — tentativo di modifica righe su versione non BOZZA (F1)
* `E_VENDITE_VERSIONE_FIELD_READONLY` — tentativo PATCH campo non consentito per stato (F2)
* `E_VENDITE_LISTINO_HAS_CHILDREN` — tentativo DELETE listino con figli (O3)
* `E_VENDITE_RIGA_GIA_PROPAGATA` — tentativo rettifica controllata su riga già usata in commessa o fatturabile (N6)
* `E_VENDITE_VARIAZIONE_PREZZO_NON_AMMESSA` — tentativo variazione eccezionale su commessa in stato non consentito o su riga già fatturata (N7)
* `E_VENDITE_SBLOCCO_PREZZO_NON_AMMESSO` — tentativo sblocco su riga non bloccata o già fatturata (N7 sblocco)
* `E_VENDITE_RIALLINEAMENTO_VERSIONE_CAMBIATA` — riallineamento N5 su versione diversa da snapshot senza conferma esplicita

---

## 13) Frontend — Listini

### 13.1 Struttura file (attuale)

```
frontend/src/vendite/
├── api/listini.js
├── stores/listini.js
├── components/
│   ├── ListiniSearchTable.vue
│   ├── ListinoDrawer.vue
│   ├── ListinoVersioniTab.vue
│   ├── ListinoAssociazioniTab.vue
│   ├── VersioneDrawer.vue
│   └── TestResolverDialog.vue
└── views/ListiniView.vue
```

### 13.2 Componenti da aggiungere (Sprint B)

**[NUOVO v3]**:

| Componente                    | Scopo                                                |
| ----------------------------- | ---------------------------------------------------- |
| `CloneVersioneDialog.vue`     | Dialog clone versione (O1) con warning retroattivo   |
| `AlertScadenzeWidget.vue`     | Badge/widget avviso listini in scadenza (N2)         |
| `ApplicaVariazioneDialog.vue` | Dialog variazione % massa su BOZZA (N8a) con preview |

### 13.3 Modifiche a componenti esistenti

**[NUOVO v3]**:

* `ListinoVersioniTab.vue`:
  * Aggiungere pulsante "Clona" su ogni riga (O1)
  * Aggiungere pulsante "Elimina" visibile solo se `stato == BOZZA` (O2)
  * Aggiungere avviso UX su PATCH `valido_al` di versione ATTIVA: dialog "Stai programmando la chiusura al [data]. Dal [data+1] i contesti gestiti da questa versione non avranno prezzo attivo, a meno che non esista già una versione successiva. Confermi?"

* `ListinoDrawer.vue`:
  * Aggiungere pulsante "Elimina" visibile solo se `versioni_count == 0 AND associazioni_count == 0` (O3)
  * In stato ATTIVA: disabilitare campi non in whitelist (solo `valido_al` editabile). In CHIUSA: tutto readonly.

* `VersioneDrawer.vue`:
  * Verificare coerenza con i fix F1/F2: la UX che nasconde i pulsanti in BOZZA deve rimanere allineata con il guard backend post-fix.

### 13.4 Regole invariate

1. Riuso di `useSearchTable`, `useDrawerState`, `useTabFreshness`, `useApiHandler`, `useInjectReadonly`, `useLookup`
2. `ArticoloLookup` (BB cross-dominio) riusato in `VersioneDrawer` e `TestResolverDialog`
3. Righe prezzo CRUD solo su versioni BOZZA (guard `isBozza` — ora allineato al guard backend post-fix)
4. Tutti i testi via `$t()`, nessun hardcoded
5. PATCH backend usa `request.data`

---

## 14) Rettifiche prezzi — RIMANDO a DB-L4

Il motore rettifiche è trattato nel documento dedicato [sviluppo-rettifiche.md](sviluppo-rettifiche.md).

Contratto con il dominio listini:
1. Nessuna riscrittura distruttiva di fatture emesse
2. Rettifica sempre tramite delta tracciato
3. Motore unico per canale MANUALE e AUTOMATICA
4. I campi tecnici `prezzo_bloccato` e `prezzo_da_riallineare` sono già in schema (DB-L3)

**[NUOVO v3 — N5]**: prima di DB-L4, valutare l'implementazione dell'operazione di riallineamento prezzo su attività non ancora fatturate (vedi §9 — N5). Non è il motore rettifiche completo, ma risolve il caso operativo più frequente con complessità minima.

---

## 15) Evoluzione v2 formule/scaglioni

Predisposizione consigliata (non bloccante v1):
1. Tabella regole formula separata da `listini_righe`
2. Tabella scaglioni separata per consumi/ore
3. Mapping input formula (letture, fasce, indici, coefficienti)
4. Output sempre normalizzato a `prezzo_snapshot` per commessa

**[NUOVO v3]**: valutare il refactor `daterange` (N1) come prerequisito architetturale di v2 prima di avviare il lavoro su formule/scaglioni.

---

## 16) Test

Stato attuale: **29 test verdi** (listini) + 49 (catalogo) = 78 test verdi complessivi.

| File                                                  | N   | Contenuto                                                |
| ----------------------------------------------------- | --- | -------------------------------------------------------- |
| `apps/vendite/tests/services/test_listini_service.py` | 8   | CRUD, ciclo versioni, righe, associazioni, test resolver |
| `apps/vendite/tests/api/test_listini_api.py`          | 21  | Tutti gli endpoint §12.3                                 |

**[NUOVO v3]** Test da aggiungere in Sprint A/B:

| Test                                                                                  | Tipo               | Sprint |
| ------------------------------------------------------------------------------------- | ------------------ | ------ |
| CRUD riga su versione ATTIVA → atteso 400                                             | Unit service + API | A      |
| CRUD riga su versione CHIUSA → atteso 400                                             | Unit service + API | A      |
| PATCH versione ATTIVA con campo non in whitelist → atteso 400                         | Unit service + API | A      |
| PATCH versione CHIUSA qualsiasi campo → atteso 400                                    | Unit service + API | A      |
| Clone versione: verifica righe copiate e stato BOZZA                                  | Unit service + API | B      |
| Clone retroattivo: verifica warning nel response                                      | Unit service       | B      |
| DELETE versione BOZZA: verifica cascade righe                                         | Unit service + API | B      |
| DELETE versione ATTIVA → atteso 400                                                   | Unit service + API | B      |
| DELETE listino con figli → atteso 400                                                 | Unit service + API | B      |
| Alert scadenze: listino con versione in scadenza senza successore                     | Unit service + API | B      |
| N6 — Rettifica riga ATTIVA non propagata: verifica modifica con audit                 | Unit service + API | B      |
| N6 — Rettifica riga ATTIVA già in commessa → atteso E_VENDITE_RIGA_GIA_PROPAGATA      | Unit service + API | B      |
| N6 — Rettifica riga ATTIVA già in attivita_fatturabili → atteso blocco                | Unit service + API | B      |
| N6 — Rettifica senza motivo → atteso 400                                              | Unit service       | B      |
| N7 — Variazione eccezionale su commessa LIBERO: verifica prezzo_bloccato=TRUE e audit | Unit service + API | B      |
| N7 — Variazione eccezionale su commessa CONFERMATO: ammessa                           | Unit service + API | B      |
| N7 — Variazione eccezionale su riga già fatturata → atteso blocco sulla riga          | Unit service + API | B      |
| N7 — Variazione eccezionale senza motivo → atteso 400                                 | Unit service       | B      |
| N7 — Sblocco prezzo bloccato: verifica prezzo_bloccato=FALSE e ricalcolo              | Unit service + API | B      |
| N7 — Sblocco prezzo su riga non bloccata → atteso 400                                 | Unit service       | B      |
| N7 — Sblocco prezzo su riga gia` fatturata → atteso 400                               | Unit service       | B      |
| N5 — Riallineamento con versione listino cambiata senza conferma → atteso 400         | Unit service       | B      |
| N5 — Riallineamento con versione cambiata + conferma esplicita → ammesso              | Unit service       | B      |
| N8a — Variazione +1500% → atteso 400 (fuori range ammesso)                            | Unit service       | B      |
| N8a — Variazione dry_run: verifica preview senza modifica dati                        | Unit service + API | B      |

---

## 17) Tracking avanzamento

### DB-L1, L2, L3 — COMPLETATI ✅

Vedi dettaglio checklist in documento v2 §13.1-13.3.

### Sprint A — Fix critici e completamento ciclo di vita — COMPLETATO ✅ (2026-04-08)

- [x] **F1** — Guard stato versione su CRUD righe (service): `_assert_versione_bozza_for_riga_op`
- [x] **F2** — Whitelist PATCH versione per stato (service): `_VERSIONE_PATCH_ALLOWED_BY_STATE`
- [x] **F3** — Test unitari e smoke test per F1/F2: 26 test unit + smoke 0..30
- [ ] **F1 defense-in-depth** — **[NUOVO v3]** Trigger DB `trgfn_listini_righe_guard_stato` *(task cross-branch `dev/db-tid`)*
- [ ] Test UI reale: permessi, readonly mode, drawer pattern, flussi completi
- [ ] Documentazione `manual/listini_versioni.md` aggiornata con regole esplicite per stato

### Sprint A-DOC — Documentazione (separato da codice)

- [ ] **N3** — **[NUOVO v3]** Definire e documentare lifecycle prezzo preventivo → commessa *(solo documentazione, nessun codice)*

### Sprint B-base — Operazioni di convenienza — COMPLETATO ✅ (2026-04-08)

- [x] **O1** — Clone versione (backend `clone_versione` + frontend `CloneVersioneDrawer.vue` + test)
- [x] **O2** — DELETE versione BOZZA (backend `delete_versione` + frontend + test)
- [x] **O3** — DELETE listino mai usato (backend `delete_listino` + frontend + test)
- [x] **D3** — Auto-close attivazione con dry_run (`AttivaVersioneDialog.vue`)
- [x] `CloneVersioneDrawer.vue` con warning retroattivo
- [x] Documentazione API in `docs/it/backend/vendite/manual/api_listini.md`

### Sprint B-v3 — Integrazioni critiche v3

- [ ] **N2** — **[NUOVO v3]** Endpoint alert-scadenze + widget frontend
- [ ] **N5** — **[NUOVO v3]** Operazione riallineamento prezzo (non-fatturato)
- [ ] **N6** — **[NUOVO v3]** Rettifica controllata riga ATTIVA non propagata (backend + trigger DB + test)
- [ ] **N7** — **[NUOVO v3]** Variazione prezzo eccezionale su commessa LIBERO/CONFERMATO (backend + test)
- [ ] **N7 sblocco** — **[NUOVO v3]** Sblocco `prezzo_bloccato` con ricalcolo resolver (backend + test)
- [ ] **N8a** — **[NUOVO v3]** Variazione % massa su versione BOZZA con dry_run (backend + frontend + test)
- [ ] Avviso UX su PATCH `valido_al` versione ATTIVA

### Sprint B-DOC — Documentazione v3

- [ ] **N8b** — **[NUOVO v3]** Documentazione operativa "listino post-it" in `guide/gestione-listini.md`

### DB-L4 Rettifiche — DA SCHEDULARE

Vedi [sviluppo-rettifiche.md](sviluppo-rettifiche.md). Prerequisito: chiusura bloccanti §8.5 di quel documento.

### Roadmap v2 — APERTA

- [ ] **N1** — **[NUOVO v3]** Ticket tecnico per valutazione `daterange` nativo PostgreSQL
- [ ] **N4** — **[NUOVO v3]** Nota documentazione match_level 3 (solo DOC, nessun codice)
- [ ] Formule/scaglioni utilities

---

## 18) Cosa resta fuori da questa fase

1. Formula engine completo utilities
2. Scaglioni avanzati multi-fascia
3. Simulazioni tariffarie previsionali
4. Listini fornitori e derivazione verso listini clienti → documento separato `sviluppo-listini-fornitori.md`

---

## 19) Building block riutilizzabili

Prodotti da questa fase:

| Componente                                                                              | Tipo                      | Consumatori previsti                        |
| --------------------------------------------------------------------------------------- | ------------------------- | ------------------------------------------- |
| `/api/v1/vendite/listini/test-prezzo/`                                                  | API REST                  | Verifica pricing cross-dominio              |
| `/api/v1/vendite/listini/alert-scadenze/`                                               | API REST **[NUOVO v3]**   | Dashboard, notifiche operatore              |
| `/api/v1/vendite/listini/{id}/versioni/{ver_id}/righe/{riga_id}/rettifica-controllata/` | API REST **[NUOVO v3]**   | Correzione listino ATTIVO senza clone       |
| `/api/v1/vendite/commesse/{id}/attivita/{att_id}/riallinea-prezzo/`                     | API REST **[NUOVO v3]**   | Riallineamento tecnico prezzo non fatturato |
| `/api/v1/vendite/commesse/{id}/attivita/{att_id}/variazione-prezzo-eccezionale/`        | API REST **[NUOVO v3]**   | Override manuale tracciato su commessa      |
| `/api/v1/vendite/commesse/{id}/attivita/{att_id}/sblocca-prezzo/`                      | API REST **[NUOVO v3]**   | Sblocco prezzo bloccato + ricalcolo resolver |
| `/api/v1/vendite/listini/{id}/versioni/{ver_id}/applica-variazione/`                    | API REST **[NUOVO v3]**   | Variazione % massa su BOZZA                 |
| `VersioneDrawer.vue`                                                                    | Componente                | Riusato da gestione pratiche se necessario  |
| `AlertScadenzeWidget.vue`                                                               | Componente **[NUOVO v3]** | Dashboard vendite                           |

Ereditati da catalogo:

| Componente                              | Origine                         |
| --------------------------------------- | ------------------------------- |
| `ArticoloLookup.vue`                    | `frontend/src/core/components/` |
| `/api/v1/catalogo/articoli/lookup/`     | Backend catalogo                |
| `/api/v1/catalogo/articoli/{id}/uom/`   | Backend catalogo                |
| `lookupCodici('catalogo.unita_misura')` | API generica core               |

---

*Sviluppo Listini — ZeroERP (aprile 2026, WIP v3 — consolidato con integrazioni critiche)*