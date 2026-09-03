# Brief DB — le modifiche certe: le date di consegna, il modo di approvvigionamento, la commessa leggibile

> **Destinatario:** team DB (`dev/db-tid`) per l'esecuzione, **e team BE/FE come
> lettori** — ⭐ **questo documento è l'unica comunicazione che BE e FE
> riceveranno su questo lavoro.** Decisione di Tid, 2026-09-01: *«non faremo
> documentazione BE/FE, manderemo solo questo nuovo brief con tutta l'attività
> fatta»*. Quindi la §5 non è un'appendice: è la parte che va letta dall'altro
> lato, e deve bastare da sola.
>
> **Origine.** Le due analisi del 2026-09-01 su commessa e magazzino. Tid:
> *«da questi dobbiamo estrarre quali potrebbero essere le modifiche necessarie,
> quelle che sicuramente servono, tenendo fuori quelle collegate a decisioni da
> prendere»*.
>
> ⭐ **Terza origine, aggiunta il 2026-09-01 a sera**:
> [analisi-simmetria-ordini-acquisto.md](analisi-simmetria-ordini-acquisto.md),
> scritta lo stesso giorno. Ha prodotto **tre** voci che passano lo stesso filtro
> (§3-bis, §7, §8) e ha allargato la motivazione del Blocco B — vedi §1.
>
> **Stato:** 🔵 **APERTO — piano scritto, nulla applicato.** Nessun changeSet
> ancora creato. ⛔ Niente si applica senza autorizzazione esplicita di Tid.
>
> ⚠️ **Perimetro:** solo ciò che **nessuna decisione aperta può cambiare**. Il
> criterio è dichiarato in §1 ed è l'unica ragione per cui una voce sta qui.

---

## 1. Il filtro, ed è tutto il valore di questo documento

Le due analisi contengono molto più di quanto sta qui. La domanda che ha separato
le voci è **una sola**:

> **Se le decisioni aperte venissero prese in un modo o nell'altro, questa voce
> cambierebbe?** Se sì, non è in questo brief.

Le decisioni aperte sono le **D-1 → D-8** dell'[analisi
magazzino](analisi-db-magazzino-aggancio-documento-e-produzione.md) §8 e la **§7**
dell'[analisi commessa](analisi-db-commessa-e-produzione-predisposizione.md) —
cioè: se l'ODL è una sorgente o un anello proprio, se il ledger di magazzino usa
il catalogo delle sorgenti o il riferimento testuale, e se la commessa di
produzione è `vendite.commesse` o un'entità sua.

⚠️ **Il filtro NON è «serve anche se la produzione non si farà mai».** La
produzione non è una delle decisioni aperte: Tid l'ha data per assunta — *«siamo
vicini a iniziare lo sviluppo, e anche se ora non c'è dobbiamo prevederlo»*. È
aperta la sua **forma**, non la sua esistenza.

### ⭐ Il risultato del filtro, ed è la cosa più utile che è emersa

**Tutte le voci certe stanno su `vendite` e `catalogo`. Tutte le decisioni aperte
stanno su `magazzino` e sulla forma dell'ODL.**

Le due analisi sembravano contigue e in realtà **non si bloccano a vicenda**: il
lavoro di questo brief si può fare adesso, sulle tabelle in esercizio, mentre
`magazzino` aspetta le sue decisioni. Non c'è un ordine da rispettare fra i due.

### ⭐ E il Blocco B serve a due cantieri, non a uno (2026-09-01)

Il Blocco B è motivato qui dalla **produzione** — «questa riga richiede
produzione?». L'analisi acquisto mostra che risponde anche a una seconda domanda,
che nessuna decisione aperta tocca: **«questo articolo si compra?»**. Il valore
`ACQUISTO` è il default del vocabolario, ed è il perno da cui parte qualunque
proposta d'acquisto.

⇒ Non cambia una riga del blocco: ne **rinforza la certezza**. Un blocco che
serve a due cantieri indipendenti non dipende dalla forma di nessuno dei due.

---

## 2. Blocco A — Le date di consegna

### 2.1 Che cosa manca, e perché è la prima

⛔ **Non esiste alcuna data di consegna in tutto il database.** Cercata su
`vendite`, `acquisti` e `magazzino` il 2026-09-01: l'unica data di previsione
dell'intero modello è `magazzino.reservations.data_prevista` (dal 2026-09-02 decisa come `magazzino.movimenti_attesi`), in uno schema che
non è in esercizio.

⚠️ **Nessuna delle date esistenti serve, e vanno nominate per non farsele
proporre di nuovo:**

| Colonna | Perché non è quella |
| --- | --- |
| `vendite.ordini.data` | è la **data documento**, e governa numerazione, anno e pavimenti |
| `commesse.competenza_dal/al` | è **competenza fiscale**: riusarla farebbe dissentire due domande sulla stessa colonna |
| `data_insert` | è quando la riga è stata scritta, non quando la merce è attesa |

⭐ **E serve anche senza produzione**: senza una data di consegna non esiste la
nozione di **ritardo**. `vw_situazione_merce_ordine` sa dire *quanto* resta da
spedire e non saprà mai dire *se è tardi*. Nessun sollecito, nessuna priorità di
evasione, nessun indicatore di puntualità.

### 2.2 Le colonne

| Tabella | Colonna | Tipo | Null |
| --- | --- | --- | --- |
| `vendite.ordini_righe` | `data_consegna_richiesta` | `date` | sì |
| `vendite.ordini_righe` | `data_consegna_confermata` | `date` | sì |
| `vendite.preventivi_righe` | `data_consegna_richiesta` | `date` | sì |
| `acquisti.ordini_righe` | `data_consegna_richiesta` | `date` | sì |
| `acquisti.ordini_righe` | `data_consegna_confermata` | `date` | sì |

