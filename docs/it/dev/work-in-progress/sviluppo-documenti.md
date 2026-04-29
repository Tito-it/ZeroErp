# WIP — Sviluppo Documenti Parametrici

> Stato: **ANALISI INIZIALE**
>
> Data: aprile 2026
>
> Scopo: definire il modello per generare documenti PDF parametrizzabili
> (preventivi, contratti, ordini, allegati, comunicazioni) separando dati,
> template, asset aziendali e file finale generato.

---

## 1. Obiettivo

Vogliamo costruire uno strumento per produrre documenti in modo controllato,
versionabile e riutilizzabile.

I documenti possono essere:

- preventivi commerciali;
- contratti;
- ordini;
- allegati contrattuali;
- comunicazioni al cliente o al fornitore;
- documenti misti composti da parti generate e PDF allegati.

Il punto centrale e' questo: un documento finale non e' solo "una pagina da
disegnare". E' il risultato di piu' elementi:

1. dati letti dal DB;
2. regole applicative che decidono quali dati esporre;
3. template che definisce come presentarli;
4. asset aziendali come logo, carta intestata, firme, condizioni generali;
5. file PDF generato e archiviato.

L'obiettivo non e' crear un editor tipo Word dentro ZeroERP . La prima
fase deve invece creare fondamenta solide: template versionati, context dati
pulito, allegati componibili e PDF finale tracciato.

## Nota  personale: 
  non dovrà esserci un Editor tipo word. 
  Zeroerp non è un editor deve solo cercare di semplificare l'attività di generazione documenti
---

## 2. Impostazione semplice

Separiamo il problema in quattro livelli.

### 2.1 Dati del documento

Il backend legge dal DB e costruisce un **document context** JSON.

Esempio per un preventivo:

```json
{
  "preventivo": {
    "codice": "PREV-2026-0001",
    "data": "2026-04-29"
  },
  "cliente": {
    "ragione_sociale": "Cliente Demo",
    "indirizzo": "Via Roma 1"
  },
  "righe": [
    {
      "descrizione": "Servizio A",
      "quantita": 1,
      "prezzo_unitario": 100,
      "totale": 100
    }
  ],
  "totali": {
    "imponibile": 100,
    "iva": 22,
    "totale": 122
  }
}
```

Il template non deve interrogare il DB direttamente. Riceve solo il JSON gia'
preparato dal backend.

### 2.2 Template

Il template decide come presentare i dati.

Per la prima versione il formato consigliato e':

- HTML/CSS per layout, tabelle, header/footer, paginazione;
- markdown solo per blocchi testuali controllati;
- variabili del context con sintassi template;
- niente editor visuale libero nella v1.

### 2.3 Asset aziendali

Gli asset sono elementi riusabili:

- logo;
- carta intestata;
- firme;
- timbri;
- immagini;
- PDF da anteporre o accodare;
- condizioni generali standard.

Gli asset sono specifici per emittente fiscale / azienda. Non e' previsto un
fallback globale: nel modello operativo un operatore lavora sempre nel contesto
di una emittente, salvo utenti admin che devono scegliere esplicitamente
l'emittente quando generano/configurano documenti.

### 2.4 Documento generato

Quando un documento viene generato, salviamo:

- template usato;
- versione template usata;
- sorgente dati;
- context JSON usato;
- file PDF finale;
- hash del contenuto;
- utente e data generazione.

Questo permette di dimostrare con quale modello e con quali dati e' stato
prodotto un PDF.

---

## 3. Principi

1. **Template versionati**: un PDF generato oggi deve restare collegato alla
   versione template usata oggi, anche se domani il template cambia.
2. **Dati separati dal layout**: il backend prepara i dati; il template li
   presenta.
3. **Nessuna query DB dentro il template**: evita logica nascosta e problemi di
   sicurezza.
4. **PDF finale archiviato**: non affidarsi solo alla rigenerazione dinamica.
5. **Allegati componibili**: condizioni generali e allegati contrattuali possono
   essere PDF gia' esistenti da accodare.
6. **Multi azienda/emittente**: carta intestata e template possono variare per
   emittente fiscale.
7. **Prima governato, poi editor**: partire con template tecnici controllati;
   aggiungere editor UI solo quando il modello e' stabile.

