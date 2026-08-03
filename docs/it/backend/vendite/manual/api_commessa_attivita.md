# API commessa_attivita (Django)

## Scopo

Esporre via HTTP la lista paginata delle attività (`commesse_attivita`) di una commessa,
con filtri opzionali per stato emissione, stato approvazione e mese di competenza.

## Contesto

Endpoint applicativo che invoca il servizio Python `fn_list_commessa_attivita`
(`apps.vendite.services.commesse_service`), il quale delega a
`CommesseRepository.list_commessa_attivita()` che chiama la funzione DB
`vendite.fn_list_commessa_attivita`.

View: `ApiCommessaAttivita` `ApiCommessaAttivita` (`apps.vendite.api.views`).

## Input

- Metodo: `GET`
- Path canonico: `/api/v1/vendite/commesse/<commessa_id>/attivita/`
- Header sicurezza: `Authorization: Bearer <access_token>`
- Parametri path:
  - `commessa_id` (int) — ID della commessa
- Query params (tutti opzionali):
  - `stato_emissione` (string) — filtro stato emissione (es. `NON_EMESSA`, `EMESSA`)
  - `stato_approvazione` (string) — filtro stato approvazione (es. `BOZZA`, `APPROVATA`)
  - `competenza_mese` (date `YYYY-MM-DD`) — filtro mese di competenza (normalizzato al primo del mese dal DB)
  - `limit` (int) — righe per pagina (default 50, range 1-200)
  - `offset` (int) — offset paginazione (default 0)
  - `order_by` (string) — colonna di ordinamento, whitelist chiusa: `id`, `data_attivita`, `competenza_mese`, `segment_key`, `quantita`, `prezzo_snapshot`, `stato_approvazione`, `stato_emissione`. Assente = ordine storico per `id`
  - `order_dir` (string) — `asc` | `desc` (default `asc`)

## Output

- `200`: lista attività

```json
{
  "data": {
    "commessa_id": 1,
    "count": 3,
    "rows": [
      {
        "id": 100,
        "commessa_id": 1,
        "segment_key": "PREV:abc123:ITEM:1",
        "articolo_id": "550e8400-e29b-41d4-a716-446655440000",
        "istanza_utility_id": 5,
        "data_attivita": "2026-02-15",
        "uom_id": 1,
        "quantita": "10.00",
        "competenza_mese": "2026-02-01",
        "competenza_dal": "2026-02-01",
        "competenza_al": "2026-02-28",
        "prezzo_snapshot": "25.50",
        "prezzo_bloccato": false,
        "prezzo_da_riallineare": false,
        "stato_approvazione": "APPROVATA",
        "stato_emissione": "NON_EMESSA",
        "sorgente_tipo_id": 1,
        "sorgente_codice": "PREVENTIVO",
        "meta": {},
        "data_update": "2026-02-26T10:00:00+00:00"
      }
    ]
  },
  "meta": { ... }
}
```

- `400`: parametri non validi (`E_COMMESSA_VALIDATION`) — es. `limit` fuori range 1-200, `order_by` fuori whitelist, `order_dir` diverso da asc/desc
- `404`: commessa non trovata (gestito dalla funzione DB)

## Regole

- Endpoint read-only, nessuna `Idempotency-Key` richiesta.
- Endpoint v1 richiede JWT.
- `commessa_id` deve essere > 0, altrimenti errore di validazione.
- `limit` validato nel service: deve essere compreso tra 1 e 200.
- `competenza_mese` parsata via `optional_iso_date` e passata come `date` al repository.
- La funzione DB normalizza `competenza_mese` al primo del mese (`date_trunc`).
- JOIN su `config.sorgenti` per risolvere `sorgente_codice` (evita N+1 lato client).
- `count` indica il numero di righe restituite nella pagina corrente, non il totale globale.
- Ordinamento server-side (dal 2026-08-03, 7° lotto liste configurabili): `order_by`/`order_dir` sono validati nel service contro `ATTIVITA_SORT_COLUMNS` (specchio della whitelist chiusa dentro la fn DB, changeset `20260802-26`) e passati a `p_order_by`/`p_order_dir`. Ordine e paginazione vivono **dentro** la funzione: ordinare a valle ordinerebbe la sola pagina estratta. `order_by` assente = ordine storico `ca.id`; tiebreak `ca.id` sempre presente. La fn solleva `E_PARAMETRO_INVALIDO` su nome fuori whitelist (difesa in profondità, il service intercetta prima).
- Funzione DB STABLE (read-only).

