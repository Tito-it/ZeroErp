# Refactor v1

## Obiettivo

Definire un percorso di refactor orientato alla **riscrittura veloce** del backend API, senza ottimizzare per compatibilita' temporanea o stabilita' di una produzione esistente.

L'obiettivo non e' preservare ogni dettaglio intermedio, ma arrivare rapidamente a una base architetturale coerente su cui proseguire lo sviluppo.

## Principio guida

L'ordine e' ottimizzato per:

- fissare subito il modello target;
- consolidare prima il centro riusabile;
- rifattorizzare poi i moduli piu' incoerenti;
- lasciare per ultimi i moduli gia' relativamente allineati;
- aggiornare la documentazione solo dopo la riscrittura strutturale.

## Checklist operativa

### Fase 1 — Definizione target

1. **Fissare il modello target prima di toccare il codice**

   Decidere una volta sola:

   - `pratiche` e' area funzionale autonoma oppure no;
   - i write API passano tutti dal protocollo core;
   - la grammatica URL sara' resource-oriented senza verbi nel path.

2. **Allineare subito il vocabolario architetturale**

   Aggiornare la documentazione architetturale minima necessaria per riflettere il modello deciso.

   Questo serve solo a evitare ambiguita' durante il refactor e a non riscrivere moduli due volte per interpretazioni diverse.

3. **Definire un template canonico per una API ZeroERP**

   Standard minimo:

   - `APIView`
   - `@extend_schema`
   - `authentication_classes`
   - `permission_classes`
   - `area_funzionale` o regola equivalente
   - helper unico per parse/error/idempotenza
   - service per orchestrazione
   - repository per SQL
   - response envelope uniforme

### Fase 2 — Consolidamento core

4. **Rifare prima il modulo `core` come piattaforma definitiva**

   Consolidare in `core` tutto quello che sara' riusato:

   - helper write
   - helper list/search
   - envelope risposta
   - policy idempotenza
   - regole permessi
   - eventuale base class per API dominio

5. **Eliminare le eccezioni nel cuore del framework API**

   Fare pulizia di:

   - `skip_area_check` non giustificati
   - naming ambigui
   - fallback impliciti
   - punti dove il resolver dei permessi si appoggia a convenzioni non documentate

   Il risultato deve essere un centro rigido, piccolo e leggibile.

6. **Sistemare il caso `pratiche` nel resolver permessi**

   Questo e' il refactor piu' importante per il modello mentale complessivo.

   Se `pratiche` resta area autonoma, renderlo esplicito e ufficiale.

   Se non resta autonoma, rimuovere il pattern dal codice e dalla documentazione.

### Fase 3 — Riscrittura moduli attivi

7. **Rifattorizzare `amm_software` per primo**

   E' la strada piu' veloce per togliere debito strutturale:

   - oggi ha molti write fuori standard;
   - tocca utenti, permessi e profili;
   - beneficia subito dell'allineamento al core.

   Obiettivi:

   - portare tutti i write su helper core;
   - spostare orchestrazione minima in service;
   - uniformare response ed error handling.

8. **Rifattorizzare `anagrafiche` subito dopo**

   Qui il vantaggio rapido e' alto:

   - uniformare le route;
   - togliere `/crea/` e `/aggiorna/`;
   - spostare logica non banale dalle view ai service.

   E' il modulo che migliora piu' visibilmente la coerenza esterna delle API.

9. **Rifattorizzare `pratiche` dopo `anagrafiche`**

   Non partire da qui se l'obiettivo e' la via piu' veloce: il dominio e' piu' ricco.

   Quando lo tocchi, applica il template gia' consolidato.

   Obiettivi:

   - view sottili;
   - service espliciti;
   - permessi allineati;
   - route coerenti.

10. **Rifattorizzare `vendite` per ultimo tra i moduli attivi**

    `vendite` e' gia' relativamente vicino al modello desiderato.

    Qui serve soprattutto convergenza finale:

    - naming
    - route
    - helper comuni
    - uniformita' dei contratti

### Fase 4 — Pulizia superficie progetto