**Le due date sono due cose diverse** e la differenza fra loro *è* la promessa:
la prima è quando il cliente la vuole, la seconda quando ci si impegna a darla.
Sull'ordine d'acquisto lo stesso, ribaltato: quando la si chiede al fornitore e
quando lui conferma — ed è l'informazione che oggi manca per sapere se la merce
arriverà in tempo per una consegna già promessa.

⛔ **Sulla RIGA, non sulla testata**, e non è un dettaglio: una riga può essere
pronta e un'altra no. È esattamente il caso «questa riga richiede produzione», ed
è anche il caso banale «il pezzo grosso arriva a marzo, il resto subito».

⛔ **Niente colonna di testata.** La data della testata è
`min(data_consegna_richiesta)` sulle righe attive: una colonna sarebbe una
**seconda sorgente di verità** che va fuori sincrono al primo cambio di riga.
Dove serve come dato — la lista ordini — si espone dalla vista (§5.2), non dalla
tabella.

⚠️ **`vendite.preventivi_righe` ha solo la richiesta**, non la confermata: su un
preventivo non c'è ancora niente da confermare.

⛔ **`vendite.offerte_commerciali` NON entra**: non ha righe articolo (ha
utilities ed eccezioni), quindi non c'è la riga a cui la data apparterrebbe.

> 🔴 **I NOMI di queste quattro colonne sono in discussione — D-16, 2026-09-02.**
> `data_consegna_confermata` compare **su due tabelle con l'attore invertito**: su
> vendite la promessa è **nostra**, su acquisti è del **fornitore**. E la proprietà è
> pure **incrociata**, perché `data_consegna_richiesta` su vendite la esprime il
> *cliente* mentre su acquisti la esprimiamo *noi*.
>
> ⛔ È il caso che la convenzione **D-12** dell'[analisi
> acquisti](analisi-simmetria-ordini-acquisto.md) è nata per prevenire — e il posto
> dove morde è la vista di [carico e scarico
> §7-bis](analisi-db-magazzino-carico-e-scarico.md), che legge **entrambe** per
> comporre impegnato e in-arrivo: lì il nome della tabella sparisce e restano due
> omonime che promettono cose di soggetti diversi.
>
> **Proposta** (*non marcato = nostro, marcato = della controparte*):
>
> | Tabella | Nostra | Della controparte |
> | --- | --- | --- |
> | `vendite.ordini_righe` | `data_consegna_confermata` | `data_consegna_richiesta_cliente` |
> | `acquisti.ordini_righe` | `data_consegna_richiesta` | `data_consegna_confermata_fornitore` |
>
> ⚠️ **Da confermare prima di P-3**, ed è il momento più economico: nessuna delle
> quattro colonne esiste. ⭐ Dopo sarebbero quattro colonne in esercizio più due viste
> — e questo brief è la comunicazione unica verso BE/FE, quindi il nome che esce di
> qui è quello su cui l'altro lato scriverà.

⭐ **E sull'ordine d'acquisto la data non è «utile»: è necessaria** *(2026-09-02)*.
La richiesta di mostrare la **merce in arrivo** sulla giacenza — [analisi carico e
scarico §7-bis](analisi-db-magazzino-carico-e-scarico.md) — si realizza solo a metà
senza `acquisti.ordini_righe.data_consegna_confermata`: *«ne arrivano 40»* non
risponde a *«faccio in tempo a promettere la consegna di giovedì?»*. È il **secondo
cantiere indipendente** che chiede la stessa colonna, e vale l'argomento della §1:
una voce che serve a due cantieri che non si parlano non dipende dalla forma di
nessuno dei due.

### 2.3 ⛔ Nessun CHECK fra le due date, ed è una scelta

La tentazione è `data_consegna_confermata >= data_consegna_richiesta`. **È
falsa**: si può confermare *prima* di quanto chiesto, ed è una buona notizia, non
un errore.

E nemmeno un CHECK contro `ordini.data`: la **retrodatazione è un caso d'uso
vivo** in questo progetto — è la lezione già pagata dal cantiere numerazione, dove
un cancello sulla data era stato motivato con «la sceglie una persona» mentre è
proprio per questo che va lasciata scegliere.

⭐ La regola applicata: *un vincolo si mette dove il modello lo richiede, non
dove sembra ordinato.*

### 2.4 Il passaggio preventivo → ordine

`vendite.fn_push_preventivo_a_ordine` deve **portare avanti** la data richiesta,
altrimenti si perde nel punto in cui il documento cambia natura, ed è il punto in
cui gli utenti smetteranno di fidarsene.

⚠️ Toccando quella funzione si incontra un residuo già noto: nel corpo cita in un
commento `trgfn_ordini_gen_codice`, funzione che non esiste più. ⭐ È dichiarato
nel brief archiviato del prefisso sul registro (§6.3) come *«si fa alla prossima
occasione in cui la si tocca»*: **questa è quell'occasione**, e costa una riga.

---

## 3. Blocco B — Da dove arriva un articolo

### 3.1 Il buco, e le tre risposte sbagliate

⛔ **Oggi niente, in nessuna tabella, sa rispondere a «questa riga richiede
produzione?»** — e neppure a «questo articolo movimenta giacenza?», che serve a
`magazzino` a prescindere dall'ODL.

⚠️ **Le tre colonne che sembrano rispondere già, e non rispondono** — vanno
nominate perché sono la scorciatoia che qualcuno proporrà:

| Colonna | A che domanda risponde davvero |
| --- | --- |
| `articoli.is_composito` | *l'articolo ha componenti da esporre in fattura* (pricing v5, `esposto_in_fattura`). Un assemblato può essere comprato finito |
| `articoli.natura_vendita_id` | *dove va la riga venduta* (`destinazione_tipo`: ORDINE / COMMESSA / CONTRATTO). Dice la destinazione, non la provenienza |
| `nature_vendita.e_cessione_beni` | è **fiscale**: lo consuma `fn_resolve_iva_riga_guscio`. Riusarlo farebbe rispondere a un dato due domande in AND |

