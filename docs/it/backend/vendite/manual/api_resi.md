# API Resi di vendita `vendite.reso`

## Scopo

Motore **resi di vendita su DDT**: il reso NASCE solo da un DDT **CONSEGNATO**
(pannello nel drawer DDT), mai standalone. Clone strutturale ridotto di
[api_ddt.md](api_ddt.md): niente componenti BoM / PDF / push / note / riepilogo
IVA / indirizzi in questa slice. Le azioni di dominio (conferma, annullo,
generazione DDT di ri-consegna) hanno effetti applicati dalle **fn madri DB** —
nessun cambia-stato generico. Espone la lista configurabile + export e le **due
code di lavoro** (da accreditare / da ri-consegnare), anch'esse liste
configurabili con export.

> **Dal 2026-08-18 espone anche il verbo dell'ACCREDITO** (la nota di credito
> sui resi): vedi la sezione dedicata più sotto e
> [brief-design-note-credito-resi.md](../../../dev/work-done/brief-design-note-credito-resi.md).
>
> Stato: BE completo. Modello e state machine (DRAFT→CONFERMATO, +ANNULLATO),
> residuo ordine, flip DDT→RESO: vedi
> [brief-db-resi-vendita.md](../../../dev/work-done/brief-db-resi-vendita.md).
> Code configurabili + export: vedi
> [brief-be-fe-resi-code-configurabili.md](../../../dev/work-done/brief-be-fe-resi-code-configurabili.md).

## Endpoints

Convenzioni identiche ad api_ddt.md (envelope standard, lista configurabile,
export via `ListaExportService`, scope emittente RLS + filtro applicativo).

### Lista + testata

- Lista `GET /api/v1/vendite/resi/` — lista configurabile `vendite.resi`. Filtri:
  `stato_codice_interno` (DRAFT|CONFERMATO|ANNULLATO; fuori vocabolario
  `config.stati_doc_reso` → 400 `E_RESO_VALIDAZIONE` col campo, 2026-10-20: prima
  lista vuota con 200), `billing_account_id`, `data_da/data_a`, `search` (min 3:
  numero/destinatario/ba_codice/id fiscale/DDT origine), `order_by` (`numero`,
  `data` default, `anno`, `destinatario_denominazione`, `ba_codice`,
  `id_fiscale_univoco_cf_piva`, `stato_descrizione`, `ddt_origine_numero`,
  `data_insert`, `pratica_numero`, `fase`) / `order_dir` (assente: `desc` sul
  default `data`, «dal più recente»).
- **Export** `GET /api/v1/vendite/resi/export/?formato=csv|xlsx` — stessi
  filtri/sort della lista; colonne visibili/ordine/permessi dalla config
  `vendite.resi`. Fetch fino a `EXPORT_MAX_ROWS+1` (nessun troncamento silenzioso;
  oltre soglia → `E_UI_EXPORT_LIMIT_EXCEEDED`).
- Create `POST /api/v1/vendite/resi/` — `{ddt_id, data?, magazzino_id?, meta?, righe?}`
  (`righe` = lista di corpi riga, vedi §Righe). Nasce DRAFT, `numero` NULL fino a
  CONFERMATO (trigger). BA/destinatario/utility/valuta/emittente ereditati dal
  DDT sorgente (**CONSEGNATO**, guard DB). `magazzino_id` = magazzino di rientro
  della merce. Una chiave fuori contratto → 400 `E_RESO_VALIDAZIONE` (2026-10-20:
  prima scartata in silenzio).
- Detail `GET /<id>/` — testata + capabilities data-driven
  (`fn_available_actions_reso`) nella chiave `capabilities`, non fuse nella
  testata (api.md §«Il blob sta SOTTO `capabilities`», 2026-09-23).
- Update `PATCH /<id>/` — `data`/`meta`/`magazzino_id` (altre chiavi → 400
  `E_RESO_VALIDAZIONE`; `{}` → 400), risposta `{reso_id, updated}`; quali colonne si cambiano fuori bozza lo dice il lock di testata del DB (`trgfn_doc_testata_lock_fuori_bozza`, dal 2026-10-10, [brief-db-testata-dopo-emissione](/dev/work-done/brief-db-testata-dopo-emissione)); il 409 del lock (`E_DOC_*`) passa com'e': a reso confermato restano aperte le note, ferme a reso annullato. Delete `DELETE /<id>/` — hard
  delete solo DRAFT + 0 righe (abbandono bozza; con righe 409
  `E_RESO_STATO_TRANSIZIONE`), risposta `{reso_id, deleted}`.

