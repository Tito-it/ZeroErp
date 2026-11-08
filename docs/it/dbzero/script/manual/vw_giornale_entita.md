## 📘 Documentazione Concettuale – Vista `script.vw_giornale_entita`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.event_log](/dbzero/vendite/tabelle/event_log) — il registro polimorfo dei momenti della pipeline, l'unico che porta il perimetro sulla riga
> * [vendite.fatturazione_lotti_log](/dbzero/vendite/tabelle/fatturazione_lotti_log) — il racconto per fase della corsa di un lotto
> * [vendite.fatturazione_lotti_task_runs](/dbzero/vendite/tabelle/fatturazione_lotti_task_runs) — ogni tentativo di ogni task, con il suo esito
> * [vendite.fatture_log](/dbzero/vendite/tabelle/fatture_log) — le segnalazioni che riguardano una fattura
> * [config.registri_giornale](/dbzero/config/tabelle/registri_giornale) — il catalogo dei registri che la vista cuce
> * [config.tipi_entita](/dbzero/config/tabelle/tipi_entita) — i valori di `entity_type`
>
> Approfondimento funzioni:
>
> * [vendite.fn_list_lotto_segnalazioni](/dbzero/vendite/funzioni/fn_list_lotto_segnalazioni) — risponde a un'altra domanda: «che cosa è ancora aperto su questo lotto»

---

### 🎯 Scopo Principale

La vista `script.vw_giornale_entita` risponde a una domanda sola: «che cosa è successo a questa
entità?», mettendo in fila cronologica, con le stesse colonne, le righe di quattro registri che ne
raccontano un pezzo ciascuno.

Non aggiunge nessun dato: rende leggibile insieme ciò che sta in quattro posti.

| Registro (`registro`) | Tabella | Entità | Che cosa racconta |
| --- | --- | --- | --- |
| `EVENT_LOG` | `vendite.event_log` | quella scritta sulla riga | i momenti della pipeline (avvio, passo, fine, errore) |
| `LOTTO_LOG` | `vendite.fatturazione_lotti_log` | `LOTTO` | il racconto per fase della corsa, il più fitto |
| `TASK_RUN` | `vendite.fatturazione_lotti_task_runs` | `LOTTO` | ogni tentativo di ogni task, con il suo esito |
| `FATTURA_LOG` | `vendite.fatture_log` | `FATTURA` | le segnalazioni su una fattura |

---

### ⭐ Vive in `script`, non in `vendite`

I registri di eventi del progetto non sono solo questi quattro: ci sono anche `pratiche.giornale`,
`documenti.documenti_generati_eventi`, `magazzino.eventi_assets`, `vendite.fatture_sdi_eventi`. La
domanda «che cosa è successo a questa pratica» è dello stesso genere, e una cucitura nata dentro un
dominio sarebbe da rifare.

Un registro nuovo entra con un ramo in più: la forma delle colonne non si rinegozia, e un registro
che non sa riempire una colonna la lascia vuota.

Ogni ramo ha la sua riga in `config.registri_giornale`, con descrizione ed etichetta a video. La vista
non legge il catalogo, il nome del registro è scritto nel ramo, ma un test pretende che i due
coincidano nei due versi: un ramo nuovo entra insieme alla sua riga di catalogo.

---

### Le colonne che non si capiscono dal nome

* `riga_key` — la chiave della riga, nella forma `REGISTRO:id`. È l'unica stabile: i quattro registri
  hanno spazi di identificativi separati e sovrapposti, e `riga_id` da solo non basta.
* `riga_id` — l'identificativo dentro il registro di origine: serve ad aprire quella riga.
* `quando` — il momento del fatto. Per un tentativo (`TASK_RUN`) è quando è nato, `started_at`: vedi
  sotto.
* `cosa` — il fatto: il codice dell'evento, il messaggio della segnalazione, oppure «task · stato ·
  codice errore» per un tentativo.
* `tx_id` — la transazione in cui la riga è stata scritta: è il ponte verso il registro tecnico degli
  errori.
* `correlation_id` — la corsa che ha prodotto la riga. Lo portano `event_log` e i tentativi; gli altri
  due registri lo lasciano vuoto.
* `auth_user_id` e `user_insert` — chi ha agito, per numero interno (regge a un cambio di nome) e per
  nome (si legge senza cercare). Il numero lo porta solo `event_log`.
* `disabilitato` — se la segnalazione è stata ritirata. È vuoto dove il concetto non si applica
  (`event_log`, append-only) o dove il ritiro passa da un altro asse (i tentativi, dove `attivo` spegne
  il record, non il segnale).

