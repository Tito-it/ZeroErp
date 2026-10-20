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

**Permesso**: i tre endpoint hanno `post_permission = "prezzo_override_manuale"`
(area `vendite`); senza l'azione → `403 E_PERMISSION_DENIED` dal cancello della view.

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
invocando il resolver listino (`PricingService.resolve_prezzo` →
`vendite.fn_resolve_prezzo_listino_v2`) con il contesto dell'attivita`. Cosa si chiede
al resolver e cosa si scrive della risposta lo decide il building block
`apps/vendite/services/prezzo_riga_commessa.py`, lo stesso del push sorgente → commessa.

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

- Guard: commessa modificabile (data-driven su `stati_commessa.modificabile`, non su codici di stato)
- Guard: riga non `RETTIFICA` (il prezzo di una rettifica è quello della riga di fattura che corregge)
- Guard: `fattura_riga_id IS NULL` (non ancora fatturata)
- Guard: `prezzo_bloccato == FALSE` (non override manuale — per riallineare prima sbloccare)
- Il resolver riceve il contesto completo:
  - dalla riga: articolo, unita' di misura, data (`data_attivita`, o `competenza_mese` se
    manca), e il kit di cui la riga e' componente (`meta.componente_di`, stadio BUNDLE del
    resolver: il componente prende il prezzo che ha dentro il kit, non quello sciolto);
  - dalla commessa padre: `billing_account_id`, `utility_id`, `emittente_soggetto_ruolo_id`.
- Il prezzo e' `prezzo_finale` del resolver; con il prezzo si riscrive la sua
  **provenienza**: `listino_versione_id`, `prezzo_base_snapshot`, `origine_prezzo`,
  variazione applicata, promo, contratto, categoria e classe utenza. L'origine dello stadio
  kit (`LISTINO_BUNDLE`) non e' fra quelle ammesse dal CHECK della colonna e resta `NULL`.
- La versione confrontata e' quella registrata sulla riga (dal push, o dall'ultimo
  riallineamento): dopo un riallineamento confermato la riga porta la versione nuova, e il
  successivo non chiede piu' conferma.
- Lock `FOR UPDATE` su `commesse_attivita` dentro la transazione
- Audit in `commesse_attivita.meta.riallineamenti[]`
- Propaga prezzo e provenienza su `attivita_fatturabili` (solo righe non fatturate;
  `listino_versione_id` sta solo sulla riga di commessa)

### Errori tipici

