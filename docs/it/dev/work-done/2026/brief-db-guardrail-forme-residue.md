# Brief DB — Le forme che muoiono all'apply: i guardrail ancora da scrivere

## ⏭️ Chi riparte — aggiornato al 2026-11-12

**Chiuso** (Tid, 2026-11-12). Gruppi A e B fatti, gruppo C deciso voce per voce (§3). Il debito che resta ha
due sedi: i cinque mirror che scrivono `''` in `brief-db-nullvalue-vuoto-cinque-mirror.md`, e il presidio dei
preset in `brief-db-lista-colonna-campo-sorgente-null.md` §5.1 (K-4), al team BE.

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | ✅ sessione DB | Gruppo A: otto regole e il modulo comune | §1 | — |
| 2 | ✅ Tid | Il via al gruppo B; `type-in-firma` ristretta agli id | §2 | 1 |
| 3 | ✅ sessione DB | Gruppo B: quattro regole, provate | §2 | 2 |
| 4 | ✅ Tid | Il gruppo C, voce per voce | §3 | — |
| 5 | ✅ sessione DB | C2: la regola `nullvalue-vuoto`; C3 al BE; il brief del debito | §3 | 4 |

**Decisioni aperte di Tid**: nessuna. Il gruppo A è nel commit `e0c2b03fec`.

**Brief vicini verificati**: `migliorie-generali-da-test-valutazione.md` (parla di guardrail su letterali
`DATE` e sul preambolo pgTAP, altre regole); `registro-residui-aperti.md` (nessuna voce sui guardrail).
Nessuno copre il tema.

## 1. Gruppo A, fatto (2026-11-12)

Decisione di Tid (2026-11-12): il gruppo A in questo giro, un modulo comune e uno script solo.

* `scripts/_guardrail_comune.py`: elenco dei changelog col perimetro, giro dei changeSet e dei blocchi `sql:`,
  marcatore delle eccezioni, primitive lessicali (commenti annidati, letterali, dollar-quote). Ci si appoggiano
  anche `guardrail_timestamp_senza_fuso.py`, `guardrail_comment_al_presente.py` e `guardrail_sql_letterali.py`,
  che ne ricopiavano dei pezzi: il loro output è identico prima e dopo, nel perimetro e su tutta la storia.
* `scripts/guardrail_forme_changeset.py`, passo CI in `ci-validate.yaml`: `sqlcheck-booleano`,
  `punto-e-virgola`, `begin-atomic-da-solo`, `log-cinque-argomenti`, `unique-ignorato`, `messaggi-segnaposto`,
  `csv-fine-riga-misti`, `pgtap-pgagent-owner`. Ogni regola è rossa su un caso costruito; il repo è verde.
  `log-cinque-argomenti` e `unique-ignorato` partono dal 2026-11-12: 27 changelog mergiati le violano, e le
  revisioni successive degli stessi oggetti le hanno corrette (nessuna chiamata a cinque argomenti nelle 1.347
  definizioni vive; i vincoli di `pagamenti.centri_riscossione` esistono).
* ⚠️ La regola sul ritorno carrello è stata ristretta ai **fine riga misti**: un CSV tutto CRLF
  (`80_data/sql/config/email_template.csv`) lo legge bene il loader di Liquibase, e nel database non arriva
  nessun `\r`. A morire è la verifica di linee-guida-sql §11.2, sul file in cui un append ha messo una riga CRLF.
* Le sedi nominano il presidio: linee-guida-sql §5c, §11.2 (regola nuova sui fine riga), §11.12, §11.13;
  liquibase-setup-workflow §2; Messaggi di Errore; guida pgTAP.

## 2. Gruppo B, fatto (2026-11-12)

Stesso script, stesso modulo; tutte e quattro partono da oggi (`20261112-31`), perché la storia le viola e le
revisioni successive l'hanno già corretta. Ognuna è rossa su un caso costruito, e il repo è verde.

* `jsonb-punto-di-domanda` ferma le due forme che si rompono, non lo stile: il `?` singolo fuori da un corpo
  (JDBC lo prende per un segnaposto) e il `??` dentro un corpo. Il `?` singolo dentro un corpo è corretto, ed è
  la forma più usata (338 occorrenze). Sulla storia: 4 `??` dentro un corpo, maggio 2026.
* `django-alla-create`: `%TYPE` su django, funzione `LANGUAGE sql` o vista che lo nomina, FK fuori da `90_end`.
  Sulla storia: una FK in un `DO` protetto da `to_regclass` (`20260418-10`), che da zero non nasce mai.
* `type-perso`: il confronto con la revisione precedente della stessa funzione, in ordine di applicazione. Sulla
  storia 261 voci; due controllate a mano (`fn_ricalcola_riepilogo_iva_fattura`, `fn_chiudi_contratto_per_successione`).
  Una ragione nel commento la esenta, come §5g prevede.
* `id-senza-type` al posto di `type-in-firma`. Misurato dal 2026-11-01: 548 tipi nudi senza ragione accanto, 105 con,
  731 con `%TYPE`; dei 548, 120 sono `*_id`. Tid ha scelto il guardrail sui soli id; gli altri restano alla revisione.

La tabella che segue è quella con cui il gruppo è nato.

| Regola | Che cosa | Sede |
| --- | --- | --- |
| `django-alla-create` | in `00_schema`/`20_code`, un riferimento a `django.*` che si risolve alla CREATE: `LANGUAGE sql`, `%TYPE` su colonne django, una vista che lo nomina, una FK fuori da `90_end` | linee-guida-sql §11.9 |
| `jsonb-punto-di-domanda` | l'operatore jsonb `?` in un `sql:`: si scrive `jsonb_exists()` | linee-guida-sql §11.12 |
| `type-in-firma` | un parametro, una colonna di `RETURNS TABLE` o una firma di COMMENT/DROP/GRANT con un tipo nudo, dove il valore riflette una colonna, senza il commento che ne dice la ragione. Fonde due voci del triage della memoria | linee-guida-sql §5g |
| `type-perso` | un `%TYPE` che c'era nella revisione precedente della stessa funzione e torna tipo nudo | linee-guida-sql §5g |

## 3. Gruppo C, deciso (Tid, 2026-11-12)

* **C1 — un oggetto nato in `80_data`/`90_end` nominato da `00_schema`/`20_code`: niente guardrail.** La CI
  ricostruisce il database da zero a ogni build, e il changeSet muore lì con «does not exist». Un controllo
  statico dovrebbe sapere dove nasce ogni oggetto, cioè rifare il migrate. La regola resta in linee-guida-sql
  §11.14.
* **C2 — il mirror a `nullValue: ""`: regola `nullvalue-vuoto`**, nello stesso script. Guarda ogni caricatore,
  senza perimetro per data, perché un append a un CSV non fa nascere un changeSet nuovo. Conta solo una colonna
  dichiarata `STRING` nel mirror **e** di testo nullable nella tabella, letta dalla doc auto-generata: una
  colonna `timestamptz` dichiarata `STRING` non può ricevere `''`. I cinque mirror che oggi lo fanno stanno nel
  registro `NULLVALUE_DEBITO`, che non tiene righe morte, e la loro correzione in
  `brief-db-nullvalue-vuoto-cinque-mirror.md`. Rossa su un caricatore costruito, verde col `nullValue: "NULL"`.
* **C3 — il `col` dei preset: un test sul seed, al team BE**, come K-4 di
  `brief-db-lista-colonna-campo-sorgente-null.md` §5.1. Le 81 chiavi di ordinamento del seed sono giuste
  (2026-11-12).
