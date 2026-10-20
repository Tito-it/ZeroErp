# API — Magazzino: il documento interno e la consultazione

## Scopo

Il lato HTTP del **motore di magazzino** (Lotto 2): il **documento interno**
con cui una persona scrive sul registro — l'**inventario** (quanto c'è a
scaffale) e la **rettifica** (una correzione firmata) — la sua
**registrazione**, e la **consultazione** di ciò che il registro dice:
disponibilità e movimenti.

Le anagrafiche dello stesso dominio (magazzini, ubicazioni, lotti) hanno la
loro pagina: [api_anagrafiche_magazzino.md](api_anagrafiche_magazzino.md).

## Contesto

Area funzionale `magazzino` (`DomainAPIView`). Il perché di ogni scelta sta in
tre documenti che questa pagina non sostituisce:

| Documento | Che cosa contiene |
| --- | --- |
| [brief-db-magazzino-lotto-2-motore.md](../../../dev/work-done/brief-db-magazzino-lotto-2-motore.md) | il **modello**: la porta sul registro, la primitiva, le decisioni D-L2-* |
| [brief-db-magazzino-lotto-2-bis-be-fe.md](../../../dev/work-done/brief-db-magazzino-lotto-2-bis-be-fe.md) | ciò che il BE/FE ha chiesto al DB: la capability (R-1), i codici (R-2, R-6, R-7), l'azione `registra_magazzino` (R-3) |
| [piano-be-fe-magazzino-lotto-2-motore.md](../../../dev/work-done/piano-be-fe-magazzino-lotto-2-motore.md) | il piano BE/FE, le domande Q-1 … Q-5 decise da Tid |

```text
magazzino.inventari            la TESTATA: un magazzino, una data, uno stato
  └─ inventari_righe           la RIGA: una posizione contata (qta_contata >= 0)
magazzino.rettifiche           la TESTATA della correzione
  └─ rettifiche_righe          la RIGA: una correzione firmata (qta_delta <> 0) + motivo
magazzino.movimenti            il REGISTRO: lo scrive SOLO la registrazione, mai a mano
```

🔴 **Il backend è sottile per obbligo.** Le regole vivono nel database: la
matrice degli stati `DRAFT → CONFIRM → POSTED | CANCEL` (guard di transizione,
matrice in `magazzino.fn_documento_interno_transizioni`), il congelamento delle
righe fuori da `DRAFT` (guard di riga), la coerenza della riga con articolo,
lotto, seriale e ubicazione (`script.fn_check_riga_magazzino`), la
registrazione (`magazzino.fn_posta_inventario` / `fn_posta_rettifica`). Il
service valida la forma del payload, chiama, traduce. ⛔ Nessun «rifiuta con
`E_…`» qui sotto è scritto in Python, salvo dove è detto.

⭐ **Inventario e rettifica sono una famiglia, non due copie** (Q-1): le rotte,
il service e il repository nascono **una volta** dalla configurazione
`FamigliaDocumentoInterno` (`db/famiglie.py`), e le differenze sono tutte lì —
la quantità (`qta_contata` / `qta_delta`), il motivo (solo rettifica), la
descrizione di testata e il piano (solo inventario), il vincolo di posizione
unica (solo inventario). Nelle rotte sotto, `{famiglia}` è `inventari` o
`rettifiche`.

🔴 **Perimetro**: testate e righe hanno la **row security** sull'emittente del
magazzino. Un documento fuori perimetro è **404**, indistinguibile
dall'inesistente (no-leak). Le viste di consultazione sono `security_invoker`:
si leggono con la connessione dell'utente, mai da un canale di sistema.

Codice: `apps/magazzino/api/views.py` (`build_documento_interno_views`),
`services/magazzino_service.py`, `services/consultazione_service.py`,
`db/magazzino_repository.py`, `db/famiglie.py`, `types.py`.

## Regole che valgono su tutte le rotte

* **Liste offset-based** (`limit`/`offset`, `{count, results}`), la lingua di
  `<ListaConfigurabile>`. `order_by` fuori whitelist è un 400 col campo;
  senza `order_dir` le colonne data (riconosciute dal nome: `data`, `data_*`,
  `*_at`, …) partono `DESC`, la colonna di default segue il verso della lista;
  senza ordinamento decide il repository (per le testate `data DESC, id DESC`).
