# Guida — Documenti e Stampe

> **Ultimo aggiornamento**: 20 ottobre 2026
>
> **Destinatari**: analisti funzionali, sviluppatori backend/frontend, operatori configuratori.
>
> **Vedi anche** — schemi DB:
>
> * [documenti.tipi_documento_output](/dbzero/documenti/tabelle/tipi_documento_output) — il catalogo di che cosa si stampa
> * [documenti.template_documenti](/dbzero/documenti/tabelle/template_documenti) — i modelli, dell'azienda o standard
> * [documenti.template_documenti_versioni](/dbzero/documenti/tabelle/template_documenti_versioni) — le versioni di un modello
> * [documenti.template_asset](/dbzero/documenti/tabelle/template_asset) — loghi e allegati di un'azienda
> * [documenti.documenti_generati](/dbzero/documenti/tabelle/documenti_generati) — il registro dei PDF prodotti
> * [documenti.documenti_generati_file](/dbzero/documenti/tabelle/documenti_generati_file) — i file dei PDF
> * [documenti.render_engine_documento](/dbzero/documenti/tabelle/render_engine_documento) — i motori di render
> * [vendite.fatture_stampa_coda](/dbzero/vendite/tabelle/fatture_stampa_coda) — la coda della stampa massiva delle fatture
>
> **Vedi anche** — funzioni e viste DB:
>
> * [documenti.fn_risolvi_template_applicabile](/dbzero/documenti/funzioni/fn_risolvi_template_applicabile) — con quale modello e quale versione si stampa un documento
> * [documenti.vw_template_versioni_stampabili](/dbzero/documenti/views/vw_template_versioni_stampabili) — i modelli che possono stampare oggi
> * [documenti.vw_template_risoluzione_emittente](/dbzero/documenti/views/vw_template_risoluzione_emittente) — per ogni azienda, con che cosa si stampa ogni documento
> * [documenti.fn_personalizza_template_standard](/dbzero/documenti/funzioni/fn_personalizza_template_standard) — «personalizza»: la copia di uno standard per un'azienda
> * [documenti.vw_template_personalizzati_scarto](/dbzero/documenti/views/vw_template_personalizzati_scarto) — quanto una copia è rimasta indietro rispetto al suo standard
> * [documenti.fn_pubblica_template_documento_versione](/dbzero/documenti/funzioni/fn_pubblica_template_documento_versione) — la pubblicazione di una versione
>
> **Vedi anche** — guide correlate:
>
> * [Gestione degli indirizzi](/guide/gestione-degli-indirizzi) — gli indirizzi congelati sui documenti

---

## 1. A cosa serve il modulo documenti

Zero ERP produce documenti PDF (preventivi, contratti, ordini, DDT, fatture) in modo controllato,
versionabile e archiviato.

Il punto di partenza è separare tre cose che spesso si confondono:

1. **I dati**: chi è il cliente, cosa ha ordinato, quale totale mostrare.
2. **Il layout**: come quei dati devono apparire nella pagina (logo, tabelle, stile, firma).
3. **Il file finale**: il PDF generato in un momento preciso, con quei dati e quel layout.

Così si cambia il layout senza toccare i dati, si cambiano i dati senza toccare il layout, e si
conserva la prova esatta di come era fatto un documento nel momento in cui è stato prodotto.

Zero ERP **non è un editor di documenti**: non si compila un PDF a mano come su Word. Il modulo
gestisce la configurazione dei modelli e l'archiviazione del risultato. La generazione del PDF è
automatica, e parte quando il processo la richiede.

---

## 2. I concetti

### 2.1 Tipo di documento

Il tipo di documento dice **che cosa** si produce. È una voce di catalogo, non un modello. Quelli
del sistema sono sei: preventivo, contratto, offerta commerciale, ordine di vendita, DDT di
vendita, fattura di vendita.

Lo stesso tipo può avere modelli diversi per aziende diverse. E la stessa sorgente può produrre
più tipi: una fattura, per esempio, potrebbe avere anche un allegato con un tipo suo.

### 2.2 Modello (template)

