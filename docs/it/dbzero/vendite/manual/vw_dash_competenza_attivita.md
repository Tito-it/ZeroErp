## 📘 Documentazione Concettuale – Vista `vendite.vw_dash_competenza_attivita`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.commesse_attivita](/dbzero/vendite/tabelle/commesse_attivita) — la riga di commessa, una per riga della vista
> * [vendite.attivita_fatturabili](/dbzero/vendite/tabelle/attivita_fatturabili) — la sua controparte fatturabile
> * [vendite.fatture_righe](/dbzero/vendite/tabelle/fatture_righe) — la riga di fattura
>
> Approfondimento viste:
>
> * [vendite.vw_dash_competenza_mensile](/dbzero/vendite/views/vw_dash_competenza_mensile) · [vendite.vw_dash_competenza_errori](/dbzero/vendite/views/vw_dash_competenza_errori) · [vendite.vw_dash_backlog_documenti](/dbzero/vendite/views/vw_dash_backlog_documenti) — la famiglia a due lenti
> * [vendite.vw_dash_competenza_gruppi](/dbzero/vendite/views/vw_dash_competenza_gruppi) — i gruppi fatturabili, costruiti da qui
> * [vendite.vw_commesse_attivita_emittibilita](/dbzero/vendite/views/vw_commesse_attivita_emittibilita) — la sede unica del «può entrare in un giro?», da cui viene la trattenuta
> * [vendite.vw_lotti_fase](/dbzero/vendite/views/vw_lotti_fase) — dice se un lotto è in gioco
>
> Approfondimento funzioni:
>
> * [vendite.fn_emit_attivita_fatturabili_da_commessa](/dbzero/vendite/funzioni/fn_emit_attivita_fatturabili_da_commessa) — l'emissione
> * [vendite.fn_gruppo_fatturabile_key_di_attivita](/dbzero/vendite/funzioni/fn_gruppo_fatturabile_key_di_attivita) · [vendite.fn_documento_uid_di_attivita](/dbzero/vendite/funzioni/fn_documento_uid_di_attivita) — la chiave del gruppo e l'uid del documento di una riga di commessa
> * [vendite.fn_resolve_registro_documento](/dbzero/vendite/funzioni/fn_resolve_registro_documento) · [vendite.fn_calcola_data_documento](/dbzero/vendite/funzioni/fn_calcola_data_documento) — il sezionale e la data previsti
> * [script.fn_check_attivita_riportabile_da_emettere](/dbzero/script/funzioni/fn_check_attivita_riportabile_da_emettere) — l'altra metà della dimensione `motivo_non_fatturata`
> * [script.fn_get_emittenti_scope_sr_ids](/dbzero/script/funzioni/fn_get_emittenti_scope_sr_ids) — il perimetro dell'emittente
>
> Guide:
>
> * [Cruscotti di fatturazione](/guide/cruscotti-fatturazione) — le due lenti

---

### 🎯 Scopo Principale

La vista di dettaglio della Lente Competenza dei cruscotti di fatturazione: una riga per attività di
commessa computabile, con la sua posizione nel ciclo a valle (commessa, attività fatturabile, riga di
fattura, stato fiscale) e i recuperi tardivi.

L'asse è la competenza vera della riga di commessa, `commesse_attivita.competenza_mese`, obbligatoria:
nessun proxy. Il backend aggrega da `vw_dash_competenza_mensile` e usa questa vista per il drill-down,
che raggruppa per commessa.

---

### Le regole delle colonne

