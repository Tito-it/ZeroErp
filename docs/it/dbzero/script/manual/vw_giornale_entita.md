# vw_giornale_entita

### Scopo

Risponde a **una domanda sola**: *«che cosa è successo a questa entità?»*.

Oggi quella risposta è sparsa in quattro registri, e ognuno ne racconta un
pezzo. Chi indaga su un lotto deve sapere che esistono tutti e quattro, e
guardarli uno per uno:

| Registro | Cosa ci trova |
|---|---|
| `vendite.event_log` | i quattro momenti della pipeline (avvio, passo, fine, errore) |
| `vendite.fatturazione_lotti_log` | il racconto per fase della corsa — è il più fitto |
| `vendite.fatturazione_lotti_task_runs` | ogni singolo tentativo di ogni task, con il suo esito |
| `vendite.fatture_log` | le segnalazioni che riguardano una fattura |

La vista **non aggiunge nessun dato**: mette in fila cronologica ciò che già
esiste, con le stesse parole per tutti.

⭐ Dal 19-09-2026 i quattro registri hanno un **catalogo**,
[`config.registri_giornale`](/dbzero/config/manual/registri_giornale): una riga
per ramo, con descrizione ed etichetta. La vista non lo interroga — il nome del
registro resta scritto nel ramo — ma il test
`test-giornale-registri-catalogo-v1.sql` pretende che i due coincidano: un ramo
nuovo entra **insieme** alla sua riga, o il test è rosso.

> **Vedi anche**
>
> - [event_log](/dbzero/vendite/tabelle/event_log) — il registro polimorfo, l'unico che porta il perimetro sulla riga
> - [fn_list_lotto_segnalazioni](/dbzero/vendite/funzioni/fn_list_lotto_segnalazioni) — risponde a un'**altra** domanda: «cosa è ancora aperto su questo lotto»
> - Brief del cantiere: [brief-db-event-log-scope-e-riga-parlante](/dev/work-done/brief-db-event-log-scope-e-riga-parlante) §3.6

---

## Schema

`script` — e non `vendite`, di proposito.

I registri di eventi del progetto sono **sei**, non uno: oltre ai quattro qui
sopra ci sono `pratiche.giornale`, `documenti.documenti_generati_eventi`,
`magazzino.eventi_assets`, `vendite.fatture_sdi_eventi`. La domanda «cosa è
successo a *questa pratica*» arriverà, e una cucitura nata dentro un dominio
sarebbe da rifare — cioè da rifare proprio la cosa che tutti avrebbero già in
mano. Un ramo nuovo entra con un `UNION ALL`; la forma delle colonne non si
rinegozia, e un registro che non sa riempirne una lascia vuoto.

---

## Output

| Colonna | Tipo | Significato |
|---|---|---|
| `riga_key` | `text` | La chiave della riga, nella forma `REGISTRO:id`. È l'unica stabile: i quattro registri hanno spazi di identificativi separati e sovrapposti. |
| `registro` | `text` | Da dove viene la riga. I valori sono quelli di [`config.registri_giornale`](/dbzero/config/tabelle/registri_giornale) (`codice_interno`): dal 19-09-2026 è il catalogo a dare il nome, la descrizione e l'etichetta a video di ogni registro, e un test tiene vista e catalogo allineati nei due versi. |
| `riga_id` | `bigint` | L'identificativo **dentro** quel registro — serve ad aprire la riga di origine. |
| `quando` | `timestamptz` | Il momento in cui è successo. ⭐ Per un tentativo (`TASK_RUN`) è **quando è nato** (`started_at`), dal 19-09-2026 — vedi la quarta scelta qui sotto. |
| `entity_type` | `text` | Di che cosa si sta raccontando la storia: `LOTTO`, `FATTURA`… I valori sono quelli di [`config.tipi_entita`](/dbzero/config/tabelle/tipi_entita). |
| `entity_id` | `bigint` | Quale lotto, quale fattura. |
| `gravita` | `text` | `INFO \| WARN \| ERROR`. |
| `cosa` | `text` | Il fatto: il codice dell'evento, il messaggio della segnalazione, oppure «task · stato · codice errore». |
| `tx_id` | `uuid` | La transazione in cui la riga è stata scritta — è il ponte verso il registro tecnico degli errori. |
| `correlation_id` | `uuid` | La **corsa** che ha prodotto la riga. Oggi lo portano solo il diario e i tentativi. |
| `auth_user_id` | `bigint` | Chi ha agito, per numero interno: regge a un cambio di nome utente. |
| `user_insert` | `text` | Chi ha agito, per nome: si legge senza cercare. |
| `disabilitato` | `boolean` | Se quella segnalazione è stata **ritirata**. ⚠️ Vuoto dove il concetto non si applica (il diario append-only) o dove il ritiro passa da un altro asse (i tentativi). |

---

## Come si legge

```sql
-- La linea del tempo di un lotto, dalla più recente
SELECT quando, registro, gravita, cosa
  FROM script.vw_giornale_entita
 WHERE entity_type = 'LOTTO'
   AND entity_id   = 6260
 ORDER BY quando DESC, riga_key DESC;
```

