# Brief DB — Preventivi: `annulla` ammessa solo da BOZZA

**Sessione**: 2026-05-21
**Branch target**: `dev/db-tid`
**Tipo**: data fix `config.transizioni_stati_preventivi` (no DDL)

## Sintesi

Restringere la transizione `ANNULLATO` per i preventivi: deve essere ammessa
**solo** da `DRAFT` (BOZZA). Disattivare la transizione manuale verso
`ANNULLATO` da `EMESSO` e da `ACCETTATO`.

## Stato attuale

Secondo [docs/it/dbzero/script/manual/fn_available_actions_preventivo.md](../../dbzero/script/manual/fn_available_actions_preventivo.md):

| `stato_codice` | Azioni disponibili |
| --- | --- |
| `DRAFT` | `emetti`, `annulla` |
| `EMESSO` | `accetta`, `rifiuta`, **`annulla`** |
| `ACCETTATO` | **`annulla`** |
| `ANNULLATO` / `RIFIUTATO` / `SCADUTO` | `[]` |

Il drawer FE preventivi e' data-driven (`script.fn_available_actions_preventivo`),
quindi mostra il bottone "Annulla" su EMESSO e ACCETTATO — comportamento non
voluto.

## Stato target

| `stato_codice` | Azioni disponibili |
| --- | --- |
| `DRAFT` | `emetti`, `annulla` |
| `EMESSO` | `accetta`, `rifiuta` |
| `ACCETTATO` | `[]` (eventualmente solo `evade` se gia' previsto) |

## Razionale di dominio

- **EMESSO**: il preventivo e' stato spedito al cliente. La negazione
  semantica corretta non e' "annullamento" ma "rifiuto" (`EMESSO → RIFIUTATO`,
  e' il cliente che rifiuta), gia' presente in matrice. Eliminare `annulla`
  evita confusione fra "io annullo cio' che ho mandato" (semantica
  scivolosa, audit-unfriendly) e "il cliente rifiuta" (semantica
  registrata correttamente).
- **ACCETTATO**: il preventivo accettato ha gia' attivato downstream
  (preparazione fatturazione, push commessa, attivita' fatturabili). Annullare
  invaliderebbe operazioni a valle gia' partite. Coerente col pattern
  contratti: `DRAFT → ANNULLATO` ammesso, post-attivazione si usa `CESSATO`
  (con data) — qui l'equivalente per preventivi accettati e' tipicamente la
  creazione di una nuova revisione.

Pattern simmetrico ai contratti (sessione 2026-05-20):
`DRAFT → ANNULLATO` ok; post-DRAFT no.

## Modifica DB richiesta

Migration in `db/changelog/migrations_v2/80_data/` (o equivalente, no DDL):

```sql
-- Disattiva la transizione manuale EMESSO -> ANNULLATO
UPDATE config.transizioni_stati_preventivi
   SET attivo = FALSE,
       user_update = 'mctit',
       data_update = NOW()
 WHERE stato_da_id = (SELECT id FROM config.stati_doc_preventivi WHERE codice_interno = 'EMESSO')
   AND stato_a_id  = (SELECT id FROM config.stati_doc_preventivi WHERE codice_interno = 'ANNULLATO');

-- Disattiva la transizione manuale ACCETTATO -> ANNULLATO
UPDATE config.transizioni_stati_preventivi
   SET attivo = FALSE,
       user_update = 'mctit',
       data_update = NOW()
 WHERE stato_da_id = (SELECT id FROM config.stati_doc_preventivi WHERE codice_interno = 'ACCETTATO')
   AND stato_a_id  = (SELECT id FROM config.stati_doc_preventivi WHERE codice_interno = 'ANNULLATO');
```

Preferenza per `UPDATE attivo=FALSE` rispetto a DELETE: preserva audit trail
delle righe storiche. La fn `script.fn_available_actions_preventivo` filtra
gia' su `attivo IS TRUE` (riga 108 della doc), quindi righe disattivate
spariscono automaticamente dall'output.

## Verifica post-migration

```sql
-- Atteso: solo "emetti", "annulla" da DRAFT; solo "accetta", "rifiuta" da EMESSO; [] da ACCETTATO
SELECT
    sd.codice_interno AS stato_da,
    sa.codice_interno AS stato_a,
    t.attivo, t.manuale
  FROM config.transizioni_stati_preventivi t
  JOIN config.stati_doc_preventivi sd ON sd.id = t.stato_da_id
  JOIN config.stati_doc_preventivi sa ON sa.id = t.stato_a_id
 WHERE t.attivo IS TRUE AND t.manuale IS NOT FALSE
 ORDER BY sd.codice_interno, sa.codice_interno;
```

Smoke FE: aprire un preventivo EMESSO → il bottone "Annulla" non deve apparire
nella DrawerActionsBar; aprire un preventivo ACCETTATO → nessuna azione di
cambio stato manuale visibile.

## Aggiornamento doc

Aggiornare [fn_available_actions_preventivo.md](../../dbzero/script/manual/fn_available_actions_preventivo.md)
righe 92-97 (sezione "Dettaglio `available_actions` per stato") con la
matrice corretta.

## Impatto BE Python

Nessuno. La whitelist di transizioni in `preventivi_service.py` (se presente)
e' una difesa-in-depth ma non e' la fonte di verita': lo e' la tabella DB.
Verificare a stretta lettura se `_TRANSIZIONI_AMMESSE` o simile nel service
include `(EMESSO, ANNULLATO)` o `(ACCETTATO, ANNULLATO)` — se si', allineare
post-migration. Nessuna API rotta: il drawer FE recepisce il nuovo
`available_actions` senza modifiche.