### 3.2 Il vocabolario `config.modi_approvvigionamento` (tabella nuova)

Colonne, sulla forma già usata da `config.nature_vendita`:

| Colonna | Note |
| --- | --- |
| `id` | identity |
| `codice_interno` | UNIQUE, **immutabile** (lock column) — è ciò su cui il codice confronta |
| `codice`, `descrizione` | mutabili, per l'operatore |
| `attivo`, `ordine`, `meta` | come tutti i vocabolari |

Seed: `ACQUISTO`, `PRODUZIONE`, `STOCK`, `NON_APPLICABILE`.

⭐ **Perché una tabella e non un CHECK su varchar**, ed è una scelta fatta qui
(revocabile, ma motivata): il modo di approvvigionamento è una **dimensione
dell'articolo** come la natura di vendita, e la natura di vendita è una tabella.
Il FE ha bisogno di una **select con etichetta** e la lista di un valore
**decodificabile**; un CHECK non dà né l'una né l'altro, e ogni consumatore
finirebbe per riscriversi le quattro stringhe a mano. ⚠️ E il giorno in cui la
produzione esiste, quel vocabolario avrà **attributi** (per esempio «richiede
ODL»): un CHECK non li può portare.

⚠️ **Tabella nuova = ciclo delle automazioni.** Audit, `tx_id` e storico non
esistono finché non gira `ci_apply`; il lock su `codice_interno` va seminato in
`dbops.automation_lock_columns`, che è **create-if-not-exists** — se la riga
esiste già va **DROP + rigenera**, non un UPDATE. E serve la riga in
`dbops.fk_index_policy` per la FK che nasce (⚠️ `dll_command` **sempre
valorizzato**, anche a `consentito = false`).

### 3.3 Le colonne su `catalogo.articoli`

| Colonna | Tipo | Null | Default |
| --- | --- | --- | --- |
| `modo_approvvigionamento_id` | `bigint` FK → `config.modi_approvvigionamento` | **no** | `ACQUISTO` |
| `gestito_a_magazzino` | `boolean` | **no** | `false` |
| `lead_time_giorni` | `integer` (CHECK `>= 0`) | **sì** | — |

⭐ **Perché queste nullabilità e non altre**, applicando la regola del progetto
(*un `NOT NULL` va dove il dato si può fornire*):

* **`modo_approvvigionamento_id` NOT NULL**: il valore si può sempre dare, e un
  NULL significherebbe «non lo so» — cioè esattamente lo stato che questa colonna
  esiste per abolire. Il default `ACQUISTO` è il caso comune e non inventa niente.
* **`gestito_a_magazzino` NOT NULL DEFAULT `false`**: il default è **fail-safe** —
  nessun articolo comincia a movimentare giacenza per distrazione. ⚠️ Ne discende
  che al rilascio *tutti* sono `false` e la merce va marcata: è un lavoro di dato,
  ed è il momento giusto per farlo, perché `magazzino` non è in esercizio.
* **`lead_time_giorni` NULLABLE**: per una prestazione non significa niente, e
  `0` non è «non si applica». Qui il NULL è un'informazione.

⚠️ **`gestito_a_magazzino` non si deriva da `natura_vendita = MERCE`**: una merce
può essere venduta senza passare da giacenza (consegna diretta dal fornitore).
Sono due domande, e vanno tenute separate anche quando oggi le risposte
coincidono.

---

## 3-bis. Blocco B-bis — `famiglie_documento`: la colonna del billing account

> ⚠️ **Voce da confermare, ed è l'unica di questo brief che non si autogiustifica.**
> Passa il filtro della §1 — nessuna decisione aperta la cambia — ma **non è
> richiesta da nulla che stia qui dentro**: la chiede il cantiere acquisto. Sta in
> questo brief per una ragione sola, di costo, ed è Tid a decidere se accettarla.

`vendite.famiglie_documento` è l'elenco dei tipi di documento che prendono il
numero da un registro. Dichiara, per ognuno, **dove vive**: schema, tabella, e il
nome di tre colonne — `colonna_numero`, `colonna_serie`, `colonna_billing_account`.

⛔ **`colonna_billing_account` è `NOT NULL`**, e il guard
`trgfn_famiglie_documento_guard_riferimenti` verifica su `pg_attribute` che la
colonna nominata **esista davvero** sulla tabella. È corretto oggi: tutte e cinque
le famiglie in servizio un billing account ce l'hanno.

Diventa sbagliato al **primo documento che non ce l'ha** — e il primo è l'ordine
di acquisto, la cui controparte è un `soggetto_ruolo`, non un BA. Registrare
quella famiglia, oggi, fallisce con
`E_FAMIGLIA_DOCUMENTO_RIFERIMENTO_INESISTENTE`.

⭐ **La correzione non è da inventare: sta già nella stessa tabella.**
`colonna_serie` è **nullable**, e il vuoto non è un dato mancante — è la
dichiarazione che *quella famiglia una serie non ce l'ha* (reso e commessa). Stessa
forma per il billing account:

| Oggetto | Cosa |
| --- | --- |
| `famiglie_documento.colonna_billing_account` | da `NOT NULL` a **nullable**: `NULL` = «questa famiglia non ha un billing account» |
| `trgfn_famiglie_documento_guard_riferimenti` | salta il controllo `pg_attribute` quando è `NULL` |
| `anagrafiche.fn_ba_ha_storia_emittente` · `fn_get_storia_emittente_ba` | **saltano** le famiglie con colonna `NULL` — corretto per costruzione: un documento senza BA non può contribuire alla storia di nessun BA |

