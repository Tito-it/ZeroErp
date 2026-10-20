# API Indirizzi documento (BB condiviso — 5 domini vendite)

## Scopo

Gestione degli **indirizzi documento** (snapshot congelato + origine soft) per
i 5 domini vendite: **preventivi, offerte, ordini, ddt, contratti**. Endpoint
identici su tutti i domini, generati dal factory condiviso
`build_indirizzi_documento_views` (`apps/vendite/api/indirizzi_documento_views.py`)
sopra il BB service `_indirizzi_documento_helpers` e il mixin repository
`IndirizziDocumentoRepositoryMixin`.

Design-of-record:
[brief-design-indirizzi-documenti-vendita.md](../../../dev/work-done/brief-design-indirizzi-documenti-vendita.md)
(decisioni D-1..D-5). Modello DB:
[brief-db-indirizzi-documenti-simmetria-e-cascata.md](../../../dev/work-done/brief-db-indirizzi-documenti-simmetria-e-cascata.md)
— tabelle `vendite.<doc>_indirizzi` simmetriche (UNIQUE uno-per-tipo, trigger
whitelist `trgfn_tipi_indirizzi_only_allowed(<AMBITO>)` fail-closed su
`config.tipi_indirizzi_allowed`).

| Dominio | Base path | Ambito whitelist | Stati editabili |
|---|---|---|---|
| Preventivi | `/api/v1/vendite/preventivi/<id>/indirizzi/` | `PREVENTIVI` | `DRAFT` (BOZZA) |
| Offerte | `/api/v1/vendite/offerte/<id>/indirizzi/` | `OFFERTE` | `BOZZA` |
| Ordini | `/api/v1/vendite/ordini/<id>/indirizzi/` | `ORDINI` | `DRAFT` |
| DDT | `/api/v1/vendite/ddt/<id>/indirizzi/` | `DDT` | `DRAFT` |
| Contratti | `/api/v1/vendite/contratti/<id>/indirizzi/` | `CONTRATTI` | `DRAFT` |

Post-emissione/attivazione lo snapshot è **congelato** col documento
(modifiche anagrafiche non retroagiscono); la cascata documentale
(preventivo→ordine, ordine→DDT, offerta→contratto) copia gli slot 1:1 nelle
funzioni madre DB, filtrati sulla whitelist di destinazione (D-1).

## Endpoints

### Pannello `GET .../<id>/indirizzi/`

- Auth: area `vendite`, livello LETTURA.
- Output `200`:
  - `tipi_ammessi[]`: `{tipo_indirizzo_id, tipo_indirizzo_codice, tipo_indirizzo_descrizione, obbligatorio}` — gli SLOT del pannello (whitelist per ambito, ordinati obbligatori-prima).
  - `indirizzi[]`: `{id, <doc>_id, tipo_indirizzo_id, tipo_indirizzo_codice, tipo_indirizzo_descrizione, snapshot (object), origine_indirizzo_id, origine_soggetto_ruolo_id}`.
- Errori: `E_<DOM>_NOT_FOUND` (404) su documento inesistente — mai pannello vuoto per documento fantasma.

### Upsert slot `POST .../<id>/indirizzi/` (uno-per-tipo)

Via `handle_post_json`. Due flussi mutuamente esclusivi:

- **PICKER** (indirizzo del cliente): body `{tipo_indirizzo_id, origine_indirizzo_id, snapshot?}`.
  Lo snapshot geografico è composto **server-side** da
  `script.fn_snapshot_indirizzo` (D-5): dal payload vengono accettati solo i
  campi di contatto `email/telefono/note`. Che l'indirizzo sia **del
  cliente del documento** (il suo ruolo e, se e' legato a una fornitura, la
  sua istanza) lo giudica il guard DB `vendite.trgfn_doc_indirizzi_guard_cliente`
  sulle sei `*_indirizzi`: `E_INDIRIZZO_DOC_NON_DEL_CLIENTE` sul campo
  `tipo_indirizzo_id`. Il backend non ha piu' un controllo suo (dal
  2026-10-12, brief-db-indirizzi-documento-seguono-il-cliente R-BE-2).
- **UNA-TANTUM** (indirizzo occasionale, D-4): body `{tipo_indirizzo_id, snapshot}`.
  Chiavi ammesse: `intestazione, via, cap, citta, prov, stato, display, email,
  telefono, note` (soli valori scalari, il resto scartato); richiesto almeno
  uno tra `via/citta/display` (altrimenti `E_<DOM>_VALIDAZIONE`). `origine_indirizzo_id` resta NULL;
  `origine_soggetto_ruolo_id` opzionale per dichiarare la provenienza
  "anagrafica soggetto" (picker su riga fonte=soggetto e slot di default):
  la giudica lo stesso guard DB. Semantica tag FE:
  entrambi NULL = una-tantum vero; solo `origine_soggetto_ruolo_id` = derivato
  dal layer soggetto (tag "Soggetto").

- Regole: upsert `ON CONFLICT (<doc>_id, tipo_indirizzo_id)` (sostituisce lo
  slot); tipo validato dal trigger whitelist DB. In quale stato si cambia lo
  dice il DB: lock «solo in bozza» dei satelliti (dal 2026-10-11,
  brief-db-testata-dopo-emissione §11), specchiato dalla capability
  `can_edit_indirizzi` del documento.