11. **Decidere il destino delle app placeholder**

    Per `acquisti`, `catalogo`, `config`, `contabilita`, `magazzino`, `pagamenti`, `storico`:

    - o vengono tolte dalla superficie API finche' non esistono davvero;
    - o ricevono uno skeleton coerente col nuovo standard.

    Non lasciare file API vuoti come falso segnale architetturale.

12. **Riallineare il routing root**

    Esportare solo i moduli che rispettano il nuovo standard.

    Il root URL deve raccontare l'architettura reale, non quella prevista.

### Fase 5 — Uniformita' finale

13. **Fare una passata finale di uniformita'**

    Normalizzare:

    - naming classi
    - nomi schema OpenAPI
    - suffissi `V1`
    - nomi route
    - shape delle liste
    - shape dei detail
    - codici errore e metadati

14. **Aggiornare tutta la documentazione tecnica dopo il refactor**

    Prima si riscrive il software.

    Poi si aggiornano guide e documenti di sviluppo concentrico sulla struttura definitiva.

    Questo e' piu' veloce che tenere sincronizzati codice e docs durante una riscrittura forte.

## Ordine sintetico consigliato

1. Decidere il modello target
2. Rendere `core` definitivo
3. Fissare permessi e caso `pratiche`
4. Riscrivere `amm_software`
5. Riscrivere `anagrafiche`
6. Riscrivere `pratiche`
7. Rifinire `vendite`
8. Pulire i placeholder
9. Riallineare il routing root
10. Aggiornare la documentazione

## Nota pratica

Dato che non esiste vincolo di produzione da preservare, la strada piu' veloce non e' introdurre compatibilita' temporanee, adapter o layer di transizione.

La strategia piu' rapida e':

- fissare il contratto giusto;
- rifare il centro;
- riscrivere i moduli secondo il contratto;
- pulire il resto alla fine.

## Delta 2

Questa sezione aggiorna la roadmap dopo il refactor gia' avviato.

L'obiettivo non e' piu' definire il primo riordino generale, ma chiudere le
incongruenze rimaste rispetto al nuovo contratto API attivo.

### Checklist delta

1. **Rendere `api-contract.md` l'unica fonte normativa**

   Deprecare o riscrivere `docs/it/dev/api.md` per allinearlo al nuovo contratto.

   Finche' restano due standard, il refactor continuera' a divergere.

2. **Chiudere subito `amm_software`**

   Portare tutti i write su `handle_post_json`.

   Eliminare letture dirette di `request.data` da `patch` e `put`.

   E' il modulo piu' veloce da riallineare e toglie subito incoerenze nel backend admin.

3. **Completare il CRUD reale di `anagrafiche`**

   Aggiungere `GET detail` alle detail view che oggi fanno solo `PATCH`.

   Se una risorsa non deve avere detail, togliere la route `/<id>/` e riallineare il contratto locale.

4. **Uniformare la grammatica `lookup`**

   Scegliere una convenzione unica e applicarla ovunque.

   Dato il contratto attivo, la via piu' rapida e' convergere tutto a suffisso `/lookup/`.

5. **Riallineare naming route Django**

   Togliere i residui `*-v1-*` nei moduli ancora vecchi.

   Uniformare i nomi a `{modulo}-{risorsa}-{azione}` senza trasportare il versioning nel nome.

6. **Rifattorizzare `pratiche` al nuovo modello**

   Togliere il pattern `Api*V1`.

   Portare le view a `DomainAPIView`.

   Mantenere le route attuali se sono gia' corrette, ma eliminare la doppia grammatica di classi.

7. **Rifattorizzare `vendite` dopo `pratiche`**

   Anche qui:

   - eliminare `Api*V1`;
   - convergere su `DomainAPIView`;
   - mantenere gli endpoint di dominio ma con naming coerente.

   `vendite` e' gia' abbastanza ordinato, quindi conviene farlo dopo.

8. **Allineare tutta la documentazione tecnica secondaria**

   Dopo `amm_software`, `anagrafiche`, `pratiche`, `vendite`, aggiornare `api.md` e gli esempi sparsi.

   L'obiettivo e' evitare che nuovi sviluppi reintroducano pattern vecchi.

