# Brief DB → BE — ritorno del lotto a DRAFT

> **Cos'è.** Il lato DB del ritorno in bozza di un lotto è **applicato e testato**
> (2026-08-03). Questo documento è ciò che serve a voi per usarlo, più **una cosa
> che senza di voi non funziona**.
>
> **Piano completo**: [piano-db-ritorno-lotto-a-draft.md](piano-db-ritorno-lotto-a-draft.md).
> **Movente**: [brief-db-termine-dal-documento-alla-commessa.md §6](brief-db-termine-dal-documento-alla-commessa.md)
> — la fattura 2263 del lotto 1200, EMESSA e non disfabile. È vostro.

---

## 1. TL;DR

| | |
|---|---|
| **Cosa c'è di nuovo** | `vendite.fn_riporta_lotto_a_draft(bigint)` + colonna `vendite.fatturazione_lotti.riaperto_il` |
| **Cosa vi chiediamo** | **due** cose (§3 e §4), entrambe in `pipeline_runner` |
| **Codici errore nuovi** | **nessuno** — usa `E_PARAMETRO_INVALIDO`, `E_VALORE_MANCANTE`, `E_CONFIG_MANCANTE`, tutti già in `error_policies.py` |
| **Va in `ALLOWED_TASK_FUNCTIONS`?** | **No** — è un'azione dell'operatore, non un task di pipeline. Endpoint, come le due funzioni di reset |
| **Rischio se non fate niente** | la funzione gira, ma il lotto riaperto **riparte dal passo sbagliato** e non rifà le righe |

---

## 2. Cosa fa la funzione

Riporta in bozza un lotto già lavorato perché si possa correggere a monte e
rifare il giro. **È un rollback, non una riapertura**: le fatture si
**cancellano** e il rilancio le rigenera.

```sql
SELECT * FROM vendite.fn_riporta_lotto_a_draft(1200);
-- updated_lotti | updated_attivita | deleted_fatture | deleted_righe | riemesse_attivita
```

Perimetro: lotti **MASSIVO o GIORNALIERO**, in **DRAFT o EMESSA**.
⚠️ **Rifiuta se una sola fattura ha già un numero** — guarda il numero, non lo
stato.

Tocca **tre** livelli: le fatture (cancellate col cleanup che già conoscete), le
`attivita_fatturabili` (sbloccate), e — il pezzo che sorprende — le
**`commesse_attivita`**, il cui `stato_emissione` torna a `NON_EMESSA`. Senza
quest'ultimo il lotto ripartirebbe **senza niente da emettere**, perché la
selezione delle attività da fatturare scarta quelle già emesse. Lo stesso campo
decide come il cruscotto competenza classifica la riga: col ripristino torna a
contare fra le **da emettere**.

**Non tocca i `task_runs`.** Li abbiamo misurati: nessuno li consulta per
decidere se rifare un passo (`resume_mode` è letto da `get_task_policy`, che non
ha chiamanti; `fn_start_lotto_task_run` calcola già `tentativo = MAX+1`). Sono un
registro storico e restano tali.

---

## 3. 🔴 La richiesta che conta — da dove riparte il rilancio

**Questo è il pezzo che senza di voi non funziona.**

Oggi [`pipeline_runner.py:144-167`](../../../backend/apps/vendite/services/pipeline_runner.py)
decide così:

```python
if is_massivo_error_rerun:      # lotto in ERRORE
    return steps[current_index:]        # rifà il passo corrente
if is_existing_lotto_request:
    return steps[current_index + 1:]    # va avanti
```

Un lotto riportato in bozza cade nel **secondo** ramo: è a DRAFT, quindi
`current_index` è DRAFT, e riparte da `current_index + 1` = **EMESSA**,
**saltando la rigenerazione delle righe**. L'operatore riporta indietro il
documento e poi non riesce a correggerlo.

Non possiamo risolverlo marcando il lotto in ERRORE: **sarebbe falso**. Il lotto
riaperto ha funzionato benissimo, è il risultato che non va bene — e la bugia si
vedrebbe subito, col lotto in rosso fra i falliti nei cruscotti.

**Il segnale è una colonna nuova:**

```sql
vendite.fatturazione_lotti.riaperto_il  timestamptz NULL   -- NULL = mai riaperto
```

