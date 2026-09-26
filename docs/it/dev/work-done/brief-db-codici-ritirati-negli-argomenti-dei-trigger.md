# Brief DB — un codice ritirato che nessun presidio vedeva: gli argomenti dei trigger

> **Perimetro:** DB (`dev/db-tid`), più una richiesta al BE in §4. **Aperto:** 2026-09-23.
> **Origine:** una riga vista passando mentre si chiudeva
> [brief-db-magazzino-lotto-2-bis-be-fe.md](../work-done/brief-db-magazzino-lotto-2-bis-be-fe.md)
> — «`CODICE_NON_MODIFICABILE` è `obsoleto_dal 2026-08-05` e il registro dei
> lock lo nomina ancora» — e la risposta di Tid: *«andrebbe corretto»*.
>
> **Stato:** ✅ **CHIUSO SUL LATO DB — applicato, verde e committato il
> 2026-09-23.** I tre changeSet (`20260923-01`, `-02`, `-03`) sono `EXECUTED`
> **sia su dbdev sia su `zeroerp_ci`**, cioè anche sul database ricostruito da
> zero; pgTAP rilanciati da Tid, **nessuna regressione**; commit `7d67d6d9d`.
>
> Letto sul catalogo vivo (non dedotto dai file): **zero** trigger di lock con un
> codice non vivo — su dev e su CI —, **zero** righe malate nelle **43** del
> registro, e il guardrail dei codici esce **0** dicendo *«nessun codice ritirato
> ancora sollevato né nei corpi né negli argomenti dei 2102 trigger»*. Su dev i
> lock di `catalogo.articoli` (`codice` + `uom_id`), `config.iva_stati` e i due
> di magazzino sono armati.
>
> ⚠️ **Due ricadute, entrambe trovate dai controlli e non da una lettura**: un
> pgTAP che pinnava il nome di un trigger consolidato (§5-bis) e il rosso su
> `zeroerp_ci` per due lock IVA scritti a mano (§5-ter). Sanate tutte e due nel
> registro, mai allentando il controllo.
>
> ✅ **Metà BE (§4) chiusa il 2026-09-23**: i due test portano
> `E_CODICE_NON_MODIFICABILE`, i quattro commenti non nominano più il codice
> ritirato né i trigger di `catalogo.articoli` che non esistono più.
>
> ✅ **CHIUSO il 2026-09-26 e spostato in `work-done/`.** La domanda sul modello
> di §7 (i lock spariti da dbdev e la convergenza «trigger vivo = registro»)
> passa a un brief suo:
> [brief-db-lock-di-colonna-fuori-registro.md](brief-db-lock-di-colonna-fuori-registro.md).
> Lì c'è anche la causa, trovata il 26-09: **non** era dev fuori modello, era il
> giro notturno che su CI non gira.
>
> **In una riga.** Un codice ritirato quarantanove giorni fa è ancora sollevato
> da **69 trigger su 68 tabelle in 8 schemi**, e il presidio che esiste apposta
> per impedirlo è **verde** — perché guarda dentro i corpi delle funzioni, e
> quel codice non è in nessun corpo: viaggia come argomento del `CREATE TRIGGER`.

---

## 1. Il difetto, sul modello

`script.trgfn_lock_columns` è una funzione di trigger **generica**: non conosce
né la colonna né il codice errore: li riceve in `TG_ARGV`, cioè scritti negli
**argomenti** del `CREATE TRIGGER`. Quegli argomenti li calcola
`dbops.fn_run_automations_lock_columns` leggendo il registro
`dbops.automation_lock_columns` più le regole implicite (`codice_interno`).

⇒ Ne discendono due proprietà che insieme fanno il danno:

1. **Il codice errore di un lock non sta in `pg_proc`.** Sta in
   `pg_trigger.tgargs`. Qualunque censimento fatto sui corpi — e sono quasi
   tutti — non lo vede.
2. **L'automazione crea solo se il trigger manca** (`existence_strategy: BOTH`):
   non confronta mai gli argomenti di uno che esiste già. ⇒ Un trigger generato
   una volta **non converge mai più** verso ciò che il registro dice oggi.

