# API commessa_stato (Django)

## Scopo

Sulla risorsa `stato` di una commessa:

- **GET** — stato, contatori aggregati e **capability** (azioni di stato ammesse), per
  dashboard e monitoraggio avanzamento;
- **POST** — applica un'**azione di stato utente** (chiudi / riapri / annulla).

## Contesto

- GET → servizio Python `fn_get_commessa_stato` (`apps.vendite.services.commesse_service`):
  contatori da `CommesseRepository.get_commessa_stato()` + capability da
  `CommesseRepository.get_capabilities()` (`script.fn_available_actions_commessa`).
- POST → servizio `cambia_stato_commessa`: difesa applicativa (azione ammessa solo se in
  `capabilities.available_actions`) + `CommesseRepository.cambia_stato_commessa()`
  (`vendite.fn_cambia_stato_commessa`, guard di matrice a DB).

View: `ApiCommessaStato` (`apps.vendite.api.views`) — `def get` + `def post` sulla stessa URL.

## Input

- Metodo: `GET`
- Path canonico: `/api/v1/vendite/commesse/<commessa_id>/stato/`
- Header sicurezza: `Authorization: Bearer <access_token>`
- Parametri path:
  - `commessa_id` (int) — ID della commessa

## Output

- `200`: commessa trovata

```json
{
  "data": {
    "commessa_id": 1,
    "stato_codice_interno": "PRONTA_FATTURAZIONE",
    "stato_commessa_id": 4,
    "stato_commessa": "PRONTA_FATTURAZIONE",
    "chiude_commessa": false,
    "emittibile": true,
    "modificabile": true,
    "policy_fatturazione": "DA_DOCUMENTO",
    "fatturazione_immediata": false,
    "priorita_operativa": null,
    "billing_account_id": 1001,
    "utility_id": 2,
    "emittente_soggetto_ruolo_id": 555,
    "total_attivita": 10,
    "total_approvate": 8,
    "total_non_approvate": 2,
    "total_emesse": 5,
    "total_non_emesse": 5,
    "total_prezzo_da_riallineare": 0,
    "last_update": "2026-06-15T10:00:00",
    "capabilities": {
      "available_actions": [
        {"key": "chiudi", "target_state": "CHIUSA", "label_key": "vendite.commesse.azione_chiudi",
         "severity": "success", "icon": "pi pi-lock", "requires_confirm": true, "outlined": false},
        {"key": "annulla", "target_state": "ANNULLATA", "label_key": "vendite.commesse.azione_annulla",
         "severity": "danger", "icon": "pi pi-times", "requires_confirm": true, "outlined": true}
      ],
      "can_change_state": true,
      "can_edit_righe": true,
      "is_emittibile": true,
      "stato_codice": "PRONTA_FATTURAZIONE"
    }
  },
  "meta": { ... }
}
```

Campi (2026-06-15): l'endpoint ora propaga **tutto** ciò che `fn_get_commessa_stato`
espone, non più i soli 3 contatori. In dettaglio:

- `stato_codice_interno` (2026-06-10): codice stato interno della testata
  (`vendite.stati_commessa.codice_interno`) — verifica l'esito del ponte di
  emittibilità post-push senza una seconda chiamata. **Dal 2026-06-16 è derivato dal
  blob `capabilities.stato_codice`** (stessa fonte `codice_interno`), evitando un
  round-trip DB dedicato; valore invariato.
- **Stato + governance** (da `vendite.stati_commessa`): `stato_commessa_id`,
  `stato_commessa` (= `codice`, etichetta di stato), flag `chiude_commessa` /
  `emittibile` / `modificabile`.
  > Nota: `stato_commessa` (`codice`) e `stato_codice_interno` (`codice_interno`) sono
  > due **colonne distinte** di `stati_commessa` (oggi con lo stesso valore nel seed, ma
  > separate per design: display vs chiave interna stabile) — non sono un duplicato.
- **Config testata**: `policy_fatturazione`, `fatturazione_immediata`,
  `priorita_operativa` (**stringa**, codice `NORMALE`/`ALTA`/`BASSA`, nullable — non un
  intero), `billing_account_id`, `utility_id`, `emittente_soggetto_ruolo_id`.