È una **data** e non un booleano di proposito: si spiega da sola, si ordina, e
non chiede a nessuno di ricordarsi di spegnere un flag (stesso asse di
`obsoleto_dal` altrove nel prodotto).

**Cosa vi chiediamo, in due punti:**

1. **leggerla** come terzo motivo per rifare il passo corrente — qualcosa come
   `deve_rifare_step_corrente = is_lotto_in_errore(id) or is_lotto_riaperto(id)`.
   Non un ramo nuovo con un comportamento nuovo: lo **stesso** comportamento del
   rerun in errore, con una causa diversa;
2. ⚠️ **azzerarla** (`riaperto_il = NULL`) quando il lotto **avanza** oltre DRAFT.
   Senza, il lotto rifà lo stesso passo **per sempre**. Non l'abbiamo messo a DB
   perché è il runner a sapere quando l'avanzamento è riuscito — ma se preferite
   che lo faccia una funzione DB chiamata da voi, ditelo e la scriviamo.

⚠️ **Non allargate `stato_lotto`**: abbiamo valutato quella strada e l'abbiamo
scartata proprio guardando il vostro codice — `set_lotto_job_stato`
(`pipeline_repository.py`) ha una macchina a stati cablata a mano che accetta
esattamente `{IN_ESECUZIONE, COMPLETATO, ERRORE}` e rifiuta il resto. Un quarto
valore avrebbe scaricato su di voi una riscrittura, per giunta breaking.

ℹ️ La funzione **non tocca `stato_lotto`**, apposta: da COMPLETATO come da ERRORE
l'unica transizione ammessa dalla vostra macchina è verso IN_ESECUZIONE, che è
esattamente quello che farà il giro successivo.

---

## 4. L'innesco applicativo

Serve un modo per l'operatore di chiedere il ritorno. Suggerimento, non
prescrizione: un verbo nel **drawer del lotto**, accanto a quelli che già ci sono
per annullare.

Sul **come esporlo**: la nostra raccomandazione è un **endpoint**, non un task di
pipeline — è un'azione decisa da una persona, non un passo che il giro esegue da
sé. Quindi **non** va in `ALLOWED_TASK_FUNCTIONS`, e assomiglia molto a come già
chiamate `fn_annulla_lotto_da_draft`.

Sul **gate**: è un'operazione distruttiva (cancella documenti), quindi merita
un'azione di processo sua o quantomeno lo stesso gate dell'annullamento. Decidete
voi: dal DB non abbiamo visibilità su quale sia il codename giusto.

---

## 5. Cosa NON vi chiediamo

- **Nessun codice errore nuovo.** Verificato: i tre che la funzione solleva sono
  già registrati in `error_policies.py`.
- **Nessuna modifica al cruscotto competenza.** Abbiamo scelto di sistemare il
  **dato** invece di insegnare alla vista un'eccezione: con `stato_emissione`
  ripristinato le viste contano giusto **senza cambiare una riga**. Se avessimo
  fatto il contrario avreste avuto un cruscotto preciso sopra un lotto che non
  riparte.
- **Nessun intervento sui `task_runs`** (§2).
- **Niente sulla fase «estrazione della singola fattura»**: è una slice separata
  (6-B nel piano) e arriverà con un brief suo.

---

## 6. Una cosa che resta aperta e vi riguarda

Il punto (3) di **D-Q** — `lotto_segnalazioni_service` blocca *qualunque*
esecuzione in presenza di criticità, quindi vieta anche il rilancio dello stesso
step, che è la via d'uscita — **non è chiuso**.

Sul percorso del ritorno a DRAFT non morde, perché cancellando le fatture spariscono
anche le loro segnalazioni. Ma resta aperto per il rilancio «normale»: va distinto
**«non avanzare»** da **«non ripartire»**. Lo segnaliamo come contesto, non come
richiesta di questo brief.

---

## 7. Definizione di «fatto»

1. un lotto riportato a DRAFT, rilanciato, **riparte dallo step DRAFT** e
   rigenera le righe;
2. dopo l'avanzamento `riaperto_il` è tornata `NULL`;
3. il lotto riaperto **non compare fra i falliti** in nessun cruscotto;
4. l'operatore ha un verbo per chiedere il ritorno, gated.

Il punto **1** è quello che vale: gli altri tre sono rifinitura, quello è la
ragione per cui il cantiere esiste.
