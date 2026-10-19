{% include-markdown "it/dbzero/vendite/manual/resi_righe_rientri.md" %}
# 📚 Tabella `resi_righe_rientri`

> 📝 **Descrizione**
>
> I RIENTRI di una riga di reso: quanta merce di un prelievo della bolla d'origine rientra, e in quale ubicazione del magazzino del reso (D-3b-b). Il rientro non sceglie lotto ne' seriale: li ritrova dal prelievo (vendite.ddt_righe_prelievi), insieme all'articolo e al componente del kit — la merce che torna e' quella che era uscita. E' la SORGENTE del carico di magazzino (RESO_VENDITA_RIENTRO, D-3b-d): un rientro = un movimento CARICO_RESO_VEN, al costo dell'uscita d'origine. Dove non c'e' niente da scegliere (un solo prelievo, magazzino senza ubicazioni) il rientro lo crea da se' la conferma. Si scrive solo in bozza (trgfn_resi_righe_rientri_guard). Brief: brief-db-magazzino-lotto-3-bis-carico-da-reso.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| resi_riga_id | bigint | NO |  |
| ddt_riga_prelievo_id | bigint | NO |  |
| qta | numeric | NO |  |
| ubicazione_id | bigint | YES |  |
| meta | jsonb | NO | '{}'::jsonb |
| tx_id | uuid | YES |  |
| storicizza | boolean | NO | true |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_resi_righe_rientri_qta_finito |  |
| CHECK | chk_resi_righe_rientri_qta_positiva |  |
| FOREIGN KEY | fk_resi_righe_rientri_prelievo | ddt_riga_prelievo_id |
| FOREIGN KEY | fk_resi_righe_rientri_riga | resi_riga_id |
| FOREIGN KEY | fk_resi_righe_rientri_ubicazione | ubicazione_id |
| PRIMARY KEY | pk_resi_righe_rientri | id |
| UNIQUE | uq_resi_righe_rientri_posizione | resi_riga_id, ddt_riga_prelievo_id, ubicazione_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_resi_righe_rientri | `CREATE UNIQUE INDEX pk_resi_righe_rientri ON vendite.resi_righe_rientri USING btree (id)` |
| uq_resi_righe_rientri_posizione | `CREATE UNIQUE INDEX uq_resi_righe_rientri_posizione ON vendite.resi_righe_rientri USING btree (resi_riga_id, ddt_riga_prelievo_id, ubicazione_id) NULLS NOT DISTINCT` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_resi_righe_rientri_a05_doc_bozza_ins_upd_dlt | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_doc_righe_lock_fuori_bozza('RESO_VENDITA', 'resi_riga_id', 'DRAFT', 'RIGA')` |
| trg_resi_righe_rientri_a05_doc_bozza_ins_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_doc_righe_lock_fuori_bozza('RESO_VENDITA', 'resi_riga_id', 'DRAFT', 'RIGA')` |
| trg_resi_righe_rientri_a05_doc_bozza_ins_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION vendite.trgfn_doc_righe_lock_fuori_bozza('RESO_VENDITA', 'resi_riga_id', 'DRAFT', 'RIGA')` |
| trg_resi_righe_rientri_a10_guard_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_resi_righe_rientri_guard()` |
| trg_resi_righe_rientri_a10_guard_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_resi_righe_rientri_guard()` |
| trg_resi_righe_rientri_a10_resi_righe_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'resi_righe', 'attivo', 'resi_riga_id', 'id')` |
| trg_resi_righe_rientri_a10_resi_righe_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'resi_righe', 'attivo', 'resi_riga_id', 'id')` |
| trg_resi_righe_rientri_a10_ubicazioni_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('magazzino', 'ubicazioni', 'attivo', 'ubicazione_id', 'id')` |
| trg_resi_righe_rientri_a10_ubicazioni_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('magazzino', 'ubicazioni', 'attivo', 'ubicazione_id', 'id')` |
| trg_resi_righe_rientri_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_resi_righe_rientri_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_resi_righe_rientri_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_resi_righe_rientri_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_resi_righe_rientri_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('resi_righe_rientri_id')` |
| trg_resi_righe_rientri_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('resi_righe_rientri_id')` |

---
{% include-markdown "signature-core.md" %}
