# 📚 Tabella `esposizioni_componente`

> 📝 **Descrizione**
>
> Come si espone in fattura un componente di kit. NASCOSTO: non compare, il suo valore sta nel totale del kit. DESCRITTIVO: riga sotto il kit, senza prezzo ne' importo, il valore sta nel totale del kit. VALORIZZATO: riga sotto il kit con quantita', prezzo e importo suoi, FUORI dal totale del kit. Il componente resta sempre legato al suo kit, anche valorizzato. Letto da catalogo.articoli_componenti.esposizione_in_fattura (proprieta' della distinta) e congelato su vendite.fatture_righe.kit_esposizione; la regola la applica vendite.vw_fattura_righe_esposte, e il totale del documento non cambia mai al variare dell'esposizione. Niente attivo: i tre valori sono la semantica della vista, non una configurazione. Brief: brief-db-esposizione-componenti-kit-in-fattura.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| codice_interno | character varying(40) | NO |  |
| codice | character varying(40) | NO |  |
| descrizione | character varying(255) | YES |  |
| etichetta_key | character varying(120) | NO |  |
| ordine | smallint | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| tx_id | uuid | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_esposizioni_componente_codice_interno_non_vuoto |  |
| PRIMARY KEY | pk_esposizioni_componente | id |
| UNIQUE | uq_esposizioni_componente_codice | codice |
| UNIQUE | uq_esposizioni_componente_codice_interno | codice_interno |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_esposizioni_componente | `CREATE UNIQUE INDEX pk_esposizioni_componente ON config.esposizioni_componente USING btree (id)` |
| uq_esposizioni_componente_codice | `CREATE UNIQUE INDEX uq_esposizioni_componente_codice ON config.esposizioni_componente USING btree (codice)` |
| uq_esposizioni_componente_codice_interno | `CREATE UNIQUE INDEX uq_esposizioni_componente_codice_interno ON config.esposizioni_componente USING btree (codice_interno)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_esposizioni_componente_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('codice_interno', 'E_CODICE_NON_MODIFICABILE')` |
| trg_esposizioni_componente_a15_codice_maiuscolo_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_esposizioni_componente_a15_codice_maiuscolo_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_esposizioni_componente_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_esposizioni_componente_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_esposizioni_componente_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_esposizioni_componente_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
