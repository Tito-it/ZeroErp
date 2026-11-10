# 📚 Tabella `ddt_righe_prelievi`

> 📝 **Descrizione**
>
> I PRELIEVI di una riga di bolla: quanta merce esce da quale lotto, seriale e ubicazione (D-L3-b). La riga e' l'unita' commerciale, il prelievo quella fisica. E' la SORGENTE del movimento di magazzino (DDT_VENDITA_PRELIEVO, D-L3-d): un prelievo = uno scarico (due per la bolla di trasferimento, OUT e IN). Se la riga e' un kit con padre non gestito, a muoversi sono i componenti gestiti e il prelievo nomina il componente (D-L3-f). Per la merce semplice (niente lotto, seriale ne' ubicazioni) il prelievo lo crea da se' il verbo all'emissione. Si scrive solo in bozza (trgfn_ddt_righe_prelievi_guard), salvo ubicazione_arrivo_id di una bolla di trasferimento. Brief: brief-db-magazzino-lotto-3-scarico-da-ddt.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| ddt_riga_id | bigint | NO |  |
| ddt_riga_componente_id | bigint | YES |  |
| qta | numeric | NO |  |
| lotto_id | bigint | YES |  |
| asset_id | bigint | YES |  |
| ubicazione_id | bigint | YES |  |
| ubicazione_arrivo_id | bigint | YES |  |
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
| CHECK | chk_ddt_righe_prelievi_asset_qta_unitaria |  |
| CHECK | chk_ddt_righe_prelievi_qta_finito |  |
| CHECK | chk_ddt_righe_prelievi_qta_positiva |  |
| FOREIGN KEY | fk_ddt_righe_prelievi_asset | asset_id |
| FOREIGN KEY | fk_ddt_righe_prelievi_componente | ddt_riga_componente_id |
| FOREIGN KEY | fk_ddt_righe_prelievi_lotto | lotto_id |
| FOREIGN KEY | fk_ddt_righe_prelievi_riga | ddt_riga_id |
| FOREIGN KEY | fk_ddt_righe_prelievi_ubicazione | ubicazione_id |
| FOREIGN KEY | fk_ddt_righe_prelievi_ubicazione_arrivo | ubicazione_arrivo_id |
| PRIMARY KEY | pk_ddt_righe_prelievi | id |
| UNIQUE | uq_ddt_righe_prelievi_posizione | ddt_riga_id, ddt_riga_componente_id, lotto_id, asset_id, ubicazione_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_ddt_righe_prelievi | `CREATE UNIQUE INDEX pk_ddt_righe_prelievi ON vendite.ddt_righe_prelievi USING btree (id)` |
| uq_ddt_righe_prelievi_posizione | `CREATE UNIQUE INDEX uq_ddt_righe_prelievi_posizione ON vendite.ddt_righe_prelievi USING btree (ddt_riga_id, ddt_riga_componente_id, lotto_id, asset_id, ubicazione_id) NULLS NOT DISTINCT` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_ddt_righe_prelievi_a05_doc_bozza_ins_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_doc_righe_lock_fuori_bozza('DDT_VENDITA', 'ddt_riga_id', 'DRAFT', 'RIGA', 'ubicazione_arrivo_id', 'EMESSO,SPEDITO')` |
| trg_ddt_righe_prelievi_a05_doc_bozza_ins_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION vendite.trgfn_doc_righe_lock_fuori_bozza('DDT_VENDITA', 'ddt_riga_id', 'DRAFT', 'RIGA', 'ubicazione_arrivo_id', 'EMESSO,SPEDITO')` |
| trg_ddt_righe_prelievi_a05_doc_bozza_ins_upd_dlt | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_doc_righe_lock_fuori_bozza('DDT_VENDITA', 'ddt_riga_id', 'DRAFT', 'RIGA', 'ubicazione_arrivo_id', 'EMESSO,SPEDITO')` |
| trg_ddt_righe_prelievi_a05_guard_ins_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION vendite.trgfn_ddt_righe_prelievi_guard()` |
| trg_ddt_righe_prelievi_a05_guard_ins_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_ddt_righe_prelievi_guard()` |
| trg_ddt_righe_prelievi_a05_guard_ins_upd_dlt | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_ddt_righe_prelievi_guard()` |
| trg_ddt_righe_prelievi_a10_assets_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('magazzino', 'assets', 'attivo', 'asset_id', 'id')` |
| trg_ddt_righe_prelievi_a10_assets_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('magazzino', 'assets', 'attivo', 'asset_id', 'id')` |
| trg_ddt_righe_prelievi_a10_ddt_righe_componenti_require_93f6e8 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'ddt_righe_componenti', 'attivo', 'ddt_riga_componente_id', 'id')` |
| trg_ddt_righe_prelievi_a10_ddt_righe_componenti_require_93f6e8 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'ddt_righe_componenti', 'attivo', 'ddt_riga_componente_id', 'id')` |
| trg_ddt_righe_prelievi_a10_ddt_righe_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'ddt_righe', 'attivo', 'ddt_riga_id', 'id')` |
| trg_ddt_righe_prelievi_a10_ddt_righe_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'ddt_righe', 'attivo', 'ddt_riga_id', 'id')` |
| trg_ddt_righe_prelievi_a10_lotti_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('magazzino', 'lotti', 'attivo', 'lotto_id', 'id')` |
| trg_ddt_righe_prelievi_a10_lotti_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('magazzino', 'lotti', 'attivo', 'lotto_id', 'id')` |
| trg_ddt_righe_prelievi_a10_ubicazioni_require_attivo_ins_708662 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('magazzino', 'ubicazioni', 'attivo', 'ubicazione_id', 'id')` |
| trg_ddt_righe_prelievi_a10_ubicazioni_require_attivo_ins_708662 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('magazzino', 'ubicazioni', 'attivo', 'ubicazione_id', 'id')` |
| trg_ddt_righe_prelievi_a10_ubicazioni_require_attivo_ins_b9ef73 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('magazzino', 'ubicazioni', 'attivo', 'ubicazione_arrivo_id', 'id')` |
| trg_ddt_righe_prelievi_a10_ubicazioni_require_attivo_ins_b9ef73 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('magazzino', 'ubicazioni', 'attivo', 'ubicazione_arrivo_id', 'id')` |
| trg_ddt_righe_prelievi_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_ddt_righe_prelievi_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_ddt_righe_prelievi_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_ddt_righe_prelievi_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_ddt_righe_prelievi_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('ddt_righe_prelievi_id')` |
| trg_ddt_righe_prelievi_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('ddt_righe_prelievi_id')` |
| trg_vendite_ddt_righe_prelievi_a10_sorgente_in_uscita_dlt | AFTER | DELETE | `EXECUTE FUNCTION script.trgfn_sorgente_in_uscita()` |

---
{% include-markdown "signature-core.md" %}