- Output `200`: riga completa upsertata (shape di `indirizzi[]`).
- Errori: `E_<DOM>_NOT_FOUND` (404); `E_DOC_DATI_COLLEGATI_NON_BOZZA` (409,
  documento fuori bozza: lo solleva il lock del DB, il service non ha piu' un
  guard di stato suo); `E_TIPO_INDIRIZZO` (trigger whitelist);
  `E_INDIRIZZO_SNAPSHOT_NOT_FOUND` (404, origine inesistente);
  `E_INDIRIZZO_DOC_NON_DEL_CLIENTE` (400, indirizzo d'anagrafica di un altro
  cliente o di un'altra fornitura, campo `tipo_indirizzo_id`);
  `E_<DOM>_VALIDAZIONE` (payload).

### Rimozione slot `DELETE .../<id>/indirizzi/<indirizzo_id>/`

- Hard delete dello slot (nessuna storicità propria). Lo stato lo giudica il
  lock dei satelliti a DB (`E_DOC_DATI_COLLEGATI_NON_BOZZA`, 409), come
  sull'upsert. Riga inesistente o di altro documento → `E_<DOM>_NOT_FOUND` (404,
  anti-tampering URL). Output `200`: `{"deleted": true, "id": <indirizzo_id>}`.
- L'obbligatorietà (es. `CON` sul DDT) è verificata dal guard DB
  **all'emissione** (`trg_ddt_a10_guard_indirizzi_obbligatori_upd` →
  `E_INDIRIZZO_DOC_OBBLIGATORIO`), non alla rimozione.

## Slot di default e cambio di cliente

Lo slot di default lo riempie il **DB**, non il backend (dal 2026-10-12,
brief-db-indirizzi-documento-seguono-il-cliente D-2):

- **alla creazione** chi crea chiama `vendite.fn_doc_indirizzo_default(<documento>, <id>)`
  (repository: `riempi_indirizzo_default`), nella **stessa transazione** della
  creazione: non e' best-effort, un errore sale e annulla anche la testata.
  Quale slot e quale ripiego sono un dato (`config.tipi_indirizzi_allowed.slot_default`,
  `ripiego_tipo_indirizzo_id`: oggi CON con ripiego FATT su DDT, ordini,
  preventivi, offerte, contratti). Lo slot si riempie **solo se e' vuoto**:
  dove c'e' la cascata dal documento sorgente il building block si chiama
  **dopo** il verbo, e la sorgente vince. Punti di chiamata: `crea_ddt`,
  `crea_ddt_da_ordine`, `genera_ddt_riconsegna`, `crea_ordine` (copre la
  conversione da offerta), `crea_ordine_da_preventivo`, `crea_preventivo`,
  `crea_offerta`, `push_a_contratto` dell'offerta. `create_contratto` no: lo fa
  `vendite.fn_create_contratto` da se'. Le revisioni di preventivo e offerta no:
  copiano gli indirizzi della versione precedente cosi' come sono;
- **al cambio di cliente in bozza** (DDT: BA o destinatario; preventivo,
  offerta, contratto: BA o istanza) un trigger toglie gli indirizzi
  d'anagrafica che non sono piu' del cliente (gli una-tantum restano) e
  riempie di nuovo lo slot rimasto vuoto. Il FE ricarica il pannello dopo il
  salvataggio del cliente.

All'emissione l'indirizzo d'altri e' un motivo del gate
(`reason_key` `common.azione_reason.indirizzo_non_del_cliente`).

## Dipendenze DB

- `vendite.<doc>_indirizzi` (6 tabelle simmetriche, incl. fatture — senza
  endpoint: cascata fattura nel cantiere fatturazione).
- `config.tipi_indirizzi_allowed` (whitelist per ambito, seed 2026-07-11) +
  `trgfn_tipi_indirizzi_only_allowed` (fail-closed).
- `script.fn_snapshot_indirizzo(p_indirizzo_id)` → `(snapshot jsonb,
  origine_soggetto_ruolo_id)`.

## Riferimenti

- FE: BB `frontend/src/vendite/_shared/indirizzi/` (`DocumentoIndirizziSection`
  inline + `DocumentoIndirizziDrawer` gestione + `makeIndirizziDocumentoApi`) —
  montato sui 5 drawer documento (DDT pilota, poi preventivi/ordini/offerte/
  contratti, rollout 2026-07-12; UX v2 brief design §7). I detail API dei 5
  domini espongono `soggetto_ruolo_id` (cliente del BA) e `istanza_utility_id`
  per la cascata anagrafica a 3 livelli del drawer di gestione.
- PDF: `DdtDocumentContextBuilder` v2 (context_version 2, 2026-07-12) legge
  `ddt_indirizzi` → blocco `indirizzi.consegna` (slot CON, chiavi fisse per
  StrictUndefined + `display_compatto`); template DDT 76 versione 2 PUBBLICATA
  stampa "Luogo di consegna" nel box destinatario, omesso se lo slot manca
  (anteprima in DRAFT). Gli altri 4 context builder restano v1 (rollout
  futuro: tipo da scegliere per ambito).
- Doc gemelle: [api_preventivi.md](api_preventivi.md) §11,
  [api_ordini.md](api_ordini.md), [api_ddt.md](api_ddt.md).
