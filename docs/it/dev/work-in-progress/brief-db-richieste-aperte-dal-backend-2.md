# Richieste aperte dal backend — elenco **2**

> **Destinatario:** team DB (`dev/db-tid`). ⭐ **È un ORDINE DI LAVORO, non un
> brief di analisi**: qui c'è *cosa fare*, con lo stato verificato. Il *perché*
> sta nei brief linkati e **non viene ricopiato**.
>
> **Perché un file nuovo e non il precedente riaperto.** Perché lo dice il
> precedente, ed è la regola giusta:
> *«Se arrivano richieste nuove dal backend, NON si riapre questo file: è chiuso
> perché il suo elenco è esaurito, e un ordine di lavoro che si riapre smette di
> dire cosa è finito. Se ne fa uno nuovo, con la stessa forma.»*
> ([elenco 1](../work-done/brief-db-richieste-aperte-dal-backend.md), chiuso il
> 2026-08-31 con tutte e cinque le voci applicate).
>
> **Stato.** 2026-08-31, verificato sul repo dopo il merge `37aaa5ad7` — non
> ricordato.

---

## L'ordine

```text
1. task di pipeline «consuma_plafond_lotto»       2 righe di seed   ⛔ blocca I4
2. fn_check_registro_disattivabile                1 funzione        🟡 non blocca
```

⭐ **La prima costa due righe di JSON**, ed è l'ultima cosa che separa il
registro del plafond costruito in Fase 2 dall'essere usato: finché non c'è,
`anagrafiche.fn_consuma_plafond_titolo_iva` **non ha nessun chiamante possibile**
e il plafond non si consuma mai.

⚠️ **La seconda NON blocca niente, e va detto**: il CRUD dei registri procede
senza — sono i suoi ultimi due passi ad aspettarla, non il cantiere. Non è
urgente; è **giusta**, ed è chiesta prima di scrivere il codice che ne dipende
invece che dopo.

---

## 1. ⛔ Manca il task di pipeline che consuma il plafond

📌 **Il ragionamento è già scritto**, e non si ricopia: `P5` e `N3` del
[piano BE/FE di Fase 3](brief-be-fe-iva-fase-3-consumatori-risolutore.md),
sezione `F3-b2`.

### Il fatto

Il consumo del plafond deve avvenire in un momento preciso, e il piano lo fissa:

```text
per ogni fattura del lotto, ORDER BY data documento, numero   ← P5
   risolvi con l'imponibile VERO
   spezza le righe                      ← fattura ancora EMESSA
   consuma il plafond                   ← fn_consuma_plafond_titolo_iva
   porta a DEFINITIVA                   ← da qui congela
```

⇒ È un **task di pipeline nello step DEFINITIVA**, e va **prima** di
`numera_fatture`: lì la fattura è ancora `EMESSA`, e
`trgfn_fattura_satellite_guard_congelamento` legge lo stato **vivo** al momento
della scrittura — dopo, la spezzatura verrebbe rifiutata.

⛔ **E i task della pipeline sono un SEED, non codice.** Verificato il
2026-08-31 su
`db/changelog/migrations_v2/80_data/sql/vendite/fatturazione_pipeline.csv`: lo
step DEFINITIVA contiene oggi, su **due** pipeline, esattamente

```text
 4  Pipeline massiva (DEFINITIVA)      ['numera_fatture', 'popola_fatture_rettifiche', 'stampa_documenti_lotto']
 6  Pipeline giornaliera (DEFINITIVA)  ['numera_fatture', 'popola_fatture_rettifiche', 'stampa_documenti_lotto']
```

⇒ Il backend può scrivere l'handler, il servizio e i suoi test per intero, ma
**niente lo invocherebbe**.

✅ **E infatti li ha scritti** (2026-08-31, `F3-b2`): `PlafondFatturaService`,
il gestore `consuma_plafond_lotto`, la voce in `ALLOWED_TASK_FUNCTIONS`, i
metodi di repository e **14 test provati per mutazione**. ⛔ Manca **solo** la
riga di configurazione: senza, il task non viene mai chiamato.

⭐ **E una cosa è già in guardia**: `_TASK_ORDER_DEPENDENCIES` dichiara da adesso
`numera_fatture → consuma_plafond_lotto`. Finché il task non è nel seed la riga
non fa nulla (un predecessore assente è una configurazione valida); il giorno
che arriva, se arriva **girata** lo step si ferma **prima** che il primo task
scriva, invece di scoprirsi a documenti già numerati. È la stessa rete che il
codice descrive per `genera_scadenze_lotto`: *«la configurazione la scrive un
altro team»*.

