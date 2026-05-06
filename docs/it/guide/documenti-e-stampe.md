# Guida — Documenti e Stampe

> **Ultima revisione**: maggio 2026 — copertura Fase A (schema `documenti`,
> template versionati, asset, generazione PDF con WeasyPrint).
>
> **Destinatari**: analisti funzionali, sviluppatori backend/frontend, operatori configuratori.
>
> **Vedi anche** — schemi DB:
>
> * [documenti.template_documenti](/dbzero/documenti/tabelle/template_documenti)
> * [documenti.template_documenti_versioni](/dbzero/documenti/tabelle/template_documenti_versioni)
> * [documenti.template_asset](/dbzero/documenti/tabelle/template_asset)
> * [documenti.documenti_generati](/dbzero/documenti/tabelle/documenti_generati)
> * [documenti.documenti_generati_file](/dbzero/documenti/tabelle/documenti_generati_file)
> * [documenti.tipi_documento_output](/dbzero/documenti/tabelle/tipi_documento_output)
> * [documenti.render_engine_documento](/dbzero/documenti/tabelle/render_engine_documento)

---

## 1. A cosa serve il modulo documenti

Zero ERP può produrre documenti PDF — preventivi, contratti, ordini, comunicazioni — in modo controllato, versionabile e archiviato.

Il punto di partenza è separare tre cose che spesso si confondono:

1. **I dati**: chi è il cliente, cosa ha ordinato, quale totale mostrare.
2. **Il layout**: come quei dati devono apparire nella pagina (logo, tabelle, stile, firma).
3. **Il file finale**: il PDF generato in un momento preciso, con quei dati e quel layout.

Questa separazione permette di cambiare il layout senza toccare i dati, di cambiare i dati senza toccare il layout, e di conservare la prova esatta di come era fatto un documento nel momento in cui è stato prodotto.

Zero ERP **non è un editor di documenti**: non si compila un PDF a mano come su Word. Il modulo gestisce la fase a monte — la configurazione del template — e la fase a valle — l'archiviazione del risultato. La generazione del PDF è automatica, avviata dal processo applicativo nel momento in cui il documento è richiesto.

---

## 2. I quattro concetti fondamentali

### 2.1 Tipo di documento

Il tipo di documento definisce **che cosa** si sta producendo: un preventivo, un contratto, un ordine. È una voce di catalogo, non un template. Lo stesso tipo può avere template diversi per emittenti diverse.

Esempi di tipi configurati:

| Codice interno | Descrizione |
|---|---|
| `PREVENTIVO` | Preventivo commerciale |
| `CONTRATTO` | Contratto di fornitura |
| `ORDINE_CLIENTE` | Conferma ordine cliente |
| `COMUNICAZIONE` | Comunicazione generica |

Nuovi tipi si aggiungono dalla configurazione, senza modificare il codice.

### 2.2 Template

Il template è la **definizione del layout** per un certo tipo di documento, collegata a un'emittente fiscale e a una sorgente dati.

Un template ha:

- un nome e un codice identificativo;
- il tipo di documento a cui si applica;
- l'emittente fiscale per cui vale (carta intestata diversa per aziende diverse);
- la sorgente dati a cui è collegato (es. `VENDITE` per i preventivi);
- un flag per indicare se è il template predefinito per quel tipo/emittente.

Un template **non contiene il codice HTML**. Il contenuto sta nelle versioni.

#### Il template di default

Il flag `is_default` indica quale template usare quando il processo applicativo non specifica un template preciso. Il backend risolve automaticamente: *"devo generare un PREVENTIVO per l'emittente X — prendo il template attivo di default per questa combinazione"*.

Il vincolo "un solo default" vale per la tripla `(tipo documento, sorgente, emittente)`. Questo significa che si possono avere default indipendenti per tipi diversi:

| Tipo | Emittente | Quanti default |
| --- | --- | --- |
| PREVENTIVO | Azienda A | al massimo 1 |
| ORDINE | Azienda A | al massimo 1 |
| PREVENTIVO | Azienda B | al massimo 1 |

Il default per i preventivi e il default per gli ordini sono vincoli separati e non interferiscono tra loro. Il DB blocca il tentativo di impostare due template di default per lo stesso tipo e la stessa emittente.

Se per un tipo di documento esiste un solo template, impostarlo come default è quasi sempre la scelta corretta.

#### Template non-default: quando servono e come vengono scelti

Un template non-default non viene mai usato automaticamente: qualcosa di esterno deve indicare esplicitamente quale template usare al posto del default. Il DB supporta questo passaggio — `documenti_generati` registra sempre quale template è stato usato — ma la logica di selezione vive nel backend o nella UI.

Ci sono tre modalità con cui un template non-default può essere selezionato:

##### 1. Campo sul record sorgente