* **`search`**: sotto la soglia del catalogo della lista il termine è ignorato,
  mai un 400.
* **Ogni lista ha il suo export sorella** `…/export/?formato=csv|xlsx`, con gli
  stessi filtri e le colonne dalla preferenza della lista (`lista_codice` letto
  dalla view della lista, presidio `test_export_lista_codice_pari`).
* **Scritture con `Idempotency-Key` obbligatoria** (`POST`, `DELETE`); i `PATCH`
  no.
* **`articolo_id` è un UUID**: un valore che non lo è risponde 400 col campo,
  mai un errore del database (`articolo_uuid`).
* **Il codice di validazione del dominio** è `E_MAGAZZINO_VALIDATION`
  (`DATO_ERRATO`, col campo nel contesto): payload, query, e i vincoli FK/CHECK
  tradotti col loro campo.

## Endpoint — il documento interno

### 1. `GET /api/v1/magazzino/{famiglia}/`

Lista delle testate (catalogo `magazzino.inventari` 70 · `magazzino.rettifiche`
73). Filtri: `magazzino_id`, `stato` (`DRAFT | CONFIRM | POSTED | CANCEL`,
fuori vocabolario 400), `data_da`/`data_a`, `search`. Ordinamento in `DOCUMENTI_SORT_COLUMNS` (`data`,
`stato`, `magazzino_codice`, `magazzino_descrizione`, `descrizione`,
`righe_count`, `data_insert`, `user_insert`, `id`).

Riga (`DocumentoInternoRow`): `id`, `uid`, `data`, `stato` (grezzo: l'etichetta
è una chiave i18n del FE, nessuna tabella di stato a DB), `magazzino_id`,
`magazzino_codice`, `magazzino_descrizione`, `magazzino_usa_ubicazioni`,
`descrizione` (`null` sulla rettifica), `righe_count`, la sorgente, `meta`,
audit.

### 2. `POST /api/v1/magazzino/{famiglia}/`

Crea la **bozza**. Payload: `magazzino_id` (obbligatorio), `data` (default oggi,
a DB), `descrizione` (solo inventario), `meta`. Un magazzino inesistente, spento
o fuori perimetro è 400 col campo `magazzino_id`: è la traduzione di un dato di
form, prima che il DB risponda con una FK senza contesto. ⚠️ **Il magazzino si
sceglie qui e basta**: decide il perimetro e se le righe chiedono l'ubicazione,
e a DB è lucchettato (`E_MAG_DOCUMENTO_MAGAZZINO_IMMUTABILE`, R-4). Risposta: il
dettaglio.

### 3. `GET /api/v1/magazzino/{famiglia}/{id}/`

Il dettaglio: la riga della lista, più

* `famiglia` — il codice di URL;
* **`capabilities`** — il blob di `script.fn_available_actions_inventario` /
  `_rettifica`, **trasportato intatto** (R-1). Chiavi: `stato_codice`,
  `available_actions[]` (le transizioni richiedibili — `conferma`, `riapri`,
  `annulla` — ciascuna con `target_state`, `label_key`,
  `requires_confirm`, `enabled`, `reason`, `reason_key`, `manuale`; icona e
  colore li sceglie il frontend dal `key`), `can_change_state`,
  `can_edit_testata`, `can_edit_righe`, `can_delete`, la terna **`can_registra`
  · `can_registra_reason` · `can_registra_reason_key`**, e `stato_info_key`
  (la nota degli stati chiusi, `null` altrove);
* `piano_riepilogo` — solo inventario: `n_righe`, `n_con_delta`,
  `n_invariate`, `n_non_contate`, `n_non_postabili`.

⛔ Il backend non deduce niente di tutto questo: le azioni vengono dalla
matrice che il guard fa rispettare, la terna di «Registra» dal primo motivo
della check che le due `fn_posta_*` sollevano. `stato_info_key` sta **solo**
sotto `capabilities`. 404 `E_MAG_DOCUMENTO_NON_TROVATO`.

### 4. `PATCH /api/v1/magazzino/{famiglia}/{id}/`

