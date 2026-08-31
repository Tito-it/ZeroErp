{% include-markdown "it/dbzero/vendite/manual/fatture_atti.md" %}
# 📚 Tabella `fatture_atti`

> 📝 **Descrizione**
>
> Snapshot dei RIFERIMENTI DELL'ATTO per fattura: una riga per (fattura, contratto). ⭐ UNA RIGA E' UN BLOCCO `DatiContratto` della FatturaPA, non ci assomiglia: quel blocco e' ripetibile 0..N dentro DatiGenerali e porta `RiferimentoNumeroLinea`, cioe' l'elenco delle righe a cui si riferisce. Una fattura con righe di due contratti produce DUE blocchi, quindi ne' la testata ne' una colonna di riga reggono il caso. Le righe si agganciano da vendite.fatture_righe.fattura_atto_id, e il generatore XML diventa una SELECT invece di un GROUP BY su testo — che e' la forma scartata, perche' due atti con lo stesso codice e date diverse si fondono o si spezzano a seconda del raggruppamento e nessun vincolo se ne accorge. ⭐ Il pattern non e' nuovo: vendite.fatture_riepiloghi_iva e' gia' un satellite che aggrega righe per produrre un blocco XML (DatiRiepilogo). ⛔ LE COLONNE SONO UNO SNAPSHOT, NON UN JOIN: un CIG corretto domani in anagrafica NON deve cambiare su una fattura gia' emessa. `contratto_id` esiste per il LINEAGE — chi stampa legge sempre le colonne snapshottate. ⚠️ Nessuna policy RLS: il cancello e' la TESTATA, come per fatture_righe e fatture_riepiloghi_iva; chi legge parte da vendite.fatture, sempre. ⚠️ Protetta dal congelamento fiscale da trg_fatture_atti_a10_guard_congelamento_ins_upd_dlt (20260831-28), che monta la guardia parametrica dei satelliti. ⭐ storicizza SPENTO di default come fatture_righe: questa tabella si RIFA' a ogni rigenerazione del lotto e si congela con la fattura, quindi la sua storia sarebbe rumore; il tx_id invece c'e', perche' registra che queste righe nascono nella stessa scrittura delle righe di fattura. brief-db-fatture-atti-riferimenti-contratto.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| fattura_id | bigint | NO |  |
| contratto_id | bigint | NO |  |
| id_documento | character varying | NO |  |
| data_documento | date | NO |  |
| codice_cig | character varying | YES |  |
| codice_cup | character varying | YES |  |
| codice_commessa | character varying | YES |  |
| storicizza | boolean | NO | false |
| tx_id | uuid | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | YES | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_fatture_atti_contratto | contratto_id |
| FOREIGN KEY | fk_fatture_atti_fattura | fattura_id |
| PRIMARY KEY | pk_fatture_atti | id |
| UNIQUE | uq_fatture_atti_fattura_contratto | fattura_id, contratto_id |
| UNIQUE | uq_fatture_atti_id_fattura | id, fattura_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_fatture_atti_contratto_id | `CREATE INDEX ix_fatture_atti_contratto_id ON vendite.fatture_atti USING btree (contratto_id)` |
| pk_fatture_atti | `CREATE UNIQUE INDEX pk_fatture_atti ON vendite.fatture_atti USING btree (id)` |
| uq_fatture_atti_fattura_contratto | `CREATE UNIQUE INDEX uq_fatture_atti_fattura_contratto ON vendite.fatture_atti USING btree (fattura_id, contratto_id)` |
| uq_fatture_atti_id_fattura | `CREATE UNIQUE INDEX uq_fatture_atti_id_fattura ON vendite.fatture_atti USING btree (id, fattura_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_fatture_atti_a10_guard_congelamento_ins_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_fattura_satellite_guard_congelamento('fattura_id')` |
| trg_fatture_atti_a10_guard_congelamento_ins_upd_dlt | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_fattura_satellite_guard_congelamento('fattura_id')` |
| trg_fatture_atti_a10_guard_congelamento_ins_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION vendite.trgfn_fattura_satellite_guard_congelamento('fattura_id')` |
| trg_fatture_atti_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_fatture_atti_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_fatture_atti_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_fatture_atti_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