- `404` `E_COMMESSA_ATTIVITA_NOT_FOUND`: riga inesistente, di un'altra commessa o fuori scope
- `400` `E_COMMESSA_VALIDATION`: prezzo bloccato, riga o commessa senza un dato che il
  listino chiede (articolo, unita' di misura, data, cliente, utility, emittente)
- Gli errori del resolver (`E_VENDITE_PRICING_FAILED` o il codice originale del DB, per
  esempio `E_PREZZO_LISTINO_RIGA_NON_TROVATA`): il listino non sa dare un prezzo alla riga
- `409` `E_VENDITE_VARIAZIONE_PREZZO_NON_AMMESSA`: commessa non modificabile, riga fatturata
- `409` `E_COMMESSA_ATTIVITA_PREZZO_RETTIFICA_IMMUTABILE`: riga `RETTIFICA`

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

- Guard: commessa modificabile (data-driven su `stati_commessa.modificabile`, non su codici di stato)
- Guard: riga non `RETTIFICA` (il prezzo di una rettifica è quello della riga di fattura che corregge)
- Guard: `fattura_riga_id IS NULL` (non ancora fatturata)
- Guard: `prezzo_bloccato == FALSE` (DEC-3: su prezzo già bloccato prima si sblocca, poi si varia)
- Imposta `prezzo_bloccato = TRUE` dopo la modifica
- Il prezzo dichiara di essere scritto a mano: `origine_prezzo = 'MANUALE'`, e la
  provenienza da listino (`listino_versione_id`, `prezzo_base_snapshot`, variazione, promo,
  contratto, categoria, classe utenza) torna `NULL`. La versione di riferimento resta
  nell'audit (`listino_versione_id_riferimento`)
- Lock `FOR UPDATE` su `commesse_attivita` dentro la transazione
- Audit in `commesse_attivita.meta.variazioni_eccezionali[]` con data, operatore,
  prezzo precedente/nuovo, motivo, stato commessa, listino_versione_id di riferimento
- Propaga prezzo e provenienza su `attivita_fatturabili` (solo righe non fatturate)

### Errori tipici

- `404` `E_COMMESSA_ATTIVITA_NOT_FOUND`: riga inesistente, di un'altra commessa o fuori scope
- `400` `E_COMMESSA_VALIDATION`: prezzo non valido, motivo mancante o troppo lungo
- `409` `E_VENDITE_VARIAZIONE_PREZZO_NON_AMMESSA`: commessa non modificabile, riga fatturata, prezzo già bloccato
- `409` `E_COMMESSA_ATTIVITA_PREZZO_RETTIFICA_IMMUTABILE`: riga `RETTIFICA`

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

- Guard: commessa modificabile (data-driven su `stati_commessa.modificabile`, non su codici di stato)
- Guard: riga non `RETTIFICA` (il prezzo di una rettifica è quello della riga di fattura che corregge)
- Guard: `fattura_riga_id IS NULL` (non ancora fatturata)
- Guard: `prezzo_bloccato == TRUE` (nulla da sbloccare se gia` libero)
- Ricalcola prezzo e provenienza come il riallineamento (§1: stesso contesto, stesso
  building block), senza il guard sulla versione
- Imposta `prezzo_bloccato = FALSE`
- Lock `FOR UPDATE` su `commesse_attivita` dentro la transazione
- Audit in `commesse_attivita.meta.sblocchi_prezzo[]`
- Propaga prezzo e provenienza su `attivita_fatturabili` (solo righe non fatturate)

### Errori tipici

- `404` `E_COMMESSA_ATTIVITA_NOT_FOUND`: riga inesistente, di un'altra commessa o fuori scope
- `400` `E_COMMESSA_VALIDATION`: motivo mancante o troppo lungo, riga o commessa senza un
  dato che il listino chiede
- Gli errori del resolver, come per il riallineamento
- `409` `E_VENDITE_SBLOCCO_PREZZO_NON_AMMESSO`: prezzo non bloccato
- `409` `E_VENDITE_VARIAZIONE_PREZZO_NON_AMMESSA`: commessa non modificabile, riga fatturata
- `409` `E_COMMESSA_ATTIVITA_PREZZO_RETTIFICA_IMMUTABILE`: riga `RETTIFICA`

---

## Regole trasversali

- Tutti gli endpoint richiedono JWT.
- I 3 endpoint usano `handle_post_json(...)` (metodo POST).
- Lock pessimistico `FOR UPDATE` su `commesse_attivita` in tutte le operazioni di update prezzo.
- Propagazione prezzo su `attivita_fatturabili` limitata a righe con `fattura_riga_id IS NULL`.
- Permesso: `post_permission = "prezzo_override_manuale"` su tutti e tre; in più la
  traccia audit nel `meta`.
- Ordine dei guard: riga (404) → commessa modificabile → non fatturata → non rettifica →
  guard specifico dell'azione.

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
  - `vendite.fn_resolve_prezzo_listino_v2(...)` (via `PricingService.resolve_prezzo`) — usato da N5 e N7-sblocco per ricalcolo
  - `vendite.trgfn_commesse_attivita_guard_prezzo_rettifica` — blocco a DB del prezzo delle righe `RETTIFICA`

## Note di migrazione

- Colonna `listino_riga_id` aggiunta a `commesse_attivita` e `attivita_fatturabili` nel DB
  (2026-04-12) — prerequisito per N6 (check propagazione) e tracciabilita` prezzo.
- Il nome `prezzo_unitario` su `attivita_fatturabili` corrisponde a `prezzo_snapshot` su
  `commesse_attivita` — naming diverso per dominio (commessa vs fatturazione), stessa semantica.

---

*API Commesse Pricing — ZeroERP (aprile 2026)*
