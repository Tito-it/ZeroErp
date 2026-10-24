# API Approvazioni prezzo (workflow L3)

## Scopo

Workflow **L3 approvazione out-of-policy** per override prezzo che violano
i limiti L2 configurati: l'operatore richiede approvazione, l'approver
(utente con `approva_prezzo_override`) decide approva/rifiuta dalla coda
dedicata.

Riferimento concettuale:
[sviluppo-listini-v5.md](/dev/work-done/sviluppo-listini-v5) §14.6
e guida operativa [gestione-listini.md §6.2](/guide/gestione-listini#62-l3-workflow-approvazione-out-of-policy).

## Contesto

Il workflow è composto da:

1. **Richiesta**: l'operatore preventiva oltre L2 con flag
   `richiesta_approvazione=true` nel payload `POST /preventivi/{id}/righe/`
   o `PATCH /preventivi/{id}/righe/{rid}/` (vedi `api_preventivi.md`).
   Il backend cattura la violazione L2, crea pratica
   `pratiche.tipi_prestazione` codice `APPROVAZIONE_PREZZO` (id 9001 seedato),
   transito immediato BOZZA → APERTA, salva la riga con
   `stato_approvazione_prezzo='PENDING'` + FK `pratica_approvazione_prezzo_id`.
   Email best-effort al recipient configurato in
   parameter `VENDITE_APPROVAZIONE_PREZZO_RECIPIENT_EMAIL`.
2. **Coda approver**: l'approver vede la propria coda via
   `GET /vendite/approvazioni-prezzo/`, scope emittente derivato dal JWT.
3. **Esito**: l'approver invoca `POST .../approva-prezzo/` o
   `.../rifiuta-prezzo/`. Riga aggiornata + pratica chiusa con nota INTERNA.

**Trigger DB di guardia** (defense-in-depth):

- `script.fn_check_prezzi_autorizzati` (building block, dal 2026-09-24): un prezzo **non autorizzato** — riga o componente BoM attivo in `PENDING` o `REJECTED` — non lascia uscire il documento dalla bozza né lo lascia accettare (`E_DOC_PREZZO_PENDENTE` / `E_DOC_PREZZO_RIFIUTATO`). Vale per preventivi, contratti, offerte, ordini e DDT; lo leggono sia i guard di transizione sia le `fn_available_actions_*`, quindi il pulsante spento e il rifiuto non divergono. **Annulla resta sempre acceso**. Sul preventivo: Regola 2 (`fn_check_preventivo_emettibile`, verso EMESSO) e Regola 3 (`trgfn_preventivi_guard_transizione`, verso ACCETTATO)
- `trgfn_preventivi_righe_guard_pending`: allowlist su righe PENDING (ammessi solo `stato_approvazione_prezzo`, `pratica_approvazione_prezzo_id`, `meta`); modifica struttura -> `E_RIGA_PREZZO_PENDENTE`

## Sorgenti e routing (preventivo / contratto / offerta)

Il workflow L3 è **sorgente-agnostico**: la stessa pratica `APPROVAZIONE_PREZZO`
può originare da una riga preventivo, una riga contratto o un'eccezione offerta
(refactor 2026-06-01). Il discriminatore vive nel `meta` della pratica
(`sorgente` + chiave riga dedicata) ed è esposto come campo top-level nella coda.
Gli endpoint approva/rifiuta sono **distinti per sorgente** perché `riga_id`
appartiene a tabelle/sequence indipendenti; il service fa dispatch via parametro
`sorgente` (`_SORGENTE_CONFIG`, niente if-chain).

| `sorgente`   | Tabella riga                            | Path approva / rifiuta                                                  | Chiave meta riga     |
| ------------ | --------------------------------------- | ----------------------------------------------------------------------- | -------------------- |
| `preventivo` | `vendite.preventivi_righe`              | `/api/v1/vendite/righe/{riga_id}/{approva,rifiuta}-prezzo/`             | `riga_preventivo_id` |
| `contratto`  | `vendite.contratti_righe`               | `/api/v1/vendite/righe-contratto/{riga_id}/{approva,rifiuta}-prezzo/`   | `riga_contratto_id`  |
| `offerta`    | `vendite.offerte_commerciali_eccezioni` | `/api/v1/vendite/eccezioni-offerta/{riga_id}/{approva,rifiuta}-prezzo/` | `riga_offerta_id`    |

Tutti gli endpoint hanno stesso `post_permission = "approva_prezzo_override"`,
stesso shape body/risposta, stessi codici errore. La coda (`§3`) restituisce per
ogni item il campo `sorgente`: il FE lo usa per instradare la chiamata
approva/rifiuta all'endpoint corretto (`ApprovazioniPrezzoListView`). Le sezioni
sotto descrivono i campi/effetti usando i preventivi come esempio; contratto e
offerta sono speculari (cambiano tabella riga e codice not-found,
`E_VENDITE_NOT_FOUND`).

## Endpoint

### 1. Approva richiesta

- Metodo: `POST`
- Path (preventivi): `/api/v1/vendite/righe/{riga_id}/approva-prezzo/`
  (contratti: `/righe-contratto/...`; offerte: `/eccezioni-offerta/...`)
- Auth: `vendite` + `post_permission = "approva_prezzo_override"` (oppure superuser)
- Header: `Idempotency-Key` non preteso (`handle_post_json` senza `require_idempotency_key`: nessun replay)
- Body JSON:
  - `nota` (string, opzionale) — registrata come nota INTERNA sulla pratica
- Output `200`:

```json
{
  "data": {
    "riga_id": 50,
    "pratica_id": 12345,
    "stato": "APPROVED"
  }
}
```

- Effetti collaterali (transazione atomica):
  - UPDATE `vendite.preventivi_righe.stato_approvazione_prezzo='APPROVED'`
  - Transizione pratica APERTA → CHIUSA via `pratiche_service.cambia_stato_pratica`
  - INSERT nota INTERNA: `"Approvato override prezzo. {nota}"` (oppure default)
- Errori:
  - `E_PERMISSION_DENIED` (403) — utente senza azione `approva_prezzo_override`: lo rifiuta il cancello della view (`post_permission`), prima di qualunque lookup riga (no leak su esistenza). Il service ripete il controllo come difesa interna (`E_PRICING_OVERRIDE_NON_AUTORIZZATO`, 403), non raggiungibile dall'endpoint
  - `E_PREV_RIGA_NOT_FOUND` (404) — riga inesistente
  - `E_APPROVAZIONE_PREZZO_NON_AMMESSA` (409) — riga non in stato `PENDING` o senza pratica collegata (stato inconsistente)

---

### 2. Rifiuta richiesta

- Metodo: `POST`
- Path (preventivi): `/api/v1/vendite/righe/{riga_id}/rifiuta-prezzo/`
  (contratti: `/righe-contratto/...`; offerte: `/eccezioni-offerta/...`)
- Auth: `vendite` + `post_permission = "approva_prezzo_override"` (oppure superuser)
- Header: `Idempotency-Key` non preteso
- Body JSON:
  - `motivazione` (string, opzionale) — registrata come nota INTERNA con prefisso "Rifiutato override prezzo. Motivo: ..."
- Output `200`:

```json
{
  "data": {
    "riga_id": 50,
    "pratica_id": 12345,
    "stato": "REJECTED"
  }
}
```

- Effetti collaterali (transazione atomica):
  - UPDATE `vendite.preventivi_righe.stato_approvazione_prezzo='REJECTED'`
  - Transizione pratica APERTA → CHIUSA
  - INSERT nota INTERNA con motivazione (o default se vuota)
- **Nota dominio**: il prezzo della riga **non viene riportato al resolver**. Spetta all'utente decidere come correggere (riduce sconto e ritenta, oppure annulla riga). La riga REJECTED non è bloccata dal trigger DB: l'utente può modificarla liberamente.
- Errori: stessi di `approva-prezzo` (403/404/409)

---

### 3. Coda approver

- Metodo: `GET`
- Path: `/api/v1/vendite/approvazioni-prezzo/`
- Auth: `vendite` + `get_permission = "approva_prezzo_override"` (oppure superuser): la coda è una pagina operativa per approver, non una lista consultiva
- Throttling: `is_search_endpoint = True`
- Cancello perimetro emittente (`lista_codice = "vendite.approvazioni_prezzo"`): può rispondere `422 E_UI_LISTA_EMITTENTE_DA_SCEGLIERE`
- Query params:
  - `limit` (int, default 25 `DEFAULT_LIMIT`, max 200 `MAX_LIMIT`; fuori da 1..200 → 400 `E_VALIDATION_INPUT`, dal 2026-10-21)
  - `offset` (int, default 0; negativo → 400 `E_VALIDATION_INPUT`)
  - `order_by` (whitelist pratiche `PRATICHE_ORDER_COLS`: `id`, `codice`, `descrizione`, `data_apertura`, `data_scadenza`, `data_insert`, `tipo_prestazione_descrizione`, `stato_descrizione`, `priorita_descrizione`, `soggetto_display`, `risorsa_umana_display`; default `data_insert`)
  - `order_dir` (`asc`/`desc`, default `desc` per qualunque colonna)
- Output `200`:

```json
{
  "data": {
    "results": [
      {
        "id": 12345,
        "tipo_prestazione_id": 9001,
        "stato_codice_interno": "APERTA",
        "priorita_id": 2,
        "descrizione": "Richiesta approvazione prezzo riga preventivo P-001 - violazione L2 SCONTO: 25.00% (max 10%).",
        "data_insert": "2026-04-23T10:30:00+02:00",
        "soggetto_id": "...",
        "meta": {
          "preventivo_id": 42,
          "articolo_id": "...",
          "prezzo_resolver": "50.00",
          "prezzo_manuale": "37.50",
          "violazione": {"tipo_violazione": "SCONTO", "variazione_abs_pct": "25.00", "limite_pct": "10"},
          "richiedente_auth_user_id": 7,
          "riga_preventivo_id": 50
        },
        "can_approve": true,
        "can_reject": true,
        "action_reason": null
      }
    ],
    "count": 1,
    "limit": 25,
    "offset": 0
  }
}
```

- Filtra automaticamente:
  - `tipo_prestazione_id = 9001` (codice `APPROVAZIONE_PREZZO`)
  - `stato_codice_interno = 'APERTA'`
  - `emittente_fiscale_id` derivato da `PermissionResolver.get_emittente_for_user` (operatore singolo emittente)
- **Capability per item (Fase 5.B1)**: ogni item della coda ha `can_approve`/`can_reject`/`action_reason` **e `sorgente`** (`preventivo`/`contratto`/`offerta`, per il routing endpoint lato FE). Permesso utente calcolato 1 volta (azione `approva_prezzo_override`); per-item la verifica della chiave riga corretta per la sorgente (`riga_preventivo_id`/`riga_contratto_id`/`riga_offerta_id`; nessun ripiego sulla vecchia chiave `riga_id`).
Poiché la coda pretende già `approva_prezzo_override`, `PERMESSO_MANCANTE` è di fatto difensivo. Codici stabili `action_reason` esposti come costanti modulo BE (`ACTION_REASON_PERMESSO_MANCANTE`, `ACTION_REASON_RIGA_NON_LINKATA`):

| `action_reason`     | Quando                                                                      | Effetto FE                                                                         |
| ------------------- | --------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| `null`              | Tutto OK: utente HA permesso + riga linkata                                 | Bottoni Approva/Rifiuta abilitati                                                  |
| `PERMESSO_MANCANTE` | Utente senza azione `approva_prezzo_override` (e non superuser)             | Bottoni disabilitati + tooltip i18n `approvazioni_prezzo.reason_permesso_mancante` |
| `RIGA_NON_LINKATA`  | Chiave riga della sorgente assente nel meta, o `sorgente` sconosciuta        | Bottoni disabilitati + tooltip i18n `approvazioni_prezzo.reason_riga_non_linkata`  |

- Errori:
  - `E_PERMISSION_DENIED` (403) — utente senza `approva_prezzo_override` (cancello della view)
  - `E_VENDITE_VALIDATION` (400) — `order_by` fuori whitelist (validato prima della risoluzione utente/emittente)
  - `E_UI_LISTA_EMITTENTE_DA_SCEGLIERE` (422) — cancello perimetro emittente
  - `E_APPROVAZIONE_PREZZO_NON_AMMESSA` (409) — admin globale senza emittente assegnato (la coda è multi-tenant per emittente; admin globale deve usare `cerca_pratiche` generico per cross-tenant)

---

## Codici errore (sintesi)

| Codice                                | HTTP | Contesto                                                                  |
| ------------------------------------- | ---- | ------------------------------------------------------------------------- |
| `E_DOC_PREZZO_PENDENTE`               | 409  | Guard DB: documento verso emissione/accettazione con prezzi PENDING       |
| `E_DOC_PREZZO_RIFIUTATO`              | 409  | Guard DB: documento verso emissione/accettazione con prezzi REJECTED      |
| `E_RIGA_PREZZO_PENDENTE`              | 409  | Trigger DB su modifica struttura riga PENDING                             |
| `E_APPROVAZIONE_PREZZO_NON_AMMESSA`   | 409  | Service: riga non PENDING, senza pratica, oppure approver senza emittente |
| `E_PERMISSION_DENIED`                 | 403  | Cancello view: utente senza `approva_prezzo_override` (POST e coda)       |
| `E_PRICING_OVERRIDE_NON_AUTORIZZATO`  | 403  | Difesa interna del service (non raggiungibile dagli endpoint)             |
| `E_VENDITE_VALIDATION`                | 400  | Coda: `order_by` fuori whitelist                                          |
| `E_UI_LISTA_EMITTENTE_DA_SCEGLIERE`   | 422  | Coda: cancello perimetro emittente                                        |

## Riferimenti

- Pattern richiesta dal preventivo: vedi `api_preventivi.md` §8 (aggiungi riga) e §9 (aggiorna riga)
- Service backend: `apps/vendite/services/approvazioni_prezzo_service.py`
- Building block: [catalogo-building-block-backend](../../../dev/backend/catalogo-building-block-backend) sezione `approvazioni_prezzo_service.*`
- Guida utente: [gestione-listini §6.2](/guide/gestione-listini#62-l3-workflow-approvazione-out-of-policy)
- ChangeSet DB: `20260422-03..07` + seed CSV `azioni_processo` id 10 + `tipi_prestazione` id 9001 + `messaggi_errore` 389/390
