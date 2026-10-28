# API DDT di vendita `vendite.ddt`

## Scopo

CRUD operativo dei **DDT di vendita** (documenti di trasporto), gemello
strutturale di [api_ordini.md](api_ordini.md) (D-4: stessa impronta, logica
DDT). Espone testata trasporto, **righe** con **componenti BoM**, **emissione**
(`DRAFT -> EMESSO`, numero assegnato dal trigger a EMESSO — C6), cambio stato
data-driven, **push singolo a commessa** (fatturazione differita), lista
configurabile + export, note partizionate, **riepilogo IVA** e **indirizzi
documento**. L'evasione (genera DDT da ordine) vive sul dominio ORDINE:
`POST /api/v1/vendite/ordini/<id>/genera-ddt/`.

> Stato: BE completo (brief-be-ddt-vendita + slice riepilogo IVA/indirizzi
> 2026-07-11/12). Per il modello e la state machine
> (DRAFT→EMESSO→SPEDITO→CONSEGNATO→RESO, +ANNULLATO) vedi
> [brief-db-ddt-vendita-evasione-e-stati.md](../../../dev/work-done/brief-db-ddt-vendita-evasione-e-stati.md).

## Endpoints

Convenzioni identiche ad api_ordini.md (envelope, lista configurabile
`vendite.ddt`, export via `ListaExportService`, note via
`PartitionedNoteRepository`, documenti/stampa via factory
`build_documenti_sorgente_views` sorgente `DDT_VENDITA`). Permesso: area
`vendite` + `model_permission = ("vendite", "ddt")` su tutte le view. Emissione e
cambio stato non dichiarano l'azione: la legge la catena dei permessi dalla **riga
del passaggio** della matrice (`post_passaggio`, guida del modello §6) e risponde
403 prima della transazione; il verbo la ricontrolla. Oggi la chiedono emissione e
annullo di una bolla emessa (`emetti_ddt`); gli altri passaggi chiedono il livello
sul documento.

⛔ **Corpo a whitelist chiusa** ovunque (testata, righe, componenti, prelievi):
una chiave fuori contratto è `400 E_DDT_VALIDAZIONE` con le chiavi ignote
(`unknown_keys`), `utility_id` compresa (sui prelievi dal 2026-10-20; prima si
scartava in silenzio).

- Lista `GET /api/v1/vendite/ddt/` — filtri: `stato_codice_interno`,
  `billing_account_id`, `utility_id`, `data_da`/`data_a` (nessun default
  backend: il default anno-1 lo mette la UI), `search` (min 3:
  numero/destinatario/ba_codice/id fiscale); paginazione `limit`/`offset`,
  `order_by`/`order_dir` (default `data` DESC; colonne data senza `order_dir`
  → DESC). `stato_codice_interno` fuori da `config.stati_doc_ddt` → `400
  E_DDT_VALIDAZIONE` col campo (2026-10-20; prima lista vuota). Scope emittente
  (RLS + filtro applicativo; cancello perimetro → possibile `422
  E_UI_LISTA_EMITTENTE_DA_SCEGLIERE`).