---

## 4. Schema DB proposto

Schema candidato: `documenti`.

Motivazione:

- il dominio e' trasversale a vendite, acquisti, pratiche, portale;
- non e' corretto legarlo solo a `vendite`;
- deve poter generare PDF da sorgenti diverse.

Tabelle principali da generare:

1. `documenti.tipi_documento_output`
2. `documenti.template_documenti`
3. `documenti.template_documenti_versioni`
4. `documenti.template_asset`
5. `documenti.template_allegati`
6. `documenti.documenti_generati`
7. `documenti.documenti_generati_file`
8. `documenti.documenti_generati_eventi`

---

## 5. Tabelle previste

### 5.1 `documenti.tipi_documento_output`

Lookup dei tipi di documento generabili.

E' una tabella dedicata del modulo `documenti`, separata dai cataloghi
documentali gestionali/fiscali esistenti. Qui si classificano gli output
producibili dal motore documentale.

Esempi:

- `PREVENTIVO`
- `CONTRATTO`
- `ORDINE_CLIENTE`
- `ORDINE_FORNITORE`
- `ALLEGATO_CONTRATTUALE`
- `COMUNICAZIONE`

Colonne previste:

| Colonna              | Tipo                                       | Note                                      |
| -------------------- | ------------------------------------------ | ----------------------------------------- |
| `id`                 | bigserial PK                               | Identificativo                            |
| `codice`             | varchar(80)                                | Codice tecnico breve, unico               |
| `codice_interno`     | varchar(80)                                | Codice stabile interno, opzionale o unico |
| `descrizione`        | text                                       | Descrizione leggibile                     |
| `area_funzionale_id` | bigint FK `config.aree_funzionali.id` NULL | Area prevalente, es. vendite/acquisti     |
| `attivo`             | boolean                                    | Soft enable                               |
| `meta`               | jsonb                                      | Estensioni future                         |
| `storicizza`         | boolean                                    | Standard audit/storico                    |
| `tx_id`              | uuid                                       | Standard transazione                      |
| `user_insert`        | text                                       | Audit                                     |
| `data_insert`        | timestamptz                                | Audit                                     |
| `user_update`        | text                                       | Audit                                     |
| `data_update`        | timestamptz                                | Audit                                     |

Vincoli/indici:

- unique su `codice`;
- unique su `codice_interno` se valorizzato;
- indice su `attivo`;
- lock columns su `codice` e `codice_interno`.

---

### 5.2 `documenti.template_documenti`

Testata logica del template.

Un template rappresenta una famiglia: per esempio "Preventivo standard
vendite", "Contratto fibra aziendale", "Ordine fornitore standard".

Colonne previste:

| Colonna                    | Tipo                                           | Note                                               |
| -------------------------- | ---------------------------------------------- | -------------------------------------------------- |
| `id`                       | bigserial PK                                   | Identificativo                                     |
| `tipo_documento_output_id` | bigint FK                                      | Tipo documento generato                            |
| `codice`                   | varchar(120)                                   | Codice template, unico nel tipo                    |
| `descrizione`              | text                                           | Nome leggibile                                     |
| `sorgente_tipo_id`         | bigint FK `config.sorgenti.id`                 | Sorgente applicativa gestita dal template, es. `PREVENTIVO` |
| `context_builder_code`     | varchar(160)                                   | Codice handler backend che costruisce il JSON dati |
| `emittente_fiscale_id`     | bigint FK `anagrafiche.emittenti_fiscali.id`   | Emittente fiscale del template                     |
| `is_default`               | boolean                                        | Default per tipo/emittente                         |
| `attivo`                   | boolean                                        | Abilitazione                                       |
| `meta`                     | jsonb                                          | Config extra                                       |
| `storicizza`               | boolean                                        | Standard audit/storico                             |
| `tx_id`                    | uuid                                           | Standard transazione                               |
| `user_insert`              | text                                           | Audit                                              |
| `data_insert`              | timestamptz                                    | Audit                                              |
| `user_update`              | text                                           | Audit                                              |
| `data_update`              | timestamptz                                    | Audit                                              |

Vincoli/indici:

- unique su `(tipo_documento_output_id, codice)`;
- indice su `sorgente_tipo_id`;
- indice su `(tipo_documento_output_id, emittente_fiscale_id, is_default)`;
- un solo default attivo per tipo documento, sorgente ed emittente;
- `emittente_fiscale_id` obbligatorio;
- lock columns su `codice`.

Decisione:

- `emittente_fiscale_id` punta a `anagrafiche.emittenti_fiscali.id` ed e'
  obbligatorio. Gli admin selezionano esplicitamente l'emittente, gli operatori
  la ereditano dal proprio contesto.
- per ogni combinazione `tipo_documento_output_id`, `sorgente_tipo_id` ed
  `emittente_fiscale_id` puo' esistere un solo template default attivo. La UI
  puo' comunque proporre template alternativi selezionabili manualmente.
- `context_builder_code` e' configurato in tabella, ma il backend lo risolve
  solo contro una registry/whitelist di handler ammessi. Non si eseguono nomi o
  funzioni arbitrarie lette dal DB.

---

### 5.3 `documenti.template_documenti_versioni`

Versione pubblicabile del template.

Qui sta il contenuto tecnico: HTML/CSS, markdown parziali, configurazione
render, stato bozza/pubblicato.

Colonne previste:

| Colonna                 | Tipo         | Note                                          |
| ----------------------- | ------------ | --------------------------------------------- |
| `id`                    | bigserial PK | Identificativo                                |
| `template_documento_id` | bigint FK    | Testata template                              |
| `versione`              | integer      | Progressivo versione                          |
| `stato`                 | varchar(30)  | `BOZZA`, `PUBBLICATA`, `OBSOLETA`             |
| `titolo`                | text         | Titolo versione                               |
| `formato_template`      | varchar(30)  | `HTML`, `HTML_MARKDOWN_BLOCKS`                |
| `html_template`         | text         | Corpo HTML principale                         |
| `css_template`          | text         | CSS dedicato                                  |
| `markdown_template`     | text NULL    | Testo markdown opzionale per modelli semplici |
| `render_engine`         | varchar(80)  | Es. `WEASYPRINT`, `PLAYWRIGHT_PDF`            |
| `page_format`           | varchar(30)  | Es. `A4`                                      |
| `page_orientation`      | varchar(20)  | `PORTRAIT`, `LANDSCAPE`                       |
| `margin_top_mm`         | numeric(8,2) | Margini PDF                                   |
| `margin_right_mm`       | numeric(8,2) | Margini PDF                                   |
| `margin_bottom_mm`      | numeric(8,2) | Margini PDF                                   |
| `margin_left_mm`        | numeric(8,2) | Margini PDF                                   |
| `valido_dal`            | date         | Inizio validita' versione                     |
| `valido_al`             | date NULL    | Fine validita'                                |
| `context_schema`        | jsonb        | Schema/contratto variabili attese             |
| `meta`                  | jsonb        | Config extra render                           |
| `attivo`                | boolean      | Abilitazione                                  |
| `storicizza`            | boolean      | Standard audit/storico                        |
| `tx_id`                 | uuid         | Standard transazione                          |
| `user_insert`           | text         | Audit                                         |
| `data_insert`           | timestamptz  | Audit                                         |
| `user_update`           | text         | Audit                                         |
| `data_update`           | timestamptz  | Audit                                         |

Vincoli/indici:

- unique su `(template_documento_id, versione)`;
- vincolo stato ammesso;
- evitare due versioni `PUBBLICATA` sovrapposte nello stesso template;
- versioni `PUBBLICATA` immutabili: non si modificano HTML/CSS, configurazione,
  validita' o engine; per cambiare template si crea una nuova versione
  `BOZZA`, poi la si pubblica;
- lock/delete block su versioni pubblicate se gia' usate da documenti generati.

Decisioni:

- HTML/CSS direttamente in tabella per la v1: semplifica editing da UI,
  versionamento e storicizzazione. Gli asset pesanti restano nello storage e
  sono referenziati dalle tabelle asset/allegati.

---

### 5.4 `documenti.template_asset`

Archivio asset riusabili nei template.

Esempi:

- logo aziendale;
- immagine firma;
- carta intestata in PDF;
- timbro;
- immagine footer;
- condizioni generali PDF.

Colonne previste:

| Colonna                | Tipo         | Note                                               |
| ---------------------- | ------------ | -------------------------------------------------- |
| `id`                   | bigserial PK | Identificativo                                     |
| `codice`               | varchar(120) | Codice asset                                       |
| `descrizione`          | text         | Nome leggibile                                     |
| `asset_tipo`           | varchar(40)  | `LOGO`, `FIRMA`, `IMMAGINE`, `PDF`, `CSS`, `ALTRO` |
| `mime_type`            | varchar(120) | Es. `application/pdf`, `image/png`                 |
| `file_name`            | text         | Nome file originale                                |
| `file_size_bytes`      | bigint       | Dimensione                                         |
| `storage_key`          | text         | Chiave storage filesystem/S3/minio                 |
| `sha256`               | varchar(64)  | Hash contenuto                                     |
| `emittente_fiscale_id` | bigint FK `anagrafiche.emittenti_fiscali.id` | Emittente fiscale dell'asset                 |
| `attivo`               | boolean      | Abilitazione                                       |
| `meta`                 | jsonb        | Info extra, es. dimensioni immagine                |
| `storicizza`           | boolean      | Standard audit/storico                             |
| `tx_id`                | uuid         | Standard transazione                               |
| `user_insert`          | text         | Audit                                              |
| `data_insert`          | timestamptz  | Audit                                              |
| `user_update`          | text         | Audit                                              |
| `data_update`          | timestamptz  | Audit                                              |

Vincoli/indici:

- unique su `(codice, emittente_fiscale_id)`;
- `emittente_fiscale_id` obbligatorio;
- indice su `asset_tipo`;
- indice su `sha256`;
- delete block se asset usato da versioni pubblicate o documenti generati.

---

### 5.5 `documenti.template_allegati`

Associazione tra versione template e asset/allegati.

Serve per dire: "quando genero questo contratto, aggiungi anche condizioni
generali, privacy, allegato tecnico".

Gli allegati PDF configurati vengono fusi nel PDF finale unico secondo ruolo e
ordinamento. La ristampa ordinaria usa quindi il solo `PDF_FINALE`.

Colonne previste:

| Colonna                | Tipo                                       | Note                                                     |
| ---------------------- | ------------------------------------------ | -------------------------------------------------------- |
| `id`                   | bigserial PK                               | Identificativo                                           |
| `template_versione_id` | bigint FK `template_documenti_versioni.id` | Versione template                                        |
| `asset_id`             | bigint FK `template_asset.id`              | Asset allegato                                           |
| `ruolo`                | varchar(40)                                | `HEADER`, `FOOTER`, `APPEND`, `PREPEND`, `INLINE`, `CSS` |
| `ordinamento`          | integer                                    | Ordine applicazione                                      |
| `obbligatorio`         | boolean                                    | Se sempre incluso                                        |
| `condizione_json`      | jsonb                                      | Regola futura per includerlo solo in certi casi          |
| `attivo`               | boolean                                    | Abilitazione                                             |
| `meta`                 | jsonb                                      | Config extra                                             |
| `storicizza`           | boolean                                    | Standard audit/storico                                   |
| `tx_id`                | uuid                                       | Standard transazione                                     |
| `user_insert`          | text                                       | Audit                                                    |
| `data_insert`          | timestamptz                                | Audit                                                    |
| `user_update`          | text                                       | Audit                                                    |
| `data_update`          | timestamptz                                | Audit                                                    |

Vincoli/indici:

- unique su `(template_versione_id, ruolo, ordinamento)`;
- indice su `asset_id`;
- controllo `ruolo` ammesso.

Decisione:

- gli allegati PDF del template sono fusi nel PDF finale, non consegnati come
  file separati nel flusso ordinario.

---

### 5.6 `documenti.documenti_generati`

Testata del documento prodotto.

E' il record funzionale: dice che e' stato generato un documento da una sorgente
e con quale template.

Colonne previste:

| Colonna                    | Tipo                           | Note                                              |
| -------------------------- | ------------------------------ | ------------------------------------------------- |
| `id`                       | bigserial PK                   | Identificativo                                    |
| `uid`                      | uuid                           | Identificativo pubblico/stabile                   |
| `tipo_documento_output_id` | bigint FK                      | Tipo documento                                    |
| `template_documento_id`    | bigint FK                      | Template logico usato                             |
| `template_versione_id`     | bigint FK                      | Versione precisa usata                            |
| `sorgente_tipo_id`         | bigint FK `config.sorgenti.id` | Tipo sorgente, es. `PREVENTIVO`                   |
| `sorgente_uid`             | text                           | Identificativo sorgente, coerente con il pattern `sorgente_uid` |
| `sorgente_riga`            | bigint NULL                    | Riga specifica se il documento nasce da dettaglio |
| `stato`                    | varchar(30)                    | `GENERATO`, `CORRENTE`, `SOSTITUITO`, `ARCHIVIATO`, `ANNULLATO`, `ERRORE` |
| `titolo`                   | text                           | Titolo documento                                  |
| `nome_file`                | text                           | Nome file suggerito                               |
| `context_json`             | jsonb                          | Snapshot completo dei dati usati per render       |
| `context_hash`             | varchar(64)                    | Hash del context                                  |
| `template_hash`            | varchar(64)                    | Hash del template/versione al momento del render  |
| `pdf_hash`                 | varchar(64)                    | Hash PDF finale                                   |
| `generato_da_user_id`      | integer FK `auth_user.id` NULL | Utente generazione                                |
| `generato_at`              | timestamptz                    | Timestamp generazione                             |
| `emittente_fiscale_id`     | bigint FK `anagrafiche.emittenti_fiscali.id` | Emittente/carta intestata usata                   |
| `meta`                     | jsonb                          | Info extra render                                 |
| `storicizza`               | boolean                        | Standard audit/storico                            |
| `tx_id`                    | uuid                           | Standard transazione                              |
| `user_insert`              | text                           | Audit                                             |
| `data_insert`              | timestamptz                    | Audit                                             |
| `user_update`              | text                           | Audit                                             |
| `data_update`              | timestamptz                    | Audit                                             |

Vincoli/indici:

- unique su `uid`;
- indice su `(sorgente_tipo_id, sorgente_uid)`;
- indice su `(sorgente_tipo_id, sorgente_uid, sorgente_riga)`;
- indice su `template_versione_id`;
- indice su `stato`;
- delete block per documenti archiviati.

Decisione:

- uniformarsi al pattern esistente `config.sorgenti` + `sorgente_uid`, gia'
  usato da fatturazione, attivita' fatturabili, commesse sorgenti e canali
  documento. In `documenti.documenti_generati` `sorgente_uid` resta `text` per
  supportare sorgenti con chiave UUID o numerica senza introdurre colonne
  doppie; il significato e la tabella target arrivano da `config.sorgenti`
  (`target_table`, `key_selector`).
- ogni generazione crea sempre un nuovo record in
  `documenti.documenti_generati`. Non si sovrascrive il documento precedente:
  la storia delle generazioni resta consultabile. Per la v1 non si aggiorna lo
  stato dei record precedenti: il documento piu' recente si ricava da
  `generato_at`/ordinamento.
- `context_json` viene salvato completo nel record generato. La ristampa usa lo
  snapshot storico e non dipende da modifiche successive a cliente, indirizzi,
  righe o descrizioni della sorgente.

---

### 5.7 `documenti.documenti_generati_file`

File fisici collegati al documento generato.

Serve per conservare il PDF finale. HTML intermedio o file diagnostici non sono
prodotti nel flusso ordinario; possono essere eccezioni tecniche abilitate per
debug/test.

Un documento generato puo' avere piu' file collegati: PDF principale, eventuale
PDF firmato, allegati materializzati, anteprima o varianti future. Il record
funzionale resta uno solo in `documenti_generati`.

Colonne previste:

| Colonna                 | Tipo         | Note                                                      |
| ----------------------- | ------------ | --------------------------------------------------------- |
| `id`                    | bigserial PK | Identificativo                                            |
| `documento_generato_id` | bigint FK    | Documento                                                 |
| `file_tipo`             | varchar(40)  | `PDF_FINALE`, `PDF_ALLEGATO`, `PDF_FIRMATO`, `HTML_RENDER` eccezionale |
| `mime_type`             | varchar(120) | MIME                                                      |
| `file_name`             | text         | Nome file                                                 |
| `file_size_bytes`       | bigint       | Dimensione                                                |
| `storage_key`           | text         | Chiave storage                                            |
| `sha256`                | varchar(64)  | Hash contenuto                                            |
| `ordinamento`           | integer      | Per file multipli                                         |
| `meta`                  | jsonb        | Extra                                                     |
| `storicizza`            | boolean      | Standard audit/storico                                    |
| `tx_id`                 | uuid         | Standard transazione                                      |
| `user_insert`           | text         | Audit                                                     |
| `data_insert`           | timestamptz  | Audit                                                     |
| `user_update`           | text         | Audit                                                     |
| `data_update`           | timestamptz  | Audit                                                     |

Vincoli/indici:

- unique su `(documento_generato_id, file_tipo, ordinamento)`;
- un solo file `PDF_FINALE` principale per documento generato, da gestire con
  vincolo parziale o regola applicativa;
- indice su `sha256`;
- indice su `storage_key`.

---

### 5.8 `documenti.documenti_generati_eventi`

Log funzionale del ciclo di vita documento.

Esempi evento:

- generato;
- scaricato;
- inviato via email;
- archiviato;
- annullato;
- errore render.

Colonne previste:

| Colonna                 | Tipo                           | Note                   |
| ----------------------- | ------------------------------ | ---------------------- |
| `id`                    | bigserial PK                   | Identificativo         |
| `documento_generato_id` | bigint FK                      | Documento              |
| `evento_tipo`           | varchar(60)                    | Tipo evento            |
| `evento_at`             | timestamptz                    | Timestamp evento       |
| `user_id`               | integer FK `auth_user.id` NULL | Utente                 |
| `esito`                 | varchar(30)                    | `OK`, `KO`, `WARN`     |
| `messaggio`             | text NULL                      | Messaggio breve        |
| `detail`                | jsonb                          | Dettaglio tecnico      |
| `storicizza`            | boolean                        | Standard audit/storico |
| `tx_id`                 | uuid                           | Standard transazione   |
| `user_insert`           | text                           | Audit                  |
| `data_insert`           | timestamptz                    | Audit                  |
| `user_update`           | text                           | Audit                  |
| `data_update`           | timestamptz                    | Audit                  |

Vincoli/indici:

- indice su `(documento_generato_id, evento_at DESC)`;
- indice su `evento_tipo`;
- tabella append-only: valutare guard delete/update.

---

## 6. Flusso di generazione previsto

### 6.1 Generazione preventivo

1. L'utente apre un preventivo.
2. Clicca "Genera PDF".
3. Il backend seleziona il template default per `PREVENTIVO` ed emittente.
   Per gli operatori l'emittente arriva dal contesto utente; per gli admin va
   scelta esplicitamente.
4. Il backend costruisce il context JSON risolvendo `config.sorgenti`
   `PREVENTIVO` + `sorgente_uid` e leggendo `vendite.preventivi`,
   `preventivi_righe`, `preventivi_indirizzi`, cliente, articoli, totali.
5. Il renderer produce HTML e poi PDF.
6. Il sistema accoda/allega eventuali PDF standard.
7. Il PDF finale viene salvato in storage.
8. Viene creato `documenti.documenti_generati`.
9. Viene creato `documenti.documenti_generati_file` per il PDF.
10. Viene scritto evento `GENERATO`.

### 6.2 Generazione contratto

1. Il backend legge contratto, cliente, indirizzi, righe/servizi,
   condizioni economiche, dati societari.
2. Il template contratto inserisce dati nei blocchi variabili.
3. Eventuali allegati PDF contrattuali vengono accodati.
4. Il PDF finale viene archiviato.

---

## 7. Backend previsto

Componenti applicativi futuri:

- `apps/documenti/db/documenti_repository.py`
- `apps/documenti/services/template_service.py`
- `apps/documenti/services/context_builders/`
- `apps/documenti/services/render_service.py`
- `apps/documenti/services/document_generation_service.py`
- API:
  - lista template;
  - dettaglio template/versione;
  - upload asset;
  - genera documento da sorgente;
  - scarica PDF generato;
  - lista documenti generati per sorgente.

Context builder iniziali:

