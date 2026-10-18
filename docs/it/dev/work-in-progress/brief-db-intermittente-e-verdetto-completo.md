# Brief DB — Il verde che non spegne la spia: «intermittente» e le corse che sono un verdetto completo

## ⏭️ Chi riparte — aggiornato al 2026-10-18

**Riparte: il team DB**, con la proposta del §4 e il censimento del §4.3.

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | Tid | ✅ direzione decisa (2026-10-18): proprietà del processo a catalogo; né finestra accorciata, né eccezione per nome | §4 | — |
| 2 | team DB | censimento: quali processi hanno corse che sono un verdetto completo | §4.3 | 1 |
| 3 | team DB | colonna a catalogo, vista, pgTAP, manual | §4.1, §4.2, §6 | 2 |
| 4 | Tid | decisioni D1–D3, se il team DB non le scioglie scrivendo | §5 | 2 |
| 5 | Tid | apply su dbdev, pgTAP, collaudo | §6 | 3 |
| 6 | chi chiude | archiviazione, riga di PROJECT_CONTEXT | — | 5 |

Decisioni aperte di Tid: D1–D3 al §5 (forma, non direzione). Ricaduta BE/FE: nessuna attesa (§7).

---

> **Chi scrive:** sessione BE (`dev/backend-tid`), 2026-10-18, su segnalazione di Tid. **A chi:** il
> team DB.
> **Origine:** il 2026-10-18 la spia del digest è accesa sullo smoke notturno, dopo tre giri verdi.
> **Filone:** `maintenance.vw_job_run_da_guardare`, vedi anche
> `brief-db-presidio-job-run-a-chi-tocca` (la causa delle righe) e `brief-db-corsa-saltata-non-e-una-corsa`.
> **Stato:** 📝 proposta, codice non iniziato.

## 1. Il caso

La vista accende una riga per tre motivi: l'ultima corsa è **fallita**, è **presa e mai chiusa**
(aperta da oltre un'ora), oppure è **intermittente** (l'ultima è verde o in corso, ma c'è almeno un
rosso negli ultimi sette giorni).

Il terzo motivo esiste per un guasto preciso: un lavoro che fallisce e passa, fallisce e passa, ha
sempre l'ultima corsa verde, e guardando solo quella nessuno lo direbbe malato
(`sync_auth_user_active`, 29 fallimenti in un giorno, il 2026-09-05). Per quel lavoro i sette giorni
sono giusti.

Lo smoke notturno è un'altra cosa. Ogni corsa **rifà da capo tutti gli smoke** e li confronta con la
baseline: un verde non dice «questa volta è andata bene», dice «oggi non ci sono regressioni». Il
verde di oggi **sostituisce** il rosso di ieri, non lo affianca. Eppure la vista lo tiene acceso per
sette giorni come un lavoro che va e viene.

## 2. Perché è un difetto del modello

Il motivo «intermittente» presuppone che ogni corsa veda **una parte** del lavoro (gli elementi di
quel giro, la coda di quel momento), così che un verde non cancelli quello che un rosso aveva lasciato
indietro. Per questi lavori è vero, e il rosso recente va tenuto in vista.

Per un lavoro la cui corsa è un **verdetto completo** sullo stato (ricontrolla tutto il suo perimetro,
ogni volta), il presupposto è falso: dopo un verde non resta niente di non verificato. Il rosso
precedente è storia, non un guasto aperto.

La vista oggi non può distinguere i due casi, perché il catalogo dei processi non lo dice. È la
stessa forma di `causa_fallimento` e di `tolleranza_minuti`: una proprietà della **natura del
processo** che la vista deve leggere e non indovinare.

Un rosso che non si nasconde, del resto, non ha bisogno della finestra: un verdetto completo che gira
una volta al giorno lascia il rosso come ultima corsa per un giorno intero, e il digest delle 7 lo
mostra. Uno smoke instabile si vede lo stesso: la spia si riaccende ogni mattina in cui torna rosso.

### Le due strade scartate

* **Accorciare i sette giorni.** È la finestra di tutti i lavori, e per quelli che falliscono e
  passano è quella giusta. Tagliarla perché oggi dà fastidio su un processo sarebbe la misura che
  disegna il progetto, e il difetto resterebbe: con tre giorni, la spia resterebbe accesa tre giorni
  dopo il verde.
* **Escludere lo smoke per nome nella vista.** Un'eccezione cablata, che il prossimo processo con la
  stessa natura dovrebbe ricopiare.

## 3. I fatti (2026-10-18, letti dal giornale; fatti datati, non motivo)

| Corsa (`job_run_log.id`) | Inizio (UTC) | Esito |
| --- | --- | --- |
| 198028, 198134, 198273 | 2026-10-13 14:00 / 15:00 / 16:00 | 🔴 `SMOKE_REGRESSIONI` (1 regressione) |
| 199365 | 2026-10-14 01:00 | 🔴 `SMOKE_REGRESSIONI` (1) |
| 202152 | 2026-10-15 01:00 | 🔴 `SMOKE_REGRESSIONI` (2) |
| 205055, 207887, 210468 | 2026-10-16 / 17 / 18 01:00 | 🟢 regressioni 0 |

