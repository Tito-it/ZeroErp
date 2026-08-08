# 📚 Tabella `inventari_righe`

> 📝 **Descrizione**
>
> Conteggi fisici di inventario

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| inventario_id | bigint | NO |  |
| articolo_id | uuid | NO |  |
| lotto | character varying | YES |  |
| seriale | character varying | YES |  |
| qta_contata | numeric | NO |  |
| qta_sistema | numeric | YES |  |
| meta | jsonb | NO | '{}'::jsonb |
| storicizza | boolean | NO | true |
| tx_id | uuid | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | YES | CURRENT_USER |
| ubicazione_id | bigint | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_mag_inventario_righe_qta_contata_non_neg |  |
| FOREIGN KEY | fk_mag_inventari_righe_ubicazione | ubicazione_id |
| FOREIGN KEY | fk_mag_inventario_righe_articolo | articolo_id |
| FOREIGN KEY | fk_mag_inventario_righe_testata | inventario_id |
| PRIMARY KEY | pk_mag_invetario_righe | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_magazzino_inventari_righe_articolo_id | `CREATE INDEX ix_magazzino_inventari_righe_articolo_id ON magazzino.inventari_righe USING btree (articolo_id)` |
| ix_magazzino_inventari_righe_ubicazione_id | `CREATE INDEX ix_magazzino_inventari_righe_ubicazione_id ON magazzino.inventari_righe USING btree (ubicazione_id)` |
| pk_mag_invetario_righe | `CREATE UNIQUE INDEX pk_mag_invetario_righe ON magazzino.inventari_righe USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_inventari_righe_a10_articoli_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'articoli', 'attivo', 'articolo_id', 'id')` |
| trg_inventari_righe_a10_articoli_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'articoli', 'attivo', 'articolo_id', 'id')` |
| trg_inventari_righe_a10_ubicazioni_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('magazzino', 'ubicazioni', 'attivo', 'ubicazione_id', 'id')` |
| trg_inventari_righe_a10_ubicazioni_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('magazzino', 'ubicazioni', 'attivo', 'ubicazione_id', 'id')` |
| trg_inventari_righe_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_inventari_righe_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_inventari_righe_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_inventari_righe_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_inventari_righe_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('inventari_righe_id')` |
| trg_inventari_righe_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('inventari_righe_id')` |

---
{% include-markdown "signature-core.md" %}
