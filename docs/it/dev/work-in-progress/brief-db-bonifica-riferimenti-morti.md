# Brief DB — bonifica dei riferimenti morti nelle funzioni

**Chi scrive:** team DB (`dev/db-tid`), 2026-08-04.
**Cos'è:** il piano per sistemare le **27 righe di difetto su 21 funzioni** che il
primo giro di `plpgsql_check` ha fatto emergere, più le **6 trigger function
orfane**. E, prima ancora, il presidio che impedisce a queste cose di tornare.
**Strumento:** [`scripts/sql/check_funzioni_riferimenti_morti.sql`](../../../../scripts/sql/check_funzioni_riferimenti_morti.sql)
**Correlati:** [piano-db-ritorno-lotto-a-draft](piano-db-ritorno-lotto-a-draft.md) §7
(misure M4-quater/quinquies/octies, da cui nasce tutto).

---

## 1. Da dove viene

Il 2026-08-04, mentre si toglieva una colonna dormiente, un migrate è fallito su
una funzione che nominava `vendite.attivita_fatturabili_lotti` — una tabella
**droppata di proposito il 2026-02-27**, cinque mesi prima.

Il motivo per cui era ancora lì: PostgreSQL **non traccia** cosa c'è dentro il
corpo di una funzione plpgsql. Il `CASCADE` che droppa una tabella porta via
viste, vincoli e trigger, ma le funzioni le lascia intatte — e non le ri-valida
mai più. Restano mute finché qualcuno non le esegue.

E non è che nessuno se ne fosse accorto. Il **2026-03-31** due di quelle funzioni
erano già state incontrate durante la campagna sugli `E_GENERICO` e **saltate**,
con tanto di changeSet che esiste solo per dirlo:

> «Dipende da `vendite.attivita_fatturabili_lotti` (tabella rimossa).
> **Da verificare se la funzione va rimossa dal DB.**» — `20260331-26`

Quella verifica non è mai stata fatta. È il punto da cui parte questo brief:
**una segnalazione in un commento non è un presidio.**

---

## 2. Lo strumento, e perché non è una regex

L'alternativa era una vista che estraeva con una regex i riferimenti
`schema.tabella` dai corpi e li confrontava con `pg_class`. Sarebbe stata
un'euristica: prende le tabelle nominate dentro le stringhe, non vede i nomi non
qualificati, e soprattutto **non arriva alle colonne** — mentre metà dei difetti
trovati sono colonne, non tabelle.

`plpgsql_check` **compila davvero** il corpo, come farebbe la prima esecuzione:
vede tabelle e colonne, vede i **rami mai eseguiti**, e non prova a validare
l'SQL dinamico (quindi fa anche meno rumore). Estensione creata dal changeSet
`20260804-36`, contesto `provision`.

> ⚠️ La suite pgTAP **non gira in CI** (solo Liquibase e i test Django), quindi il
> presidio vive sul server di sviluppo. Portarlo in CI vorrebbe dire aggiungere
> `postgresql-18-plpgsql-check` all'immagine: è una decisione a parte.

---

## 3. La classificazione, e perché i falsi positivi si etichettano invece di nasconderli

Il primo giro produsse **60 righe**, di cui più della metà rumore. Se avessimo
consegnato quella lista come piano di lavoro, si sarebbe passata mezza giornata
su trentatré non-problemi. Tre giri di affinamento dopo, il quadro è:

| Classe | Righe | Cos'è |
|---|---|---|
| **REALE** | 27 | La lista di lavoro |
| **ORFANA** | 6 | Trigger function senza alcun trigger agganciato |
| `FP_VARIADIC` | 17 | `fn_log_and_raise_error(...)` chiamata **senza** valori variadici: PostgreSQL lo ammette, `plpgsql_check` no |
| `FP_RAMO_ALTRA_TABELLA` | 14 | Trigger function generica: il ramo dedicato a un'altra tabella |
| `FP_TRANSITION_TABLE` | 5 | `new_rows`/`old_table`: esistono solo durante lo scatto del trigger |
| `FP_SQL_DINAMICO` | 1 | Errore di sintassi dentro un `EXECUTE`: segnaposto non ancora sostituiti |

