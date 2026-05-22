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
2. `documenti.tipi_asset_documento`
3. `documenti.ruoli_template_asset`
4. `documenti.tipi_file_documento`
5. `documenti.render_engine_documento`
6. `documenti.template_documenti`
7. `documenti.template_documenti_versioni`
8. `documenti.template_asset`
9. `documenti.template_allegati`
10. `documenti.documenti_generati`
11. `documenti.documenti_generati_file`
12. `documenti.documenti_generati_eventi`

---

## 5. Tabelle previste

### 5.1 `documenti.tipi_documento_output`

Lookup dei tipi di documento generabili.

E' una tabella dedicata del modulo `documenti`, separata dai cataloghi
documentali gestionali/fiscali esistenti. Qui si classificano gli output
producibili dal motore documentale. E' configurabile da UI come lookup
standard; i codici di sistema restano protetti da lock su `codice` e
`codice_interno`. `codice_interno` segue lo standard Zero ERP: codice tecnico
stabile, lockato e usato dai binding applicativi.

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

### 5.2 `documenti.tipi_asset_documento`

Lookup dei tipi asset documentali.

E' una tabella configurabile standard Zero ERP con
`id/codice/codice_interno/descrizione`, da aggiungere alla whitelist lookup
generica. `codice_interno` resta lockato e usato dai binding applicativi.

Esempi:

- `LOGO`
- `FIRMA`
- `IMMAGINE`
- `PDF`
- `CSS`
- `ALTRO`

Colonne previste:

| Colonna              | Tipo                                       | Note                                      |
| -------------------- | ------------------------------------------ | ----------------------------------------- |
| `id`                 | bigserial PK                               | Identificativo                            |
| `codice`             | varchar(80)                                | Codice tecnico breve, unico               |
| `codice_interno`     | varchar(80)                                | Codice stabile interno, lockato           |
| `descrizione`        | text                                       | Descrizione leggibile                     |
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
- unique su `codice_interno`;
- indice su `attivo`;
- lock columns su `codice_interno`; per i record di sistema anche `codice`.

---

### 5.3 `documenti.ruoli_template_asset`

Lookup dei ruoli con cui un asset viene usato in una versione template.

E' tabella configurabile standard Zero ERP con
`id/codice/codice_interno/descrizione`, da aggiungere alla whitelist lookup
generica.

Esempi:

- `HEADER`
- `FOOTER`
- `APPEND`
- `PREPEND`
- `INLINE`
- `CSS`

Colonne previste:

| Colonna              | Tipo         | Note                            |
| -------------------- | ------------ | ------------------------------- |
| `id`                 | bigserial PK | Identificativo                  |
| `codice`             | varchar(80)  | Codice tecnico breve, unico     |
| `codice_interno`     | varchar(80)  | Codice stabile interno, lockato |
| `descrizione`        | text         | Descrizione leggibile           |
| `attivo`             | boolean      | Soft enable                     |
| `meta`               | jsonb        | Estensioni future               |
| `storicizza`         | boolean      | Standard audit/storico          |
| `tx_id`              | uuid         | Standard transazione            |
| `user_insert`        | text         | Audit                           |
| `data_insert`        | timestamptz  | Audit                           |
| `user_update`        | text         | Audit                           |
| `data_update`        | timestamptz  | Audit                           |

Vincoli/indici:

- unique su `codice`;
- unique su `codice_interno`;
- indice su `attivo`;
- lock columns su `codice_interno`; per i record di sistema anche `codice`.

---

### 5.4 `documenti.tipi_file_documento`

Lookup dei tipi file collegabili a un documento generato.

E' tabella configurabile standard Zero ERP con
`id/codice/codice_interno/descrizione`, da aggiungere alla whitelist lookup
generica.

Esempi:

- `PDF_FINALE`
- `PDF_ALLEGATO`
- `PDF_FIRMATO`
- `HTML_RENDER`

Colonne previste:

| Colonna              | Tipo         | Note                            |
| -------------------- | ------------ | ------------------------------- |
| `id`                 | bigserial PK | Identificativo                  |
| `codice`             | varchar(80)  | Codice tecnico breve, unico     |
| `codice_interno`     | varchar(80)  | Codice stabile interno, lockato |
| `descrizione`        | text         | Descrizione leggibile           |
| `attivo`             | boolean      | Soft enable                     |
| `meta`               | jsonb        | Estensioni future               |
| `storicizza`         | boolean      | Standard audit/storico          |
| `tx_id`              | uuid         | Standard transazione            |
| `user_insert`        | text         | Audit                           |
| `data_insert`        | timestamptz  | Audit                           |
| `user_update`        | text         | Audit                           |
| `data_update`        | timestamptz  | Audit                           |

Vincoli/indici:

- unique su `codice`;
- unique su `codice_interno`;
- indice su `attivo`;
- lock columns su `codice_interno`; per i record di sistema anche `codice`.

---

### 5.5 `documenti.render_engine_documento`

Lookup degli engine di render PDF supportati/configurabili.

E' tabella configurabile standard Zero ERP con
`id/codice/codice_interno/descrizione`, da aggiungere alla whitelist lookup
generica. Il backend esegue comunque solo engine registrati in whitelist codice.

Esempi:

- `WEASYPRINT`
- `PLAYWRIGHT_PDF`

Colonne previste:

| Colonna              | Tipo         | Note                            |
| -------------------- | ------------ | ------------------------------- |
| `id`                 | bigserial PK | Identificativo                  |
| `codice`             | varchar(80)  | Codice tecnico breve, unico     |
| `codice_interno`     | varchar(80)  | Codice stabile interno, lockato |
| `descrizione`        | text         | Descrizione leggibile           |
| `attivo`             | boolean      | Soft enable                     |
| `meta`               | jsonb        | Estensioni future               |
| `storicizza`         | boolean      | Standard audit/storico          |
| `tx_id`              | uuid         | Standard transazione            |
| `user_insert`        | text         | Audit                           |
| `data_insert`        | timestamptz  | Audit                           |
| `user_update`        | text         | Audit                           |
| `data_update`        | timestamptz  | Audit                           |

Vincoli/indici:

- unique su `codice`;
- unique su `codice_interno`;
- indice su `attivo`;
- lock columns su `codice_interno`; per i record di sistema anche `codice`.

---

### 5.6 `documenti.template_documenti`

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
| `file_name_pattern`        | text NULL                                      | Pattern nome file, es. `PREVENTIVO-{{ codice }}-{{ yyyyMMdd }}.pdf` |
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
  funzioni arbitrarie lette dal DB. E' un binding tecnico a codice applicativo,
  non lookup configurabile.
- il nome file e' generato da `file_name_pattern` configurabile sul template.
  Per il preventivo v1 il default applicativo e'
  `PREVENTIVO-{{ codice }}-{{ yyyyMMdd }}.pdf`. Il pattern usa la stessa
  sintassi Jinja-style del template, ma con contesto limitato e sanificazione
  obbligatoria del risultato per produrre un filename valido.

---

### 5.7 `documenti.template_documenti_versioni`

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
| `render_engine_id`      | bigint FK `documenti.render_engine_documento.id` | Engine render PDF                 |
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
- per la v1 deve esistere al massimo una versione `PUBBLICATA` attiva alla data
  corrente per template;
- versioni `PUBBLICATA` immutabili: non si modificano HTML/CSS, configurazione,
  validita' o engine; per cambiare template si crea una nuova versione
  `BOZZA`, poi la si pubblica;
- versioni `BOZZA` cancellabili fisicamente su conferma utente;
- lock/delete block su versioni pubblicate se gia' usate da documenti generati.

Decisioni:

- HTML/CSS direttamente in tabella per la v1: semplifica editing da UI,
  versionamento e storicizzazione. Gli asset pesanti restano nello storage e
  sono referenziati dalle tabelle asset/allegati.
- in UI una versione `PUBBLICATA` e' completamente readonly. L'unica azione di
  modifica ammessa e' creare una nuova versione `BOZZA` derivata dalla
  pubblicata.
- l'azione "crea nuova versione da questa" clona contenuti, configurazione e
  allegati della versione origine nella nuova `BOZZA`, poi l'utente modifica
  solo cio' che serve.
- il modello mantiene `valido_dal`/`valido_al` per storico e cambi pianificati,
  ma in v1 la pubblicazione deve garantire una sola versione pubblicata attiva
  alla data corrente per template.
- in pubblicazione, se `valido_dal` non e' valorizzato, viene impostato alla
  data corrente. Una pubblicazione futura richiede `valido_dal` esplicito.
- quando una nuova versione `PUBBLICATA` entra in validita' e si sovrappone a
  una pubblicata precedente dello stesso template, il service chiude/marca
  `OBSOLETA` la precedente. Se la nuova versione e' futura, la precedente resta
  valida fino alla propria scadenza.
- `context_schema` descrive le variabili attese dal template e viene validato
  prima della pubblicazione, per evitare versioni pubblicate con riferimenti
  variabile errati o non supportati dal context builder.
- la validazione pre-pubblicazione controlla sia la correttezza formale del
  `context_schema`, sia che le variabili referenziate in HTML, CSS templated e
  `file_name_pattern` siano presenti/ammissibili nello schema.
- il renderer espone solo filtri Jinja custom in whitelist. Filtri v1 previsti:
  `date`, `money`, `number`, `percent`, `upper`, `lower`, `default`. Eventuali
  nuovi filtri vanno aggiunti a codice e documentati, non definiti liberamente
  da tabella.
- gli stati tecnici di workflow, es. `BOZZA`, `PUBBLICATA`, `OBSOLETA`,
  `GENERATO`, `ARCHIVIATO`, `ANNULLATO`, non sono lookup configurabili: restano
  valori controllati da guard DB/applicativa.
- anche `documenti_generati_eventi.evento_tipo` resta tecnico e non
  configurabile: rappresenta eventi applicativi controllati dal service.
- `formato_template` resta tecnico e non configurabile come lookup: influenza
  parser/rendering ed e' gestito dal codice.
- `page_format` e `page_orientation` restano opzioni tecniche controllate da
  guard DB/applicativa, non lookup configurabili.

---

### 5.8 `documenti.template_asset`

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
| `codice_interno`       | varchar(120) | Codice tecnico stabile asset                       |
| `descrizione`          | text         | Nome leggibile                                     |
| `asset_tipo_id`        | bigint FK `documenti.tipi_asset_documento.id` | Tipo asset documentale                    |
| `mime_type`            | varchar(120) | Es. `application/pdf`, `image/png`                 |
| `file_name`            | text         | Nome file originale                                |
| `file_size_bytes`      | bigint       | Dimensione                                         |
| `storage_key`          | text         | Chiave storage filesystem/S3/minio                 |
| `sha256`               | varchar(64)  | Hash contenuto, obbligatorio per deduplica         |
| `emittente_fiscale_id` | bigint FK `anagrafiche.emittenti_fiscali.id` | Emittente fiscale dell'asset                 |
| `valido_dal`           | date         | Inizio validita' uso asset                         |
| `valido_al`            | date NULL    | Fine validita' uso asset                           |
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
- unique su `(codice_interno, emittente_fiscale_id)`;
- `emittente_fiscale_id` obbligatorio;
- indice su `asset_tipo_id`;
- unique/guard deduplica su `(emittente_fiscale_id, sha256)`;
- no delete fisico: gli asset si disattivano o chiudono con `valido_al`;
- lock modifica file (`storage_key`, `sha256`, `file_size_bytes`, `mime_type`)
  se asset usato da versioni pubblicate o documenti generati.

Decisione:

- `sha256` obbligatorio e deduplica immediata per emittente: lo stesso file non
  viene caricato due volte per la stessa emittente fiscale. Due emittenti
  diverse possono avere asset distinti anche con lo stesso hash, mantenendo
  ownership e permessi separati.
