# API Commesse — Operazioni Pricing (Vendite)

## Scopo

Esporre via HTTP le operazioni di gestione prezzo su attivita` di commessa:
riallineamento da listino (N5), variazione eccezionale manuale (N7) e sblocco
prezzo bloccato (N7-sblocco).

## Contesto

Tutti gli endpoint risiedono sotto `/api/v1/vendite/commesse/` e sono implementati in:

- `apps/vendite/api/views.py`
- `apps/vendite/services/commesse_service.py`
- `apps/vendite/db/commesse_repository.py`

Le API richiedono JWT (`Authorization: Bearer <token>`) e usano l'envelope standard
`{ "data": {}, "meta": { "request_id": "..." } }`.

## Base URL

```text
/api/v1/vendite/commesse/{commessa_id}/attivita/{att_id}/
```

---

## 1. Riallineamento prezzo (N5)

| | |
|---|---|
| **Metodo** | `POST` |
| **URL** | `/api/v1/vendite/commesse/{commessa_id}/attivita/{att_id}/riallinea-prezzo/` |

Ricalcola il prezzo di un'attivita` non ancora fatturata e non bloccata manualmente,
invocando il resolver listino (`fn_resolve_prezzo_listino`) con il contesto originale
dell'attivita` (BA, utility, emittente dalla commessa padre).

### Body JSON

| Campo | Tipo | Obbligatorio | Descrizione |
|---|---|---|---|
| `conferma_versione_diversa` | bool | No | Se `true`, forza il riallineamento anche se la versione listino e` cambiata |

### Risposta — versione invariata (200)

```json
{
  "data": {
    "attivita_id": 501,
    "prezzo_precedente": "45.0000000000",
    "prezzo_nuovo": "46.0000000000",
    "versione_cambiata": false
  }
}
```

### Risposta — versione cambiata, conferma richiesta (200)

Se la versione listino attuale e` diversa da quella nello snapshot originale,
l'endpoint restituisce un warning e non applica modifiche:

```json
{
  "data": {
    "versione_cambiata": true,
    "versione_originale_id": 101,
    "versione_attuale_id": 202,
    "prezzo_attuale": "45.0000000000",
    "prezzo_ricalcolato": "46.0000000000",
    "richiede_conferma": true
  }
}
```

Il frontend mostra un dialog di conferma e ripete la chiamata con
`conferma_versione_diversa: true` per forzare l'applicazione.

### Regole specifiche

- Guard: commessa in stato `LIBERO` o `CONFERMATO`
- Guard: `fattura_riga_id IS NULL` (non ancora fatturata)
- Guard: `prezzo_bloccato == FALSE` (non override manuale — per riallineare prima sbloccare)
- Il resolver riceve il contesto completo dalla commessa padre:
  `billing_account_id`, `utility_id`, `emittente_soggetto_ruolo_id`
- Lock `FOR UPDATE` su `commesse_attivita` dentro la transazione
- Audit in `commesse_attivita.meta.riallineamenti[]`
- Propaga prezzo su `attivita_fatturabili.prezzo_unitario` (solo righe non fatturate)

### Errori tipici

- `400` `E_COMMESSA_VALIDATION`: prezzo bloccato, commessa non trovata
- `409` `E_VENDITE_VARIAZIONE_PREZZO_NON_AMMESSA`: stato commessa non ammesso, riga fatturata

---

## 2. Variazione prezzo eccezionale (N7)

| | |
|---|---|
| **Metodo** | `POST` |
| **URL** | `/api/v1/vendite/commesse/{commessa_id}/attivita/{att_id}/variazione-prezzo-eccezionale/` |

Override manuale del prezzo su un'attivita` di commessa. Imposta `prezzo_bloccato = TRUE`
(il prezzo non sara` piu` ricalcolato dal resolver). Motivo obbligatorio.

### Body JSON

| Campo | Tipo | Obbligatorio | Descrizione |
|---|---|---|---|
| `prezzo` | decimal | Si | Nuovo prezzo, `> 0` |
| `motivo` | string | Si | Motivazione obbligatoria, max 500 caratteri |

### Risposta (200)

```json
{
  "data": {
    "attivita_id": 501,
    "prezzo_precedente": "45.0000000000",
    "prezzo_nuovo": "42.0000000000",
    "prezzo_bloccato": true,
    "motivo": "sconto eccezionale concordato con cliente per ordine annuale"
  }
}
```

### Regole specifiche

- Guard: commessa in stato `LIBERO` o `CONFERMATO`
- Guard: `fattura_riga_id IS NULL` (non ancora fatturata)
- Imposta `prezzo_bloccato = TRUE` dopo la modifica
- Conserva `listino_versione_id` originale per audit comparativo
- Lock `FOR UPDATE` su `commesse_attivita` dentro la transazione
- Audit in `commesse_attivita.meta.variazioni_eccezionali[]` con data, operatore,
  prezzo precedente/nuovo, motivo, stato commessa, listino_versione_id di riferimento
- Propaga prezzo su `attivita_fatturabili.prezzo_unitario` (solo righe non fatturate)

