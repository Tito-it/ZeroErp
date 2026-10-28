# Brief DB — La scadenza dei preventivi (EMESSO → SCADUTO)

## ⏭️ Chi riparte — aggiornato al 2026-10-25

**Riparte: Tid**, con la decisione E-1 (§4): la scadenza la scrive un processo del database, oppure SCADUTO
esce dal modello del preventivo. Nessuno sviluppo prima del via.

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | ✅ team DB | Il caso, i fatti, le domande | §1-§4 | — |
| 2 | **Tid** ⏭️ | E-1 … E-3 | §4 | 1 |
| 3 | team DB | Il giro, dopo il via | §5 | 2 |
| 4 | team BE/FE | Solo se E-1 tocca l'interfaccia (lo stato in lista, un filtro) | — | 3 |

Decisioni aperte di Tid: E-1 … E-3. Lavoro da committare: questo documento.

> **Chi scrive:** team DB (`dev/db-tid`), 2026-10-25. **A chi:** Tid, poi il team DB.
> **Origine:** W-3 di [brief-modello-documento-vendita](brief-modello-documento-vendita.md) §8.12 (debito X-2,
> dichiarato nel §8.6 del giro 6). Tid, 2026-10-25: «brief separato».
> **Brief vicini verificati:** [brief-modello-documento-vendita](brief-modello-documento-vendita.md) (il
> verbo e i passaggi di processo: questo brief ne usa i pezzi comuni, non li cambia);
> [brief-design-proiezione-stato-dominio](brief-design-proiezione-stato-dominio.md) (legge SCADUTO come stato
> chiuso negativo: è un lettore, non uno scrittore). Nessun brief aperto scrive la scadenza.

## 1. Il caso

Il preventivo ha lo stato SCADUTO nel vocabolario (`config.stati_doc_preventivi`, fase CHIUSO) e il passaggio
EMESSO → SCADUTO nella matrice, segnato **di processo** (`manuale = false`): l'operatore non lo chiede, e il
verbo `vendite.fn_cambia_stato_preventivo` lo rifiuta se chiesto a mano (`E_DOC_PASSAGGIO_DI_PROCESSO`).

**Nessuno lo scrive.** La guida dei preventivi (§3.1) parlava di un «job notturno» al superamento di
`validita_al`, che non esiste né nel database né nel backend (verificato il 2026-10-25). Oggi un preventivo
emesso con la validità superata resta EMESSO, e si può ancora accettare.

## 2. Il modello

* La guida del modello (§5) dice chi scrive un passaggio di processo: **il verbo che ne è la causa**, con la
  sola seconda metà del verbo comune (`script.fn_doc_scrivi_stato`), attraverso la porta. Per la scadenza la
  causa è il **tempo**: non c'è un'operazione di un operatore da cui partire, quindi serve un processo.
* La data è sul documento: `vendite.preventivi.validita_al` (nullable: un preventivo senza scadenza non scade
  mai; il NULL è un caso del modello, non un'eccezione).
* I processi del database girano su pgAgent, col giornale dei job e il ruolo `zeroerp_job` (guida dei processi).

## 3. Da verificare prima del giro (DB)

1. Se l'accettazione di un preventivo con `validita_al` superata oggi è rifiutata da qualche guard: se no, il
   documento scaduto «per data» e quello SCADUTO «per stato» dicono due cose diverse fino al passaggio del job.
2. Chi legge SCADUTO (capability, liste, la proiezione dello stato di dominio): cosa cambia per loro quando lo
   stato comincia a esistere davvero.
3. Il fuso: la scadenza è una data, il job gira a un'ora; quale giorno è «oggi» per un'azienda.

## 4. Decisioni per Tid

* **E-1. Chi scrive la scadenza.** (a) un processo del database (job pgAgent giornaliero) che porta in SCADUTO
  i preventivi EMESSI con `validita_al` superata, con un verbo di processo; (b) SCADUTO esce dal modello: la
  scadenza resta una data, letta da chi la mostra, e l'accettazione oltre la data si rifiuta nel guard.
  **Consiglio (a)**: lo stato c'è già nel vocabolario e nella matrice, e lo leggono già capability e
  proiezione dello stato di dominio; (b) è una revoca del modello attuale del preventivo.
* **E-2. L'accettazione oltre la data.** Con (a), fra la scadenza e il passaggio del job un preventivo è
  ancora EMESSO: si rifiuta l'accettazione anche per data (nel guard di transizione), o basta il job?
  Consiglio: anche nel guard, perché la regola non dipenda dall'ora del job.
* **E-3. Riaprire uno scaduto.** Oggi SCADUTO è terminale. Una revisione del preventivo (la funzione
  esiste) è la via per riproporlo, o serve un passaggio SCADUTO → EMESSO con una nuova data?

## 5. Il giro (dopo il via)

Si scrive dopo le decisioni: verbo di processo, job e sua registrazione nel catalogo dei processi, guard
(E-2), pgTAP che costruiscono il caso (un preventivo con `validita_al` passata), guida dei preventivi §3.1.
