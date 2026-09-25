# Brief DB — Il pannello di configurazione scrive con un verbo

> **Chi scrive:** team DB (`dev/db-tid`), 2026-09-25. **A chi:** Tid (decisioni,
> §4), poi team DB e team backend/frontend (§6).
> **Origine:** decisione **D-3** di
> [brief-db-permesso-nel-verbo-di-scrittura.md](brief-db-permesso-nel-verbo-di-scrittura.md)
> (§7.1), con la **D-5** per la forma del permesso. È il secondo brief operativo
> del modello, dopo [brief-db-magazzino-verbi-con-permesso.md](brief-db-magazzino-verbi-con-permesso.md).
> **Stato:** ✅ **D-P1 → D-P5 decise da Tid il 2026-09-25, tutte sulla proposta** (§4).
> ✅ **Lato DB scritto, provato e applicato da Tid su dbdev il 2026-09-25 (19:16)**
> (`20260925-29…-34`, §5): la lista, i due building block, il verbo, la porta su `causali`.
> I COMMENT vivi coincidono coi file. ✅ **Corsa pgTAP di Tid verde.** ⏳ Resta il backend
> (§6), poi il frontend; e il commit del lato DB.
>
> **In una riga:** il pannello «Gestione tabelle» scrive su 87 tabelle con SQL
> costruito nel backend, e chiede sempre il livello `TUTTO` sull'area
> Configurazione, qualunque sia la tabella. Qui diventa **un verbo DB** che
> controlla il livello sull'**oggetto** a cui la riga appartiene, e la lista delle
> tabelle ammesse diventa **un dato del DB** al posto della costante del backend.

---

## 1. Il punto di partenza — letto il 2026-09-25

Fatti datati, letti dal codice e dal catalogo di dbdev. Descrivono da dove si
parte: non decidono la forma.

### 1.1 Come scrive oggi il pannello

* **Due operazioni sole**: `INSERT` e `UPDATE` per `id`. Nessun `DELETE`: una riga
  si ritira con un `PATCH` su `attivo` o `obsoleto_dal`, che sono colonne come le
  altre (`core/db/config_crud_repository.py`, `create_record` e `update_record`).
* **Le colonne** si leggono da `information_schema`; ne sono escluse `data_insert`,
  `user_insert`, `data_update`, `user_update`, `tx_id`, `storicizza`, `uid`. La
  chiave è **sempre** `id` (`config_metadata_repository.py`).
* ⚠️ **Una chiave del payload che non è una colonna viene scartata in silenzio**, e
  un payload tutto sconosciuto diventa un `INSERT` che non fa niente (`{}`) o un
  «non trovato» sull'`UPDATE`.
* **Il nome della tabella** entra nell'SQL per interpolazione, dopo il controllo
  `rel in REL_CONSENTITE` nel service.
* **Il permesso**: le quattro view (`core/api/views_config_crud.py`) dichiarano
  `area_funzionale = "config"`; `POST` e `PATCH` chiedono `TUTTO` su **config**.

### 1.2 La lista ammessa

* `REL_CONSENTITE` (`core/db/dbops_repository.py`), **87 voci distinte**: 61 in `config`,
  le altre in `anagrafiche`, `catalogo`, `documenti`, `magazzino`, `pagamenti`,
  `pratiche`, `ui`, `vendite`.
* ⭐ **Serve a due cose**, e questo conta per il disegno:
  * è la whitelist del **lookup generico** (`dbops.fn_get_lookup_codici`), cioè le
    tendine di tutta l'applicazione;
  * è l'elenco delle tabelle del **pannello**, lette e scritte.
* Ne esiste una terza copia nel frontend, `frontend/src/core/config-tables.js`
  (il registro con le etichette), legata alla prima da un test Django.

### 1.3 Quello che il modello non sapeva

* ⛔ **Quasi nessuna tabella della lista ha un model Django**: il backend ne
  dichiara 15 in tutto, quasi tutti del sistema permessi. La D-5 voleva nominare
  l'oggetto con `app_label` + `model_name` «che il catalogo ha già»: per il
  pannello **non c'è**.
