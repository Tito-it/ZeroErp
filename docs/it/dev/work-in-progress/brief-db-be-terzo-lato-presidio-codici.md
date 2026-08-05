# Brief DB+BE — il terzo lato: i codici che il database dice e nessuno ha classificato

**Chi scrive:** DB (`dev/db-tid`), 2026-08-05.
**Origine:** rilievo del team BE, §12.5 di
[brief-db-codice-errore-strutturato](../work-done/brief-db-codice-errore-strutturato.md) (chiuso).
**Stato:** 🔴 **aperto — serve una decisione prima del codice.**
**Perimetro:** misura e cancello lato DB · assegnazione dei significati lato BE.

> **Non è una regressione.** Questo difetto c'era anche prima; la slice del codice
> errore strutturato l'ha soltanto reso **visibile**, perché ora il codice arriva
> davvero al backend invece di perdersi per strada.

---

## 1. Il problema, in parole semplici

Quando il database rifiuta un'operazione dice una **parola** — il codice errore.
Su quelle parole devono andare d'accordo **tre elenchi**:

1. il **catalogo** delle parole che il database può dire, con la frase che
   l'operatore legge (`config.messaggi_errore`);
2. le parole che usa il **codice applicativo**;
3. la tabella che dice, per ogni parola, **che tipo di risposta** dare a chi ha
   fatto la richiesta: «non esiste», «non ti è permesso», «è in conflitto con lo
   stato attuale», «hai sbagliato a compilare» (`error_policies.py`).

Oggi due accordi sono controllati automaticamente, il terzo no:

| Direzione | Presidiata da |
|---|---|
| le parole usate nel codice applicativo sono dichiarate | test lato backend ✅ |
| le parole che dice il database sono nel catalogo | guardrail DB ✅ |
| **le parole che dice il database hanno un tipo di risposta** | 🔴 **nessuno** |

**Conseguenza.** L'operatore legge comunque la frase giusta — quella viene dal
catalogo. Ma il *tipo* di risposta viene appiattito su «hai sbagliato a
compilare» anche quando la verità è «non esiste» o «non ti è permesso».

È come un commesso che, qualunque sia il problema, risponde sempre «c'è un errore
nella sua richiesta» invece di «quel prodotto non ce l'abbiamo» oppure «questo non
glielo posso vendere». Chi ascolta capisce lo stesso; chi deve **reagire** — la
pagina che decide se mostrare un avviso o riportarti indietro, un allarme, un
tentativo automatico — no.

⚠️ Ed è la stessa direzione da cui erano passati inosservati i nove codici delle
guard di cambio stato del cantiere precedente. Non è un caso: è **l'unico lato
che nessuno guarda**, quindi è lì che le cose si accumulano.

---

## 2. Quanto è grande

Misurato sul DB vivo il 2026-08-05, dopo la chiusura del cantiere precedente:

| | |
|---:|---|
| **341** | codici `E_*` **sollevati** da funzioni PL/pgSQL vive, via `script.fn_log_and_raise_error` |
| **141** | di questi, **senza una voce** in `error_policies.py` |
| **90** | dei 141, sollevati da funzioni **agganciate a un trigger**: sono sul percorso di una richiesta vera |

### ⚠️ Le misure riconciliate — e la terza era sbagliata

Tre numeri sono circolati per lo stesso fatto: **133** (BE), **141** (DB) e poi un
**137** «raffinato». Vale la pena dire com'è andata, perché è la trappola che
questo progetto continua a incontrare.

Il 137 nasceva dal restringere la misura ai soli letterali **dentro la chiamata
che solleva** — più preciso, in apparenza. In realtà **perdeva i codici del
gruppo C**: quelli che arrivano da un'espressione (`v_motivi -> 0 ->> 'codice'`),
dove il letterale vive dentro la funzione pura `fn_check_*` e non dentro la
`PERFORM`. Sono 19 codici, **4 dei quali senza policy**.

`137 + 4 = 141`. **Il numero grezzo di partenza era quello giusto**, e la
raffinazione l'aveva peggiorato dichiarando conformi quattro codici che non lo
sono. *Anche la misura di un difetto è un programma, e può avere il suo difetto.*

Da qui la scelta della vista canonica (§7): **volutamente larga**. Fra i due
errori possibili si sceglie quello che si corregge guardando i falsi positivi —
una policy di troppo costa una riga — non quello che non si vede.

L'insieme è fissato: **141 decisioni**, di cui **90 prioritarie**.

---

## 3. Perché non è ancora stato fatto

Non per dimenticanza. Il BE l'ha **trovato e segnalato** mentre chiudeva la
propria parte, e ha anche già scritto la misura. Si è fermato lì per una ragione
giusta:

> assegnare il tipo di risposta a 141 codici **non è una traduzione, è una
> decisione di dominio**, una per codice.

Centoquarantuno decisioni improvvisate in un pomeriggio sarebbero
centoquarantuno scelte da rifare. E non essendo una regressione, non c'era nessuna urgenza che giustificasse
la fretta.

