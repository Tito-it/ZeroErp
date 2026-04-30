# API Approvazioni prezzo (workflow L3)

## Scopo

Workflow **L3 approvazione out-of-policy** per override prezzo che violano
i limiti L2 configurati: l'operatore richiede approvazione, l'approver
(utente con `approva_prezzo_override`) decide approva/rifiuta dalla coda
dedicata.

Riferimento concettuale:
[sviluppo-listini-v5.md](/dev/work-in-progress/sviluppo-listini-v5) §14.6
e guida operativa [gestione-listini.md §6.1](/guide/gestione-listini#61-l3-workflow-approvazione-out-of-policy-sprint-e).

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

- `trgfn_preventivi_guard_transizione_approvazione`: blocca transizione preventivo → ACCETTATO se esistono righe PENDING (`E_PREVENTIVO_RIGHE_PRICING_PENDENTI`)
- `trgfn_preventivi_righe_guard_pending`: allowlist su righe PENDING (ammessi solo `stato_approvazione_prezzo`, `pratica_approvazione_prezzo_id`, `meta`); modifica struttura -> `E_RIGA_PREZZO_PENDENTE`

## Endpoint

### 1. Approva richiesta

- Metodo: `POST`
- Path: `/api/v1/vendite/righe/{riga_id}/approva-prezzo/`
- Auth: `vendite` + `post_permission = "approva_prezzo_override"` (oppure superuser)
- Header: `Idempotency-Key` raccomandato (gestito da `handle_post_json`)
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
  - `E_PREV_OVERRIDE_NON_AUTORIZZATO` (403) — utente senza azione `approva_prezzo_override`. **Defense-in-depth**: check eseguito PRIMA del lookup riga (no leak su esistenza)
  - `E_PREV_RIGA_NOT_FOUND` (404) — riga inesistente
  - `E_APPROVAZIONE_PREZZO_NON_AMMESSA` (409) — riga non in stato `PENDING` o senza pratica collegata (stato inconsistente)

---

### 2. Rifiuta richiesta

- Metodo: `POST`
- Path: `/api/v1/vendite/righe/{riga_id}/rifiuta-prezzo/`
- Auth: `vendite` + `post_permission = "approva_prezzo_override"` (oppure superuser)
- Header: `Idempotency-Key` raccomandato
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
- Auth: `vendite` LETTURA (l'approver agisce con `approva_prezzo_override` su singolo POST)
- Throttling: `is_search_endpoint = True`
- Query params:
  - `limit` (int, default 50, max 200, clamp via `apps.core.api.constants.MAX_LIMIT`)
  - `offset` (int, default 0)
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
    "limit": 50,
    "offset": 0
  }
}
```

- Filtra automaticamente:
  - `tipo_prestazione_id = 9001` (codice `APPROVAZIONE_PREZZO`)
  - `stato_codice_interno = 'APERTA'`
  - `emittente_fiscale_id` derivato da `PermissionResolver.get_emittente_for_user` (operatore singolo emittente)
- **Capability per item (Fase 5.B1)**: ogni item della coda ha `can_approve`/`can_reject`/`action_reason`. Permesso utente calcolato 1 volta (azione `approva_prezzo_override`); per-item solo la verifica `meta.riga_preventivo_id`. Codici stabili `action_reason` esposti come costanti modulo BE (`ACTION_REASON_PERMESSO_MANCANTE`, `ACTION_REASON_RIGA_NON_LINKATA`):

| `action_reason` | Quando | Effetto FE |
| --- | --- | --- |
| `null` | Tutto OK: utente HA permesso + riga linkata | Bottoni Approva/Rifiuta abilitati |
| `PERMESSO_MANCANTE` | Utente senza azione `approva_prezzo_override` (e non superuser) | Bottoni disabilitati + tooltip i18n `approvazioni_prezzo.reason_permesso_mancante` |
| `RIGA_NON_LINKATA` | `meta.riga_preventivo_id` assente (pratica legacy o crash post-create_riga) | Bottoni disabilitati + tooltip i18n `approvazioni_prezzo.reason_riga_non_linkata` |

- Errori:
  - `E_PREV_OVERRIDE_NON_AUTORIZZATO` (403) — utente non autenticato
  - `E_APPROVAZIONE_PREZZO_NON_AMMESSA` (409) — admin globale senza emittente assegnato (la coda è multi-tenant per emittente; admin globale deve usare `cerca_pratiche` generico per cross-tenant)

---

## Codici errore (sintesi)

| Codice | HTTP | Contesto |
|---|---|---|
| `E_PREVENTIVO_RIGHE_PRICING_PENDENTI` | 409 | Trigger DB su transizione preventivo → ACCETTATO con righe PENDING |
| `E_RIGA_PREZZO_PENDENTE` | 409 | Trigger DB su modifica struttura riga PENDING |
| `E_APPROVAZIONE_PREZZO_NON_AMMESSA` | 409 | Service: riga non PENDING, senza pratica, oppure approver senza emittente |
| `E_PREV_OVERRIDE_NON_AUTORIZZATO` | 403 | Auth: utente non autenticato o senza `approva_prezzo_override` |

## Riferimenti

- Pattern richiesta dal preventivo: vedi `api_preventivi.md` §8 (aggiungi riga) e §9 (aggiorna riga)
- Service backend: `apps/vendite/services/approvazioni_prezzo_service.py`
- Building block: [catalogo-building-block-backend](../../../dev/backend/catalogo-building-block-backend) sezione `approvazioni_prezzo_service.*`
- Guida utente: [gestione-listini §6.1](/guide/gestione-listini#61-l3-workflow-approvazione-out-of-policy-sprint-e)
- ChangeSet DB: `20260422-03..07` + seed CSV `azioni_processo` id 10 + `tipi_prestazione` id 9001 + `messaggi_errore` 389/390