⚠️ **Il dettaglio che decide se funziona**: le due funzioni compongono SQL dinamico
con `%I`, e il salto va scritto nella query che **sceglie** le famiglie, non dentro
la composizione.

🔴 **Correzione del 2026-09-02, verificata sul database.** La prima stesura
motivava la regola dicendo che *«un `NULL` passato a `format('%I')` non solleva un
errore parlante»*. **È falso**: `%I` con `NULL` solleva eccome —
`i valori vuoti non possono essere formattati come un identificativo SQL`.
⭐ La regola resta la stessa e il motivo diventa **migliore**: comporre e poi
fallire significa che un operatore vede un errore **di PostgreSQL** — nessun codice
di dominio, nessun `context`, nessun campo da accendere — al posto di una funzione
che semplicemente non considera quella famiglia. Si salta *prima* per non arrivarci.
⚠️ **E il pericolo del silenzio esiste, ma vive su `%s`**: `format('%s', NULL)`
produce **stringa vuota** senza fiatare. Se in quelle due funzioni una parte del
comando si compone con `%s`, il ramo muto è lì, non su `%I`.

### Perché proporla adesso, e perché potresti dire di no

| Per farla ora | Per rimandarla |
| --- | --- |
| è il momento di **costo minimo**: cinque righe, nessun consumatore acquisto, nessun registro vivo di acquisto | non serve a **niente** di ciò che sta in questo brief |
| dopo si tocca una tabella con registri in esercizio e il guard in servizio | il cantiere acquisto ha i suoi lotti, e questa è roba sua |
| la forma è **certa** e ha il precedente identico accanto | ⚠️ farla ora significa una colonna nullable che per mesi non ha nessun `NULL` — e questo brief altrove **contesta** proprio le strutture senza funzione |

⛔ **Non la decido io.** La riga di destra è un argomento vero, ed è lo stesso che
in §8 tiene fuori altre voci. ⇒ **P-9 è marcata come opzionale** in §6: si esegue
solo se Tid la conferma.

⚠️ E comunque **il trasloco del motore fuori da `vendite` NON è di questo brief**:
l'analisi acquisto lo ha rimandato di proposito al giorno in cui il primo ordine
d'acquisto prende davvero un numero — la regola del 2 non si applica a un secondo
consumatore che non esiste ancora.

---

## 4. Blocco C — La commessa leggibile

⛔ Oggi `vendite.commesse` ha `codice` e **nient'altro di parlante**: in una lista
non si capisce che cosa sia.

| Colonna | Tipo | Null | Note |
| --- | --- | --- | --- |
| `descrizione` | `varchar(255)` | sì | l'oggetto della commessa, in parole |
| `data_apertura` | `date` | **no**, default `script.fn_data_operativa()` | ⛔ **mai `now()` nudo**: è la convenzione del progetto |
| `responsabile_soggetto_ruolo_id` | `bigint` FK → `anagrafiche.soggetti_ruoli` | sì | chi la governa |

⭐ **Perché sono certe**: servono alla commessa **così com'è oggi**, cioè al
contenitore di fatturazione. Valgono identiche in tutti e due gli esiti della §7 —
se domani la commessa diventasse anche la testata di produzione, queste tre
resterebbero e se ne aggiungerebbero altre.

⚠️ **Attenzione al guard che nasce da solo.** La FK nuova genera un trigger
`BEFORE ROW` di *parent attivo*, e i trigger `BEFORE ROW` scattano in **ordine
alfabetico**: su `commesse` ce ne sono già tre scritti a mano
(`guard_emittente_ba`, `guard_transizione`, `guard_chiave_immutabile`). Va
verificato che il generato non **oscuri** uno di quelli, cambiando l'errore che
l'operatore vede.

---

## 4-bis. I default che AFFERMANO — e perché resta una domanda di modello

> 🔴 **Riscritta il 2026-09-02.** La prima stesura trattava questo come un problema
> di **migrazione dati**: backfill obbligatorio, sequenza in tre passi per non
> scrivere mai il valore falso. ⛔ **Era cerimonia da produzione, e produzione non
> ce n'è.** Tid: *«i dati sono solo di test, possiamo fare quello che vogliamo»* —
> è la regola già in vigore nel progetto (breaking secchi ammessi, nessun fallback
> transitorio), e qui non l'avevo applicata.
>
> ⭐ **Ma la domanda che resta non è sui dati: è sul modello.** Ed è per questo che
> la sezione non sparisce, si accorcia.

### Quel che cade

⛔ Niente sequenza `nullable → backfill → SET NOT NULL`, niente `UPDATE` di
bonifica obbligatorio, niente precauzioni sull'ordine dei changeSet. Con dati
usa-e-getta si scrive la forma finale e, se le righe di prova danno fastidio, si
rifanno. **Non è un rischio: è una comodità che abbiamo.**

### Quel che resta, ed è la parte che i dati non risolvono

`NOT NULL` è un'**affermazione strutturale**: *«ogni riga di questa tabella ha
questo dato, e lo sappiamo»*. Se esiste un caso in cui la risposta onesta è «non lo
so», allora `NOT NULL` è la scelta sbagliata **sul modello** — e resta sbagliata
anche con zero righe, perché il caso si ripresenta il giorno in cui arriva un
import, un percorso di creazione che non valorizza la colonna, o una commessa
generata da un flusso che quella data non ce l'ha.

⇒ Le tre `NOT NULL` con default vanno guardate **una per una**, e non sono la
stessa cosa:

