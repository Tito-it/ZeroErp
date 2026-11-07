{% include-markdown "it/dbzero/dbops/manual/emittente_modi.md" %}
# 📚 Tabella `emittente_modi`

> 📝 **Descrizione**
>
> I modi con cui una riga raggiunge il suo emittente: la sede unica del vocabolario e della strada di ogni modo. Ogni riga legge una tabella per chiave (colonna_chiave) e trova l'emittente nella colonna, secondo la forma: PK (la colonna e' l'id dell'emittente fiscale), SR (la colonna e' il soggetto-ruolo dell'emittente), SALTO (la colonna e' la FK verso la testata, che ha il suo modo, modo_padre). Da queste righe dbops.fn_genera_risolutori_emittente genera script.fn_resolve_emittente_fiscale_id e script.fn_resolve_emittente_sr_id: un modo nuovo e' una riga del seed, mai un ramo scritto a mano. La scrive solo il proprietario della tabella, cioe' il migrate (dbops.trgfn_emittente_modi_solo_migrazione). La leggono anche dbops.processi_bersagli (la via dichiarata e' un modo) e i guard di scrittura script.trgfn_guard_emittente_scope, che ricevono il modo come primo argomento.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| modo | text | NO |  |
| schema_tabella | text | NO |  |
| nome_tabella | text | NO |  |
| colonna_chiave | text | NO | 'id'::text |
| forma | text | NO |  |
| colonna | text | NO |  |
| modo_padre | text | YES |  |
| note | text | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| tx_id | uuid | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_emittente_modi_forma |  |
| CHECK | chk_emittente_modi_modo |  |
| CHECK | chk_emittente_modi_padre |  |
| CHECK | chk_emittente_modi_padre_diverso |  |
| FOREIGN KEY | fk_emittente_modi_modo_padre | modo_padre |
| PRIMARY KEY | pk_emittente_modi | modo |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_emittente_modi_modo_padre | `CREATE INDEX ix_emittente_modi_modo_padre ON dbops.emittente_modi USING btree (modo_padre)` |
| pk_emittente_modi | `CREATE UNIQUE INDEX pk_emittente_modi ON dbops.emittente_modi USING btree (modo)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_emittente_modi_a05_solo_migrazione_ins_upd_dlt | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_emittente_modi_solo_migrazione()` |
| trg_emittente_modi_a05_solo_migrazione_ins_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION dbops.trgfn_emittente_modi_solo_migrazione()` |
| trg_emittente_modi_a05_solo_migrazione_ins_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_emittente_modi_solo_migrazione()` |

---
{% include-markdown "signature-core.md" %}