- Export `GET /api/v1/vendite/ddt/export/?formato=csv|xlsx` — stessi filtri e ordinamento.
- Form-defaults `GET /api/v1/vendite/ddt/form-defaults/`.
- Create `POST /api/v1/vendite/ddt/` — chiavi ammesse (`CREATE_KEYS_DDT`):
  `billing_account_id`, `destinatario_soggetto_ruolo_id`, `emittente_fiscale_id`,
  `valuta_id`, `mittente_soggetto_ruolo_id`, `vettore_soggetto_ruolo_id`,
  `causale_trasporto_id`, `aspetto_bene_id`, `modalita_addebito_trasporto_id`,
  `num_colli`, `peso_lordo`, `peso_netto`, `volume`, `targa`, `autista`,
  `tracking_code`, `data`, `meta`, `magazzino_id`, `magazzino_arrivo_id`,
  `fatturazione_immediata`. Il cliente (`billing_account_id`) e'
  **facoltativo** (brief-db-esecutivi-ba-coppia D-2, 2026-10-10): lo pretende
  l'**emissione** quando la causale manda merce a un cliente
  (`config.causali_trasporto.richiede_cliente`: vendita, omaggio, campionatura,
  conto visione) → 409 `E_DDT_CLIENTE_OBBLIGATORIO`, capability con reason
  `CLIENTE_MANCANTE`. Col BA, `destinatario_soggetto_ruolo_id` e `utility_id`
  sono copie del BA e le scrive `trgfn_ddt_normalize` (BB
  `script.fn_cliente_dal_billing_account`): un destinatario diverso e' 400
  `E_DOC_CLIENTE_DIVERSO_DA_BA`, la `utility_id` non e' nel contratto (`400
  E_DDT_VALIDAZIONE`). Senza BA il destinatario (terzista, deposito) e' **obbligatorio**:
  il NOT NULL del DB, 400 col campo. L'emittente, se omesso, il trigger lo
  risolve dal BA. Stato iniziale
  DRAFT, `numero` NULL fino a EMESSO. **Auto-assegnazione indirizzo** (UX v2):
  alla creazione (standalone ed evasione, se la cascata non l'ha gia' portato)
  lo slot Consegna viene valorizzato best-effort dall'indirizzo di RUOLO del
  cliente (CON, fallback FATT); mai bloccante.
- Detail `GET /api/v1/vendite/ddt/<id>/` — testata + capabilities data-driven
  (`fn_available_actions_ddt`) nella chiave `capabilities`, non fuse nella
  testata (api.md §«Il blob sta SOTTO `capabilities`», 2026-09-23). Accanto,
  `contatori` (dal 2026-10-25): `{"note": <n>}`, il numero sul pulsante «Gestisci note» del drawer, dal BB `contatori_documento` — contato **dopo** il cancello di testata, con lo stesso perimetro della lista note. Forma e ragioni in [api_fattura_dettaglio §`contatori`](/backend/vendite/manual/api_fattura_dettaglio).
- Update `PATCH /api/v1/vendite/ddt/<id>/` — in bozza tutti i campi; quali colonne si cambiano fuori bozza lo dice il lock di testata del DB (`trgfn_doc_testata_lock_fuori_bozza`, dal 2026-10-10, [brief-db-testata-dopo-emissione](/dev/work-done/brief-db-testata-dopo-emissione)); il 409 del lock (`E_DOC_*`) passa com'e': a bolla emessa restano aperti trasporto, tracciamento e note (D-0, D-1), fermi a bolla resa o annullata. Cliente e
  destinatario **si scelgono in bozza** (`billing_account_id`,
  `destinatario_soggetto_ruolo_id`; `utility_id` ed `emittente_fiscale_id`
  fuori contratto → 400). Corpo senza campi → 400. Risposta `{ddt_id, updated}`: al cambio di
  BA il destinatario non inviato segue il BA nuovo, un BA tolto toglie la
  utility e lascia il destinatario. Fuori bozza li blocca il DB
  (`trg_ddt_a05_lock_fuori_bozza_upd`: 409 `E_DDT_CLIENTE_IMMUTABILE`). Fino al
  2026-10-10 il service rifiutava il cambio di BA anche in bozza.
- Delete `DELETE /api/v1/vendite/ddt/<id>/` — hard delete solo DRAFT **e senza
  righe** (pattern abbandono bozza); altrimenti `409 E_DDT_STATO_TRANSIZIONE`
  (con righe si annulla, non si cancella). Risposta `{ddt_id, deleted}`.
- Riepilogo IVA `GET /api/v1/vendite/ddt/<id>/riepilogo-iva/` — lettura pura
  da `vendite.vw_ddt_riepilogo_iva_dettaglio` (ROUND 2 per aliquota, DPR
  633/72 art. 21; righe con `prezzo_unitario` NULL escluse: DDT solo di
  trasporto → riepilogo vuoto). Shape identico a ordini
  ([api_ordini.md](api_ordini.md) §Riepilogo IVA).
- Indirizzi `GET/POST /<id>/indirizzi/` + `DELETE /<id>/indirizzi/<iid>/` —
  BB condiviso, vedi [api_indirizzi_documento.md](api_indirizzi_documento.md).
  Ambito `DDT`: solo `CON` (consegna), **obbligatorio all'emissione** (guard
  DB `E_INDIRIZZO_DOC_OBBLIGATORIO`).
- Emetti `POST /api/v1/vendite/ddt/<sorgente_id>/emetti/` (multipart) —
  DRAFT→EMESSO + genera PDF accompagnatorio + allegati, atomico (factory
  documenti). Il trigger assegna `numero` e valida componenti BoM + indirizzi
  obbligatori. È **l'unica strada** verso EMESSO (M-2).
- Cambia stato `POST /api/v1/vendite/ddt/<id>/cambia-stato/` — body
  `{stato_codice}` (matrice `config.transizioni_stati_ddt`). Risposta
  `{ddt_id, stato_precedente, stato, movimenti_scritti}` (`movimenti_scritti`
  = movimenti di magazzino scritti dal verbo se la bolla muove merce; assente
  sull'annullo). Stato mancante o non configurato → `400 E_DDT_VALIDAZIONE`;
  `EMESSO` → `400 E_DDT_VALIDAZIONE` (si emette solo da «Emetti»); un passaggio di
  processo (`RESO`) → `E_DOC_PASSAGGIO_DI_PROCESSO`. Verso `ANNULLATO`
  passa sempre dal verbo `vendite.fn_annulla_ddt`: su una bolla con legami
  (ordini, resi, righe di commessa da emettere) risponde
  `E_DOC_ANNULLO_CON_LEGAMI` (409, `confirm_and_retry`) finché il body non
  dichiara `legami_confermati`, il numero letto da `…/legami/`. Confermato, i
  legami si ritirano (ordine da evadere, reso da ri-consegnare).
- Legami `GET /<id>/legami/` (factory `build_legami_view`, BB
  `_annullo_con_legami.legami_del_documento`): `{documento, id, legami, righe}`,
  una riga per legame di `vendite.fn_documento_legami` con `origine` (codice di `config.sorgenti`), `natura`
  (CONSUMO/PROVENIENZA), `origine_id` e il nome del documento dall'altra parte
  dal lineage (`origine_tipo_codice_interno`, `origine_codice`). `legami` e' il
  numero da dichiarare. Alimenta la finestra di conferma dell'annullo.
- Push `POST /api/v1/vendite/ddt/<id>/push/` — push singolo a commessa
  (sorgente `DDT_VENDITA`, fatturazione differita). DDT senza righe eleggibili
  → `409 E_DDT_NESSUNA_RIGA`.
- Lista configurabile delle righe `GET /<id>/righe/lista/` (+ `export/`): BB condiviso, vedi [api_righe_documento.md](api_righe_documento.md).
- Righe `GET/POST /<id>/righe/`, `PATCH/DELETE /<id>/righe/<riga_id>/` — solo
  DRAFT; `prezzo_unitario`/`iva_id` nullable (DDT anche solo di trasporto).
  ⛔ Una chiave fuori whitelist è un `400 E_DDT_VALIDAZIONE` con le chiavi ignote
  (`unknown_keys`), sulla testata come sulle righe (dal 2026-10-19; prima si
  scartava in silenzio). In creazione della riga è ammessa anche
  `componenti_overrides`; `iva_id` non si manda: l'aliquota la decide il
  risolutore.
  ⭐ **Il DDT è l'unico documento dove il prezzo mancante non è un errore**:
  vedi la sezione dedicata più sotto.
  Sulla riga **evasa** (`evasa = true` nella lista: legata a una riga d'ordine o
  di reso) articolo, UoM e quantità sono fermi (`E_DDT_RIGA_EVASA_FERMA`); in
  bozza la DELETE riesce e ritira i legami.
- Quantità evasa `POST /<id>/righe/<riga_id>/qta-evasa/` — body
  `{qta_operativa}`; verbo `vendite.fn_ddt_riga_correggi_qta_evasa`: riga,
  legami e stato dell'ordine insieme. Il pulsante segue
  `correggi_qta_evasa_blocco` della riga (`NULL` = acceso). Oltre il residuo:
  `E_QTA_SUPERA_RESIDUO`.
- Componenti BoM `GET /<id>/righe/<rid>/componenti/` +
  `PATCH/DELETE .../componenti/<cid>/` + preview — mixin condiviso. PATCH:
  un `prezzo_unitario` non nullo richiede l'azione `prezzo_override_manuale`
  (`403 E_PRICING_OVERRIDE_NON_AUTORIZZATO`); `null` no (torna al risolutore).
- Prelievi (Lotto 3, magazzino):
  - `GET /<id>/prelievi/` — testata (`ddt_id`, `muove_merce`, `magazzino_id`,
    `magazzino_usa_ubicazioni`, `magazzino_arrivo_id`,
    `magazzino_arrivo_usa_ubicazioni`) + `voci[]`: ogni voce da movimentare
    (riga o componente del kit: `ddt_riga_id`, `ddt_riga_componente_id`,
    `riga_nr`, articolo, `requires_lotto`/`requires_serial`, `uom_codice`,
    `qta`, `prelevata`, `automatico`) con i suoi `prelievi[]` (`id`, `qta`,
    `lotto_id`/`lotto_codice`, `asset_id`/`asset_seriale`,
    `ubicazione_id`/`_codice`, `ubicazione_arrivo_id`/`_codice`). Sola lettura.
  - `POST /<id>/righe/<rid>/prelievi/` — corpo `qta` (obbligatoria),
    `ddt_riga_componente_id`, `lotto_id`, `asset_id`, `ubicazione_id`,
    `ubicazione_arrivo_id` (id interi positivi). Risposta `{ddt_id, riga_id, prelievo_id}`.
  - `PATCH /<id>/righe/<rid>/prelievi/<pid>/` — `asset_id`, `lotto_id`, `qta`,
    `ubicazione_arrivo_id`, `ubicazione_id`; `DELETE` stesso path. Il prelievo
    deve essere della riga dell'URL, altrimenti `404 E_DDT_NOT_FOUND`.
  - Chiavi estranee → `400 E_DDT_VALIDAZIONE`; le regole (bozza, kit,
    ubicazioni, lotto/seriale) sono dei trigger DB (`qta` ≤ 0, non numerica, o
    ≠ 1 su un seriale → `400 E_VENDITE_VALIDATION` col campo).
- Note `GET/POST /<id>/note/` + `GET/PATCH/DELETE /<id>/note/<note_id>/` —
  building block, contratto comune in [api_note_documento](../../core/manual/api_note_documento.md)
  (partizione `vendite.note_ddt`, `target_tipo='DDT_VENDITA'`).
- Documenti/Stampa `…/<id>/documenti/…` — vedi api_ordini.md §Documenti.

### Lineage / genealogia (brief-be-fe-lineage, 2026-07-15)

- **Colonne lineage in lista** (Fase B): la lista espone anche `fase`
  (proiezione normalizzata dallo stato), `pratica_id`/`pratica_numero`/
  `n_pratiche` (pratica collegata), `frontiera_tipo_id` +
  `frontiera_tipo_codice_interno` e `frontiera_natura_doc_codice_interno`
  (dalla vista, non piu' decodificati dal repository: changeSet `20260829-01/02`
  — ⛔ il nome e' cambiato, e con lui la sorgente),
  `frontiera_codice`/`frontiera_stato_codice_interno`/`frontiera_fase`,
  `n_discendenti_attivi`, `is_transitato` — dalla vista canonica estesa
  (LEFT JOIN `vendite.vw_documento_lineage`). Colonne configurabili
  `pratica`/`fase`/`transito` visibili di default (seed preset). `order_by`
  accetta anche `pratica_numero` e `fase` (la frontiera NON e' ordinabile).
- **Passaggi** `GET /api/v1/vendite/ddt/<id>/passaggi/` — genealogia del
  documento: pratica + frontiera + catena transiti in entrambe le direzioni.
  Contratto completo nel manuale del BB condiviso:
  [api_lineage_passaggi.md](api_lineage_passaggi.md).

## Righe senza prezzo — il campo `prezzo_esito`

⭐ **Il DDT è l'unico documento dove il prezzo mancante non è un errore.** Una
riga in conto visione, un reso in ri-consegna, un articolo fuori listino: sono
casi legittimi, e pretendere il prezzo significherebbe impedire di salvare la
riga. Ordini, preventivi, contratti e offerte continuano invece a **rifiutare**
la riga: lì il prezzo assente è un difetto.

### Cosa risponde `POST /api/v1/vendite/ddt/{id}/righe/`

Quando il prezzo non è passato dal client, il BE lo risolve. Se **non** è
risolvibile, la riga **si salva lo stesso** con `prezzo_unitario = null`, e la
risposta porta il motivo:

```json
{ "data": { "ddt_id": 12, "riga_id": 31, "is_composito": false,
            "prezzo_esito": { "codice": "E_CATEGORIA_LISTINO_NON_MAPPATA",
                              "messaggio": "Categoria cliente non mappata a listino per la quadrupla indicata." } } }
