# Brief DB — Cinque mirror scrivono `''` dove la colonna ammette `NULL`

## ⏭️ Chi riparte — aggiornato al 2026-11-12

**Riparte: Tid**, con la decisione D1 (§3) e il via al giro. Il lavoro non è iniziato.

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | ✅ sessione DB | Il guardrail `nullvalue-vuoto` e il censimento dei cinque mirror | §1, §2 | — |
| 2 | **Tid** ⏭️ | D1 e il via | §3 | 1 |
| 3 | sessione DB | Il giro, un mirror alla volta | §4 | 2 |
| 4 | Tid | Apply e pgTAP | — | 3 |

**Decisioni aperte di Tid**: D1. **Da committare**: questo brief.

**Brief vicini verificati**: `brief-db-lista-colonna-campo-sorgente-null.md` (lo stesso difetto su
`ui.lista_colonna`, già corretto: il giro qui ne riprende la forma); `brief-db-guardrail-forme-residue.md`
(archiviato, ha fatto nascere il guardrail). Nessuno copre questi cinque mirror.

## 1. Il difetto

Un caricatore con `nullValue: ""` scrive la cella vuota di una colonna `STRING` come stringa vuota. Dove la
colonna della tabella è di testo e nullable, l'assenza ha così due forme: `''` dal seed, `NULL` da chi scrive
la riga per altra strada. Chi legge deve accettarle entrambe, e chi se ne dimentica sbaglia in silenzio. La
forma giusta è `NULL` (la stessa decisione di Tid su `lista_colonna`, 2026-11-12).

Dal 2026-11-12 il guardrail `scripts/guardrail_forme_changeset.py`, regola `nullvalue-vuoto`, ferma i casi
nuovi. I cinque che c'erano stanno nel suo registro `NULLVALUE_DEBITO`, e una riga che non viola più fa rosso
il cancello: si toglie nello stesso giro in cui si corregge il suo mirror.

## 2. I cinque, come fatto datato (dbdev, 2026-11-12)

| Mirror (`80_data/changelog/`) | Tabella | Colonna | Righe con `''` / righe |
| --- | --- | --- | --- |
| `20250814-04-upsert-config-iva-assoggettamenti` | `config.iva_assoggettamenti` | `note` | 3 / 3 |
| `20250918-02-upsert-dbops-automations_rule_table` | `dbops.automation_rules_tbl` | `name_template` | 17 / 24 |
| `20251001-51-upsert-magazzino-causali-table` | `magazzino.causali` | `user_insert` | 10 / 16 |
| `20260123-11-upsert-automation-delete-block-ruoli` | `dbops.automation_delete_block` | `trigger_name` | 8 / 8 |
| `20260329-60-upsert-config-email-account` | `config.email_account` | `email_reply_to` | 1 / 1 |

I conteggi non decidono niente: la regola vale anche per una riga sola.

## 3. Decisione aperta

**D1 — Per ogni colonna: `NULL`, oppure la colonna diventa NOT NULL?** Prima di correggere si chiede al
modello che cosa vuol dire la cella vuota:

* `note`, `email_reply_to`: un'assenza vera, quindi `NULL`;
* `name_template`, `trigger_name`: sono nomi generati dalle automazioni. Se un nome serve sempre, la cella
  vuota è un nome che manca, e il rimedio è il nome, o un `NOT NULL`, non il `NULL`;
* `magazzino.causali.user_insert`: una colonna di audit vuota nel seed. Va scritta, non annullata.

Proposta: `NULL` per le prime due; per le altre tre, il giro legge chi le usa e porta a Tid la risposta,
colonna per colonna.

## 4. Il giro, per ciascun mirror

La forma di `lista_colonna` (`80_data/20260806-15` e `90_end/20261112-30`):

1. il mirror passa a `nullValue: "NULL"`, e le celle vuote delle colonne nullable portano il token, anche quelle
   non testo, che col token nuovo non accetterebbero la cella vuota;
2. un `CHECK (<colonna> IS NULL OR btrim(<colonna>) <> '')` in `90_end`, preceduto dalla conversione delle `''`
   rimaste fuori dal CSV;
3. si censiscono i lettori della colonna e i lettori del CSV (script, test del backend), come in
   `brief-db-lista-colonna-campo-sorgente-null` §5.1: un lettore del CSV che non conosce il token prende `'NULL'`
   per un valore;
4. la riga del mirror esce da `NULLVALUE_DEBITO`.

Il loader si prova col render offline di Liquibase (`updateSQL --url=offline:postgresql`) su una copia del
mirror senza `preConditions`.
