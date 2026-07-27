# Brief DB — Bonifica dei pgTAP rotti dal guard sorgente polimorfa

> **Tipo**: brief operativo DB (debito tecnico) · **Target**: `dev/db-tid` ·
> **Data**: 2026-07-26 · **Chiuso**: 2026-07-27 · **Owner**: Tid
> **Stato**: ✅ **CHIUSO** — perimetro esaurito e obiettivo superato.
>
> | | |
> |---|---|
> | Perimetro dichiarato | ~60 file (stima) |
> | Perimetro **reale** (censimento §7) | **13** |
> | Bonificati | **13 / 13**, tutti verdi |
> | `SORGENTE_POLIMORFA` in baseline | **0** |
> | Rossi totali della suite | 131 → **111** |
>
> **Consegnato oltre il perimetro** (§7.3, §7.5, §9): un difetto di prodotto
> corretto, uno strumento di baseline, e due test resi non-fragili.
>
> ⚠️ **Il censimento ha però trovato altro**, fuori dal perimetro di questo brief
> (§5 lo prevedeva): la suite ha **131 file rossi su 394**, e questa causa ne
> spiega solo **13**. Fra le altre c'è **un difetto di prodotto verificato**, non
> debito di test → §7.3.
>
> **Origine**: rilevato ripetutamente durante le slice del 2026-07-24/26
> (porta oneri, guard uscita commessa, chiusura ri-consegna): ogni volta che si
> esegue una batteria di pgTAP su `vendite`, una parte fallisce per **questa
> stessa causa**, estranea alla slice in lavorazione.

---

## 1. Il sintomo

~~Molti pgTAP di `db/pgtap/vendite/` (stima corrente **~60**, da censire con
precisione — §3)~~ **13 pgTAP** (censimento 2026-07-27, §7) falliscono con:

```text
ERRORE: Chiave sorgente in formato non valido per il key_selector del tipo.
        (atteso uuid, ricevuto SRC-CM-1bc19e109627)
```

Il fallimento avviene **nel fixture**, non in un'asserzione: la transazione
aborta e il file intero risulta rosso (`Bad plan. You planned N tests but ran 0`).

Esempi confermati: `test-commesse-core-functions-v1`, `test-vw-contatore-merce-v1`,
`test-vw-resi-da-accreditare-contatore-v1`, `test-fn-list-ddt-da-pushare-contatore-v1`,
`test-attivita-guardrail-commessa-v1`, `test-vw-dash-backlog-resi-v1`.

## 2. La causa — e perché il guard ha ragione

Il 2026-07-18 è entrato il **guard sorgente polimorfa**
(`script.trgfn_guard_sorgente_polimorfa*`), che verifica che
`sorgente_uid` sia coerente col `key_selector` dichiarato dalla sorgente in
`config.sorgenti`:

| sorgente | `key_selector` | forma attesa di `sorgente_uid` |
| --- | --- | --- |
| `PREVENTIVO`, `OFFERTA_COMMERCIALE` | `uid` | UUID |
| `COMMESSA`, `ORDINE_VENDITA`, `DDT_VENDITA`, `FATTURA`, `RESO_VENDITA`, `ATTIVITA`, `ATTIVITA_CONSUMI`, `CONTRATTO` | `id` | `id::text` |

I fixture rotti costruiscono `sorgente_uid` con **stringhe inventate** del tipo
`'SRC-CM-1bc19e109627'`, `'SRC-ACC-5bd27aa21082'`, `'SRC-LS-f60634625c28'`:
comode quando nessuno controllava, illegali da quando il guard esiste.

**Il guard non è il problema, è la cura**: la chiave polimorfa id-vs-uid è
portante nel modello ([[reference_sorgente_polimorfa_key_selector]]) e prima del
guard era possibile agganciare una riga a una sorgente inesistente. I test
scritti *prima* usavano una libertà che non doveva esistere.

