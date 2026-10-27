# API reset_lotto_draft (Django)

## Scopo
Esporre via HTTP l'**annullamento** di un lotto in DRAFT (`reset-draft`) e, accanto,
il suo opposto: il **ritorno a bozza** (`riporta-a-draft`). Sono i due verbi che
disfano il lavoro di un lotto, ma fanno cose opposte: il primo **chiude** il lotto
(fiscale `ANNULLATA`, non si riapre), il secondo lo rimette in lavorazione.

## Contesto
View `ApiResetLottoDraft` → `fn_annulla_lotto_da_draft`
(`apps/vendite/services/pipeline_service.py` → `LottoResetService`) → funzione SQL
`vendite.fn_annulla_lotto_da_draft`. L'URL conserva il nome storico «reset-draft»:
è un contratto verso i client.

## Input
- Metodo: `POST`
- Path: `/api/v1/vendite/lotti/{lotto_id}/reset-draft/`
- Header: `Authorization: Bearer <access_token>`, `Idempotency-Key` (obbligatorio)
- Permesso: l'azione della **riga del passaggio** verso lo stato d'annullo del
  vocabolario (`PassaggioDocumento`, `stato_del_modello="annullo"`). Oggi la riga
  DRAFT → ANNULLATA non ha azione, perché non c'è niente di fiscale da disfare (Q-F2
  di brief-modello-documento-vendita, 2026-10-27), e decide il **livello sul
  documento** (area `vendite`). Se la matrice le dà un'azione, il gate la segue.
  Prima chiedeva `reset_lotto_draft`, ritirata dal catalogo.
- Body JSON: vuoto

## Output
- `200`: `{ "data": { "updated_lotti": <int>, "updated_attivita": <int>, "deleted_fatture": <int>, "deleted_righe": <int> }, "meta": { ... } }`
- `400 E_RESET_LOTTO_VALIDATION`: `lotto_id` ≤ 0
- `404 E_LOTTO_NON_TROVATO`; rifiuti di dominio col codice del **primo** motivo di
  `script.fn_check_lotto_annullabile` (sede unica della regola, letta anche da
  `fn_available_actions_lotto` per il pulsante): `E_LOTTO_NON_ANNULLABILE` (lotto non
  in DRAFT), `E_LOTTO_FATTURE_NON_PRE_FISCALI`, `E_LOTTO_FATTURE_NUMERATE`,
  `E_FATTURE_RIGHE_RETTIFICATE`, `E_FATTURE_PLAFOND_CONSUMATO`

## Regole
- Ammesso per lotti `MASSIVO` **e** `GIORNALIERO` in DRAFT; le precondizioni sono del
  DB e non si ricopiano nel backend.
- Cancella le fatture pre-fiscali, rimette le attività «da emettere», chiude i task
  run e lascia un guscio col fiscale `ANNULLATA` (fuori dal registro lotti di
  default, vedi [api_lotti_list.md](api_lotti_list.md)).
- Pattern core `handle_post_json(..., require_idempotency_key=True)`.

## Ritorno a bozza — `POST lotti/{lotto_id}/riporta-a-draft/`

- View `ApiRiportaLottoADraft` → `fn_riporta_lotto_a_draft` → SQL
  `vendite.fn_riporta_lotto_a_draft`. È un'azione dell'operatore, non un task di
  pipeline.
- Permesso: l'azione della **riga del passaggio** EMESSA → stato iniziale (oggi
  `numera_fatture_lotti`, la stessa di «numera», Q-F1), col BB
  `PassaggioDocumento(stato_del_modello="iniziale")`: lo stato d'arrivo lo dice il DB
  a ogni richiesta (`script.fn_doc_stato_iniziale_id`, brief-modello-documento-vendita
  §15.13), mai un `'DRAFT'` scritto nel backend. Su un lotto già in bozza (sola
  pulizia) la riga non c'è e basta il livello sul documento. Prima chiedeva
  `reset_lotto_draft`, ritirata dal catalogo. `Idempotency-Key` obbligatorio, body vuoto.
- È la via d'uscita da EMESSA, dove l'annullamento è rifiutato: il lotto torna in
  lavorazione e il giro successivo rifà lo step (`riaperto`). Precondizioni (tipo
  lotto, stato, nessuna fattura numerata) nella funzione DB.
- `200`: `{ "data": { "updated_lotti", "updated_attivita", "deleted_fatture",
  "deleted_righe", "riemesse_attivita", "annullati_task_run" } }` —
  `riemesse_attivita` = attività di commessa tornate `NON_EMESSA`;
  `annullati_task_run` = task run chiusi ad `ANNULLATO` su tutti gli step (senza,
  il lotto riaperto rilancerebbe a vuoto).
- `400 E_RESET_LOTTO_VALIDATION` su `lotto_id` ≤ 0; rifiuti di dominio dalla
  funzione DB.

## Dipendenze DB
- `vendite.fn_annulla_lotto_da_draft`, `script.fn_check_lotto_annullabile`
- `vendite.fn_riporta_lotto_a_draft`