La testata, per delta: `data`, `descrizione` (solo inventario; `null` la
toglie), `meta`. ⛔ Non lo stato (rotta 6), non il magazzino. ⚠️ **Nessun
vincolo di stato** (Q-2): il database non ne ha uno sulla testata, e il backend
non lo conia. A video il form è in sola lettura fuori da `DRAFT`. `data` decide
la data dei movimenti **alla registrazione**.

### 5. `DELETE /api/v1/magazzino/{famiglia}/{id}/`

Elimina una bozza. Fuori da `DRAFT` il DB risponde
`E_MAG_DOCUMENTO_NON_ELIMINABILE` (409). Risposta `{id, eliminato}`.

### 6. `POST /api/v1/magazzino/{famiglia}/{id}/stato/`

Payload `{"stato": "CONFIRM" | "CANCEL" | "DRAFT"}`. La matrice la applica il
guard: una transizione non ammessa è `E_MAG_DOCUMENTO_TRANSIZIONE_NON_AMMESSA`
(409). ⛔ **`POSTED` non si chiede qui**: è fuori vocabolario (400) prima di
arrivare al DB, dove prenderebbe `E_MAG_DOCUMENTO_POSTED_SOLO_DA_OPERAZIONE`,
un TECNICO. Risposta: il dettaglio.

### 7. `POST /api/v1/magazzino/{famiglia}/{id}/registra/`

🔴 **La registrazione: l'unico gesto irreversibile del dominio.** Una sola
`SELECT` su `fn_posta_<famiglia>`: il database è la transazione, e il service
non apre un `atomic()` attorno a una scrittura sola.

Il permesso è controllato **due volte**, e nessuna delle due è di troppo:
l'endpoint ha `post_permission = registra_magazzino` (area Magazzino,
`pericolosa`), e il verbo a DB lo richiede di nuovo come prima riga
(`script.fn_guard_azione`, [brief dei verbi](../../../dev/work-done/brief-db-magazzino-verbi-con-permesso.md)).
⚠️ Una riga a catalogo non è un permesso: finché l'azione non è assegnata a un
profilo, solo i super admin registrano (fail-closed).

I rifiuti vengono dalla check, nell'ordine: documento non in `CONFIRM`
(`E_MAG_DOCUMENTO_TRANSIZIONE_NON_AMMESSA`), senza righe
(`E_MAG_DOCUMENTO_SENZA_RIGHE`), una riga non postabile (**il codice della
riga**, cioè il primo motivo di `fn_check_riga_magazzino`: per esempio
`E_MAG_LOTTO_OBBLIGATORIO`, `E_MAG_UBICAZIONE_OBBLIGATORIA`,
`E_MAG_ARTICOLO_NON_GESTITO`). Rifiuta **tutto** il documento: nessun movimento
scritto, il documento resta in `CONFIRM`.

Risposta: `movimenti[]` (`movimento_id`, `riga_id`, `qta` **firmata**, il verso
della causale), `n_movimenti`, `documento` (il dettaglio, ora `POSTED`).

### 8. `GET /api/v1/magazzino/inventari/{id}/piano/` — solo inventario

Il **piano**: che cosa la registrazione scriverà, posizione per posizione
(`magazzino.fn_inventario_piano`, lista `magazzino.inventario_piano` 72).
Nessun vincolo di stato: in `DRAFT` è un'anteprima. Filtri: `search` (nessun
400 sotto soglia). Ordinamento in `PIANO_SORT_COLUMNS`; senza: articolo, poi la
catena della posizione (ubicazione, lotto, seriale).

Riga (`PianoRigaRow`): `chiave_riga` (`articolo|ubicazione|lotto|asset`, la
chiave per la lista: `riga_id` è `null` sulle non contate), `riga_id`,
articolo, ubicazione, lotto, seriale (id + codice), `qta_contata`,
`qta_sistema`, `delta`, `causale_codice_interno`, **`esito`**
(`INV_INIZIALE | RETT_POS | RETT_NEG | INVARIATA | NON_CONTATA |
NON_POSTABILE`), e la coppia **`posting_blocco_reason` ·
`posting_blocco_reason_key`**, valorizzata sulle `NON_POSTABILE` (api.md
§Capability di riga).