* ⭐ **Una convenzione però esiste**, ed è già in due sedi: la chiave
  `(schema, nome logico)`. È quella di `config.area_model_overrides` (per esempio
  `('anagrafiche', 'soggetto')`) e dei model riservati dell'interfaccia permessi
  (`('config', 'profili_accesso')`, `amm_software_repository.py`). L'area per
  default è il primo pezzo della chiave (area = schema, guida
  architettura-permessi §6.2).
* **Quattro tabelle della lista hanno la RLS attiva**: `magazzino.magazzini`,
  `magazzino.ubicazioni`, `pagamenti.enti_incasso`, `vendite.listini`. Due hanno
  anche il guard di perimetro sull'emittente (`magazzini`, `listini`). Le altre 83
  sono cataloghi senza perimetro.
* **Tredici tabelle della lista hanno anche endpoint propri** che scrivono con SQL
  diretto: fra le altre `magazzino.magazzini` e `ubicazioni` (piano del
  2026-09-21), `vendite.listini`, `ui.lista_definizione`, `pratiche.template_flussi`,
  `catalogo.unita_misura`, `config.email_account`.
* Nessun test Django esegue una scrittura vera del pannello sul DB.

## 2. Il problema, sul modello

1. **Il permesso guarda l'area sbagliata.** Chi ha `TUTTO` su Configurazione e
   `LETTURA` su Magazzino crea causali di magazzino dal pannello: il livello si
   chiede sull'area del **pannello**, non su quella della **riga**. È il difetto
   del §7.1 del brief del modello.
2. **Il DB non applica niente.** L'app ha `INSERT`/`UPDATE` su tutte le 87 tabelle.
3. **La lista vive nel backend**, in tre copie (costante, registro FE, test).

## 3. Il disegno proposto

### 3.1 La lista a DB: `config.tabelle_gestibili`

Una tabella di catalogo, un CSV in `80_data` (una tabella, un CSV):

| Colonna | Cosa dice |
| --- | --- |
| `id`, `codice` | la riga; `codice` = `schema.tabella` |
| `schema_tabella`, `nome_tabella` | la tabella fisica |
| `app_label`, `model_name` | **l'oggetto** a cui la riga appartiene (D-5), con la convenzione `(schema, nome logico)` del §1.3 — vedi D-P1 |
| `lookup` | la tabella serve al lookup generico (le tendine) |
| `pannello` | la tabella si gestisce dal pannello |
| `attivo`, audit | come ogni catalogo |

⭐ **Due capacità in una riga, non due liste.** Oggi la stessa costante vale per
tutte e due; una tabella può restare nelle tendine e uscire dal pannello (D-P2).

L'area **non è una colonna**: si ricava dall'oggetto (§3.2). Scriverla qui sarebbe
una seconda sede della regola «area di un oggetto».

Un presidio pgTAP lega la lista al catalogo: ogni riga esiste come tabella, ha
una colonna `id`, e **nessuna riga con `pannello = true` ha la RLS attiva**
(§3.4).

### 3.2 I due building block del permesso sull'oggetto

* **`script.fn_area_di_oggetto(p_app_label, p_model_name)`**, check pura: l'area
  da `area_model_overrides` se c'è un override, altrimenti `app_label` (area =
  schema). Oggi la stessa regola la fa **il backend**, in Python
  (`PermissionResolver.get_area_schema_db`, `core/services/permissions_resolver.py:310`):
  la sede diventa il DB, e il backend la chiama (richiesta al §6). Senza questo
  passo il verbo ne sarebbe una seconda copia.
* **`script.fn_guard_livello(p_auth_user_id, p_app_label, p_model_name, p_livello_minimo)`**,
  il gemello di `fn_guard_azione` previsto dalla D-2 e dalla D-5. Chiede a
  `fn_resolve_livello_oggetto` (override utente sull'oggetto, poi l'area, già col
  gate di contesto dal 24-09) e solleva `E_PERMESSO_NEGATO` se il livello è sotto
  il minimo, anche a utente `NULL`. INVOKER.

### 3.3 Il verbo: `config.fn_pannello_scrivi(p_tabella, p_id, p_dati)`

