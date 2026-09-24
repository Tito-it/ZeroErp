# API Famiglie di documento — il catalogo dei documenti numerati sui registri

## Scopo

`vendite.famiglie_documento` è l'elenco dei **tipi di documento che prendono il
numero da un registro** (fattura, DDT, ordine, commessa, reso). Per ognuno
dichiara **dove vive** — schema, tabella, e il nome delle colonne che portano
numero, billing account e serie — e **con quale forma nasce** il suo numero
(prefisso e lunghezza di default, anno nel numero). Questa pagina documenta il
CRUD: quali campi si scrivono, con quale verbo, e che cosa il database rifiuta.

⚠️ Il gemello dei registri è [api_registri_numerazione.md](/backend/vendite/manual/api_registri_numerazione):
la famiglia dice ciò che un documento **può** esprimere, il registro ciò che
quel sezionale **fa**. Il modello e le decisioni stanno in
[brief-be-fe-crud-registri-di-numerazione](/dev/work-done/brief-be-fe-crud-registri-di-numerazione) §11.

## Endpoint

| Metodo | Path | Cosa fa |
| --- | --- | --- |
| `GET` | `/api/v1/vendite/famiglie/` | Lista paginata (ricerca, filtri, ordinamento) su `vw_famiglie_documento_lista`, con i conteggi dei registri e i **due blocchi col motivo** |
| `POST` | `/api/v1/vendite/famiglie/` | Creazione — **passa dalla madre** `fn_crea_famiglia_documento`, che nella stessa transazione provvede i registri mancanti su ogni emittente |
| `GET` | `/api/v1/vendite/famiglie/<id>/` | Dettaglio, stessa riga della vista |
| `PATCH` | `/api/v1/vendite/famiglie/<id>/` | Modifica delle sole colonne ammesse |
| `POST` | `/api/v1/vendite/famiglie/<id>/attivo/` | Accende / spegne — **verbo suo**, come per i registri |
| `GET` | `/api/v1/vendite/famiglie/export/?formato=csv\|xlsx` | Export delle righe filtrate |
| `GET` | `/api/v1/vendite/famiglie/lookup/` | Le famiglie attive coi loro default, per il drawer dei registri (`DomainAPIView`, area `vendite`, envelope `{"results": [...]}`) |