Il modello è la **definizione del layout** di un tipo di documento per una sorgente di dati (il
preventivo, l'ordine, la fattura…). Non contiene l'HTML: il contenuto sta nelle versioni.

Un modello è di uno di due generi:

* **dell'azienda**: appartiene a un'azienda emittente, e vale solo per i suoi documenti;
* **standard**: è del sistema, non ha un'azienda e vale per tutte. Il sistema ne fornisce uno per
  ogni tipo di documento. Uno standard non si modifica dall'interfaccia: lo fanno evolvere gli
  aggiornamenti del sistema. Chi lo vuole diverso lo **personalizza** (§4).

Ogni modello ha il flag **predefinito**: per ogni azienda, tipo di documento e sorgente c'è al
massimo un predefinito attivo, e uno solo anche fra gli standard. Il database rifiuta il secondo.

### 2.3 Versione

Ogni modello ha più versioni nel tempo. La versione contiene l'HTML e il CSS veri.

| Stato | Significato |
|---|---|
| `BOZZA` | In preparazione: si modifica liberamente, non stampa |
| `PUBBLICATA` | Usabile per generare documenti, dalla sua data di validità |
| `OBSOLETA` | Superata da una pubblicazione successiva |

Una versione pubblicata **non cambia più**: per cambiare il layout si crea una versione nuova. Per
lo stesso modello le versioni pubblicate attive non si sovrappongono nel tempo. Pubblicando una
versione nuova, la precedente si chiude il giorno prima e diventa obsoleta.

Ogni versione dichiara anche la **forma dei dati** che legge (`versione_contesto`): se la stampa
prepara dati di una forma diversa, il database la ferma prima del render, invece di produrre un
PDF sbagliato.

### 2.4 Asset

Gli asset sono gli elementi grafici di un'azienda: logo, carta intestata, firma, allegati. Una
versione li richiama per codice, e il motore li cerca **fra gli asset dell'azienda del
documento**. Un asset che manca ferma la stampa, invece di produrre un PDF senza logo. Per questo i
modelli standard non richiamano asset.

Un asset non si sovrascrive: se il logo cambia si carica un asset nuovo, e i documenti già
generati continuano a puntare al vecchio.

---

## 3. Con quale modello si stampa un documento

La scelta la fa **il database**, con una funzione sola: chi stampa (le viste, la coda delle
fatture, l'anteprima) la chiama, e ne riceve il modello **e** la versione con cui stampare.

### 3.1 Un modello conta solo se può stampare

Un modello entra nella scelta solo se **oggi può stampare**:

* il modello è attivo;
* ha una versione pubblicata, attiva e valida alla data di oggi dell'azienda.

Un modello con la sola bozza, una versione spenta, o una pubblicazione che vale da una data futura
non contano. La regola sta in un posto solo, e la usano la stampa, «personalizza» e lo scarto.

### 3.2 I due livelli

Se chi stampa non indica un modello, la regola è:

1. **l'azienda ha modelli suoi che possono stampare** per quel tipo e quella sorgente: si stampa
   con il **suo predefinito**. Se nessuno dei suoi è predefinito, la stampa si ferma e chiede di
   segnarne uno. Lo standard non entra: un modello suo pubblicato vuol dire «per questo documento
   uso i miei», e un predefinito dimenticato non deve far uscire il documento con la grafica
   sbagliata;
2. **l'azienda non ne ha nessuno**: si stampa con lo **standard predefinito**. Se nemmeno quello
   può stampare, la stampa si ferma con un errore che va segnalato all'assistenza.

Spegnere tutti i propri modelli di un tipo riporta allo standard.

Il tipo di documento si può omettere solo se, fra i modelli che possono stampare, ce n'è uno solo
per quella sorgente. Con più tipi la stampa si ferma invece di sceglierne uno a caso.

### 3.3 Il modello indicato

Chi stampa può **indicare** il modello: l'operatore che lo sceglie al momento della stampa, o la
riga della coda delle fatture che porta un modello forzato. In questo caso il modello non si
sceglie, **si verifica**, con la stessa funzione:

* deve essere adatto al documento: stessa sorgente, stesso tipo (se indicato), e dell'azienda del
  documento oppure standard;
* deve poter stampare oggi (§3.1): un modello spento indicato a mano non stampa.

### 3.4 Che cosa vede l'operatore quando la stampa si ferma

| Caso | Che cosa dice | Chi rimedia |
|---|---|---|
| Modelli suoi pubblicati, nessuno predefinito | l'azienda ha modelli suoi, ma nessuno è predefinito | l'operatore: segna un predefinito |
| Nessun modello, nemmeno lo standard | nessun modello di stampa per il documento | l'assistenza: manca lo standard |
| Tipo non indicato su una sorgente con più tipi | il documento produce più tipi | chi ha chiamato la stampa: indicare il tipo |
| Modello indicato spento o senza versione valida | il modello oggi non può stampare, e perché | l'operatore: lo riattiva o pubblica una versione |
| Modello indicato non adatto | il modello non è adatto a questo documento, e perché | l'operatore: sceglie un altro modello |

### 3.5 Che cosa vede la lista Modelli documento

Per ogni azienda e ogni documento la lista mostra con che cosa si stampa: con il suo modello, con
lo standard, oppure bloccata perché ha modelli suoi ma nessun predefinito. È la stessa regola della
stampa, letta dal database, non ricalcolata.

---

## 4. Il modello standard e «personalizza»

### 4.1 Lo standard

Un'azienda nuova stampa dal primo giorno con gli standard, senza configurare niente. Gli standard
non hanno testi fissi di un'azienda e non richiamano asset. Si leggono da tutti e non si
modificano dall'interfaccia: il database rifiuta la scrittura.

### 4.2 Personalizzare

«Personalizza» crea il modello di un'azienda a partire da uno standard, in un'operazione sola:

* la copia parte dalla **versione con cui lo standard stampa oggi**;
* nasce come bozza: finché non la si pubblica, l'azienda continua a stampare con lo standard;
* nasce **predefinita** se l'azienda non ha già un suo predefinito per quel documento; altrimenti
  no, e la scelta fra i due resta all'operatore;
* ricorda da quale versione dello standard deriva.

Si personalizza solo uno standard che stampa oggi. Uno standard non predefinito (per esempio un
layout alternativo) si può personalizzare: la copia si confronta con lui.

### 4.3 Lo scarto

Una copia smette di ricevere le evoluzioni dello standard. Lo scarto dice quanto è rimasta
indietro, confrontando la versione con cui la copia stampa oggi con quella dello standard da cui
deriva:

| Stato | Significato |
|---|---|
| `ALLINEATA` | la copia deriva dalla versione con cui lo standard stampa oggi |
| `STANDARD_AVANTI` | lo standard è andato avanti: la copia funziona, ma non ha l'evoluzione |
| `CONTESTO_SUPERATO` | la copia legge una forma dei dati più vecchia: alla stampa si fermerà |
| `ORIGINE_NON_DICHIARATA` | il modello non dice da dove deriva: si confronta solo la forma dei dati, con lo standard predefinito |

---

## 5. Come è fatto un modello

Il contenuto di una versione è **HTML con CSS incorporato**. Riceve i dati da un contesto JSON
preparato dal backend, e usa le variabili con la sintassi dei template (Jinja2).

Il modello **non interroga mai il database**: riceve solo i dati già preparati. Niente logica
nascosta nel layout, e la generazione è riproducibile.

La **fattura** non legge i dati «vivi»: intestazione delle due parti e indirizzo arrivano dai
valori congelati sul documento quando è nata. Cambiando l'anagrafica e ristampando, il PDF della
fattura non cambia. Il dettaglio è nella guida
[Gestione degli indirizzi](/guide/gestione-degli-indirizzi).

---

## 6. Che cosa succede quando si genera un documento

1. Il database dice **modello e versione** (§3).
2. Il database controlla che la versione legga la forma dei dati che la stampa prepara.
3. Il backend prepara il contesto JSON.
4. Il motore combina HTML, dati e asset dell'azienda del documento.
5. Il motore produce il PDF (WeasyPrint).
6. Il PDF va nello storage, e nasce il record del documento generato.

Il record del documento generato porta il modello e la versione usati, lo snapshot del contesto,
l'hash del contenuto, chi l'ha generato e quando, il file. Alla sua scrittura il database
ricontrolla che il modello sia adatto al documento: è la stessa regola del §3.3.

La **ristampa fedele** di un documento già generato usa la versione registrata sul documento,
anche se oggi non stamperebbe più: è la prova di com'era, non una stampa nuova.

---

## 7. La coda di stampa delle fatture

La stampa massiva delle fatture non avviene mentre si numera: chi chiude il lotto **accoda** una
riga per fattura, e un worker le stampa dopo, fuori dalla transazione della numerazione.

* La riga può dire **che cosa stampare**: il tipo di documento. Senza tipo decide il database
  alla stampa, se il candidato è uno.
* La riga può forzare un **modello**: allora indica anche il tipo, e il modello deve essere di
  quel tipo e delle fatture. Alla stampa passa dalla verifica del §3.3.
* Per una fattura le righe in attesa sono **o** una senza tipo, **o** più righe con tipi diversi.
  Una riga senza tipo esclude le altre: sarebbe la stessa stampa due volte. Riaccodare non
  duplica niente; dopo una stampa conclusa si può riaccodare.

---

## 8. Configurare i documenti di un'azienda

Di solito non serve niente: l'azienda stampa con gli standard. Per un layout suo:

1. **Personalizzare** lo standard del documento (§4.2): nasce la copia in bozza.
2. **Modificare** la bozza: HTML, CSS, margini; provarla su dati di prova con l'anteprima.
3. **Pubblicarla** da una data: da quel giorno l'azienda stampa con la sua.
4. **Caricare gli asset** che il layout richiama (logo, firma).

Per un modello scritto da zero si crea il modello dell'azienda, la prima versione, e la si
pubblica. Per cambiare un layout in uso si crea una versione nuova: quella pubblicata non cambia.

Un tipo di documento nuovo si aggiunge al catalogo dei tipi, con lo standard che lo stampa: è un
aggiornamento del sistema, non una configurazione dell'azienda.

---

## 9. Più aziende

Il modulo vale per più aziende emittenti. I modelli di un'azienda, e i suoi asset, valgono solo
per i suoi documenti; gli standard valgono per tutte. Un operatore vede i modelli delle aziende
del suo perimetro e gli standard. Un amministratore che vede più aziende sceglie l'azienda quando
configura o genera.

---

## 10. Che cosa il modulo non fa ancora

* **Allegati PDF componibili**: accodare PDF esistenti (condizioni generali, allegati) al
  documento generato.
* **Più motori di render**: oggi c'è solo WeasyPrint.
* **Editor visuale**: il modello si modifica scrivendo HTML e CSS.
* **Logo nello standard**: uno standard non richiama asset; il logo dell'azienda, quando c'è,
  richiederebbe che il modello possa chiedere se l'asset esiste.

---

## 11. Garanzie del sistema

| Garanzia | Come è implementata |
|---|---|
| Un PDF si ricollega sempre al modello e alla versione usati | Sono registrati nel documento generato |
| Il layout di una versione pubblicata non cambia | Le colonne della versione sono bloccate dal database una volta pubblicata |
| Un documento si stampa solo con un modello che può stampare | La regola sta in un punto solo del database, letto da tutta la stampa |
| Un modello di un'azienda non stampa i documenti di un'altra | Lo verifica il database prima del render e alla scrittura del documento generato |
| Un'azienda nuova emette dal primo giorno | Gli standard di sistema |
| Uno standard non si modifica dall'interfaccia | Il database rifiuta la scrittura a chi non è il proprietario delle tabelle |
| Un asset non sparisce se lo si aggiorna | Gli asset sono in sola aggiunta |
| Un documento generato non si cancella | Il record è protetto; lo stato cambia ad archiviato o annullato |
| Il PDF prodotto è verificabile | L'hash del file è conservato col record |

---

## 12. Struttura DB di riferimento

```text
documenti/
├── tipi_documento_output              — catalogo dei tipi (PREVENTIVO, FATTURA_VENDITA, ...)
├── tipi_asset_documento               — catalogo dei tipi di asset (LOGO, FIRMA, ...)
├── tipi_file_documento                — catalogo dei tipi di file (PDF_FINALE, ...)
├── render_engine_documento            — motori di render (WEASYPRINT)
├── template_documenti                 — i modelli, dell'azienda o standard
├── template_documenti_versioni        — le versioni (BOZZA / PUBBLICATA / OBSOLETA)
├── template_asset                     — gli asset di un'azienda
├── documenti_generati                 — il registro delle generazioni
├── documenti_generati_file            — i file dei PDF
├── vw_template_versioni_stampabili    — i modelli che possono stampare oggi
├── vw_template_risoluzione_emittente  — per ogni azienda e documento, con che cosa si stampa
└── vw_template_personalizzati_scarto  — lo scarto delle copie dal loro standard
```

I parametri dello storage (provider, bucket, limiti) sono in `config.parameters` con prefisso
`documenti_*`.

---

## Area tecnica — esempi

Per vedere con che cosa stampa ogni documento di un'azienda (l'esito, il modello e la versione):

```sql
SELECT tipo_documento_output_id, sorgente_tipo_id, esito,
       template_documento_id, template_versione_id
  FROM documenti.vw_template_risoluzione_emittente
 WHERE emittente_fiscale_id = :emittente;
```

Per sapere con quale modello e versione si stamperebbe un documento, e perché si ferma:

```sql
SELECT *
  FROM documenti.fn_risolvi_template_applicabile(:sorgente_tipo_id, :emittente, :tipo);
```

Il contesto JSON che un modello di preventivo riceve, in forma ridotta:

```json
{
  "preventivo": { "codice": "PREV-2026-0001", "data": "2026-04-29" },
  "cliente": { "ragione_sociale": "Cliente Demo", "indirizzo": "Via Roma 1, Milano" },
  "righe": [
    { "descrizione": "Servizio di consulenza", "quantita": 5, "prezzo_unitario": 120.00, "totale": 600.00 }
  ],
  "totali": { "imponibile": 600.00, "iva": 132.00, "totale": 732.00 }
}
```

---
{% include-markdown "signature-core.md" %}