### La richiesta

**Aggiungere il task `consuma_plafond_lotto` in TESTA al `processi` delle
pipeline `4` e `6`**, prima di `numera_fatture`:

```json
{"task":"consuma_plafond_lotto","fase":"Consumo plafond titoli IVA",
 "params":{"implementation_key":"default"}}
```

⚠️ **In testa e non in coda**: dopo `numera_fatture` la fattura è già oltre la
soglia di congelamento, e la spezzatura verrebbe **rifiutata** — non
silenziosamente, ma con un errore che parla d'altro e in un punto dove nessuno
lo cerca.

⚠️ **Su entrambe le pipeline, non su una.** Una sola sistemata darebbe un
comportamento che dipende dal *tipo di lotto*: il plafond consumato sui lotti
giornalieri e non su quelli massivi, e nessuno se ne accorgerebbe finché i conti
di un esportatore abituale non tornano.

📌 **La riga in `fatturazione_pipeline_task_policy` la decide il team DB.**
Verificato: `popola_fatture_rettifiche` gira nelle stesse due pipeline e **non
ne ha una** — quindi non è obbligatoria. Se il task deve essere annullabile o
avere un `resume_mode` proprio, la riga serve; altrimenti no.

### Cosa blocca

`F3-b2`, cioè la **seconda metà di `I4`**: la riga di fattura che si spezza
quando il plafond copre solo una quota, e il consumo che ne segue.

⛔ E con essa l'intero senso di Fase 2: il registro dei titoli IVA, i movimenti,
l'accumulatore e l'annullo delle forzature esistono e sono provati, ma
**nessuna fattura li tocca**. `fn_consuma_plafond_titolo_iva` ha **zero
chiamanti** — verificato.

### Presidio atteso

⭐ **Quello che discrimina non è «il task compare nella lista»**: è l'**ordine**.
Un lotto portato a DEFINITIVA su un titolo con capienza parziale deve avere, a
fine giro, **due righe** sulla fattura e **un movimento** nel registro. Con il
task in coda invece che in testa, la stessa prova fallisce con il rifiuto del
guard di congelamento — che è l'esito da vedere **una volta**, per sapere che
la posizione conta.

⚠️ E il gemello: un lotto senza titoli deve passare **identico a oggi**, con
zero movimenti scritti. Senza, un task che «gira sempre» passerebbe il primo.

---

## 2. 🟡 Manca la `fn_check_*` che dice perché un registro non si disattiva

📌 **Il ragionamento è già scritto**, e non si ricopia: §FE-2 del
[brief BE/FE del CRUD dei registri](brief-be-fe-crud-registri-di-numerazione.md).

### Il fatto — i registri non hanno CRUD, e disattivare è la parte delicata

`vendite.registri_fatturazione` **non ha nessun CRUD** — verificato il
2026-08-31 su cinque superfici: nessuna rotta, nessuna riga in
`ui.lista_definizione`, nessuna voce nel lookup generico, nessun drawer, nessuna
voce di menu. Le 14 righe di oggi nascono da changeSet di seed e dal
provisioning automatico (`fn_provision_registri_emittente`).

Il CRUD si scrive ora, e la sua azione di riga più delicata è **disattiva**,
perché su questa tabella i guard sono **tre**:

```text
trg_registri_fatturazione_a10_fatture_block_deact_upd          → ha fatture
trg_registri_fatturazione_a10_registri_fatturazione_prog_…     → ha progressivi
trg_registri_fatturazione_a10_tipi_doc_fiscale_registri_…      → ha mapping tipo doc
```

⭐ **Il secondo è quello che sorprende**: un registro che ha numerato anche **un
solo** documento ha una riga di contatore viva, quindi non si spegne più. Ne
discende che il cestino è **quasi sempre** indisponibile — e senza un motivo a
video l'operatore lo scopre premendo.

### La richiesta — una `fn_check_*`

```sql
script.fn_check_registro_disattivabile(p_registro_id bigint) RETURNS jsonb
```

Forma del §12.5.1: `[]` se disattivabile, altrimenti array **ordinato** di
`{codice, reason, reason_key, dettaglio, valori}`. Un motivo per guard:

| `reason` | Quando |
| --- | --- |
| `HA_FATTURE` | esistono fatture attive sul registro |
| `HA_PROGRESSIVI` | esiste una riga viva in `registri_fatturazione_progressivi` |
| `HA_MAPPING_TIPO_DOC` | esiste una riga in `tipi_doc_fiscale_registri` |

⭐ **Nessun codice errore nuovo**: la check *nomina* gli `E_ATTIVO_BLOCK_CHILDREN_*`
che sono **già a catalogo con la loro policy** — verificato. §12.5.2 dice che se
servisse un codice nuovo il difetto sarebbe a monte: la madre starebbe
rifiutando senza saper dire perché.

⛔ **I `reason` NON portano il prefisso `E_`.** È la convenzione del §12.5.1, ed
è presidiata solo per caso: il guardrail dei codici errore cerca i letterali
`E_*` nei corpi delle funzioni e un `reason` così prefissato gli arriva come
**codice senza policy**. È costato un changeSet stamattina — `E_UN_ANNULLO` →
`RIGA_DI_ANNULLO`, `20260831-35`.

⚠️ **`SECURITY DEFINER` come le gemelle**: la check legge `vendite.fatture`, che
ha la RLS. Sotto il perimetro di un operatore le fatture di un altro emittente
sono invisibili, e la check concluderebbe «si può disattivare» **proprio nel
caso da bloccare**.

📌 **Dove leggerla, lo decide il BE** e non serve qui: la lista dei registri è
una query del repository, quindi basta una `LEFT JOIN LATERAL` come fa
`EmittentiFiscaliBillingAccountRepository` con `fn_check_ba_cambio_emittente` —
nessuna vista nuova.

### Cosa blocca — niente, ed è il punto

⚠️ **Niente, e va detto.** I passi 1-4 del CRUD (repository, service, mappa
vincoli, lista, drawer) non la toccano. Aspettano solo il passo 5 — il cestino
col motivo — e il 6.

⭐ È chiesta **prima** di scrivere il codice che ne dipende, che è la differenza
con la voce 5 dell'elenco 1: là il prerequisito si scoprì a lavoro fatto.

### Presidio atteso — la madre che CHIAMA

* Un registro **senza** figli: la check risponde `[]`, e la disattivazione passa;
* ⛔ il **gemello negativo**, e senza non si distingue «rifiuta il caso giusto»
  da «rifiuta tutto»: un registro con un progressivo vivo risponde
  `HA_PROGRESSIVI`, e la disattivazione viene rifiutata dal trigger con lo
  stesso codice che la check nomina;
* ⭐ il presidio che vale davvero, §12.5.2: **la madre non contiene più il
  predicato** — cioè il guard di disattivazione chiama la check invece di
  riscriverla. Se restano due predicati, l'invariante è la disciplina e non la
  struttura.

---

## ⛔ Cosa NON è da fare qui — e la prima voce è la più importante

### ⛔ **NON scrivere una madre `fn_consuma_plafond_lotto`**

La richiesta è **due righe di JSON**. Non una funzione.

⚠️ **Il rischio è concreto perché il nome del task suona come una madre per
lotto**, e su questa stessa pipeline è già successo — sta scritto accanto al
codice:

> *«`vendite.fn_generate_fatture_righe` è stata RIMOSSA il 2026-07-28
> (changeset `20260728-21`): l'implementazione in esercizio è
> `FattureRigheService.generate_fatture_righe`. Lasciare qui il nome di una
> funzione inesistente è precisamente ciò che ha fatto scrivere **due requisiti
> di aggregazione su codice non eseguito**.»*

⇒ Il task va dichiarato **senza chiave `fn`**, come `generate_fatture_righe`:
l'implementazione è Python e `ALLOWED_TASK_FUNCTIONS` la registra già a `None`.
⚠️ Un `fn` dichiarato in configurazione per un task a `None` viene **respinto**
con `E_TASK_NOT_ALLOWED` — quindi il presidio c'è, ma è meglio non farlo
scattare.

⭐ **Cosa resta alla madre DB**, e non cambia: `fn_consuma_plafond_titolo_iva`
fa la parte che **deve** stare sotto lock — capienza, movimento, ripartizione.
Il BE ordina le fatture, decide quali righe spezzare e la chiama. La divisione è
quella di sempre: la regola che protegge un invariante concorrente sta nel DB,
l'orchestrazione sta qui.

### Il resto

* ⛔ **L'ordinamento `ORDER BY data documento, numero`** del giro (`P5`,
  `D15-bis`): è **lavoro nostro**, sta nel servizio Python e non nel seed;
