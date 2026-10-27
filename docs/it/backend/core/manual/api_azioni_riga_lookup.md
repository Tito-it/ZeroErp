# API Lookup Azioni di riga — il registro `config.azioni_riga`

## Scopo

Restituire il **registro delle azioni di riga** — per ogni azione attiva il
`codice_interno` e le due colonne della sua superficie che dicono perché il
pulsante è spento (`colonna_motivo`, il codice macchina del motivo;
`colonna_motivo_chiave`, la sua chiave i18n) — così che il frontend costruisca
il pulsante di riga leggendo **quali colonne guardare**, invece di scriverle in
ogni componente. Primo consumatore: «togli dal giro» nel drawer del lotto
(BB `useAzioneRiga`).

## Contesto

Il registro nasce col giro della fattura di
[brief-modello-documento-vendita](../../../dev/work-in-progress/brief-modello-documento-vendita.md)
§15.10-§15.11 (F-5, Q-F5 di Tid, 2026-10-27): un'azione di riga nuova si
aggiunge con una riga di registro e la sua vista, senza un pulsante nuovo. Il
presidio pgTAP del registro verifica che superficie, colonne, `fn_check` e verbo
esistano e che la vista chiami la stessa `fn_check` del verbo: tooltip ed errore
non possono dire due cose diverse.

⛔ **Lookup dedicato e non generico**: la tabella non ha `codice` (solo
`codice_interno`), e servono due colonne oltre al contratto del lookup generico,
mentre la variante specializzata ne porta una sola.

## Endpoint

```http
GET /api/v1/core/lookup/azioni-riga/
```

View: `LookupAzioniRigaView` (`apps.core.api.views_lookup`), `DomainAPIView`
con **`skip_area_check = True`** — cross-dominio: il registro serve le liste di
ogni documento. Nessun parametro.

## Input

Nessuno. Solo JWT.

## Output

Envelope di lookup **`{"data": {"results": [...]}}`** — mai la lista nuda
(api.md §L'ENVELOPE DI UN LOOKUP).

```json
{
  "data": {
    "results": [
      {
        "codice_interno": "ESCLUDI_DOCUMENTO_DA_GIRO",
        "colonna_motivo": "uscita_blocco_reason",
        "colonna_motivo_chiave": "uscita_blocco_reason_key"
      }
    ]
  },
  "meta": { "request_id": "…" }
}
```

## Regole

- Solo le azioni **attive**: un'azione spenta non ha più un pulsante.
- Superficie, `fn_check` e verbo **non** viaggiano: al client servono solo i nomi
  delle colonne della riga che riceve già.
- Ordine per `codice_interno`; nessuna paginazione (popolazione di catalogo).
- Lato FE: `useAzioneRiga(codice)` (cache condivisa `core.azioni_riga`, una fetch
  per sessione). Fail-closed: senza registro il pulsante è spento.

## Dipendenze DB

- `config.azioni_riga` (seed `80_data/sql/config/azioni_riga.csv`).

## Test

- `apps/core/tests/api/test_lookup_azioni_riga_api.py` — porta (401), forma
  dell'envelope con repository finto, e **una lettura sul DB provvisto** (colonne
  per nome, la prima azione presente, azioni attive = `count(*)` del registro).