Da sole sono due scelte ragionevoli. Insieme, significano che *una regola resta
scritta nella forma che aveva il giorno in cui la tabella è nata*, e nessun
meccanismo la riallinea.

## 2. Come si è manifestato

Il 2026-08-05 il changeSet `20260805-26` ha rinominato undici codici `*` → `E_*`,
fra cui `CODICE_NON_MODIFICABILE` → `E_CODICE_NON_MODIFICABILE`. La sua
intestazione dichiara il metodo, ed è un metodo giusto:

> *«Le 14 funzioni qui sotto sono l'elenco COMPLETO dei posti che nominano gli 11
> codici, ricavato da `pg_proc` e non a memoria.»*

Completo **rispetto a `pg_proc`**. La rinomina ha corretto il generatore — che
oggi fa `COALESCE(error_code, 'E_CODICE_NON_MODIFICABILE')` — quindi ogni trigger
nato dopo porta il codice vivo. Quelli nati prima sono rimasti com'erano.

⭐ **La forma del difetto**: la stessa regola — *«questa colonna non si cambia»* —
oggi risponde con **due codici diversi** a seconda di quando è nato il trigger.
Non è una decisione: è storia della macchina.

### La misura (dbdev, 2026-09-23 — fatto datato, non un motivo)

| | |
| --- | --- |
| trigger di lock col codice **ritirato** | **69**, su **68 tabelle**, in `acquisti`, `anagrafiche`, `catalogo`, `config`, `documenti`, `magazzino`, `pagamenti`, `vendite` |
| trigger di lock col codice **vivo** | 15 (tabelle nate dopo il 05-08) |
| funzioni plpgsql che lo nominano **nel corpo** | **zero** |
| righe del registro che nominano un codice **non vivo** | **26 su 38** — 25 ritirato, 1 inesistente |

⚠️ La misura porta un **controesempio**, non la ragione: la ragione è che un
codice ritirato non si solleva, e varrebbe identica a un trigger su 87.

## 3. Che cosa entra, e perché in quest'ordine

### 3.1 Il registro (`80_data/sql/dbops/automation_lock_columns.csv`)

* **25 righe** `CODICE_NON_MODIFICABILE` → `E_CODICE_NON_MODIFICABILE`;
* **1 riga** `EMITTENTE_NON_MODIFICABILE` → `E_EMITTENTE_NON_MODIFICABILE`
  (`vendite.preventivi.emittente_fiscale_id`). ⚠️ Quel codice **non esiste a
  catalogo**: era la stessa rinomina del 05-08, mancata anche lì. Era innocuo
  solo perché quel trigger non è mai stato rigenerato — armato, avrebbe risposto
  `[MESSAGGIO NON DEFINITO: EMITTENTE_NON_MODIFICABILE]`;
* **2 righe nuove**, e non sono regole nuove: sono regole **già in vigore fuori
  dal registro** (§3.2).

⛔ **Il CSV da solo non serve a niente**: non muove nessuno dei 69 trigger, che
esistono già. È il prerequisito, non il rimedio.

### 3.2 ⭐ Le due righe nuove — il vero rischio della bonifica

Droppare e rigenerare è sicuro **solo se il registro dice già tutto quello che i
trigger vivi presidiano**. Provato: non era così.

| Colonna | Chi la presidiava | Che cosa sarebbe successo |
| --- | --- | --- |
| `catalogo.articoli.codice` | `trg_articoli_a10_protect_codice_upd`, scritto **a mano**, solo *rinominato* (non creato) dal `20251119-51` | il drop lo toglieva, l'automazione rigenerava con il solo `uom_id`: **lock perso in silenzio** |
| `config.sorgenti.categoria` | `trg_sorgenti_a10_lock_columns_upd`, generato da un registro che quella riga **non la dice più** | idem |

⇒ Entrambe entrano nel registro con `E_CODICE_NON_MODIFICABILE`. È la regola di
casa applicata a sé stessa: *un `CREATE TRIGGER` scritto a mano con la stessa
funzione è un oggetto che **sembra** governato dall'automazione e non lo è.*