### Azioni di dominio (fn madri DB, effetti atomici)

- Conferma `POST /<id>/conferma/` — DRAFT→CONFERMATO: numero dal trigger,
  riapertura residuo ordine, proiezione stato ordine, flip DDT→RESO se reso totale.
- Annullo `POST /<id>/annulla/` — storna gli effetti post-conferma; bloccato se
  già ri-spedito (`E_RESO_ANNULLO_CON_RICONSEGNE`).
- Permesso di conferma e annullo: l'azione la dice la **riga del passaggio**
  (`post_passaggio`, guida del modello §6), letta dallo stato corrente; 403 prima
  della transazione, e il verbo la ricontrolla. Oggi `conferma_reso` per la
  conferma e per l'annullo di un confermato; l'annullo di una **bozza** chiede il
  solo livello sul documento (M-4).
- Genera ri-consegna `POST /<id>/genera-ddt-riconsegna/` — body
  `{righe?: [{resi_riga_id, qta}], data?}` in unità BASE; omesse/null = tutta la
  copertura residua. Il DDT nasce DRAFT. Righe degeneri → 400 (mai degrado a
  "ri-spedisci tutto"). Risposta `{reso_id, ddt_id, numero: null}`.
- Chiudi ri-consegna `POST /<id>/chiudi-riconsegna/` — dichiara **definitiva**
  una quota resa per ri-consegna (non tornerà al cliente), fn madre
  `fn_chiudi_riconsegna_reso`: il residuo ordine si chiude (→ EVASO) e
  l'accredito in coda passa da FACOLTATIVA a DOVUTA **senza cambiare importo**.
  Body `{righe?: [{resi_riga_id, qta}], note?}`, `qta` in unità BASE (stesso
  contratto della ri-spedizione); `righe` omesse/null = tutta la copertura
  residua, degeneri → 400. Risposta `{reso_id, righe_chiuse}`. Errori dal DB:
  `E_RESO_NON_CONFERMATO`, `E_RESO_NESSUNA_RICONSEGNA_PENDENTE`,
  `E_RESO_RINUNCIA_SUPERA_RESO`.
- Riapri ri-consegna `POST /<id>/riapri-riconsegna/` — annulla una chiusura (fn
  madre `fn_riapri_riconsegna_reso`): la quota torna ri-spedibile, l'ordine torna
  PARZIALMENTE_EVASO, l'accredito torna FACOLTATIVA. Body
  `{righe?: [{resi_riga_id, qta}]}`; omesse = tutte le rinunce del reso, scalate
  dalle più recenti (LIFO, a DB). Risposta `{reso_id, righe_riaperte}`.

### Righe

- Lista configurabile delle righe `GET /<id>/righe/lista/` (+ `export/`): BB condiviso, vedi [api_righe_documento.md](api_righe_documento.md).
- `GET/POST /<id>/righe/`, `PATCH/DELETE /<id>/righe/<riga_id>/` — scrittura
  solo DRAFT (`E_RIGA_DOC_NON_BOZZA`). Articolo/UoM/factor sono **snapshot** dalla
  riga DDT sorgente.
  - Corpo create: `ddt_riga_id` (**obbligatorio**, riga del DDT sorgente del
    reso), `tipo_reso_id` (**obbligatorio**: a credito / per ri-consegna),
    `qta_operativa` (**obbligatoria**; la base la calcola il trigger), `motivo`,
    `meta`. Corpo PATCH: `tipo_reso_id`, `qta_operativa`, `motivo`, `meta`.
    Chiave fuori contratto (anche `quantita`) → 400 `E_RESO_VALIDAZIONE`
    (2026-10-20: prima scartata). DELETE è hard delete.
  - Risposte: PATCH `{reso_id, riga_id, updated}`, DELETE `{reso_id, riga_id, deleted}`.
- ⭐ **`gia_accreditato`** (2026-08-18) — quanti pezzi della riga sono già stati
  accreditati, in unità di **merce**. Letto da
  `vendite.fn_resi_riga_accreditato_partita`, che è il **punto unico della
  formula** (la consuma anche `vw_resi_da_accreditare`): non si ricalcola con un
  `SUM` sul ponte, che su un kit moltiplicherebbe la quota — N righe portano la
  **stessa** quota padre. È il dato su cui il drawer offre l'**annullo**
  dell'accredito: dopo il verbo la riga esce dalla coda, quindi il reso è
  l'unica sede da cui si può ancora disfare.
