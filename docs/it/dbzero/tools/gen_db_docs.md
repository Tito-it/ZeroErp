# Generatore della documentazione DB — `scripts/gen_db_docs.py`

> **Ultimo aggiornamento**: 24 ottobre 2026
>
> **Destinatari**: chi cambia il database e deve rigenerarne la documentazione; chi scrive le pagine `manual/`
>
> **Vedi anche**:
>
> * [Standard delle guide](/dev/standard-guide) — che cosa si scrive a mano (`manual/`) e che cosa no
> * [Configurazione GitHub](/dev/github/configurazione) — dove la CI rigenera la doc e pubblica il sito

---

## Che cosa fa

Legge il database **vivo** e scrive una pagina Markdown per ogni oggetto degli schemi elencati, sotto
`docs/it/dbzero/<schema>/`:

| Cartella     | Che cosa contiene                                                                                     |
| ------------ | ----------------------------------------------------------------------------------------------------- |
| `tabelle/`   | descrizione (dal `COMMENT`), colonne, vincoli, indici, trigger                                         |
| `funzioni/`  | firma e definizione completa di funzioni **e** procedure, un blocco per ogni firma                     |
| `views/`     | definizione delle viste, **anche materializzate** (con i loro indici)                                  |
| `manual/`    | ⛔ **non la tocca**: la scrivono le persone                                                            |
| `index.md`   | l'indice dello schema verso le pagine generate, con lo «scopo» preso dalla pagina `manual/` se c'è     |
| `index.ci.md`| l'indice dello schema verso le sole pagine `manual/`                                                  |

In più scrive `maintenance/job_pgagent.md`, l'elenco dei job pgAgent con il loro programma, se
l'estensione è installata (altrimenti la pagina si toglie).

Se esiste `docs/it/dbzero/<schema>/manual/<nome>.md`, la pagina generata la **include in testa**
(`include-markdown`): la spiegazione scritta a mano e il contratto letto dal database stanno nella
stessa pagina, ma in due file.

⛔ Le pagine di `tabelle/`, `funzioni/` e `views/` non si modificano a mano: alla prossima
generazione si riscrivono. Si scrive solo in `manual/`.

---

## Come si lancia

Dalla radice del progetto, con la venv degli strumenti di sviluppo (`requirements.txt` in radice,
che porta `psycopg` e `python-dotenv`):

```bash
python scripts/gen_db_docs.py
```

Lo lanciano anche `scripts/serve_docs.sh` e `scripts/serve_docs_static.sh`, prima dell'anteprima del
sito, e `ci.yaml` in CI.

### Configurazione

Le variabili si leggono da due file in radice: `internal.env` (locale, non committato, con le
credenziali; vince) e `git.env` (committato, i valori di default).

| Variabile          | A che cosa serve                                                                                          |
| ------------------ | --------------------------------------------------------------------------------------------------------- |
| `DATABASE_DSN`     | la connessione. In alternativa `DB_HOST`, `DB_PORT`, `DB_NAME`, `POSTGRESQL_USER`, `POSTGRESQL_PWD`         |
| `DB_DOC_SCHEMAS`   | gli schemi da documentare, separati da virgola. L'elenco di riferimento è quello di `git.env`             |
| `DB_DOCS_MODE`     | `ci` (o `minimal`, `manual`) produce le pagine ridotte della CI, vedi sotto. Vuota = generazione completa  |
| `DB_DOCS_OUT_DIR`  | una cartella `docs` alternativa in cui scrivere; vuota = `docs/` del progetto                             |

---

## Le quattro regole che lo rendono affidabile

La regola di casa dice di prendere il contratto di un oggetto da queste pagine, non dagli YAML. Per
questo il generatore si difende da quattro modi di scrivere pagine sbagliate senza accorgersene.

1. **Si lancia come proprietario del database.** `information_schema` è filtrato dai permessi: con
   un utente che vede meno, le pagine perderebbero sezioni intere (per esempio tutti i vincoli) e
   sembrerebbero quelle di oggetti che quei vincoli non li hanno. Prima di scrivere, il generatore
   confronta `information_schema` con `pg_constraint` e, se non concordano, **si ferma** senza
   scrivere niente, nominando l'utente e le tabelle che non vede.
2. **Il `search_path` lo fissa lui, a `public`.** I trigger mostrano il nome della funzione secondo
   il `search_path` di chi interroga: senza questa regola, lanciarlo con un altro utente cambierebbe
   migliaia di righe senza che nel database sia cambiato niente.
3. **Toglie le pagine degli oggetti che non esistono più.** Una pagina di un oggetto droppato
   sarebbe giusta nel contenuto e falsa nell'esistenza. La potatura non scatta se l'elenco degli
   oggetti vivi di una cartella è vuoto: una query fallita non deve cancellare uno schema intero. Non
   tocca mai `manual/`.
4. **Lavora in autocommit.** Una transazione unica terrebbe un lock su ogni tabella letta fino alla
   fine del giro, e un migrate o un pgTAP lanciati nel frattempo finirebbero in deadlock.

⚠️ Gli indici (`index.md`, `index.ci.md`) si allineano solo alla generazione successiva: se si
sposta o si cancella una pagina `manual/`, l'elenco cambia quando si rilancia lo script.

---

## In CI

`ci.yaml`, sui push a `main`, ricostruisce il database da zero e lancia lo script con
`DB_DOCS_MODE=ci`. In questa modalità le pagine generate contengono **solo** l'include della pagina
`manual/`, senza la definizione SQL, e la pagina dei job pgAgent non si scrive (in CI pgAgent non
c'è). È questa la versione che il sito pubblica.

La doc **completa**, con le definizioni, è quella committata nel repository: la si rigenera sul
database di sviluppo dopo aver applicato i changeSet, e si committa insieme a loro.

---

{% include-markdown "signature-core.md" %}