**Nessuna riga viene filtrata via**: escono tutte con la loro etichetta, e il
file stampa apposta anche i falsi positivi, così si controllano a campione invece
di fidarsi della classificazione. Se una è etichettata male, si vede.

Due regole meritano di essere conosciute perché sono il cuore della cosa:

* **Trigger multi-tabella** — una trigger function agganciata a N tabelle viene
  validata contro **tutte**, e l'errore conta solo se compare per **tutte**. Se
  compare su alcune e non su altre, è il ramo di un'altra tabella: comportamento
  voluto, non difetto. Senza questa regola `trgfn_lotto_fatture_guard_stato_coerente`
  (tre tabelle) produceva da sola quattro falsi allarmi.
* **Variadici, distinti per TIPO** — escludere in blocco tutti i «la funzione non
  esiste» avrebbe nascosto **quattro difetti veri**: quelli in cui fra i valori
  passati c'è un `bigint` o un `integer`, per cui il cast implicito a `text` non
  esiste e **la chiamata fallisce davvero**. Lì il guard, quando scatta, solleva
  un errore incomprensibile al posto del messaggio di dominio.

---

## 4. La lista di lavoro, per famiglie

Si lavora per **famiglia di difetto**, non funzione per funzione: dentro una
famiglia il rimedio è lo stesso ripetuto.

### F1 — La coda del drop «attivita pipeline» (3) 🔴 chiudere per prima

Stessa origine dei tre casi già sistemati il 2026-08-04. È la ragione per cui il
cantiere esiste, e finché resta aperta il prossimo migrate può inciampare di nuovo.

| Funzione | Difetto |
|---|---|
| `vendite.fn_list_attivita_sorgenti_abilitate` | legge `attivita_fatturabili_sorgenti_branch_policy`, droppata |
| `vendite.trgfn_attivita_fatturabili_lotti_gen_codice` | orfana (nessun trigger) |
| `vendite.trgfn_attivita_fatturabili_guard_fonte` | orfana (nessun trigger) |

Il precedente dice che si **droppano**: riscriverle vorrebbe dire inventare un
requisito su tabelle tolte di proposito. Da confermare con la stessa verifica dei
consumatori in sei sedi usata per le altre due.

### F2 — Colonne sparite o rinominate (6)

| Funzione | Difetto |
|---|---|
| 🔴 `vendite.fn_prepare_sdi_payload` | usa `tentativo`, la colonna è `tentativo_num` |
| `dbops.fn_admin_merge_stradario` | `id_comune_orig` non esiste |
| `dbops.fn_normalize_indirizzo` | `codice_postale` non esiste |
| `script.fn_get_stradario` | `cp.codice_postale` non esiste |
| `script.fn_get_tipo_contatto_id` | `cod_int_tipo_contatto` non esiste |
| `script.fn_search_stradario` | struttura della query diversa dal tipo di ritorno |

⚠️ **La prima è la più seria del brief.** `fn_prepare_sdi_payload` non può girare,
ed è sulla via SDI che il contesto di progetto dà per «payload pronto». Nota
scomoda: è stata **riscritta il 2026-08-04** nel changeSet `20260804-20`,
copiando il corpo fedelmente dalla doc auto-generata — quindi il difetto c'era già
ed è stato riprodotto tale e quale. La regola «corpo dall'auto-gen» protegge dalle
regressioni, non dai difetti già presenti.

Le altre cinque sono tutte in area stradario/contatti: sembrano la coda di una
migrazione di colonne mai propagata. Da guardare insieme.

### F3 — Chiamate a `fn_log_and_raise_error` con tipi non testuali (4)

`dbops.fn_refresh_mv_ddt_ordini` (`integer`) · `dbops.fn_run_automations_storico`
(`text[]`) · `script.trgfn_note_validate_generic` (`bigint`) ·
`vendite.trgfn_ordini_ful_guard_consistenza` (`bigint`).