### 3.3 La bonifica (`90_end/20260923-02-rigenera-lock-columns-con-codici-vivi`)

Un `DO` forward e idempotente: censisce i trigger di lock che negli argomenti
nominano un codice **non vivo** (assente dal catalogo *o* con `obsoleto_dal`
scaduta), li droppa, richiama l'automazione, e **poi verifica**.

⭐ **Si rigenera, non si riscrive l'argomento.** Ricostruire ogni `CREATE TRIGGER`
da `pg_get_triggerdef` sostituendo la stringa sarebbe un **secondo** posto che
calcola l'elenco degli argomenti, accanto al generatore — cioè il difetto che
questo registro esiste per chiudere.

**I tre controlli, e il secondo è quello che conta:**

| | Che cosa pretende |
| --- | --- |
| (a) | ogni tabella toccata ha di nuovo un trigger di lock |
| **(b)** | **nessuna colonna che era lockata è rimasta scoperta** — se lo è, il migrate si ferma, perché vuol dire che quel lock non è nel registro |
| (c) | nessun trigger di lock nomina più un codice non vivo |

⛔ **Su un database da zero non fa niente**, ed è voluto: nella prima passata i
trigger non sono ancora nati (li genera `ci_apply`, la seconda invocazione), il
censimento torna vuoto e il changeSet esce **senza chiamare l'automazione** — la
sequenza di un DB nuovo resta identica a oggi.

### 3.4 Il rubinetto (`scripts/sql/guardrail_codice_errore_strutturato.sql`, in CI)

* **controllo (D) esteso**: ora legge **due** superfici — i letterali nei corpi
  plpgsql **e** gli argomenti dei trigger. ⚠️ Il confronto sugli argomenti è per
  **uguaglianza**, non `LIKE`: un `LIKE '%CODICE_NON_MODIFICABILE%'` aggancerebbe
  anche `E_CODICE_NON_MODIFICABILE`, cioè il codice **vivo**, e il presidio
  sarebbe rosso per sempre sulla cosa giusta;
* **controllo (H) nuovo**: il registro dei lock non può nominare un codice non
  vivo. È il rubinetto vero — una riga lì è un **call site differito**, e (H)
  avrebbe preso *entrambi* i difetti alla nascita, senza aspettare una
  rigenerazione.

⛔ **Non si è aggiunto un pgTAP**, ed è una scelta: il criterio vive nel
guardrail, e un pgTAP che lo ripete sarebbe una seconda copia del criterio —
la cosa che questo progetto non fa. Il pgTAP `config/test-codici-errore-obsoleto-dal`
tiene la **sua** metà (un codice ritirato continua a risolversi a runtime) e ora
rimanda a (D) dicendo che le superfici sono due.

## 4. 🔵 Al BE — una richiesta e una finestra dichiarata

Due test asseriscono la stringa `'CODICE_NON_MODIFICABILE'`:

* `apps/magazzino/tests/db/test_anagrafiche_magazzino_db.py:142` — è un **e2e sul
  DB vero** (`magazzino.magazzini.codice`), e diventa **rosso** appena la
  bonifica è applicata. ⇒ va portato a `E_CODICE_NON_MODIFICABILE`;
* `apps/core/tests/services/test_config_crud_service.py:118` — è un **mock**:
  fabbrica l'eccezione, quindi resta verde e racconta una cosa falsa. Stesso
  cambio, senza urgenza.

⚠️ **Per chi usa il software non cambia niente**: i due codici hanno la stessa
classe (`CONFLITTO_STATO`) e la **stessa identica frase**, e
`error_policies_generated.py` / `error_messages_fallback.py` li portano già
entrambi.

✅ **Ordine deciso da Tid il 23-09: il DB va avanti e la finestra si dichiara.**
Quel test pinna un codice **ritirato**: il rosso dice la verità, e non siamo in
produzione.

⚠️ Da rivedere quando il BE tocca quei punti, tutti **commenti** (nessun
comportamento):

* `apps/magazzino/services/anagrafiche_magazzino_service.py` e
  `apps/core/services/config_crud_service.py` nominano il **codice** vecchio;
