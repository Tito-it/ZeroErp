# Brief DB — Quattro processi che non guarda nessuno

> **Chi scrive:** backend (`dev/backend-tid`), 2026-09-11. **A chi:** team DB.
> **Origine:** una domanda di Tid a valle del cantiere dei presidi —
> *«per i lavori che girano ogni minuto ci si accorge subito che non girano;
> per gli altri cosa si può fare?»*.
>
> **In una riga:** dei sei processi che il backend dichiara di svegliare, **due**
> hanno un presidio che si accorge se smettono di girare. Gli altri **quattro**
> no, e per tre di loro il rimedio è la stessa vista che esiste già per il primo.
>
> ⛔ **Il backend non può fare niente da solo**: tutte e quattro le mosse sono
> viste e righe di catalogo, cioè database. Ciò che il backend farà appena
> arrivano è al §7.

---

## 1. Come è nato, e la domanda era giusta

Chiuso il cantiere dei presidi (`brief-db-un-destinatario-per-i-presidi.md`),
Tid ha osservato che per i **drenatori** — quelli che girano ogni minuto — un
fermo si nota subito, perché il lavoro che serve non viene fatto.

⭐ **È vero, e c'è di più: quel caso è già presidiato**, e non da una persona.
`dbops.vw_coda_lavori_da_guardare` dice testualmente *«mai preso: il worker non
sta girando»* su un `PENDING` più vecchio di un'ora — natura `ZERO`, cadenza
`GIORNALIERA`, quindi finisce nel digest.

⚠️ **Ma la frequenza non è il criterio, e la prova sta nei fatti di questo
progetto**: `send_pending_emails` gira **ogni 5 minuti** — alta frequenza — ed è
rimasto **non installato** su `backend-dev` senza che nessuno se ne accorgesse
(§11.5 del brief dei presidi). Non perché sia raro: perché **nessuno aspetta una
mail entro un tempo preciso**.

> **Il discriminante non è «ogni quanto gira»: è «qualcuno aspetta l'esito, e in
> quanto tempo se ne accorge?»**

## 2. Il quadro — misurato il 2026-09-11 su `backend-dev`

| Processo | Cadenza | Che cosa lo presidia oggi | |
| --- | --- | --- | --- |
| `draina_coda_lavori` | 1 min | `vw_coda_lavori_da_guardare` + badge liveness | ✅ |
| `draina_coda_stampa` | 2 min | **solo** il badge in topbar — la vista gemella **non esiste** | 🟠 §4 |
| `send_pending_emails` | 5 min | **niente** | ⛔ §5 |
| `digest_presidi:giornaliera` | 1/g | il battito della corsa settimanale | ✅ |
| `digest_presidi:settimanale` | 1/sett | **niente** — il battito sta dentro di lui | ⛔ §6 |
| `listen_cambio_reparto` | sempre acceso | **niente** — scrive un run solo all'avvio | ⛔ §7-bis |
| `run_fatturazione_batch` ×2 | spenti | — | n/a |

I **13 job pgAgent** sono coperti da `vw_processi_programmazione_da_guardare`,
che li vede perché vivono dentro il database. Sui `COMMAND` quella vista dichiara
`FUORI_PORTATA`, ed è corretto: **il database non può vedere systemd**.

## 3. Il criterio: si presidia l'EFFETTO, non lo schedulatore

⭐ È già così che funziona per `draina_coda_lavori`: nessuno chiede a systemd se
il timer è acceso — si guarda **la coda che si accumula**. È più robusto, perché
intercetta anche il caso in cui il processo gira ma sbaglia, e non ha bisogno di
sapere niente dell'host.

⇒ Tre dei quattro buchi si chiudono così. Il quarto (§6) no, ed è il più
interessante.

⭐ **E c'è un effetto collaterale che vale da solo: presidiare l'effetto chiude
anche il buco del §11.5** del brief dei presidi — *«fra dichiarato e installato
non guarda nessuno»*. Un timer mai installato non ha un effetto: la coda si
accumula, le email restano ferme, il digest non arriva. ⇒ Non serve **nessuna**
interfaccia verso systemd per accorgersene: basta guardare il lavoro che non
viene fatto. *La domanda «il timer è acceso?» è tecnica; la domanda «il lavoro si
sta facendo?» è quella che interessa, e ha già una risposta a database.*

---

## 4. 🔵 RICHIESTA 1 — la coda stampa: un'asimmetria che grida

