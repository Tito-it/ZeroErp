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
| `GET` | `/api/v1/vendite/famiglie/sorgenti/` | Le sorgenti fra cui si sceglie la famiglia da creare (dal 2026-10-20): i tipi di documento di `config.sorgenti` con la loro tabella, `famiglia_esistente` e `tabella_numerata_da` (`AdminAPIView`, envelope `{"results": [...]}`) |

⭐ **Una famiglia è quella di una sorgente** (dal 2026-10-20,
[brief-db-grammatica-unica-documenti](../../../dev/work-in-progress/brief-db-grammatica-unica-documenti.md)
2c, G-5): il suo `codice_interno` è il `codice_interno` di `config.sorgenti`
(FK `fk_famiglie_documento_sorgenti`) e la tabella dei documenti è la
`target_table` della sorgente. `schema_tabella` e `nome_tabella` non sono più
colonne della famiglia né campi dei verbi: la vista li calcola ancora, in sola
lettura, insieme a `tabella_documento`. L'elenco `sorgenti/` porta, per ogni
sorgente, due **informazioni** con cui la maschera spegne la voce e dice perché
(`famiglia_esistente`: la sorgente ha già una famiglia, che si riaccende;
`tabella_numerata_da`: la descrizione della famiglia attiva che numera già la
stessa tabella). Il rifiuto resta al database.

**Parametri della lista** (e dell'export, senza paginazione): `attivo` (bool;
assente = **tutte**, spente comprese — sono quelle che spiegano un rifiuto in
creazione), `gestisce_serie` (bool, derivato da `colonna_serie IS NOT NULL`),
`search`, `order_by` (whitelist, default `codice_interno`; fuori whitelist →
**400** `E_VALIDATION_INPUT`, dal 2026-10-20), `order_dir` (`asc` default | `desc`), `limit` (default `25`,
max `200`) / `offset`. Un booleano non riconosciuto è un `400`. Risposta:
envelope paginato standard (`count`, `page`, `page_size`, `total_pages`,
`results`).

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

⛔ **Una chiave fuori dall'elenco del verbo è un `400 E_VENDITE_VALIDATION`**
(«Campi non ammessi in creazione/modifica…», `validate_allowed_keys`), in
creazione **e** in modifica — `attivo` o `codice_interno` spediti in `PATCH`
compresi. Prima del 2026-09-26 il repository le scartava in silenzio.

| Campo | CREATE | UPDATE | Perché |
| --- | :---: | :---: | --- |
| `codice_interno` | ✅ obbligatorio | ⛔ | Il codice della **sorgente** (da `sorgenti/`): FK verso `config.sorgenti`. È ciò su cui il codice confronta: **immutabile** (lock automatico `trgfn_lock_columns`) |
| `codice` | ⛔ | ✅ | Il codice che la lista **mostra e cerca** (changeSet DB `20260924-03…-07`): mutabile, `UNIQUE`, `NOT NULL`. Alla nascita lo valorizza il trigger `trg_famiglie_documento_a10_default_codice_ins` col `codice_interno`: la madre non ha il parametro, quindi la creazione non lo passa e si cambia **dopo**, in modifica (Tid, 2026-09-24). Vuoto → `400 E_VENDITE_VALIDATION` col campo. ⚠️ Sulle sei famiglie di **seed** il valore lo decide il CSV (mirror `runOnChange`): una modifica dal CRUD torna al valore del seed al migrate successivo, come già la `descrizione` |
| `descrizione` | ✅ obbligatorio | ✅ | Etichetta |
| `colonna_numero` | ✅ obbligatoria | ✅ (a registri assenti) | Dove il documento scrive il numero. Il guard dei riferimenti verifica su `pg_attribute` che la tabella della sorgente e le colonne **esistano davvero** |
| `schema_tabella`, `nome_tabella` | ⛔ | ⛔ | **Ritirati il 2026-10-20**: la tabella è la `target_table` della sorgente. Spediti, sono un `400 E_VENDITE_VALIDATION` con `unknown_keys` |
| `colonna_billing_account` | ✅ **facoltativa** | ✅ (a registri assenti) | Il nome della colonna che porta il cliente. ⭐ **`NULL` = «questa famiglia non ha un billing account»**, la forma dell'ordine di acquisto, la cui controparte è un `soggetto_ruolo`. Stessa forma di `colonna_serie`; `''` normalizzata a `NULL`. Le famiglie senza BA **saltano** in `fn_ba_ha_storia_emittente` / `fn_get_storia_emittente_ba` — corretto per costruzione, un documento senza BA non contribuisce alla storia di nessun BA |
| `colonna_serie` | ✅ facoltativa | ✅ (a registri assenti) | `NULL` = «questa famiglia non gestisce le serie»: un registro di una famiglia senza serie **non può** avere un `serie_default` |
| `prefisso_default`, `lunghezza_default` | ✅ | ✅ | La forma del numero con cui **nasce** un registro della famiglia; da lì in poi vive sul registro |
| `attivo` | ✅ | ⛔ | Ha il suo verbo |
| `meta` | ✅ (default) | ⛔ | Colonna tecnica: nessuna maschera la scrive |
| `presidia_data_documento`, `anno_nel_numero_default`, `ammette_regole_fiscali` | ⛔ | ⛔ | Una famiglia creata dal CRUD nasce **non fiscale** e il `CHECK` dei registri cabla `'FATTURA'`: offrire il campo prometterebbe un comportamento che il resto del modello non dà |