9. **Fare una passata finale di pulizia lessicale**

   Correggere typo e naming residui come:

   - `Prerequisti` / `Prerequisiti`
   - classi `Api*`
   - nomi schema OpenAPI non uniformi

   E' lavoro veloce ma va fatto solo dopo il grosso del refactor.

### Ordine sintetico Delta 2

1. `api.md` / standard unico
2. `amm_software`
3. completamento CRUD `anagrafiche`
4. `lookup` uniformi
5. naming route
6. `pratiche`
7. `vendite`
8. documentazione secondaria
9. pulizia finale lessicale

## Delta 3

Questa sezione chiude le incongruenze residue tra:

- `docs/it/dev/api.md`
- `docs/it/frontend/frontend-standards.md`
- implementazione reale di backend e frontend

L'ordine e' ottimizzato per **sviluppo/refactor veloce**.

Dato che non esiste produzione da preservare:

- non servono layer di compatibilita' temporanei;
- non servono adapter di transizione;
- conviene convergere direttamente sul modello finale.

### Checklist backend

1. **Rendere reale la policy idempotenza**

   Applicare la regola documentata: tutti i write che modificano stato devono usare
   `handle_post_json(..., require_idempotency_key=True)` oppure una policy unica
   e dichiarata esplicitamente.

   Priorita' massima per:

   - `pratiche`
   - `anagrafiche`
   - `amm_software`

2. **Chiudere `amm_software`**

   Portare tutti i write sul percorso unico:

   - niente `request.data` diretto nelle view mutanti;
   - usare `handle_post_json` per `POST`, `PATCH`, `PUT`;
   - mantenere la view sottile e lasciare logica al service.

   Questo e' il refactor backend piu' corto e con il miglior rapporto beneficio/tempo.

3. **Completare il CRUD reale di `anagrafiche`**

   Per tutte le risorse che hanno route `/<id>/`:

   - o aggiungere `GET detail`;
   - o eliminare la route detail se non ha senso esporla.

   Non lasciare route nominalmente "detail" che in pratica fanno solo `PATCH`.

4. **Uniformare definitivamente la grammatica lookup**

   Applicare una sola regola:

   - lookup generico via `core/lookup/codici`
   - lookup dedicato con suffisso `/lookup/`

   Adeguare subito gli endpoint rimasti fuori convenzione.

5. **Chiudere naming e shape route backend**

   Uniformare:

   - nomi route Django
   - nomi classi view
   - eventuali residui del vecchio naming

   L'obiettivo e' evitare un backend con due lessici contemporanei.

6. **Fare una passata finale backend sui moduli gia' quasi allineati**

   Ultimo giro su:

   - `vendite`
   - `pratiche`

   Non per rifarli da zero, ma per togliere le ultime differenze rispetto al contratto definitivo.

### Checklist frontend

7. **Rimettere i componenti di dominio dentro i domini**

   Spostare fuori da `src/core/components/` tutti i componenti che dipendono da uno
   store o da un dominio specifico `anagrafiche`.

   Esempi tipici:

   - search table geografiche
   - drawer geografici
   - componenti CRUD specializzati

   `core/` deve contenere solo componenti realmente shared.

8. **Introdurre coordinamento globale drawer**

   Lo standard dice che non si possono aprire due drawer contemporaneamente.

   Serve una sola delle due strade, scelta e applicata ovunque:

   - store/composable globale che chiude gli altri drawer;
   - un solo drawer controller per vista complessa.

   La via piu' veloce e' centralizzare il controllo, non aggiungere guard locali sparsi.

9. **Ripulire `IndirizziView` come vista orchestratrice**

   La vista oggi e' utile ma e' anche il punto dove si vede di piu' la stratificazione.

   Obiettivi:

   - mantenere i tab;
   - mantenere i SearchTable;
   - ridurre il numero di stati locali scollegati;
   - usare un pattern unico per apertura/chiusura drawer.

10. **Verificare tutti i pattern lista contro lo standard**

    Controllare i componenti lista e renderli omogenei rispetto a:

    - toolbar
    - filtri
    - `NewButton`
    - `useSearchTable`
    - click riga
    - paginazione sopra
    - classi CSS standard

    Non fare miglioramenti creativi per singolo componente: convergere tutti allo stesso pattern.