## Dipendenze DB

- `vendite.fn_list_commessa_attivita(p_commessa_id, p_stato_emissione, p_stato_approvazione, p_competenza_mese, p_limit, p_offset, p_order_by, p_order_dir)` — funzione principale, restituisce TABLE con 21 colonne
- `vendite.commesse_attivita` — tabella dati
- `config.sorgenti` — JOIN per `sorgente_codice`

---

## Azione APPROVA — righe di una commessa (A-1, cockpit fatturazione)

### Scopo

Portare le attività della commessa da `stato_approvazione = BOZZA` ad `APPROVATA`
(prerequisito di riga per l'emissione verso `attivita_fatturabili`). È il verbo
**Approva** del cockpit Dashboard Competenza a grana riga/commessa
(design: `brief-design-gestione-processi-fatturazione.md` §3, decisione D-3).

### Input

- Metodo: `POST`
- Path: `/api/v1/vendite/commesse/<commessa_id>/attivita/approva/`
- Header: `Authorization: Bearer <token>` + `Idempotency-Key` (obbligatoria)
- Permesso: azione di processo **`approva_attivita_commessa`** (`post_permission`)
- Body JSON:
  - `righe_ids` (int[], opzionale) — righe da approvare; **assente = tutte** le
    righe `NON_EMESSA` in `BOZZA` della commessa. Lista vuota = `400` (per
    "tutte" omettere il campo).

### Output

- `200`: `{ "data": { "commessa_id": 42, "approvate": 5 } }` — `approvate` è il
  numero di righe effettivamente transitate (già `APPROVATA` = non contate:
  la fn DB è **idempotente**, seconda invocazione → 0).
- `400`: `E_COMMESSA_VALIDATION` — `commessa_id`/`righe_ids` non validi
- `403`: azione di processo non abilitata
- `404`: `E_COMMESSA_NOT_FOUND` — commessa inesistente

### Regole

- View `ApiCommessaAttivitaApprova` → service `approva_commessa_attivita` →
  `CommesseRepository.approva_commessa_attivita` → fn DB.
- Il service verifica l'esistenza della commessa prima della fn (404 parlante).
- La fn approva solo righe `BOZZA` **e** `NON_EMESSA`: le emesse non sono toccate.

### Dipendenze DB

- `vendite.fn_approva_commessa_attivita(p_commessa_id, p_righe_ids, p_user)`

---

## Azione APPROVA massiva per competenza (A-2, cockpit fatturazione)

### Scopo

Approvare in un colpo **tutte le attività in stadio `DA_APPROVARE` di un mese di
competenza** — esattamente la popolazione che la card `DA_APPROVARE` della
Dashboard Competenza mostra (stessa vista del drill-down, WYSIWYG). Verbo
**Approva** a grana mese (D-3).

### Input

- Metodo: `POST`
- Path: `/api/v1/vendite/fatturazione/approva-competenza/`
- Header: `Authorization: Bearer <token>` + `Idempotency-Key` (obbligatoria)
- Permesso: azione di processo **`approva_attivita_commessa`**
- Body JSON:
  - `competenza_mese` (date `YYYY-MM-DD`, **obbligatoria**) — normalizzata al 1° del mese
  - `commessa_ids` (int[], opzionale) — restringe al subset di commesse del mese

### Output

- `200`: `{ "data": { "competenza_mese": "2026-07-01", "commesse": 2, "approvate": 3 } }`
  — perimetro vuoto = contatori a zero (non è un errore).
- `400`: `E_COMMESSA_VALIDATION` — mese mancante / liste non valide
- `403`: azione di processo non abilitata

### Regole

- View `ApiFatturazioneApprovaCompetenza` → service `approva_attivita_competenza`.
- Popolazione da `vendite.vw_dash_competenza_attivita` (`stadio = 'DA_APPROVARE'`,
  `competenza_mese = M`): **scope emittente applicato in-vista** (GUC
  `app.current_user_id`, `security_invoker`) — l'operatore approva solo il suo
  perimetro, per costruzione.
- **All-or-nothing**: il loop per commessa gira in UNA `transaction.atomic()`
  (guardrail «una azione = una unità atomica»); un errore su una commessa
  annulla tutto. Il retry è innocuo (fn idempotente).

### Dipendenze DB

- `vendite.vw_dash_competenza_attivita` (read, selezione popolazione)
- `vendite.fn_approva_commessa_attivita` (write, per commessa)

---

## Azione ANNULLA — riga MANUALE di commessa

### Scopo

Togliere dal giro una **voce manuale** (tipicamente un onere) caricata per
errore — causale sbagliata, importo sbagliato, doppio click. Fino al 2026-07-28
non c'era rimedio: nessun DELETE, l'onere di storno negativo è vietato per
costruzione (`fn_aggiungi_onere_commessa` rifiuta `importo <= 0`) e la
variazione prezzo eccezionale esige `prezzo > 0` — una penale da 500 € inserita
per sbaglio poteva diventare da 1 €, **non sparire**.

La riga **non si cancella**: passa a `stato_emissione = 'ANNULLATA'`, il terzo
valore del CHECK già onorato da tutte le porte a valle. È il libro giornale:
annullare senza cancellare, con il motivo tracciato. Nessun «ripristina» — se
serve, si ricarica l'onere.

Brief: `docs/it/dev/work-done/brief-annullamento-righe-manuali-commessa.md`.

### Input

- Metodo: `POST`
- Path: `/api/v1/vendite/commesse/<commessa_id>/attivita/<att_id>/annulla/`
- Header: `Authorization: Bearer <token>` + `Idempotency-Key` (obbligatoria)
- Permesso: azione di processo **`carica_voce_manuale`** — lo **stesso** della
  porta oneri (decisione Tid): chi può caricare una voce manuale può annullarla,
  nessun permesso dedicato.
- Body JSON:
  - `motivo` (string, **obbligatorio**, max 500) — l'annullamento è
    irreversibile e l'unica traccia del *perché* è l'evento di log.

### Output

- `200`: `{ "data": { "commessa_id": 42, "attivita_id": 501, "stato_emissione": "ANNULLATA", "motivo": "causale sbagliata" } }`
- `400`: `E_RIGA_COMMESSA_MOTIVO_OBBLIGATORIO` — motivo assente, vuoto o oltre i 500 caratteri
- `403`: azione di processo non abilitata
- `404`: `E_COMMESSA_ATTIVITA_NOT_FOUND` — riga inesistente **oppure non
  appartenente alla commessa dell'URL** (nessun leak fra i due casi)
- `409`: `E_RIGA_COMMESSA_GIA_ANNULLATA` / `E_RIGA_COMMESSA_NON_MANUALE` /
  `E_RIGA_COMMESSA_GIA_EMESSA` / `E_VENDITE_VARIAZIONE_PREZZO_NON_AMMESSA`
  (commessa non più modificabile)

### Regole

- View `ApiCommessaAttivitaAnnulla` → service `annulla_attivita_manuale` →
  `CommesseRepository.annulla_attivita` → madre DB.
- **Scoping riga↔commessa esplicito**: il service rilegge la riga con
  `_get_attivita_pricing_or_raise(commessa_id, attivita_id)`, la cui `WHERE`
  filtra su entrambi gli id. Senza, il `commessa_id` dell'URL sarebbe decorativo
  e si annullerebbe la riga di un altro cliente indovinando un intero.
  **La RLS non copre il buco**, ma non perché sia dormiente: la policy
  `rls_commesse_attivita_ef_whitelist` **si applica** all'app (`zeroerp_app` non
  è owner della tabella — l'owner è `titodb` — e non ha `BYPASSRLS`; `NO FORCE`
  esenta il solo owner). Risponde però a una domanda **diversa**: «l'operatore è
  nella whitelist dell'emittente di questa commessa?», non «questa riga
  appartiene alla commessa nell'URL?». Un operatore autorizzato sull'emittente X
  può quindi ancora colpire la riga di un'**altra** commessa dello stesso
  emittente: il guard applicativo è l'unico che chiude quel caso.