⚠️ **Gli obbligatori si controllano sul valore, non sul `NULL`**: una stringa
vuota attraverserebbe il `NOT NULL`. Il service normalizza `''` → `NULL` su
tutto il payload (`_normalizza`) e rifiuta con `E_VENDITE_VALIDATION` + `field`
i **tre** campi che la madre pretende: `codice_interno`, `descrizione`,
`colonna_numero` (erano cinque fino al 2026-10-20). Il BE non rifiuta niente
che la madre accetti: un elenco applicativo più stretto sarebbe una capacità
del DB non esposta.

## Che cosa rifiuta il database, e come arriva al client

| Rifiuto | Codice | Da dove |
| --- | --- | --- |
| tabella o colonna dichiarata che non esiste (anche: la sorgente non dichiara una tabella) | `E_FAMIGLIA_DOCUMENTO_RIFERIMENTO_INESISTENTE` | `trgfn_famiglie_documento_guard_riferimenti` (`P0001`), sulle famiglie **attive** — il BA si verifica **solo se dichiarato** |
| colonna serie dichiarata ma fuori dal vincolo di unicità del numero | `E_FAMIGLIA_DOCUMENTO_SERIE_NON_DISCRIMINA` | idem |
| cambio di `colonna_numero` / `colonna_billing_account` / `colonna_serie` su una famiglia che **ha registri** | `E_FAMIGLIA_DOCUMENTO_CHIAVE_IMMUTABILE` | `trgfn_famiglie_documento_guard_struttura` — `IS DISTINCT FROM`, quindi anche `NULL ↔ valore` è un cambio |
| spegnere una famiglia con registri vivi | guard di disattivazione | `script.fn_check_famiglia_documento_disattivabile` |
| seconda famiglia **attiva** sulla stessa tabella (due sorgenti possono avere la stessa `target_table`) | `E_FAMIGLIA_DOCUMENTO_TABELLA_GIA_NUMERATA`, che nomina la famiglia che la numera | `trgfn_famiglie_documento_guard_riferimenti` (`P0001`). Fino al 2026-10-20 era l'indice `uq_famiglie_documento_tabella_attiva`, tradotto dal service: la tabella ora viene dalla sorgente e un indice non fa join |
| `codice_interno` che non è una sorgente, su una famiglia creata **spenta** (su un'attiva rifiuta prima il guard) | `E_VENDITE_VALIDATION` col campo `codice_interno` | `fk_famiglie_documento_sorgenti`, tradotto dal service |
| `codice_interno` duplicato | `E_VENDITE_DUPLICATO` | `uq_famiglie_documento_codice_interno`, tradotto dal service |
| `codice` duplicato | `E_VENDITE_DUPLICATO` | `uq_famiglie_documento_codice`, tradotto dal service col campo `codice` in modifica e `codice_interno` in creazione (il codice nasce dal codice interno) |

⛔ **I quattro codici dei guard NON si traducono nel service**: arrivano come
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
  passa gli argomenti **per nome** (`p_<campo> => %s`, da `_CAMPI_CREATE`): un
  parametro rinominato o ritirato nella madre è un errore SQL, non un valore
  finito nel parametro sbagliato.
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
- `config.sorgenti`, `config.fn_sorgente_tabella` — la sorgente della famiglia e la sua tabella
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
  `apps/vendite/tests/api/test_famiglie_api.py` (rotte, envelope del lookup e
  delle sorgenti)
- Frontend: `frontend/src/amministrazione/components/FamigliaDocumentoDrawer.vue`
  (in creazione sceglie la sorgente; `FamigliaDocumentoDrawer.spec.js`)
- Guida: [Numerazione dei documenti e codici](/guide/numerazione-documenti-e-codici)