| Colonna | Che cosa afferma il default | Verdetto sul modello |
| --- | --- | --- |
| `articoli.gestito_a_magazzino = false` | «non movimenta giacenza» | ✅ **fail-safe**: dice *nel dubbio non fare*, ed è sempre una risposta legittima. `NOT NULL` è corretto. ⚠️ Resta il registro del §7, che non è una bonifica ma un **presidio**: la colonna a `false` ovunque è indistinguibile da «nessuno l'ha ancora marcata» |
| `articoli.modo_approvvigionamento_id = ACQUISTO` | «questo articolo si compra» | ⚠️ **afferma un fatto positivo**. Per una prestazione è falso, e il vocabolario ha `NON_APPLICABILE` apposta. ⇒ da decidere: il default giusto è `ACQUISTO` o `NON_APPLICABILE`? Il primo è il caso comune, il secondo è quello che **non mente mai** |
| `commesse.data_apertura` | «questa commessa è stata aperta oggi» | ⛔ **una data inventata non è un default**: è un valore che sembra un fatto. Se una commessa può esistere senza che si sappia quando è stata aperta, la colonna è **nullable** |

⭐ **E su `data_apertura` c'è un'alternativa che non richiede di scegliere**:
`commesse.data_insert` esiste ed è `NOT NULL` per convenzione. Non è la data di
apertura *reale*, ma è **un fatto** — se si vuole `NOT NULL`, il valore iniziale
si prende da lì invece di inventarlo. ⚠️ È un `UPDATE` di comodo, non una
bonifica: lo si fa perché è più utile di «oggi», non perché ci siano dati da
salvare.

## 5. ⭐ La predisposizione BE/FE — la parte che va letta dall'altro lato

> ⛔ **Non ci sarà altra documentazione.** Questa sezione è la richiesta a BE e FE,
> e dichiara **tutto ciò che il DB consegna già pronto**, così che dall'altro lato
> non serva nessun lavoro di scoperta.

### 5.1 Che cosa il DB consegna, in una riga

**Le colonne nuove escono già dalle viste canoniche e sono già configurate come
colonne di lista.** BE e FE non devono aggiungere una vista, né una riga di
configurazione: devono **consumare** e, sul FE, tradurre le chiavi i18n.

### 5.2 Le viste che cambiano

| Vista | Colonne aggiunte | A cosa serve |
| --- | --- | --- |
| `vendite.vw_ordini_lista` | `data_consegna_richiesta_min` | ⭐ è la vista **canonica lista *e* dettaglio** degli ordini: la stessa colonna serve la lista e il drawer di testata |
| `vendite.vw_situazione_merce_ordine` | `data_consegna_richiesta`, `data_consegna_confermata`, `giorni_ritardo` | è la vista **per riga** che già tiene ordinato / consegnato / `da_spedire` con la soglia dell'impegno |
| `catalogo.vw_articoli_dettaglio` | `modo_approvvigionamento_id`, `modo_approvvigionamento_codice_interno`, `modo_approvvigionamento_descrizione`, `gestito_a_magazzino`, `lead_time_giorni` | è la vista della lista **e** del drawer articolo (lista `catalogo.articoli`, id 26) |

⭐ **`giorni_ritardo` sta lì e non altrove**, ed è la scelta che evita un difetto:
il ritardo non è «oggi > data richiesta», è «oggi > data richiesta **e** resta
merce da spedire». Il residuo e la soglia dell'impegno vivono in
`vw_situazione_merce_ordine`, che li calcola già; metterlo altrove significherebbe
ricalcolarli, cioè creare una seconda verità sul residuo. ⛔ **NULL quando
`da_spedire` è NULL o zero**: «non è in ritardo» e «non c'è niente da spedire»
sono due cose diverse, e quella vista ha già la disciplina di non confonderle.

⚠️ **Due trappole tecniche su queste viste, entrambe verificate:**

1. **`CREATE OR REPLACE VIEW` può solo APPENDERE**: le colonne nuove finiscono
   **in ultima posizione**. Non è disordine da sistemare, ed è già dichiarato nel
   commento di `vw_ordini_lista`. Chi consuma per posizione si romperebbe: si
   consuma per nome.
2. **`security_invoker=on` va RI-SPECIFICATA** in ogni `CREATE OR REPLACE VIEW`,
   altrimenti PostgreSQL la azzera e la vista smette di rispettare l'RLS di chi
   la legge. È la reloption di tutte e tre.

⛔ **E un nome che il guardrail CI respinge**: `codice_interno AS *_codice` è
**vietato** (`linee-guida-sql` §6c, presidiato da
`scripts/sql/check_naming_stato_codice.sql`). Per questo la colonna decodificata
si chiama `modo_approvvigionamento_codice_interno` e **non** `..._codice`: quel
valore viene dalla colonna immutabile, e un consumatore che confronta contro un
`*_codice` si aspetta invece quella mutabile.

### 5.3 Le colonne di lista — sono **dato**, non DDL

La configurazione delle liste è una riga in `ui.lista_colonna` per colonna,
appesa al CSV `db/changelog/migrations_v2/80_data/sql/ui/lista_colonna.csv`.

| Lista | `lista_id` | Colonne nuove |
| --- | --- | --- |
| `vendite.ordini` | **7** | `data_consegna_richiesta_min` |
| `catalogo.articoli` | **26** | `modo_approvvigionamento`, `gestito_a_magazzino`, `lead_time_giorni` |

Per ogni riga vanno dati: `codice`, `etichetta`, `campo_sorgente` (il nome della
colonna **nella vista**), `tipo_colonna = informazione`, `tipo_dato`
(`date` / `boolean` / `numero`), `formato` (`date_short` per le date),
`larghezza_default`, `ordine_default`, `allineamento`, `gruppo`,
`filtrabile` / `ordinabile` / `esportabile`, `etichetta_i18n_key`, `priorita`.

⛔ **`sensibile` resta `f`.** Non è un'etichetta: è un **cancello** — a `t`, senza
il grant corrispondente, la colonna diventa **invisibile** e nessuno capisce
perché.

⚠️ **Il CSV si appende a mano.** `csv.writer` di Python pianta un CRLF e ri-quota
tutto il file: dopo l'append, `git diff --numstat` deve dare **`1 1`** e non un
rewrite di centinaia di righe.