* ⛔ **La spezzatura della riga**: colonna, FK, guard e vista sono **già
  applicati** (voce 5 dell'elenco 1, `20260831-30..33`);
* 📌 **Il generatore XML FatturaPA**: non esiste, e non è di questo cantiere.

---

## ⭐ Come si decide se una voce è DB o BE — la prova, non l'impressione

> Scritto il 2026-08-31 dopo una domanda di Tid: *«siamo sicuri che stiamo
> gestendo bene la pipeline e non abbiamo spostato al DB richieste non
> necessarie, che poi magari duplichiamo?»*. ⛔ La domanda era giusta: la prima
> versione di questa voce diceva che il consumo del plafond «non è scrivibile»
> lato BE, ed **era falso** — handler, servizio e test erano scrivibili, e sono
> stati scritti.

**La prova è una sola, e si esegue sul repo**: *esiste un percorso di scrittura
BE su quell'artefatto?*

| Artefatto | Percorso di scrittura BE | Chi |
| --- | --- | --- |
| `vendite.fatturazione_pipeline` (i task di uno step) | **nessuno** — verificato: il BE la legge via `fn_list_fatturazione_pipeline_steps` e `fn_resolve_fatturazione_pipeline_step`, non esiste `INSERT`/`UPDATE`, nessuna rotta, nessuna schermata | **DB** |
| L'**handler** di un task, il servizio, i test | è codice Python | **BE** |
| `config.parameters` (riga base: codice e valore) | **nessuno** — il `ParameterService` scrive solo `parameter_overrides`, che è un'altra tabella | **DB** |
| `config.codici_errore` / `messaggi_errore` | **nessuno** — il generatore delle policy **legge** e produce un file Python | **DB** |
| Corpo di una funzione SQL, DDL, trigger, viste | — | **DB** |

⚠️ **Il caso che inganna è proprio il primo**, e va nominato: «il task di
pipeline» non è un artefatto solo. È **due**: il codice che lo esegue (BE) e la
riga che dice quando eseguirlo (DB). Chiamarlo con un nome solo fa sbagliare
l'instradamento in entrambi i versi — chiedere al DB ciò che si può scrivere, o
scrivere qui ciò che non prenderebbe mai effetto.

⭐ **E il verso pericoloso è quello della duplicazione**: il codice lo dice già,
sulla stessa pipeline — `fn_generate_fatture_righe` fu scritta a DB **mentre**
l'implementazione viva era in Python, e *«ha fatto scrivere due requisiti di
aggregazione su codice non eseguito»*.

---

## Diario

| Data | Cosa |
| --- | --- |
| 2026-08-31 (3) | ➕ **Voce 2**: `fn_check_registro_disattivabile`, dal cantiere del CRUD dei registri. ⭐ **Non blocca** — i primi quattro passi di quel brief partono senza — ed è chiesta *prima* di scrivere il codice che ne dipende. ⚠️ La strada alternativa (derivare `can_remove` in Python) è stata **scartata da Tid**: è il grado ⛔ del §12.5 e sarebbe il difetto che il mapping BA ha appena finito di chiudere, per giunta su **tre** guard invece di uno. ⛔ E i `reason` non portano il prefisso `E_`: la regola è costata un changeSet stamattina (`E_UN_ANNULLO` → `RIGA_DI_ANNULLO`, `20260831-35`) |
| 2026-08-31 (2) | ⛔ **Corretta una frase sbagliata di questo stesso file**, su segnalazione di Tid: diceva che il consumo del plafond non era scrivibile lato BE. Era falso — handler, servizio, repository e 14 test sono BE, e sono stati scritti. Al DB resta **solo** la configurazione. Aggiunta la regola di instradamento (§«Come si decide») e il divieto esplicito di scrivere una madre `fn_consuma_plafond_lotto`, che è la duplicazione che questo cantiere ha già pagato una volta |
| 2026-08-31 | Elenco nato chiudendo `F3-b1` (la riga di fattura che chiede l'IVA al risolutore) e verificando **dove** possa vivere il consumo del plafond. ⚠️ **È lo stesso schema della voce 5 dell'elenco 1**: un lavoro che sembrava «solo BE» fermo su un prerequisito che nessuno aveva chiesto — lì una colonna, qui due righe di seed. ⭐ La differenza è che stavolta è stato trovato **prima** di scrivere il codice che ne dipende |