* `p_tabella` è il `codice` della lista, `p_id` NULL = inserimento, altrimenti
  modifica di quella riga; `p_dati` è un `jsonb`. Ritorna la riga scritta come
  `jsonb`, senza le colonne escluse.
* **SECURITY DEFINER del proprietario**, `search_path` bloccato (stampo dei verbi
  di magazzino).
* **Passo 0:** la tabella è nella lista con `pannello = true` e `attivo`,
  altrimenti rifiuto. **Passo 1:** `fn_guard_livello(utente, app_label,
  model_name, 'TUTTO')`, con l'oggetto **della riga di lista**.
* **Colonne:** quelle del catalogo meno le escluse (le stesse di oggi, più `id`).
  I valori li converte PostgreSQL (`jsonb_populate_record` sul tipo di riga),
  quindi date, numeri e `jsonb` hanno la conversione del DB, non quella del
  driver.
* **Chiavi sconosciute nel payload: rifiuto**, non scarto silenzioso (D-P3).
* I trigger delle tabelle (audit, `ATTIVO`, guard di codice, storico) scattano
  come oggi: il verbo non li sostituisce.
* Nessun `DELETE`, come oggi.

### 3.4 Il perimetro: perché la lista non ammette tabelle con RLS

Come DEFINER il verbo non vede la RLS. Per i verbi di magazzino il perimetro l'ha
rimesso il verbo stesso, con il predicato della policy nella `WHERE`. Un verbo
**generico** non può farlo: ogni tabella ha la sua policy, e ricopiarle nel verbo
sarebbe una seconda sede di ciascuna. ⇒ **Il pannello gestisce solo tabelle
senza perimetro**, e il verbo lo verifica al passo 0 (`relrowsecurity`), non si
fida della lista. Le quattro tabelle con RLS escono dal pannello (D-P2): hanno già
tutte endpoint propri.

### 3.5 La porta

* Si chiude **per dominio**, come deciso in D-3: l'app perde
  `INSERT`/`UPDATE`/`DELETE` sulle tabelle della lista dei domini che adottano il
  modello, oggi **`magazzino`**. Nel loop dei grant (`v_tabelle_sola_lettura_app`)
  e nel provisioning, non con un `REVOKE` in un changeSet.
* ⚠️ Delle tre tabelle di magazzino nella lista, **solo `causali`** resta nel
  pannello. `magazzini` e `ubicazioni` hanno RLS ed endpoint propri che scrivono
  con SQL diretto: chiuderle chiede i **loro** verbi, un lavoro del cantiere
  magazzino (D-P4).
* Le tabelle degli altri domini restano scrivibili anche direttamente finché il
  loro dominio non passa al modello. La lista a DB lo può dire: le tabelle
  «chiuse» sono quelle del loop.

## 4. Decisioni — di Tid

| # | Domanda | Proposta |
| --- | --- | --- |
| **D-P1** | Come si nomina l'**oggetto** di una tabella senza model Django (§1.3)? | ✅ **DECISA da Tid il 2026-09-25, sulla proposta:** **Con la convenzione che esiste già, `(schema, nome tabella)`**: `app_label = 'magazzino'`, `model_name = 'causali'`. È la chiave di `area_model_overrides` e dei model riservati; un override utente su quell'oggetto funziona senza niente di nuovo. Precisa la D-5 («la chiave che il catalogo ha già»): per il pannello la chiave c'è, ma è la convenzione, non il model |
| **D-P2** | Le quattro tabelle con RLS (`magazzini`, `ubicazioni`, `enti_incasso`, `listini`) | ✅ **DECISA da Tid il 2026-09-25, sulla proposta:** **Escono dal pannello e restano nelle tendine** (`pannello = false`, `lookup = true`). Il verbo generico non sa rimettere un perimetro senza ricopiare le policy (§3.4); tutte e quattro hanno già endpoint propri |
| **D-P3** | Una chiave del payload che non è una colonna | ✅ **DECISA da Tid il 2026-09-25, sulla proposta:** **Rifiuto** con un codice registrato, invece dello scarto silenzioso di oggi (AGENTS: non normalizzare in silenzio). Cambia il comportamento per un client che manda campi in più: da dire al frontend |
| **D-P4** | `magazzino.magazzini` e `ubicazioni`: chi li chiude | ✅ **DECISA da Tid il 2026-09-25, sulla proposta:** **Un brief a sé del cantiere magazzino**, con i loro verbi (perimetro come in `fn_posta_*`). Questo brief chiude solo `causali`. Finché non si fa, `magazzino` è un dominio **a metà** (§5 del modello), e la sua guida lo deve dire con l'elenco |
| **D-P5** | La terza copia della lista, `config-tables.js` nel frontend | ✅ **DECISA da Tid il 2026-09-25, sulla proposta:** **Si ritira** a favore della lista a DB, con le etichette dalle chiavi i18n per convenzione. Decisione da prendere col team FE: qui la si segnala |