⭐ **Non c'è niente da aspettare, sul FE.** Le liste si montano già con
`<ListaConfigurabile>`: una colonna nuova **compare come dato**, senza toccare un
componente. L'unica cosa che serve dall'altro lato sono le **traduzioni**.

### 5.4 Le chiavi i18n dichiarate qui

Le chiavi seguono la convenzione già in uso (`vendite.contratti.col_data`,
`vendite.ordini.col_data`). Sono queste, e il FE deve solo aggiungere il testo:

```
vendite.ordini.col_data_consegna_richiesta_min
vendite.ordini_righe.col_data_consegna_richiesta
vendite.ordini_righe.col_data_consegna_confermata
catalogo.articoli.col_modo_approvvigionamento
catalogo.articoli.col_gestito_a_magazzino
catalogo.articoli.col_lead_time_giorni
config.modi_approvvigionamento.acquisto
config.modi_approvvigionamento.produzione
config.modi_approvvigionamento.stock
config.modi_approvvigionamento.non_applicabile
```

### 5.5 Che cosa deve fare il BE

1. **Righe d'ordine — scrittura**: gli endpoint di creazione/aggiornamento riga
   (vendite e acquisti) devono accettare e persistere le due date. Sono
   nullable: ometterle resta legittimo.
2. **Drawer articolo — scrittura**: i tre campi nuovi nel payload del drawer, con
   il modo di approvvigionamento come **lookup** sul vocabolario.
3. **Lookup nuovo**: `config.modi_approvvigionamento` va esposto come le altre
   decodifiche (attivi, ordinati per `ordine`).
4. **Drawer commessa**: `descrizione` e `responsabile` in scrittura,
   `data_apertura` in sola lettura (la scrive il default).
5. **Niente da fare per la lista**: le colonne arrivano dalla configurazione.

⚠️ **Sulla commessa, un fatto che eviterà una ricerca a vuoto: non esiste una
lista configurata `vendite.commesse`.** In `ui.lista_definizione` ci sono
`vendite.commesse_attivita` (id 38, senza vista) e il drill-down di dashboard,
non la commessa. Le tre colonne del Blocco C hanno quindi come sola superficie il
**drawer/API**, finché una lista non verrà configurata — e configurarla è dato,
non un cantiere.

⛔ **Capability solo sul DETTAGLIO**: se serviranno azioni di riga governate, la
sede è il dettaglio, non la lista.

### 5.6 Che cosa NON arriva a BE/FE con questo brief

Niente che riguardi la produzione: **nessun ODL, nessuno stato di copertura,
nessun ciclo di lavorazione, nessun consuntivo**. Se compaiono in una richiesta,
non vengono da qui.

---

## 6. I passi

> ⚠️ La numerazione dei file (`YYYYMMDD-NN`) è **globale per data** e il numero
> libero **scade nel minuto**: si ricontrolla subito prima di salvare, non
> all'inizio del lavoro.

| # | Passo | Fase |
| --- | --- | --- |
| **P-1** | `config.modi_approvvigionamento`: tabella + seed + lock su `codice_interno` + `fk_index_policy` | `00_schema` + `80_data` |
| **P-2** | `catalogo.articoli`: le tre colonne (FK, boolean, integer). ⚠️ **§4-bis**: decidere se il default di `modo_approvvigionamento_id` è `ACQUISTO` (il caso comune) o `NON_APPLICABILE` (quello che non mente) | `00_schema` |
| **P-3** | `vendite.ordini_righe` + `vendite.preventivi_righe` + `acquisti.ordini_righe`: le date. ⚠️ **D-16 (§2.2) va confermata PRIMA**: decide i nomi | `00_schema` |
| **P-4** | `vendite.commesse`: `descrizione`, `data_apertura`, `responsabile_soggetto_ruolo_id`. ⚠️ **§4-bis**: `data_apertura` è `NOT NULL` o nullable? Se `NOT NULL`, il valore iniziale si prende da `data_insert`, non da «oggi» | `00_schema` |
| **P-5** | `fn_push_preventivo_a_ordine` porta avanti la data richiesta (+ toglie il nome morto nel commento) | `20_code` |
| **P-6** | `catalogo.vw_articoli_dettaglio` + `vendite.vw_ordini_lista` + `vendite.vw_situazione_merce_ordine` | `20_code` |
| **P-7** | `ui.lista_colonna`: le righe nuove, append al CSV | `80_data` |
| **P-8** | pgTAP (§7) | `db/pgtap` |
| **P-9** | ⚠️ **OPZIONALE, da confermare (§3-bis)** — `famiglie_documento.colonna_billing_account` nullable + salto nel guard e nelle due `fn_*_storia_emittente` | `00_schema` + `20_code` |

⛔ **L'ordine di fase non è negoziabile**: `00_schema` → `20_code` → `80_data`.
Una `preCondition` di `20_code` **non** deve verificare il *contenuto* di
`80_data`, che gira dopo.

⚠️ **Stato finale `runOnChange: false`** su schema e codice — è vietato e
presidiato in CI (`guardrail_run_on_change.py`); resta lecito solo sul mirror CSV
di `80_data`. E `validCheckSums` **al plurale**: il singolare è una chiave che
Liquibase ignora.

⛔ **Negli YAML si cita il NOME di questo brief**
(`brief-db-modifiche-certe-ciclo-vendita-e-articolo`), **mai il path
`work-in-progress/`**: il documento un giorno si sposterà, e il riferimento deve
sopravvivere al trasloco.

---

## 7. I presidi

