# 📚 Tabella `fatture_stampa_coda`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| sorgente_tipo_id | bigint | NO |  |
| sorgente_id | bigint | NO |  |
| sorgente_uid | text | NO |  |
| lotto_id | bigint | YES |  |
| template_documento_id | bigint | YES |  |
| stato | text | NO | 'PENDING'::text |
| tentativi | integer | NO | 0 |
| ultimo_errore | jsonb | YES |  |
| documento_id | bigint | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| tx_id | uuid | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_fatture_stampa_coda_stato |  |
| CHECK | chk_fatture_stampa_coda_tentativi |  |
| FOREIGN KEY | fk_fatture_stampa_coda_fattura | sorgente_id |
| FOREIGN KEY | fk_fatture_stampa_coda_lotto | lotto_id |
| PRIMARY KEY | pk_fatture_stampa_coda | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_fatture_stampa_coda_da_lavorare | `CREATE INDEX ix_fatture_stampa_coda_da_lavorare ON vendite.fatture_stampa_coda USING btree (id) WHERE (stato = ANY (ARRAY['PENDING'::text, 'IN_CORSO'::text]))` |
| pk_fatture_stampa_coda | `CREATE UNIQUE INDEX pk_fatture_stampa_coda ON vendite.fatture_stampa_coda USING btree (id)` |
| uq_fatture_stampa_coda_vivo | `CREATE UNIQUE INDEX uq_fatture_stampa_coda_vivo ON vendite.fatture_stampa_coda USING btree (sorgente_tipo_id, sorgente_id) WHERE (stato = ANY (ARRAY['PENDING'::text, 'IN_CORSO'::text]))` |

---
{% include-markdown "signature-core.md" %}