11. **Verificare separazione `core` vs domini**

    Oltre ai componenti, controllare anche:

    - composable
    - client API
    - store
    - helper UI

    Se un modulo conosce troppo `anagrafiche`, `amm-software` o altro dominio,
    non deve stare in `core`.

12. **Allineare navigazione e routing al reale stato del frontend**

    Verificare che:

    - `core/navigation.js` resti davvero unica fonte di verita';
    - le route reali e i placeholder raccontino lo stato reale;
    - non ci siano voci di menu che promettono strutture non ancora coerenti col pattern finale.

    Questo va fatto dopo la pulizia dei componenti e dei drawer.

### Pulizia finale

13. **Fare la passata lessicale e documentale finale**

    Solo dopo i refactor strutturali:

    - correggere typo e naming residui;
    - riallineare esempi nei documenti;
    - togliere descrizioni ormai vecchie;
    - verificare che `api.md` e `frontend-standards.md` descrivano davvero il codice esistente.

    Non fare questa fase troppo presto, altrimenti verra' rifatta due volte.

### Ordine sintetico Delta 3

1. policy idempotenza reale
2. `amm_software`
3. CRUD reale `anagrafiche`
4. lookup backend uniformi
5. naming/shape backend
6. rifinitura `vendite` e `pratiche`
7. componenti dominio fuori da `core`
8. coordinamento globale drawer
9. pulizia `IndirizziView`
10. pattern lista uniformi
11. separazione `core` vs domini
12. navigazione e routing
13. pulizia finale documentale

---

## Audit API — Stato reale (15 marzo 2026)

Fotografia delle API esistenti per guidare il piano esecutivo del refactor.

### Numeri

| Modulo              | Endpoint attivi | Service layer                                   | URL REST standard | Verbi nel path                                    |
| ------------------- | --------------- | ----------------------------------------------- | ----------------- | ------------------------------------------------- |
| `core`              | 25+             | N/A (infrastruttura)                            | Si'               | No                                                |
| `vendite`           | 14              | Si' (`pipeline_service`, `commesse_service`)    | Parziale          | `/run/`, `/reset-draft/`, `/stato/`               |
| `pratiche`          | 30+             | Si' (`pratiche_service`, `generazione_service`) | Parziale          | `/stato/`, `/sospendi/`, `/riattiva/`, `/genera/` |
| `amm_software`      | 17              | No (view → repository diretto)                  | Si'               | `/disabilita/`                                    |
| `anagrafiche`       | 20+             | No (view → repository diretto)                  | **No**            | `/crea/`, `/aggiorna/` su tutte le entita'        |
| Placeholder (7 app) | 0               | —                                               | —                 | —                                                 |
| **Totale**          | **~106**        |                                                 |                   |                                                   |

### Problemi identificati per modulo

#### `anagrafiche` — Priorita' alta (creato oggi, massima incoerenza)

| #   | Problema                                                                                              | Impatto                                        |
| --- | ----------------------------------------------------------------------------------------------------- | ---------------------------------------------- |
| A1  | **URL con verbi**: `/crea/`, `/aggiorna/` su tutte le 7 entita' (21 route)                            | Incoerente con `amm_software` e contratto REST |
| A2  | **Nessun service layer**: le view contengono validazione, orchestrazione, chiamate DB                 | View spesse, logica non riusabile              |
| A3  | **Repository "God class"**: `IndirizziRepository` gestisce 7 entita' di 2 schemi diversi (700+ righe) | Violazione naming convention AGENTS.md         |
| A4  | **5 dynamic UPDATE builder identici**: pattern fields/params ripetuto in ogni update_*                | Duplicazione, fragilita'                       |
| A5  | **Comuni non ha edit**: ComuniSearchTable non emette row-click, ComuneDrawer e' solo create           | Feature incompleta                             |

#### `amm_software` — Priorita' media

