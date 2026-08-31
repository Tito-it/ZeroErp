# Collaudo in-app · l'esito parziale del pull da commessa

> **Cos'è.** Il copione della validazione a video: si tiene aperto accanto
> all'applicazione e si spunta. Non è il brief — il *perché* di ogni scelta sta
> in [brief-be-fan-out-isolato-e-esito-parziale.md](brief-be-fan-out-isolato-e-esito-parziale.md)
> §13.1 (voce **V1**); qui c'è solo **cosa fare, cosa deve succedere, e cosa
> fare se non succede**.
>
> **Stato**: 🔴 **APERTO** — nessuna prova eseguita. · **Ambiente**: sviluppo
> (`dbdev`). · **Pagine**: `Vendite → Fatturazione` (cockpit) e `vendite/lotti`.
>
> **Perché esiste.** È l'ultima voce di **V1**, e l'unica cosa che tiene aperto
> il cantiere del fan-out insieme alle due di V2. Il codice è scritto dal
> 2026-08-09, i test sono verdi, e il **telaio** del BB `run_fan_out` è stato
> esercitato in applicazione il 2026-08-26 — ma su un **altro** consumatore
> (l'accredito massivo, prova 5 di
> [collaudo-in-app-nota-credito-resi.md](../work-done/collaudo-in-app-nota-credito-resi.md)).
> Sul **pull da commessa** il ramo parziale non è **mai** stato percorso: la
> misura del 2026-08-16 lo dice senza margini — zero run in
> `vendite.fatturazione_lotti_task_runs` dal 2026-08-03, e i 13 run storici del
> task erano **tutti** `COMPLETATO`, tutti precedenti al fix.
>
> ⭐ **E la ragione vera per cui questo documento esiste è una sola riga dei
> test.** I tre test che coprono il caso portano
> `@patch("apps.core.services.fan_out.transaction")`: **il savepoint è mockato
> via**. Quindi la proprietà su cui poggia tutto il cantiere — *«una commessa
> rifiutata non si porta via il lavoro di quelle passate prima»* — è oggi
> **asserita e mai eseguita** su questo percorso. Se si rompesse, si romperebbe
> in silenzio: attività perse, nessun errore, un lotto che sembra a posto.

---

## ⛔ Cinque cose da sapere prima di cominciare

**1 · ⚠️ Il guasto lo inietti tu, nei dati, e va DISFATTO.** Non esiste un modo
di far fallire una commessa «per caso»: si crea la condizione di errore a mano
(§La materia), si esegue il giro, e **si ripristina**. Se ti fermi a metà, resta
una commessa che non emette più — e nessuno saprà perché.

**2 · ⚠️ `kill -HUP` sul master gunicorn PRIMA di cominciare.** Il backend di
sviluppo non ha autoreload: senza il segnale gira ancora il codice vecchio e la
prova direbbe il falso. È lo stesso prerequisito del §13.1 del brief, ed è la
ragione per cui la misura del 2026-08-16 fu inconcludente.

**3 · ⛔ Le azioni sul database non le fa l'agent.** Le tre `UPDATE` di questo
documento (guasto + ripristino) le esegui tu o le giri al team DB. Sono di sola
manutenzione del dato, reversibili, e scritte per esteso.

**4 · Nessun documento fiscale viene bruciato.** Il giro si ferma **prima** della
numerazione: si lavora su un lotto in `DRAFT`, si guardano i `task_run` e le
attività. ⛔ **Non premere «Rendi definitive»** in nessuna delle prove.

**5 · L'ordine conta.** Le prove **1 → 2** preparano e osservano; la **3** è il
cuore (il rilancio che ritenta); la **4** ripristina e chiude il giro; la **5**
è il caso tutto-rosso e va per ultima, perché lascia lo step fermo.

---

## La materia

> ⚠️ **I soggetti NON sono stati misurati, ed è dichiarato.** Gli altri collaudi
> di questa serie aprono con una tabella di dati veri presi il giorno prima.
> Qui no: chi ha scritto il copione non ha interrogato il database. Quindi la
> sezione dice **quali proprietà** deve avere la materia e **come trovarla**,
> non quali id usare. Un id inventato in un copione è peggio di un id assente —
> sembra verificato.

### Cosa serve

Un **mese di competenza** il cui perimetro contenga **almeno due commesse
emittibili** — meglio tre. Una farà da guasto, le altre da controprova.