⭐ `NON_CONTATA` è merce **a registro** in una posizione che il conteggio non
ha nominato (D-L2-n): la registrazione la lascia com'è.

Export: `…/piano/export/`. Sulla rettifica la rotta non esiste.

### 9. `GET /api/v1/magazzino/{famiglia}/{id}/righe/`

Le righe della testata (liste `magazzino.inventario_righe` 71 ·
`magazzino.rettifica_righe` 74). `search` senza 400 sotto soglia; senza
ordinamento, l'ordine di digitazione (`id ASC`).

Riga (`RigaDocumentoInternoRow`): `id`, la FK col nome **fisico** della
famiglia (`inventario_id` / `rettifica_id`), articolo (`articolo_id`, codice,
descrizione, `articolo_requires_lotto`, `articolo_requires_serial`), la
quantità col nome fisico (`qta_contata` / `qta_delta`), `qta_sistema` (solo
inventario, la scrive la registrazione), `motivo` (solo rettifica),
`costo_unitario`, ubicazione, lotto, seriale (id + codice), `meta`, audit.

Export: `…/righe/export/`.

### 10. `POST /api/v1/magazzino/{famiglia}/{id}/righe/`

Payload: `articolo_id`, la quantità della famiglia (obbligatori, decimali
esatti), `motivo` (rettifica), `costo_unitario` (vuoto = alla media corrente del
registro), `ubicazione_id`, `lotto_id`, `asset_id`, `meta`. Fuori da `DRAFT` il
guard di riga risponde `E_MAG_DOCUMENTO_RIGHE_CONGELATE` (409).

⚠️ **La riga incoerente passa** (Q-3): senza lotto su un articolo che lo
chiede, o su un articolo non gestito a magazzino, la riga si salva in bozza — è
un fatto del conteggio — e il piano la dichiara `NON_POSTABILE`. Un rifiuto qui
sarebbe una regola più stretta del modello, scritta fuori dal DB. Il form la
mostra prima con la rotta 12.

Vincoli tradotti col campo: `qta_contata >= 0`, `qta_delta <> 0`, costo non
negativo, quantità unitaria con un seriale (`E_MAGAZZINO_VALIDATION`); due righe
d'inventario sulla **stessa posizione** (articolo, ubicazione, lotto, seriale)
sono `E_MAG_INVENTARIO_RIGA_POSIZIONE_DUPLICATA` col campo `articolo_id` (R-2).
⛔ La rettifica non ha il vincolo: due correzioni sulla stessa posizione sono
due fatti.

### 11. `PATCH` · `DELETE /api/v1/magazzino/{famiglia}/{id}/righe/{riga_id}/`

Parziale (`null` esplicito azzera un campo facoltativo: togliere il lotto). Il
guard risponde fuori da `DRAFT`. La coppia (documento, riga) è la risorsa: una
riga di un altro documento è 404 `E_MAG_DOCUMENTO_RIGA_NON_TROVATA` (R-7). Il
`PATCH` risponde con la riga; il `DELETE` (con `Idempotency-Key`) con
`{riga_id, eliminata}`.

### 12. `GET /api/v1/magazzino/righe/motivi/`

L'**anteprima** del form di riga: `script.fn_check_riga_magazzino` così com'è,
la stessa funzione che il piano e la primitiva usano — ciò che si vede è ciò che
verrà scritto. Parametri: `magazzino_id`, `articolo_id` (obbligatori),
`lotto_id`, `asset_id`, `ubicazione_id`. Risposta `{"motivi": [...]}`; `[]` =
nessun motivo. Il frontend la tratta come best-effort: non blocca il salvataggio.

## Endpoint — i lookup del form di riga