Quindi: **niente da correggere nel prodotto. Va aggiornata la suite.**

## 3. Cosa serve fare

### 3.1 Censimento (primo passo, mezz'ora) — ✅ **ESEGUITO 2026-07-27, vedi §7**

La stima «~60» è di seconda mano e va sostituita con un numero verificato. Su un
campione di 22 file di `db/pgtap/vendite/` ne sono risultati 2 — il rapporto
suggerisce che il totale reale su tutta `db/pgtap/` potrebbe essere **inferiore**
a 60. Comando:

```bash
for f in db/pgtap/*/*.sql; do
  if timeout 60 scripts/testpgtap.sh "$f" 2>&1 | grep -q key_selector; then echo "$f"; fi
done | tee /tmp/pgtap_sorgente_polimorfa.txt
wc -l /tmp/pgtap_sorgente_polimorfa.txt
```

Senza questo elenco non si può stimare il lavoro né dichiararlo finito.

### 3.2 Correzione per file

Per ogni fixture: sostituire la stringa inventata con la **chiave nativa** della
sorgente usata.

- `key_selector = 'id'` → `sorgente_uid = <id_reale>::text` dell'entità
  effettivamente creata dal fixture;
- `key_selector = 'uid'` → l'`uid` reale dell'entità.

⚠️ **Non aggirare il guard** con `SET myapp.bypass_*` o disattivando il trigger:
si perderebbe la copertura proprio sull'invariante che il guard protegge. Il
punto della bonifica è che i fixture diventino **realistici**, non che il
controllo taccia.

### 3.3 Ordine consigliato

Prima i file che coprono aree attive (contatore merce, coda accrediti, dashboard
resi): sono quelli che si ri-eseguono più spesso come non-regressione, quindi
danno il beneficio maggiore. Il resto a seguire.

## 4. Perché conviene farlo, anche se non è urgente

Nessun rischio di prodotto, ma un **costo ricorrente e insidioso**:

1. **Rumore su ogni slice.** Chi esegue una batteria di regressione vede rossi
   che non c'entrano, e ogni volta deve ri-verificare a mano che siano
   preesistenti. È accaduto tre volte in tre giorni.
2. **Rischio di mascheramento — il punto vero.** Un file rosso *nel fixture* non
   esegue **nessuna** asserzione: la copertura di quel file è **zero**, non
   «parziale». Se una modifica futura rompesse davvero qualcosa lì, il test
   sarebbe già rosso e nessuno se ne accorgerebbe. Il debito non è cosmetico:
   sono aree scoperte che *sembrano* coperte.
3. **Abitudine al rosso.** Una suite con 60 rossi noti insegna a ignorare il
   rosso, che è esattamente ciò che i test dovrebbero impedire.

## 5. Fuori perimetro

- Non si tocca il guard né `config.sorgenti`.
- Non si introduce alcun bypass permanente per i test.
- Non è questa la sede per i pgTAP rossi con **altre** cause (es. i fixture che
  non passavano `tipo_doc_fiscale_id` prima del guard `tipo_doc_emittibile`, già
  sanati nelle slice del 2026-07-24, o eventuali altri): il censimento §3.1
  filtra per `key_selector`, e chi trova altro lo annota a parte.

## 6. Riferimenti

- Guard: `script.trgfn_guard_sorgente_polimorfa`, `_tipizzata`, `_testuale`
- Convenzione della chiave: [[reference_sorgente_polimorfa_key_selector]] ·
  `docs/it/dbzero/config/manual/sorgenti.md` §Convenzione chiave sorgente
- Slice che hanno incontrato il problema:
  [brief-db-guard-uscita-commessa-e-capabilities.md](brief-db-guard-uscita-commessa-e-capabilities.md),
  [brief-db-chiusura-riconsegna-reso-definitivo.md](../work-done/brief-db-chiusura-riconsegna-reso-definitivo.md) §9