Lo trovi da `Vendite → Fatturazione`: scegli l'anno e scorri i mesi finché la
card **«Da emettere»** ne mostra almeno due. In alternativa, la lista
**gruppi fatturabili** dello stesso cruscotto elenca le unità dell'emissione e
dice a quale commessa appartengono.

### Il guasto: togliere la ROOT source a **una** commessa

`vendite.fn_emit_attivita_fatturabili_da_commessa` può sollevare in tre punti.
Ne serve **uno solo**, e la scelta è motivata:

| Strada | Perché sì / no |
| --- | --- |
| ⭐ **ROOT source mancante** → `E_VALORE_MANCANTE` | **questa.** Condizione **di dato**, mirata su **una** commessa, e **reversibile** con un `UPDATE` che rimette tutto com'era |
| `E_RIGA_GIA_FATTURATA` | serve una riga già fatturata: si costruisce solo passando da un giro precedente, ed è più intricata da disfare |
| `E_CODICE` su `config.sorgenti` COMMESSA | ⛔ **no**: è configurazione **globale**, farebbe fallire *tutte* le commesse e romperebbe il sistema per chiunque altro stia lavorando |

**Perché funziona** — righe 73-85 della funzione: la ROOT è obbligatoria, e se
manca solleva `E_VALORE_MANCANTE` con dettaglio *«ROOT source mancante per
commessa N»*.

⭐ **E non si CANCELLA la riga: le si cambia il ruolo.** La commessa è
multi-sorgente (1 ROOT + N COLLEGATO) e l'unicità è **parziale, solo sulla
ROOT** (`uq_commesse_sorgenti_commessa_root`) — quindi portarla a `COLLEGATO`
è ammesso, non perde niente, e si torna indietro con l'`UPDATE` speculare.
Una `DELETE` distruggerebbe il legame documento→commessa.

```sql
-- GUASTO — sostituisci <commessa_id>. Annotati il valore prima di eseguire.
UPDATE vendite.commesse_sorgenti
   SET ruolo_link = 'COLLEGATO'
 WHERE commessa_id = <commessa_id>
   AND ruolo_link = 'ROOT';
```

```sql
-- RIPRISTINO — la stessa riga, al contrario. Da eseguire nella prova 4.
UPDATE vendite.commesse_sorgenti
   SET ruolo_link = 'ROOT'
 WHERE commessa_id = <commessa_id>
   AND ruolo_link = 'COLLEGATO';
```

⚠️ **Prima di guastare, annota quali commesse sono nel perimetro e quali no.**
Serve alla prova 2: senza l'elenco di partenza, «le altre sono passate» non è
verificabile.

### Il prerequisito che decide il senso della prova 3

Il rilancio ritenta **solo se** la policy del task lo ammette:
`vendite.fn_resolve_lotto_task_execution_mode` dà `RESUME` su ultimo run in
`ERRORE` **quando** `resume_mode` è `RESUME_TASK` o `RESUME_STEP`; altrimenti dà
`RESET_REQUIRED`.

```sql
-- Deve rispondere RESUME_TASK. Se risponde altro, la prova 3 va riletta.
SELECT pipeline_id, task_code, resume_mode, annullabile
  FROM vendite.fatturazione_pipeline_task_policy
 WHERE task_code = 'pull_attivita_da_commessa';
```

- [ ] `resume_mode` = **`RESUME_TASK`** su tutte le righe.

> 📌 Al seed è `RESUME_TASK` per la pipeline **1** (MASSIVO) e la **8**
> (GIORNALIERO). Il controllo serve a escludere che sia stato cambiato dopo.

---

## Prove

### 1 · Il giro **non si ferma**, e il task_run va in **ERRORE**

**Dove**: `Vendite → Fatturazione`, mese scelto. Applica il **guasto** a una sola
commessa, poi lancia **«Fattura adesso»** (o l'emissione mirata sui gruppi, se
preferisci restringere il perimetro).

- [ ] il giro **arriva in fondo**: non compare un errore rosso che ferma tutto;
- [ ] viene creato un **lotto**, e lo trovi in `vendite/lotti`.

Apri il lotto, scheda **Task** (i `task_run`):

- [ ] la riga di **`pull_attivita_da_commessa`** ha stato **`ERRORE`**, non
      `COMPLETATO`;
