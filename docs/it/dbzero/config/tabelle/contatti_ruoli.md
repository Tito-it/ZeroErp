# Tabella `contatti_ruoli`

## Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO | nextval('config.contatti_ruoli_id_seq'::regclass) |
| descrizione | text | NO |  |
| descrizione_breve | text | NO |  |
| data_insert | timestamp with time zone | NO | CURRENT_TIMESTAMP |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | CURRENT_TIMESTAMP |
| user_update | text | NO | CURRENT_USER |

## Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_contatto_ruolo | id |
| UNIQUE | uq_contatto_ruolo_contatto_ruolo_descrizione | descrizione |

## Indici
| Nome | Definizione |
|------|-------------|
| pk_contatto_ruolo | `CREATE UNIQUE INDEX pk_contatto_ruolo ON config.contatti_ruoli USING btree (id)` |
| uq_contatto_ruolo_contatto_ruolo_descrizione | `CREATE UNIQUE INDEX uq_contatto_ruolo_contatto_ruolo_descrizione ON config.contatti_ruoli USING btree (descrizione)` |

## Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_upd_contatti_ruoli_audit_data_user | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_upd_audit_data_user_generic()` |