`vendite.fatture_stampa_coda` è la **gemella** di `dbops.coda_lavori`: stessa
forma, stessa bandiera `archiviato`, stesso codice errore, e a database esiste
perfino un pgTAP che confronta colonne, vincoli e trigger delle due *perché la
simmetria non resti una promessa*.

⛔ **Ma il presidio ce l'ha una sola delle due.** Se il drenatore della stampa si
ferma, le fatture restano in coda e il digest non dice niente.

**Serve** `vendite.vw_coda_stampa_da_guardare` con lo stesso predicato della
gemella (`ERRORE`, `IN_CORSO` da troppo, `PENDING` da troppo, e `NOT archiviato`),
più la riga a catalogo.

⚠️ **Due differenze vere fra le due tabelle, che il predicato deve affrontare:**

| | `dbops.coda_lavori` | `vendite.fatture_stampa_coda` |
| --- | --- | --- |
| colonne di tempo | `claimed_at`, `run_after`, `started_at`, `ended_at` | **solo** `data_insert` / `data_update` |
| stati | 5 (con `ANNULLATO`) | 4 |
| **RLS** | **no** | **sì** |

⇒ **D1** e **D2** al §8. E dalla RLS discende il perimetro: **`DEFINER`**.

## 5. 🔵 RICHIESTA 2 — le email che restano in coda

Nessuna vista guarda `config.email_log`. Se `send_pending_emails` non gira, le
email si accumulano in `PENDING` **per sempre**, in silenzio.

⛔ **Non è un'ipotesi: è successo.** Quel timer non era installato, e l'unico
motivo per cui non ci sono state conseguenze è che la coda era vuota.

**Serve** una vista sulle email **vive e vecchie** — `stato IN ('PENDING','RETRY')`
oltre una soglia — natura `ZERO`, cadenza `GIORNALIERA`.

⚠️ `config.email_log` **ha la RLS**: la vista va a perimetro **`DEFINER`**, o il
conteggio risponde zero per cecità — che è esattamente il difetto già pagato
sulle `riferimenti_morti` (§9.4 del brief dei presidi). ⇒ **D3**, **D4**.

## 6. 🔵 RICHIESTA 3 — chi guarda il guardiano

Il digest segnala tutti gli altri. **Se muore lui**, l'unica cosa che lo direbbe
è il battito — che sta **dentro** il digest.

> **Un digest morto non manda il messaggio che dice che è morto**, e l'assenza di
> una mail non si nota.

⭐ **La via d'uscita non passa da systemd**: pgAgent vive **dentro il database**,
cioè in un mondo che non muore insieme al backend. Un job pgAgent che legge
`maintenance.job_run_log` e chiede *«`digest_presidi` ha girato nelle ultime N
ore?»* chiude la ricorsione — è il guardiano dall'altra parte del muro.

⛔ **L'ostacolo è dove vive la soglia.** Oggi `tolleranza_minuti` sta in
`backend/deploy/sveglie.json`, un file sul server backend che pgAgent non può
leggere. Le uscite sono due, e la seconda tocca una decisione già presa:

1. il job pgAgent si porta la soglia **scritta dentro** → è una **seconda sede**
   dello stesso fatto, cioè il difetto che il cantiere delle sveglie ha appena
   tolto (⛔ sconsigliata, e la scriviamo solo per dichiararla scartata);
2. la **tolleranza** va a catalogo, su `dbops.processi`.

⚠️ **La 2 contraddice il §9.2 del brief dei presidi**, dove sta scritto che *«come
li si sveglia è un fatto di deploy e vive dove vive il deploy»* — ed è la ragione
per cui il team DB aveva rifiutato di dichiarare su quella tabella la cadenza dei
job pgAgent.

⭐ **Ma forse la contraddizione è apparente, e la distinzione vale la discussione**:

| Fatto | Natura | Dove |
| --- | --- | --- |
| **cadenza** — *quando* si sveglia | **deploy**: dipende dall'host, dal fuso, dal carico | `sveglie.json`, come oggi |
| **tolleranza** — *entro quanto* è tollerabile che taccia | **modello**: non cambia da macchina a macchina | ⇒ candidata al catalogo |

⇒ **D5**. È la domanda che vale più di tutto questo brief.

## 7-bis. 🔵 RICHIESTA 4 — il listener, che non ha cadenza