- [ ] il suo `meta` porta i quattro numeri: `totale`, `ok`, `falliti`, e
      **`commesse_fallite`** con dentro **l'id della commessa che hai guastato**.

⚠️ **Se il task_run è `COMPLETATO`**: è il difetto originale del cantiere,
tornato. Un parziale chiuso in COMPLETATO significa che al rilancio il resolver
dirà `SKIP` e la commessa rimasta indietro **non verrà mai più ritentata**.
Fermati e segnala — è la cosa che questo cantiere esisteva per correggere.

⚠️ **Se il giro si è fermato con un errore rosso**: guarda il codice. Se è
`E_PULL_COMMESSA_ALL_FAILED`, il perimetro conteneva **una sola** commessa e hai
fatto la prova 5 per sbaglio: rimetti la ROOT, allarga il perimetro, ricomincia.

### 2 · ⭐ Le commesse **sane** sono passate — e sono RIMASTE

> È la prova che conta più di tutte. Il savepoint per commessa è la proprietà
> che i test **non eseguono** (transazione mockata): se è rotto, il rollback
> della commessa rifiutata si porta via anche il lavoro di quelle passate prima,
> **senza nessun errore**.

Sul lotto, scheda **Documenti**:

- [ ] ci sono documenti, e **non sono zero**;
- [ ] le attività delle commesse **non guastate** sono dentro — confronta con
      l'elenco che ti eri annotato.

Poi, sul cruscotto (`Vendite → Fatturazione`, stesso mese):

- [ ] le commesse sane **non compaiono più** fra quelle da emettere;
- [ ] la commessa guastata **c'è ancora**: il suo lavoro non è stato consumato.

⚠️ **Se il lotto è vuoto, o mancano attività di commesse che non hai toccato**:
🔴 **fermati e segnala.** È l'isolamento per item che non regge, ed è il difetto
peggiore possibile su questo percorso — silenzioso, e con perdita di lavoro.

### 3 · 🔴 IL CUORE — il rilancio **RITENTA**, non salta

> Questa prova chiude l'unica voce che nessun altro percorso ha mai esercitato.
> Fino al 2026-08-09 qui il rilancio faceva **SKIP** e la commessa rimasta
> indietro spariva in silenzio, per sempre.

**Prima**, verifica cosa dice il resolver — sostituisci `<lotto_id>` e
`<pipeline_id>` (li leggi sul lotto):

```sql
SELECT execution_mode, last_task_stato, last_tentativo
  FROM vendite.fn_resolve_lotto_task_execution_mode(
         <lotto_id>, <pipeline_id>, 'pull_attivita_da_commessa');
```

- [ ] `last_task_stato` = **`ERRORE`**;
- [ ] `execution_mode` = **`RESUME`** — ⛔ **non `SKIP`**.

⚠️ **Se dice `SKIP`**: il difetto è tornato, e la prova 1 aveva già dato il
segnale (task_run COMPLETATO). ⚠️ **Se dice `RESET_REQUIRED`**: la policy non è
più `RESUME_TASK` — vedi il prerequisito nella Materia.

**Poi** rilancia lo step **lasciando il guasto in piedi**, dal drawer del lotto.

- [ ] il pulsante c'è e si può premere: **«Riprova step»** se il lotto è in
      `ERRORE`, **«Rigenera la bozza»** se è stato riportato in lavorazione,
      **«Avanza step»** altrimenti;
- [ ] il tentativo **riparte** e la commessa guastata viene **ritentata** — nella
      scheda **Task** compare un run **nuovo** (`last_tentativo` incrementato),
      non un salto;
- [ ] fallisce **di nuovo**, con lo stesso motivo: il guasto è ancora lì, ed è
      giusto così.

⚠️ **Se «Avanza step» è DISABILITATO** con il tooltip sulle segnalazioni: è
atteso e non è un difetto — il pull scrive una segnalazione **critica** per ogni
commessa fallita (`E_PULL_COMMESSA`, severity `C`), e le criticità bloccano
l'**avanzamento**. Il rilancio dello **stesso** step invece è ammesso di
proposito (`is_rilancio_stesso_step` nel runner): è la via d'uscita.
🔴 **Ma se NESSUNO dei tre pulsanti è premibile**, l'operatore è in un vicolo
cieco — il lavoro non è recuperabile da video. **Fermati e segnala**: sarebbe un
difetto di percorso, non di calcolo, e nessun test poteva vederlo.

