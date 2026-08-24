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

> **Vedi anche**
>
> - [event_log](/dbzero/vendite/tabelle/event_log) — il registro polimorfo, l'unico che porta il perimetro sulla riga
> - [fn_list_lotto_segnalazioni](/dbzero/vendite/funzioni/fn_list_lotto_segnalazioni) — risponde a un'**altra** domanda: «cosa è ancora aperto su questo lotto»
> - Brief del cantiere: [brief-db-event-log-scope-e-riga-parlante](/dev/work-in-progress/brief-db-event-log-scope-e-riga-parlante) §3.6

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
| `registro` | `text` | Da dove viene la riga: `EVENT_LOG \| LOTTO_LOG \| TASK_RUN \| FATTURA_LOG`. |
| `riga_id` | `bigint` | L'identificativo **dentro** quel registro — serve ad aprire la riga di origine. |
| `quando` | `timestamptz` | Il momento in cui è successo. |
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
* gli altri tre una regola propria non ce l'hanno, e si agganciano al documento
  che li possiede: le due tabelle del lotto al lotto, il registro delle fatture
  alla fattura. ⛔ L'aggancio **è** il perimetro: se il documento non è tuo, la
  riga non compare.

> ⚠️ Perché funzioni, la vista deve girare **con i permessi di chi la legge** e
> non con quelli del proprietario. È una proprietà tecnica (`security_invoker`)
> ed è la precondizione di tutto: senza, ognuno vedrebbe i documenti degli
> altri. Il test `db/pgtap/script/test-vw-giornale-entita.sql` la verifica per
> prima.

---

## Tre scelte da conoscere prima di modificarla

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

---

{% include-markdown "signature-core.md" %}