Rimedio meccanico — `::text` sui valori variadici — ma l'effetto non è cosmetico:
oggi quei quattro guard, **proprio quando scattano**, falliscono con «la funzione
non esiste» invece del messaggio di dominio.

### F4 — Variabili speciali plpgsql usate male (4, tutte in `anagrafiche`)

`trgfn_sepa_mandati_guard` e `trgfn_soggetti_conti_bancari_guard` usano `sqlerrm`
fuori da un blocco `EXCEPTION`; `trgfn_soggetti_ruoli_conti_bancari_guard` scrive
`tgname` invece di `TG_NAME`; `trgfn_gestori_guard` mette argomenti posizionali
dopo quelli con nome. Sono tutti guard: falliscono nel momento in cui servono.

### F5 — Campi che il record non ha (4) — **da esaminare uno per uno**

`anagrafiche.trgfn_soggetti_conti_bancari_guard` (`new.data_al`) ·
`script.trgfn_qta_from_operativa` (`new.uom_id`, `new.quantita_fissa`) ·
`vendite.trgfn_documenti_sync_canali` (`new.ordine_id`, `new.ddt_id`) ·
🔴 `vendite.trgfn_preventivi_guard_annullamento` (`new.codice`).

Qui la classificazione automatica non basta: l'errore compare su **tutte** le
tabelle agganciate, quindi non è il ramo di un'altra — ma può essere un guard
generico attaccato a una tabella che non ha quel campo. Vanno letti.

⚠️ L'ultimo è **appena stato creato** dal changeSet `20260804-35` del cantiere
*vie d'uscita operatore*: va segnalato lì prima che quel lavoro si chiuda.

### F6 — Flusso e tipo di ritorno (3)

`script.fn_get_stato_cliente_by_istanza` (query senza destinazione + `control
reached end of function without RETURN`) · `script.trgfn_prevent_modification_generic`
(idem) · `dbops.fn_run_automations` (`elemento FROM per la tabella "n" mancante`).

### F7 — Trigger function orfane, area contratti (3)

`trgfn_contratti_guard_modalita_c_activation` ·
`trgfn_contratti_righe_componenti_guard_pending` ·
`trgfn_contratti_righe_guard_modalita_c`, più
`script.trgfn_guard_sorgente_polimorfa_tipizzata`.

Nessun trigger le usa. ⚠️ Prima di droppare va verificato **perché**: una guard
scritta e mai agganciata è un presidio che si crede attivo e non lo è — il
problema potrebbe essere il trigger mancante, non la funzione di troppo.

---

## 5. Il presidio, che è il punto

Sistemare 27 difetti senza presidio significa ritrovarsi qui fra sei mesi.

**Forma proposta**: un pgTAP che lancia il controllo e pretende **zero** righe
`REALE`/`ORFANA`, con un **registro del debito** sul modello di
`db/pgtap/baseline-rossi.tsv` — stessa filosofia dichiarata lì: *«un registro di
debito, non una lista di eccezioni: deve calare»*.

Il primo giro sarà rosso su 27, e va bene: serve a fissare il punto di partenza.
Ogni voce del registro porta funzione, messaggio, data e **motivo per cui è ancora
lì**. Una voce senza motivo non si aggiunge.

---

## 6. Decisioni aperte

1. **F1 si droppa o si riscrive?** Il precedente del 2026-08-04 dice droppare.
2. **F7: chi manca, la funzione o il trigger?** Da guardare prima di decidere.
3. **Il presidio va anche in CI?** Vuol dire mettere il pacchetto nell'immagine.
4. **Ordine dei lavori.** Proposta: F1 (chiude il cantiere che ha aperto tutto) →
   F2 (contiene l'unico difetto su una via di produzione) → F3 e F4 (meccanici,
   veloci) → F5 e F6 (richiedono lettura) → F7 (richiede una decisione).