**Ricerca libera** (`search`, lista ed export): le colonne le decide il catalogo
della lista `vendite.famiglie_documento` (`ricerca_full` nella configurazione).
Da **un** carattere: è una tabella di configurazione, con prefissi e codici
corti. ⭐ Dal 2026-09-24 si cerca il `codice`, non il `codice_interno` (chiave
immutabile del sistema, non il codice dell'operatore). Il `codice` esce in lista
e nel dettaglio (`SELECT v.*` sulla vista); il **lookup** porta ancora il solo
`codice_interno`, che è la chiave con cui i registri si agganciano.

Tutto il CRUD sta su **`AdminAPIView`** (solo amministratore): una famiglia è
configurazione del sistema, non un dato di dominio. ⛔ Il **lookup no**: lo
chiama una schermata di dominio, e chiuderlo spegnerebbe i campi del drawer
dei registri per tutti gli altri, in silenzio.

Sede della verità: `_CAMPI_CREATE` / `_CAMPI_UPDATE` in
`apps/vendite/db/famiglie_repository.py` e `_OBBLIGATORI_CREATE` in
`apps/vendite/services/famiglie_service.py`.

## I campi, per verbo

| Campo | CREATE | UPDATE | Perché |
| --- | :---: | :---: | --- |
| `codice_interno` | ✅ obbligatorio | ⛔ | È ciò su cui il codice confronta: **immutabile** (lock automatico `trgfn_lock_columns`) |
| `codice` | ⛔ | ✅ | Il codice che la lista **mostra e cerca** (changeSet DB `20260924-03…-07`): mutabile, `UNIQUE`, `NOT NULL`. Alla nascita lo valorizza il trigger `trg_famiglie_documento_a10_default_codice_ins` col `codice_interno`: la madre non ha il parametro, quindi la creazione non lo passa e si cambia **dopo**, in modifica (Tid, 2026-09-24). Vuoto → `400 E_VENDITE_VALIDATION` col campo. ⚠️ Sulle sei famiglie di **seed** il valore lo decide il CSV (mirror `runOnChange`): una modifica dal CRUD torna al valore del seed al migrate successivo, come già la `descrizione` |
| `descrizione` | ✅ obbligatorio | ✅ | Etichetta |
| `schema_tabella`, `nome_tabella`, `colonna_numero` | ✅ obbligatori | ✅ (a registri assenti) | Dove vive il documento e dove scrive il numero. Il guard dei riferimenti verifica su `pg_attribute` che tabella e colonne **esistano davvero** |
| `colonna_billing_account` | ✅ **facoltativa** | ✅ (a registri assenti) | Il nome della colonna che porta il cliente. ⭐ **`NULL` = «questa famiglia non ha un billing account»**, la forma dell'ordine di acquisto, la cui controparte è un `soggetto_ruolo`. Stessa forma di `colonna_serie`; `''` normalizzata a `NULL`. Le famiglie senza BA **saltano** in `fn_ba_ha_storia_emittente` / `fn_get_storia_emittente_ba` — corretto per costruzione, un documento senza BA non contribuisce alla storia di nessun BA |
| `colonna_serie` | ✅ facoltativa | ✅ (a registri assenti) | `NULL` = «questa famiglia non gestisce le serie»: un registro di una famiglia senza serie **non può** avere un `serie_default` |
| `prefisso_default`, `lunghezza_default` | ✅ | ✅ | La forma del numero con cui **nasce** un registro della famiglia; da lì in poi vive sul registro |
| `attivo` | ✅ | ⛔ | Ha il suo verbo |
| `meta` | ✅ (default) | ⛔ | Colonna tecnica: nessuna maschera la scrive |
| `presidia_data_documento`, `anno_nel_numero_default`, `ammette_regole_fiscali` | ⛔ | ⛔ | Una famiglia creata dal CRUD nasce **non fiscale** e il `CHECK` dei registri cabla `'FATTURA'`: offrire il campo prometterebbe un comportamento che il resto del modello non dà |

⚠️ **Gli obbligatori si controllano sul valore, non sul `NULL`**: una stringa
vuota attraverserebbe il `NOT NULL`. Il service normalizza `''` → `NULL` su
tutto il payload (`_normalizza`) e rifiuta con `E_VENDITE_VALIDATION` + `field`
i **cinque** campi che la madre pretende: `codice_interno`, `descrizione`,
`schema_tabella`, `nome_tabella`, `colonna_numero`. Il BE non rifiuta niente
che la madre accetti: un elenco applicativo più stretto sarebbe una capacità
del DB non esposta.

## Che cosa rifiuta il database, e come arriva al client

| Rifiuto | Codice | Da dove |
| --- | --- | --- |
| tabella o colonna dichiarata che non esiste | `E_FAMIGLIA_DOCUMENTO_RIFERIMENTO_INESISTENTE` | `trgfn_famiglie_documento_guard_riferimenti` (`P0001`) — il BA si verifica **solo se dichiarato** |
| colonna serie dichiarata ma fuori dal vincolo di unicità del numero | `E_FAMIGLIA_DOCUMENTO_SERIE_NON_DISCRIMINA` | idem |
| cambio di `schema_tabella` / `nome_tabella` / `colonna_numero` / `colonna_billing_account` / `colonna_serie` su una famiglia che **ha registri** | `E_FAMIGLIA_DOCUMENTO_CHIAVE_IMMUTABILE` | `trgfn_famiglie_documento_guard_struttura` — `IS DISTINCT FROM`, quindi anche `NULL ↔ valore` è un cambio |
| spegnere una famiglia con registri vivi | guard di disattivazione | `script.fn_check_famiglia_documento_disattivabile` |
| seconda famiglia **attiva** sulla stessa tabella | `E_VENDITE_DUPLICATO` con la famiglia che blocca **nominata** | `uq_famiglie_documento_tabella_attiva` (indice parziale `WHERE attivo`), tradotto dal service |
| `codice_interno` duplicato | `E_VENDITE_DUPLICATO` | `uq_famiglie_documento_codice_interno`, tradotto dal service |
| `codice` duplicato | `E_VENDITE_DUPLICATO` | `uq_famiglie_documento_codice`, tradotto dal service col campo `codice` in modifica e `codice_interno` in creazione (il codice nasce dal codice interno) |

⛔ **I tre codici dei guard NON si traducono nel service**: arrivano come
`P0001` da `script.fn_log_and_raise_error`, non sono `IntegrityError`, e
risalgono al middleware che li risolve con la policy generata dal catalogo.
Intercettarli qui vorrebbe dire riscrivere il loro messaggio accanto a quello
del database.

⭐ I due blocchi si **leggono prima** di provare: la vista espone
`can_disattivare` / `rimozione_blocco_*` e `can_modificare_struttura` /
`struttura_blocco_*` col motivo, così la maschera spegne il pulsante invece di
far fallire il verbo — la capability propone, il guard ammette.

## Regole

- **La creazione non fa un `INSERT`**: passa da `vendite.fn_crea_famiglia_documento`,
  che scrive la famiglia **e** provvede i registri mancanti su ogni emittente
  nella stessa transazione. La risposta porta `registri_creati`. Il repository
  passa gli argomenti **per posizione** (`_CAMPI_CREATE`): posizioni e tipi
  della madre sono un contratto.
- **`PATCH` parziale**: si scrivono solo le colonne presenti nel payload;
  `''` diventa `NULL`. Zero righe toccate → rilettura: inesistente → `404`
  `E_VENDITE_NOT_FOUND`, altrimenti la riga com'è.
- **Il verbo `attivo/` è idempotente**: se la famiglia è già nello stato
  richiesto risponde la riga com'è. Riaccendere è ciò che si fa **al posto** di
  creare una seconda famiglia sulla stessa tabella.
- ⚠️ **Il migrate riscrive le cinque righe di seed**: i mirror CSV di
  `80_data` sono `runOnChange` e rileggono il file intero — una modifica fatta
  in maschera a una famiglia di seed dura fino al prossimo `db-migrate`. Un
  valore che deve restare si cambia **nel CSV**.

## Dipendenze DB

- `vendite.famiglie_documento`, `vendite.vw_famiglie_documento_lista`
- `vendite.fn_crea_famiglia_documento` — la madre
- `vendite.trgfn_famiglie_documento_guard_riferimenti`,
  `trgfn_famiglie_documento_guard_struttura`,
  `trgfn_famiglie_documento_guard_disattivazione`
- `script.fn_check_famiglia_documento_disattivabile`,
  `fn_check_famiglia_documento_struttura_modificabile`
- `anagrafiche.fn_ba_ha_storia_emittente`, `fn_get_storia_emittente_ba` — i
  lettori che saltano le famiglie senza BA

## Riferimenti

- Repository: `apps/vendite/db/famiglie_repository.py`
- Service: `apps/vendite/services/famiglie_service.py`
- View: `apps/vendite/api/views_famiglie.py`, rotte in `urls_famiglie.py`
- Test: `apps/vendite/tests/services/test_famiglie_service.py` (obbligatori,
  BA vuoto/assente → `NULL` alla madre, traduzione vincoli),
  `apps/vendite/tests/api/test_famiglie_api.py` (rotte, envelope del lookup)
- Frontend: `frontend/src/amministrazione/components/FamigliaDocumentoDrawer.vue`
- Guida: [Numerazione dei documenti e codici](/guide/numerazione-documenti-e-codici)