⭐ Chiedendo un `LOTTO`, il ramo delle fatture **non viene nemmeno aperto**: il
tipo di entità è scritto nella vista come valore fisso, e il motore di ricerca
del database scarta in partenza i registri che non c'entrano.

---

## Chi vede che cosa

Ogni persona vede **solo il perimetro del proprio emittente**, e il meccanismo
è diverso a seconda del registro:

* `event_log` **si protegge da sé**: porta l'emittente sulla riga e ha la sua
  regola di visibilità. È il registro *polimorfo* — non ha un documento padre a
  cui appoggiarsi — ed è esattamente la ragione per cui quella colonna esiste;
* gli altri tre **dal 10-09-2026 hanno la propria regola** (via lotto, via
  fattura — il cantiere che ha portato il perimetro fino ai satelliti), e in più
  si agganciano al documento che li possiede: le due tabelle del lotto al lotto,
  il registro delle fatture alla fattura. L'aggancio resta come ancora
  all'entità e seconda difesa. ⚠️ Fino al 19-09 questa riga diceva che «una
  regola propria non ce l'hanno»: era vero al 24-08, stantio dal 10-09.

> ⚠️ Perché funzioni, la vista deve girare **con i permessi di chi la legge** e
> non con quelli del proprietario. È una proprietà tecnica (`security_invoker`)
> ed è la precondizione di tutto: senza, ognuno vedrebbe i documenti degli
> altri. Il test `db/pgtap/script/test-vw-giornale-entita.sql` la verifica per
> prima.

---

## Quattro scelte da conoscere prima di modificarla

**1. `vendite.attivita_fatturabili_log` resta fuori — non è una dimenticanza.**
Né lui né la tabella che lo possiede hanno un filtro di perimetro: quel ramo
mostrerebbe righe di altri emittenti. Entra quando il padre avrà la sua regola
di visibilità — non prima, e non «per simmetria».

**2. La vista non nasconde niente — e dal 2026-08-24 lo dice.** Le segnalazioni
ritirate restano: un diario racconta cosa è **successo**, non cosa è ancora
aperto. Ma restare non basta: senza il flag `disabilitato`, chi legge non può
distinguere una segnalazione viva da una che è stata ritirata, e **non si filtra
ciò che non si vede**.

> ⭐ Il caso che l'ha deciso, in tre righe (fattura 19563): due segnalazioni
> consecutive con la **stessa identica frase**, la prima ritirata quando il lotto
> è stato rifatto pochi minuti dopo. Senza il flag, a video sono due errori — e
> chi legge conclude che sia successo due volte, mentre è successo una volta.

⛔ **A filtrare è il consumatore**, che dirà anche quante righe ha nascosto. La
vista non ha e non avrà un `WHERE` su questo campo. E per «cosa è ancora aperto»
esiste già [`fn_list_lotto_segnalazioni`](/dbzero/vendite/funzioni/fn_list_lotto_segnalazioni),
che quel filtro ce l'ha — e che chiama il campo con lo **stesso nome**: lo stesso
fatto non deve avere due nomi.

**3. La `gravita` è l'unico punto in cui i vocabolari si incontrano.** I quattro
registri usano parole diverse per dire la stessa cosa — `I/W/C` da una parte,
`COMPLETATO/ERRORE/ANNULLATO` dall'altra — e qui diventano `INFO/WARN/ERROR`.
⚠️ La traduzione **non ha un ramo «tutto il resto»**: un valore che nessuno ha
previsto esce **vuoto**, e il test lo segnala. È voluto — un valore nuovo
sepolto fra quelli innocui è un difetto che nessuno scopre.

**4. La riga di un tentativo è datata alla nascita (R-6, 19-09-2026).** Nel
ramo `TASK_RUN` `quando` è `started_at`. Fino a quel giorno era
`COALESCE(ended_at, started_at)`, e il test lo pinnava come «scelta di disegno»
— *il momento in cui ha preso lo stato che mostra*. Ma `ended_at` lo scrive
anche la corsa **successiva**: `fn_start_lotto_task_run` chiude come
`ANNULLATO` il tentativo rimasto aperto, e un task partito il 21 compariva col
22, in mezzo alle righe del 22 — la Storia del lotto raccontava un ordine che
non era successo (misurato il 19-09 su dbdev: sui 352 `ANNULLATO` la distanza
fra i due orari ha mediana un quarto d'ora e massimo quasi due giorni).

⭐ L'argomento che decide: **l'orario di una riga di diario non si muove dopo
che è stata scritta.** `started_at` si scrive una volta; lo stato mostrato è
quello corrente, e «il tentativo nato alle 10:00 è finito `ANNULLATO`» non è
una contraddizione. `ended_at` resta nella tabella: se un giorno servirà al
lettore, sarà una colonna in più (`fino_a`), non l'orario della riga.

---

{% include-markdown "signature-core.md" %}