- **Guard «commessa modificabile»** (data-driven su `stati_commessa.modificabile`):
  annullare una riga *è* modificare la commessa, come le tre azioni prezzo
  sorelle. Vive nel BE e **non** scende nella madre — il gemello
  `fn_aggiungi_onere_commessa` non fa quel lookup.
- **Ordine dei guard**, identico a quello della madre e non indifferente:
  1. *già annullata* — una riga `ANNULLATA` è per costruzione manuale, quindi in
     testa non toglie il posto a una diagnosi migliore. Codice **dedicato**:
     dire «è entrata nella catena di fatturazione» a chi ha cliccato due volte è
     un'informazione **falsa**, e lo manda a cercare una fattura che non esiste.
  2. *non manuale* — **prima** di «già emessa» perché è l'**identità** della
     riga, non una sua condizione: a una riga da push dire «già emessa»
     suggerisce che, se non lo fosse, si potrebbe annullare (falso — il rimedio
     è a monte, sul documento).
  3. *già emessa* — la riga ha già generato un'`attivita_fatturabili`:
     annullarla qui la lascerebbe orfana in viaggio verso la fattura.
- Discriminante di «riga manuale» = **`sorgente_tipo_id IS NULL`** (sourceless),
  la stessa definizione con cui `fn_build_gruppo_fatturabile_key` costruisce il
  gruppo `MAN:<commessa_id>`. **Non** `tipo_movimento = 'ONERE'` (è la natura del
  movimento, non l'origine: il CHECK ammette già `RETTIFICA`) né
  `segment_key LIKE 'MAN:%'` (i prefissi sono una convenzione di leggibilità,
  non un contratto). ⚠️ Il giorno che nasce un **secondo** tipo di riga
  sourceless questo perimetro va **riletto**, non dato per buono: `carica_voce_manuale`
  lo coprirebbe automaticamente.
- I guard applicativi arrivano prima nel caso normale, ma **la madre resta
  l'ultima parola**: sotto `SELECT ... FOR UPDATE` intercetta le corse (due
  annullamenti simultanei, un'emissione concorrente) che la rilettura
  applicativa non vede. I suoi codici sono tradotti 1:1 dal service
  (`_ANNULLA_DB_ERROR_MARKERS`), mai appiattiti su `E_DATABASE`.
- Nessun `transaction.atomic()`: una sola `SELECT` di funzione madre = unità
  atomica per costruzione (UPDATE + evento di log insieme).

### Effetti a valle (nessun filtro nuovo da scrivere)

`ANNULLATA` era già onorato ovunque conti — è questa la ragione per cui il
lavoro DB è stato *una funzione* e non «colonna + backfill + filtri»:

| Dove | Effetto |
| --- | --- |
| `fn_emit_attivita_fatturabili_da_commessa` | filtra `NON_EMESSA` → **mai in fattura** |
| `fn_list_commesse_emittibili` / `fn_list_emittibili_lane` | nessuna terna, nessun lotto |
| `vw_dash_competenza_attivita` / `vw_dash_competenza_gruppi` | sparisce dal cockpit |
| `vw_dash_fatturazione_commesse` | idem |
| `fn_approva_commessa_attivita` | filtra `NON_EMESSA` → **non ri-approvabile** (il «nessun ripristina» è strutturale) |
| `script.fn_check_commessa_chiudibile` | annullare **sblocca la chiusura** della commessa, prima incastrata fra il guard di uscita e un onere non togliibile |
| `fn_get_commessa_stato` | `total_approvate`/`total_non_approvate`/`total_non_emesse`/`total_prezzo_da_riallineare` escludono le annullate; `total_attivita` resta il conteggio **fisico** (la riga esiste) |

### Dipendenze DB

- `vendite.fn_annulla_commessa_attivita(p_commessa_attivita_id, p_motivo) → bigint`
  — madre: `FOR UPDATE` + guard + `UPDATE stato_emissione` + evento
  `RIGA_MANUALE_ANNULLATA` su `vendite.commesse_attivita_log`
- `config.messaggi_errore` ids **564-567** (i quattro codici sopra)
- `vendite.commesse_attivita.stato_emissione` — CHECK a tre valori
  (`NON_EMESSA` / `EMESSA` / `ANNULLATA`): **nessuna colonna nuova**