Il record che origina il documento (es. la testata del preventivo) ha una colonna `template_documento_id`. Se è valorizzata, il backend usa quel template specifico; se è NULL, cade sul default. La scelta si fa una volta sola sulla testata e rimane fissa per tutta la vita del documento.

È il pattern più pulito: la scelta è tracciata nel dato, non dipende da chi avvia la stampa.

##### 2. Scelta dell'utente al momento della stampa

La UI mostra un selettore — *"quale modello vuoi usare?"* — prima di avviare la generazione. L'utente sceglie ogni volta. È più flessibile ma richiede un passo manuale a ogni stampa.

##### 3. Regola di business nel backend

Il service decide in base a una logica applicativa senza coinvolgere l'utente. Esempio classico: se il cliente ha lingua impostata a `EN`, il backend seleziona automaticamente il template in inglese anziché il default in italiano. La regola vive nel codice, non nella configurazione.

Esempio concreto di questo scenario:

| Template | `is_default` | Quando viene usato |
| --- | --- | --- |
| Preventivo IT (layout standard) | sì | clienti italiani — selezione automatica |
| Preventivo EN (layout in inglese) | no | clienti esteri — il backend lo sceglie leggendo la lingua del cliente |

In questo caso il template EN non ha bisogno di essere "impostato" dall'utente: è il backend che, prima di avviare la generazione, verifica la lingua del cliente e sceglie il template corretto. Per l'operatore il processo è trasparente.

> **Nota per lo sviluppo**: la logica di selezione del template non-default non è ancora implementata nella Fase A, dove ogni tipo di documento ha un solo template attivo. Va disegnata nel momento in cui emerge il primo caso d'uso concreto che la richiede, scegliendo tra le tre modalità sopra quella più adatta al contesto.

### 2.3 Versione del template

Ogni template può avere più versioni nel tempo. Una versione contiene il **codice HTML/CSS** effettivo che verrà usato per generare il PDF.

Una versione può trovarsi in uno di tre stati:

| Stato | Significato |
|---|---|
| `BOZZA` | In lavorazione, non ancora usata in produzione |
| `PUBBLICATA` | Attiva e usabile per generare documenti |
| `OBSOLETA` | Disattivata, non più usabile per nuove generazioni |

Regola chiave: **una versione pubblicata è immutabile**. Non si modifica un template già in produzione — si crea una nuova versione. Questo garantisce che i PDF generati in passato siano sempre ricostruibili a partire dalla stessa definizione di layout.

Per lo stesso template, una sola versione può essere pubblicata nel medesimo periodo di validità. Quando si pubblica una nuova versione con decorrenza successiva, il comando DB di pubblicazione chiude automaticamente la versione pubblicata precedente al giorno prima della nuova decorrenza e la porta a `OBSOLETA`.

### 2.4 Asset aziendali

Gli asset sono gli elementi grafici e documentali riutilizzabili collegati a un'emittente:

- logo;
- carta intestata;
- firma autorizzata;
- immagini promozionali;
- condizioni generali in PDF.

Ogni asset è identificato da un codice stabile. Il template HTML può fare riferimento agli asset tramite quel codice: il motore di render li recupera automaticamente al momento della generazione.

Analogamente alle versioni, **un asset non si sovrascrive**: se il logo cambia, si carica un nuovo asset. Il vecchio resta presente e continua a essere usato dai documenti generati in precedenza.

---

## 3. Come è fatto un template

Il contenuto di una versione è scritto in **HTML con CSS incorporato**. Il template riceve i dati tramite un contesto JSON preparato dal backend e può usare variabili con la sintassi standard dei template (es. Jinja2).

Esempio di struttura di contesto per un preventivo:

```json
{
  "preventivo": {
    "codice": "PREV-2026-0001",
    "data": "2026-04-29"
  },
  "cliente": {
    "ragione_sociale": "Cliente Demo",
    "indirizzo": "Via Roma 1, Milano"
  },
  "righe": [
    {
      "descrizione": "Servizio di consulenza",
      "quantita": 5,
      "prezzo_unitario": 120.00,
      "totale": 600.00
    }
  ],
  "totali": {
    "imponibile": 600.00,
    "iva": 132.00,
    "totale": 732.00
  }
}
```

Il template **non interroga mai il database direttamente**: riceve sempre e solo i dati già preparati. Questo è un vincolo intenzionale: evita logica nascosta nel layout e rende la generazione riproducibile.

---

## 4. Cosa succede quando un documento viene generato

Quando il processo applicativo richiede la generazione di un documento (es. alla conferma di un preventivo), il sistema:

1. Recupera il template predefinito per quel tipo di documento e quell'emittente.
2. Identifica la versione pubblicata attiva in quel momento.
3. Prepara il contesto JSON con tutti i dati necessari.
4. Renderizza l'HTML combinando template, dati e asset.
5. Converte l'HTML in PDF tramite il motore configurato (WeasyPrint per la Fase A).
6. Salva il PDF nello storage e crea un record permanente.

