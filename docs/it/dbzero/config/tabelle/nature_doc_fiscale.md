{% include-markdown "it/dbzero/config/manual/nature_doc_fiscale.md" %}
# 📚 Tabella `nature_doc_fiscale`

> 📝 **Descrizione**
>
> Natura fiscale del documento: FATTURA / NOTA_CREDITO / NOTA_DEBITO. E' un asse ORTOGONALE al canale, che vive in config.tipi_doc_fiscale (FRONTOFFICE/BACKOFFICE) ed e' una scelta configurabile dell'azienda (decisione di dominio 2026-06-19). La natura invece non e' una scelta: e' la legge, e domani e' il TipoDocumento della FatturaPA. ⚠️ Il vocabolario resta NEUTRO per dichiarazione del modello ("senza vincoli di specifico ordinamento nazionale"): il codice italiano vive in meta.sdi_tipo_documento come parametro di profilo nazionale, non come colonna. Se servira' un secondo profilo fiscale diventera' una tabella di mapping, non prima. Le tre righe sono bootstrappate inline dal changeSet che crea la tabella (ON CONFLICT DO NOTHING) perche' 80_data gira DOPO 00_schema e la colonna natura_doc_id NOT NULL DEFAULT FATTURA non troverebbe la riga da cui prendere il default: la SEDE dei valori resta comunque il CSV nature_doc_fiscale.csv, che ri-upserta e riallinea. Stesso pattern di config.esiti_flussi_pratiche. brief-design-note-credito-resi D-NC-3 e S12.4-bis. rev 2026-08-18.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| codice_interno | character varying | NO |  |
| codice | character varying | NO |  |
| descrizione | character varying | NO |  |
| attivo | boolean | NO | true |
| ordine | smallint | NO | 0 |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | k_nature_doc_fiscale_codice_interno_nonvuoto |  |
| CHECK | k_nature_doc_fiscale_codice_nonvuoto |  |
| PRIMARY KEY | pk_nature_doc_fiscale | id |
| UNIQUE | uq_nature_doc_fiscale_codice | codice |
| UNIQUE | uq_nature_doc_fiscale_codice_interno | codice_interno |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_nature_doc_fiscale | `CREATE UNIQUE INDEX pk_nature_doc_fiscale ON config.nature_doc_fiscale USING btree (id)` |
| uq_nature_doc_fiscale_codice | `CREATE UNIQUE INDEX uq_nature_doc_fiscale_codice ON config.nature_doc_fiscale USING btree (codice)` |
| uq_nature_doc_fiscale_codice_interno | `CREATE UNIQUE INDEX uq_nature_doc_fiscale_codice_interno ON config.nature_doc_fiscale USING btree (codice_interno)` |

---
{% include-markdown "signature-core.md" %}
