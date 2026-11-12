{% include-markdown "it/dbzero/magazzino/manual/causali.md" %}
# 📚 Tabella `causali`

> 📝 **Descrizione**
>
> Catalogo delle causali di movimento: il VERSO (segno), se e' una rettifica, se ammette stock negativo. Dal 2026-09-15 non porta piu' ne' regole di valorizzazione (la valorizzazione e' una, M-4) ne' gli obblighi di lotto/seriale (li dice l'articolo, M-5) ne' un ambito (D-8): la primitiva di scrittura e' guidata da due cataloghi, la causale e l'articolo. Vocabolario, uguale per tutti gli emittenti: fuori dal perimetro RLS. Brief: brief-db-magazzino-lotto-1-terreno-vuoto, sezione 4.1.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| codice | character varying(32) | NO |  |
| descrizione | character varying(255) | NO |  |
| segno | smallint | NO |  |
| ordine | smallint | NO | 0 |
| attivo | boolean | NO | true |
| meta | jsonb | YES | '{}'::jsonb |
| tx_id | uuid | YES |  |
| user_insert | text | NO | CURRENT_USER |
| user_update | text | NO | CURRENT_USER |
| data_insert | timestamp with time zone | NO | now() |
| data_update | timestamp with time zone | YES |  |
| storicizza | boolean | NO | false |
| is_installazione_asset | boolean | NO | false |
| is_rettifica | boolean | NO | false |
| consente_stock_negativo | boolean | NO | false |
| codice_interno | character varying(32) | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_mag_causali_codice_interno_nonvuoto |  |
| CHECK | chk_magazzino_causali_segno |  |
| PRIMARY KEY | pk_magazzino_causali | id |
| UNIQUE | uq_mag_causali_codice_interno | codice_interno |
| UNIQUE | uq_magazzino_causali_codice | codice |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_magazzino_causali_attivo | `CREATE INDEX ix_magazzino_causali_attivo ON magazzino.causali USING btree (attivo)` |
| pk_magazzino_causali | `CREATE UNIQUE INDEX pk_magazzino_causali ON magazzino.causali USING btree (id)` |
| uq_mag_causali_codice_interno | `CREATE UNIQUE INDEX uq_mag_causali_codice_interno ON magazzino.causali USING btree (codice_interno)` |
| uq_magazzino_causali_codice | `CREATE UNIQUE INDEX uq_magazzino_causali_codice ON magazzino.causali USING btree (codice)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_causali_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('codice_interno', 'E_CODICE_NON_MODIFICABILE')` |
| trg_causali_a10_movimenti_attesi_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('magazzino', 'movimenti_attesi', 'causale_id', 'id', 'attivo')` |
| trg_causali_a10_movimenti_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('magazzino', 'movimenti', 'causale_id', 'id', 'attivo')` |
| trg_causali_a15_codice_maiuscolo_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_causali_a15_codice_maiuscolo_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_causali_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_causali_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_causali_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_causali_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_causali_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('causali_id')` |
| trg_causali_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('causali_id')` |

---
{% include-markdown "signature-core.md" %}