Il tipo di entità dei tre registri del lotto e della fattura è scritto nel ramo come valore fisso:
chiedendo un `LOTTO`, il planner scarta in partenza il ramo delle fatture.

---

### Chi vede che cosa

La vista è `security_invoker`: gira con i permessi di chi la legge, non del proprietario. È la
precondizione di tutto, e il test la verifica per prima.

Ogni ramo si protegge con la regola di visibilità della propria tabella, per perimetro dell'emittente:
`event_log` sulla colonna di perimetro che porta sulla riga (è un registro polimorfo, senza un
documento padre a cui appoggiarsi), gli altri tre attraverso il lotto o la fattura a cui appartengono.
In più i rami del lotto e della fattura si agganciano al documento che li possiede: l'aggancio fa da
ancora all'entità e da seconda difesa.

---

### ⛔ La vista non nasconde le segnalazioni ritirate: le mostra

Un diario racconta che cosa è successo, non che cosa è ancora aperto: le segnalazioni ritirate
restano. Ma restare non basta: senza `disabilitato` chi legge non distingue una segnalazione viva da
una ritirata, e due righe con la stessa frase, la prima ritirata quando il lotto è stato rifatto,
sembrerebbero lo stesso errore successo due volte.

A filtrare è il consumatore, che dirà anche quante righe ha nascosto: la vista non ha un filtro su
questo campo. Per «che cosa è ancora aperto» c'è `vendite.fn_list_lotto_segnalazioni`, che il filtro
ce l'ha e chiama il campo con lo stesso nome.

---

### ⚠️ La gravità è dove i vocabolari si incontrano

I registri dicono la stessa cosa con parole diverse: `I`/`W`/`C` nel diario del lotto e in quello
della fattura, `COMPLETATO`/`IN_ESECUZIONE`/`ANNULLATO`/`ERRORE` nei tentativi. Qui diventano
`INFO`/`WARN`/`ERROR` (un tentativo annullato è `WARN`, uno in esecuzione `INFO`).

La traduzione non ha un ramo «tutto il resto»: un valore che nessuno ha previsto esce vuoto, e il test
lo segnala. È voluto: un valore nuovo sepolto fra quelli innocui è un difetto che nessuno scopre.

---

### ⭐ La riga di un tentativo è datata alla nascita

Nel ramo `TASK_RUN`, `quando` è `started_at`. L'orario di una riga di diario non si muove dopo che è
stata scritta: `ended_at` invece lo può scrivere anche la corsa successiva, quando
`fn_start_lotto_task_run` chiude come `ANNULLATO` il tentativo rimasto aperto, e una riga datata così
cambierebbe posto nella linea del tempo dopo essere nata.

Lo stato mostrato è quello corrente: «il tentativo nato alle 10:00 è finito annullato» non è una
contraddizione. Se un giorno servirà al lettore, l'orario di fine sarà una colonna in più, non
l'orario della riga.

---

### Test

* `script/test-vw-giornale-entita` — la vista è `security_invoker`; ogni registro del catalogo arriva
  nella vista e nessun registro ne sta fuori; `riga_key` è unica; la mappa della gravità e nessuna
  riga con la gravità vuota; ogni `entity_type` esiste in `config.tipi_entita`; il `quando` di un
  tentativo chiuso è lo `started_at`; una segnalazione ritirata resta e porta il flag.
* `script/test-giornale-registri-catalogo-v1` — vista e catalogo `config.registri_giornale`
  coincidono.

---

### Note di migrazione

* 2026-08-22 — nasce la vista, con i quattro registri di oggi (brief-db-event-log-scope-e-riga-parlante).
* 2026-08-24 — la vista espone `disabilitato`: prima mostrava le segnalazioni ritirate senza dirlo.
* 2026-09-10 — i tre registri del lotto e della fattura hanno ricevuto la propria regola di
  visibilità; prima la vista si appoggiava solo all'aggancio al documento.
* 2026-09-11 — ritirata `vendite.attivita_fatturabili_log`, che la vista non aveva mai cucito perché
  non aveva un filtro di perimetro: era un residuo senza scrittori né lettori.
* 2026-09-19 — nasce il catalogo `config.registri_giornale`; nel ramo `TASK_RUN` `quando` passa da
  «fine, se c'è, altrimenti inizio» a `started_at` (brief-db-osservabilita-lotto-fermo-r6-indici).

---

{% include-markdown "signature-core.md" %}
