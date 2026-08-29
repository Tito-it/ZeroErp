# API «Riporta da emettere» — il verbo di recupero delle attività residue (Django)

## Scopo

Rimette in coda di fatturazione un elenco di `vendite.attivita_fatturabili`
**residue** — rimaste senza fattura dopo che il documento che le conteneva è
stato eliminato — e riporta a `NON_EMESSA` le righe di commessa passate a
`EMESSA` per causa loro. Il lavoro ricompare in «Da emettere» e segue il giro
normale: **nessun lotto viene rigenerato, nessuna fattura viene ricreata**.

## Contesto

Consegna **BE-3** di
[brief-be-fe-lavoro-che-non-torna-indietro.md](../../../dev/work-done/brief-be-fe-lavoro-che-non-torna-indietro.md),
metà applicativa del cantiere DB
[brief-db-lavoro-che-non-torna-indietro.md](../../../dev/work-done/brief-db-lavoro-che-non-torna-indietro.md).

⭐ **Perché esiste.** Fino al 2026-08-26 «Elimina dal lotto» non liberava niente:
la pulizia cancellava le righe di fattura **prima** di riallineare le attività, e
una FK `ON DELETE SET NULL` azzerava il puntatore nel frattempo. Le attività
restavano timbrate e lucchettate, le loro righe di commessa ferme su `EMESSA`:
**due porte chiuse invece di una**, in silenzio. Il DB ha corretto l'ordine e
messo il muro; questo verbo è la via d'uscita per ciò che era già rimasto
indietro — e per qualunque altra causa futura che scolleghi un'attività dalla sua
riga.

⛔ **Non è un verbo di annullamento.** Non distrugge niente: se il riporto era
sbagliato si rifattura e si è al punto di prima. È la ragione per cui **non
chiede un motivo** (a differenza di `fn_annulla_commessa_attivita`), ma scrive
**sempre** una riga di registro.

## Input

### `POST /api/v1/vendite/attivita-fatturabili/riporta-da-emettere/`

```json
{ "attivita_fatturabili_ids": [1123, 1130, 1131] }
```

- Header `Idempotency-Key` **obbligatorio** (endpoint di scrittura).
- Permesso di processo `riporta_da_emettere` (`config.azioni_processo` id 33).

### `POST /api/v1/vendite/attivita-fatturabili/riportabili/`

Stesso body. Restituisce i **motivi ostativi** senza tentare nulla.

⚠️ **È un POST pur essendo una lettura**, e la ragione è l'elenco di id: una
selezione di 200 righe non sta in una query string. Nessun side-effect, nessuna
`Idempotency-Key`.

⛔ **Porta lo stesso permesso del verbo** — `riporta_da_emettere` — e va
dichiarato a mano: senza `post_permission`, `ZeroERPPermission` cade sul mestiere
del metodo HTTP e un POST finisce a chiedere `add` sull'area. Sarebbe il gate
sbagliato nei **due versi**: chi può riportare ma non creare si vedrebbe negare
la spiegazione di un verbo che gli è concesso, e chi può creare senza poter
riportare potrebbe interrogare un verbo che non gli spetta. Chi può agire può
chiedere: è la stessa porta, guardata prima di aprirla.

⭐ **Chi lo chiama.** Il frontend, **prima** di ogni riporto: si conferma il
gesto, e sull'accettazione la prima chiamata è questa. Se torna un motivo, il
verbo non parte — si avvisa, si azzera la selezione e si rilegge l'elenco. Non è
una cortesia: la mutazione è **atomica**, quindi senza questo passo il rifiuto
arriverebbe come *un* errore per l'intero elenco e chi guarda non saprebbe quale
riga lo ha fermato né perché.

## Output

```json
{ "data": { "riportate": 5, "riemesse_attivita": 5 } }
```

- `riportate` — attività liberate (lucchetto, legame con la riga di fattura,
  stato di esecuzione).
- `riemesse_attivita` — righe di `commesse_attivita` tornate a `NON_EMESSA`.

⚠️ **I due numeri possono differire, e non è un difetto**: la seconda scrittura
tocca solo le righe che erano davvero su `EMESSA`.

⛔ **`riportate = 0` non è un successo**: significa che l'elenco su cui si è
agito era invecchiato. Il frontend lo rende come **avviso**, non come conferma
verde.

Per `riportabili/`:

```json
{ "data": { "motivi": [
  { "codice": "E_ATTIVITA_ANCORA_IN_FATTURA",
    "reason": "ATTIVITA_IN_FATTURA",
    "reason_key": "vendite.attivita.azione_reason.ancora_in_fattura",
    "dettaglio": "commessa CMM-…, competenza 07/2026",
    "attivita_fatturabile_id": 11, "commessa_id": 22, "fattura_id": 33 }
] } }
```

Array vuoto = il verbo è ammesso su tutte.

## Regole

### Il perimetro lo decide il database, non questo endpoint

Le tre condizioni sono `fattura_riga_id IS NULL` **e** `lock_in_fatturazione`
**e** `stato_esecuzione = 'COMPLETED'`.

⛔ **Il perimetro NON usa `fatturato`**, e non è un dettaglio: dal `20260826-33`
quella colonna è **generata** da `fattura_riga_id`, quindi il predicato
`fatturato IS TRUE AND fattura_riga_id IS NULL` è **sempre falso**. Un verbo
fondato lì smetterebbe di funzionare **in silenzio**.

⭐ La terza condizione è ciò che separa l'orfana dal **giro vivo**:
`PENDING`/`RUNNING` vuol dire lotto in corso, e quello non si tocca.

### I cinque rifiuti, e perché sono cinque codici e non uno

| Codice | Quando | Classe |
| --- | --- | --- |
| `E_ATTIVITA_RIPORTO_SELEZIONE_VUOTA` | elenco assente o vuoto | `TECNICO` (500) |
| `E_ATTIVITA_FATTURABILE_NON_TROVATA` | non esiste **oppure** è fuori dal perimetro emittente | `NON_TROVATO` (404) |
| `E_ATTIVITA_ANCORA_IN_FATTURA` | è agganciata a una riga di fattura viva | `CONFLITTO_STATO` (409) |
| `E_ATTIVITA_GIA_DA_EMETTERE` | non è lucchettata: è già disponibile | `CONFLITTO_STATO` (409) |
| `E_ATTIVITA_IN_LAVORAZIONE` | è dentro un giro non ancora concluso | `CONFLITTO_STATO` (409) |

⭐ **«È già a posto» e «è dentro un documento» sono situazioni opposte**, e il
rimedio della prima è **non fare niente**: dire la seconda quando vale la prima
manderebbe a cercare una fattura che non c'è.

⚠️ `E_ATTIVITA_FATTURABILE_NON_TROVATA` **copre due casi di proposito**: dal
punto di vista di chi chiede sono la stessa cosa, e dire «non hai il permesso»
rivelerebbe l'esistenza di un documento altrui. Il suo `dettaglio` è il
**conteggio**, non gli id: di una riga che non si vede non si può nominare niente
che l'operatore riconosca.

### Il bersaglio dell'errore

Su `E_ATTIVITA_ANCORA_IN_FATTURA` la madre DB compone un `bersaglio` che arriva
fino all'envelope come `error.targets`:

```
targets = [ {type: "COMMESSA", id: "322"}, {type: "FATTURA", id: "20024"} ]
```

Prima la cosa **su cui** l'errore è successo (la commessa, unico posto dove
quella riga si vede), poi quella **da sistemare** (la fattura che la tiene). A
video diventa «Apri Fattura 20024» senza che nessun componente scriva una riga.

### La traduzione degli errori usa `translate_db_errors`

⛔ **E non `raise_from_database_error`**, che accetta il codice del database solo
se il chiamante lo ha **dichiarato** in un elenco locale — cioè una seconda copia
del catalogo. Il vocabolario di questo dominio è già cresciuto da tre a quattro
valori senza che il backend lo sapesse: una copia si sarebbe disallineata in
silenzio, e un codice nuovo sarebbe arrivato all'operatore come generico.

### Guard sull'elenco, nel service

Elenco vuoto o assente, id non interi o non positivi, oltre **200** elementi →
`E_VENDITE_VALIDATION` (400). I duplicati si rimuovono preservando l'ordine.

⭐ **Il tetto di 200 è la CONVENZIONE DI CASA dei verbi di massa**, non un numero
scelto qui: `MAX_ACCREDITI_MASSIVI` (accredita resi) e
`MAX_GRUPPI_EMISSIONE_MIRATA` (emissione mirata) valgono lo stesso, e **nessuno
dei tre è rispecchiato nel frontend** — tutti e tre lasciano rifiutare il
backend. Oltre un certo punto «riporta indietro N righe» smette di essere un
gesto che una persona ha guardato.