Envelope `{"results": [...]}` (api.md §L'envelope di un lookup). ⛔ Sono
lookup **dedicati**, dentro l'area `magazzino`, e non il lookup generico: il
filtro per padre non è nel suo contratto.

| # | Rotta | Che cosa |
| --- | --- | --- |
| 13 | `GET /api/v1/magazzino/magazzini/{id}/ubicazioni/lookup/` | le ubicazioni **attive** del magazzino |
| 14 | `GET /api/v1/magazzino/lotti/lookup/?articolo_id=&search=` | i lotti **attivi** dell'articolo (`articolo_id` obbligatorio) |
| 15 | `GET /api/v1/magazzino/assets/lookup/?articolo_id=&magazzino_id=` | i seriali **attivi** dell'articolo, dell'emittente del magazzino (entrambi obbligatori) |

Il picker dell'**articolo** non è qui: è il lookup del catalogo col filtro
`gestito_a_magazzino` (R-5, [api_catalogo.md](../../catalogo/manual/api_catalogo.md)),
che il form di riga chiama con i soli articoli gestiti.

## Endpoint — la consultazione

Sola lettura per costruzione: sul registro si scrive solo dalla porta
(`fn_scrivi_movimento`), che l'app non può chiamare.

### 16. `GET /api/v1/magazzino/disponibilita/`

Per (articolo, magazzino), da `vw_disponibilita` (lista
`magazzino.disponibilita` 75). Filtri: `magazzino_id`, `articolo_id`,
`solo_negativa` (disponibile sotto zero: le promesse che una rettifica ha reso
non più mantenibili, D-L2-d), `solo_con_giacenza`, `search`. Ordinamento in `DISPONIBILITA_SORT_COLUMNS`; senza: articolo,
magazzino.

Riga: `chiave_riga` (`articolo|magazzino`), articolo (con `requires_lotto` /
`requires_serial`), magazzino, `giacenza`, **`bloccata` (negativa)**,
`disponibile`, `n_blocchi`. ⭐ `disponibile = giacenza + bloccata`: la formula
è **in colonne** nella vista, il backend non somma niente.

Export: `…/disponibilita/export/`.

### 17. `GET /api/v1/magazzino/disponibilita/articoli/`

Per articolo, somma sui magazzini visibili (`vw_disponibilita_articolo`, lista
`magazzino.disponibilita_articoli` 76, colonne sue). Stessi filtri meno
`magazzino_id`; riga con `n_magazzini`. Export: `…/articoli/export/`.

### 18. `GET /api/v1/magazzino/disponibilita/blocchi/?articolo_id=&magazzino_id=`

Il drill-down di `n_blocchi` (D-L2-j): gli attesi `APERTA` **in uscita** su
(articolo, magazzino), con quantità, data prevista, causale, sorgente, soggetto
decodificato e nota. Non paginato: `{"results": [...]}`.

### 18-bis. `POST /api/v1/magazzino/disponibilita/blocchi/` — apri un blocco manuale

Il blocco manuale (Lotto 3): una promessa di merce, scritta dal verbo
`magazzino.fn_apri_blocco` con una sola `SELECT`. Permesso `blocca_merce`
(`post_permission`, richiesto di nuovo dal verbo a DB), `Idempotency-Key`
obbligatoria.

Corpo: `magazzino_id`, `articolo_id` (UUID), `qta` (decimale) obbligatori;
`soggetto_ruolo_id`, `nota`, `lotto_id`, `asset_id`, `ubicazione_id`
facoltativi. Risposta `{"blocco_id": n}`. Payload malformato: 400
`E_MAGAZZINO_VALIDATION` col campo; i rifiuti di merito sono i codici del verbo.

### 18-ter. `POST /api/v1/magazzino/disponibilita/blocchi/{blocco_id}/libera/`

Libera il blocco (verbo `magazzino.fn_libera_blocco`: autore, momento, nota).
Stesso permesso `blocca_merce`, `Idempotency-Key` obbligatoria. Corpo
`{"nota": "…"}` (facoltativa). Risposta `{"blocco_id": n, "liberato": true}`.
Un blocco inesistente o già liberato risponde col codice del DB.

### 19. `GET /api/v1/magazzino/movimenti/`

Il registro (lista `magazzino.movimenti` 77). Filtri: `magazzino_id`,
`articolo_id`, `causale_id`, `data_da`/`data_a` (su `data_mov`, giorni **dell'azienda** (fuso `SYSTEM_FUSO_ORARIO`, confini calcolati dal DB col BB `predicato_giorno_operativo`, dal 2026-10-09), `data_a` incluso; il floor
standard lo applica il frontend), `sorgente_tipo` (`config.sorgenti.codice_interno`:
`INVENTARIO_RIGA`, `RETTIFICA_RIGA`, …), **`inventario_id` / `rettifica_id`**
(i movimenti nati dalle righe di quel documento: è il deep-link dal documento
`POSTED`), `search`. Senza ordinamento: `data_mov DESC, id DESC`.

Riga (`MovimentoRow`): `id`, `data_mov`, articolo, magazzino, `qta` (firmata),
`costo_unitario`, causale (`codice`, `descrizione`, `segno`), ubicazione, lotto,
seriale, sorgente (`sorgente_codice_interno`, `sorgente_riga`, `sorgente_uid`),
`transfer_uid`, `storno_di_movimento_id`, audit.

Export: `…/movimenti/export/`.

## Codici errore

| codice | classe | quando |
| --- | --- | --- |
| `E_MAGAZZINO_VALIDATION` | DATO_ERRATO | payload o query rifiutati dal BE, FK/CHECK tradotti — col campo (R-6) |
| `E_MAG_DOCUMENTO_NON_TROVATO` | NON_TROVATO | la testata non c'è o è fuori perimetro (404 no-leak) |
| `E_MAG_DOCUMENTO_RIGA_NON_TROVATA` | NON_TROVATO | la riga non c'è, o è di un altro documento (R-7) |
| `E_MAG_DOCUMENTO_TRANSIZIONE_NON_AMMESSA` | CONFLITTO_STATO | la matrice non ammette il passaggio; anche «registra» fuori da `CONFIRM` |
| `E_MAG_DOCUMENTO_RIGHE_CONGELATE` | CONFLITTO_STATO | scrivere una riga fuori da `DRAFT` |
| `E_MAG_DOCUMENTO_NON_ELIMINABILE` | CONFLITTO_STATO | eliminare fuori da `DRAFT` |
| `E_MAG_DOCUMENTO_MAGAZZINO_IMMUTABILE` | CONFLITTO_STATO | cambiare il magazzino dopo la nascita (R-4; il BE non lo manda mai) |
| `E_MAG_DOCUMENTO_SENZA_RIGHE` | NON_ESEGUIBILE | registrare un documento vuoto |
| `E_MAG_INVENTARIO_RIGA_POSIZIONE_DUPLICATA` | DATO_ERRATO | stessa posizione due volte nell'inventario, campo `articolo_id` (R-2) |
| `E_PERMESSO_NEGATO` | NON_PERMESSO | registrare senza l'azione `registra_magazzino`; aprire o liberare un blocco senza `blocca_merce` |
| i codici della riga | DATO_ERRATO | alla registrazione, il primo motivo di `fn_check_riga_magazzino` (`E_MAG_LOTTO_OBBLIGATORIO`, `E_MAG_UBICAZIONE_OBBLIGATORIA`, `E_MAG_ARTICOLO_NON_GESTITO`, …): passano **com'è**, con la frase e il campo del catalogo |
| `E_MAG_DOCUMENTO_POSTED_SOLO_DA_OPERAZIONE` | TECNICO | la porta `POSTED` aperta fuori dal verbo: dall'API non si raggiunge (rotta 6) |

## Presidi

`apps/magazzino/tests/services/test_magazzino_service.py` (unit, mock del
repository), `tests/api/test_magazzino_api.py` (rotte, parametri, gate di
`registra/`, coppie lista/export), `tests/db/test_documento_interno_db.py` (DB
provvisto: la catena del primo carico, la capability che segue la matrice del
guard, i tre motivi di «Registra» spento, il duplicato di posizione, il pinning
dei **nomi** del blob), `tests/db/test_stati_documento_interno.py` (il
vocabolario degli stati pinnato sul `CHECK`). Smoke:
`backend/scripts/tests/smoke-magazzino-inventario-primo-carico.py` (12 passi,
rollback; prova anche il verbo dal percorso reale come `zeroerp_app`).
Trasversali: `test_liste_configurabili_seed`, `test_perimetro_emittente_copertura`,
`test_export_lista_codice_pari`.

⚠️ Il frontend della barra del drawer non ha un test che la monti: regge sul
pinning dei nomi lato BE e sul
[collaudo a video](../../../dev/work-in-progress/collaudo-in-app-magazzino-inventario-e-rettifica.md).