---

## 4. Come lo chiuderei

La forma che ha già funzionato due volte in questo progetto — **misura, registro
del debito, cancello** — e nell'ordine che permette di accendere il cancello
**subito**, senza aspettare le 141 decisioni:

| # | Cosa | Chi |
|---|---|---|
| 1 | ~~Riconciliare le misure e fissare l'insieme~~ | ✅ **fatto** (§2) — DB |
| 2 | **Cancello** in CI: un codice `E_*` che il DB può nominare deve avere una voce in `error_policies.py` | **BE** (§5) |
| 3 | ~~**Registro del debito** con i codici già esistenti~~ | ✅ **fatto** (§7) — DB |
| 4 | Assegnare il tipo di risposta, **a lotti e per dominio** — non in ordine alfabetico: i codici di uno stesso dominio si decidono meglio insieme | BE + Tid |

Senza il punto 3 il cancello sarebbe rosso dal primo giorno e finirebbe
disattivato — che è il modo in cui i presidi muoiono.

⚠️ **Priorità dentro il punto 4:** i **90 da trigger agganciati** vengono prima.
Gli altri stanno in funzioni che potrebbero non essere sul percorso di una
richiesta, quindi il loro tipo di risposta non lo legge nessuno.

---

## 5. Una cosa da decidere prima di cominciare

Il cancello **non può leggere `error_policies.py` da SQL**: è un file Python. Due
strade, e vanno pesate insieme:

* **il controllo vive lato BE** — un test che legge le funzioni del database
  (serve una connessione) e le confronta col dizionario. È dove sta già il
  presidio gemello `test_error_codes_declared_guardrail`;
* **il controllo vive lato DB** — lo script SQL legge il *testo* di
  `error_policies.py`. È quello che fa oggi la misura scritta dal BE, funziona,
  ma lega un guardrail SQL alla forma di un sorgente Python.

Propendo per il **lato BE**: il dizionario è loro, e un test che gli sta accanto
si accorge di un rinominio molto prima di uno script che ne legge il testo.

✅ **Ed è tecnicamente possibile**, cosa che fino a ieri non era ovvia. Un test
Django che interroga `pg_proc` ha bisogno di un database **col nostro schema**, e
in CI ce l'ha: il runner non crea il database di test usa-e-getta finché nessun
test ne dichiara uno, quindi la connessione resta quella provvista da Liquibase.
È lo stesso meccanismo che fa funzionare i tre end-to-end di
`test_db_error_fields` (§14 del brief chiuso) — **con la stessa fragilità**: il
giorno in cui un test dichiarerà un database, questo controllo va adeguato
insieme a quelli. Sta scritto in `.codex/AGENTS.md` §Regole test Django.

Ma è una decisione da prendere insieme, non da imporre.

---

## 6. Riferimenti

* [brief-db-codice-errore-strutturato](../work-done/brief-db-codice-errore-strutturato.md)
  §12.5 (il rilievo originale) e §10 (la forma dei due presidi già in servizio)
* [Presidi e registri del debito](../../guide/presidi-e-registri-del-debito.md) §3.3
* `scripts/sql/guardrail_codice_errore_strutturato.sql` — i cinque controlli esistenti

---

## 7. ✅ Pronto lato DB — la misura e il registro

Preparati il 2026-08-05, **da applicare**. Il cancello (punto 2) resta al BE.

| ChangeSet | Cosa |
|---|---|
| `20260805-35` | **la misura canonica**: vista `dbops.vw_codici_errore_da_dichiarare` |
| `20260805-36` | **il registro**: `dbops.codici_errore_senza_policy` |
| `20260805-37` + CSV | le **141 voci**, mirror `DELETE` + `loadData` |

### Perché una vista e non una query per ciascuno

È il pezzo che conta più della tabella. Tre numeri diversi per lo stesso fatto
sono nati perché ognuno si è scritto la propria query: la vista toglie quel
problema alla radice, e il cancello lato BE diventa poche righe.

```sql
SELECT codice, da_trigger, n_funzioni, funzioni
  FROM dbops.vw_codici_errore_da_dichiarare
 WHERE codice NOT IN (SELECT codice FROM dbops.codici_errore_senza_policy);
```

Il confronto col dizionario Python resta al test: `error_policies.py` da SQL non
si legge, ed è la ragione del §5.

**Verificato**: la vista dà esattamente gli stessi numeri della misura scritta a
mano — 360 codici totali, i 141 del registro tutti presenti, `da_trigger`
concorde su ognuno.

### Quello che il cancello deve fare, nei due versi

1. un codice della vista **senza** policy e **non** nel registro → **rosso**
   (è il 142esimo, quello nuovo);
2. una voce del registro che **ha ottenuto** la sua policy → **rosso**, la riga
   va tolta dal CSV.

⚠️ Senza il secondo verso il registro può solo allungarsi, e torna a essere un
elenco di eccezioni. È la regola che ha fatto passare il registro gemello da 57
voci a 1 in una giornata.