Il record del documento generato contiene:

- il riferimento al template e alla versione usata;
- lo snapshot del contesto JSON usato (i dati al momento esatto);
- l'hash del contenuto per verificarne l'integrità;
- chi ha avviato la generazione e quando;
- il riferimento al file PDF archiviato.

Questo permette di rispondere in qualsiasi momento a: *"Con quale template e con quali dati è stato prodotto questo PDF?"*

---

## 5. Configurare un nuovo tipo di documento

I passi per rendere operativo un nuovo tipo di documento seguono sempre questo ordine.

### Passo 1 — Aggiungere il tipo di documento

Nella tabella `documenti.tipi_documento_output` si aggiunge il nuovo tipo con il suo codice interno e la descrizione. Il codice interno, una volta impostato, non cambia: viene usato come riferimento stabile dal codice applicativo.

Se il tipo è un nuovo caso d'uso (es. un tipo di allegato contrattuale), si verifica anche se serve una nuova voce nella lookup delle sorgenti (`config.sorgenti`) che indichi da dove vengono i dati.

### Passo 2 — Creare il template

Si crea un record in `documenti.template_documenti` specificando:

- il tipo di documento;
- l'emittente fiscale a cui si applica;
- la sorgente dati;
- se è il template predefinito per quella combinazione.

### Passo 3 — Scrivere la prima versione

Si crea una versione in stato `BOZZA` con il contenuto HTML/CSS del layout. In questa fase si può modificare liberamente il template, testarlo su dati di prova, aggiustare margini e stili.

### Passo 4 — Pubblicare la versione

Quando il layout è pronto, la versione passa a `PUBBLICATA`. Da questo momento può essere usata per generare documenti reali.

Se in futuro il layout deve cambiare, si crea una nuova versione `BOZZA` a partire dal contenuto attuale, si modificano i cambiamenti, e si pubblica quella nuova versione. La precedente passa a `OBSOLETA`.

### Passo 5 — Caricare gli asset

Per ogni emittente, si caricano gli asset necessari (logo, carta intestata, firma). Gli asset vengono referenziati nel template HTML tramite codice stabile; il motore di render li risolve automaticamente al momento della generazione.

---

## 6. Multi-azienda

Il modulo è progettato per ambienti con più emittenti fiscali (aziende o unità operative distinte). Template e asset sono sempre collegati a un'emittente specifica.

Un operatore che lavora nel contesto di un'emittente vede e usa solo i template e gli asset di quell'emittente. Gli utenti amministratori possono scegliere esplicitamente l'emittente quando configurano documenti o avviano generazioni fuori dal contesto operativo normale.

---

## 7. Cosa non fa il modulo (in questa fase)

Alcune funzionalità sono previste ma rimandate a fasi successive:

- **Allegati PDF componibili**: accodare PDF esistenti (condizioni generali, allegati contrattuali) al documento generato.
- **Più motori di render**: per ora l'unico motore supportato è WeasyPrint (PDF da HTML). In futuro potranno aggiungersi motori alternativi.
- **Log eventi di stato**: tracciare chi ha archiviato o annullato un documento generato.
- **Editor UI**: un'interfaccia per modificare il template direttamente da browser. Per ora la modifica avviene editando il codice HTML/CSS della versione.

---

## 8. Garanzie del sistema

Il modulo offre alcune garanzie strutturali, non negoziabili:

| Garanzia | Come è implementata |
|---|---|
| Un PDF può sempre essere ricollegato al template usato | La versione è registrata nel documento generato |
| Il layout di una versione pubblicata non cambia | Le colonne strutturali sono bloccate dal DB una volta in stato PUBBLICATA |
| Un asset non sparisce se lo si aggiorna | I file asset sono append-only; per cambiare si carica un nuovo asset |
| Un documento generato non si cancella | Il record è protetto da cancellazione; lo stato cambia ad `ARCHIVIATO` o `ANNULLATO` |
| Il PDF prodotto è verificabile | L'hash del file è conservato assieme al record |

---

## 9. Struttura DB di riferimento

```
documenti/
├── tipi_documento_output        — catalogo tipi (PREVENTIVO, CONTRATTO, ...)
├── tipi_asset_documento         — catalogo tipi asset (LOGO, FIRMA, CSS, ...)
├── tipi_file_documento          — catalogo tipi file (PDF_FINALE, ...)
├── render_engine_documento      — motori di render (WEASYPRINT, ...)
├── template_documenti           — contenitore logico del template
├── template_documenti_versioni  — versioni (BOZZA / PUBBLICATA / OBSOLETA)
├── template_asset               — catalogo asset per emittente
├── documenti_generati           — registro storico delle generazioni
└── documenti_generati_file      — file PDF collegati alla generazione
```

I parametri di configurazione dello storage (provider, bucket, limiti di dimensione) sono in `config.parameters` con prefisso `documenti_*`.