- nessun delete fisico degli asset. Per non usarli piu' si imposta `attivo =
  false` o si valorizza `valido_al`. Se un file cambia, si carica un nuovo asset
  e si crea una nuova versione template. La regola vale anche per asset non
  ancora usati da versioni.
- `asset_tipo_id` punta a `documenti.tipi_asset_documento`; niente varchar
  hardcoded per configurazioni.
- `codice_interno` identifica in modo stabile l'asset come entita'
  configurabile; `sha256` identifica il contenuto binario e non sostituisce il
  codice tecnico.
- upload file e modifica metadati sono operazioni separate. L'upload crea
  l'asset con file/hash/storage; gli update successivi possono modificare solo
  campi descrittivi, validita', `attivo` e `meta`. Il file non si sostituisce:
  si carica un nuovo asset.
- upload asset vincolato da MIME whitelist per tipo asset: PDF, immagini
  supportate e CSS. Nessun upload generico libero.
- upload asset soggetto a limite dimensione configurabile. Default v1 proposto:
  25 MB per asset caricato; eventuale limite PDF generato separato e
  parametrico.

---

### 5.9 `documenti.template_allegati`

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
| `ruolo_id`             | bigint FK `documenti.ruoli_template_asset.id` | Ruolo applicazione asset                              |
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

- unique su `(template_versione_id, ruolo_id, ordinamento)`;
- indice su `asset_id`;
- indice su `ruolo_id`.

Decisione:

- gli allegati PDF del template sono fusi nel PDF finale, non consegnati come
  file separati nel flusso ordinario.
- `ruolo_id` punta a `documenti.ruoli_template_asset`; niente varchar hardcoded
  per configurazioni.
- gli allegati fanno parte della versione template. Non si gestisce validita'
  temporale sull'associazione `template_allegati`: se cambiano allegati,
  ordinamento, obbligatorieta' o condizioni, si crea una nuova versione
  `BOZZA` del template e poi la si pubblica.

---

### 5.10 `documenti.documenti_generati`

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
| `progressivo_sorgente`     | integer                        | Progressivo generazione per stessa sorgente       |
| `stato`                    | varchar(30)                    | `GENERATO`, `CORRENTE`, `SOSTITUITO`, `ARCHIVIATO`, `ANNULLATO` |
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
- unique su `(sorgente_tipo_id, sorgente_uid, sorgente_riga, progressivo_sorgente)`;
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
  `progressivo_sorgente` e `generato_at`.
- `progressivo_sorgente` viene calcolato dal service di generazione dentro una
  transazione, con gestione della concorrenza. Il DB resta guard finale tramite
  unique per sorgente/progressivo.
- `context_json` viene salvato completo nel record generato. La ristampa usa lo
  snapshot storico e non dipende da modifiche successive a cliente, indirizzi,
  righe o descrizioni della sorgente.
- il context builder non deve mai includere segreti tecnici, token, password o
  credenziali nel `context_json`. Per la v1 lo snapshot funzionale viene
  salvato completo; una classificazione/mascheratura campi sensibili potra'
  essere aggiunta in seguito se emergeranno esigenze specifiche.
- `context_hash`, `template_hash` e `pdf_hash` sono valorizzati gia' dalla v1
  per audit, confronto tra generazioni e verifica dell'output prodotto.
- se render o salvataggio falliscono, non viene creato un record in
  `documenti.documenti_generati`: questa tabella rappresenta solo documenti
  effettivamente prodotti. L'errore resta nel normale log tecnico/API.

---

### 5.11 `documenti.documenti_generati_file`

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
| `file_tipo_id`          | bigint FK `documenti.tipi_file_documento.id` | Tipo file documento                                |
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

- unique su `(documento_generato_id, file_tipo_id, ordinamento)`;
- un solo file `PDF_FINALE` principale per documento generato, da gestire con
  vincolo parziale o regola applicativa;
- indice su `file_tipo_id`;
- indice su `sha256`;
- indice su `storage_key`.

Decisione:

- nessuna deduplica fisica/logica sui PDF generati: anche PDF identici possono
  rappresentare generazioni storiche distinte. `sha256` resta per audit e
  confronto.
- `file_tipo_id` punta a `documenti.tipi_file_documento`; niente varchar
  hardcoded per configurazioni.

---

### 5.12 `documenti.documenti_generati_eventi`

Log funzionale del ciclo di vita documento.

La tabella registra solo eventi legati a documenti persistenti. Le anteprime
PDF in streaming non creano eventi in questa tabella nella v1.

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

Decisione:

- eventi solo per documenti persistenti; anteprime escluse dalla timeline
  documentale.
- ogni download del PDF persistente registra evento `SCARICATO`.

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
5. Il renderer produce HTML e poi PDF in memoria/file temporaneo.
6. Il sistema fonde eventuali PDF standard nel PDF finale.
7. Il service apre transazione DB, calcola `progressivo_sorgente`, crea
   `documenti.documenti_generati` e riserva `storage_key`.
8. Il PDF finale viene salvato in storage.
9. Viene creato `documenti.documenti_generati_file` per il PDF.
10. Viene scritto evento `GENERATO`.
11. Commit transazione.

Nota consistenza DB/storage: DB e storage non sono atomici insieme. Se upload
storage fallisce, la transazione DB viene annullata. Se il commit DB fallisce
dopo upload riuscito, il service prova cleanup best-effort del file salvato e
registra l'errore tecnico.

### 6.2 Generazione contratto

1. Il backend legge contratto, cliente, indirizzi, righe/servizi,
   condizioni economiche, dati societari.
2. Il template contratto inserisce dati nei blocchi variabili.
3. Eventuali allegati PDF contrattuali vengono accodati.
4. Il PDF finale viene archiviato.

---

## 7. Backend previsto

> Nota stato (2026-05-03): la traccia funzionale qui sotto resta valida,
> ma per lo stato implementativo aggiornato consultare §12. I marcatori
> `[DONE]`/`[TODO]`/`[WIP]` riflettono la situazione al 2026-05-03.

Componenti applicativi:

- [DONE] `apps/documenti/db/documenti_repository.py` (read-only template + versioni)
- [DONE] `apps/documenti/services/template_service.py` (read-only)
- [DONE] `apps/documenti/services/context_builders/` (registry + interface base)
- [DONE] `apps/documenti/services/storage/` (DocumentStorage + Filesystem v1)
- [DONE] `apps/documenti/services/render_service.py` (Tranche I: WeasyPrint + Jinja2)
- [DONE] `apps/documenti/services/document_generation_service.py` (Tranche I: orchestratore)
- API:
  - [DONE] lista template
  - [DONE] dettaglio template/versione
  - [DONE] upload asset (multipart)
  - [DONE] aggiorna metadati asset
  - [DONE] crea/aggiorna testata template
  - [DONE] crea/aggiorna versione `BOZZA`
  - [DONE] clona versione in nuova `BOZZA`
  - [DONE] pubblica versione
  - [DONE] cancella versione `BOZZA`
  - [TODO] genera documento da sorgente
  - [TODO] anteprima PDF temporanea
  - [TODO] scarica PDF generato
  - [TODO] lista documenti generati per sorgente

Le API seguono gli standard di `docs/it/dev/api.md` e dei building block
backend: APIView esplicite, service layer per orchestrazione, repository per
accesso DB, error envelope uniforme, schema OpenAPI vicino all'endpoint,
nessuna esecuzione dinamica libera dal DB. Il naming endpoint segue lo standard
esistente `api.md`: CRUD senza verbo nel path quando e' CRUD reale; comandi di
dominio con verbo esplicito solo per azioni non-CRUD.

Le modifiche anagrafiche semplici restano CRUD dove appropriato, ma il ciclo
vita delle versioni usa comandi espliciti: clonare, pubblicare e cancellare una
bozza non sono semplici PATCH perche' applicano guard, validazioni e regole di
storicizzazione.

Permessi:

- gestione template, versioni e asset: ambito configurazione documentale,
  usando il sistema permessi gia' abilitato, assegnabile anche a responsabili
  non admin;
- generazione documento, lista documenti generati e download PDF: permessi del
  dominio sorgente, es. preventivi per `PREVENTIVO`.

Context builder iniziali:

- [DONE] `PreventivoDocumentContextBuilder` (Tranche J, sblocca render PREVENTIVO)
- [TODO] `ContrattoDocumentContextBuilder`
- [TODO] `OrdineDocumentContextBuilder`

---

## 8. Frontend previsto

Per la prima fase:

- pulsante "Genera documento" nelle view sorgente;
- drawer/dialog scelta template se piu' template disponibili;
- tab/lista documenti generati collegati alla sorgente;
- download PDF;
- gestione asset/template nell'area Configurazione, voce italiana "Modelli
  documenti", non come voce documenti separata in sidebar;
- gestione template con form semplice: campi HTML e CSS in textarea/code editor
  base, senza editor visuale avanzato.

Il frontend deve seguire `docs/it/dev/frontend/frontend-standards.md` e
`docs/it/dev/frontend/catalogo-building-block-frontend.md`: layout lista
standard, drawer laterale per create/edit, `NewButton`, `DrawerFooter`,
`RowActionsMenu`, classi CSS condivise (`app-page`, `app-datatable`,
`form-grid`, `app-drawer-content`) e componenti/composable riusabili. I pezzi
specifici del modulo documenti devono essere pensati come building block
estensibili: lista documenti generati per sorgente, selettore template,
gestione versioni template, upload asset, azione genera/scarica PDF.

Per la v1 l'archivio PDF generati e' esposto solo dalla sorgente, per esempio
dal preventivo. La lista documenti generati deve pero' essere un building block
riusabile, cosi' potra' essere montata in futuro anche in una vista generale
trasversale senza riscrivere logica e UI.

La UI eredita la stessa separazione permessi gia' disponibile: configurazione
template/asset visibile nell'area Configurazione a utenti abilitati, anche
responsabili non admin; azioni di generazione e scarico visibili dentro la
sorgente solo se l'utente ha accesso operativo a quella sorgente.

Comportamento del comando "Genera documento":

- se esiste un solo template applicabile/default, genera direttamente;
- se esistono piu' template applicabili, apre il drawer/dialog di scelta;
- se non esiste alcun template applicabile, mostra errore di configurazione
  chiaro.

Anteprima:

- la generazione ordinaria produce e salva subito il PDF;
- l'anteprima e' disponibile solo come azione esplicita a richiesta;
- l'anteprima produce un PDF temporaneo, per validare l'impaginazione reale;
- l'anteprima viene restituita in streaming response;
- l'anteprima non crea record in `documenti.documenti_generati` e non salva file
  nello storage.

Editor visuale template: **fuori scope v1**. La v1 deve comunque lasciare una
base estensibile per introdurre in seguito anteprima, validazione variabili,
test render e un editor piu' ricco senza riscrivere il flusso.

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

## 10. Decisioni Chiuse

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
   I parametri non segreti usano il sistema esistente `config.parameters`
   letto tramite gli helper standard; le credenziali non si salvano in chiaro in
   DB, ma si referenziano tramite secret ref/env/secret manager.
3. ~~Engine PDF: WeasyPrint, Playwright/Chromium, altro?~~
   **Decisione 2026-04-29**: usare WeasyPrint come engine iniziale/default.
   L'engine non deve essere hardcoded: resta configurabile tramite lookup
   `documenti.render_engine_documento` e FK
   `template_documenti_versioni.render_engine_id`, cosi' una versione template
   futura potra' usare un renderer diverso (es. Playwright/Chromium) senza
   cambiare il modello dati. Il backend esegue solo engine registrati in
   whitelist codice.
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
20. ~~Hash context/template/pdf gia' in v1?~~
    **Decisione 2026-04-29**: valorizzare da subito `context_hash`,
    `template_hash` e `pdf_hash`, per audit e confronto tra generazioni.
21. ~~Editor template v1.~~
    **Decisione 2026-04-29**: per la v1 niente editor visuale avanzato.
    Gestione template con form semplice e campi HTML/CSS in textarea/code
    editor base, costruita pero' con building block frontend/backend
    riutilizzabili e coerenti con la documentazione standard.
22. ~~UI modifica versioni pubblicate.~~
    **Decisione 2026-04-29**: le versioni `PUBBLICATA` sono readonly in UI.
    L'azione ammessa e' "crea nuova versione da questa", che produce una nuova
    `BOZZA` modificabile.
23. ~~Validita' versioni pubblicate.~~
    **Decisione 2026-04-29**: mantenere `valido_dal`/`valido_al`, ma per la v1
    garantire una sola versione `PUBBLICATA` attiva alla data corrente per
    template. Le validita' restano utili per storico e cambi pianificati.
24. ~~Default `valido_dal` in pubblicazione.~~
    **Decisione 2026-04-29**: meccanismo standard. In pubblicazione, se
    `valido_dal` non e' valorizzato, viene impostato alla data corrente. Per
    una pubblicazione futura l'utente deve indicare `valido_dal`.
25. ~~Permessi template/asset vs generazione/download.~~
    **Decisione 2026-04-29**: separare i permessi. Gestione template, versioni
    e asset e' amministrativa/configurazione documentale; generazione, lista e
    download dei documenti generati usano i permessi del dominio sorgente.
26. ~~Generazione immediata o scelta template sempre aperta?~~
    **Decisione 2026-04-29**: se esiste un solo template applicabile/default,
    il comando genera direttamente. Se ci sono alternative, la UI apre la
    scelta template. Se manca un template applicabile, mostra errore di
    configurazione.
27. ~~Anteprima o salvataggio diretto?~~
    **Decisione 2026-04-29**: generazione ordinaria con salvataggio diretto del
    PDF. Anteprima disponibile a richiesta come azione esplicita, senza creare
    record storico ne' file persistente nel flusso ordinario.
28. ~~Formato anteprima.~~
    **Decisione 2026-04-29**: l'anteprima produce un PDF temporaneo, non una
    semplice preview HTML, per verificare l'impaginazione effettiva.
29. ~~Persistenza PDF temporaneo anteprima.~~
    **Decisione 2026-04-29**: solo streaming response. Il PDF temporaneo non
    viene salvato in storage e non richiede cleanup nella v1.
30. ~~Eventi per anteprima.~~
    **Decisione 2026-04-29**: registrare eventi solo per documenti persistenti.
    Le anteprime non entrano in `documenti.documenti_generati_eventi` nella v1.
31. ~~Evento download PDF.~~
    **Decisione 2026-04-29**: registrare evento `SCARICATO` a ogni download del
    PDF persistente.
32. ~~Record documento in caso di errore render.~~
    **Decisione 2026-04-29**: se il PDF non viene prodotto/salvato, non si crea
    `documenti.documenti_generati`. Gli errori di render/generazione restano
    nel log tecnico/API.
33. ~~Pattern nome file PDF.~~
    **Decisione 2026-04-29**: usare `file_name_pattern` configurabile sul
    template, con default applicativo v1
    `PREVENTIVO-{{ codice }}-{{ yyyyMMdd }}.pdf`.
34. ~~Sintassi pattern nome file.~~
    **Decisione 2026-04-29**: usare la stessa sintassi Jinja-style del template,
    con contesto limitato e sanificazione obbligatoria del filename generato.
35. ~~Validazione `context_schema`.~~
    **Decisione 2026-04-29**: `context_schema` e' richiesto come contratto
    leggero delle variabili attese e viene validato prima della pubblicazione
    della versione template.
36. ~~Ampiezza validazione pre-pubblicazione.~~
    **Decisione 2026-04-29**: validare sia la correttezza formale del
    `context_schema`, sia la coerenza delle variabili referenziate da HTML, CSS
    templated e `file_name_pattern` rispetto allo schema.
37. ~~Filtri/funzioni Jinja custom.~~
    **Decisione 2026-04-29**: introdurre filtri custom in whitelist gia' dalla
    v1 (`date`, `money`, `number`, `percent`, `upper`, `lower`, `default`).
    Nessun filtro/funzione dinamico definito da tabella.
38. ~~Dati sensibili nel `context_json`.~~
    **Decisione 2026-04-29**: salvare completo lo snapshot funzionale usato per
    la ristampa, ma i context builder non devono mai includere segreti tecnici,
    token, password o credenziali. Eventuale mascheratura/classificazione campi
    sensibili resta estensione futura.
39. ~~Collocazione UI configurazione documenti.~~
    **Decisione 2026-04-29**: gestione template/versioni/asset nell'area
    Configurazione, usando il sistema permessi gia' abilitato e assegnabile
    anche a responsabili non admin. Non creare per v1 una voce sidebar autonoma
    "Documenti".
40. ~~Label voce configurazione documenti.~~
    **Decisione 2026-04-29**: usare label italiana "Modelli documenti".
    Traduzioni EN tramite meccanismo i18n gia' predisposto.
41. ~~Archivio PDF generale o solo da sorgente.~~
    **Decisione 2026-04-29**: per la v1 i PDF generati si consultano dalla
    sorgente. La lista documenti generati va comunque progettata come building
    block riusabile per una futura vista archivio generale.
42. ~~Ordinamento generazioni stessa sorgente.~~
    **Decisione 2026-04-29**: aggiungere `progressivo_sorgente` a
    `documenti.documenti_generati`, con unique per sorgente, per ordinare in
    modo stabile le generazioni dello stesso documento sorgente oltre a
    `generato_at`.
43. ~~Calcolo `progressivo_sorgente`: service o DB.~~
    **Decisione 2026-04-29**: calcolo nel service di generazione dentro
    transazione, perche' la generazione orchestra context, render, storage e DB.
    Il DB mantiene la guard finale con unique su sorgente/progressivo e il
    service gestisce eventuale concorrenza.
44. ~~Consistenza DB/storage in generazione.~~
    **Decisione 2026-04-29**: render PDF prima, poi transazione DB con
    creazione record e riserva `storage_key`, upload storage, insert file/evento
    e commit. Se upload fallisce rollback DB; se commit fallisce dopo upload,
    cleanup best-effort del file.
45. ~~Deduplica asset tramite `sha256`.~~
    **Decisione 2026-04-29**: `sha256` obbligatorio e deduplica immediata per
    emittente fiscale con guard unique su `(emittente_fiscale_id, sha256)`.
46. ~~Deduplica PDF generati.~~
    **Decisione 2026-04-29**: nessuna deduplica dei PDF generati. Stesso hash
    puo' corrispondere a generazioni storiche distinte; `sha256`/`pdf_hash`
    restano solo per audit e confronto.
47. ~~Ambito deduplica asset.~~
    **Decisione 2026-04-29**: deduplica asset logica per emittente fiscale, non
    globale tra emittenti. Eventuale deduplica fisica storage potra' essere
    trasparente in futuro.
48. ~~Delete/modifica asset usati.~~
    **Decisione 2026-04-29**: nessun delete fisico degli asset. Gli asset si
    disattivano o chiudono con `valido_al`; se il file cambia si carica un nuovo
    asset. La regola vale anche per asset non usati; per asset usati da versioni
    pubblicate/documenti generati si bloccano anche le colonne file/hash.
49. ~~Validita' temporale su `template_allegati`.~~
    **Decisione 2026-04-29**: nessuna validita' temporale
    sull'associazione allegati. Gli allegati sono parte immutabile della
    versione template; ogni cambio richiede nuova versione `BOZZA` e successiva
    pubblicazione.
50. ~~Clone allegati in nuova versione.~~
    **Decisione 2026-04-29**: "crea nuova versione da questa" clona anche gli
    allegati collegati, oltre a HTML/CSS/configurazione, nella nuova `BOZZA`.
51. ~~Obsolescenza vecchia versione pubblicata.~~
    **Decisione 2026-04-29**: quando una nuova versione pubblicata entra in
    validita' e si sovrappone alla precedente, il service chiude/marca
    `OBSOLETA` la vecchia. Se la nuova versione e' futura, la vecchia resta
    pubblicata fino alla scadenza.
52. ~~Cancellazione versioni bozza.~~
    **Decisione 2026-04-29**: una versione `BOZZA` puo' essere cancellata
    fisicamente su conferma utente. Versioni pubblicate/usate restano bloccate.
53. ~~Gestione `tipi_documento_output`.~~
    **Decisione 2026-04-29**: lookup configurabile da UI, con lock su
    `codice`/`codice_interno` per i tipi di sistema come `PREVENTIVO`.
54. ~~Lookup generica per `tipi_documento_output`.~~
    **Decisione 2026-04-29**: aggiungere `documenti.tipi_documento_output` alla
    whitelist lookup generica, essendo tabella standard
    `id/codice/codice_interno/descrizione`. `codice_interno` resta lockato
    secondo standard.
55. ~~Stile tabelle configurazione documenti.~~
    **Decisione 2026-04-29**: tutte le tabelle documentali che rappresentano
    configurazione devono seguire lo standard lookup
    `id/codice/codice_interno/descrizione`, con `codice_interno` lockato e
    inserimento nella whitelist lookup generica.
56. ~~Tipi asset documentali.~~
    **Decisione 2026-04-29**: creare `documenti.tipi_asset_documento` come
    lookup standard configurabile e in whitelist; `template_asset.asset_tipo_id`
    punta a questa tabella invece di usare varchar hardcoded.
57. ~~Stati workflow come lookup?~~
    **Decisione 2026-04-29**: gli stati tecnici (`BOZZA`, `PUBBLICATA`,
    `OBSOLETA`, `GENERATO`, `ARCHIVIATO`, `ANNULLATO`) non sono lookup
    configurabili. Restano valori controllati da guard DB/applicativa.
58. ~~Ruoli asset template come lookup.~~
    **Decisione 2026-04-29**: creare `documenti.ruoli_template_asset` come
    lookup standard configurabile e in whitelist; `template_allegati.ruolo_id`
    punta a questa tabella invece di usare varchar hardcoded.
59. ~~Tipi file documento come lookup.~~
    **Decisione 2026-04-29**: creare `documenti.tipi_file_documento` come lookup
    standard configurabile e in whitelist; `documenti_generati_file.file_tipo_id`
    punta a questa tabella invece di usare varchar hardcoded.
60. ~~Tipo evento documento come lookup?~~
    **Decisione 2026-04-29**: `documenti_generati_eventi.evento_tipo` e'
    tecnico, non configurabile come lookup. Gli eventi sono controllati dal
    service/guard DB.
61. ~~Render engine come lookup.~~
    **Decisione 2026-04-29**: creare `documenti.render_engine_documento` come
    lookup standard configurabile e in whitelist;
    `template_documenti_versioni.render_engine_id` punta a questa tabella. Il
    backend esegue comunque solo engine registrati in whitelist codice.
62. ~~Formato template come lookup?~~
    **Decisione 2026-04-29**: `formato_template` resta tecnico, non lookup
    configurabile, perche' influenza parser/rendering ed e' gestito dal codice.
63. ~~Formato pagina/orientamento come lookup?~~
    **Decisione 2026-04-29**: `page_format` e `page_orientation` restano
    tecnici con valori ammessi controllati da guard DB/applicativa, non lookup
    configurabili.
64. ~~Context builder come lookup?~~
    **Decisione 2026-04-29**: `context_builder_code` resta tecnico, non lookup
    configurabile. E' un binding a registry backend/whitelist di codice
    applicativo.
65. ~~API CRUD o comandi espliciti per versioni.~~
    **Decisione 2026-04-29**: CRUD solo per modifiche anagrafiche/bozza dove
    appropriato; ciclo vita versioni tramite comandi espliciti (`clona`,
    `pubblica`, `cancella-bozza`) per applicare guard e validazioni.
66. ~~Upload asset e modifica metadati.~~
    **Decisione 2026-04-29**: separare upload file e update metadati. L'upload
    crea asset con file/hash/storage; update successivi modificano solo
    descrizione, validita', `attivo` e `meta`. Il file non si sostituisce.
67. ~~MIME upload asset.~~
    **Decisione 2026-04-29**: upload asset con MIME whitelist per tipo asset
    (PDF, immagini supportate, CSS). Nessun upload generico libero.
68. ~~Limite dimensione upload/generazione.~~
    **Decisione 2026-04-29**: prevedere limiti dimensionali configurabili.
    Default v1 proposto: 25 MB per asset caricato; limite PDF generato separato
    e parametrico.
69. ~~Naming endpoint/API.~~
    **Decisione 2026-04-29**: seguire lo standard esistente di `api.md`: CRUD
    senza verbo nel path per CRUD reale, comandi espliciti con verbo solo per
    azioni non-CRUD come `pubblica`, `clona`, `anteprima`, `genera`.
70. ~~Seed iniziali minimi.~~
    **Decisione 2026-04-29**: seed iniziali per `PREVENTIVO`,
    `WEASYPRINT`, `PDF_FINALE`, tipi asset base (`LOGO`, `FIRMA`, `IMMAGINE`,
    `PDF`, `CSS`, `ALTRO`) e ruoli asset base (`HEADER`, `FOOTER`, `APPEND`,
    `PREPEND`, `INLINE`, `CSS`).
71. ~~Parametri storage documenti.~~
    **Decisione 2026-04-29**: usare il sistema parametri esistente
    `config.parameters` per configurazioni non segrete (`provider`, endpoint,
    base URL/DNS, bucket/container, prefix, limiti dimensionali). Le credenziali
    non stanno in chiaro in DB: si salva al massimo un secret ref e il backend
    risolve da env/secret manager. Confermato come scelta definitiva.
72. ~~Storage v1: posizione interfaccia, mapping parametri, cleanup.~~
    **Decisione 2026-05-03**: interfaccia `DocumentStorage` astratta in
    `apps/documenti/services/storage/base.py`, prima implementazione
    `filesystem.py`. Selettore `get_storage()` legge
    `documenti_storage_provider` da `config.parameters` (override possibile via
    settings Django). I 6 parametri seed (`provider`, `endpoint`, `base_url`,
    `bucket`, `prefix`, `secret_ref`) coprono il futuro adapter S3/MinIO senza
    modifiche alla firma. Cleanup post-fail commit: `try/finally` con
    `storage.delete()` best-effort + log warning + evento `STORAGE_ORPHAN` su
    `documenti_generati_eventi` (vedi Decisione 76).
73. ~~Dipendenza WeasyPrint.~~
    **Decisione 2026-05-03**: aggiungere `weasyprint` (ultima stabile
    compatibile Python 3.14, vincolo da fissare al pip-compile) a
    `backend/requirements.in`. Aggiornare `Dockerfile` con dipendenze native
    (`libpango-1.0-0`, `libpangoft2-1.0-0`, `libharfbuzz0b`, `libfontconfig1`,
    `libcairo2`, `libgdk-pixbuf-2.0-0`, `shared-mime-info`). Aggiungere nota in
    `docs/it/` sui prerequisiti dev (Linux/macOS). Rigenerare
    `backend/requirements.txt` con pip-compile.
74. ~~Posizione registry context_builder.~~
    **Decisione 2026-05-03**: registry **centrale** in
    `apps/documenti/services/context_builders/registry.py` (dict
    `CODE -> Builder`). Le implementazioni concrete vivono nei domini sorgente
    (es. `apps/vendite/services/preventivo_document_context_builder.py`) e si
    registrano via import esplicito dal modulo registry. Niente auto-discovery
    via signal Django: stesso pattern di `pipeline_task_registry_impl` (vendite),
    coerente con la regola "nessuna esecuzione dinamica libera dal DB"
    (Decisione 18). `template_documenti.context_builder_code` viene validato
    contro le chiavi del registry all'esecuzione: `ServiceError(E_DOCUMENTI_VALIDATION)`
    se non whitelisted.
75. ~~Permessi gestione vs generazione.~~
    **Decisione 2026-05-03**: introdurre **2 nuove azioni processo dedicate**
    `DOCUMENTI_TEMPLATE_MANAGE` + `DOCUMENTI_ASSET_MANAGE`, seedate insieme alla
    nuova area funzionale `documenti` (per i livelli area TUTTO/LETTURA/BLOCCATO
    della UI di configurazione). Le azioni di generazione/lista/download
    riusano i permessi del dominio sorgente (es. `vendite` per preventivi),
    senza nuovi permessi. Brief al team DB per la migration seed.
76. ~~Log evento download v1: opzione A vs B.~~
    **Decisione 2026-05-03**: opzione **A** — anticipare
    `documenti.documenti_generati_eventi` da Fase B a v1. DDL append-only
    (trigger guard delete + update) + pgTAP. Set CHECK chiuso v1: `GENERATO`,
    `SCARICATO`, `STORAGE_ORPHAN` (no `ANTEPRIMA` per Decisione 30: anteprime
    non persistenti escluse dalla timeline; no `RENDER_KO` per Decisione 32:
    errori render gestiti via log applicativo, non timeline funzionale).
    Estensioni Fase B (es. `INVIATO`, `ARCHIVIATO`, `ANNULLATO`) tramite
    migration successiva. Allinea v1 alle Decisioni 30/31 e copre il pattern
    di cleanup storage (Decisione 72). Tranche DB atterrata (changeset
    `20260503-06` + `20260503-07/08`).

---

## 10-bis. Decisioni operative (chiuse 2026-05-03)

> Stato DB Fase A: chiuso (DDL + guards A1..A7-bis + check + storico off + 9
> pgTAP + doc manuale). Step D whitelist Python `_REL_CONSENTITE`
> applicato a `apps/core/db/dbops_repository.py` il 2026-05-03 (4 lookup
> `documenti.*`: `tipi_documento_output`, `tipi_asset_documento`,
> `tipi_file_documento`, `render_engine_documento`).
>
> Le 5 decisioni operative riassunte qui sotto sono state chiuse dal team
> backend il 2026-05-03 e formalizzate nelle Decisioni 72-76 della §10
> sopra. I dettagli operativi e il razionale rimangono in queste
> sotto-sezioni come reference implementativo.

### 10-bis.1 Storage v1 concreto — CHIUSA

**Esito 2026-05-03 (Decisione 72)**: filesystem locale dietro interfaccia
`DocumentStorage` (`write/read/delete/exists`). MinIO/S3 entrera' come
seconda implementazione della stessa interfaccia, senza riscrivere il
render service.

Implementazione concordata:

- nome modulo e posizione interfaccia (es.
  `apps/documenti/services/storage/base.py` + `filesystem.py`);
- mapping parametri `config.parameters.documenti_storage_*` →
  configurazione runtime;
- gestione cleanup best-effort se commit DB fallisce dopo upload riuscito
  (vedi §6.1 nota consistenza DB/storage).

### 10-bis.2 Dipendenza WeasyPrint — CHIUSA

**Esito 2026-05-03 (Decisione 73)**: ok ad aggiungere `weasyprint` a
`backend/requirements.in`. Versione minima da fissare al momento del
pip-compile (vincolo: ultima stabile compatibile Python 3.14). Aggiornare
`Dockerfile` con le dipendenze native (`libpango-1.0-0`,
`libpangoft2-1.0-0`, `libharfbuzz0b`, `libfontconfig1`, `libcairo2`,
`libgdk-pixbuf-2.0-0`, `shared-mime-info`). Aggiungere nota in `docs/it/`
sui prerequisiti dev (Linux/macOS). Rigenerare `backend/requirements.txt`
con `pip-compile`.

### 10-bis.3 Posizione registry `context_builder` — CHIUSA

**Esito 2026-05-03 (Decisione 74)**: registry **centrale** in
`apps/documenti/services/context_builders/registry.py` con dizionario
`CODE -> Builder`. Implementazioni concrete nei domini sorgente (es.
`apps/vendite/services/preventivo_document_context_builder.py`); la
registrazione avviene via import esplicito dal modulo registry. Nessun
auto-discovery via signal Django: stesso pattern di
`pipeline_task_registry_impl` in `apps/vendite/db/vendite_pipeline_repository.py`,
con vantaggio di IDE-grep e zero magia.

Vincolo invariato: **nessuna esecuzione dinamica libera dal DB**
(coerente con Decisione 18). `template_documenti.context_builder_code`
resta binding logico; il backend solleva
`ServiceError(E_DOCUMENTI_VALIDATION)` se la chiave non e' nel registry.

### 10-bis.4 Permessi gestione vs generazione — CHIUSA

**Esito 2026-05-03 (Decisione 75)**: introdurre **2 nuove azioni
processo dedicate** `DOCUMENTI_TEMPLATE_MANAGE` + `DOCUMENTI_ASSET_MANAGE`,
seedate insieme alla nuova **area funzionale** `documenti` (per livelli
TUTTO/LETTURA/BLOCCATO della UI di configurazione documentale,
assegnabile a responsabili non admin per Decisione 25).

- generazione/lista/download: riusano permessi del dominio sorgente
  (`vendite` per preventivi, ecc.), nessun nuovo permesso;
- 2 azioni processo + 1 area funzionale: 1 migration seed unica.

Brief al team DB: vedi
[brief-db-documenti-permessi-seed.md](../work-done/brief-db-documenti-permessi-seed.md).

### 10-bis.5 Log evento download in v1 — CHIUSA

**Esito 2026-05-03 (Decisione 76)**: **opzione A** — anticipare
`documenti.documenti_generati_eventi` da Fase B a v1. Tranche atterrata
(changeset `20260503-06` DDL + `20260503-07/08` trigger guard delete/update).
Set CHECK chiuso v1: `GENERATO`, `SCARICATO`, `STORAGE_ORPHAN` (no
`ANTEPRIMA` per Decisione 30; no `RENDER_KO` per Decisione 32; estensioni
Fase B con migration successiva). Copre Decisioni 30/31 e il pattern di
cleanup storage (Decisione 72, evento `STORAGE_ORPHAN`).

**Nota implementativa BE**: su INSERT in `documenti_generati_eventi` non
passare `tx_id` esplicito; lo popola la regola 4 dell'automation. Lasciare
NULL e fidarsi del default DB.

Brief al team DB: vedi
[brief-db-documenti-eventi-anticipo-fase-b.md](../work-done/brief-db-documenti-eventi-anticipo-fase-b.md).

---

## 11. Piano Sviluppo DB

Questa sezione resta come traccia sintetica e storico decisionale.

Il **piano DB operativo aggiornato** e' stato estratto e corretto nel documento:

- [sviluppo-documenti-db.md](./sviluppo-documenti-db.md)

Motivo dello split:

- separare il piano concettuale generale dal piano Liquibase esecutivo;
- allineare il lavoro DB agli standard reali del repo;
- spezzare la consegna in tranche coerenti con il primo consumatore reale
  (`PREVENTIVO`), evitando di modellare subito tutto il motore finale.

Per lo sviluppo attivo fare riferimento prima a `sviluppo-documenti-db.md`,
poi a questa sezione come contesto funzionale di alto livello.

### 11.1 Regole generali

- Usare schema dedicato `documenti`.
- Usare Liquibase secondo naming/progressivi standard del progetto.
- Tutte le tabelle di configurazione devono seguire lo standard lookup:
  `id`, `codice`, `codice_interno`, `descrizione`, `attivo`, `meta`,
  colonne audit/storico standard.
- `codice_interno` e' codice tecnico stabile e lockato.
- Le tabelle lookup standard vanno aggiunte alla whitelist della lookup
  generica.
- Gli stati workflow restano tecnici, non lookup configurabili.
- Nessuna credenziale storage in chiaro nel DB: solo parametri non segreti e
  `secret_ref`.
- Le tabelle devono usare gli standard gia' presenti per audit, storico, lock
  colonne e delete block.

### 11.2 Changeset 1 — Schema `documenti`

Creare lo schema:

- `documenti`

Verificare:

- ownership/permessi coerenti con gli altri schemi applicativi;
- commento schema;
- inclusione nello standard di documentazione/generazione se previsto.

### 11.3 Changeset 2 — Lookup Standard

Creare queste tabelle lookup:

1. `documenti.tipi_documento_output`
2. `documenti.tipi_asset_documento`
3. `documenti.ruoli_template_asset`
4. `documenti.tipi_file_documento`
5. `documenti.render_engine_documento`

Colonne comuni:

| Colonna          | Tipo         | Note                            |
| ---------------- | ------------ | ------------------------------- |
| `id`             | bigserial PK | Identificativo                  |
| `codice`         | varchar(80)  | Codice leggibile/operativo      |
| `codice_interno` | varchar(80)  | Codice tecnico stabile, lockato |
| `descrizione`    | text         | Descrizione                     |
| `attivo`         | boolean      | Default true                    |
| `meta`           | jsonb        | Default `{}`                    |
| `storicizza`     | boolean      | Standard progetto               |
| `tx_id`          | uuid         | Standard progetto               |
| `user_insert`    | text         | Audit                           |
| `data_insert`    | timestamptz  | Audit                           |
| `user_update`    | text         | Audit                           |
| `data_update`    | timestamptz  | Audit                           |

Vincoli comuni:

- PK su `id`;
- unique su `codice`;
- unique su `codice_interno`;
- check non vuoto su `codice`, `codice_interno`, `descrizione`;
- default `attivo = true`;
- default `meta = '{}'::jsonb`;
- lock su `codice_interno`;
- lock su `codice` per record di sistema, se lo standard locale lo prevede.

Whitelist lookup generica:

- aggiungere tutte e cinque le tabelle alla whitelist della lookup generica
  `id/codice/codice_interno/descrizione`.

### 11.4 Changeset 3 — Seed Lookup

Inserire seed minimi, idempotenti e basati su `codice_interno`.

`documenti.tipi_documento_output`:

- `PREVENTIVO` — Preventivo

`documenti.tipi_asset_documento`:

- `LOGO`
- `FIRMA`
- `IMMAGINE`
- `PDF`
- `CSS`
- `ALTRO`

`documenti.ruoli_template_asset`:

- `HEADER`
- `FOOTER`
- `APPEND`
- `PREPEND`
- `INLINE`
- `CSS`

`documenti.tipi_file_documento`:

- `PDF_FINALE`
- `PDF_ALLEGATO`
- `PDF_FIRMATO`
- `HTML_RENDER`

`documenti.render_engine_documento`:

- `WEASYPRINT`
- opzionale non attivo o solo predisposto: `PLAYWRIGHT_PDF`

Regole seed:

- upsert idempotente;
- non dipendere da ID numerici;
- valorizzare `codice_interno`;
- record di sistema protetti da lock su `codice_interno` e, dove previsto,
  `codice`.

### 11.5 Changeset 4 — `template_documenti`

Creare `documenti.template_documenti`.

Colonne principali:

- `id bigserial PK`
- `tipo_documento_output_id bigint NOT NULL`
- `codice varchar(120) NOT NULL`
- `descrizione text NOT NULL`
- `sorgente_tipo_id bigint NOT NULL`
- `context_builder_code varchar(160) NOT NULL`
- `file_name_pattern text NULL`
- `emittente_fiscale_id bigint NOT NULL`
- `is_default boolean NOT NULL DEFAULT false`
- `attivo boolean NOT NULL DEFAULT true`
- `meta jsonb NOT NULL DEFAULT '{}'::jsonb`
- colonne standard audit/storico

FK:

- `tipo_documento_output_id` -> `documenti.tipi_documento_output(id)`
- `sorgente_tipo_id` -> `config.sorgenti(id)`
- `emittente_fiscale_id` -> `anagrafiche.emittenti_fiscali(id)`

Vincoli/indici:

- unique su `(tipo_documento_output_id, codice)`;
- indice su `sorgente_tipo_id`;
- indice su `(tipo_documento_output_id, sorgente_tipo_id, emittente_fiscale_id)`;
- vincolo/default unico: un solo template default attivo per
  `(tipo_documento_output_id, sorgente_tipo_id, emittente_fiscale_id)`;
- check non vuoto su `codice`, `descrizione`, `context_builder_code`;
- lock su `codice`.

Note:

- `context_builder_code` e' tecnico: non lookup.
- Il backend lo risolvera' via registry/whitelist applicativa.

### 11.6 Changeset 5 — `template_documenti_versioni`

Creare `documenti.template_documenti_versioni`.

Colonne principali:

- `id bigserial PK`
- `template_documento_id bigint NOT NULL`
- `versione integer NOT NULL`
- `stato varchar(30) NOT NULL`
- `titolo text NOT NULL`
- `formato_template varchar(30) NOT NULL`
- `html_template text NOT NULL`
- `css_template text NULL`
- `markdown_template text NULL`
- `render_engine_id bigint NOT NULL`
- `page_format varchar(30) NOT NULL DEFAULT 'A4'`
- `page_orientation varchar(20) NOT NULL DEFAULT 'PORTRAIT'`
- `margin_top_mm numeric(8,2) NOT NULL`
- `margin_right_mm numeric(8,2) NOT NULL`
- `margin_bottom_mm numeric(8,2) NOT NULL`
- `margin_left_mm numeric(8,2) NOT NULL`
- `valido_dal date NULL`
- `valido_al date NULL`
- `context_schema jsonb NOT NULL DEFAULT '{}'::jsonb`
- `meta jsonb NOT NULL DEFAULT '{}'::jsonb`
- `attivo boolean NOT NULL DEFAULT true`
- colonne standard audit/storico

FK:

- `template_documento_id` -> `documenti.template_documenti(id)`
- `render_engine_id` -> `documenti.render_engine_documento(id)`

Vincoli/indici:

- unique su `(template_documento_id, versione)`;
- check `versione > 0`;
- check stato in `BOZZA`, `PUBBLICATA`, `OBSOLETA`;
- check `formato_template` in `HTML`, `HTML_MARKDOWN_BLOCKS`;
- check `page_orientation` in `PORTRAIT`, `LANDSCAPE`;
- check `page_format` almeno su valori iniziali ammessi, es. `A4`, `A3`,
  `LETTER`;
- check margini >= 0;
- check `valido_al IS NULL OR valido_al >= valido_dal`;
- indice su `(template_documento_id, stato, attivo)`;
- indice su `(template_documento_id, valido_dal, valido_al)`;
- evitare due versioni `PUBBLICATA` sovrapposte per lo stesso template.

Regole DB richieste:

- una versione `PUBBLICATA` deve essere immutabile per contenuto/configurazione;
- bloccare modifica di HTML, CSS, markdown, engine, formato, margini,
  validita', context schema per versioni pubblicate;
- versione `BOZZA` cancellabile fisicamente;
- versioni pubblicate/usate da documenti generati non cancellabili.

Nota:

- la pubblicazione e la chiusura della versione precedente saranno orchestrate
  dal service, ma il DB deve mantenere guard minime contro stati incoerenti.

### 11.7 Changeset 6 — `template_asset`

Creare `documenti.template_asset`.

Colonne principali:

- `id bigserial PK`
- `codice varchar(120) NOT NULL`
- `codice_interno varchar(120) NOT NULL`
- `descrizione text NOT NULL`
- `asset_tipo_id bigint NOT NULL`
- `mime_type varchar(120) NOT NULL`
- `file_name text NOT NULL`
- `file_size_bytes bigint NOT NULL`
- `storage_key text NOT NULL`
- `sha256 varchar(64) NOT NULL`
- `emittente_fiscale_id bigint NOT NULL`
- `valido_dal date NOT NULL`
- `valido_al date NULL`
- `attivo boolean NOT NULL DEFAULT true`
- `meta jsonb NOT NULL DEFAULT '{}'::jsonb`
- colonne standard audit/storico

FK:

- `asset_tipo_id` -> `documenti.tipi_asset_documento(id)`
- `emittente_fiscale_id` -> `anagrafiche.emittenti_fiscali(id)`

Vincoli/indici:

- unique su `(codice, emittente_fiscale_id)`;
- unique su `(codice_interno, emittente_fiscale_id)`;
- unique su `(emittente_fiscale_id, sha256)` per deduplica asset per
  emittente;
- check `file_size_bytes > 0`;
- check `length(sha256) = 64`;
- check `valido_al IS NULL OR valido_al >= valido_dal`;
- indice su `asset_tipo_id`;
- indice su `emittente_fiscale_id`;
- indice su `storage_key`;
- indice su `attivo`;
- no delete fisico asset.

Regole DB richieste:

- bloccare delete fisico sempre;
- per asset usati da versioni pubblicate/documenti generati, bloccare modifica
  di `storage_key`, `sha256`, `file_size_bytes`, `mime_type`, `file_name`;
- per non usare piu' un asset si usa `attivo = false` o `valido_al`.

Nota applicativa:

- upload e update metadati sono separati;
- MIME whitelist e limite dimensione saranno validati dal service, con
  parametri configurabili.

### 11.8 Changeset 7 — `template_allegati`

Creare `documenti.template_allegati`.

Colonne principali:

- `id bigserial PK`
- `template_versione_id bigint NOT NULL`
- `asset_id bigint NOT NULL`
- `ruolo_id bigint NOT NULL`
- `ordinamento integer NOT NULL`
- `obbligatorio boolean NOT NULL DEFAULT true`
- `condizione_json jsonb NULL`
- `attivo boolean NOT NULL DEFAULT true`
- `meta jsonb NOT NULL DEFAULT '{}'::jsonb`
- colonne standard audit/storico

FK:

- `template_versione_id` -> `documenti.template_documenti_versioni(id)`
- `asset_id` -> `documenti.template_asset(id)`
- `ruolo_id` -> `documenti.ruoli_template_asset(id)`

Vincoli/indici:

- unique su `(template_versione_id, ruolo_id, ordinamento)`;
- check `ordinamento > 0`;
- indice su `asset_id`;
- indice su `ruolo_id`;
- indice su `template_versione_id`;
- no validita' temporale sull'associazione.

Regole DB richieste:

- se la versione template collegata e' `PUBBLICATA`, bloccare insert/update/delete
  sugli allegati della versione;
- se cambiano allegati, si crea nuova versione template.

### 11.9 Changeset 8 — `documenti_generati`

Creare `documenti.documenti_generati`.

Colonne principali:

- `id bigserial PK`
- `uid uuid NOT NULL`
- `tipo_documento_output_id bigint NOT NULL`
- `template_documento_id bigint NOT NULL`
- `template_versione_id bigint NOT NULL`
- `sorgente_tipo_id bigint NOT NULL`
- `sorgente_uid text NOT NULL`
- `sorgente_riga bigint NULL`
- `progressivo_sorgente integer NOT NULL`
- `stato varchar(30) NOT NULL`
- `titolo text NOT NULL`
- `nome_file text NOT NULL`
- `context_json jsonb NOT NULL`
- `context_hash varchar(64) NOT NULL`
- `template_hash varchar(64) NOT NULL`
- `pdf_hash varchar(64) NOT NULL`
- `generato_da_user_id integer NULL`
- `generato_at timestamptz NOT NULL`
- `emittente_fiscale_id bigint NOT NULL`
- `meta jsonb NOT NULL DEFAULT '{}'::jsonb`
- colonne standard audit/storico

FK:

- `tipo_documento_output_id` -> `documenti.tipi_documento_output(id)`
- `template_documento_id` -> `documenti.template_documenti(id)`
- `template_versione_id` -> `documenti.template_documenti_versioni(id)`
- `sorgente_tipo_id` -> `config.sorgenti(id)`
- `generato_da_user_id` -> `auth_user(id)`
- `emittente_fiscale_id` -> `anagrafiche.emittenti_fiscali(id)`

Vincoli/indici:

- unique su `uid`;
- unique su `(sorgente_tipo_id, sorgente_uid, sorgente_riga,
  progressivo_sorgente)`;
- check `progressivo_sorgente > 0`;
- check stato in `GENERATO`, `CORRENTE`, `SOSTITUITO`, `ARCHIVIATO`,
  `ANNULLATO`;
- check lunghezza hash = 64 per `context_hash`, `template_hash`, `pdf_hash`;
- indice su `(sorgente_tipo_id, sorgente_uid)`;
- indice su `(sorgente_tipo_id, sorgente_uid, sorgente_riga)`;
- indice su `template_versione_id`;
- indice su `generato_at DESC`;
- indice su `stato`;
- delete block per documenti generati.

Note:

- `progressivo_sorgente` viene calcolato dal service in transazione;
- il DB mantiene la guard unique finale;
- non creare record in caso di errore render/salvataggio.

### 11.10 Changeset 9 — `documenti_generati_file`

Creare `documenti.documenti_generati_file`.

Colonne principali:

- `id bigserial PK`
- `documento_generato_id bigint NOT NULL`
- `file_tipo_id bigint NOT NULL`
- `mime_type varchar(120) NOT NULL`
- `file_name text NOT NULL`
- `file_size_bytes bigint NOT NULL`
- `storage_key text NOT NULL`
- `sha256 varchar(64) NOT NULL`
- `ordinamento integer NOT NULL DEFAULT 1`
- `meta jsonb NOT NULL DEFAULT '{}'::jsonb`
- colonne standard audit/storico

FK:

- `documento_generato_id` -> `documenti.documenti_generati(id)`
- `file_tipo_id` -> `documenti.tipi_file_documento(id)`

Vincoli/indici:

- unique su `(documento_generato_id, file_tipo_id, ordinamento)`;
- check `file_size_bytes > 0`;
- check `length(sha256) = 64`;
- check `ordinamento > 0`;
- indice su `file_tipo_id`;
- indice su `sha256`;
- indice su `storage_key`;
- indice su `documento_generato_id`;
- garantire un solo `PDF_FINALE` principale per documento generato, tramite
  vincolo parziale o guard equivalente basata sul tipo file.

Note:

- nessuna deduplica dei PDF generati;
- stesso hash puo' rappresentare generazioni storiche distinte.

### 11.11 Changeset 10 — `documenti_generati_eventi`

Creare `documenti.documenti_generati_eventi`.

Colonne principali:

- `id bigserial PK`
- `documento_generato_id bigint NOT NULL`
- `evento_tipo varchar(60) NOT NULL`
- `evento_at timestamptz NOT NULL`
- `user_id integer NULL`
- `esito varchar(30) NOT NULL`
- `messaggio text NULL`
- `detail jsonb NOT NULL DEFAULT '{}'::jsonb`
- colonne standard audit/storico

FK:

- `documento_generato_id` -> `documenti.documenti_generati(id)`
- `user_id` -> `auth_user(id)`

Vincoli/indici:

- check `evento_tipo` in valori tecnici iniziali: `GENERATO`, `SCARICATO`,
  `ARCHIVIATO`, `ANNULLATO`;
- check `esito` in `OK`, `KO`, `WARN`;
- indice su `(documento_generato_id, evento_at DESC)`;
- indice su `evento_tipo`;
- append-only: bloccare update/delete, salvo standard tecnico di correzione se
  previsto dal progetto.

Note:

- eventi solo per documenti persistenti;
- anteprime PDF streaming non creano eventi;
- ogni download persistente registra `SCARICATO`.

### 11.12 Changeset 11 — Parametri `config.parameters`

Creare seed parametri non segreti per storage e limiti.

Parametri proposti:

- `documenti_storage_provider`
- `documenti_storage_endpoint`
- `documenti_storage_base_url`
- `documenti_storage_bucket`
- `documenti_storage_prefix`
- `documenti_storage_secret_ref`
- `documenti_asset_upload_max_mb`
- `documenti_pdf_generato_max_mb`

Regole:

- usare `config.parameters` e standard esistente;
- valori non portabili devono usare codici/stringhe, non ID numerici;
- nessuna credenziale in chiaro;
- `documenti_storage_secret_ref` e' solo riferimento logico a env/secret
  manager;
- default v1 asset upload: `25` MB.

### 11.13 Changeset 12 — Guard e Trigger

Applicare o predisporre le guard DB secondo standard progetto.

Guard richieste:

- lock `codice_interno` su lookup;
- delete block asset sempre;
- lock colonne file/hash asset se asset usato;
- lock versioni `PUBBLICATA`;
- blocco modifica allegati di versione pubblicata;
- blocco delete documenti generati;
- append-only eventi;
- default/audit/storico standard su tutte le tabelle previste.

Nota:

- le automations applicheranno i trigger standard dove previsto; il piano DB
  deve comunque indicare quali guard logiche sono richieste.

### 11.14 Changeset 13 — Whitelist Lookup Generica

Aggiungere alla whitelist lookup generica:

- `documenti.tipi_documento_output`
- `documenti.tipi_asset_documento`
- `documenti.ruoli_template_asset`
- `documenti.tipi_file_documento`
- `documenti.render_engine_documento`

Verificare che la lookup esponga almeno:

- `id`
- `codice`
- `codice_interno`
- `descrizione`
- `attivo`, se lo standard lo filtra automaticamente.

### 11.15 Test DB Attesi

Preparare test DB/pgtap o equivalenti per:

- creazione schema e tabelle;
- unique `codice`/`codice_interno` sulle lookup;
- lock `codice_interno`;
- whitelist lookup generica;
- FK principali;
- default unico template per tipo/sorgente/emittente;
- blocco sovrapposizione versioni pubblicate;
- immutabilita' versione pubblicata;
- cancellazione consentita solo per `BOZZA`;
- deduplica asset per `(emittente_fiscale_id, sha256)`;
- no delete fisico asset;
- lock colonne file asset usato;
- blocco modifica allegati di versione pubblicata;
- unique `progressivo_sorgente`;
- un solo `PDF_FINALE` per documento generato;
- append-only eventi;
- seed idempotenti.

### 11.16 Deliverable Attesi dal Team DB

- Changeset Liquibase ordinati e idempotenti.
- Seed iniziali lookup e parametri.
- Aggiornamento whitelist lookup generica.
- Test DB/pgtap dove applicabile.
- Commenti su tabelle e colonne principali.
- Nessuna introduzione di credenziali in chiaro.
- Nessun endpoint/API/backend in questa fase.

---

## 12. Stato implementazione backend

> Snapshot progressivo dello sviluppo backend `apps/documenti/`. Aggiornare
> al chiudersi di ogni tranche concentrica per mantenere visibile il
> confine tra cio' che e' atterrato e cio' che e' ancora previsto.

### 12.1 Tranche atterrate

#### Tranche A — Allineamento doc + whitelist (2026-05-03, PR #636)

- [DONE] Decisioni 72-76 chiuse in §10 (storage v1, WeasyPrint, registry
  context_builder, permessi area+azioni, eventi anticipati).
- [DONE] Step D whitelist Python `_REL_CONSENTITE`: aggiunte 4 lookup
  `documenti.*` (`tipi_documento_output`, `tipi_asset_documento`,
  `tipi_file_documento`, `render_engine_documento`) in
  [apps/core/db/dbops_repository.py](../../../../backend/apps/core/db/dbops_repository.py).
- [DONE] Brief al team DB per anticipo
  `documenti_generati_eventi` (Decisione 76) e seed permessi
  area+azioni (Decisione 75) — atterrati lato DB sullo stesso PR.

#### Tranche B — Foundation app + storage + registry (2026-05-03, PR #636)

- [DONE] Skeleton `apps/documenti/` (api, services, db, tests). Wiring in
  `INSTALLED_APPS` e `urls.py` (`/api/v1/documenti/`).
- [DONE] Storage layer: interfaccia astratta `DocumentStorage`
  (`write/read/delete/exists`) + impl `FilesystemDocumentStorage`
  (atomic write via tempfile+`os.replace`, guard path traversal,
  cleanup tempfile orfani su crash) + selector `get_storage()` da
  `config.parameters` (`documenti_storage_provider`,
  `documenti_storage_prefix`).
- [DONE] Registry centrale `context_builders` (`register_builder` /
  `get_builder` / `registered_codes`). Whitelist applicativa: chiave
  `template_documenti.context_builder_code` non registrata ->
  `E_DOCUMENTI_VALIDATION` (Decisione 18+74).
- [DONE] Settings `DOCUMENTI_STORAGE_ROOT` (default
  `<BASE_DIR>/var/documenti`, override env). `.gitignore` esclude
  `var/`. WeasyPrint `>=63,<64` aggiunto a `requirements.in`,
  Dockerfile aggiornato con dipendenze native Pango/Cairo/HarfBuzz/PixBuf.
- [DONE] 7 codici errore registrati in
  [error_policies.py](../../../../backend/apps/core/services/error_policies.py):
  5 dominio (`E_DOCUMENTI_VALIDATION/NOT_FOUND/DENIED/RENDER_FAILED/STORAGE_FAILED`),
  piu' 2 guard timeline (`E_EVENTO_DOCUMENTO_DELETE/UPDATE_VIETATA`, HTTP 409
  mappati ai trigger DB Fase A).

#### Tranche C — API read-only template + versioni (2026-05-03)

- [DONE] [types.py](../../../../backend/apps/documenti/types.py): TypedDict
  `TemplateDocumentoListRow/DetailRow`, `TemplateVersioneListRow/DetailRow`
  (proiezione leggera vs payload pesante con html/css/markdown).
- [DONE] [documenti_repository.py](../../../../backend/apps/documenti/db/documenti_repository.py):
  `list_templates` (paginato + scope EF via `bigint[]`/`ANY(%s)` + search
  ILIKE 3 colonne + ORDER BY whitelisted con `t.id` tiebreaker), `get_template`
  (404 unificato no leak), `list_versioni`, `get_versione` (defense-in-depth
  bind `template_documento_id`).
- [DONE] [template_service.py](../../../../backend/apps/documenti/services/template_service.py):
  facade lettura con scope EF automatico (`PermissionResolver.get_emittenti_ids`),
  validazione `stato` versione contro `{BOZZA,PUBBLICATA,OBSOLETA}`, guard
  id positivo prima del DB.
- [DONE] [api/views.py](../../../../backend/apps/documenti/api/views.py)
  e [urls.py](../../../../backend/apps/documenti/api/urls.py): 4 endpoint
  `DomainAPIView` con `area_funzionale="documenti"`, `is_search_endpoint=True`
  sulla list, `@extend_schema` con `inline_serializer`:
  - `GET /api/v1/documenti/templates/`
  - `GET /api/v1/documenti/templates/<id>/`
  - `GET /api/v1/documenti/templates/<id>/versioni/`
  - `GET /api/v1/documenti/templates/<id>/versioni/<vid>/`
- [DONE] Doc API manuale
  [api_documenti_templates.md](../../backend/documenti/manual/api_documenti_templates.md),
  voce in `dev/api.md` "Endpoint attivi" e sezione dedicata in
  `catalogo-building-block-backend.md`.
- [DONE] **44 unit/smoke test verdi** (12 storage, 5 registry, 9 repository,
  8 service, 7 API smoke, 3 atomic write/order_by validation).

#### Tranche D — Review critica + fix (2026-05-03)

- [DONE] **Atomic write** `FilesystemDocumentStorage.write`: tempfile
  nello stesso filesystem + `os.replace` (atomic POSIX) + cleanup
  tempfile orfani in `except`. Invariante: `documenti_generati_file.storage_uri`
  punta a file completo o assente, mai parziale.
- [DONE] **Default storage root** allineato: `settings.py` default =
  `<BASE_DIR>/var/documenti` (coerente con `.gitignore`); `selector.py`
  rimuove fallback dead-code, settings mancante = errore esplicito
  `E_DOCUMENTI_STORAGE_FAILED`.
- [DONE] **`order_by` validation** in repository: `KeyError` -> 500
  sostituito con `ServiceError(E_DOCUMENTI_VALIDATION)` -> 400. Defense-in-depth:
  fail-fast prima del round-trip DB.

#### Tranche E — CRUD admin testata template (2026-05-03)

- [DONE] [TemplateAdminService](../../../../backend/apps/documenti/services/template_admin_service.py)
  con `PayloadValidator` + `map_integrity_error`. POST `templates/` +
  PATCH `templates/<id>/` con `post_permission` /
  `patch_permission = "documenti_template_manage"`.
- [DONE] Mapping vincoli DB (3 unique + 3 FK del DDL Fase A) -> messaggi
  applicativi parlanti. Defense-in-depth: scope EF in create, immutabili
  in update rifiutati prima di altre validazioni, `is_default`
  partial-unique senza demote automatico (FE orchestra).
- [DONE] **22 nuovi test** (66 totali): 13 admin service, 4 repository,
  5 smoke API write.

#### Tranche F — Ciclo vita versione template (2026-05-03)

- [DONE] [TemplateVersioniAdminService](../../../../backend/apps/documenti/services/template_versioni_admin_service.py)
  con 5 metodi (`create_versione`, `update_versione`, `delete_versione`,
  `clone_versione`, `pubblica_versione`). Numero versione calcolato
  `MAX+1` per template (race protetta da unique DB).
- [DONE] 5 nuovi endpoint write con `post_permission`/`patch_permission`/
  `delete_permission = "documenti_template_manage"`:
  - `POST /api/v1/documenti/templates/<id>/versioni/`
  - `PATCH /api/v1/documenti/templates/<id>/versioni/<vid>/`
  - `DELETE /api/v1/documenti/templates/<id>/versioni/<vid>/`
  - `POST /api/v1/documenti/templates/<id>/versioni/<vid>/clona/`
  - `POST /api/v1/documenti/templates/<id>/versioni/<vid>/pubblica/`
- [DONE] 2 codici errore registrati in `error_policies.py`:
  `E_DOCUMENTI_VERSIONE_PUBBLICATA_IMMUTABILE` (HTTP 409, mappato a
  trigger DB A1) + `E_DOCUMENTI_VERSIONE_DELETE_BLOCKED` (HTTP 409,
  trigger DB A2).
- [DONE] Pubblicazione atomic con `valido_dal NOT NULL` guard +
  `transaction.atomic()`. Niente demote automatico del precedente
  (decisione concentrica v1: FE orchestra).
- [DONE] **24 nuovi test** (90 totali): 14 admin service versioni,
  5 repository versioni, 5 smoke API.

#### Tranche G — CRUD admin asset (2026-05-04)

- [DONE] [TemplateAssetAdminService](../../../../backend/apps/documenti/services/template_asset_admin_service.py)
  con 2 metodi: `upload_asset` (multipart binario + metadati anagrafici)
  e `update_asset_metadati` (no sostituzione file). `DocumentiRepository`
  esteso con `list_asset`, `get_asset`, `create_asset`,
  `update_asset_metadati`, `get_tipo_asset`. Type `TemplateAssetListRow`/
  `DetailRow`.
- [DONE] 4 endpoint asset:
  - `GET /api/v1/documenti/asset/` (lista paginata + search + scope EF)
  - `POST /api/v1/documenti/asset/` (multipart upload, parser_classes
    `MultiPartParser`+`FormParser`)
  - `GET /api/v1/documenti/asset/<id>/`
  - `PATCH /api/v1/documenti/asset/<id>/` (metadati: descrizione,
    valido_dal/al, attivo, meta — i 5 campi file rifiutati a monte +
    trigger A4 come guardrail finale)
- [DONE] **No DELETE** esposta: trigger DB A3 blocca cancellazione
  fisica. Soft-disable via PATCH `attivo=false` o `valido_al`.
- [DONE] 2 codici errore registrati: `E_DOCUMENTI_ASSET_DELETE_BLOCKED`
  (HTTP 409, trigger A3) + `E_DOCUMENTI_ASSET_FILE_IMMUTABILE`
  (HTTP 409, trigger A4).
- [DONE] **MIME whitelist per `tipi_asset_documento.codice_interno`**
  (`_MIME_WHITELIST_PER_TIPO` hardcoded service-side, Decisione 67):
  - `LOGO`/`IMMAGINE` → image/png, image/jpeg, image/svg+xml, image/webp, image/gif
  - `FIRMA` → image/png, image/jpeg, image/svg+xml, image/webp
  - `PDF` → application/pdf
  - `CSS` → text/css
  - `ALTRO` non ammesso in v1 (no upload generico).
- [DONE] **Pattern transazionale upload**: INSERT row dentro
  `transaction.atomic()` (dedup naturale via unique
  `(emittente, sha256)`), poi `storage.write` (atomic via tempfile +
  `os.replace`). Cleanup STORAGE_ORPHAN su fail commit post-write
  (best-effort + log warning, no raise per non mascherare l'eccezione
  originale del commit). Limite size da parameter
  `documenti_asset_upload_max_mb` (default 25).
- [DONE] `storage_key` stabile derivata: `assets/<emittente_id>/<sha256>.<ext>`.
- [DONE] **5 smoke test API** (95 totali): list requires JWT, list ok,
  upload requires file field, upload happy multipart, PATCH metadati.
  Test repo + service unit asset chiusi in Tranche H1 (vedi sotto).

#### Tranche H (review critica E + F + G post-coding, 2026-05-04)

- [DONE] **Refactor duplicazione** `_build_create_data` /
  `_build_update_data` in `template_versioni_admin_service.py`:
  estratto helper `_fill_optional_versione_fields` riusato da entrambi
  (~80 righe risparmiate), aggiunto cross-field guard
  `valido_al >= valido_dal` (DDL non ha CHECK su asset/versioni).
- [DONE] **Layer violation fix**: `_resolve_codice_tipo_asset` non usa
  piu' `from django.db import connection` inline. Aggiunto
  `DocumentiRepository.get_tipo_asset()` con dict ritornato; service
  consuma via repo.
- [DONE] **Helper `_guard_date_range`** centralizzato in
  `template_asset_admin_service.py` (chiamato in
  `_build_upload_metadati` + `_build_update_data`) e analoga difesa
  cross-field in `template_versioni_admin_service` (helper opzionali +
  clone). Daterange empty silenzioso (workaround DDL) bloccato a monte.
- [DONE] Suite **95/95 verde** post-fix.

#### Tranche H1 — Test repo + service unit asset (2026-05-04)

- [DONE] **Repository asset** — 13 test in
  [test_documenti_repository_asset.py](../../../../backend/apps/documenti/tests/services/test_documenti_repository_asset.py):
  `list_asset` (filtri completi + search ILIKE su 4 colonne incluso
  `file_name`, scope `ANY(%s)`, paginazione cap 200 + tiebreaker `a.id ASC`,
  `order_by` fuori whitelist → `E_DOCUMENTI_VALIDATION` senza toccare il DB),
  `get_asset` (row → dict, missing → None, scope), `create_asset`
  (INSERT solo colonne whitelisted in `ASSET_CREATE_COLUMNS` +
  `RETURNING id`), `update_asset_metadati` (UPDATE solo colonne in
  `ASSET_UPDATE_COLUMNS`, immutabili file/anag silenziosamente filtrate
  come guardrail in profondita'; data vuoto → False senza SQL),
  `get_tipo_asset` (dict normalizzato, None se inesistente).
- [DONE] **Service admin asset** — 28 test in
  [test_template_asset_admin_service.py](../../../../backend/apps/documenti/tests/services/test_template_asset_admin_service.py).
  Mock-only (regola CI), niente DB ne' filesystem. Coperti:
  - upload happy path admin globale: sequenza INSERT → `storage.write`
    (dopo l'INSERT, dentro `transaction.atomic`) → commit → ritorno via
    `reader.get_asset` fresh; verifica derivazione `storage_key`
    `assets/<emittente>/<sha>.<ext>` e sha256 64 hex;
  - scope emittente: admin globale (`PermissionResolver` → None),
    operatore in scope, operatore fuori scope, anon → tutti gli ultimi
    rifiutati con `E_DOCUMENTI_VALIDATION` senza DB ne' write;
  - validazione payload: chiave extra, campo obbligatorio mancante,
    `file_bytes` vuoto, `file_name` vuoto, oversize con limite parametrico
    (`documenti_asset_upload_max_mb`), `_guard_date_range`
    `valido_al < valido_dal`;
  - risoluzione tipo asset: inesistente, non attivo, `ALTRO` non ammesso
    in v1 (no upload generico);
  - MIME whitelist per tipo: copertura ammesso/rifiutato per ciascun
    `codice_interno` whitelisted (LOGO/IMMAGINE/FIRMA/PDF/CSS) +
    rifiuto MIME fuori whitelist (es. `application/pdf` su LOGO);
  - dedup naturale: `IntegrityError` su `uq_template_asset_emittente_sha256`
    mappata a messaggio applicativo parlante; `storage.write` non chiamato
    perche' INSERT precede write nel try interno;
  - cleanup STORAGE_ORPHAN: simulato commit fail al `__exit__` di
    `transaction.atomic` con context manager custom → `storage.delete`
    chiamato sull'uri restituito da `write` (best-effort, senza
    mascherare l'eccezione del commit);
  - storage.write fail: `transaction.atomic` rollback, niente cleanup
    (file mai esistito, `need_cleanup=False`);
  - update: happy path con `reader.get_asset` chiamato 2 volte (pre-check
    visibilita' + ritorno fresh), `asset_id` non positivo rifiutato senza
    DB, propagazione 404 dal reader, immutabili file
    (`storage_key`/`sha256`/`file_size_bytes`/`mime_type`/`file_name`)
    e anag (`codice`/`codice_interno`/`asset_tipo_id`/`emittente_fiscale_id`)
    rifiutati PRIMA di altre validazioni con messaggio parlante,
    `validate_allowed_keys`, payload vuoto post-validate,
    `_guard_date_range`, `attivo=None` rifiutato (NULL non ammesso),
    `IntegrityError` mappata, repo False → `E_DOCUMENTI_NOT_FOUND`.
- [DONE] Suite **136/136 verde** (95 + 41 nuovi: 13 repo + 28 service).
- Note: nessun cambio al codice `template_asset_admin_service.py` ne' al
  `documenti_repository.py`: il debito era solo di copertura test. La
  Tranche H1 chiude il compromesso preso in Tranche G ("priorita' review
  critica").

#### Tranche I — Render service WeasyPrint + orchestratore (2026-05-04)

- [DONE] **`render_service.render_pdf`**
  ([render_service.py](../../../../backend/apps/documenti/services/render_service.py)).
  Funzione pura `render_pdf(template_versione, context) -> bytes`:
  whitelist applicativa engine (v1: solo `WEASYPRINT`, case-insensitive
  con normalize uppercase, Decisione 3) -> Jinja2 con `StrictUndefined`
  (fail-fast su variabile mancante, Decisione 4) -> WeasyPrint
  (`HTML(string=...)`+`CSS(string=...)`, lazy import per non risolvere
  Pango/Cairo a meno che il render non sia effettivamente invocato).
  Errori interni di Jinja (variabile mancante, sintassi malformata) e
  WeasyPrint (parse/font/IO) mappati a `E_DOCUMENTI_RENDER_FAILED` con
  `detail` diagnostico. Guard versione minima: `html_template` o
  `render_engine_codice` mancanti -> errore parlante.
- [DONE] **`DocumentGenerationService.genera_documento`**
  ([document_generation_service.py](../../../../backend/apps/documenti/services/document_generation_service.py)).
  Orchestratore della generazione persistita:
  - auth/scope check (PermissionResolver)
  - resolve template: override esplicito `template_documento_id` ->
    `TemplateService.get_template` (404 + scope unificato); altrimenti
    `repo.find_template_applicabile` su `(sorgente_tipo, emittente,
    is_default=true)` con scope, `tipo_documento_output_id` opzionale
  - coerenza template-input: emittente o sorgente_tipo del template
    diversi dai parametri richiesti -> `E_DOCUMENTI_VALIDATION` parlante
  - resolve versione PUBBLICATA attiva: `repo.get_versione_pubblicata_attiva`
    su `validita @> CURRENT_DATE` (data passata via hook `_today()` per
    testabilita'), versione DESC, LIMIT 1
  - context builder: `registry.get_builder(template.context_builder_code)`
    (whitelist applicativa Decisione 18+74) -> `builder.build_context()`
  - render PDF: `render_pdf(...)` FUORI dalla transazione (Decisione 32:
    render fail = niente record DB)
  - hashes: `context_hash` (sha256 JSON canonical sort_keys),
    `template_hash` (sha256 html|css|markdown), `pdf_hash` (sha256 bytes)
  - `nome_file` via `str.format(template.file_name_pattern, **context)`,
    `KeyError`/`IndexError` -> `E_DOCUMENTI_RENDER_FAILED` parlante;
    fallback `<codice>.pdf` se pattern assente
  - lookup tipo_file `PDF_FINALE` via codice (memoria
    feedback_no_hardcoded_ids), assente o non attivo -> VALIDATION
  - `next_progressivo_sorgente` con branching IS NULL vs `=` su
    `sorgente_riga`; race protetta da unique
    `uq_documenti_generati_sorgente_progressivo` -> mappato a errore
    parlante
  - sequenza atomica `transaction.atomic()`:
    INSERT `documenti_generati` (id, uid RETURNING) ->
    INSERT `documenti_generati_file` (`is_principale=true`,
    `ordinamento=1`, file_tipo PDF_FINALE) ->
    INSERT evento `GENERATO/OK` SENZA `tx_id` esplicito (Decisione 76 -
    automation regola 4) -> `storage.write` (atomic write filesystem) ->
    commit
  - cleanup STORAGE_ORPHAN best-effort se commit fallisce post-write:
    `storage.delete` + `logger.warning` (no raise per non mascherare
    l'eccezione del commit). Nota: `documenti_generati_eventi.documento_generato_id`
    NOT NULL impedisce di registrare evento `STORAGE_ORPHAN` linkato a
    un doc fantasma -> log applicativo per intervento manuale.
- [DONE] **Repository extended** con 7 nuovi metodi
  ([documenti_repository.py](../../../../backend/apps/documenti/db/documenti_repository.py)):
  `find_template_applicabile`, `get_versione_pubblicata_attiva`,
  `next_progressivo_sorgente`, `create_documento_generato` (RETURNING
  id+uid), `create_documento_generato_file`, `emit_evento_documento`
  (NIENTE `tx_id` in whitelist colonne), `get_tipo_file_documento_by_codice`.
  Whitelist colonne `DOCUMENTO_GENERATO_CREATE_COLUMNS` /
  `DOCUMENTO_GENERATO_FILE_CREATE_COLUMNS` /
  `EVENTO_DOCUMENTO_CREATE_COLUMNS` per defense-in-depth contro chiavi
  extra in input.
- [DONE] **Dipendenza** Jinja2 aggiunta a `backend/requirements.in`
  (`jinja2>=3.1,<4`) e `requirements.txt` rigenerato via `pip-compile`.
  Scelta motivata: `StrictUndefined` di Jinja fail-fast su variabili
  mancanti (allinea con feedback_bug_logici_modello — preferiamo
  errore esplicito al silenzioso campo vuoto di DTL).
- [DONE] **41 nuovi test** mock-only (177/177 totali = 136 + 12 repo
  Tranche I + 11 render_service + 18 document_generation_service):
  - repo: `find_template_applicabile` con/senza tipo_output, scope,
    nessun match; `get_versione_pubblicata_attiva` filtri stato/attivo/
    validita; `next_progressivo_sorgente` branching IS NULL vs `=`;
    INSERT 3 tabelle con whitelist (incluso check `tx_id` non in SQL
    eventi); lookup tipo_file
  - render: happy path Jinja+Weasy; engine whitelist e normalizzazione
    case; html vuoto / engine vuoto rifiutati; StrictUndefined
    variabile mancante; TemplateSyntaxError mappato; ciclo
    `{% for %}`; WeasyPrint exception/empty mappati; CSS opzionale
  - generation: pipeline completa (chiamate + payload), auth/scope,
    template via id vs find applicabile, no match -> NOT_FOUND,
    coerenza emittente+sorgente_tipo, no versione PUBBLICATA,
    context_builder_code vuoto, render solleva (no DB), render empty,
    file_name_pattern var mancante, tipo_file mancante/non-attivo,
    IntegrityError progressivo mappato, storage.write fail (no
    cleanup), commit fail (cleanup STORAGE_ORPHAN best-effort)
- Note implementative:
  - storage_key formato `documenti/<emittente>/<pdf_sha256>.<ext>`:
    dedup naturale per parita' di contenuto (re-render dello stesso
    input scrive sopra; record DB diversi puntano alla stessa key
    quando il content e' identico — comportamento accettabile v1)
  - render avviene PRIMA del DB: render fail non lascia record orfani
    (Decisione 32) — niente evento `RENDER_KO` da loggare in v1
  - hash `context_json` calcolato con `json.dumps(sort_keys=True,
    default=str)` -> deterministico anche per Decimal/date

#### Tranche I+J — Review critica + refactor (2026-05-04)

Review post-coding di I+J prima del commit, con fix mirati su bug reali e
duplicazioni. **Nessun cambio API**, solo robustezza.

- 🔴 **Bug fix — context_json non JSON-safe**: il context restituito dai
  builder (`Decimal` da totali, `date` da scadenze) sarebbe stato passato
  raw a psycopg per il jsonb -> `TypeError` al primo INSERT in DB reale.
  L'orchestrator ora normalizza il context una sola volta via
  `json.loads(json.dumps(context, sort_keys=True, default=str))` e usa la
  versione JSON-safe sia per `context_json` (DB) sia per `context_hash`.
- 🔴 **Bug fix — `context_hash` non deterministico**: il builder
  `PreventivoDocumentContextBuilder` metteva `built_at = now()` in
  `_meta`, rompendo la promessa "stesso context -> stesso hash" della
  doc Tranche I (annullava il dedup logico). Rimosso `built_at`
  (`generato_at` lato DB e' la fonte autoritativa). Test aggiunto:
  due build con stesso input -> stesso `context_hash`.
- 🟡 **Hardening — `template_hash` separator**: `\n--CSS--\n` /
  `\n--MARKDOWN--\n` collision-prone se l'html template li contiene
  letteralmente. Sostituito con NULL byte `\x00` (non valido in HTML/CSS/
  markdown) -> collision-proof.
- 🟡 **Optimization — scope cached**: `PermissionResolver.get_emittenti_ids`
  era chiamato 2 volte (`_guard_emittente_in_scope` + `_resolve_template`)
  per ogni invocazione. Ora calcolato una sola volta in
  `genera_documento` e propagato a `_resolve_template`.
- 🟡 **Cleanup — `generato_at` rimosso dal return**: il valore lato
  Python (timezone.now post-commit) divergeva dal valore DB (default
  `now()` al momento INSERT). Il caller fa lookup se serve.
- 🟡 **Hardening — input guard espliciti**: `genera_documento` ora
  rifiuta pre-DB `emittente_fiscale_id`/`sorgente_tipo_id`/`sorgente_id`
  non positivi e `sorgente_uid` vuoto/whitespace -> errore parlante
  invece di IntegrityError generico DB.
- 🟢 **Refactor — duplicazioni eliminate** (memoria
  feedback_concentrico_no_yagni / Tid review):
  - `_guard_id` di `TemplateService` (Tranche C) + `_guard_positive_int`
    di `DocumentGenerationService` (introdotto qui) + guard inline di
    `PreventivoDocumentContextBuilder` (Tranche J): tutti consolidati su
    `PayloadValidator.guard_positive_int` (gia' usato dai service admin
    Tranche E/F/G). Aggiunto `PayloadValidator.guard_non_empty_string`
    per il caso scalare (es. `sorgente_uid`).
  - `_guard_emittente_in_scope` duplicato in 3 service del dominio
    documenti (Tranche E, G, I): estratto in nuovo modulo
    [apps/documenti/services/_scope.py](../../../../backend/apps/documenti/services/_scope.py)
    con 4 funzioni standalone: `guard_user_authenticated`,
    `resolve_emittente_scope`, `guard_emittente_in_scope`,
    `guard_emittente_in_scope_for_user` (composizione end-to-end).
    `template_admin_service` e `template_asset_admin_service` delegano
    a `guard_emittente_in_scope_for_user`; l'orchestrator usa le 3
    utility separate per cachare lo scope.
- **Test aggiunti** (10 nuovi su `_scope.py` + 3 sull'orchestrator =
  196/196 totali = 183 + 13):
  - `_scope`: auth/None/anon, scope=None vs lista, id in/out scope,
    `guard_emittente_in_scope_for_user` happy + anon + fuori scope;
  - orchestrator: context con `Decimal`/`date` JSON-safe; due build con
    stesso input -> stesso `context_hash`; input guard scalari
    (`emittente`/`sorgente_tipo`/`sorgente_id`/`sorgente_riga` non
    positivi + `sorgente_uid` vuoto/whitespace).

#### Tranche J — Context builder PREVENTIVO (2026-05-04)

- [DONE] **`PreventivoDocumentContextBuilder`**
  ([apps/vendite/services/preventivo_document_context_builder.py](../../../../backend/apps/vendite/services/preventivo_document_context_builder.py))
  con `CODE = "PREVENTIVO"`. `build_context(sorgente_id, *, auth_user_id,
  locale)` legge dalla `PreventiviRepository` (esistente Fase 3.F6
  refactor vendite) testata + righe + riepilogo IVA + indirizzi e ritorna
  un dict stabile a 6 sezioni: `preventivo`, `cliente`, `indirizzi`,
  `righe`, `riepilogo_iva`, `_meta` (locale + auth_user_id + built_at +
  context_version).
- [DONE] **Auto-register al boot Django**
  ([apps/vendite/apps.py](../../../../backend/apps/vendite/apps.py)):
  `VenditeConfig.ready()` importa il modulo per side-effect; la
  `register_builder(...)` finale del modulo popola il registry centrale
  Tranche B. Niente auto-discovery via signal Django (coerente con
  pattern `pipeline_task_registry_impl`).
- [DONE] Confine v1 chiarito:
  - il builder NON applica scope/permessi: la sicurezza e' del caller
    (orchestrator + view dominio Tranche K con permessi `vendite_*`);
  - guard `sorgente_id` positivo intero (no bool, no string);
  - `cliente` shape minima (billing_account + denominazione) — nessuna
    espansione P.IVA/CF/sede in v1; estensione Fase B se serve;
  - `righe` e `riepilogo_iva` pass-through dalle viste denormalizzate
    di vendite (nessun ricalcolo Python lato builder).
- [DONE] **6 nuovi test** mock-only (183/183 totali = 177 + 6):
  - happy path con shape completa + chiavi attese a tutti i livelli;
  - id non valido (0/-1/bool/string) -> `E_DOCUMENTI_VALIDATION` no DB;
  - preventivo inesistente -> `E_DOCUMENTI_NOT_FOUND` con cleanup
    early (no chiamate ai metodi list_*);
  - delega 1:1 ai metodi repo;
  - `CODE = 'PREVENTIVO'`;
  - registrazione registry: dopo import esplicito del modulo,
    `registered_codes()` contiene 'PREVENTIVO' e `get_builder("PREVENTIVO")`
    ritorna istanza di `PreventivoDocumentContextBuilder`.

#### Tranche K — Endpoint generazione/anteprima/lista/download (2026-05-04)

- [DONE] **4 endpoint** sotto `/api/v1/vendite/preventivi/<id>/documenti/`
  ([apps/vendite/api/preventivi_documenti_views.py](../../../../backend/apps/vendite/api/preventivi_documenti_views.py)
  con route in
  [preventivi_urls.py](../../../../backend/apps/vendite/api/preventivi_urls.py)):
  - `POST genera/` -> `DocumentGenerationService.genera_documento`,
    body opzionale `template_documento_id`/`tipo_documento_output_id`
    per override del default `is_default=true`;
  - `POST anteprima/` -> `anteprima_documento`, risposta binaria
    `application/pdf` con `Content-Disposition: inline` (Decisione 30:
    no persist, no evento timeline);
  - `GET` lista -> `list_documenti_per_sorgente`, paginato + scope EF;
  - `GET <documento_id>/file/` -> `download_documento`, risposta binaria
    `attachment` + emit evento `SCARICATO` (Decisione 31).
  Le view sono in `apps/vendite/api/` perche' i permessi sono del
  dominio sorgente (Decisione 75): `area_funzionale="vendite"` con
  permission default lettura preventivi. Il path nidificato
  `preventivi/<id>/documenti/<doc_id>/` consente difesa-in-profondita'
  contro tampering URL (la `_resolve_contesto_preventivo` nella view
  download verifica visibilita' del preventivo prima di leggere il file).
- [DONE] **3 nuovi metodi** in `DocumentGenerationService`:
  `anteprima_documento` (pipeline render senza persist),
  `list_documenti_per_sorgente` (wrapping repo + scope),
  `download_documento` (lookup + storage.read + emit `SCARICATO` in
  tx separata best-effort: se il log fallisce il file e' gia' tornato
  al client, l'audit non blocca il download).
- [DONE] **4 nuovi metodi** in `DocumentiRepository`:
  `get_sorgente_tipo_id_by_codice` (lookup `config.sorgenti` per codice,
  no ID hardcoded), `list_documenti_per_sorgente` (filtri sorgente +
  scope `ANY(%s)` + paginazione cap 200 + ORDER BY `generato_at DESC`),
  `get_documento_generato` (404 unificato no leak via scope opzionale),
  `get_documento_generato_file_principale` (filtro `is_principale=true`
  con `LIMIT 1`).
- [DONE] **1 nuovo metodo** in `PreventiviRepository`:
  `get_for_documento_generation` -> `{id, uid, emittente_fiscale_id}`,
  proiezione minima senza JOIN su anagrafiche/billing_account
  (`emittente_fiscale_id` e' colonna nativa NOT NULL del DDL preventivi).
- [DONE] **`DocumentStorage.build_storage_uri(key)`** aggiunto
  all'interfaccia astratta + impl filesystem: il caller post-fact ha solo
  la `storage_key` letta dal DB e ricostruisce lo storage_uri prima di
  passare a `read/delete/exists`. Risolve la disconnessione fra
  `storage_uri` ritornato da `write` (memoria runtime) e `storage_key`
  salvato su DB.
- [DONE] **22 nuovi test** mock-only (218/218 totali = 196 + 22 K):
  - repo: `get_sorgente_tipo_id_by_codice`, `list_documenti_per_sorgente`
    branching `IS NULL` vs `=`, scope `ANY(%s)`, paginazione cap 200 +
    ORDER, `get_documento_generato` row/None/scope,
    `get_documento_generato_file_principale` `is_principale=true` +
    LIMIT 1;
  - service: `anteprima` happy + anon + render fail + input guard;
    `list_per_sorgente` happy + anon + uid vuoto;
    `download` happy (storage.read + emit SCARICATO) + 404 documento +
    404 file principale + storage read fail mappato + emit fail
    best-effort + input guard.

#### Tranche L — Frontend Configurazione "Modelli documenti" (2026-05-04)

- [DONE] **2 voci sidebar Configurazione**
  ([core/navigation.js](../../../../frontend/src/core/navigation.js)):
  `modelli-documenti` (icona `pi pi-file-pdf`) e `asset-documenti`
  (icona `pi pi-paperclip`). Route in
  [router/index.js](../../../../frontend/src/router/index.js):
  `/config/modelli-documenti` e `/config/asset-documenti`.
- [DONE] **API client** (`config/api/`):
  `templateDocumenti.js` (10 endpoint Tranche C/E/F: list/get/create/update
  template + list/get/create/update/delete/clona/pubblica versioni),
  `templateAssetDocumenti.js` (4 endpoint Tranche G: list/get/upload
  multipart/update metadati).
- [DONE] **Store Pinia** (`config/stores/`):
  `templateDocumenti.js` (factory `createCrudAdminStore` con
  `userScoped: true`, filtri tipo_output/sorgente/emittente),
  `templateAssetDocumenti.js` (defineStore custom con `userScoped: true`
  e azione `upload(formData)` multipart),
  `templateVersioni.js` (defineStore custom con `userScoped: true` per
  ciclo vita versioni di un template).
- [DONE] **Componenti** (`config/components/`):
  - `TemplateDocumentiSearchTable.vue`: lista paginata con
    `useSearchTable`, filtri tipo_output / sorgente / attivo via
    `LookupSelect`, `NewButton` + `RowActionsMenu`;
  - `TemplateDocumentoDrawer.vue`: drawer testata con campi codice/
    codice_interno/descrizione, dropdown tipo_output/sorgente
    (LookupSelect immutabili dopo create), context_builder hardcoded
    whitelist (PREVENTIVO/CONTRATTO/ORDINE) con warning quando il
    builder selezionato non e' registrato lato BE, file_name_pattern,
    is_default, attivo. Dopo create il drawer evolve a edit per
    consentire la gestione versioni;
  - `TemplateVersioniSection.vue`: master-detail inline delle
    versioni dentro il drawer template. DataTable + form inline con
    textarea html/css/markdown (Decisione 9: editor visuale fuori
    scope v1) e `RowActionsMenu` (Pubblica BOZZA, Clona, Elimina BOZZA)
    e Dialog dedicato pubblicazione con `DatePicker` valido_dal/al;
  - `TemplateAssetSearchTable.vue`: lista asset con filtri
    asset_tipo / attivo, formattazione size human-readable;
  - `TemplateAssetDrawer.vue`: drawer create con `FileUpload` multipart
    (cap 25MB) + metadati; in edit solo metadati editabili (file
    immutabile, Decisione 66; DELETE bloccata da trigger DB A3:
    soft-disable via `attivo=false`).
- [DONE] **View** (`config/views/`):
  `ModelliDocumentiTemplatesView.vue` + `ModelliDocumentiAssetView.vue`,
  pattern coerente con `CategorieClientiListView`.
- [DONE] **i18n** ([locales/it.json](../../../../frontend/src/locales/it.json)
  e [en.json](../../../../frontend/src/locales/en.json)): sezione
  `documenti.context_builders` + `config.modelli_documenti` con ~80
  chiavi (toolbar, drawer testata, sezione versioni, asset).
- [DONE] **Costanti FE riusabili**
  ([config/constants/](../../../../frontend/src/config/constants/)):
  `documentiContextBuilders.js` (whitelist hardcoded codici allineata
  al registry BE: PREVENTIVO=registered, CONTRATTO/ORDINE=placeholder),
  `documentiVersioniWhitelists.js` (PAGE_FORMATS/PAGE_ORIENTATIONS/
  FORMATI_TEMPLATE allineate a CHECK DDL Tranche F + ASSET_UPLOAD_MAX_*
  costanti).
- [DONE] **Bug fix architetturale** in
  [createCrudAdminStore](../../../../frontend/src/core/composables/createCrudAdminStore.js):
  il factory NON applicava `userScoped: true` di default. Tutti gli
  store CRUD admin esistenti basati sul factory leakavano dati
  cross-user al logout (memoria feedback_pinia_userscoped). Default
  cambiato a `userScoped: true`; override esplicito a `false` per dati
  globali. Fix di sicurezza diffuso.
- [DONE] **Refactor duplicazioni** durante review FE:
  - `formatSize` da component-locale a `core/utils/format.js` (esistente);
  - `toIsoDate` / `new Date(iso)` da component-locale a
    `localDateToIso` / `isoToLocalDate` di `core/utils/dateHelpers.js`
    (anche fix timezone shift su DatePicker);
  - costanti DDL whitelist (PAGE_FORMATS, PAGE_ORIENTATIONS,
    FORMATI_TEMPLATE) da inline a `documentiVersioniWhitelists.js`;
  - max upload bytes hardcoded `26214400` -> `ASSET_UPLOAD_MAX_BYTES`
    costante.
- Build `vite build` verde dopo refactor.

#### Tranche M — Frontend genera documento da sorgente (2026-05-04)

- [DONE] **Pulsante "Genera PDF" generico riusabile**
  ([documenti/components/GeneraPdfButton.vue](../../../../frontend/src/documenti/components/GeneraPdfButton.vue)).
  Icona `pi pi-file-pdf` + classe centralizzata `app-pdf-btn`
  (pattern building block `app-*-btn`, vedi
  [main.css](../../../../frontend/src/assets/main.css)) con variabili
  CSS dedicate `--app-btn-pdf-*` in
  [theme.css](../../../../frontend/src/assets/theme.css). Risolve
  internamente `sorgente_tipo_id` da `sorgenteCode` via
  `useGlobalLookup('config.sorgenti')` (cache modulo-level, 1 fetch
  per app session). Comportamento branched in base al numero di
  template applicabili: 0 -> toast warn, 1 -> POST genera diretto, >1
  -> apre dialog scelta. Prop `auto-download` per scaricare
  automaticamente il PDF dopo la generazione.
- [DONE] **Dialog scelta template**
  ([SceltaTemplateDocumentoDialog.vue](../../../../frontend/src/documenti/components/SceltaTemplateDocumentoDialog.vue)).
  `Listbox` PrimeVue con preselezione automatica del template
  `is_default=true` (riduce un click sull'happy path).
- [DONE] **Lista documenti generati per sorgente** building block
  riusabile
  ([DocumentiGeneratiSorgenteList.vue](../../../../frontend/src/documenti/components/DocumentiGeneratiSorgenteList.vue)).
  DataTable timeline `generato_at DESC` con `RowActionsMenu` per
  download. Riusabile da qualsiasi sorgente (PREVENTIVO, futuro
  CONTRATTO/ORDINE) tramite mappa `SORGENTE_CLIENT_MAP` nello store.
- [DONE] **API client riusabile**
  ([documenti/api/documentiPerSorgente.js](../../../../frontend/src/documenti/api/documentiPerSorgente.js))
  con factory `buildSorgenteClient(basePathFn)` per consentire ad
  altri domini sorgente di riutilizzare la stessa interfaccia senza
  duplicazione. v1 esporta `preventivoDocumenti`. Lookup template
  applicabili in
  [templateDocumentiLookup.js](../../../../frontend/src/documenti/api/templateDocumentiLookup.js).
- [DONE] **Store Pinia**
  ([documenti/stores/documentiPerSorgente.js](../../../../frontend/src/documenti/stores/documentiPerSorgente.js))
  scoped per coppia (sorgenteCode, sorgenteId), `userScoped: true`.
  Mappa `SORGENTE_CLIENT_MAP` per dispatch dinamico verso il client
  API del sorgente corrente. Helper `extractFileName` per RFC 5987
  Content-Disposition (axios espone `headers` come plain object).
- [DONE] **Helper download blob centralizzato**
  ([core/utils/download.js](../../../../frontend/src/core/utils/download.js)).
  `downloadBlob(blob, fileName)` standalone con revoke ritardato 1s
  (alcuni browser leggono il blob URL dopo `link.click()`). Riusato
  sia da `GeneraPdfButton.downloadDocumento` sia da
  `DocumentiGeneratiSorgenteList.onDownload` (no duplicazione).
- [DONE] **Integrazione** in
  [PreventiviDrawer.vue](../../../../frontend/src/vendite/preventivi/components/PreventiviDrawer.vue):
  pulsante visibile appena `hasDetail && detail.emittente_fiscale_id`
  (anche su readonly: il PDF e' una snapshot, non modifica il
  preventivo). Lista documenti sotto la sezione Integrazione, visibile
  in EDIT.
- [DONE] **BE: aggiunto `emittente_fiscale_id` alla proiezione
  `PreventiviRepository.get_preventivo`** per consentire al FE di
  costruire il pulsante senza un round-trip aggiuntivo. Suite BE
  invariata (578/578 vendite + documenti verde).
- [DONE] **i18n** `documenti.genera_pdf.*`, `documenti.scelta_template.*`,
  `documenti.lista.*` in `it.json` + `en.json`.
- [DONE] **Review critica fix applicati**:
  - 🔴 `URL.revokeObjectURL` immediato dopo click -> race con
    download stream su alcuni browser. Spostato in `setTimeout(...,
    1000)` (helper `downloadBlob`).
  - 🟡 `headers?.get?.()` dead code in `extractFileName`: axios
    espone `headers` come plain object, niente Headers API.
  - 🟡 `onMounted(() => {})` no-op rimosso da
    `DocumentiGeneratiSorgenteList`.
  - 🟡 Logica blob -> `<a>` -> click duplicata in 2 component:
    estratta in `core/utils/download.js`.
  - 🟢 Hardcoded `'application/pdf'` MIME e `'documento-${id}.pdf'`
    fallback filename: corretti per v1 (PDF e' l'unico tipo file
    seedato in `tipi_file_documento`).
- [DONE] Build `vite build` verde dopo refactor.

### 12.2 Tranche aperte (in attesa di partire)

Nessuna tranche aperta. Il motore documentale parametrico v1 e'
funzionalmente completo end-to-end (DB Fase A + BE Tranche A-K + FE
Tranche L-M).

### 12.3 Note per le prossime tranche

- L'invariante "INSERT eventi senza `tx_id` esplicito" si applica a
  qualsiasi codice BE che scrivera' su `documenti_generati_eventi` (vedi
  Decisione 76 — automation regola 4 popola la colonna). Atterrato in
  Tranche I via whitelist `EVENTO_DOCUMENTO_CREATE_COLUMNS` del repository.
- Il pattern transazionale di Tranche I (INSERT 3 record + `storage.write`
  dentro `transaction.atomic()` + cleanup post-fail commit) e' il modello
  di riferimento per qualsiasi nuova generazione persistita.
- Builder concreti (Tranche J) si registrano via import esplicito da
  `services/context_builders/registry.py` — niente auto-discovery via
  signal Django. La firma `build_context(sorgente_id: int, *,
  auth_user_id, locale)` resta come da `base.py`: l'orchestratore
  gestisce in input sia `sorgente_id: int` (passato al builder) sia
  `sorgente_uid: str` (scritto su `documenti_generati.sorgente_uid`).
- Tranche K (endpoint `genera`/`anteprima`/`download`) puo' invocare
  `DocumentGenerationService.genera_documento(...)` direttamente: la
  decodifica permessi del dominio sorgente va aggiunta a livello view,
  non duplicata in service (l'orchestratore applica gia' lo scope
  emittente generico).

---

*Sviluppo Documenti Parametrici — ZeroERP (WIP, aggiornato 2026-05-04)*
