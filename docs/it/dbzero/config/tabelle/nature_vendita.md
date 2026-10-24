{% include-markdown "it/dbzero/config/manual/nature_vendita.md" %}
# 📚 Tabella `nature_vendita`

> 📝 **Descrizione**
>
> Natura commerciale di riga ai fini del routing post-accettazione del preventivo (anello3 §5.3.2). Proprieta' intrinseca dell'articolo (catalogo.articoli.natura_vendita_id), ereditata e congelata sulla riga di preventivo. destinazione_tipo guida lo split: ogni riga finisce nella destinazione operativa della sua natura.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| codice_interno | character varying(40) | NO |  |
| codice | character varying(40) | NO |  |
| descrizione | character varying(255) | YES |  |
| destinazione_tipo | character varying(50) | NO |  |
| attivo | boolean | NO | true |
| ordine | smallint | YES |  |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| e_cessione_beni | boolean | NO |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_nature_vendita_destinazione_tipo_sorgenti | destinazione_tipo |
| PRIMARY KEY | pk_nature_vendita | id |
| UNIQUE | uq_nature_vendita_codice | codice |
| UNIQUE | uq_nature_vendita_codice_interno | codice_interno |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_nature_vendita | `CREATE UNIQUE INDEX pk_nature_vendita ON config.nature_vendita USING btree (id)` |
| uq_nature_vendita_codice | `CREATE UNIQUE INDEX uq_nature_vendita_codice ON config.nature_vendita USING btree (codice)` |
| uq_nature_vendita_codice_interno | `CREATE UNIQUE INDEX uq_nature_vendita_codice_interno ON config.nature_vendita USING btree (codice_interno)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_nature_vendita_a10_articoli_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('catalogo', 'articoli', 'natura_vendita_id', 'id', 'attivo')` |
| trg_nature_vendita_a10_ddt_righe_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'ddt_righe', 'natura_vendita_id', 'id', 'attivo')` |
| trg_nature_vendita_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('codice_interno', 'E_CODICE_NON_MODIFICABILE')` |
| trg_nature_vendita_a10_nature_vendita_erogazioni_block_d_52fac6 | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('config', 'nature_vendita_erogazioni', 'natura_vendita_id', 'id', 'attivo')` |
| trg_nature_vendita_a10_ordini_righe_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'ordini_righe', 'natura_vendita_id', 'id', 'attivo')` |
| trg_nature_vendita_a10_preventivi_righe_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'preventivi_righe', 'natura_vendita_id', 'id', 'attivo')` |
| trg_nature_vendita_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_nature_vendita_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