| #   | Problema                                                                                                      | Impatto               |
| --- | ------------------------------------------------------------------------------------------------------------- | --------------------- |
| B1  | **Nessun service layer**: `UtentiListView.post` fa validazione + hash password + chiama repository (40 righe) | View spessa           |
| B2  | **`/disabilita/` e' un verbo nel path**: dovrebbe essere `PATCH /utenti/<id>/` con `{"attivo": false}`        | Incoerenza minore     |
| B3  | **Error code `E_AMM_VALIDAZIONE` era non registrato** in error_policies (corretto il 15 marzo)                | Ora OK                |
| B4  | **`skip_area_check=True` su tutte le view**: corretto perche' usa `IsAdminZeroERP`, ma non documentato        | Confusione potenziale |
| B5  | **Test UI reali mancanti**: funziona visivamente ma mai testato end-to-end                                    | Rischio bug latenti   |

#### `pratiche` — Priorita' bassa (gia' vicino al target)

| #   | Problema                                                                                          | Impatto                                                           |
| --- | ------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------- |
| C1  | **Verbi azione nel path**: `/stato/`, `/sospendi/`, `/riattiva/`, `/genera/`                      | Giustificabile per azioni di dominio, ma da decidere se allineare |
| C2  | **View consistenti ma spesse**: alcune view fanno validazione inline prima di delegare al service | Minore — il service esiste gia'                                   |
| C3  | **Naming classi con suffisso V1**: `ApiPraticheListV1`, `ApiPraticaDetailV1`                      | Da decidere se tenere V1 o togliere                               |

#### `vendite` — Priorita' bassa (piu' vicino al target)

| #   | Problema                                                                     | Impatto                             |
| --- | ---------------------------------------------------------------------------- | ----------------------------------- |
| D1  | **Verbi azione**: `/pipeline/run/`, `/reset-draft/`                          | Giustificabile per operazioni batch |
| D2  | **Service layer presente e funzionante**: pipeline_service, commesse_service | Gia' allineato                      |
| D3  | **Naming classi con suffisso V1**: `ApiRunLottoPipelineV1`                   | Coerente con pratiche               |

#### `core` — Da consolidare come piattaforma

| #   | Problema                                                                                                                      | Impatto                                  |
| --- | ----------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------- |
| E1  | **`skip_area_check=True` usato su 10+ endpoint**: profilo, sessioni, diagnostica, lookup                                      | Giustificato ma da documentare la regola |
| E2  | **Manca una base class per view dominio**: ogni view ripete `authentication_classes`, `permission_classes`, `area_funzionale` | Duplicazione su 80+ view                 |
| E3  | **Nessun helper per list view**: ogni modulo riscrive parsing parametri (risolto parzialmente con `parse_list_params`)        | Da promuovere a standard                 |
| E4  | **Manca un helper per PATCH/update**: il pattern dynamic UPDATE e' nel repository, ma le view hanno boilerplate simile        | Da centralizzare                         |

### Grammatica URL — Decisione necessaria

Lo stato attuale e' incoerente:

```
amm_software:   POST /utenti/              PATCH /utenti/<id>/         ← REST standard
anagrafiche:    POST /toponomastica/crea/   PATCH /toponomastica/<id>/aggiorna/  ← verbi
pratiche:       POST /                      PATCH /<id>/               ← REST standard
                POST /<id>/stato/           POST /<id>/sospendi/       ← verbi azione
vendite:        POST /pipeline/run/         POST /lotti/<id>/reset-draft/  ← verbi azione
```

**Proposta di regola unica:**

1. **CRUD standard** → verbo HTTP determina l'azione, nessun verbo nel path
   - `POST /toponomastica/` (create), `PATCH /toponomastica/<id>/` (update)
2. **Azioni di dominio** (non-CRUD: cambio stato, sospensione, reset, run pipeline) → verbo ammesso come ultimo segmento
   - `POST /<id>/stato/`, `POST /<id>/sospendi/`, `POST /pipeline/run/`