### Errori tipici

- `400` `E_COMMESSA_VALIDATION`: prezzo non valido, motivo mancante o troppo lungo
- `409` `E_VENDITE_VARIAZIONE_PREZZO_NON_AMMESSA`: stato commessa non ammesso, riga fatturata

---

## 3. Sblocca prezzo (N7-sblocco)

| | |
|---|---|
| **Metodo** | `POST` |
| **URL** | `/api/v1/vendite/commesse/{commessa_id}/attivita/{att_id}/sblocca-prezzo/` |

Sblocca un prezzo precedentemente bloccato (da variazione eccezionale) e ricalcola
dal resolver listino. Complemento naturale di N7: senza sblocco, un errore sulla
variazione richiede interventi manuali sul DB.

### Body JSON

| Campo | Tipo | Obbligatorio | Descrizione |
|---|---|---|---|
| `motivo` | string | Si | Motivazione obbligatoria, max 500 caratteri |

### Risposta (200)

```json
{
  "data": {
    "attivita_id": 501,
    "prezzo_bloccato_precedente": "42.0000000000",
    "prezzo_ricalcolato": "45.0000000000",
    "prezzo_bloccato": false,
    "motivo": "variazione eccezionale errata, ripristino prezzo da listino"
  }
}
```

### Regole specifiche

- Guard: commessa in stato `LIBERO` o `CONFERMATO`
- Guard: `fattura_riga_id IS NULL` (non ancora fatturata)
- Guard: `prezzo_bloccato == TRUE` (nulla da sbloccare se gia` libero)
- Ricalcola prezzo invocando il resolver con contesto completo dalla commessa
- Imposta `prezzo_bloccato = FALSE`
- Lock `FOR UPDATE` su `commesse_attivita` dentro la transazione
- Audit in `commesse_attivita.meta.sblocchi_prezzo[]`
- Propaga prezzo su `attivita_fatturabili.prezzo_unitario` (solo righe non fatturate)

### Errori tipici

- `400` `E_COMMESSA_VALIDATION`: motivo mancante o troppo lungo
- `409` `E_VENDITE_SBLOCCO_PREZZO_NON_AMMESSO`: prezzo non bloccato
- `409` `E_VENDITE_VARIAZIONE_PREZZO_NON_AMMESSA`: stato commessa non ammesso, riga fatturata

---

## Regole trasversali

- Tutti gli endpoint richiedono JWT.
- I 3 endpoint usano `handle_post_json(...)` (metodo POST).
- Lock pessimistico `FOR UPDATE` su `commesse_attivita` in tutte le operazioni di update prezzo.
- Propagazione prezzo su `attivita_fatturabili` limitata a righe con `fattura_riga_id IS NULL`.
- In futuro, le operazioni N7 e N7-sblocco dovrebbero richiedere un permesso specifico
  (`vendite.variazione_prezzo_eccezionale`). Per v1 la traccia audit nel `meta` e` il meccanismo
  di controllo sufficiente.

### Scope emittente (RLS, 2026-07-20)

Le tabelle `vendite.commesse` / `commesse_attivita` hanno RLS scope emittente
(`rls_commesse_ef_whitelist` + `rls_commesse_attivita_ef_whitelist`, EF whitelist
dell'operatore — vedi `analisi-attivazione-rls-operatori.md`). I 3 endpoint sono
**probe-first**: leggono l'attivita con `get_attivita_pricing` (SELECT su
`commesse_attivita JOIN commesse`, SECURITY INVOKER, quindi filtrata dalla RLS)
**prima** di qualsiasi UPDATE. Un'attivita di un emittente fuori dallo scope
dell'operatore e` **indistinguibile da una inesistente**: entrambe → **404
`E_COMMESSA_ATTIVITA_NOT_FOUND`**, nessun UPDATE eseguito (nessun no-op silenzioso
su UPDATE a 0 righe). Regressione blindata in
`test_prezzi_attivita_fuori_scope_o_inesistente_404`.

## Dipendenze DB

- Tabelle:
  - `vendite.commesse` (stato, billing_account_id, utility_id, emittente_soggetto_ruolo_id)
  - `vendite.commesse_attivita` (prezzo_snapshot, prezzo_bloccato, listino_versione_id, listino_riga_id, meta)
  - `vendite.attivita_fatturabili` (prezzo_unitario, prezzo_bloccato, fattura_riga_id)
- Funzioni SQL:
  - `vendite.fn_resolve_prezzo_listino(...)` — usato da N5 e N7-sblocco per ricalcolo

## Note di migrazione

- Colonna `listino_riga_id` aggiunta a `commesse_attivita` e `attivita_fatturabili` nel DB
  (2026-04-12) — prerequisito per N6 (check propagazione) e tracciabilita` prezzo.
- Il nome `prezzo_unitario` su `attivita_fatturabili` corrisponde a `prezzo_snapshot` su
  `commesse_attivita` — naming diverso per dominio (commessa vs fatturazione), stessa semantica.

---

*API Commesse Pricing — ZeroERP (aprile 2026)*
