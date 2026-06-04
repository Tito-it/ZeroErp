# Brief DB — Estensione coordinata di tutte le 5 `fn_list_<sorgente>_da_pushare` per push singolo

> **Tipo**: estensione DB function esistente (signature change additive, no breaking).
> **Branch**: `dev/db-tid`.
> **Autore brief**: backend agent (Tid, sessione 2026-05-10, **rev 2026-05-10 17:30** dopo code review critico).
> **Trigger**: completamento del pulsante "Push commessa" del drawer preventivo
> ([PreventiviIntegrazione.vue](../../../../frontend/src/vendite/preventivi/components/PreventiviIntegrazione.vue))
> oggi BE-stub (TODO esplicito in
> [preventivi_service.push_a_commessa](../../../../backend/apps/vendite/services/preventivi_service.py)).
>
> **⚠ Rev 2 — 2026-05-10 17:30**: la prima stesura chiedeva l'estensione solo
> a `fn_list_preventivi_da_pushare`. Il code review critico ha rilevato che il
> wrapper Python `CommesseRepository.fetch_pushable_rows` chiama tutte le fn
> con la **stessa signature** (`(date, int, int, ?int)`): se estendiamo solo
> preventivi e atterriamo il BE, il **batch globale** `pr_run_commesse_push`
> rompe sulle altre 4 sorgenti con `"function fn_list_<x>_da_pushare(date,
> integer, integer, integer) does not exist"`. La coordinazione e' obbligatoria.

## Contesto

Il modello "push commesse" esiste end-to-end per il **batch globale**:
`pr_run_commesse_push()` invoca `CommessaPushOrchestrator.run()` che esegue
in sequenza tutti gli handler registrati in `config.sorgenti`. Ogni handler
chiama `vendite.fn_list_<sorgente>_da_pushare(competenza_mese,
billing_account_id, limit)` per ottenere la lista delle righe da
sincronizzare verso `commesse_attivita`.

Per il caso d'uso "push **un solo** preventivo dal pulsante UI" la
signature attuale non basta: anche restringendo il dataset col filtro
`billing_account_id`, processiamo tutti i preventivi pushable di quel
cliente, non solo quello selezionato.

L'alternativa "filtro Python sul risultato" e' tecnicamente possibile ma
introduce un round-trip DB inutile (la query DB ritorna piu' righe di
quelle che servono) e duplica una semantica di filtro che dovrebbe stare
dove sta il dato.

## Azione richiesta al team DB (su `dev/db-tid`)