| Test | Che cosa prova |
| --- | --- |
| `catalogo/test-articoli-approvvigionamento-v1` | il vocabolario ha i quattro valori; un articolo non può puntare a una riga **spenta**; il default è `ACQUISTO`; `lead_time_giorni` rifiuta il negativo |
| `vendite/test-date-consegna-ordine-v1` | le date si scrivono e si rileggono sulla riga; ⭐ **la data sopravvive al push** preventivo → ordine — provata sul **percorso reale**, chiamando `fn_push_preventivo_a_ordine`, non confrontando due colonne |
| `vendite/test-situazione-merce-ritardo-v1` | `giorni_ritardo` è **NULL** quando `da_spedire` è NULL o zero, ed è valorizzato solo sopra la soglia dell'impegno |

⚠️ **Un `has_column` sulle viste non basta**: prova che la colonna esiste, non
**da dove viene il valore**. Sulle tre viste il test deve confrontare il valore
con la sorgente, altrimenti passa anche se la colonna arriva dal posto sbagliato.

⚠️ **Preambolo obbligatorio** in ogni file (`BEGIN;`, riga di contesto,
`SET CONSTRAINTS ALL IMMEDIATE`), presidiato da
`scripts/guardrail_pgtap_preambolo.py`: senza, il file diventa verde **per
sottrazione**.

⚠️ E la suite ha **rossi preesistenti**: si confronta con
`scripts/pgtap-baseline.sh`, non si attribuisce un rosso a questo lavoro senza
averlo verificato.

### ⛔ Il presidio che manca, e riguarda ciò che consegna QUESTO brief

⭐ **Aggiunto il 2026-09-01.** Le tre analisi della giornata hanno fatto uscire
**quattro volte** lo stesso difetto: *una cosa esiste, è costruita bene, e non è
collegata a niente* — il guard tipizzato montato su zero tabelle, due policy RLS
senza `ENABLE`, `magazzino.causali.ambito_causale_id` vuota in **tutte e dieci** le
righe seminate, `config.ambiti` con zero FK entranti. **Nessuna produce un rosso.**

🔴 **Questo brief consegna due candidati alla stessa classe**, e i test della
tabella sopra non li intercettano:

| Deliverable | Perché è un candidato | Il presidio che serve |
| --- | --- | --- |
| `config.modi_approvvigionamento` | è un **catalogo nuovo**: se domani nessuna vista, nessuna funzione e nessun consumatore lo legge, è vivo e inerte esattamente come `config.ambiti` | un registro che elenca i cataloghi **senza FK entranti** — e la FK da `catalogo.articoli` c'è, quindi questo passa: il presidio serve a **provarlo**, non a sperarlo |
| `articoli.gestito_a_magazzino` | `NOT NULL DEFAULT false` ⇒ al rilascio **tutte le righe sono `false`**. La §3.3 lo dice già («la merce va marcata: è un lavoro di dato») ma lo lascia come **nota** | ⛔ una nota non è un presidio: serve un **registro che deve calare** — «articoli con `gestito_a_magazzino = true`», che al rilascio vale zero e deve smettere di valerlo |

⛔ **Attenzione alla POLARITÀ del secondo registro, o nasce con lo stampo
sbagliato.** Le otto viste `dbops` esistenti — e le tre proposte dall'analisi
acquisto — devono restare **vuote**: una riga è un difetto. Questa no: «articoli
con `gestito_a_magazzino = true`» deve **riempirsi**, e lo zero è l'allarme.
⇒ Non è un registro del debito «che deve calare»: è un **controllo di prontezza**,
e va scritto come tale. Chi lo implementasse copiando lo stampo degli altri otto
otterrebbe un presidio verde esattamente nel momento in cui il problema c'è.

⚠️ **Il secondo è il più insidioso**, ed è la ragione per cui questa sezione
esiste: la colonna sarà presente, popolata, con il default fail-safe **giusto** —
e `magazzino` la leggerà trovando che nessun articolo movimenta giacenza. Nessun
errore, nessun test rosso, e un dominio intero che si comporta come se non ci
fosse merce. È **la stessa forma** di `ambito_causale_id`: seminata, valorizzata a
vuoto, e nessuno se n'è accorto per mesi.

⇒ Il presidio **generale** della classe (tre viste in `dbops` che devono restare
vuote — funzioni trigger montate da nessuno, policy su tabelle senza RLS attiva,
cataloghi orfani) è proposto in
[analisi-simmetria-ordini-acquisto §9-bis](analisi-simmetria-ordini-acquisto.md).
⚠️ **È un cantiere di `dbops`, non di questo brief**: qui resta l'obbligo del
registro su `gestito_a_magazzino`, che è nostro e non si può delegare a un cantiere
che forse non parte.

---

## 8. Che cosa NON entra, e dove sta