- `GET /api/v1/vendite/ddt/<ddt_id>/righe-per-reso/` — righe DDT con
  `qta_gia_resa`/`qta_resa_residua` (alimenta il pannello "crea reso").

### Rientri — dove rientra la merce

Sola lettura dello stato e scrittura dei rientri in bozza: bozza, prelievo della
riga di bolla giusta e, alla conferma, quadratura, tetto per prelievo e
ubicazione (`script.fn_check_reso_merce`) li giudica il DB; il backend non
ricopia regole.

- `GET /<id>/rientri/` — testata (`reso_id`, `muove_merce`, `magazzino_id`,
  `magazzino_usa_ubicazioni`) + `voci[]`: la riga o il componente del kit com'era
  uscito, ciascuna con `prelievi_origine[]` (lotto, seriale, ubicazione di
  partenza) e `rientri[]`. Reso inesistente/fuori perimetro → 404 `E_RESO_NOT_FOUND`.
- `POST /<id>/righe/<rid>/rientri/` — body `{ddt_riga_prelievo_id, qta,
  ubicazione_id?}` (`ddt_riga_prelievo_id` e `qta` obbligatori). Risposta
  `{reso_id, riga_id, rientro_id}`.
- `PATCH /<id>/righe/<rid>/rientri/<rtid>/` — body `{qta?, ubicazione_id?}` (il
  prelievo d'origine non cambia); risposta `{…, rientro_id, updated}`.
- `DELETE /<id>/righe/<rid>/rientri/<rtid>/` — risposta `{…, rientro_id, deleted}`.

Chiave fuori contratto → 400 `E_RESO_VALIDAZIONE`; riga non del reso o rientro
non della riga → 404 `E_RESO_NOT_FOUND`.

### Code di lavoro (liste configurabili di RIGHE reso CONFERMATE)

Grana RIGA (`resi_riga_id` = dataKey; azione "apri reso" via `reso_id`). Filtri:
`billing_account_id`, `data_da/data_a`, `search` (min 3), `order_by`/`order_dir`
(whitelist per vista). Si auto-limitano ai resi CONFERMATO pertinenti (niente
filtro stato).

⭐ **Filtro documento** (2026-08-18) — `?ddt_id=<id>` **oppure** `?ordine_id=<id>`
su **entrambe** le code, list **ed export**: è il collegamento dal pannello
situazione merce del drawer ordine/DDT. Predicato condiviso con il pannello
(`apps/vendite/db/_coda_documento_filtro.py`), così i due non possono divergere.
⚠️ I due id sono **alternativi**: insieme → `E_RESO_VALIDAZIONE` (due domande in
una, con la seconda che restringe la prima in silenzio). Lato ordine il legame è
il **fulfillment** della riga di DDT resa, non `ordine_riga_id` — che con la
partita generalizzata è nullable. L'export **dichiara** il filtro nel foglio
«Filtri applicati»: un file estratto da una coda filtrata, senza quella riga, si
legge come la coda intera.

- Da accreditare `GET /api/v1/vendite/resi/da-accreditare/` (+ `…/export/`) —
  **forma contatore** (2026-07-18, brief DDT-resi §3c): righe la cui partita ha
  differenza negativa (`accredito_dovuto = fatturati − tenuti > 0`),
  **qualunque tipo di reso** — il tipo è degradato a `etichetta`
  `DOVUTA` (a credito, NC obbligatoria) | `FACOLTATIVA` (per ri-consegna,
  opzione DL-26). Colonne del conto esposte: `accredito_dovuto`, `tenuti`,
  `fatturati`; `ddt_numero`/`ddt_id` possono essere **NULL** (aggancio partita
  via ordine, join DDT LEFT). Filtro extra `etichetta` (whitelist
  `DOVUTA|FACOLTATIVA`, case-insensitive; fuori whitelist →
  `E_RESO_VALIDAZIONE`; assente = tutte). Config `vendite.resi_da_accreditare`.
- Da ri-consegnare `GET /api/v1/vendite/resi/da-riconsegnare/` (+ `…/export/`) —
  righe con copertura incompleta + `stato_riconsegna` derivato
  (DA_RICONSEGNARE/PARZIALE/COMPLETATA), config `vendite.resi_da_riconsegnare`.

### Accredito — il verbo della nota di credito (2026-08-18)

Registra l'accredito della merce resa: genera le righe di **RETTIFICA** in
commessa (quantità negativa, prezzo/sconto/IVA **copiati dalla riga di fattura
rettificata**) e le annota sul ponte `vendite.resi_righe_accrediti`.

⚠️ **Il verbo NON emette la nota di credito.** Il documento nasce al giro di
fatturazione successivo, sul sezionale NC e con natura `NOTA_CREDITO`; il legame
documento-a-documento lo scrive poi il task di pipeline
`popola_fatture_rettifiche` dello step DEFINITIVA. Ogni testo mostrato
all'operatore deve dire questo: una conferma che promette «emetti nota di
credito» promette un documento che poi non si trova.

- **Accredita** `POST /api/v1/vendite/resi/accrediti/` — body
  `{resi_riga_ids: [5797, 5799, …]}`. Permesso di processo
  **`accredita_riga_reso`**; `Idempotency-Key` **obbligatoria**.

  ⭐ **Un endpoint solo, e la riga singola è una lista di uno** (D-NC-7): due
  superfici per lo stesso verbo divergerebbero su permessi, conferme e forma
  dell'esito. Fan-out isolato per riga (`run_fan_out`: savepoint per elemento),
  lista vuota **rifiutata** (non significa «tutte»), id deduplicati **con ordine
  preservato** (lo stesso id due volte produrrebbe un
  `E_ACCREDITO_GIA_ESEGUITO` autoinflitto), cap `MAX_ACCREDITI_MASSIVI = 200`.

  Risposta **200 sempre** — un REPORT, non un atto:

  ```json
  { "data": { "esito": "PARZIALE", "totale": 20, "ok": 19,
              "accrediti": [ {"resi_riga_id": 5797, "accredito_id": 901,
                              "commessa_attivita_id": 5501,
                              "fattura_riga_rettificata_id": 7101,
                              "qta": "-3.000000", "qta_partita": "-3.000000"} ],
              "falliti":   [ {"resi_riga_id": 5799,
                              "codice": "E_ACCREDITO_GIA_ESEGUITO",
                              "messaggio": "…"} ] } }
  ```

  ⚠️ **Anche «tutte fallite» è 200** (`esito: ERRORE`). Il verbo non è l'atto
  fiscale — il documento nasce dopo — quindi un esito parziale non lascia mai
  mezzo documento: lascia righe che restano in coda. E sollevare darebbe al
  client **due forme da leggere** per la stessa domanda. I codici per-riga stanno
  in `falliti`, ed è su quelli che il frontend instrada.
  ⭐ Una riga produce **N** accrediti, non uno: su un kit una rettifica per
  componente, e sul consumo di più righe di fattura a prezzi diversi altrettante.

- **Annulla l'accredito** `POST /api/v1/vendite/resi/<reso_id>/righe/<riga_id>/annulla-accredito/`
  — body `{motivo: "…"}`, **obbligatorio**. Stesso permesso
  `accredita_riga_reso` (chi può accreditare può disfare il proprio click: due
  codename per le due facce dello stesso atto si sfilano al primo profilo
  configurato a mano), `Idempotency-Key` obbligatoria.

  Porta le rettifiche ad `ANNULLATA` e **cancella** le righe di ponte — è quella
  cancellazione a far risalire l'accredito dovuto in coda. Ritorna le coppie
  rimosse. È **tutto-o-niente sull'insieme**: se anche una sola rettifica è già
  emessa non si annulla niente (un annullo parziale lascerebbe in coda un
  residuo che nessuno può più chiudere).

  ⛔ **Non è l'annullo del DOCUMENTO**: quello è la pipeline di fatturazione, ed
  è lo stesso delle fatture. ⚠️ E il **reset di lotto fa l'opposto**: riporta le
  rettifiche a `NON_EMESSA`, quindi la nota di credito viene **RIGENERATA** al
  giro successivo — la merce resa non è cambiata. Le due strade sono distinte e
  devono restare distinte; il messaggio del catalogo lo dice all'operatore
  (campo `hint` dell'envelope, [api.md](../../../dev/api.md)).

### Lineage / genealogia (brief-be-fe-lineage, 2026-07-15)

- **Passaggi** `GET /api/v1/vendite/resi/<id>/passaggi/` — genealogia del
  reso; catena significativa = **Origine** (reso ← DDT ← ordine ← …, arco R
  ramo inverso). Contratto: [api_lineage_passaggi.md](api_lineage_passaggi.md).
  ⛔ **Superato il 2026-08-25**: la riga diceva «nessuna colonna lineage sulla
  lista resi (fuori perimetro Fase B)», ed e' falsa da quando `vw_resi_lista` e'
  diventata la **sesta sorella**. La lista porta `pratica_numero`, `fase` e le
  colonne di frontiera, e la cella «Transito» di un reso e' la **nota di
  credito** che lo accredita (arco `S`). ⚠️ Dal `20260829-01/02` i nomi sono
  `frontiera_tipo_codice_interno` e `frontiera_natura_doc_codice_interno`, e
  arrivano **dalla vista**: il repository non decodifica piu' niente.

## Codici errore principali

`E_RESO_NOT_FOUND` (404), `E_RESO_DDT_NON_CONSEGNATO` (create su DDT non
consegnato), `E_RESO_QTA_SUPERA_CONSEGNATO` (over-return), `E_RESO_ANNULLO_CON_RICONSEGNE`,
`E_RESO_VALIDAZIONE` (400: payload del verbo, chiavi fuori contratto su testata,
righe e rientri, filtro di stato fuori vocabolario, filtri coda, etichetta fuori
whitelist), `E_RESO_STATO_TRANSIZIONE` (409: delete di un reso non in bozza o con
righe; la testata fuori bozza la ferma il lock DB, `E_DOC_*`),
`E_RIGA_DOC_NON_BOZZA` (409: righe aggiunte/modificate/tolte fuori bozza — dal
2026-09-22 il pre-check BE `richiedi_righe_in_bozza` usa il codice del BB a DB
`trgfn_doc_righe_lock_fuori_bozza`, che su `resi_righe` **non è ancora
montato**: il lettore `fn_get_stato_testata_documento` non conosce `RESO`),
`E_UI_EXPORT_FORMAT_INVALID` (400), `E_UI_EXPORT_LIMIT_EXCEEDED` (422).

**Accredito** — sollevati dalle madri DB e tradotti dal service; nel massivo
arrivano **per riga** dentro `falliti`, non come envelope di errore:

| Codice | Quando |
| --- | --- |
| `E_ACCREDITO_NON_IN_CODA` (422) | la riga non è in coda, o il suo dovuto è già a zero |
| `E_ACCREDITO_GIA_ESEGUITO` (409) | doppio click: l'accredito è già registrato |
| `E_ACCREDITO_ATTIVITA_NON_FATTURATA` (422) | la merce non è mai finita in una riga di fattura: non c'è un prezzo da cui accreditare |
| `E_ACCREDITO_QUOTA_NON_COPERTA` (422) | le righe di fattura non coprono tutto il dovuto — l'accredito è **sempre pieno** (D-NC-6) |
| `E_ACCREDITO_KIT_NON_MISURABILE` (422) | componente senza `coeff_qta`: la quantità in unità padre non è calcolabile |
| `E_ACCREDITO_KIT_SENZA_PADRE` (422) | componente senza `componente_di`: il difetto è sul **documento di origine**, non sul reso |
| `E_ACCREDITO_SENZA_SPEDIZIONE` (500) | tecnico: la rettifica va sempre sul segmento della spedizione (D-NC-1) |
| `E_ACCREDITO_SEGMENT_DUPLICATO` (409) | difesa in profondità: modifica concorrente, riprovare |
| `E_ACCREDITO_NON_TROVATO` (404) | annullo: nessun accredito da annullare (mai fatto, oppure già annullato — indistinguibili per costruzione) |
| `E_ACCREDITO_ANNULLO_NON_AMMESSO` (409) | annullo: una o più rettifiche sono già emesse. Il `hint` dice quale strada prendere |
| `E_ACCREDITO_MOTIVO_OBBLIGATORIO` (400) | annullo senza motivo: l'annullo cancella il ponte, il motivo è l'unica traccia del perché |
| `E_ACCREDITO_ANNULLO_INCOMPLETO` (409) | difesa in profondità: la UPDATE ha toccato meno rettifiche di quante ne risultano (perimetro emittente) |

## Riferimenti

- Service: `apps/vendite/services/resi_service.py` · Repo:
  `apps/vendite/db/resi_repository.py` (`_list_coda` = letture condivise delle
  due code, whitelist sort + search per vista) · Views: `apps/vendite/api/views_resi.py`
  · URLs: `urls_resi.py`.
- Madri DB dell'accredito: `vendite.fn_accredita_riga_reso` e
  `vendite.fn_annulla_accredito_riga_reso` (entrambe `RETURNS TABLE`: una riga
  per rettifica — `rows_to_list`, mai `fetchone`).
- Smoke end-to-end del giro (coda → rettifica → documento NC → numerazione →
  legame → annullo), in transazione annullata:
  `backend/scripts/tests/smoke-nota-credito-resi.py`.
- FE: `frontend/src/vendite/resi/` (lista, drawer, code configurabili, verbo e
  annullo, host dal drawer DDT).
