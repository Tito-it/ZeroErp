{% include-markdown "it/dbzero/config/manual/regimi_fiscali.md" %}
# 📚 Tabella `regimi_fiscali`

> 📝 **Descrizione**
>
> Il vocabolario del regime fiscale di un emittente: i codici RegimeFiscale del tracciato FatturaPA (RF01 ordinario, RF17 IVA per cassa, RF19 forfettario...). Letto da anagrafiche.emittenti_fiscali.regime_fiscale_rf, FK su codice_interno (D-9). Il codice e' del tracciato e il SIGNIFICATO sta nelle colonne: la regola dell'esigibilita' (script.fn_esigibilita_iva) legge iva_per_cassa, mai un letterale RF (D-10, stesso stampo di config.iva_natura.is_reverse_charge). Un codice che esce dal tracciato si spegne con attivo = false, non si cancella. Brief: brief-db-esigibilita-iva-per-cassa-emittente.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| codice_interno | character varying(40) | NO |  |
| codice | character varying(40) | NO |  |
| descrizione | character varying(255) | NO |  |
| iva_per_cassa | boolean | NO | false |
| annotazione_documento | text | YES |  |
| attivo | boolean | NO | true |
| ordine | smallint | YES |  |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| tx_id | uuid | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_regimi_fiscali_annotazione_non_vuota |  |
| CHECK | chk_regimi_fiscali_codice_interno_forma |  |
| CHECK | chk_regimi_fiscali_descrizione_non_vuota |  |
| CHECK | chk_regimi_fiscali_per_cassa_annotazione |  |
| PRIMARY KEY | pk_regimi_fiscali | id |
| UNIQUE | uq_regimi_fiscali_codice | codice |
| UNIQUE | uq_regimi_fiscali_codice_interno | codice_interno |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_regimi_fiscali | `CREATE UNIQUE INDEX pk_regimi_fiscali ON config.regimi_fiscali USING btree (id)` |
| uq_regimi_fiscali_codice | `CREATE UNIQUE INDEX uq_regimi_fiscali_codice ON config.regimi_fiscali USING btree (codice)` |
| uq_regimi_fiscali_codice_interno | `CREATE UNIQUE INDEX uq_regimi_fiscali_codice_interno ON config.regimi_fiscali USING btree (codice_interno)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_regimi_fiscali_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('codice_interno', 'E_CODICE_NON_MODIFICABILE')` |
| trg_regimi_fiscali_a15_codice_maiuscolo_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_regimi_fiscali_a15_codice_maiuscolo_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_regimi_fiscali_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_regimi_fiscali_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_regimi_fiscali_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_regimi_fiscali_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