| Voce | Dove vive | Perché non è qui |
| --- | --- | --- |
| Stato di **copertura** della riga d'ordine | analisi commessa §8.3 | se ODL e ordine d'acquisto saranno agganciati alla riga è **derivabile**: una colonna sarebbe una seconda verità. Va fatta vista, dopo la §7 |
| `uom_id` del componente e **sfrido** sulla BoM | analisi commessa §8.4 | dipendono dal fatto che la distinta di produzione sia o no `articoli_componenti`, che è **immutabile** per un altro motivo |
| **Consuntivo**, ODL, ciclo di lavorazione | analisi commessa §6 e §7 | sono **strutture**, non colonne, e stanno di là dalla decisione |
| Cliente proprio, budget, data di chiusura prevista sulla commessa | analisi commessa §8.5 ⏸️ | dipendono dalla §7 |
| `vw_giacenza` (il segno) e la **causale di versamento** | ⭐ *aggiornato 2026-09-02*: hanno una sede loro, [analisi-db-magazzino-carico-e-scarico](analisi-db-magazzino-carico-e-scarico.md) §4, §3 e §7 | ⚠️ **il fatto è certo, la forma è una decisione**: che vadano toccati non è in dubbio, *come* sì. ✅ *2026-09-02*: la **scelta sul verso è presa** (sta nella quantità), quindi `vw_giacenza` **resta com'è**; di lei resta da scrivere il `COMMENT` che dice perché. La causale di versamento è ancora aperta |
| `uq_mag_movimenti_docref` | analisi magazzino **§8-quater** (D-4) | ⭐ *aggiornato 2026-09-01 sera*: la forma ora **c'è** — chiave dell'operazione, colonna e non tabella. Resta fuori di qui perché è `magazzino` e perché la D-4 è di Tid, non perché manchi il disegno |
| `causali.ambito_causale_id` | analisi magazzino D-8 | ⭐ *aggiornato*: gli appunti di revisione lo chiudono («valorizzare», + `NOT NULL` perché l'undicesima causale non rinasca vuota). ⇒ smetterà di essere una decisione, ma resta `magazzino`: andrà in un piano suo, non qui |
| Chi scrive un movimento di magazzino | analisi magazzino D-1 | la forma del riferimento al documento è la prima decisione aperta |
| **Prezzo di riferimento del fornitore** sull'articolo | analisi acquisto §9, D-8 | ⚠️ **tocca `catalogo.articoli`, cioè P-2.** Le due forme in campo (una colonna sull'articolo *oppure* la tabella `catalogo.articoli_fornitori`) sono una decisione aperta ⇒ chi esegue P-2 sappia che quella tabella **potrebbe essere toccata una seconda volta**, e non consideri P-2 l'ultimo intervento su di lei |
| **Discriminante di ciclo** sugli stati (`stati_doc_ordini`, `stati_doc_ddt`) | analisi acquisto §7, D-3 | il fatto è certo — le due tabelle sono **condivise con `acquisti`** e non hanno modo di dire a quale ciclo appartiene uno stato — ma la **forma** (satellite, colonna, split) è ancora da confermare |
| Ancora doppia degli **indirizzi documento** | analisi acquisto §7-bis, D-6b | tocca un BB usato da **5 domini di vendita**, ed è aperta. ⚠️ Non è DDL: è backend |
| Partita di acquisto, reso a fornitore, **chiusura del ramo credito** | analisi acquisto §8, D-14 | è il cantiere acquisto, e poggia su un motore di stato che non esiste |

### ⭐ Una convenzione che invece entra, e non costa una riga di DDL

L'analisi acquisto ha stabilito una regola che **vale per tutto il progetto** e che
finora non era scritta da nessuna parte:

> `numero` (+ `serie`, `anno`) è **sempre e solo il numero NOSTRO**, quello che
> assegna un registro. Il numero della **controparte** ha un nome proprio e non
> occupa mai quella colonna.

⚠️ **Perché riguarda anche la vendita**, benché il caso sia emerso sugli acquisti:
il «vostro riferimento» del cliente su un ordine di vendita è lo stesso concetto,
oggi non ce l'ha nessun documento, e il giorno che servirà **la tentazione sarà di
metterlo dove c'è posto**. Su `acquisti.ddt` quella tentazione ha già prodotto il
danno: `numero` **è** il numero del fornitore, e `famiglie_documento.colonna_numero`
puntata lì lo sovrascriverebbe.

⛔ Qui non si aggiunge nessuna colonna — nessuno l'ha chiesta. Si scrive la regola,
perché il costo di scriverla adesso è zero e quello di scoprirla dopo è una
migrazione.

---

### ⚠️ Revisione del 2026-09-01 (sera) — il filtro ha tenuto

Gli appunti di revisione sulle due analisi hanno chiuso o proposto **D-1** (ledger a
catalogo), **D-4** (l'indice si toglie, la regola passa su una chiave
dell'operazione), **D-6** (sciolta: il «movimento senza documento» non è un caso
reale), **D-7** (assorbita) e **D-8**; hanno ristretto **D-2/D-3** e rinviato
**D-5**.

⭐ **Ripassati i tre blocchi voce per voce: non cambia niente.** Nessuna colonna,
nessuna nullabilità, nessun default, nessuna vista, nessuna riga di lista.

Non è una coincidenza fortunata, ed è la prova che il §1 valeva la pena: le voci
di questo brief stanno su `vendite` e `catalogo`, le decisioni stanno su
`magazzino`. Muovendo le seconde, le prime non si spostano.

⇒ Della revisione è cambiata **solo la §8**, e solo nello *stato* di due voci
escluse: la loro forma adesso esiste. Restano fuori perché sono di un altro
dominio, non perché siano indecise.

---

## 9. Riferimenti

* [analisi-db-commessa-e-produzione-predisposizione.md](analisi-db-commessa-e-produzione-predisposizione.md)
  — perché il punto di fermata non è la commessa, e la §8 da cui questo brief è estratto
* [analisi-db-magazzino-aggancio-documento-e-produzione.md](analisi-db-magazzino-aggancio-documento-e-produzione.md)
  — le decisioni D-1 → D-8, nessuna delle quali tocca questo brief
* [analisi-simmetria-ordini-acquisto.md](analisi-simmetria-ordini-acquisto.md)
  — terza origine (2026-09-01): il §3-bis viene dal suo §6, la convenzione del §8
  dal suo §6 «I DUE numeri», il presidio del §7 dal suo §9-bis. ⚠️ Le sue
  decisioni aperte (D-2, D-6b, D-13) non toccano questo brief; **D-8 sì**, di
  striscio, perché insiste su `catalogo.articoli`
* Convenzioni SQL (naming, §6c sul `codice_interno`): `docs/it/linee-guida-sql.md`
* Standard liste e `<ListaConfigurabile>`: `docs/it/dev/frontend/frontend-standards.md`
* Il residuo del nome morto in `fn_push_preventivo_a_ordine`:
  [brief-db-prefisso-sul-registro-e-allineamento-contatori.md](../work-done/brief-db-prefisso-sul-registro-e-allineamento-contatori.md) §6.3
