# API commessa oneri — porta oneri (Django)

## Scopo

Caricare su una commessa una **voce di puro valore** (onere): una riga
`commesse_attivita` con `quantita = 1` fissa, `tipo_movimento = 'ONERE'`, già
`APPROVATA`, il cui prezzo **è** l'importo dell'onere.

## Contesto

È l'unica porta d'ingresso per le righe non nate dal push. Nasce dal principio
«la commessa è un libro giornale»: una riga esistente non si modifica mai, si
**aggiunge** un fatto nuovo (brief
[brief-db-immutabilita-quantita-e-porta-oneri](../../../dev/work-done/brief-db-immutabilita-quantita-e-porta-oneri.md)
§1-§2). Poiché la riga manuale porta **valore e non quantità**, una nota di
credito travestita da quantità negativa è impossibile per costruzione, e la
riconciliazione con il documento d'origine non si rompe mai.

Le altre due porte (correzione merce → percorso reso/contatore/NC;
aggiustamento prezzo → endpoint N5/N7) restano distinte: qui non passano.

Catena: view `ApiCommessaOneri` (`apps.vendite.api.views`) →
`commesse_service.aggiungi_onere_commessa` →
`CommesseRepository.aggiungi_onere` → madre DB
`vendite.fn_aggiungi_onere_commessa`.

## Input

- Metodo: `POST`
- Path canonico: `/api/v1/vendite/commesse/<commessa_id>/oneri/`
- Header sicurezza: `Authorization: Bearer <access_token>`
- Header: `Idempotency-Key` **obbligatorio**
- Permesso: azione di processo **`carica_voce_manuale`** (`post_permission`)
- Parametri path:
  - `commessa_id` (int) — commessa su cui caricare l'onere
- Body:
  - `articolo_onere_id` (uuid, **obbligatorio**) — articolo-onere, cioè un
    articolo di catalogo con `causale_onere_id` valorizzato. Da esso il DB
    deriva causale, unità di misura e **IVA**
  - `importo` (decimal, **obbligatorio**, > 0) — il valore dell'onere
  - `tipo_doc_fiscale_id` (int, **obbligatorio**) — la riga nasce
    APPROVATA + NON_EMESSA, quindi emittibile: il guard DB `tipo_doc_emittibile`
    lo esige
  - `istanza_utility_id` (int, opzionale) — se omesso (o `0`) viene derivato
    dal billing account della commessa; se esplicito **deve coincidere** con
    l'istanza del BA (BB `istanza_del_billing_account`), altrimenti `400`
    `E_COMMESSA_VALIDATION` sul campo `istanza_utility_id`
  - `motivo` (string, opzionale, max 500) — testo libero di audit
  - `data_attivita` (date `YYYY-MM-DD`, opzionale) — default `CURRENT_DATE`

Esempio:

```json
{
  "articolo_onere_id": "3f1c9a52-0d5e-4c7b-9a10-2b6d8e4f0011",
  "importo": "150.00",
  "tipo_doc_fiscale_id": 7,
  "motivo": "trasferta cantiere del 12/07"
}
```

## Output

- `200`: onere caricato

```json
{
  "data": {
    "commessa_id": 42,
    "attivita_id": 5150,
    "importo": "150.00"
  },
  "meta": { "request_id": "..." }
}
```

## Regole

- **Nessuna approvazione a due passi**: la riga nasce `APPROVATA`. Il presidio è
  *all'ingresso* — chi ha `carica_voce_manuale` è responsabile di ciò che carica
  (decisione §4c.5 del brief DB). L'audit resta pieno: causale + motivo + la riga
  stessa + evento `ONERE_AGGIUNTO` su `commesse_attivita_log`.
- **Quantità sempre 1**: non è un parametro. L'onere porta valore, non quantità.
- **Importo solo positivo**: sia guard applicativo (400 immediato) sia guard DB
  (`E_ONERE_IMPORTO_NON_VALIDO`).
- **IVA per-onere**: l'IVA vive sull'articolo, quindi ogni onere porta la sua
  (es. penale = escluso art. 15, gli altri 22%). Non esiste un'aliquota unica.
- **Riga sourceless**: nessun documento d'origine (`sorgente_tipo_id`/`_uid`
  NULL); il discriminatore è `tipo_movimento = 'ONERE'` + causale + `segment_key`
  con prefisso `MAN:`.
- **Cieca al contatore merce**: i segmenti `MAN:` non entrano nella misura della
  partita e il contatore filtra comunque `tipo_movimento = 'NORMALE'`.
- Il perimetro Python è deliberatamente sottile: guard di input, esistenza
  commessa, derivazione istanza, traduzione errori. Ogni regola di dominio vive
  nella madre DB e non è duplicata.

## Codici errore

| Codice | HTTP | Quando |
| --- | --- | --- |
| `E_COMMESSA_VALIDATION` | 400 | payload malformato (UUID, importo, tipo doc, commessa); `istanza_utility_id` diverso da quello del BA della commessa; commessa senza billing account (istanza non risolvibile) |
| `E_COMMESSA_NOT_FOUND` | 404 | commessa inesistente o fuori scope RLS |
| `E_ONERE_ARTICOLO_MANCANTE` | 400 | l'articolo non esiste, non è attivo, o non è un onere (nessuna causale) |
| `E_ONERE_IMPORTO_NON_VALIDO` | 400 | importo ≤ 0 (guard DB) |
| `E_ONERE_CAUSALE_NON_VALIDA` | 400 | causale inesistente o non attiva |
| `E_COMMESSA_ATTIVITA_TIPO_DOC_OBBLIGATORIO` | 400 | tipo documento fiscale mancante sulla riga emittibile |

## Dipendenze DB

- `vendite.fn_aggiungi_onere_commessa` — madre della porta (riusa
  `fn_upsert_commessa_attivita` e scrive `commesse_attivita_log`)
- `catalogo.articoli.causale_onere_id` — discriminatore articolo-onere (1:1)
- `config.causali_onere` — vocabolario causali (mono-lingua, seed CSV)
- `vendite.commesse_attivita.causale_onere_id` + CHECK biconditional
  `(tipo_movimento='ONERE') ⇔ (causale IS NOT NULL)`
- `anagrafiche.billing_account.istanza_utility_id` — derivazione istanza

## Note di migrazione

- Prerequisito seed: azione di processo `carica_voce_manuale` in
  `config.azioni_processo` (area vendite). Fino all'apply del seed l'endpoint è
  fail-closed: accessibile solo a SUPER_ADMIN/superuser.
- La sorgente `DIRECT_ENTRY` di `config.sorgenti` **non** è usata da questa
  slice (riga sourceless): resta disponibile per un futuro inserimento diretto
  *con* chiave esterna.