3. **Lookup** → `/lookup/` come suffisso (gia' in uso)
   - `GET /regioni/lookup/`, `GET /stati/lookup/`

Questa regola rende coerenti tutte le API senza forzare un purismo REST dove non ha senso.

---

## Piano esecutivo refactor

### RF-1 — Decidere le 3 regole e documentarle (Fase 1)

Creare un file `docs/it/dev/api-contract.md` con:

- Grammatica URL (proposta sopra)
- Template canonico view (APIView + extend_schema + area_funzionale)
- Envelope standard (successo, errore, lista paginata)
- Regola `skip_area_check` (quando ammesso)
- Naming classi (con o senza suffisso V1)
- `pratiche` come area funzionale autonoma (conferma)

**Effort**: 1 sessione. **Prerequisiti**: nessuno.

### RF-2 — Base class core per view dominio (Fase 2)

Creare `AnagraficheBaseView(APIView)` o meglio una generica `DomainAPIView`:

```python
class DomainAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [ZeroERPPermission]
    # area_funzionale definita dalla sottoclasse
```

Elimina 3 righe ripetute su 80+ view.

**Effort**: 1 sessione. **Prerequisiti**: RF-1.

### RF-3 — Allineare URL anagrafiche (Fase 3)

Togliere `/crea/` e `/aggiorna/` da tutte le 7 entita':

| Da                                                     | A                            |
| ------------------------------------------------------ | ---------------------------- |
| `POST /toponomastica/crea/`                            | `POST /toponomastica/`       |
| `PATCH /toponomastica/<id>/aggiorna/`                  | `PATCH /toponomastica/<id>/` |
| (idem per indirizzi, comuni, province, regioni, stati) |                              |

Unificare list + create nella stessa view (pattern `amm_software`).
Aggiornare frontend API client (un file: `anagrafiche.js`).

**Effort**: 1 sessione. **Prerequisiti**: RF-1.

### RF-4 — Estrarre service layer per anagrafiche (Fase 3)

Creare `apps/anagrafiche/services/indirizzi_service.py`:

- Spostare validazione e orchestrazione dalle view al service
- Le view diventano sottili: parsing → service → response
- Il service gestisce IntegrityError e logica multi-step (get_or_create_stradario)

**Effort**: 1-2 sessioni. **Prerequisiti**: RF-3.

### RF-5 — Splittare IndirizziRepository (Fase 3)

Da 1 God class (700+ righe) a:

| File                      | Contenuto                                       |
| ------------------------- | ----------------------------------------------- |
| `indirizzi_repository.py` | Solo indirizzi_dettaglio + stradario            |
| `geo_repository.py`       | Toponomastica, comuni, province, regioni, stati |

**Effort**: 1 sessione. **Prerequisiti**: RF-4.

### RF-6 — Estrarre service layer per amm_software (Fase 3)

Creare `apps/amm_software/services/amm_software_service.py`:

- Spostare hash password, validazione, orchestrazione dalla view
- Togliere `/disabilita/` → `PATCH /utenti/<id>/` con payload `{"attivo": false, "ruolo_sistema": "DISABILITATO"}`

**Effort**: 1 sessione. **Prerequisiti**: RF-2.

### RF-7 — Allineare pratiche e vendite (Fase 3)

Impatto minimo: pratiche e vendite sono gia' vicini al target.

- Decidere se i verbi azione (`/stato/`, `/sospendi/`, `/run/`) restano (proposta: si')
- Allineare naming classi (togliere o tenere V1 — coerenza)
- Eventuale base class `DomainAPIView` anche qui

**Effort**: 1 sessione. **Prerequisiti**: RF-2.

### RF-8 — Pulizia placeholder e routing root (Fase 4)

- Togliere include vuoti da `urls.py` root per le 7 app placeholder
- Oppure lasciare con commento `# stub — nessun endpoint attivo`

**Effort**: 30 minuti. **Prerequisiti**: RF-7.

### RF-9 — Passata uniformita' finale (Fase 5)

- Naming classi coerente
- Schema OpenAPI allineato
- Codici errore tutti registrati in error_policies
- Shape liste e detail uniformi

**Effort**: 1 sessione. **Prerequisiti**: RF-8.

---

## Ordine esecutivo consigliato

```
RF-1  Decidere le 3 regole               → 1 sessione
RF-2  Base class DomainAPIView            → 1 sessione
RF-3  Allineare URL anagrafiche           → 1 sessione
RF-4  Service layer anagrafiche           → 1-2 sessioni
RF-5  Split repository anagrafiche        → 1 sessione
RF-6  Service layer amm_software          → 1 sessione
RF-7  Allineare pratiche e vendite        → 1 sessione
RF-8  Pulizia placeholder                 → 30 minuti
RF-9  Uniformita' finale                  → 1 sessione
      ────────────────────────────────────
      Totale stimato: 8-9 sessioni
```






# Analisi Gap Architetturale — ZeroERP

> Documento complementare al piano di refactor (Refactor v1).
> Il refactor risolve la **forma** del codice. Questo documento identifica i gap che riguardano il **comportamento del sistema** sotto carico reale di un ERP.

---

## Contesto

Il piano Refactor v1 copre:

- grammatica URL coerente (RF-1)
- base class `DomainAPIView` (RF-2)
- allineamento moduli `anagrafiche` e `amm_software` (RF-3 / RF-6)
- estrazione service layer (RF-4 / RF-6)
- pulizia strutturale (RF-7 / RF-9)

Quello che **non tocca** è l'architettura del sistema: come si testa, come si valida l'input, come i moduli si parlano, come si separano letture da scritture, come si gestiscono gli errori in modo sistematico.

---

## Gap identificati

### 1. Strategia di test

**Priorità: Alta**

È il buco più grande. Il piano Refactor v1 cita "test UI mancanti" per `amm_software` come nota a margine, ma non esiste nessun RF dedicato ai test.

Con il service layer estratto tramite RF-4 e RF-6, ogni funzione di business diventa finalmente testabile in isolamento, senza HTTP e senza database:

```python
# Testabile senza avviare Django, senza DB
def test_crea_utente_email_duplicata():
    result = utenti_service.create({"email": "gia@esistente.it"})
    assert result.error_code == "E_EMAIL_DUPLICATA"
```

**Senza test, ogni refactor successivo è un salto nel vuoto.** Il service layer estratto ha valore pieno solo se è coperto da test.

**Azione consigliata:** Aggiungere RF-10 al piano — scrittura test unitari sul service layer di `amm_software` e `anagrafiche` come primo batch.

---

### 2. Validazione input al confine

**Priorità: Alta**

Oggi la validazione vive nel service (o peggio nella view), in forma procedurale. Il pattern moderno è validare l'input **al confine del sistema**, prima che i dati entrino nella logica di business.

Il beneficio è che il service riceve dati già validati e non deve difendersi dall'input:

```python
# Schema dichiarativo — non logica procedurale nella view o nel service
class CreaUtenteInput(BaseModel):
    email: EmailStr
    ruolo: RuoloEnum
    password: str = Field(min_length=8)
```

Django REST Framework ha i serializer per questo scopo. Pydantic è un'alternativa più esplicita. La scelta dello strumento è secondaria — il principio è che **la validazione è separata dalla logica**.

**Azione consigliata:** Definire il pattern di validazione preferito per ZeroERP (serializer DRF o schema Pydantic) e aggiungerlo al template canonico della view definito in RF-1.

---

### 3. Domain events per la comunicazione tra moduli

**Priorità: Media**

ZeroERP ha moduli che si parlano: una pratica genera una commessa in `vendite`, un pagamento aggiorna lo stato in `pratiche`. Questo accoppiamento è probabilmente gestito oggi con chiamate dirette tra service.

Il problema delle chiamate dirette è che creano dipendenze esplicite tra moduli: `pratiche_service` deve conoscere `vendite_service`. Con un ERP che cresce, questa rete di dipendenze diventa difficile da gestire.

Il pattern alternativo è usare **eventi di dominio**:

```
PraticaChiusaEvent        →  vendite_service ascolta   →  crea commessa
PagamentoRegistratoEvent  →  pratiche_service ascolta  →  aggiorna stato
```

I moduli non si conoscono direttamente. Parlano attraverso eventi. Questo è importante per un ERP perché i flussi cross-modulo sono numerosi e crescono nel tempo.

**Non serve un message broker** (Kafka, RabbitMQ) per iniziare. Un dispatcher sincrono interno è sufficiente nelle fasi iniziali e non introduce complessità operativa.

**Azione consigliata:** Documentare i flussi cross-modulo esistenti e identificare quali beneficerebbero di un event dispatcher interno. Rimandare l'implementazione a quando il numero di flussi giustifica il pattern.

---

### 4. CQRS leggero — letture separate dalle scritture

**Priorità: Media**

La separazione fisica tra list view e detail view esiste già, ma non è formalizzata come principio architetturale. Le **query di lettura** e le **operazioni di scrittura** hanno requisiti diversi:

|                | Letture                         | Scritture                       |
| -------------- | ------------------------------- | ------------------------------- |
| Obiettivo      | Velocità, proiezioni flessibili | Correttezza, transazioni, audit |
| Ottimizzazione | SQL grezzo, viste, cache        | Service layer, stored functions |
| Errori         | Tollerabili (dati stale)        | Intollerabili (dati corrotti)   |

ZeroERP ha già le basi per questo: le stored functions PostgreSQL gestiscono le scritture con garanzie transazionali, mentre le letture possono essere ottimizzate indipendentemente.

Formalizzare questo divide il repository in due famiglie:

```
repositories/
  commands/   ← scritture: insert, update, delete via stored functions
  queries/    ← letture: SQL ottimizzato, proiezioni, lookup
```

**Azione consigliata:** Introdurre la distinzione `commands/` vs `queries/` nel repository durante RF-5 (split `IndirizziRepository`) come primo esempio del pattern.

---

### 5. Tassonomia degli errori

**Priorità: Bassa**

`error_policies` esiste con i codici errore, ma ogni modulo li gestisce in modo leggermente diverso. Un sistema coerente prevede una tassonomia a tre livelli con HTTP status code corrispondenti uniformi:

| Categoria      | Significato                               | HTTP |
| -------------- | ----------------------------------------- | ---- |
| `E_VALIDATION` | Input errato — il client deve correggersi | 400  |
| `E_CONFLICT`   | Stato incompatibile — es. email duplicata | 409  |
| `E_FORBIDDEN`  | Permessi insufficienti                    | 403  |
| `E_NOT_FOUND`  | Risorsa non esistente                     | 404  |
| `E_INTERNAL`   | Bug — non esporre dettagli al client      | 500  |

Ogni codice errore specifico (`E_EMAIL_DUPLICATA`, `E_RUOLO_NON_VALIDO`) appartiene a una categoria. Il frontend può gestire le categorie in modo generico e i codici specifici dove necessario.

**Azione consigliata:** Aggiungere il campo `categoria` alla struttura di `error_policies` e applicarlo durante RF-9 (passata uniformità finale).

---

## Riepilogo priorità

| Priorità | Gap                             | Quando affrontarlo                    |
| -------- | ------------------------------- | ------------------------------------- |
| 🔴 Alta   | Test sul service layer          | Subito dopo RF-4 e RF-6               |
| 🔴 Alta   | Validazione input al confine    | Da includere nel template RF-1        |
| 🟡 Media  | Domain events cross-modulo      | Quando i flussi cross-modulo crescono |
| 🟡 Media  | CQRS leggero (commands/queries) | Durante RF-5 come primo esempio       |
| 🟢 Bassa  | Tassonomia errori sistematica   | Durante RF-9                          |

---

## Relazione con il piano Refactor v1

Il refactor e i gap architetturali non sono in competizione. L'ordine corretto è:

1. **Refactor v1** — forma coerente, service layer estratto, URL allineate
2. **Validazione al confine** — aggiunta al template canonico (estende RF-1)
3. **Test** — scritti sul service layer appena estratto (nuovo RF-10)
4. **CQRS leggero** — introdotto durante lo split repository (estende RF-5)
5. **Domain events e tassonomia errori** — quando il sistema cresce

Il refactor crea le condizioni necessarie per applicare questi pattern. Senza service layer non ci sono test unitari. Senza test unitari ogni refactor successivo è rischioso.

---

*Documento prodotto il 15 marzo 2026 — complementare a `refactor-v1.md`*