* `apps/catalogo/api/views.py:74` e `apps/catalogo/services/catalogo_service.py:62`
  nominano i due **trigger** di `catalogo.articoli` che dal 23-09 non esistono
  più (`trg_articoli_a10_protect_codice_upd` / `_protect_uom_id_upd`): ora è uno
  solo, `trg_articoli_a10_lock_columns_upd`, e comunque il nome lo decide
  l'automazione — meglio non citarlo affatto.

## 5. Come è stato provato, e che cosa questo NON prova

SQL **estratto dal changeSet**, in `BEGIN … ROLLBACK` su dbdev come owner, con il
registro corretto simulato nella stessa transazione (cioè lo stato in cui
`80_data` lo lascia):

* 69 trigger rigenerati, **nessuna colonna persa**, zero residui con codice non vivo;
* **idempotente**: una seconda passata nella stessa transazione dice *«niente da
  bonificare»* e non tocca nulla — è anche il percorso del DB da zero;
* ⭐ **prova per mutazione**: tolte le due righe nuove dal registro dentro la
  transazione, il controllo (b) diventa **rosso** e nomina esattamente
  `catalogo.articoli.codice` e `config.sorgenti.categoria`. Senza quel controllo
  sarebbero spariti due lock senza che niente lo dicesse;
* il **guardrail**: oggi esce **3** (rosso) e nomina i 69 trigger uno per uno;
  applicata la bonifica nella stessa transazione esce **0**.

⛔ **Non prova** che regga da zero: su `zeroerp_ci` non è stato applicato niente,
e la CI di GitHub è ferma dal 21-09 (billing). Non prova nemmeno il comportamento
**come applicazione**: l'harness gira da owner.

⚠️ E non prova che i 69 lock **facessero** il loro lavoro prima: prova che le
colonne lockate dopo sono le stesse di prima, più quelle che il registro dichiara.

## 6. Che cosa cambia, oltre al codice

* `catalogo.articoli` aveva **due** trigger di lock (`_protect_codice_upd` e
  `_protect_uom_id_upd`, entrambi a mano): l'automazione ne fa **uno** con
  entrambe le colonne. Il doppione sparisce;
* `config.sorgenti` prende anche `codice_interno`, che l'automazione locka
  implicitamente su ogni tabella che ce l'ha: ne era fuori solo perché il suo
  trigger è più vecchio di quella regola;
* `vendite.preventivi` prende `emittente_fiscale_id`, che il registro dichiara
  dal 2026-08 e il trigger vivo non ha mai avuto;
* ⭐ e l'automazione arma anche i **due lock di magazzino** del Lotto 2-bis (R-4,
  `inventari`/`rettifiche`.`magazzino_id`), che erano dichiarati e non generati:
  87 trigger di lock → 88.

## 5-bis. ⚠️ La ricaduta dell'apply: un pgTAP che pinnava il NOME

Applicata la bonifica (08:10 del 23-09), `catalogo/test-articoli-seed-uom-base-lock`
è andato rosso al **test 3**:

```text
# Failed test 3: "3) trigger trg_articoli_a10_protect_uom_id_upd presente su catalogo.articoli"
```

⭐ **E ha ragione il codice, non il test.** Quel trigger non esiste più perché è
stato *consolidato*: i due scritti a mano sono diventati l'unico
`trg_articoli_a10_lock_columns_upd`, con **entrambe** le colonne e il codice vivo.
Il test asseriva un **nome** che appartiene all'automazione — la decide il
`name_template` di `dbops.automation_rules_tbl` — quindi pinnava un dettaglio di
implementazione e non la regola. È la forma «test che pinna il sintomo»: diventa
rosso **su una riparazione**.

⛔ **Ed è un buco del censimento di §3, che va dichiarato**: cercando i
consumatori ho grepato il **codice** (`CODICE_NON_MODIFICABILE`) nei pgTAP, non i
**nomi dei trigger** che la bonifica rinomina. Il codice l'avevo trovato in
cinque file, ma solo in righe di descrizione; il nome era in un'asserzione, e
quello no. *Chi consolida dei trigger censisce i nomi, non solo i valori che
portano dentro.*

**Sanato** — e il test ora dice una cosa più forte di prima:

* cerca il lock per **funzione e argomenti**, mai per nome;
* asserisce **entrambe** le colonne. ⚠️ Fino al 22-09 il lock su `codice` **non
  era pinnato da nessuno**: era esattamente ciò che una rigenerazione poteva far
  sparire in silenzio, e adesso c'è un test che se ne accorgerebbe;
* al test 7 è stato dato lo **SQLSTATE** (`P0001`, verificato sul catalogo vivo):
  era `throws_ok(sql, NULL, NULL)`, che accetta qualunque errore — anche una
  fixture rotta — e sarebbe passato senza misurare il lock. ⇒ Il debito del
  guardrail cala da 121 a **120**, e la soglia in
  `scripts/guardrail_pgtap_preambolo.py` è stata abbassata di conseguenza.

⚠️ **Una trappola trovata scrivendo l'asserzione**: `encode(tgargs,'escape')`
termina con un `\000`, quindi `string_to_array` restituisce un elemento **vuoto**
in coda — e la coda cade in posizione **dispari**, cioè fra le colonne. Senza
`AND a <> ''` l'array atteso dovrebbe contenere `''`.

⭐ **Gli altri pgTAP che nominano un trigger di lock non si toccano**: pinnano il
nome **da template** (`trg_<tabella>_a10_lock_columns_upd`), che la rigenerazione
riproduce identico. `catalogo.articoli` era l'unica tabella con trigger di lock
scritti a mano — verificato su `pg_trigger` confrontando ogni nome col template.
⛔ **Falso sul modello**, vedi §5-ter: la verifica era su `pg_trigger` di **dbdev**.

## 5-ter. 🔴 Rosso su zeroerp_ci: i lock scritti a mano che dev aveva perso

Il migrate su zeroerp_ci è andato rosso nel 20260923-02:

```text
LOCK_COLUMNS: tabelle rimaste SENZA lock dopo la rigenerazione: config.iva_stati
```

**Perché su dev è passato e su CI no.** Nel 2025 sono stati scritti a mano due
trigger di lock, `20251006-13` su `config.iva` e `20251006-22` su
`config.iva_stati` (poi rinominati dal `20251119-21`). Nominano
`E_PERC_IVA_NO_MOD` / `E_ASSOGGETTAMENTO_NO_MOD`, ritirati il 2026-08-07 dal
piano-db-classe-codici-errore come «nessuna funzione li solleva»: lo stesso punto
cieco su `tgargs` di §1, in un secondo cantiere.
Sul DB ricostruito da zero i due trigger esistono. Il censimento li prende, li
droppa, e il runner non li ricrea perché il registro non li conosce. Su **dbdev**
invece non c'erano più. Nessun changeSet li toglie e il runner di drop lavora
solo sul nome da template, quindi sono stati tolti fuori da Liquibase, da chi non
si sa. Il censimento su dev non li ha visti.
⇒ **È dev a essere fuori modello, non la CI.**
⛔ **Corretto il 2026-09-26: le due frasi qui sopra sono false.** Il runner di
drop, `dbops.fn_run_automations_drop_lock_trg`, con `existence_strategy = BOTH`
cerca **anche per funzione**: droppa ogni trigger su `script.trgfn_lock_columns`
di una tabella senza `codice_interno` e senza righe attive nel registro, anche
se è scritto a mano. Gira ogni notte alle 21:10 nel job pgAgent, che esiste
solo su dbdev perché `85_pgagent` in CI è `MARK_RAN`. Quindi dev non è fuori
modello: è l'unico ambiente dove il modello gira per intero. Il seguito è in
[brief-db-lock-di-colonna-fuori-registro.md](brief-db-lock-di-colonna-fuori-registro.md).

Anche la frase del changeSet «da
zero il censimento torna vuoto» era falsa: i lock scritti a mano in `20_code`
esistono già alla prima passata (intestazione corretta, solo commenti `#`,
checksum invariato).

⚠️ **Il rosso seguente era già in coda.** (a) solleva prima di (b). Dopo aver
sanato solo `iva_stati`, il controllo (b) avrebbe fermato la CI su
`config.iva.assoggettamento_id`: la colonna era lockata dal trigger a mano e non
dal registro, che copre solo `aliquota_iva` e `natura_iva_id`. Provato per
mutazione, vedi sotto.