- Esempio di fixture corretto (usa la chiave nativa `commessa_id::text` per la
  sorgente `COMMESSA`): `db/pgtap/vendite/test-porta-oneri-giro-completo-v1.sql`

---

## 7. Censimento eseguito — 2026-07-27

Eseguito su **tutti** i 394 file di `db/pgtap/`, non solo su `vendite`, con
classificazione della causa. Sostituisce la stima «~60» di §1.

### 7.1 Il quadro completo

| Esito | File | Note |
|---|---|---|
| ✅ PASS | 263 | 67% |
| ❌ **ALTRO** (errore in fixture, altra causa) | **84** | il grosso del debito, **fuori** da questo brief |
| ❌ ASSERZIONE (il test gira ma un'asserzione fallisce) | 34 | copertura reale, esito negativo |
| | | *aggiornamento 2026-07-27: **-6** grazie al fix di §7.3-A → **125 rossi*** |
| ❌ **SORGENTE_POLIMORFA** | **13** | **il perimetro di questo brief** |

**La stima era 4-5 volte in eccesso.** Il debito «sorgente polimorfa» è il
**10%** dei rossi, non il 100%: il lavoro di §3.2 è quindi molto più piccolo del
previsto — ma il problema della suite è molto più grande.

Distribuzione dei 131 rossi per schema: `vendite` 54 · `anagrafiche` 30 ·
`script` 15 · `config` 11 · `catalogo` 5 · `ui` 4 · `rls` 4 · `dbops` 3 ·
`pratiche` 2 · `pagamenti` 2 · `documenti` 1.

### 7.2 I 13 file da bonificare (perimetro di questo brief)

| File |
|---|
| `db/pgtap/pratiche/test-proiezione-stato-sorgente.sql` |
| `db/pgtap/vendite/test-attivita-guardrail-commessa-v1.sql` |
| `db/pgtap/vendite/test-commesse-core-functions-v1.sql` |
| `db/pgtap/vendite/test-fn-batch-upsert-commessa-attivita-v1.sql` |
| `db/pgtap/vendite/test-fn-emit-attivita-propaga-audit-pricing-v1.sql` |
| `db/pgtap/vendite/test-fn-list-ddt-da-pushare-contatore-v1.sql` |
| `db/pgtap/vendite/test-guard-tipo-doc-emittibile-v1.sql` |
| `db/pgtap/vendite/test-sorgente-origine-tipo-doc-fiscale-v1.sql` |
| `db/pgtap/vendite/test-tipo-movimento-colonna-v1.sql` |
| `db/pgtap/vendite/test-trigger-af-commessa-aware-v1.sql` |
| `db/pgtap/vendite/test-vw-contatore-merce-v1.sql` |
| `db/pgtap/vendite/test-vw-dash-backlog-resi-v1.sql` |
| `db/pgtap/vendite/test-vw-resi-da-accreditare-contatore-v1.sql` |

Sei erano già citati in §1; **sette no** — la lista di partenza era incompleta.
Uno sta in `pratiche`, non in `vendite`: il problema non era confinato lì.

⚠️ **Attenzione su `test-sorgente-origine-tipo-doc-fiscale-v1`**: il pattern di
riferimento (ROOT su sorgente `COMMESSA` con `sorgente_uid = commessa_id::text`,
vedi §6) **non è applicabile alla cieca** dove il test asserisce qualcosa sul
*tipo* della sorgente d'origine. Va letto prima di correggerlo.

### 7.3 ⚠️ Trovato fuori perimetro: un difetto di PRODOTTO

§5 prevedeva di annotare a parte ciò che il censimento avesse trovato d'altro.
Due voci, di cui la prima **non è debito di test**.

**A · `script.fn_get_parameter_full` ha due overload ambigui** — 7 file rossi.

```text
script.fn_get_parameter_full(text, bigint, integer, integer[], text, text)
script.fn_get_parameter_full(text, bigint, integer, integer[], text, text, smallint)
```

Entrambi hanno default su tutti i parametri tranne il primo: **qualunque
chiamata a un solo argomento è ambigua**, e non si risolve col cast.

```sql
SELECT script.fn_get_parameter_full('AI_DISABLED_TOOLS');        -- ERRORE: non è unica
SELECT script.fn_get_parameter_full('AI_DISABLED_TOOLS'::text);  -- ERRORE: non è unica
```

⚠️ **Il backend la chiama così**:
`backend/apps/ai_assistant/services/tool_registry.py:140` esegue letteralmente
`SELECT script.fn_get_parameter_full('AI_DISABLED_TOOLS')`. Quel percorso è
**rotto a runtime**, non solo nei test. Sette pgTAP rossi lo stavano segnalando
da tempo, ma essendo confusi nel rumore generale nessuno li ha letti.

**✅ RISOLTO — `20260727-25-drop-fn-get-parameter-full-overload-ambiguo-mctit.yaml`,
applicata 2026-07-27. I 6 pgTAP che dipendevano dal difetto sono tutti verdi.**

*Analisi*: la firma a 7 argomenti è un **sovrainsieme stretto** della 6 —
stessi parametri più `p_categoria_cliente_id` opzionale in coda, che a NULL
salta il proprio livello di cascata. È anche la più recente (`20260515-08` vs
`20260403-15`). Unica differenza di corpo: la 6-arg conteneva un
`RAISE EXCEPTION` dopo `PERFORM fn_log_and_raise_error` — codice morto e
anti-pattern vietato dalle regole di progetto. Si droppa quindi la **6-arg**.

*Verifica pre-applicazione* (DROP dentro transazione + `ROLLBACK`, DB intatto):

| Arietà | Prima | Dopo il DROP |
|---|---|---|
| 1 arg | ❌ «non è unica» | ✅ risolve |
| 6 arg | ❌ «non è unica» | ✅ risolve |
| 7 arg | ✅ | ✅ risolve |

Tutte e tre restituiscono lo **stesso valore**: nessun chiamante va modificato,
è il DB che torna a rispondere.

*Nel changeSet*: precondizione `HALT` che pretende l'esistenza della firma a 7
argomenti prima di togliere l'altra, e un `COMMENT ON FUNCTION` che spiega
perché la firma deve restare **unica** — così il prossimo che vuole aggiungere
un livello alla cascata non rifà lo stesso errore creando un altro overload
«backward compatible».

*Coda*: `db/pgtap/script/test-fn-get-parameter-full-emittente.sql` è tornato a
girare ma il suo caso 1 asseriva l'esistenza della firma appena rimossa — era
«la nuova» quando il test fu scritto (`20260403-15`). Aggiornato alla firma
viva, e **aggiunto un caso 9 di guardrail**: verifica che di
`fn_get_parameter_full` esista **una sola** firma. Non è una ripetizione del
caso 1 — quello controlla che la funzione ci sia, il 9 che non ce ne sia una
**seconda**. È il presidio che avrebbe intercettato il difetto il giorno in cui
è nato. `plan(9)`, verde.

*Esito*: 6 file rossi → **6 verdi**.

| File | |
|---|---|
| `config/test-parameters-emittente-defaults-cascade.sql` | ✅ |
| `config/test-fn-get-parameter-full-categoria-cliente-v1.sql` | ✅ |
| `config/test-parameter-fk-surrogate-dispatch-v1.sql` | ✅ |
| `config/test-parameters-uom-defaults-cascade-v1.sql` | ✅ |
| `config/test-parameters-vendite-limiti-prezzi.sql` | ✅ |
| `script/test-fn-get-parameter-full-emittente.sql` | ✅ (`plan(9)`) |

**B · La colonna `ruolo_sistema` non esiste più** — 7 file rossi.

I test la referenziano (`rau.ruolo_sistema`, `rua.ruolo_sistema`) ma la colonna
non esiste in **nessuna** tabella del DB. Il backend è già migrato: i commenti
in `apps/amm_software/api/views.py` dicono che `is_super_admin` sostituisce «il
legacy `ruolo_sistema` (rimosso)».

Questo **è** debito di test puro: la migrazione multi-face ha lasciato indietro
la suite. Stessa natura del problema di questo brief, causa diversa.

### 7.4 Cosa suggerisce il censimento

Il costo ricorrente denunciato in §4 è **reale ma mal attribuito**: chi esegue
una batteria e vede rossi, nel 90% dei casi non sta guardando questo problema.
Bonificare i 13 file riduce il rumore di poco meno di un decimo.

Il vero rimedio è una **baseline dei rossi noti**, da confrontare a ogni giro.

### 7.5 ✅ Baseline dei rossi noti — realizzata (2026-07-27)

**Strumento**: `scripts/pgtap-baseline.sh` ·
**Registro**: `db/pgtap/baseline-rossi.tsv` (125 righe, `file` + causa).

```bash
scripts/pgtap-baseline.sh vendite          # confronta solo gli schemi toccati
scripts/pgtap-baseline.sh                  # tutta la suite (~7 min)
scripts/pgtap-baseline.sh --update vendite # dopo aver sanato dei file
```

Distingue tre casi e li tratta diversamente:

| Situazione | Comportamento |
|---|---|
| rosso **presente** in baseline | atteso → silenzio |
| rosso **non** in baseline | **REGRESSIONE** → elencato con la causa, `exit 1` |
| file in baseline ora **verde** | **RIENTRATO** → segnalato, va tolto dalla baseline |

Verificato su entrambi i rami: `exit 1` con regressione simulata, `exit 0`
senza. L'aggiornamento parziale (`--update <schema>`) sostituisce **solo** le
righe di quegli schemi, lasciando intatto il resto — così si può sanare un'area
per volta senza rigenerare 7 minuti di baseline.

**Cosa cambia in pratica**: la domanda «questo rosso è colpa mia?», che finora
costava una verifica manuale per ogni file, ora costa un comando. È il problema
denunciato in §4.1, e non dipendeva dai 13 file di questo brief.

⚠️ **La baseline è un registro di debito, non una lista di eccezioni**: deve
calare. Ogni riga è un file la cui copertura vale **zero** — se fallisce nel
fixture non esegue nessuna asserzione — non «parziale». Documentato in
`.codex/AGENTS.md` §Test (pgtap), dove chi lavora lo troverà.

**Stato al 2026-07-27**: 125 rossi su 394 file.

| Causa | File |
|---|---|
| `ERRORE_FIXTURE` (altra causa) | 78 |
| `ASSERZIONE` (il test gira, l'asserzione fallisce) | 34 |
| `SORGENTE_POLIMORFA` (perimetro di questo brief) | 13 |

Per schema: `vendite` 54 · `anagrafiche` 30 · `script` 14 · `config` 6 ·
`catalogo` 5 · `ui` 4 · `rls` 4 · `dbops` 3 · `pratiche` 2 · `pagamenti` 2 ·
`documenti` 1.

---

## 8. Bonifica eseguita — 2026-07-27

**13 file su 13, tutti verdi.** Nessuna migration: sono modifiche ai soli test.

### 8.1 Il pattern applicato

ROOT su sorgente **COMMESSA** (`key_selector='id'`) con
`sorgente_uid = commessa_id::text`: la riga esiste per costruzione, quindi passa
**entrambi** i controlli del guard — formato (`id::text`) ed esistenza nel
target. `fn_emit` pretende solo che una ROOT esista, non ne dereferenzia il tipo.

In ogni file corretto è rimasta una nota che spiega **perché** quella forma, così
la prossima fixture non reinventa una stringa.

### 8.2 ⚠️ Il debito era a STRATI: quattro cause, non una

La chiave inventata era solo quella in superficie. Sbloccato il fixture, sotto
sono emerse altre tre cause — **invisibili** finché la transazione abortiva. È la
conferma sul campo del §4.2: quei file non avevano copertura «parziale», avevano
copertura **zero**, e ci nascondevano altri difetti.

| # | Causa | File |
|---|---|---|
| 1 | chiave sorgente inventata (il perimetro di questo brief) | 13 |
| 2 | righe `ONERE` senza `causale_onere_id` — il `CHECK` biconditional è del 2026-07-21, **dopo** i test | 2 |
| 3 | sorgente cercata per `codice` invece che `codice_interno` — antipattern **BUG_DUAL** (linee-guida-sql §6d) | 4 |
| 4 | attesa posizionale disallineata dal seed (`PARZIALMENTE_EVASO` aggiunto dopo) | 1 |

### 8.3 ⚠️ Reperto: due test riscrivevano una riga di SEED condivisa

`test-attivita-guardrail-commessa-v1` e `test-commesse-core-functions-v1`
facevano un `INSERT ... ON CONFLICT DO UPDATE` su `config.sorgenti`, imponendo
per la sorgente COMMESSA `target_table = 'vendite.commesse_attivita'` — **il
valore errato** che il reperto **R2** di
[brief-db-guard-sorgente-polimorfa](../work-done/brief-db-guard-sorgente-polimorfa.md)
aveva corretto nel seed a `vendite.commesse`.

I due test **reintroducevano il bug dentro la propria transazione**: da lì in
poi ogni validazione girava contro la tabella sbagliata. Rimossi: la sorgente
esiste già nel seed, correttamente configurata, e al test basta leggerla.

> **Regola che ne discende**: un test non deve riscrivere righe di seed
> condivise. Ne altera il comportamento per tutto il resto della transazione, e
> maschera proprio le correzioni che il seed ha ricevuto.

### 8.4 Il caso che è diventato più onesto, non solo più verde

`test-proiezione-stato-sorgente` (pratiche) creava **apposta** sorgenti non
risolvibili, con stringhe `'FAKE-UNRESOLVED-*'` e il commento «mima la commessa»
— per verificare che la vista degradi bene (`risolto = false`).

Il guard rende impossibile scrivere una chiave malformata, ma **non** rende
impossibile il caso che il test voleva coprire: una chiave **valida** su una
sorgente il cui ramo in `vw_stato_sorgente` **non esiste**. È esattamente la
COMMESSA (reperto §5 del brief guard: le 19 righe COMMESSA di
`pratiche_sorgenti` sono a chiave giusta e non risolvono per questo).

Sostituite le stringhe finte con l'id di una commessa reale: il test ora **mima
davvero** ciò che il commento diceva di mimare, invece di falsificarlo.

### 8.5 Esito sulla baseline

`SORGENTE_POLIMORFA`: **13 → 0**. Baseline complessiva: **125 → 112**.

⚠️ Il confronto ha però segnalato **3 rossi nuovi**, estranei a questa bonifica:
`test-{contratti,ddt,ordini}-righe-componenti-v1` falliscono su indici FK
mancanti (es. `ix_vendite_ordrighe_comp_riga`). Provengono dai changeset `dbops`
sulla policy indici della stessa giornata. **Non assorbiti in baseline di
proposito**: restano segnalati come regressione finché non vengono guardati.

---

## 9. Consuntivo e chiusura

### 9.1 Cosa è stato consegnato

| # | Lavoro | Esito |
|---|---|---|
| 1 | **Censimento** dell'intera suite (394 file), con classificazione della causa | §7 — la stima «~60» era 4-5× in eccesso |
| 2 | **Difetto di prodotto** `script.fn_get_parameter_full`: overload ambiguo | §7.3-A — `20260727-25`, 6 file rientrati |
| 3 | **Baseline dei rossi noti** + strumento di confronto | §7.5 — `scripts/pgtap-baseline.sh` |
| 4 | **Bonifica** dei 13 file del perimetro | §8 — 13/13 verdi |
| 5 | Due test resi **non-fragili** | §9.2 |

### 9.2 I due test resi non-fragili

Non erano nel perimetro, ma erano rossi per asserzioni che **non potevano
diventare vere**:

- `script/test-fn-get-parameter-full-emittente.sql` — asseriva l'esistenza della
  firma appena rimossa (era «la nuova» quando fu scritto). Aggiornato alla firma
  viva, **più un caso 9 di guardrail** che verifica che di
  `fn_get_parameter_full` esista **una sola** firma: è l'asserzione che avrebbe
  intercettato il difetto il giorno in cui è nato.
- `vendite/test-preventivi-righe-componenti-v1.sql` — confrontava 10 **nomi
  letterali** di trigger, uno dei quali lungo 67 caratteri contro il limite di 63
  di PostgreSQL: l'automazione lo tronca e vi appende un hash, quindi il nome
  atteso **non poteva esistere**. Riscritto per asserire sul **comportamento** —
  i presidi bespoke per funzione eseguita, i guard `require_attivo` per **tabella
  padre presidiata**, letta da `pg_get_triggerdef`. Copertura salita da 10 a 13
  trigger: tre guard non erano nemmeno menzionati.

### 9.3 Cosa resta aperto, e dove vive adesso

Il debito **non** è finito: restano **111 rossi**, ma ora sono *registrati*, non
*ignorati*. La differenza è che «questo rosso è colpa mia?» costa un comando
invece di una verifica manuale.

| Categoria | File | Dove si tiene traccia |
|---|---|---|
| `ERRORE_FIXTURE` (cause varie) | 78 | `db/pgtap/baseline-rossi.tsv` |
| `ASSERZIONE` | 33 | idem |
| `SORGENTE_POLIMORFA` | **0** | — chiuso da questo brief |

Fra le cause note e non ancora affrontate, due gruppi identificati dal
censimento:

- **~15 file**: «Operatore senza emittente fiscale assegnato» — fixture che non
  impostano lo scope;
- **7 file**: la colonna `ruolo_sistema` **non esiste più** in nessuna tabella
  (§7.3-B). Il backend è già migrato a `is_super_admin`; la suite no. Stessa
  natura del debito chiuso qui, causa diversa.

⚠️ **Non assorbiti in baseline di proposito**: 3 file
(`test-{contratti,ddt,ordini}-righe-componenti-v1`) rossi per indici FK
mancanti, provenienti dai changeset `dbops` sulla policy indici del 2026-07-27.
Restano segnalati come regressione finché non vengono guardati.

### 9.4 Le tre lezioni da portarsi dietro

1. **Un fixture che aborta nasconde tutto ciò che viene dopo.** Sbloccati i 13
   file, sotto sono emerse altre tre cause (causale onere mancante, antipattern
   BUG_DUAL, attesa disallineata dal seed). La copertura non era «parziale»: era
   **zero**, e ci nascondeva dentro altri difetti.
2. **Un test non deve riscrivere righe di seed condivise.** Due lo facevano, e
   reintroducevano nella propria transazione proprio il valore errato che il
   seed aveva corretto (§8.3).
3. **Asserire su nomi generati è fragile.** I nomi auto-provisionati vengono
   troncati e hashati oltre i 63 caratteri: si asserisce sul comportamento, non
   sull'etichetta (§9.2).

> **Nota per chi riprende**: altri quattro test confrontano nomi di trigger
> letterali (`test-fn-ricalcola-totali-preventivo`,
> `test-trgfn-documenti-default-valuta`, `test-ordini-riepilogo-iva-totali`,
> `test-trgfn-preventivi-default-emittente-e-guard-coerenza`). Oggi sono verdi
> perché i loro nomi stanno sotto i 63 caratteri, ma hanno la stessa fragilità
> latente.
