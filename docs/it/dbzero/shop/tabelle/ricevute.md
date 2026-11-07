{% include-markdown "it/dbzero/shop/manual/ricevute.md" %}
# 📚 Tabella `ricevute`

> 📝 **Descrizione**
>
> Ricevute consumer emesse dal canale shop B2C. Documento fiscale leggero (no SdI, no XML, no partita IVA emittente sul doc). Decisione dominio 20-04-2026: shop e' canale B2C autonomo. BA collegato deve avere canale_origine=SHOP (verifica service-side). Numerazione dedicata, generata lato service shop.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | uuid | NO | uuidv7() |
| numero | character varying(40) | NO |  |
| data_emissione | date | NO | script.fn_data_operativa() |
| soggetto_ruolo_id | bigint | NO |  |
| billing_account_id | bigint | NO |  |
| ordine_shop_id | bigint | YES |  |
| totale_lordo | numeric(15,2) | NO |  |
| totale_iva | numeric(15,2) | NO | 0 |
| pagamento_metodo | character varying(40) | NO |  |
| pagamento_esito | character varying(20) | NO | 'PENDING'::character varying |
| canale_origine | config.canale_origine | NO | 'SHOP'::config.canale_origine |
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
| CHECK | chk_ricevute_totale_iva_finito |  |
| CHECK | chk_ricevute_totale_lordo_finito |  |
| CHECK | chk_shop_ricevute_canale_shop |  |
| CHECK | chk_shop_ricevute_pagamento_esito |  |
| CHECK | chk_shop_ricevute_totali_non_neg |  |
| FOREIGN KEY | fk_shop_ricevute_billing_account | billing_account_id |
| FOREIGN KEY | fk_shop_ricevute_ordini | ordine_shop_id |
| FOREIGN KEY | fk_shop_ricevute_soggetti_ruoli | soggetto_ruolo_id |
| PRIMARY KEY | pk_shop_ricevute | id |
| UNIQUE | uq_shop_ricevute_numero | numero |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_shop_ricevute | `CREATE UNIQUE INDEX pk_shop_ricevute ON shop.ricevute USING btree (id)` |
| uq_shop_ricevute_numero | `CREATE UNIQUE INDEX uq_shop_ricevute_numero ON shop.ricevute USING btree (numero)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_ricevute_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_ricevute_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_ricevute_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_ricevute_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_ricevute_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('ricevute_id')` |
| trg_ricevute_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('ricevute_id')` |
| trg_shop_ricevute_a10_guard_ba_canale_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION shop.trgfn_ricevute_guard_ba_canale()` |
| trg_shop_ricevute_a10_guard_ba_canale_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION shop.trgfn_ricevute_guard_ba_canale()` |

---
{% include-markdown "signature-core.md" %}
