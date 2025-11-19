{% include-markdown "it/dbzero/anagrafiche/manual/dati_catastali.md" %}
# 📚 Tabella `dati_catastali`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| indirizzo_dettaglio_id | integer | NO |  |
| sezione_catastale | character | YES |  |
| foglio_catastale | character | YES |  |
| particella | character | YES |  |
| subalterno | character | YES |  |
| categoria_catastale | character varying | YES |  |
| classe_catastale | character varying | YES |  |
| rendita_catastale | numeric | YES |  |
| consistenza | integer | YES |  |
| tipo_accatastamento | character | YES |  |
| immobile_rurale | boolean | NO | false |
| destinazione_immobile | character | YES |  |
| anno_protocollo | integer | YES |  |
| superficie | integer | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | character varying | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | character varying | NO | CURRENT_USER |
| tx_id | uuid | YES |  |
| storicizza | boolean | NO | true |
| istanza_utility_id | integer | NO |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_dati_catastali_istanze_utilities | istanza_utility_id |
| FOREIGN KEY | fk_dettaglio_catastali_indirizzi_dettaglio | indirizzo_dettaglio_id |
| PRIMARY KEY | dati_catastali_pkey | id |
| UNIQUE | uq_dati_catastali_indirizzo_istanza | indirizzo_dettaglio_id, istanza_utility_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| dati_catastali_pkey | `CREATE UNIQUE INDEX dati_catastali_pkey ON anagrafiche.dati_catastali USING btree (id)` |
| uq_dati_catastali_indirizzo_istanza | `CREATE UNIQUE INDEX uq_dati_catastali_indirizzo_istanza ON anagrafiche.dati_catastali USING btree (indirizzo_dettaglio_id, istanza_utility_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_dati_catastali_audit_data_user_generic_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_upd_audit_data_user_generic()` |
| trg_dati_catastali_tx_id_managed_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_dati_catastali_tx_id_managed_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_dati_catastali_z90_storico_generic_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_upd_dlt_storico_generic('dato_catastale_id')` |
| trg_dati_catastali_z90_storico_generic_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_upd_dlt_storico_generic('dato_catastale_id')` |

---
{% include-markdown "signature-core.md" %}