La vista, il 2026-10-18 alle 08:07: `motivo` = «ultima corsa OK, ma ha fallito di recente:
intermittente», `falliti_ultimi_7_giorni` = 9, `ultimo_rosso_job_run_id` = 202152, `causa` =
`PROGRAMMA`. Con la regola di oggi esce dalla vista il 2026-10-22, dopo sette verdi di fila.

Nella definizione della vista la finestra compare due volte: nel filtro d'ingresso
(`p.started_at >= now() - '7 days'`) e nel conteggio `falliti_ultimi_7_giorni`
(`p.started_at >= g.started_at - '7 days'`).

## 4. La proposta

### 4.1 Catalogo

In `dbops.processi` una colonna booleana, `NOT NULL DEFAULT false`, che dichiara: **«ogni corsa di
questo processo è un verdetto completo: un verde chiude i rossi precedenti»**. Nome a scelta del team
DB (D1); per fissare le idee, `corsa_verdetto_completo`. Nel CSV `processi.csv`, `smoke_notturno` a
`true`, tutti gli altri a `false` salvo il censimento del §4.3.

### 4.2 Vista

Per un lavoro il cui processo ha la colonna a `true`:

* il motivo **intermittente** non scatta: la vista guarda solo l'ultima corsa;
* **fallita** e **presa e mai chiusa** restano come oggi;
* **la corsa in corso non è un verdetto** (D2): finché non chiude, conta l'ultima corsa **chiusa**.
  Se l'ultima chiusa è rossa, la riga resta «fallita» anche mentre il giro nuovo gira; se è verde,
  la vista resta vuota. Oggi un rosso seguito da una corsa in corso diventa «in corso adesso, ma ha
  fallito di recente: intermittente», che per un verdetto completo non è vero (il giro nuovo non ha
  ancora detto niente).

Per i lavori senza processo a catalogo, o con la colonna a `false`: niente cambia.

`falliti_ultimi_7_giorni` resta per tutti: è un dato utile anche su un verdetto completo (quanti
giorni rossi nell'ultima settimana), solo non accende più la riga.

### 4.3 Censimento

Il team DB passa i processi a catalogo e dice, per ciascuno, se la corsa ricontrolla tutto il suo
perimetro o ne lavora una parte. Ipotesi da verificare sul codice, non da prendere per buone:

| Processo | Ipotesi | Perché |
| --- | --- | --- |
| `smoke_notturno` | ✅ verdetto completo | rifà tutti gli smoke contro la baseline |
| digest dei presidi | da verificare | ogni corsa rilegge tutte le viste di presidio; ma un digest non inviato ieri non lo reinvia oggi |
| coda lavori, coda stampa | ❌ | un lavoro fallito resta fallito, la corsa dopo lavora altri lavori |
| fatturazione batch, invio mail | ❌ | gli elementi falliti di una corsa (D9) non sono ripresi dalla successiva |
| job pgAgent di manutenzione | da verificare uno per uno | |

Il criterio, da scrivere nel manuale della colonna: **dopo un verde, resta qualcosa che il rosso
aveva lasciato e il verde non ha ricontrollato?** Se sì, `false`.

## 5. Decisioni per Tid (se il team DB non le scioglie scrivendo)

* **D1 — nome e posto della colonna.** Proposta: `dbops.processi.corsa_verdetto_completo`, accanto a
  `tolleranza_minuti` e `causa_fallimento`.
* **D2 — la corsa in corso su un verdetto completo** (§4.2, terzo punto). Proposta: non conta finché
  non chiude.
* **D3 — il digest dei presidi**, se il censimento lo dà ambiguo (inviato o no è una parte, rilettura
  completa è un verdetto).

## 6. Collaudo

pgTAP nuovi in `test-vw-job-run-da-guardare` (o file gemello `-verdetto-completo-v1`), su un processo
di prova con la colonna a `true` e uno a `false`, stessa storia di corse:

1. rosso → verde: verdetto completo **fuori** dalla vista; l'altro **dentro**, intermittente;
2. rosso → in corso (meno di un'ora): verdetto completo **dentro**, motivo «fallita», sull'ultima
   chiusa (D2); l'altro come oggi;
3. verde → in corso: tutti e due fuori;
4. rosso → in corso da più di un'ora: tutti e due «presa e mai chiusa»;
5. verde → rosso: tutti e due «fallita»;
6. lavoro senza processo a catalogo: comportamento di oggi;
7. `falliti_ultimi_7_giorni` invariato su tutti i casi.

Poi i pgTAP della causa (`test-vw-job-run-da-guardare-causa-v1`) e di `processi` senza regressioni.

Sul DB vero, dopo l'apply: lo smoke esce dalla vista se l'ultima corsa è verde.

## 7. Ricadute BE/FE

Nessuna attesa. Il backend non legge il testo del motivo né `falliti_ultimi_7_giorni` (verificato il
2026-10-18 nel codice di `backend/` e `frontend/src`); il digest legge le righe della vista. Se la
colonna entra nel drawer dei processi come dato informativo, è una richiesta a parte. Se il team DB
ne vede un'altra scrivendo, la scrive qui.