**Sanato nel registro**, con tre righe nel CSV, tutte con
`E_IVA_TRATTAMENTO_IMMUTABILE` (stessa regola del codice IVA, stesso codice):

* `config.iva.assoggettamento_id`: gemello di `natura_iva_id`, perché il CHECK
  `chk_iva_zero_requires_natura_or_assogg` li tratta alla pari;
* `config.iva_stati.aliquota_override` e `assoggettamento_id_override`.

In alternativa si potevano riattivare i due codici ritirati (il ritiro era un
falso negativo). Scartata: due codici per una regola che su `config.iva` ne ha già
uno. Il pgTAP `vendite/test-ricalcola-riepiloghi-iva` fa solo INSERT e DELETE su
`iva_stati`, e il BE non scrive sugli override, quindi il lock (solo UPDATE) non
rompe niente di noto.

**Nuovo `90_end/20260923-03-provision-lock-iva-e-iva-stati`.** Da zero le tre
righe bastano, perché il 02 rigenera completo. Su dev no: il 02 è già EXECUTED,
`iva_stati` non ha un trigger e quello di `iva` non copre `assoggettamento_id`
(il runner non aggiunge colonne a un lock esistente). Il 03 rifà solo le tabelle
del perimetro in cui una colonna del registro non è coperta, poi controlla (a)
che le colonne del registro siano coperte e (b) che nessuna colonna sia stata persa.

**Prove** (SQL estratto dallo YAML, `BEGIN … ROLLBACK` su dbdev, 23-09):

1. Il 03 da solo, con le tre righe inserite: rifà `iva` e `iva_stati`. Esce
   `iva` = `codice_interno, aliquota_iva, assoggettamento_id, natura_iva_id` e
   `iva_stati` = i due override. Una seconda passata non fa niente.
2. **Il percorso CI simulato**: trigger a mano rimessi con i codici ritirati,
   quello generato di `iva` tolto, poi 02 e 03. Il 02 rigenera 2 trigger e resta
   verde, il 03 non fa niente.
3. **Mutazione**: lo stesso percorso senza la riga `iva.assoggettamento_id` va
   rosso su (b), con `config.iva.assoggettamento_id`.

⚠️ **Che cosa NON prova**: è dbdev con due trigger rimessi a mano, non un DB
ricostruito da zero. Il verdetto vero è la prossima corsa su zeroerp_ci. Il
censimento dei lock scritti a mano è stato rifatto **dai changelog** (ogni
`CREATE TRIGGER … trgfn_lock_columns(` in `migrations_v2`). Oltre ai due IVA:
`articoli` (già nel registro); `stati_fornitore` e `stati_commessa`, con il solo
`codice_interno`, che il runner locka comunque; `user_emittenti_fiscali`,
`fatture.natura_doc_id` e `fatture_fondi_fattura_source`, che hanno codici vivi e
quindi il 02 non li tocca.
🔍 **Da guardare a parte**: anche `trg_fatture_a10_lock_natura_doc_upd`
(`20260818-28`, EXECUTED) **manca su dbdev**. È il terzo lock sparito da dev
senza un changeSet: qualcosa, fuori da Liquibase, toglie trigger di lock.

## 7. Che cosa resta — ✅ il lato DB è chiuso

### Fatto e verificato il 2026-09-23

| | |
| --- | --- |
| **migrate su dev** | `20260923-01`, `-02`, `-03` `EXECUTED`; mirror del registro `RERAN` alle 09:33 |
| **migrate da ZERO** | gli stessi tre `EXECUTED` anche su **`zeroerp_ci`** — ed è la prova che conta, perché è lì che il difetto di §5-ter si era visto |
| **guardrail dei codici** | esce **0** su dev (prima usciva **3**, nominando i 69 trigger uno per uno) |
| **pgTAP** | rilanciati da Tid: **nessuna regressione**, compreso `catalogo/test-articoli-seed-uom-base-lock` sanato in §5-bis |
| **commit** | `7d67d6d9d` — CSV, i due changeSet nuovi, il guardrail dei codici, `guardrail_pgtap_preambolo.py` (soglia 120), il pgTAP di `catalogo`, le pagine `manual/` e i brief |

