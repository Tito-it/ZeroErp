# fn_group_attivita_fatturabili (Django)

## Scopo
Costruire in Django la chiave di aggregazione delle attivita fatturabili.

> ⚠️ **Il nome e` quello dell'entrypoint Python** (`pipeline_service.fn_group_attivita_fatturabili`),
> **non** di una funzione SQL. La funzione DB omonima **non esiste piu`**: rimossa
> il 2026-07-28 col changeset `20260728-21`.

## Contesto
La logica di `vendite.fn_group_attivita_fatturabili()` (funzione DB **rimossa**) e` stata portata in:
- `apps/vendite/services/fatture_righe_service.py` (`group_attivita_fatturabili`)
- `apps/vendite/services/pipeline_service.py` (`fn_group_attivita_fatturabili`)

## Input
- `attivita_id`

## Output
- `group_key` strutturata (dict): articolo, destinazione, uom, prezzo, **IVA**,
  competenza, regole di arrotondamento, rettifica e **atto**.

## Regole
- Deterministica e stabile.
- `dest_billing_account_id` e` sempre BA reale da attivita.
- `uom_id` usa fallback da articolo se assente su attivita.
- Competenza valorizzata solo se diversa dalla singola data attivita.
- Error handling centralizzato via `ErrorManager`.

### ⛔ `iva_id` NON viene piu` dall'articolo (2026-08-31, `I4`)

Fino a quella data la proiezione leggeva `art.iva_id`, e quella era la risposta:
la **nona** risposta autonoma alla domanda «che IVA ha questa riga», che
scavalcava l'uso della fornitura e i **titoli documentati del cliente**. Su un
esportatore abituale scriveva l'aliquota piena, in fattura, senza sintomo.

Ora l'IVA la risolve `vendite.fn_resolve_iva_riga` (via `IvaResolverService`) e
arriva a `_build_group_key` come **parametro esplicito**.
⭐ Togliendo `art.iva_id` non si perde niente: l'aliquota dell'articolo e` lo
**stadio A1** del risolutore, che la ritorna con `origine = 'ARTICOLO'`.
⛔ `iva_id` e` un parametro e non un campo della riga apposta: se fosse rimasto
sulla dataclass con un default, un chiamante distratto avrebbe prodotto righe a
IVA `None` **senza nessun errore**.

⚠️ **Sulla RETTIFICA vince la riga rettificata**, non il risolutore (`N-1`, «la
nota di credito non puo` differire da quanto fatturato»): li` il risolutore non
viene nemmeno interrogato.

### ⛔ `contratto_id` sta nella chiave (2026-08-31)

Era un **difetto vivo**: due attivita` di contratti **diversi** collassavano
nella stessa riga di fattura, e su quella riga aggregata nessuna domanda per atto
ha una risposta — a partire dal CIG, che la FatturaPA vuole per blocco
`DatiContratto`.

⭐ **Non sposta nessun raggruppamento esistente**: fuori da un contratto il
valore e` `NULL` per tutte le attivita`, quindi si spezzano SOLO le righe che
mescolavano davvero due atti.
⚠️ Sulla **rettifica** vale `NULL`, ed e` deliberato: l'identita` di una riga di
nota di credito e` la riga che rettifica, piu` specifica del contratto. Dargli
peso potrebbe spezzare due rettifiche della **stessa** riga su un dato
incoerente a monte.

### ⚠️ La facade a singola attivita` e` DIAGNOSTICA

`pipeline_service.fn_group_attivita_fatturabili(attivita_id)` risolve l'IVA su
un contesto **ridotto** — l'attivita` puo` non avere ancora una testata, quindi
il cliente e` il suo billing account e la data e` quella dell'attivita`.
⛔ **L'autorita` e` `generate_fatture_righe`**, che legge cliente, emittente e
data dalla **TESTATA**. Su un'attivita` la cui fattura porta una data diversa, le
due risposte possono legittimamente non coincidere.

## Dipendenze DB
- Tabelle `vendite.attivita_fatturabili` (compresa `contratto_id`),
  `catalogo.articoli`, `vendite.articolo_regole_fatturazione`.
- `vendite.fn_resolve_iva_riga` (l'IVA della riga) e, tramite lui,
  `anagrafiche.soggetti_titoli_iva` — che ha la **RLS**.
- `anagrafiche.fn_get_emittente_fiscale_pk` per il contesto della testata.
  ⛔ La **PK** dell'emittente, non il `soggetto_ruolo_id` che la testata porta:
  con quello sbagliato il risolutore non trova i titoli e risponde con
  l'ordinaria **senza sollevare**.

## Matrice responsabilita` (Python vs DB)
- Python: composizione chiave di grouping, validazioni input, politica errori.
- DB: source of truth dei dati (attivita/articolo/regole) e vincoli di integrita`.

## Note di migrazione
- Stato attuale: migrazione completata lato Python (dal 2026-02-03, commit `ece04a5ff`).
- **La funzione SQL e` stata RIMOSSA** il 2026-07-28 (changeset `20260728-21`),
  insieme a `vendite.fn_generate_fatture_righe` che era il suo unico chiamante.

  ⚠️ Qui prima si leggeva: *«la funzione SQL puo` restare come compatibilita`
  storica/transitoria»*. Vale la stessa avvertenza del manuale gemello: quella
  formula ha reso indistinguibile un residuo da un'implementazione viva, e ci si
  e` sviluppato sopra per un giorno. Storia completa:
  `docs/it/dev/work-in-progress/brief-db-ritiro-generatore-righe-fattura-sql.md`.