ℹ️ La selezione a video si compone fra le pagine e il frontend ne offre fino a
100 per pagina, quindi tre pagine piene fanno 300 e il rifiuto arriva **dopo** la
conferma. Il messaggio è comprensibile («Troppe attività selezionate (massimo
200)») e non si perde nulla. ⛔ **Deciso di lasciarlo così** (Tid, 2026-08-27):
un avviso lato client sarebbe **una** decisione per la famiglia di tre e
vorrebbe dire ricopiare il 200 in tre punti del frontend, a meno di esporlo dal
backend — che oggi nessuno dei tre fa.

⚠️ **L'elenco vuoto si ferma qui e non nella madre**: passandolo, il database
solleverebbe comunque, ma con un `TECNICO` (500) per un errore di chiamante. E
un elenco vuoto che passasse darebbe «zero attività riportate», cioè un
messaggio identico a quello di un'operazione riuscita che non aveva niente da
fare.

⚠️ **Il dedup non è cosmetico**: due volte lo stesso id è la stessa riga e la
madre la tratterebbe una volta sola — senza dedup il conteggio a video direbbe un
numero diverso da quello che si è spuntato.

### Atomicità e sincronia

Una sola `SELECT` sulla funzione madre, che fa le due scritture e l'evento di
registro nella stessa transazione.

⛔ **Niente `transaction.atomic()` con due chiamate**: sarebbe una seconda
implementazione di un'atomicità che il database già garantisce.

⛔ **Niente coda.** Il verbo è **sincrono**: due scritture, nessun job.
Accodarlo per simmetria con «Rendi definitive» importerebbe il problema della
dedup (`gruppi_digest`), che qui non esiste.

## Dipendenze DB

| Oggetto | Ruolo |
| --- | --- |
| `vendite.fn_riporta_attivita_da_emettere(bigint[])` | la madre: due scritture + evento di registro |
| `script.fn_check_attivita_riportabile_da_emettere(bigint[])` | i motivi, funzione **pura** |
| `vendite.fn_libera_attivita_fatturabili(bigint[])` | la primitiva condivisa con `fn_cleanup_fatture_by_ids` |
| `vendite.commesse_attivita_log` | evento `RIGA_RIPORTATA_DA_EMETTERE`, con lotto e stato precedenti |
| `config.azioni_processo` id 33 | permesso `riporta_da_emettere` |

⛔ **Lo scope sta sulla COMMESSA, non sull'attività.**
`vendite.attivita_fatturabili` **non ha row level security**;
`vendite.commesse_attivita` sì. La `fn_check_*` risolve l'attività passando per
quel `JOIN`, che **è** il cancello: leggere la sola `attivita_fatturabili`
sarebbe fail-open — e il danno non sarebbe un permesso concesso a vuoto, sarebbe
che la mutazione libererebbe l'attività e **non** riporterebbe la riga di
commessa, cioè lo stato spezzato che la primitiva condivisa esiste per impedire.

⚠️ **La madre NON imposta la GUC** `zeroerp.maintenance_reset_lotto_draft`: su
un'attività orfana `fattura_riga_id` è già `NULL`, quindi
`trgfn_attivita_fatturabili_guard_fatturato` lascia passare da sé. Impostarla
sarebbe l'unico modo di trasformare questo verbo in un modo per **scollegare una
fattura viva**.

## Note di migrazione

- Il verbo vale **anche sulle attività di `RETTIFICA`** e non c'è whitelist su
  `tipo_movimento` (Q-8). ⚠️ La risposta è **opposta** a quella di
  `fn_annulla_commessa_attivita`, che una whitelist ce l'ha — perché lì il verbo
  **distrugge**. Qui no: rimettere in coda una rettifica orfana rigenera la nota
  di credito al giro successivo.
- Il verbo vive su `attivita-fatturabili/` e **non** sotto
  `dashboard-competenza/`: il cruscotto è dove oggi si preme il pulsante, ma
  l'oggetto è l'attività fatturabile — domani lo stesso gesto può partire da
  un'altra schermata.
- ⚠️ La lettura del `jsonb` dei motivi passa da un ramo difensivo
  (`isinstance(payload, str)`): su questa connessione psycopg lo consegna come
  **stringa**, e `list()` su una stringa ne itera i **caratteri** — `"[]"`
  diventerebbe due motivi dove non ce n'è nessuno, e il verbo risulterebbe
  bloccato su righe perfettamente riportabili. Stesso ramo di
  `apps.core.db._helpers.call_jsonb_fn`, che qui non si può riusare perché è
  annotato `-> dict` e questa funzione ritorna un **array**.