| Aspetto | Regola |
| --- | --- |
| `stadio` | `DA_APPROVARE` (non emessa e non approvata) · `DA_EMETTERE` (approvata, non emessa) · `EMESSA_NON_FATTURATA` (emessa, senza riga di fattura) · `FATTURATA` (agganciata a una riga di fattura, con lo stato fiscale per il dettaglio) |
| `valore` | Prezzo congelato della riga di commessa per la quantità, su tutti gli stadi: è la stessa misura del resolver commesse, e il ciclo resta omogeneo |
| `valore_fatturato` | La riconciliazione col fatturato reale: l'imponibile della riga di fattura, ripartito sulla quantità dell'attività fatturabile (zero se la riga di fattura ha quantità zero, vuoto se non c'è) |
| `data_emissione` | La nascita dell'attività fatturabile (`data_insert`): la riga nasce una volta all'emissione, e il reset di un lotto la aggiorna senza spostarne la data |
| `emessa_in_ritardo` | Il mese del giorno operativo dell'emissione è successivo alla competenza: la competenza M è stata lavorata dopo M. Vuoto per un'attività non ancora emessa |
| `lotto_id` | Il lotto della fattura, l'ultimo se la fattura ne ha più d'uno |
| `cliente_display` | L'intestatario del billing account della commessa |
| `emittente_ragione_sociale` | Il nome dell'emittente della commessa |
| `commessa_stato_descrizione` | La descrizione dello stato della commessa, o il suo codice quando a catalogo la descrizione manca |

**Perimetro computabile.** Restano fuori le commesse annullate e le attività che non arriveranno mai
in fattura: annullate, oppure rifiutate e non emesse.

**Perimetro dell'emittente.** La vista è `security_invoker` e filtra al suo interno con
`script.fn_get_emittenti_scope_sr_ids` letto dalla variabile di sessione dell'operatore: tutto, niente
o l'elenco degli emittenti visibili. ⚠️ È fail-closed: senza `app.current_user_id` la funzione dà
l'elenco vuoto e non passa nessuna riga, anche per un superuser, perché il filtro sta nella vista e
non in una regola RLS che `BYPASSRLS` scavalcherebbe. Chi interroga a mano, o scrive un test, imposta
la variabile.

---

### ⭐ `data_emissione` appartiene alla sua riga di commessa

L'emissione ritrova l'attività fatturabile per `commessa_attivita_id`, la FK obbligatoria e unica
verso la riga di commessa: un'attività non può ereditare la `data_insert` di un'altra, e il flag di
ritardo non può sotto-stimare.

---

### ⚠️ `EMESSA_NON_FATTURATA` è uno stadio residuale, non una tappa

Il prelievo delle attività e la generazione delle righe stanno nello stesso passo del lotto: il
percorso normale va da `DA_EMETTERE` a `FATTURATA`, e questo stadio si popola solo fuori da quel
percorso. Ci finiscono situazioni con rimedi opposti, e la colonna `motivo_non_fatturata` è ciò che le
distingue: chi emette in modo mirato vede passare di qui lavoro sano, accanto a lavoro rimasto orfano.

#### La dimensione: `motivo_non_fatturata`

Lo stadio guarda una cosa sola, la riga di fattura. La dimensione, vuota fuori da
`EMESSA_NON_FATTURATA`, dice il rimedio:

| `motivo_non_fatturata` | Come si riconosce | Rimedio | Il verbo «riporta da emettere» la tocca? |
| --- | --- | --- | --- |
| `GIRO_IN_CORSO` | Attività lucchettata da un giro non ancora completato; oppure libera, col marchio di un lotto in gioco (il transito fra prelievo e selezione) | Si aspetta che il lotto finisca | No (`E_ATTIVITA_IN_LAVORAZIONE`) |
| `RESIDUO` | Lucchettata da un giro completato, senza riga di fattura; oppure libera col marchio di un lotto non più in gioco, o senza marchio: una divergenza che nessun giro riprende | «Riporta da emettere» | Sì |
| `SENZA_ATTIVITA_FATTURABILE` | La riga di commessa è emessa ma non ha nessuna attività fatturabile (il modello ne ammette la cancellazione finché non è fatturata) | Nessuno: non c'è niente da riportare | No: la chiave del verbo è vuota |

«In gioco» si legge da `vendite.vw_lotti_fase`, ed è valutato solo sulle righe libere dello stadio.

⛔ **Lo stadio non si spezza in due valori.** Lo stadio dice a che punto del ciclo è il lavoro, e
queste situazioni sono allo stesso punto: cambia la loro salute, non il loro avanzamento. Spezzarlo
confonderebbe i due assi e romperebbe un vocabolario che backend, traduzioni e cataloghi di lista
consumano.

⛔ **Le due superfici non devono divergere.** `motivo_non_fatturata` e
`script.fn_check_attivita_riportabile_da_emettere` rispondono alla stessa domanda da due lati, con gli
stessi rami. Cambiarne uno senza l'altro non dà nessun errore: la lista proporrebbe il verbo su una
riga che la mutazione rifiuta, o lo nasconderebbe su una che accetta. Le lega un test con una fixture
costruita per ogni caso.

⛔ **Il confronto con `COMPLETED` tratta il vuoto come «non completato».** `stato_esecuzione` è
nullable e ammette anche `ERRORE`: un confronto per disuguaglianza semplice darebbe un risultato
indeterminato su un lucchetto senza stato, e la riga cadrebbe su `RESIDUO` dove la funzione risponde
`E_ATTIVITA_IN_LAVORAZIONE`. Un giro in errore resta così `GIRO_IN_CORSO`, col rimedio giusto:
aspettare che il lotto si chiuda.

⛔ **`fatturato` non entra nel discriminante**: è generata da `fattura_riga_id`, e dentro questo stadio
è sempre falsa.

#### La chiave del verbo: `attivita_fatturabile_id`

`vendite.fn_riporta_attivita_da_emettere` consuma l'id dell'attività fatturabile, e la vista lo espone.
Il backend potrebbe tradurlo da `commessa_attivita_id`, ma tradurre a mano un legame che il database
conosce già è una seconda implementazione. ⚠️ È un identificatore, non una colonna da mostrare.

Accanto stanno le due metà del discriminante (`lock_in_fatturazione`, `stato_esecuzione`) e il decode
dell'articolo (`articolo_codice`, `articolo_descrizione`): una lista di residui su cui si deve agire
ha bisogno del nome del lavoro.

#### ⚠️ Il lotto di provenienza non è `lotto_id`

`lotto_id` viene dalla catena della fattura: su un residuo la fattura non c'è, quindi è vuoto proprio
dove la domanda si pone. `lotto_provenienza_id` e `lotto_provenienza_codice` vengono invece dal lotto
che ha lucchettato l'attività o, se il lucchetto non c'è, da quello che l'ha marchiata: un residuo
divergente è stato marchiato da un giro e mai lucchettato. Per un'attività lucchettata i due
coincidono.

* Il collegamento è lecito perché sul lato dei lotti la chiave del giro è unica: non può moltiplicare
  le righe di una vista che ne alimenta altre.
* È esterno, non interno, perché i lotti hanno la RLS: un lotto fuori perimetro lascia le colonne
  vuote, non fa sparire il residuo.
* `lotto_provenienza_codice` viene da un codice mutabile: è display, e nessuna logica ci si appoggia.

ℹ️ I collegamenti al lotto di provenienza e all'articolo non li paga chi non ne legge le colonne: sono
esterni su chiavi uniche, e PostgreSQL li toglie dal piano quando nessuna loro colonna è selezionata.
⚠️ Regge finché regge l'unicità: togliendola, la vista comincerebbe a contare doppio in silenzio.

#### ⭐ Lo stadio si calcola una volta sola

Lo stadio è calcolato una volta, in un `LATERAL`, e serve sia la colonna `stadio` sia
`motivo_non_fatturata`: ricopiarne la condizione avrebbe messo la definizione dello stadio in due
posti della stessa vista.

---

### Il sezionale e la data che il documento porterà

`registro_id`, `registro_codice`, `politica_data_documento` e `data_documento_prevista` rispondono,
prima di fatturare, a due domande: su quale sezionale finirà il documento, e che data porterà.

* ⭐ Il sezionale si risolve con `vendite.fn_resolve_registro_documento`, la stessa funzione che usa la
  costruzione della fattura vera: la previsione è una lettura, non una seconda implementazione, e non
  può divergere dal documento.
* ⚠️ Alla funzione si passa il billing account della commessa, quello della riga: risale al padre da
  sé, e passarle quello di fatturazione darebbe una previsione plausibile e sbagliata proprio sui
  billing account con padre.
* ⛔ La previsione si fa solo dove la riga di fattura non c'è ancora: dove il documento esiste la
  colonna mentirebbe al proprio nome. Il discriminante è la riga di fattura, non lo stadio: anche
  un'attività rimasta orfana di una fattura eliminata riceve la previsione, ed è lì che serve.
* ⛔ La data si calcola solo quando il sezionale è risolto: `vendite.fn_calcola_data_documento` solleva
  su un sezionale nullo, e senza quella condizione una sola riga non risolvibile farebbe morire tutta
  la lista.
* ⚠️ `registro_codice` è un codice mutabile, solo display: chi filtra lo fa su `registro_id`.

---

### La trattenuta: `emissione_trattenuta`

`emissione_trattenuta` dice che la riga di commessa ha classe `TRATTENUTA` in
`vendite.vw_commesse_attivita_emittibilita`: il suo gruppo fatturabile è trattenuto da un lotto di
competenza uguale o successiva, e un altro giro non può prenderla. `emissione_trattenuta_da_lotti` è
l'elenco di quei lotti, ordinato, e vuoto quando la riga non è trattenuta. La vista non ricalcola il
criterio: lo legge dalla sua sede unica.

---

### Colonne di gruppo fatturabile

`sorgente_tipo_id`, `sorgente_uid`, `tipo_movimento` e `gruppo_key` collegano la riga al gruppo
fatturabile.

* `sorgente_tipo_id` è il tipo del documento da cui nasce la riga di commessa.
* ⚠️ `sorgente_uid` **non** è la colonna uuid della provenienza: è l'uid del documento in testo, per
  ogni tipo (anche per quelli a chiave `id`), letto dal `segment_key` della riga con
  `vendite.fn_documento_uid_di_attivita`. È la stessa forma che sta nella chiave di gruppo; chi deve
  arrivare al documento la passa al ponte delle chiavi in testo (`script.fn_sorgente_documento_da_chiave`).
  Vuoto su una riga senza documento.
* `gruppo_key` viene da `vendite.fn_gruppo_fatturabile_key_di_attivita`, che compone la chiave con
  `vendite.fn_build_gruppo_fatturabile_key`, la stessa dei filtri per gruppo dell'emissione: le chiavi
  mostrate sono esattamente quelle che l'emissione accetta.

Questa vista è la base di `vendite.vw_dash_competenza_gruppi`, che ne eredita il perimetro
dell'emittente e la coerenza dei conteggi con la card.

---

### ⚠️ Due vincoli su ogni modifica

1. La vista si ridefinisce aggiungendo colonne solo in fondo: quelle esistenti non si rinominano, non
   si riordinano e non si tolgono.
2. `security_invoker` va ridichiarato a ogni ridefinizione: PostgreSQL lo azzera in silenzio, e la
   vista girerebbe coi permessi del proprietario, aprendo il perimetro dell'emittente su tutte le
   dashboard di competenza.

⚠️ Raggruppando per commessa, il drill-down può mettere `emittente_ragione_sociale` nel raggruppamento
in sicurezza: l'emittente è un campo della commessa, non dell'attività. La colonna nel raggruppamento
serve comunque, perché su una colonna di vista PostgreSQL non deduce la dipendenza funzionale. E le
catene del cliente e dell'emittente passano dalle stesse tabelle anagrafiche: scambiarle non darebbe
nessun errore, solo un nome sbagliato a video.

---

### Test

* `vendite/test-vw-dash-competenza-v1` — stadi, misure, perimetro, e la sentinella sul reset di un
  lotto per `data_emissione`.
* `vendite/test-motivo-non-fatturata-v1` — la dimensione `motivo_non_fatturata` caso per caso, legata a
  `script.fn_check_attivita_riportabile_da_emettere`.
* `vendite/test-viste-dash-emittente-v1` — `emittente_ragione_sociale` e il perimetro dell'emittente.

---

### Note di migrazione

* 2026-07-06 — nasce come dettaglio della Lente Competenza (brief-db-fatturazione-due-lenti).
* 2026-07-27 — arrivano le colonne di gruppo fatturabile.
* 2026-08-15 — arriva `commessa_stato_descrizione`: il backend risolveva la descrizione con un proprio
  collegamento, che la vista faceva già (brief-db-emittibilita-visibile-e-sbloccabile).
* 2026-08-18 — arriva `emittente_ragione_sociale`; il flag multi-emittente della lista si accende a
  parte, quando la colonna è certificata su dati veri (brief perimetro-emittente).
* 2026-08-26 — arrivano il sezionale e la data previsti (brief-db-registro-e-data-prevista-in-competenza)
  e la chiave del verbo con la dimensione `motivo_non_fatturata`
  (brief-db-residui-competenza-dimensione-e-chiave). Lo stesso giorno `fatturato` diventa generata da
  `fattura_riga_id`, e il disaccordo fra le due smette di essere rappresentabile.
* 2026-09-09 — arrivano `emissione_trattenuta` ed `emissione_trattenuta_da_lotti`
  (brief-db-il-trattenuto-passa-lo-stesso).
* 2026-09-12 — ritirato il valore `IN_ATTESA_LOTTO` di `motivo_non_fatturata` («non lucchettata, il
  prossimo giro la prende da sé»): dentro questo stadio la riga è emessa, e nessun giro la riprende. Il
  lotto di provenienza si legge anche dal marchio (brief-db-rilancio-step-non-rivede-le-proprie-commesse).
* 2026-11-07 — `sorgente_uid` e `gruppo_key` si leggono dal `segment_key` della riga di commessa;
  l'emissione ritrova l'attività fatturabile per `commessa_attivita_id`
  (brief-db-sorgente-documento-e-riga).

---

{% include-markdown "signature-core.md" %}
