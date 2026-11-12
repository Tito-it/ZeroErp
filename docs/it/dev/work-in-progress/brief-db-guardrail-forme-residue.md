# Brief DB — Le forme che muoiono all'apply: i guardrail ancora da scrivere

## ⏭️ Chi riparte — aggiornato al 2026-11-12

**Riparte: Tid**, col via al gruppo B (§2). Il gruppo C (§3) aspetta una decisione per voce.

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | ✅ sessione DB | Gruppo A: otto regole in `scripts/guardrail_forme_changeset.py`, sul modulo comune `scripts/_guardrail_comune.py` | §1 | — |
| 2 | **Tid** ⏭️ | Il via al gruppo B | §2 | 1 |
| 3 | sessione DB | Gruppo B: quattro regole nello stesso script | §2 | 2 |
| 4 | Tid | Per ogni voce del gruppo C: guardrail, pgTAP o niente | §3 | — |

**Decisioni aperte di Tid**: il via a B; le tre voci di C. **Da committare**: il gruppo A (§1).

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

## 2. Gruppo B, da fare

Stesso script, stesso modulo. Servono letture del SQL più attente, quindi falsi allarmi da tarare sul repo
prima di accenderli.

| Regola | Che cosa | Sede |
| --- | --- | --- |
| `django-alla-create` | in `00_schema`/`20_code`, un riferimento a `django.*` che si risolve alla CREATE: `LANGUAGE sql`, `%TYPE` su colonne django, una vista che lo nomina, una FK fuori da `90_end` | linee-guida-sql §11.9 |
| `jsonb-punto-di-domanda` | l'operatore jsonb `?` in un `sql:`: si scrive `jsonb_exists()` | linee-guida-sql §11.12 |
| `type-in-firma` | un parametro, una colonna di `RETURNS TABLE` o una firma di COMMENT/DROP/GRANT con un tipo nudo, dove il valore riflette una colonna, senza il commento che ne dice la ragione. Fonde due voci del triage della memoria | linee-guida-sql §5g |
| `type-perso` | un `%TYPE` che c'era nella revisione precedente della stessa funzione e torna tipo nudo | linee-guida-sql §5g |

## 3. Gruppo C, da decidere

| Voce | Perché non è un guardrail facile | Proposta |
| --- | --- | --- |
| Un oggetto nato in `80_data`/`90_end` nominato da `00_schema`/`20_code` | serve la mappa di dove nasce ogni oggetto | pgTAP o build da zero, già in CI: valutare se basta |
| Una colonna nullable nuova in un CSV col mirror a `nullValue: ""` | dipende dal tipo e dai vincoli della colonna | un controllo sul mirror: `nullValue: ""` su un CSV che ha colonne non testo |
| Il `col` dei preset di `ui.lista_preset` nomina il `campo_sorgente`, non il `codice` | è un dato del seed, non una forma del file | un pgTAP sul seed |