- `PreventivoDocumentContextBuilder`
- `ContrattoDocumentContextBuilder`
- `OrdineDocumentContextBuilder`

---

## 8. Frontend previsto

Per la prima fase:

- pulsante "Genera documento" nelle view sorgente;
- drawer/dialog scelta template se piu' template disponibili;
- tab/lista documenti generati collegati alla sorgente;
- download PDF;
- gestione asset/template inizialmente admin-only.

Editor visuale template: **fuori scope v1**.

---

## 9. Fuori scope v1

1. Editor visuale tipo Word(mai).
2. Firma digitale.
3. Firma grafometrica.
4. Invio PEC.
5. Conservazione sostitutiva.
6. Workflow approvazione template.
7. Condizioni complesse sugli allegati.
8. Rendering real-time collaborativo.

---

## 10. Decisioni aperte

1. ~~Nome schema definitivo: `documenti` oppure estensione in schema esistente?~~
   **Decisione 2026-04-29**: creare schema dedicato `documenti`, perche'
   la generazione PDF e' trasversale a vendite, acquisti, pratiche, portale e
   altri domini futuri.
2. ~~Storage file: filesystem locale, MinIO/S3, tabella bytea?~~
   **Decisione 2026-04-29**: usare uno storage astratto. Target architetturale
   S3/MinIO, con fallback filesystem per sviluppo/installazioni semplici.
   Il backend deve leggere configurazione parametrica per endpoint/base URL/DNS,
   bucket/container, path prefix e credenziali, cosi' lo storage puo' essere
   eseguito esterno e non necessariamente locale.
3. ~~Engine PDF: WeasyPrint, Playwright/Chromium, altro?~~
   **Decisione 2026-04-29**: usare WeasyPrint come engine iniziale/default.
   L'engine non deve essere hardcoded: resta configurabile in tabella tramite
   `template_documenti_versioni.render_engine`, cosi' una versione template
   futura potra' usare un renderer diverso (es. Playwright/Chromium) senza
   cambiare il modello dati.
4. ~~Sintassi/formato template iniziale?~~
   **Decisione 2026-04-29**: usare HTML/CSS come formato principale del
   template, con variabili e cicli lato backend in stile Jinja (`{{ ... }}`,
   `{% for ... %}`). Markdown ammesso solo per blocchi testuali controllati,
   convertiti in HTML prima del render. Il markdown non e' il formato
   principale perche' tabelle, header/footer e impaginazione A4 richiedono
   controllo HTML/CSS.
5. ~~Template/asset globali o per emittente?~~
   **Decisione 2026-04-29**: template e asset sono per emittente fiscale,
   senza fallback globale. Un operatore genera nel contesto della propria
   emittente; un admin deve selezionare esplicitamente l'emittente. Resta da
   verificare solo la FK tecnica corretta verso il modello DB attuale.
6. ~~ID sorgente come `text` o colonne tipizzate?~~
   **Decisione 2026-04-29**: uniformarsi allo standard esistente
   `config.sorgenti` + `sorgente_uid`. Le tabelle documenti usano
   `sorgente_tipo_id` FK a `config.sorgenti` e `sorgente_uid text`; eventuale
   dettaglio riga usa `sorgente_riga`. Il backend/context builder valida
   l'esistenza della sorgente usando `target_table` e `key_selector`.
7. ~~Primo documento pilota: preventivo o contratto?~~
   **Decisione 2026-04-29**: il primo documento pilota e' `PREVENTIVO`.
   Motivo: ha dati completi ma gestibili (testata, cliente, indirizzi, righe,
   totali), testa bene il context JSON e riduce il rischio rispetto a un
   contratto con clausole legali.
8. ~~Policy modifica template pubblicati.~~
   **Decisione 2026-04-29**: una versione `PUBBLICATA` e' immutabile. Non si
   modificano contenuto, CSS, engine o parametri di validita' della versione
   pubblicata; ogni cambio crea una nuova versione `BOZZA`, che potra' poi
   essere pubblicata. Le ristampe continuano a usare la versione storica legata
   al documento generato.
9. ~~HTML/CSS in tabella o file asset?~~
   **Decisione 2026-04-29**: per la v1 `html_template` e `css_template`
   restano in `documenti.template_documenti_versioni`. Gli asset binari o
   pesanti, come logo, carta intestata e PDF allegati, stanno invece nello
   storage parametrico e sono referenziati dalle tabelle asset/allegati.