```

Quando il prezzo si risolve, `prezzo_esito` è `null`.

| | |
|---|---|
| **dov'è** | dentro `data`, **non** nell'envelope degli errori: la riga è stata salvata, quindi non è un fallimento (DEC-3) |
| **il testo** | è il messaggio a catalogo del codice, **senza segnaposto** — il FE lo mostra, non lo riscrive e non ne tiene una copia i18n (DEC-4) |
| **persistenza** | il motivo resta anche dopo il ricarico: sta in `ddt_righe.meta.prezzo_resolver_context.esito_codice`, stesso nome della colonna che il DB usa sui componenti (DEC-8) |

⛔ **`importo_riga` esce `null`, non `0`.** La lista righe non fa più
`COALESCE(prezzo, 0)`: uno zero sarebbe indistinguibile da una riga che vale
davvero zero, e il totale del documento tornerebbe «giusto» sommando quel che
non c'è.

⛔ **Il padre di un kit si inserisce con prezzo `null`**, non `0`: il ricalcolo
lato DB mette `NULL` se anche un solo figlio è scoperto.

### Cosa serve al client per decidere

`GET /api/v1/vendite/ddt/{id}/` espone **`causale_trasporto_fatturabile`**:

* `true` — il documento vende: una riga senza prezzo bloccherà l'emissione;
* `false` — non vende (conto visione, ri-consegna): il prezzo assente è normale;
* `null` — **causale non ancora scelta**, che è un terzo caso e non un `false`.

Il BE non fa `COALESCE(false)` di proposito: al client serve distinguere «non
vende» da «non lo so ancora» (DEC-5).

Riferimento: `docs/it/dev/work-done/brief-ddt-righe-senza-prezzo.md`.

## Codici errore principali

`E_DDT_NOT_FOUND` (404), `E_DDT_VALIDAZIONE` (400), `E_DDT_STATO_TRANSIZIONE`
(409, la testata), `E_DDT_CLIENTE_OBBLIGATORIO` (409, emissione senza cliente
con una causale che lo vuole), `E_DDT_CLIENTE_IMMUTABILE` (409, cliente fuori
bozza), `E_DOC_CLIENTE_DIVERSO_DA_BA` (400, destinatario diverso dal BA),
`E_DOC_CLIENTE_DIVERSO_DA_SORGENTE` (400, BA diverso da quello dell'ordine o
del reso da cui la bolla nasce), `E_DOC_SORGENTE_NON_TROVATA` (400, sorgente
inesistente o di un'altra azienda), `E_DOC_EMITTENTE_FUORI_BOZZA` (409), `E_RIGA_DOC_NON_BOZZA` (409: righe e componenti solo in
bozza — dal 2026-09-22 lo stesso codice del BB a DB
`trgfn_doc_righe_lock_fuori_bozza`, che il pre-check BE `richiedi_righe_in_bozza`
solleva con la frase a catalogo),
`E_STATO_DDT_TRANSIZIONE_NON_VALIDA` (matrice), `E_QTA_SUPERA_RESIDUO`
(evasione), `E_INDIRIZZO_DOC_OBBLIGATORIO` (emissione senza CON),
`E_TIPO_INDIRIZZO` (whitelist), `E_INDIRIZZO_SNAPSHOT_NOT_FOUND` (404),
`E_DDT_NESSUNA_RIGA` (409, push senza righe eleggibili), `E_VENDITE_DUPLICATO`
(409, vincolo unico), `E_VENDITE_FK` (400, riferimento non valido: articolo,
cliente, destinatario, IVA, emittente), `E_VENDITE_VALIDATION` (400, ripiego
dei vincoli DB non mappati e regole dei prelievi), `E_PERMESSO_NEGATO` (403,
permesso di processo verificato dal DB nel cambio stato),
`E_PRICING_OVERRIDE_NON_AUTORIZZATO` (403, prezzo manuale sul componente),
`E_DOC_STATO_SOLO_DAL_VERBO` e `E_DOC_PASSAGGIO_DI_PROCESSO` (TECNICI: lo stato
scritto senza il verbo, un passaggio di processo chiesto a mano).

## Riferimenti

- Service: `apps/vendite/services/ddt_service.py` · Repo:
  `apps/vendite/db/ddt_repository.py` (mixin componenti + riepilogo IVA +
  indirizzi) · Views: `apps/vendite/api/views_ddt.py` + `ddt_documenti_views.py`
  · URLs: `urls_ddt.py`.
- FE: `frontend/src/vendite/ddt/` (lista, drawer, evasione dal drawer ordine).
