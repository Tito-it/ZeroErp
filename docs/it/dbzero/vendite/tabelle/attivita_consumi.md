{% include-markdown "it/dbzero/vendite/manual/attivita_consumi.md" %}
# 📚 Tabella `attivita_consumi`

> 📝 **Descrizione**
>
> WIP: testata consumi per utilities (gas/acqua/energia).

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| uid | uuid | NO | uuidv7() |
| fattura_id | bigint | YES |  |
| billing_account_id | bigint | NO |  |
| competenza_mese | date | NO |  |
| periodo_dal | date | YES |  |
| periodo_al | date | YES |  |
| consumo_totale | numeric(20,6) | YES |  |
| uom_id | bigint | YES |  |
| stato_calcolo | text | NO | 'OK'::text |
| meta | jsonb | NO | '{}'::jsonb |
| storicizza | boolean | NO | true |
| tx_id | uuid | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_attivita_consumi_consumo_totale_finito |  |
| CHECK | chk_attivita_consumi_stato_calcolo |  |
| FOREIGN KEY | fk_attivita_consumi_ba | billing_account_id |
| FOREIGN KEY | fk_attivita_consumi_fattura | fattura_id |
| FOREIGN KEY | fk_attivita_consumi_uom | uom_id |
| PRIMARY KEY | pk_attivita_consumi | id |
| UNIQUE | uq_attivita_consumi_uid | uid |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_attivita_consumi | `CREATE UNIQUE INDEX pk_attivita_consumi ON vendite.attivita_consumi USING btree (id)` |
| uq_attivita_consumi_uid | `CREATE UNIQUE INDEX uq_attivita_consumi_uid ON vendite.attivita_consumi USING btree (uid)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_attivita_consumi_a10_unita_misura_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'unita_misura', 'attivo', 'uom_id', 'id')` |
| trg_attivita_consumi_a10_unita_misura_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'unita_misura', 'attivo', 'uom_id', 'id')` |
| trg_attivita_consumi_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_attivita_consumi_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_attivita_consumi_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_attivita_consumi_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_attivita_consumi_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('attivita_consumi_id')` |
| trg_attivita_consumi_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('attivita_consumi_id')` |
| trg_vendite_attivita_consumi_a10_sorgente_in_uscita_dlt | AFTER | DELETE | `EXECUTE FUNCTION script.trgfn_sorgente_in_uscita()` |

---
{% include-markdown "signature-core.md" %}
