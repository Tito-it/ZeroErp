{% include-markdown "it/dbzero/catalogo/manual/articoli.md" %}
# 📚 Tabella `articoli`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | uuid | NO | gen_random_uuid() |
| codice | character varying | NO |  |
| descrizione | character varying | NO |  |
| descrizione_breve | character varying | YES |  |
| uom_id | bigint | YES |  |
| tipo_voce_id | bigint | YES |  |
| gruppo_voce_id | bigint | YES |  |
| spesa_id | bigint | YES |  |
| iva_id | bigint | YES |  |
| conto_contabile_vendita_id | bigint | YES |  |
| conto_contabile_acquisto_id | bigint | YES |  |
| is_composito | boolean | NO | false |
| requires_serial | boolean | NO | false |
| voce_utility | boolean | NO | false |
| fondo_fattura | boolean | NO | false |
| meta | jsonb | YES | '{}'::jsonb |
| user_insert | character varying | NO | CURRENT_USER |
| user_update | character varying | YES | CURRENT_USER |
| data_insert | timestamp with time zone | NO | now() |
| data_update | timestamp with time zone | NO | now() |
| tx_id | uuid | YES |  |
| storicizza | boolean | YES | true |
| attivo | boolean | NO | true |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_articoli_articoli_gruppi | gruppo_voce_id |
| FOREIGN KEY | fk_articoli_articoli_spesa | spesa_id |
| FOREIGN KEY | fk_articoli_articoli_tipologie | tipo_voce_id |
| FOREIGN KEY | fk_articoli_conti_contabili_acquisto | conto_contabile_acquisto_id |
| FOREIGN KEY | fk_articoli_conti_contabili_vendita | conto_contabile_vendita_id |
| FOREIGN KEY | fk_articoli_iva | iva_id |
| FOREIGN KEY | fk_articoli_unita_misura | uom_id |
| PRIMARY KEY | pk_articoli | id |
| UNIQUE | uq_articoli_codice | codice |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_articoli_codice_upper | `CREATE INDEX ix_articoli_codice_upper ON catalogo.articoli USING btree (upper((codice)::text))` |
| pk_articoli | `CREATE UNIQUE INDEX pk_articoli ON catalogo.articoli USING btree (id)` |
| uq_articoli_codice | `CREATE UNIQUE INDEX uq_articoli_codice ON catalogo.articoli USING btree (codice)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_a10_articoli_upd_protect_codice | BEFORE | UPDATE | `EXECUTE FUNCTION catalogo.trgfn_articoli_upd_protect_codice()` |
| trg_articoli_ins_upd_gen_tx_id | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_articoli_ins_upd_gen_tx_id | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_block_deact_articoli_attivita_fatturabili | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'attivita_fatturabili', 'articolo_id')` |
| trg_block_deact_articoli_regole_fatturazione_articolo | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'regole_fatturazione_articolo', 'prodotto_id')` |
| trg_chk_articoli_parent_fk_articoli_articoli_gruppi | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'articoli_gruppi', 'attivo', 'gruppo_voce_id')` |
| trg_chk_articoli_parent_fk_articoli_articoli_gruppi | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'articoli_gruppi', 'attivo', 'gruppo_voce_id')` |
| trg_chk_articoli_parent_fk_articoli_articoli_spesa | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'articoli_spesa', 'attivo', 'spesa_id')` |
| trg_chk_articoli_parent_fk_articoli_articoli_spesa | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'articoli_spesa', 'attivo', 'spesa_id')` |
| trg_chk_articoli_parent_fk_articoli_articoli_tipologie | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'articoli_tipologie', 'attivo', 'tipo_voce_id')` |
| trg_chk_articoli_parent_fk_articoli_articoli_tipologie | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'articoli_tipologie', 'attivo', 'tipo_voce_id')` |
| trg_chk_articoli_parent_fk_articoli_unita_misura | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'unita_misura', 'attivo', 'uom_id')` |
| trg_chk_articoli_parent_fk_articoli_unita_misura | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'unita_misura', 'attivo', 'uom_id')` |
| trg_soft_del_articoli_articoli_componenti_fk_articoli_co_126924 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_soft_delete_cascade('catalogo', 'articoli_componenti', 'prodotto_id')` |
| trg_soft_del_articoli_articoli_componenti_fk_articoli_co_9b0295 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_soft_delete_cascade('catalogo', 'articoli_componenti', 'componente_id')` |
| trg_soft_del_articoli_articoli_descrizioni_aggiuntive_fk_dbb354 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_soft_delete_cascade('vendite', 'articoli_descrizioni_aggiuntive', 'articolo_id')` |
| trg_soft_del_articoli_contratti_righe_fk_contrighe_articoli | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_soft_delete_cascade('vendite', 'contratti_righe', 'articolo_id')` |
| trg_soft_del_articoli_preventivi_righe_fk_prevrighe_articoli | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_soft_delete_cascade('vendite', 'preventivi_righe', 'articolo_id')` |
| trg_upd_articoli_audit_data_user | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_upd_audit_data_user_generic()` |
| trg_z90_articoli_upd_dlt_storico | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_upd_dlt_storico_generic('articoli_id')` |
| trg_z90_articoli_upd_dlt_storico | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_upd_dlt_storico_generic('articoli_id')` |

---
{% include-markdown "signature-core.md" %}