Estendere la signature di **tutte e 5** le funzioni
`vendite.fn_list_<sorgente>_da_pushare` con un parametro **opzionale**
`p_sorgente_id` (alias coerente: `p_preventivo_id` su preventivi,
`p_ordine_id` su ordini, ecc. — il nome semantico e' al team DB) di tipo
identificativo della riga sorgente, default `NULL`.

Le 5 fn target:

* `vendite.fn_list_preventivi_da_pushare` → param `p_preventivo_id`
* `vendite.fn_list_ordini_da_pushare` → param `p_ordine_id`
* `vendite.fn_list_contratti_da_pushare` → param `p_contratto_id`
* `vendite.fn_list_ddt_da_pushare` → param `p_ddt_id`
* `vendite.fn_list_consumi_da_pushare` → param `p_consumo_id`

Comportamento (uguale per tutte):

* `p_<sorgente>_id IS NULL` → comportamento attuale invariato (lista
  globale filtrata da `competenza_mese`/`billing_account_id`/`limit`).
* `p_<sorgente>_id IS NOT NULL` → la query restringe il `WHERE` alla
  riga sorgente del documento specifico, ignorando gli altri filtri
  competenza/BA che restano comunque applicabili in AND per coerenza
  semantica (utile se in futuro si vuole "push solo se il documento
  rientra anche in quei filtri"). Validazione: se l'id non corrisponde
  a un documento "pushable" la fn ritorna 0 righe (no errore — coerente
  con l'attuale comportamento "no rows" come default benigno).

> **Perche' tutte e 5 e non solo preventivi?** Il client Python
> `CommesseRepository.fetch_pushable_rows` chiama tutte le fn con la
> **stessa signature posizionale** `(competenza_mese, billing_account_id,
> limit, sorgente_uid)`. Se atterra solo preventivi, il batch
> `pr_run_commesse_push` (orchestrator + tutti gli handler attivi) rompe
> sulle altre 4 con "function does not exist". L'estensione coordinata
> e' obbligatoria. PR1 BE+FE oggi tocca solo il dominio preventivi
> dell'UI, ma il batch deve restare funzionante.

### Ordine dei parametri (uniforme)

```text
fn_list_<sorgente>_da_pushare(
  p_competenza_mese    date    DEFAULT NULL,
  p_billing_account_id int     DEFAULT NULL,
  p_limit              int     DEFAULT NULL,
  p_<sorgente>_id      int     DEFAULT NULL    -- NUOVO
)
```

Aggiungere in coda con `DEFAULT NULL` mantiene compatibilita' con eventuali
caller esterni (la chiamata Python diventa 4 args posizionali con `None`
come 4°, ma Postgres riconosce comunque la signature giusta).

### Nota tecnica — tipo del parametro

Verificare il tipo della colonna PK di `vendite.preventivi` /
`vendite.ordini` / ... (presumibilmente `int` / `bigint` / `uuid`). Il
parametro `p_<sorgente>_id` di ogni fn deve essere allineato al suo PK.
La cardinalita' `int` / `bigint` e' la piu' probabile guardando i pattern
attuali del dominio vendite (es. preventivo_id usato come int negli
endpoint REST), ma e' al team DB la decisione finale.

Se nei domini coinvolti i PK sono di tipi diversi (es. ordini int,
contratti int, ma consumi uuid), il client Python lo gestisce gia'
trasparentemente perche' `psycopg` adatta il bind. L'unica differenza
visibile sara' il `pg_typeof` che il team DB registrera' nel test pgTAP.

### Commenti SQL richiesti

Inserire commento sintetico nella fn per documentare il nuovo parametro:

* sopra la signature: "Estensione 2026-05: parametro `p_preventivo_id`
  per push commessa di un singolo preventivo (UI driven). NULL preserva
  il comportamento di lista globale del batch orchestrator."
* sopra la `WHERE` clause: nota dell'AND col filter `(p_preventivo_id IS
  NULL OR preventivo_id = p_preventivo_id)`.

### Test pgTAP — casi da coprire (per ognuna delle 5 fn)

Per ognuna delle 5 fn (preventivi, ordini, contratti, ddt, consumi),
casi minimali analoghi:

* `p_<sorgente>_id NULL` (regressione): la fn ritorna lo stesso conteggio
  attuale per dataset esistente (smoke).
* `p_<sorgente>_id` valido di un documento pushable: ritorna esattamente
  le N righe di quel documento (e nessuna di altri).
* `p_<sorgente>_id` valido di un documento NON in stato pushable
  (es. DRAFT o gia' pushato): ritorna 0 righe (no errore).
* `p_<sorgente>_id` invalido (id che non esiste): ritorna 0 righe
  (no errore — coerente con il filtro che e' WHERE).
* `p_<sorgente>_id` valido + `p_billing_account_id` di un BA diverso:
  ritorna 0 righe (i filtri sono in AND).

Almeno il primo caso (regressione `NULL`) e' bloccante: se rompe il batch
non puo' atterrare. Gli altri 4 casi possono essere coperti in modo
prioritario su preventivi e in modo minimale sulle altre 4 (le altre
sorgenti non hanno UI di push singolo in PR1 — le coperture complete
arrivano col rispettivo pulsante).

## BE Python (non azione team DB)

Sul branch `dev/backend-tid` aggiornero' il client Python (
[CommesseRepository.fetch_pushable_rows](../../../../backend/apps/vendite/db/commesse_repository.py))
per propagare il nuovo parametro come `sorgente_uid: int | None = None`,
unico punto di accesso. Vedi WIP gemello
[sviluppo-push-singolo-preventivo.md](sviluppo-push-singolo-preventivo.md).

## Riferimenti

* Memoria progetto: `feedback_db_actions_passaggio_team` (BE agent non
  esegue DDL, sempre brief al team DB).
* Memoria progetto: `feedback_concentrico_no_yagni` (estensione minima
  ma progettata per generalizzazione futura ad altre sorgenti).
* Guida: [docs/it/guide/fatturazione.md](../../guide/fatturazione.md)
  §"Fase 1 - Push sorgenti su commesse" e
  [docs/it/guide/gestione-commesse.md](../../guide/gestione-commesse.md)
  §"Flusso tipo - Push sorgente -> commessa".
* WIP architetturale:
  [gestione-commesse-v2.md](gestione-commesse-v2.md) §6.3 "Come una
  sorgente arriva sulla commessa - processore batch".

## Note di rollback

L'estensione e' additive (`DEFAULT NULL`): se servisse rollback, basta
ripristinare la signature precedente con una nuova migration successiva
e i test pgTAP del singolo preventivo cesseranno di matchare ma il
comportamento batch resta invariato.
