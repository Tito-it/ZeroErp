{% include-markdown "it/dbzero/vendite/manual/fatture_stampa_coda.md" %}
# 📚 Tabella `fatture_stampa_coda`

> 📝 **Descrizione**
>
> Outbox della stampa massiva fatture: un work-item per fattura, accodato dal task pipeline stampa_documenti_lotto e drenato da worker esterno (backstop numerazione + render via documenti.DocumentGenerationService). Satellite di vendite.fatture.

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
| archiviato | boolean | NO | false |
| archiviato_il | timestamp with time zone | YES |  |
| archiviato_da | text | YES |  |
| tipo_documento_output_id | bigint | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_fatture_stampa_coda_archiviato_coerente |  |
| CHECK | chk_fatture_stampa_coda_archiviato_non_vivo |  |
| CHECK | chk_fatture_stampa_coda_modello_con_tipo |  |
| CHECK | chk_fatture_stampa_coda_stato |  |
| CHECK | chk_fatture_stampa_coda_tentativi |  |
| FOREIGN KEY | fk_fatture_stampa_coda_fattura | sorgente_id |
| FOREIGN KEY | fk_fatture_stampa_coda_lotto | lotto_id |
| FOREIGN KEY | fk_fatture_stampa_coda_template_documento | template_documento_id, tipo_documento_output_id, sorgente_tipo_id |
| FOREIGN KEY | fk_fatture_stampa_coda_tipo_documento_output | tipo_documento_output_id |
| PRIMARY KEY | pk_fatture_stampa_coda | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ex_fatture_stampa_coda_vivo | `CREATE INDEX ex_fatture_stampa_coda_vivo ON vendite.fatture_stampa_coda USING gist (sorgente_tipo_id, sorgente_id, int8range(tipo_documento_output_id, tipo_documento_output_id, '[]'::text)) WHERE (stato = ANY (ARRAY['PENDING'::text, 'IN_CORSO'::text]))` |
| ix_fatture_stampa_coda_da_lavorare | `CREATE INDEX ix_fatture_stampa_coda_da_lavorare ON vendite.fatture_stampa_coda USING btree (id) WHERE (stato = ANY (ARRAY['PENDING'::text, 'IN_CORSO'::text]))` |
| ix_fatture_stampa_coda_lotto_id | `CREATE INDEX ix_fatture_stampa_coda_lotto_id ON vendite.fatture_stampa_coda USING btree (lotto_id)` |
| ix_fatture_stampa_coda_sorgente_id | `CREATE INDEX ix_fatture_stampa_coda_sorgente_id ON vendite.fatture_stampa_coda USING btree (sorgente_id)` |
| pk_fatture_stampa_coda | `CREATE UNIQUE INDEX pk_fatture_stampa_coda ON vendite.fatture_stampa_coda USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_fatture_stampa_coda_a10_archiviazione_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_coda_archiviazione()` |
| trg_fatture_stampa_coda_a10_guard_emittente_scope_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_guard_emittente_scope('fattura', 'sorgente_id')` |
| trg_fatture_stampa_coda_a10_guard_emittente_scope_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_guard_emittente_scope('fattura', 'sorgente_id')` |
| trg_fatture_stampa_coda_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_fatture_stampa_coda_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_fatture_stampa_coda_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_fatture_stampa_coda_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