### 4 · Rimosso il guasto, il lavoro **torna a casa**

Esegui il **RIPRISTINO** (la `UPDATE` speculare della Materia), poi rilancia lo
step ancora una volta.

- [ ] il task_run **nuovo** chiude in **`COMPLETATO`**;
- [ ] le attività della commessa prima guastata sono **entrate** nel lotto;
- [ ] sul cruscotto quella commessa **non risulta più** da emettere;
- [ ] ⭐ e non ci sono **doppioni**: le attività delle commesse sane non sono
      state emesse due volte.

⚠️ **Se compaiono doppioni**: l'idempotenza dell'emit non regge al ri-tentativo.
La funzione mappa `segment_key` in UUID deterministico proprio per evitarlo —
segnala con l'id della commessa.

### 5 · Il caso **tutto-rosso** — e lo step si ferma

> Ultima, perché lascia lo step fermo e va poi ripulita.

Applica il guasto a **tutte** le commesse del perimetro (se sono poche; se sono
molte, restringi il perimetro con l'emissione mirata a un gruppo solo, poi
guasta quella commessa). Lancia il giro.

- [ ] lo step **si ferma**, e non prosegue a costruire un lotto vuoto;
- [ ] l'errore è **`E_PULL_COMMESSA_ALL_FAILED`**;
- [ ] il messaggio dice **quante** su quante (`Errori: N/N`) e l'esito riporta i
      primi motivi per-commessa.

⚠️ **Se invece lo step prosegue e nasce un lotto senza documenti**: è il ramo
«tutte fallite» degradato a parziale. Un lotto vuoto che avanza è peggio di uno
step fermo — segnala.

**Poi ripristina tutto** e verifica di essere tornato al punto di partenza:

- [ ] tutte le commesse toccate hanno di nuovo `ruolo_link = 'ROOT'`;
- [ ] il mese di competenza torna a mostrare le commesse da emettere.

```sql
-- Controllo finale: nessuna commessa deve essere rimasta senza ROOT.
SELECT c.id
  FROM vendite.commesse c
  LEFT JOIN vendite.commesse_sorgenti cs
    ON cs.commessa_id = c.id AND cs.ruolo_link = 'ROOT'
 WHERE cs.id IS NULL;
```

- [ ] la query non restituisce **nessuna** delle commesse che hai toccato.

---

## Verbale

**Chiuso il**: — · **Da**: — · **Ambiente**: sviluppo (`dbdev`)

| # | Prova | Scrive | Esito | Note |
| --- | --- | --- | --- | --- |
| 0 | La policy del task è `RESUME_TASK` | no | | |
| 1 | Il giro non si ferma, il task_run va in **ERRORE** | **sì** | | |
| 2 | ⭐ Le commesse sane sono passate **e rimaste** (savepoint) | no | | |
| 3 | 🔴 Il rilancio **RITENTA**, non salta | **sì** | | |
| 4 | Rimosso il guasto, il lavoro torna a casa senza doppioni | **sì** | | |
| 5 | Tutto-rosso → `E_PULL_COMMESSA_ALL_FAILED`, step fermo | **sì** | | |

### Che cosa ha trovato il collaudo

> Da compilare. Se non trova niente, si scrive che non ha trovato niente — è
> un'informazione, non un vuoto.

---

## Quando questo verbale è chiuso

La voce **V1** del §13.1 di
[brief-be-fan-out-isolato-e-esito-parziale.md](brief-be-fan-out-isolato-e-esito-parziale.md)
si chiude, e con lei la metà **pipeline** dell'esito parziale — l'altra metà, il
**telaio** del BB, è già validata dal collaudo nota di credito del 2026-08-26.

Restano allora le due voci di **V2**: il ramo `CONFERMATO` di **DL-23** (nessun
soggetto, va costruito) e la verifica dell'**area RESI** delle card, che dal
2026-08-26 non è più bloccata. Chiuse quelle, il brief va in `work-done` e la
linea del fan-out chiude per intero.

⚠️ **Se una prova fallisce, non aggiustare il dato**: annota cosa hai visto e
passa alla successiva — tranne la 2, dove un difetto significa perdita di lavoro
e conviene fermarsi. E **ripristina sempre le ROOT** prima di chiudere la
sessione, comunque sia andata.
