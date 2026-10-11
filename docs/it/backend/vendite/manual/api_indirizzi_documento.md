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
  campi di contatto `email/telefono/note`. **Guard ownership**: l'indirizzo
  deve appartenere al `soggetto_ruolo` del cliente (billing account) del
  documento, altrimenti `E_<DOM>_VALIDAZIONE`.
- **UNA-TANTUM** (indirizzo occasionale, D-4): body `{tipo_indirizzo_id, snapshot}`.
  Chiavi ammesse: `intestazione, via, cap, citta, prov, stato, display, email,
  telefono, note` (soli valori scalari, il resto scartato); richiesto almeno
  uno tra `via/citta/display`. `origine_indirizzo_id` resta NULL;
  `origine_soggetto_ruolo_id` opzionale per dichiarare la provenienza
  "anagrafica soggetto" (picker su riga fonte=soggetto e auto-assegnazione):
  validato contro il cliente del documento (anti-tampering). Semantica tag FE:
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
  `E_<DOM>_VALIDAZIONE` (payload/ownership).

### Rimozione slot `DELETE .../<id>/indirizzi/<indirizzo_id>/`

- Hard delete dello slot (nessuna storicità propria). Documento in stato
  editabile. Riga inesistente o di altro documento → `E_<DOM>_NOT_FOUND` (404,
  anti-tampering URL).
- L'obbligatorietà (es. `CON` sul DDT) è verificata dal guard DB
  **all'emissione** (`trg_ddt_a10_guard_indirizzi_obbligatori_upd` →
  `E_INDIRIZZO_DOC_OBBLIGATORIO`), non alla rimozione.

## Auto-assegnazione default alla creazione (UX v2)

`auto_assegna_indirizzo_default(cfg, documento_id)` (helper condiviso): alla
creazione del documento, se lo slot default (CON → FATT) e' vuoto e il cliente
ha un indirizzo di **ruolo** di tipo CON (fallback FATT), lo snapshot viene
congelato con `origine_*`. Best-effort (mai bloccante). Attivo su **tutti i
5 domini** (rollout 2026-07-12): DDT (create standalone + evasione da ordine),
preventivi (`crea_preventivo`), ordini (`crea_ordine`, che copre anche la
conversione da offerta, + fallback post `fn_push_preventivo_a_ordine`),
offerte (`crea_offerta`), contratti (`create_contratto` + fallback post
`fn_push_offerta_a_contratto` via `auto_assegna_indirizzo_default_contratto`).
Dove esiste la cascata DB dal documento sorgente, l'helper agisce solo da
fallback (salta se lo slot default e' gia' valorizzato).

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