**Il verdetto, letto sul catalogo vivo e non dedotto dai file:** zero trigger di
lock con un codice non vivo (dev **e** CI), zero righe malate nelle 43 del
registro, `catalogo.articoli` con un solo trigger su `codice` e `uom_id`,
`config.iva_stati` lockata, i due lock di magazzino armati.

### ✅ Il BE

✅ **Chiuso il 2026-09-23.** I due test di **§4** asseriscono
`E_CODICE_NON_MODIFICABILE` (l'e2e di magazzino e il mock di
`test_config_crud_service.py`, verde 7/7); i quattro commenti citano il codice
vivo e, per `catalogo.articoli`, il lock di colonna **senza** il nome del
trigger, che lo decide l'automazione. Le occorrenze residue del codice vecchio
sono volute: `error_policies_generated.py` / `error_messages_fallback.py` (un
codice ritirato continua a risolversi) e il commento storico dell'e2e.

### 🔍 Resta una domanda sul MODELLO, non un residuo di questo giro

> ➡️ **Passata il 2026-09-26 a
> [brief-db-lock-di-colonna-fuori-registro.md](brief-db-lock-di-colonna-fuori-registro.md)**,
> con la causa di `iva_stati` e `fatture` trovata. Il testo qui sotto resta com'era
> il 23-09.

**dbdev ha perso dei trigger di lock che il database da zero ha.** Misurato il
23-09 confrontando i due cataloghi: dev **89** trigger di lock, `zeroerp_ci`
**90**, e la differenza è una sola tabella —

```text
vendite.fatture → trg_fatture_a10_lock_natura_doc_upd (natura_doc_id, E_COLONNA_NON_MODIFICABILE)
```

⭐ **Sta su CI e non su dev**, come era per `config.iva` e `config.iva_stati` in
§5-ter. ⚠️ E questo terzo caso **non c'entra con i codici ritirati**:
`E_COLONNA_NON_MODIFICABILE` è vivo, quindi la bonifica non l'ha mai toccato —
il trigger è sparito da dev prima, per altra via. Sono **tre** tabelle con la
stessa storia: un lock scritto a mano in `20_code`, presente su un DB
ricostruito e assente su dev.

⇒ Due cose distinte, e vanno tenute distinte:

1. **Chi toglie quei trigger da dbdev, e quando.** Finché non si sa, *dev non è
   un metro*: un presidio verde lì può essere verde perché la cosa che doveva
   presidiare non c'è. È la stessa lezione di §5-ter, dove è stata la corsa da
   zero a dire la verità;
2. **Una convergenza generale «trigger vivo = registro»**, che oggi il runner
   non fa (è create-if-missing) e che i due changeSet di questo giro hanno fatto
   a mano su perimetri fissi. ⛔ Non si allarga di straforo il `20260923-03`:
   è un cantiere `dbops` suo, e va deciso.

---

## Nota di metodo — che cosa si porta via chi legge

⭐ **Un censimento vale quanto la superficie su cui è fatto, e la superficie va
dichiarata.** `20260805-26` scrisse «elenco COMPLETO … ricavato da `pg_proc`»: la
prima metà era una promessa, la seconda era il suo limite, e nessuno le lesse
insieme. Il presidio nato per quel ritiro ereditò la stessa superficie, quindi non
poteva che essere d'accordo.

⭐ **Un valore che viaggia come DATO non si trova cercando CODICE.** Vale per i
`TG_ARGV` di una funzione generica, e vale per ogni riga di registro che un
generatore trasformerà in DDL: sono **call site differiti**, e il momento in cui
sbagliano non è quando li scrivi.

⭐ **Prima di droppare per rigenerare, chiedi che cosa il vivo sa e la sede no.**
Qui erano due lock su due colonne, in vigore da anni fuori dal registro. Il
controllo che li ha trovati è rimasto nel changeSet: costa nulla e la prossima
volta parla.