`listen_cambio_reparto` non è un timer: è un processo **sempre acceso** in
`LISTEN/NOTIFY`. Scrive **un solo run**, quello di avvio — decisione di Tid del
2026-09-05, con la ragione scritta: *«è vivo adesso?» è una domanda diversa da
«ha girato stanotte?», e ha una sede sua*.

⛔ **Il fatto è che quella sede non è mai stata costruita.** Se il servizio muore
alle 03:00, l'ultimo run resta quello dell'avvio e nessuno se ne accorge finché
qualcuno non cambia reparto a un operatore e la cosa non succede.

Le forme possibili sono due, e **nessuna delle due è gratis**:

* un **battito**: il listener scrive un segno di vita ogni N minuti. ⚠️ Cambia la
  decisione del 2026-09-05 e mette righe periodiche su `job_run_log` — che è il
  giornale delle **corse**, non un heartbeat;
* un **timestamp che si sovrascrive**, su una riga sola (`dbops.processi` o una
  tabella di stato). Non sporca il giornale, ma è un dato nuovo.

⇒ **D6**.

---

## 7. Che cosa fa il backend appena arrivano

| # | Cosa | Dove |
| --- | --- | --- |
| 1 | niente per §4 e §5: il pannello legge le `ZERO` **dal catalogo**, quindi le due viste nuove compaiono **da sole** | `presidi_repository.stato_presidi` |
| 2 | niente per il digest: filtra per **cadenza**, non per elenco di viste | `presidi_digest` |
| 3 | se passa la **D5**: leggere `tolleranza_minuti` dal catalogo invece che da `sveglie.json`, e togliere il campo dal file (una sede sola) | `apps.core.services.sveglie` |
| 4 | se passa la **D6**: il battito del listener | `notify_listener` |

⭐ **I punti 1 e 2 sono la prova che il catalogo era la scelta giusta**: due
presidi nuovi entrano nel pannello e nel digest **senza una riga di backend**.

## 8. 🟠 Domande aperte

| # | Domanda | Perché non la decide il backend |
| --- | --- | --- |
| **D1** | Per la coda stampa, «preso e mai chiuso» su quale colonna? Non c'è `claimed_at`: resta `data_update`, che però cambia **a ogni** update | è la semantica della tabella, e la possiede chi l'ha scritta |
| **D2** | La soglia di **un'ora** della gemella vale anche per la stampa, che gira ogni 2 minuti? Un'ora è 30 giri | dipende da quanto è tollerabile una stampa in ritardo — è dominio |
| **D3** | Per le email, quale soglia? E i `RETRY`, che hanno un **backoff** legittimo, entrano nel presidio o no? | un RETRY in attesa non è un guasto: serve il criterio |
| **D4** | Confermate **`DEFINER`** su entrambe le viste nuove (RLS su `email_log` e `fatture_stampa_coda`)? ⚠️ Conseguenza: il digest mostra il **numero** e non le righe | è la stessa scelta già fatta per `riferimenti_morti` |
| **D5** | ⭐ La **tolleranza di liveness** va a catalogo su `dbops.processi`, separandola dalla cadenza che resta nel deploy? | tocca una decisione già presa in senso opposto (§9.2) |
| **D6** | Il listener deve battere? Con quale cadenza, e su quale sede — `job_run_log` o un timestamp che si sovrascrive? | è una decisione di Tid, e cambia quella del 2026-09-05 |
| **D7** | Le due viste nuove hanno una `colonna_stato`/`stato_atteso` a catalogo, o restano `NULL` come `vw_coda_lavori_da_guardare`? | dipende da come si vuole leggere il conteggio |

## 9. Che cosa NON si chiede

* **nessuna interfaccia verso systemd**: valutata e scartata — `systemctl`
  risponde solo per la macchina che serve la richiesta, quindi con più host
  mostrerebbe «un host a caso», e in un container non esiste affatto. Il
  confronto fra dichiarato e vissuto non ha nessuno dei due problemi;
* **nessuna modifica ai drenatori né alle code**: le tabelle vanno bene come
  sono, mancano solo le viste che le guardano;
* **nessun backfill**: le righe vecchie restano come sono;
* **niente per `run_fatturazione_batch`**: è spento per decisione, e un timer
  spento non ha una liveness da presidiare.

*Brief del 2026-09-11. Le misure sono letture di `backend-dev` e del dbdev di
quel giorno: valgono come controesempio, non come motivo. Il motivo sta sul
modello, ed è che un processo che non parte non lascia una riga da nessuna
parte — e una riga che manca non si vede, se non contro l'elenco di ciò che ci
si aspettava.*