## 5. I passi

| Passo | Stato |
| --- | --- |
| **P-0** | ✅ **2026-09-25.** Le 87 voci di `REL_CONSENTITE` esistono tutte e hanno `id`. L'`id` nasce identity in 86; ⚠️ **`vendite.stati_commessa` non ha default sull'`id`**: dal pannello non si inserisce, né prima né ora (il backend escludeva già `id`) — fatto dichiarato, non corretto. Due tabelle hanno già una chiave d'oggetto in `area_model_overrides`: `catalogo.unita_misura` coincide con la convenzione, **`vendite.listini` è `('vendite', 'listino')`** e il CSV usa quella. Chi scrive `magazzino.causali` come app: nessuno nel backend, un pgTAP al runner `owner` |
| **P-1** | ✅ Scritto. `00_schema/config/20260925-29-create-config-tabelle-gestibili`: `codice_interno` = `schema.tabella` (CHECK), oggetto con CHECK di forma, `lookup` e `pannello`, niente `attivo` (una riga con i due flag spenti è ritirata). `80_data/changelog/20260925-30-seed-tabelle-gestibili` + `80_data/sql/config/tabelle_gestibili.csv`: 87 righe, `lookup` tutte, `pannello` 83 (fuori le quattro con RLS) |
| **P-2** | ✅ Scritto. `20_code/script/20260925-31-create-fn-area-di-oggetto` (plpgsql, perché il presidio dei riferimenti morti vede solo il plpgsql) e `-32-create-fn-guard-livello`. ⛔ L'enum `livello_accesso` è ordinato `TUTTO < LETTURA < BLOCCATO`: il rifiuto è `livello > minimo`, pinnato nei due versi dal pgTAP |
| **P-3** | ✅ Scritto. `20_code/config/20260925-33-create-fn-pannello-scrivi`. **Nessuna funzione di lettura**: il backend legge la lista con un `SELECT`, che l'app ha. Quattro codici nuovi in `codici_errore.csv` e `messaggi_errore.csv` (id 1134…1137): `E_PANNELLO_TABELLA_NON_AMMESSA` (TECNICO), `E_PANNELLO_DATI_VUOTI`, `E_PANNELLO_CAMPO_NON_AMMESSO` (DATO_ERRATO, con `campo`), `E_PANNELLO_RIGA_NON_TROVATA` (NON_TROVATO) |
| **P-4** | ✅ Scritto. `90_end/20260925-34-revoke-app-scrittura-pannello-magazzino` + `v_tabelle_sola_lettura_app` nel loop `20260205-41` + blocco nel provisioning: in sola lettura per l'app **`magazzino.causali`** e **`config.tabelle_gestibili`** (la lista è una porta: il verbo scrive come proprietario su ogni tabella che vi compare) |
| **P-5** | ✅ Scritto e provato. `script/test-fn-guard-livello-v1` (12), `config/test-fn-pannello-scrivi-v1` (14), `config/test-pannello-porta-v1` (7). **Prova** su `zeroerp_ci` come proprietario, SQL estratto di `-29`, `-31…-34` più il CSV (con `\copy`: il `loadUpdateData` non è provato, la sua forma è quella del seed `20260919-09`) e i quattro codici, in transazione annullata: `plpgsql_check` a zero sulle tre funzioni; guard 12/12, verbo 14/14, porta 5/7 — rossi il 3 e il 4, veri solo come app (dichiarato nel file). Due difetti trovati nei test e corretti: `format('%s')` su un booleano scrive `t`; il 4 della porta, da proprietario, inseriva davvero una riga e sporcava il 6 (ora `WHERE false`). Guardrail statici verdi |
| **P-6** | ✅ Brief e pagine `manual/` (`tabelle_gestibili`, `fn_pannello_scrivi`, `fn_guard_livello`, `fn_area_di_oggetto`). ⏳ La guida dei permessi e `PROJECT_CONTEXT` dopo l'apply |