10. ~~FK tecnica emittente fiscale.~~
    **Decisione 2026-04-29**: `emittente_fiscale_id` punta a
    `anagrafiche.emittenti_fiscali.id` ed e' obbligatorio per template, asset e
    documenti generati.
11. ~~Tipi documento output dedicati o riuso cataloghi esistenti?~~
    **Decisione 2026-04-29**: usare tabella dedicata
    `documenti.tipi_documento_output`, per classificare gli output producibili
    dal motore documentale senza accoppiare questa logica ai tipi documento
    gestionali/fiscali esistenti.
12. ~~Uno o piu' file per documento generato?~~
    **Decisione 2026-04-29**: mantenere
    `documenti.documenti_generati_file` come tabella separata multi-file. Ogni
    documento generato ha un record funzionale unico e puo' collegare PDF
    principale, PDF firmato, allegati materializzati, anteprime o file
    diagnostici.
13. ~~Rigenerazione documento: update o nuovo record?~~
    **Decisione 2026-04-29**: ogni generazione crea sempre un nuovo record in
    `documenti.documenti_generati`. Il record precedente non viene
    sovrascritto; resta disponibile per audit e ristampa storica.
14. ~~Gestione documento corrente/sostituito.~~
    **Decisione 2026-04-29**: per la v1 non si marca automaticamente il
    precedente come `SOSTITUITO`. Il documento piu' recente per la stessa
    sorgente si determina da `generato_at` e ordinamento.
15. ~~Salvare anche HTML renderizzato?~~
    **Decisione 2026-04-29**: nel flusso ordinario si salva solo il PDF finale.
    `HTML_RENDER` resta un'eccezione tecnica per debug/test, da abilitare solo
    quando serve.
16. ~~Allegati PDF fusi o separati?~~
    **Decisione 2026-04-29**: gli allegati PDF configurati sul template vengono
    fusi nel `PDF_FINALE` secondo ruolo e ordinamento. La ristampa ordinaria
    usa quindi un solo file PDF.
17. ~~Template default unico o scelta manuale?~~
    **Decisione 2026-04-29**: entrambe. Deve esserci un solo template default
    attivo per `tipo_documento_output_id`, `sorgente_tipo_id` ed
    `emittente_fiscale_id`, ma la UI puo' permettere la scelta manuale di un
    template alternativo quando disponibile.
18. ~~Context builder configurabile liberamente o registry backend?~~
    **Decisione 2026-04-29**: `context_builder_code` resta in tabella, ma il
    backend puo' eseguire solo handler registrati in una whitelist applicativa.
    Il DB non abilita esecuzione dinamica libera.
19. ~~Salvataggio context JSON completo?~~
    **Decisione 2026-04-29**: salvare sempre il `context_json` completo usato
    per generare il PDF. La ristampa storica usa questo snapshot e non rilegge i
    dati correnti della sorgente.

---

## 11. Roadmap proposta

### Fase 1 — Foundation DB

- [ ] creare schema `documenti`;
- [ ] creare lookup `tipi_documento_output`;
- [ ] creare template, versioni, asset, allegati;
- [ ] creare documenti generati e file;
- [ ] definire parametri storage documenti (provider, endpoint/base URL,
      bucket/container, prefix, credenziali/secret ref);
- [ ] trigger standard audit/storico/lock/delete block dove necessario.

### Fase 2 — Backend render minimo

- [ ] repository/service documenti;
- [ ] context builder preventivo;
- [ ] renderer HTML -> PDF;
- [ ] storage PDF;
- [ ] endpoint genera/scarica documento.

### Fase 3 — UI minima

- [ ] pulsante genera PDF su preventivo;
- [ ] lista documenti generati;
- [ ] download PDF;
- [ ] pagina admin minima per template e asset.

### Fase 4 — Estensione contratti/ordini

- [ ] context builder contratto;
- [ ] context builder ordine;
- [ ] allegati standard condizionati;
- [ ] gestione template per emittente.

---

*Sviluppo Documenti Parametrici — ZeroERP (WIP iniziale, aprile 2026)*