- **Contatori righe** `commesse_attivita`: `total_attivita`,
  `total_approvate` / `total_non_approvate`, `total_emesse` / `total_non_emesse`,
  `total_prezzo_da_riallineare`.
- `last_update` (ISO 8601, nullable): max tra update testata e ultima riga.
- `capabilities` (2026-06-16): blob data-driven da `script.fn_available_actions_commessa`
  (pattern gemello di ordini/preventivi/offerte/contratti):
  - `available_actions`: array delle **azioni di stato utente** ammesse dallo stato
    corrente (transizioni `meta.manuale=true` della matrice), ognuna con `key`
    (`chiudi`/`riapri`/`annulla`), `target_state` (codice stato destinazione),
    `label_key` (i18n), `severity`, `icon`, `requires_confirm`, `outlined` — pensate per
    renderizzare i pulsanti FE senza logica cablata. Array vuoto negli stati terminali;
  - `can_change_state` (bool), `can_edit_righe` (= `modificabile`),
    `is_emittibile` (= `emittibile`), `stato_codice`.

I campi nullable possono valere `null` (es. `priorita_operativa`, `last_update`).

- `400`: `commessa_id` non valido (`E_COMMESSA_VALIDATION`)
- `404`: commessa non trovata (`E_COMMESSA_NOT_FOUND`)

---

## POST — Azione di stato utente

- Metodo: `POST`
- Path: `/api/v1/vendite/commesse/<commessa_id>/stato/`
- Header: `Authorization: Bearer <token>` + **`Idempotency-Key` obbligatoria**
- Body JSON:
  - `nuovo_stato` (string) — **codice stato di destinazione** (`target_state` preso da una
    delle `capabilities.available_actions`, es. `CHIUSA` / `IN_ESECUZIONE` / `ANNULLATA`).

Output `200`:

```json
{ "data": { "commessa_id": 1, "stato_da": "PRONTA_FATTURAZIONE", "stato_a": "CHIUSA" },
  "meta": { ... } }
```

Errori:

- `400` `E_COMMESSA_VALIDATION` — `commessa_id` ≤ 0 o `nuovo_stato` mancante;
- `404` `E_COMMESSA_NOT_FOUND` — commessa inesistente;
- `409` `E_COMMESSA_AZIONE_NON_AMMESSA` — `nuovo_stato` non è tra le azioni utente ammesse
  (difesa applicativa: respinge anche le transizioni **automatiche** — ponte
  push/emittibilità — che il guard DB accetterebbe);
- `472` `E_COMMESSA_STATO_TRANSIZIONE_INVALIDA` / `473` `E_COMMESSA_NESSUNA_RIGA_APPROVATA`
  — sollevati dal guard DB se la coppia non è in matrice / precondizione non soddisfatta.

## Regole

- **GET** read-only, nessuna `Idempotency-Key`. **POST** write, `Idempotency-Key` obbligatoria.
- Endpoint v1 richiede JWT.
- `commessa_id` deve essere > 0, altrimenti errore di validazione.
- GET: stato, flag di governance e contatori calcolati nel DB in un round-trip
  (`fn_get_commessa_stato`) + capability da `fn_available_actions_commessa`.
- POST: la transizione effettiva e le precondizioni di matrice restano a
  `fn_cambia_stato_commessa` (guard DB); il service aggiunge la difesa applicativa
  "azione tra le available_actions" (impedisce di forzare via API le transizioni
  automatiche, che il guard DB non distingue dal flag `manuale`).
- Implementa il pattern standard `handle_post_json` (POST) / `success_response` (GET).

## Dipendenze DB

- `vendite.fn_get_commessa_stato` (stato + contatori)
- `script.fn_available_actions_commessa` (capability / azioni di stato)
- `vendite.fn_cambia_stato_commessa` (transizione sanzionata, guard di matrice)
- `vendite.commesse`, `vendite.commesse_attivita`, `vendite.transizioni_stati_commessa`,
  `vendite.stati_commessa`