✅ **Tid:** apply su dbdev (19:16, codici compresi) e corsa col runner **verde**, come app (i due rossi «da owner» della porta sono verdi) — presidi trasversali compresi, presidi trasversali compresi (`test-riferimenti-morti-v1`; `test-rubinetto-primo-motivo-v1` non si sposta).

## 6. Ricadute sul backend e sul frontend

* **Il repository del pannello chiama il verbo** al posto dell'SQL costruito:
  `create_record` e `update_record` diventano una chiamata. Le mappe dei vincoli
  (`_mappe_vincoli`) restano: gli errori del DB arrivano come oggi.
* **`REL_CONSENTITE` si ritira nello stesso giro**: lookup e pannello leggono la
  lista dal DB. Una sede sola.
* **L'area di un oggetto la dà `script.fn_area_di_oggetto`**: la risoluzione in
  Python (`permissions_resolver`, `area_model_overrides`) la chiama invece di
  rifarla.
* ⚠️ **Effetto voluto sul comportamento** (§7.1 del modello): chi aveva `TUTTO`
  solo su Configurazione non scrive più le tabelle degli altri domini dal
  pannello. Qualche profilo andrà rivisto; non siamo in produzione.
* Il 403 del backend resta: il controllo dell'endpoint chiede lo stesso livello
  sulla stessa area, prima di aprire la transazione.
* Test Django: nessuno oggi scrive davvero sul DB dal pannello; ne serve uno per
  il percorso nuovo.
* **I codici nuovi** (`E_PANNELLO_*`) vanno nel catalogo generato del backend
  (`error_policies_generated.py`). `E_PANNELLO_RIGA_NON_TROVATA` prende il posto di
  `E_ANAG_NOT_FOUND` per l'aggiornamento di una riga che non c'è.
* ⚠️ **Il frontend non deve mandare campi in più** (D-P3): una chiave che non è una
  colonna scrivibile ora è `E_PANNELLO_CAMPO_NON_AMMESSO`, non viene più ignorata.
  `context.campo` dice quale.
* Le quattro tabelle con RLS escono dal pannello (D-P2): il registro del frontend e
  l'elenco delle tabelle del pannello le devono togliere; nelle tendine restano.

---

## Registro

| Data | Chi | Cosa |
| --- | --- | --- |
| 2026-09-25 | DB | Brief scritto dalla D-3 del brief del modello. Emersi dalla struttura: la lista serve anche al lookup (due capacità), le tabelle del pannello non hanno model Django (D-P1), quattro hanno la RLS (D-P2) |
| 2026-09-25 | Tid | D-P1 → D-P5 decise, tutte sulla proposta («ok 5 si») |
| 2026-09-25 | DB | **P-0 → P-6 lato DB scritti e provati** (`20260925-29…-34`), non applicati. Emersi: `vendite.stati_commessa` senza default sull'`id`; `vendite.listini` ha già la chiave `('vendite','listino')`; `ui.lista_definizione` ha un'area non a catalogo (solo SUPER_ADMIN, coerente coi suoi endpoint); la lista stessa va chiusa all'app |
| 2026-09-25 | Tid | `-29…-34` applicati su dbdev (19:16), mirror dei codici compreso. Verificato: COMMENT vivi uguali ai file, 87 righe (83 nel pannello), porta chiusa su `causali` e sulla lista |
| 2026-09-25 | Tid | Corsa pgTAP: **test verdi**. Lato DB chiuso; resta il backend (§6) |
