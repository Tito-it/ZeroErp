# Brief DB — magazzino, Lotto 2: il motore

> **Destinatario:** team DB (`dev/db-tid`). 🔵 **Due richieste a BE/FE**, in §4.9 e
> §4.10, da fare **nello stesso giro di PR**: senza, la CI del merge è rossa
> (codici senza ripiego, `reason_key` senza chiave i18n). Il resto del BE di
> magazzino — il primo endpoint, il drawer dell'inventario — **non nasce qui**:
> è un brief BE/FE suo, e parte quando questa primitiva esiste.
>
> **Origine.** Analisi [carico e scarico §8](../work-in-progress/analisi-db-magazzino-carico-e-scarico.md)
> (spacchettamento del 2026-09-14): *«Lotto 2 — DB, motore: la primitiva (M-2),
> la `fn_check` di disponibilità separata, l'operazione inventario iniziale
> (passo 2), la vista situazione merce (M-3, senza le colonne che aspettano il
> satellite D-17), la vista degli orfani (D-9), il presidio di prontezza su
> `gestito_a_magazzino`, i pgTAP di comportamento (M-7). ⚠️ Con `requires_lotto`
> esposto in vista/BE/drawer senza il lock BoM di `requires_serial`»*. I due
> prerequisiti sono **chiusi**: il Lotto 1
> ([brief](brief-db-magazzino-lotto-1-terreno-vuoto.md), 15-09,
> PR #1593) e il BB dell'emittente di default
> ([brief](brief-db-emittente-di-default-un-bb-solo.md), 17-09,
> `20260915-36 → -46` `EXECUTED`).
>
> **Stato:** ✅ **LATO DB CHIUSO il 2026-09-18** — ventidue changeSet
> `20260918-06 … -27` **`EXECUTED` su dbdev** (i ventuno del lotto alle 12:23,
> il `-27` nel pomeriggio), tre sedi della postura in place, 27 codici
> `E_MAG_*`, 4 presidi in `dbops`, **dodici pgTAP nuovi + tre ri-collocati
> verdi col runner come app**, e verdi anche i due presidi **trasversali** che
> il primo giro del runner aveva reso rossi (`dbops/test-riferimenti-morti-v1`,
> `script/test-rubinetto-primo-motivo-v1` — §7, §11). Le quattordici decisioni
> D-L2-a → D-L2-n sono di Tid (17-09); le sedici criticità C1–C16 di P-0 sono
> tutte chiuse (§6-ter).
>
> 📦 **ARCHIVIATO il 2026-09-24** in `work-done/` (decisione di Tid), dopo la chiusura
> della porta coi verbi (`brief-db-magazzino-verbi-con-permesso`, nota in D-L2-b).
>
> ✅ **E dal 2026-09-22 il lotto è CONSEGNATO INTERO** (§12.5): B-7 `--update`
> fatto e committato, commit `787ab05ba` mergiato in `Tito-dev` (PR #1605), le
> due richieste a BE/FE di §4.9 e §4.10 consegnate, la **CI da zero verde con
> la suite pgTAP** (corsa `35451924195`, 19-09, che contiene questo commit) e
> la **prova del lock a due sessioni eseguita**: B ha atteso 8,1 s il rilascio
> di A e poi ha riletto la disponibilità sul saldo committato (§12.5.4).
> ⏳ Resta **un solo ramo dichiarato non provato** — «…oppure passa sul saldo
> aggiornato», che vorrebbe una prima sessione che **committa** un movimento su
> dbdev — e `ci-local.sh --fresh --ci-apply`, che la corsa vera di CI ha reso
> ridondante. 🔵 **Decisione di Tid, 22-09: il brief resta in `work-in-progress/`** —
> il lotto è consegnato, l'archiviazione si farà quando lo dirà lui.
>
> **Perimetro:** il **codice che scrive** su `magazzino.movimenti` e su
> `valore_giacenza` — la primitiva e le due operazioni **senza documento
> commerciale** (inventario, rettifica) — con la **porta** che rende quella
> scrittura l'unica possibile; il controllo di disponibilità che UI e primitiva
> condividono; le viste che rileggono (disponibilità, orfani, divergenza del
> valore, prontezza); i pgTAP di **comportamento**. ⛔ Fuori: lo scarico da DDT,
> lo storno, il trasferimento, gli eventi asset, la ricezione, la produzione —
> la §9 dice dove sta ciascuno e perché.
>
> ⚠️ **Le decisioni non si ridiscutono qui.** Ogni riga cita la decisione da
> cui discende (M-* di carico/scarico, D-* dell'aggancio, D-L1-* del Lotto 1).
> Se una riga non ha una decisione dietro, è in §3 con una raccomandazione —
> oppure è un difetto di questo brief.
>
> ⚠️ **Le sei lezioni del Lotto 1 sono la §5 di questo brief**, non un
> rimando: il 15-09 sette cose erano verdi in sessione per ragioni sbagliate e
> le ha trovate il DB da zero o il runner. Qui il rischio è **più alto**, perché
> il lotto scrive codice che si esegue e non solo forma.

---

## 0. In due parole, senza tecnicismi

Il Lotto 1 ha messo le tabelle nella forma decisa e ha chiuso il recinto (chi
vede che cosa). Ma **nessun programma scrive ancora nel registro**: la porta è
aperta e dentro non passa nessuno.

Questo lotto costruisce **il motore**:

* **una sola funzione che scrive un movimento**, con dentro tutti i controlli
  — il verso, la merce che non può andare sotto zero, il lotto e il seriale
  quando l'articolo li pretende, il valore che si aggiorna — e **la chiude a
  chiave**: da adesso nel registro non scrive nessun altro, nemmeno per
  sbaglio;
* **le prime due cose che un magazziniere fa senza un documento
  commerciale**: contare la merce (l'inventario, che al primo giro è il primo
  carico in assoluto) e correggere un errore (la rettifica). Sono le sole due
  operazioni di questo lotto, e sono quelle che collaudano il registro senza
  dipendere da nessuna catena;
* **il numero su cui si decide**: quanto c'è, quanto è bloccato per qualcuno,
  quanto se ne può ancora usare — lo stesso conto che la funzione fa prima di
  scrivere, così la scheda non promette mai ciò che il sistema rifiuterà;
* **tre spie** che devono restare spente: un movimento che punta a un
  documento sparito, un valore di giacenza che non torna col registro, e
  «nessun articolo è ancora marcato come gestito a magazzino» — quest'ultima
  esiste perché al rilascio *nessun* articolo lo è, e senza una spia il
  magazzino resterebbe un mobile vuoto senza che nessuno se ne accorga.

Non fa uscire merce con una bolla di vendita e non gestisce gli acquisti:
quelli sono i lotti dopo, e arrivano su un registro **già provato**.

---

## 1. Il filtro: che cosa entra qui, e perché adesso

Entra ciò che soddisfa **tutte e tre** le condizioni:

1. è **deciso** (M-1 → M-9, D-1 → D-9, D-L1-a → D-L1-g);
2. è **il codice che la forma del Lotto 1 aspetta**: la primitiva, ciò che la
   primitiva legge (il controllo di disponibilità), ciò che la primitiva
   alimenta (il valore), le operazioni che **non hanno un documento
   commerciale a monte** e le viste che rileggono;
3. **non tocca un documento di un altro dominio**: niente `vendite.ddt`,
   niente `acquisti`, niente `eventi_assets`. Il primo scrittore deve poter
   sbagliare **da solo**, su un dominio che ha solo sé stesso da rompere.

⭐ **La terza condizione è la ragione della sequenza di §8** dell'analisi:
*«inventario iniziale come primo carico: non ha un documento a monte, quindi
collauda il registro senza dipendere da nessuna catena»*. E il 14-09 la D-6 ha
aggiunto la rettifica alla stessa famiglia — *«la correzione a mano È una
rettifica»* — quindi le operazioni senza documento commerciale sono **due**,
e si fanno insieme (D-L2-g).

⚠️ **E la porta entra qui, non «quando ci sarà un secondo scrittore»** — è la
§5 dell'analisi: *«su `magazzino.movimenti` scrive solo la primitiva. È un
`GRANT`, non un vincolo — ed è l'unica forma che ferma davvero chi non passa
dalla porta»*. Il Lotto 1 §9 lo dice in una riga che vale il lotto: *«finché
non c'è, `movimenti` resta scrivibile dall'app: il perimetro RLS c'è, la porta
no»*. Un registro con un solo scrittore **e la porta aperta** è un registro
con N scrittori potenziali e nessuno che lo sa.

---

## 2. Le decisioni da cui discende ogni riga

| Decisione | Dove | Che cosa impone qui |
| --- | --- | --- |
| **M-1** verso nella quantità | c/s §4 | la primitiva riceve `qta` **firmata** (D-L2-a), la confronta con `causali.segno` **subito dopo aver risolto la causale**, prima di ogni controllo di dominio, e solleva `E_MAG_MOVIMENTO_VERSO_INCOERENTE` con la frase; il trigger di Lotto 1 resta **la rete** |
| **M-2** primitiva + operazioni | c/s §5-bis | **due livelli**: `magazzino.fn_scrivi_movimento` con tutti i controlli duri; le operazioni non ricontrollano niente e la chiamano in **una** transazione. Guidata da **due cataloghi** (causale: verso, stock negativo, rettifica · articolo: gestito, lotto, seriale). Blocco su `(magazzino, articolo)`, **solo in uscita**, **prima** di leggere. ⛔ Nessuna domanda dentro la scrittura |
| **M-3** disponibile | c/s §7-bis | `disponibile = sum(movimenti.qta) + sum(movimenti_attesi.qta dei blocchi altrui)` — in **colonne**, non a parole, ed è **la stessa funzione** che la UI chiama e la primitiva usa per rifiutare (§4.3). L'impegno derivato **non si sottrae**; le colonne impegnata/potenziale/in arrivo **aspettano D-17** e qui non nascono (D-L2-j) |
| **M-4** valorizzazione | c/s §7-ter | la primitiva aggiorna `valore_giacenza` (**valore**, mai la quantità); `costo_unitario` con i **tre** significati (D-L2-c); `fn_ricalcola_valore_giacenza` = **ri-somma**, mai ri-esecuzione; vista di divergenza che deve restare vuota |
| **M-5** lotti, seriali, ubicazioni | c/s §7-quater | **decide l'articolo**: `requires_lotto` ⇒ `lotto_id` obbligatorio e dell'articolo; `requires_serial` ⇒ `asset_id` obbligatorio, dell'articolo e dell'emittente, `\|qta\| = 1`, **posizione derivata** difesa (D-L2-e); `ubicazione_id` del magazzino (controllo cross-tabella rinviato qui dal Lotto 1 §4.4); `requires_lotto` in vista/BE/drawer **senza** lock BoM (Lotto 1 §4.3) |
| **M-6** perimetro | c/s §7-sexies | la primitiva **non attraversa mai due emittenti**: il magazzino è l'ancora, e la DEFINER (D-L2-b) resta dentro il perimetro **con il guard di scrittura BB**, non con un controllo scritto a mano |
| **M-7** pgTAP | c/s §9 | i test di **comportamento** (§7), come l'applicazione, con fixture costruite; i tre file di Lotto 1 che scrivono direttamente sul ledger si **ri-collocano** (§5) |
| **M-8** storno | c/s §7-quinquies | qui **solo il ramo della primitiva**: `storno_di_movimento_id` ⇒ costo **dell'originale**, verso opposto, sorgente ereditata; la utility è del Lotto 3 |
| **M-9** allocazione | c/s §7-septies | niente: chiusa come non necessaria |
| **D-1 / D-6** sorgente a catalogo, obbligatoria | aggancio §8-quater | la primitiva **riceve** la sorgente (tipo + una chiave) e la scrive; a verificarla resta il guard tipizzato del Lotto 1 — la primitiva non lo duplica |
| **D-4 / D-L1-c** identità | idem, Lotto 1 §3 | la primitiva **cerca l'identità prima di scrivere** e risponde `E_MAG_MOVIMENTO_GIA_REGISTRATO` con l'id esistente: il `UNIQUE` resta la rete, la madre dà il messaggio (c/s §6: *«il controllo dentro la funzione resta e serve a dare un messaggio comprensibile»*) |
| **D-7** operazioni a catalogo | idem | le operazioni risolvono la sorgente per `codice_interno` (`INVENTARIO_RIGA`, `RETTIFICA_RIGA`), mai per id |
| **D-9** presidi | idem | la **vista degli orfani**, generica su `config.sorgenti` (§4.7) |
| **D-L1-a** UoM base | Lotto 1 §3 | la primitiva **non converte**: riceve `qta` già in UoM base e lo scrive nel `COMMENT`; la conversione è dell'operazione — e le due di questo lotto lavorano su righe che **sono già** in UoM base (`inventari_righe.qta_contata`, `rettifiche_righe.qta_delta` non hanno una UoM propria) |
| **D-L1-b** attesi `APERTA`/`CHIUSA` | idem | la disponibilità legge **solo le `APERTA`**; il blocco si libera portandolo a `CHIUSA` (operazione non di questo lotto, §9) |
| **D-L1-d** causali dello storno | idem | il ramo storno della primitiva pretende `STORNO_POS`/`STORNO_NEG` col verso opposto all'originale |
| **presidio di prontezza** | brief modifiche certe §7, c/s §8 riquadro | vista `dbops` a **una riga**, `MARCATI`/`NESSUNO_MARCATO`, natura `ZERO`, `stato_atteso = MARCATI` (§4.8) |

---

## 3. ⚠️ Le quattordici decisioni piccole che il motore richiede — ✅ tutte prese il 2026-09-17

> Sono uscite scrivendo la firma della primitiva e il corpo delle operazioni,
> non le analisi. Ognuna ha una raccomandazione. ⭐ Dove la raccomandazione è
> «più lavoro adesso», la ragione è scritta sul **modello**, mai sulla
> comodità.

### D-L2-a — La firma della primitiva → **quantità FIRMATA, causale per `codice_interno`, ritorna l'id** — ✅ confermata da Tid il 2026-09-17

```
magazzino.fn_scrivi_movimento(
    p_magazzino_id      magazzino.movimenti.magazzino_id%TYPE,
    p_articolo_id       magazzino.movimenti.articolo_id%TYPE,
    p_causale           magazzino.causali.codice_interno%TYPE,   -- 'INV_INIZIALE', 'RETT_NEG', …
    p_qta               magazzino.movimenti.qta%TYPE,            -- FIRMATA: un'uscita è −10
    p_sorgente_tipo_id  magazzino.movimenti.sorgente_tipo_id%TYPE,
    p_sorgente_riga     magazzino.movimenti.sorgente_riga%TYPE  DEFAULT NULL,
    p_sorgente_uid      magazzino.movimenti.sorgente_uid%TYPE   DEFAULT NULL,
    p_costo_unitario    magazzino.movimenti.costo_unitario%TYPE DEFAULT NULL,  -- vedi D-L2-c
    p_lotto_id          magazzino.movimenti.lotto_id%TYPE       DEFAULT NULL,
    p_asset_id          magazzino.movimenti.asset_id%TYPE       DEFAULT NULL,
    p_ubicazione_id     magazzino.movimenti.ubicazione_id%TYPE  DEFAULT NULL,
    p_data_mov          magazzino.movimenti.data_mov%TYPE       DEFAULT now(),
    p_transfer_uid      magazzino.movimenti.transfer_uid%TYPE   DEFAULT NULL,
    p_storno_di_movimento_id magazzino.movimenti.storno_di_movimento_id%TYPE DEFAULT NULL,
    p_meta              magazzino.movimenti.meta%TYPE           DEFAULT '{}'
) RETURNS magazzino.movimenti.id%TYPE
```

**Firmata e non assoluta**, ed è una scelta. L'alternativa — `p_qta > 0`, il
verso lo mette la primitiva dalla causale — rende impossibile a un chiamante
di contraddirsi, ma **nasconde il verso nella chiamata**: `('SCARICO_VEN', 10)`
si legge come un'entrata di dieci. M-1 ha scelto A perché *il movimento porta
il proprio verso come fatto*; chi lo scrive lo dice esplicitamente, e la
causale **valida**, come sul ledger. Il prezzo è un controllo in più nella
primitiva (`sign(p_qta) = segno`, **primo** fra tutti: senza, un'uscita
passata col segno sbagliato arriverebbe al controllo di disponibilità come
entrata e produrrebbe un rifiuto sbagliato o un passaggio silenzioso). ⭐ Ed è
**una convenzione sola per due tabelle**: sugli attesi la quantità la scrive
chi apre il blocco, firmata, e la valida lo stesso trigger.

**Per `codice_interno`, non per id**: le operazioni nominano la causale come
costante (`'INV_INIZIALE'`), il seed le dà l'id — un id nel codice è una
fotografia del seed (linee-guida-sql §6b). Causale assente o `attivo = false`
⇒ `E_CONFIG_MANCANTE` (`TECNICO`: un pezzo non configurato, non un dato
dell'operatore; è la famiglia `NOT_FOUND` su un catalogo che quel codice porta
già, quindi il rubinetto non lo ferma).

### D-L2-b — La porta → **DEFINER del proprietario, `zeroerp_app` in sola lettura sul ledger, perimetro col guard BB** — ✅ confermata da Tid il 2026-09-17

> ⚠️ **Porta chiusa a metà — riletto il 2026-09-24.** La porta decide **da dove**
> si scrive, non **chi** può scrivere: l'app conserva `EXECUTE` su
> `fn_scrivi_movimento` e `fn_ricalcola_valore_giacenza` (può saltare le
> operazioni), e nessuna delle quattro funzioni controlla un permesso
> (`registra_magazzino` lo guarda solo il backend). ✅ **Completata il 2026-09-24**
> (`20260924-38` → `-42` applicati, pgTAP verdi): i due verbi applicano
> `registra_magazzino` e l'app non esegue più primitiva e ricalcolo. Dettaglio in
> [brief-db-magazzino-verbi-con-permesso.md](../work-in-progress/brief-db-magazzino-verbi-con-permesso.md),
> primo cantiere del modello deciso in
> [brief-db-permesso-nel-verbo-di-scrittura.md](../work-in-progress/brief-db-permesso-nel-verbo-di-scrittura.md)
> (D-4). Il testo qui sotto resta com'era: descrive ciò che è stato consegnato.

| Chi | Che cosa può fare, da questo lotto |
| --- | --- |
| `zeroerp_app` su `magazzino.movimenti` | **solo `SELECT`** — `REVOKE INSERT, UPDATE, DELETE` |
| `zeroerp_app` su `magazzino.valore_giacenza` | **solo `SELECT`** — la copia la scrive la primitiva (e il ricalcolo) |
| `zeroerp_app` su `magazzino.movimenti_attesi` | `SELECT, INSERT, UPDATE`, **senza `DELETE`**: un blocco si **chiude** (D-L1-b), non si cancella |
| `magazzino.fn_scrivi_movimento`, `fn_ricalcola_valore_giacenza` | **`SECURITY DEFINER` del PROPRIETARIO** (`titodb` su dbdev, `zeroerp` in CI — chi migra possiede anche le tabelle), `SET search_path = pg_catalog, public, pg_temp` **nella definizione** |
| le operazioni (`fn_posta_inventario`, `fn_posta_rettifica`) e il controllo (`fn_check_disponibilita_uscita`) | **`SECURITY INVOKER`**: leggono e scrivono il **documento** sotto RLS come l'operatore, e chiamano la primitiva |

⭐ **Perché DEFINER ed è il punto**: senza `INSERT` sul ledger l'app **non può**
scrivere un movimento se non attraverso una funzione che gira con i permessi
del proprietario. È la sola forma in cui *«scrive solo la primitiva»* è un
fatto e non una disciplina. Precedenti: `config.fn_accoda_email_sistema`
(*«DEFINER del PROPRIETARIO, non di un superuser»*), `dbops.fn_conta_presidio`.

⛔ **Ma una DEFINER del proprietario SCAVALCA la RLS** (`ENABLE` senza
`FORCE`, postura del progetto): dentro la primitiva le policy di `movimenti`
non filtrano niente. Il perimetro va **rimesso**, e la forma **non è un
controllo scritto a mano nella primitiva** — sarebbe la seconda sede della
regola di scope. È il **BB che vendite usa già in scrittura**:
`script.trgfn_guard_emittente_scope`, montato come `BEFORE INSERT OR UPDATE OF
magazzino_id` su `movimenti`, `movimenti_attesi` e `valore_giacenza`, con un
**modo nuovo `'magazzino'`** in `script.fn_resolve_emittente_fiscale_id`
(`SELECT m.emittente_fiscale_id FROM magazzino.magazzini m WHERE m.id = p_valore`,
un `ELSIF` accanto a `fiscale`/`soggetto_ruolo`/`fattura`/`ente_incasso`/`contabile`).
Il guard legge le GUC di sessione — che dentro la DEFINER sono **quelle
dell'operatore** — e chiede a `fn_check_user_emittente_scope` la stessa
domanda della policy: emittente attivo, super admin, whitelist. ⭐ Così policy
(lettura), guard (scrittura diretta dell'app) e primitiva (scrittura DEFINER)
**non possono divergere**: è una funzione sola. ⚠️ Il ramo «utente NULL» del
guard passa solo chi `row_security_active()` non filtrerebbe comunque
(revisione del 04-09): per la primitiva chiamata da una sessione senza
identità vale la stessa regola di `vendite.ordini`.

⭐ **E la porta ha un secondo effetto voluto**: dentro la DEFINER,
`vw_giacenza` e `movimenti_attesi` si leggono **completi** — è ciò che il
controllo di disponibilità vuole, e non mescola niente perché un magazzino è di
**un** emittente (c/s §7-sexies, 6).

**Come si dichiara la postura** (AGENTS.md §«Un `REVOKE` in un changeSet
normale NON tiene»): nel loop `90_end/ci_apply/20260205-41-apply-runtime-grants-ci`
una lista nuova `v_tabelle_sola_lettura_app` (`GRANT SELECT` + `REVOKE INSERT,
UPDATE, DELETE`, ramo accanto a `v_registri_append_only`) e `magazzino.movimenti_attesi`
in una lista `v_tabelle_senza_delete` (oggi esiste solo per **schemi**,
`v_schemi_senza_delete`: si aggiunge la forma per tabella), **più** un
changeSet `90_end` forward che applica subito su dev — `ci_apply` su dev non
gira da solo — **più `scripts/sql/provision_db_roles.sql`** (blocco «POSTURA
DICHIARATA»: in CI e in `ci-local.sh` gira **dopo** `ci_apply` e rifà
`GRANT … ON ALL TABLES IN SCHEMA magazzino` all'app; senza la sua eccezione
riapre la porta nello stesso build — P-0, §6-ter C2; fino al 18-09 questa riga
nominava due sedi). Si asserisce con `has_table_privilege('zeroerp_app', …, 'INSERT')`
= false, **mai** con `role_table_grants` (cieco fuori dal ruolo connesso).

⚠️ **Due pgTAP del Lotto 1 diventano rossi per costruzione** (`INSERT INTO
magazzino.movimenti` diretto, come app: `test-movimenti-vincoli-v2` 14 volte,
`test-valore-giacenza-forma-v1` 1; `test-movimenti-attesi-forma-v1` scrive
**solo attesi**, che restano scrivibili: invariato — P-0, §6-ter C11). Non è un difetto del test né della porta: il
**soggetto** di `vincoli-v2` sono i vincoli del ledger, che dal Lotto 2 solo
uno scrittore privilegiato può far scattare — è la **forma 3** del criterio di
`scripts/testpgtap.sh` (*«il test collauda un guard che solo uno scrittore
privilegiato può far scattare»*) ⇒ `-- pgtap-runner: owner` con la ragione;
`valore-giacenza-forma` costruisce la giacenza **attraverso la primitiva**
(diventa un test di comportamento: §7). ⛔ Non si allarga la baseline.

### D-L2-c — Il costo si decide dalla STRUTTURA del movimento → **niente colonna nuova su `causali`; `costo_unitario` sulle righe di inventario e rettifica** — ✅ confermata da Tid il 2026-09-17

M-4 dà a `costo_unitario` tre significati e l'analisi li lascia al `COMMENT`.
Scrivendo la primitiva serve una **regola eseguibile** su *chi* dà il costo, e
la tentazione è una colonna su `causali` (`costo_da ∈ {DOCUMENTO, MEDIA,
GEMELLA, ORIGINALE}`). ⛔ Non serve: ciascun caso è **già leggibile dal
movimento stesso**, nell'ordine in cui si escludono:

| Se il movimento porta… | Il costo è | `p_costo_unitario` |
| --- | --- | --- |
| `storno_di_movimento_id` | quello **dell'originale** (M-8: *al costo originale, non alla media di oggi*) | ⛔ deve essere NULL — `E_MAG_COSTO_NON_AMMESSO` |
| `transfer_uid` **e** segno `+1` (l'entrata gemella) | quello della riga **OUT con lo stesso `transfer_uid`**, che deve esistere già (M-4 terzo caso) | ⛔ NULL — idem; OUT assente ⇒ `E_MAG_GEMELLA_NON_TROVATA` |
| segno `−1` (ogni uscita, compresa la OUT del trasferimento) | la **media corrente** `valore / giacenza` di (articolo, magazzino), letta **dentro il blocco**; `NULL` se la giacenza è ≤ 0 o non c'è riga di valore | ⛔ NULL — idem |
| segno `+1`, nessuno dei casi sopra (entrata da documento o da conteggio) | **`COALESCE(p_costo_unitario, media corrente)`**: il documento lo dà, il conteggio può darlo; se nessuno dei due, `NULL` | facoltativo, `>= 0` |

⭐ Il `COALESCE` è la risposta a una domanda che l'analisi non si era fatta:
**l'inventario iniziale non ha un costo** — `inventari_righe` porta
`qta_contata`/`qta_sistema` e niente altro, quindi il primo carico in assoluto
entrerebbe **senza valore** e la media resterebbe `NULL` fino al primo
acquisto. ⇒ `inventari_righe.costo_unitario numeric` **nullable**, `CHECK >= 0`
— la **valorizzazione iniziale** — e la stessa colonna su
`rettifiche_righe` (una rettifica positiva di merce ritrovata si valorizza alla
media, ma chi la compila può conoscere un costo migliore). Sono le due colonne
di DDL di questo lotto.

⚠️ **Un'entrata senza costo non è un errore: è un fatto dichiarato.** Scrive
`costo_unitario = NULL`, lascia il valore com'è, e la media si **diluisce** —
è la conseguenza onesta di aver caricato merce senza dire quanto vale. Non si
inventa uno zero. Si **vede**: `dbops.vw_magazzino_movimenti_senza_costo (C15)` (natura
`LAVORAZIONE`: è una tendenza da guardare, non un guasto) — così il primo
carico senza valore compare nel digest invece di sparire nella media.

### D-L2-d — La disponibilità si controlla alla GRANA del movimento; i blocchi alla grana dell'articolo; `is_rettifica` esonera dai blocchi, `consente_stock_negativo` da tutto — ✅ confermata da Tid il 2026-09-17

Un'uscita di **5 pezzi del lotto L** non può passare perché l'articolo ne ha 20
in totale se il lotto L ne ha 3. E un **seriale** che esce deve essere **qui**.
⇒ Il controllo fisico si fa alla grana **più fine che il movimento dichiara**:

| Il movimento dichiara | Il fisico si legge su | Deve valere |
| --- | --- | --- |
| `asset_id` | `sum(qta)` di quell'asset **in questo magazzino** | `= 1` in uscita (D-L2-e) |
| `lotto_id` (senza asset) | `sum(qta)` di (articolo, magazzino, **lotto**) | `>= \|qta\|` |
| niente | `vw_giacenza` (articolo, magazzino) | `>= \|qta\|` |

I **blocchi** invece stanno alla grana dell'**articolo**: un blocco manuale
non nomina un lotto (può, ma non deve), e una promessa fatta sull'articolo vale
su qualunque scatola. ⇒ Secondo motivo: `giacenza(articolo, magazzino) +
sum(attesi APERTA altrui) >= |qta|`, dove *altrui* = **sorgente diversa** da
quella del movimento (tipo + chiave; un blocco senza sorgente è sempre altrui).

**Chi è esonerato, e da che cosa** — letto dalla causale, cioè dal catalogo:

| Causale | Fisico | Blocchi | Perché |
| --- | --- | --- | --- |
| `consente_stock_negativo = true` | no | no | è la dichiarazione esplicita di M-2 |
| `is_rettifica = true` (`RETT_NEG`) | **sì** | **no** | ⭐ una rettifica registra un **fatto** sulla merce («ce ne sono 8, non 10»); un blocco è una **promessa** sulla merce. Il fatto vince: se dopo la rettifica la promessa non è più mantenibile, lo dice `vw_disponibilita` (disponibile negativo), non un rifiuto del conteggio — un magazzino che non può registrare ciò che vede è un magazzino che mente. Il fisico resta: una rettifica non porta sotto zero (e con `qta_contata >= 0` non può) |
| tutte le altre uscite | sì | sì | la regola |

⭐ È il **primo consumatore di `causali.is_rettifica`**, che esisteva e non era
armata (Lotto 1 §4.1). ⚠️ E il **perimetro del blocco advisory coincide col
perimetro del controllo** (memoria `reference_advisory_lock_2_arg_namespace`):
la chiave è `(magazzino, articolo)` e tutte e tre le letture — asset, lotto,
articolo, blocchi — stanno **dentro** quella coppia. Un lock per lotto sarebbe
più stretto della lettura dei blocchi e non serializzerebbe niente.

### D-L2-e — Un seriale ha una posizione DERIVATA, e la primitiva la difende — ✅ confermata da Tid il 2026-09-17

§7-quater dice che *«dov'è il pezzo si deriva dal registro»* e `|qta| = 1`.
Ma senza un controllo lo stesso asset può risultare **dentro due magazzini**
(due entrate senza uscita) o **uscire da dove non è**. La posizione derivata è
vera solo se qualcuno la difende alla scrittura:

* **entrata** (`+1`) con `asset_id`: `sum(qta)` dell'asset **su tutti i
  magazzini** deve valere `0` — il pezzo non è dentro da nessuna parte;
* **uscita** (`−1`): `sum(qta)` dell'asset **in questo magazzino** deve valere
  `1` — il pezzo è qui.

Altrimenti `E_MAG_ASSET_POSIZIONE_INCOERENTE` (`CONFLITTO_STATO`: è lo stato
del registro, non un dato del form). ⚠️ La somma su tutti i magazzini è
**dentro un emittente** per costruzione (`assets.emittente_fiscale_id =
magazzini.emittente_fiscale_id`, controllato prima) — non attraversa niente.
⭐ Il lock `(magazzino, articolo)` copre l'uscita; l'entrata di un asset non
ha un lock (regola «solo in uscita»): due entrate simultanee dello **stesso
seriale** in due magazzini si fermerebbero sul secondo per il controllo di
posizione solo se la prima fosse già visibile. È una corsa **benigna**
(READ COMMITTED: la seconda legge dopo il commit della prima) ma va scritta
nel `COMMENT`, perché è il caso che qualcuno cercherà.

### D-L2-f — L'inventario posta la DIFFERENZA, alla grana della riga; la causale la decide il registro — ✅ confermata da Tid il 2026-09-17 (⚠️ l'«angolo» delle ubicazioni qui sotto **sparisce** con D-L2-m: decide il magazzino, e la grana del registro coincide con quella del conteggio per costruzione. Resta il caso «contata in UY, a registro in UX» → D-L2-n)

`fn_posta_inventario(p_inventario_id)`, per ogni riga (in ordine di `id`):

1. `qta_sistema := sum(movimenti.qta)` alla **grana della riga** — `articolo`,
   `magazzino` della testata, e `ubicazione_id`, `lotto_id`, `asset_id` con
   **`IS NOT DISTINCT FROM`** (una riga senza lotto confronta la merce senza
   lotto; una con lotto L confronta il lotto L). Si **scrive sulla riga**: è la
   fotografia contro cui il conteggio è stato posto, e resta;
2. `delta := qta_contata − qta_sistema`; `delta = 0` ⇒ **nessun movimento**
   (il `CHECK qta <> 0` non lo ammetterebbe, e non c'è niente da dire);
3. la causale: `delta > 0` **e** nessun movimento esiste per (articolo,
   magazzino) ⇒ **`INV_INIZIALE`** — è *il primo carico in assoluto* di quella
   merce in quel posto, cioè esattamente ciò che la causale dice (c/s §3);
   `delta > 0` altrimenti ⇒ `RETT_POS`; `delta < 0` ⇒ `RETT_NEG`. ⭐ «Iniziale»
   si **deriva** dallo stato del registro invece di chiederlo a un flag sulla
   testata: un inventario che conta articoli mai movimentati **e** articoli
   già in giacenza scrive causali diverse per righe diverse, ed è preciso —
   per i primi è il primo carico, per i secondi una differenza inventariale.
   ⛔ Non due causali `INV_POS`/`INV_NEG`: direbbero ciò che la **sorgente**
   dice già (`INVENTARIO_RIGA` contro `RETTIFICA_RIGA`), cioè la sedicesima
   riga-specchio che D-L1-d ha rifiutato;
4. chiama la primitiva con `sorgente = INVENTARIO_RIGA:{riga.id}`, `qta =
   delta` (firmata), `costo = riga.costo_unitario` (D-L2-c), lotto/asset/
   ubicazione **della riga**, `data_mov = inventari.data`.

⚠️ **La grana è una regola con un angolo**: se la merce sta a registro **senza
ubicazione** e il conteggio la dichiara **per ubicazione**, i delta non si
compensano (la riga per U1 vede sistema 0 e carica; la merce senza ubicazione
resta a registro). Non è un difetto della funzione: è che il conteggio ha una
grana diversa dal registro. Va scritto nel `COMMENT` e provato in pgTAP
(caso costruito); il rimedio, quando servirà, è una riga di conteggio
*senza* ubicazione che chiuda il residuo — cioè un dato, non codice.

### D-L2-g — Le due operazioni SENZA documento commerciale entrano insieme; il trasferimento no — ✅ confermata da Tid il 2026-09-17, **e la D su `trasferimenti` è presa** (sotto)

`fn_posta_rettifica(p_rettifica_id)` ha la **stessa forma** di
`fn_posta_inventario` con un passo in meno: il delta è **dato**
(`rettifiche_righe.qta_delta`), la causale è `RETT_POS`/`RETT_NEG` dal segno,
la sorgente `RETTIFICA_RIGA:{riga.id}`, il costo `riga.costo_unitario` (D-L2-c).
⭐ È la *«correzione a mano»* che D-6 promette: senza, dal giorno in cui il
registro si scrive non ci sarebbe **nessun** modo di correggere un errore fino
al Lotto 3 (lo storno). Due operazioni con la stessa forma sono anche la
seconda occorrenza che giustifica il telaio comune (§4.5: guard di transizione
e di immutabilità **parametrici**, uno per famiglia).

⛔ **Il trasferimento resta fuori — e il perché va detto giusto** (riscritto il
17-09 su rilievo di Tid: la prima stesura diceva che lo spostamento «non ha
un documento», ed era falso a metà). Verificato su dbdev:

* il trasferimento **con trasporto** fra due depositi ha già il suo documento:
  il **DDT con `config.causali_trasporto.TRASFERIMENTO`** («Trasferimento tra
  depositi», `fatturabile = false`), letto da dieci oggetti di `vendite`
  (`vw_ddt_lista`, `fn_check_ddt_emittibile`, `vw_partite_merce`, …). La
  coppia `TRASF_OUT`/`TRASF_IN` fra magazzini nasce **da lì**: OUT dal
  magazzino di partenza all'emissione, IN in quello di arrivo al ricevimento.
  ⚠️ Ma il DDT oggi **non sa da quale magazzino parte né dove arriva** —
  nessuna colonna `magazzino_id` su `vendite.ddt` né su `ddt_righe`. È la
  stessa cosa che serve allo **scarico da DDT di vendita** (da quale
  magazzino esce la merce): si decide nel **Lotto 3**, con una seconda
  colonna di destinazione per la sola causale `TRASFERIMENTO`;
* `magazzino.trasferimenti` (sorgente `TRASFERIMENTO_RIGA`) le analisi non
  l'hanno mai messo accanto al DDT. Se il trasferimento con trasporto è il
  DDT, questo documento ha senso solo come **spostamento interno senza
  trasporto**: fra ubicazioni dello stesso magazzino (il riordino di
  scaffale, che con D-L2-m diventa quotidiano) o fra due magazzini dello
  stesso sito. Oggi però vieta `magazzino_id_from = magazzino_id_to`
  (`chk_mag_trasferimenti_da_a_distinti`) e le righe **non portano
  un'ubicazione**: per fare quel mestiere deve imparare `ubicazione_id_da`/
  `ubicazione_id_a` sulle righe, e il vincolo deve ammettere lo stesso
  magazzino con ubicazioni diverse.

✅ **DECISO da Tid il 2026-09-17: `magazzino.trasferimenti` è il trasferimento
merci INTERNO** — dentro lo stesso magazzino (fra ubicazioni) **o** fra
magazzini diversi **dello stesso emittente**, senza documento di trasporto. Il
trasferimento con trasporto resta il DDT `TRASFERIMENTO`. Ne discende, **per
il lotto che ne scriverà il posting** (non questo): `trasferimenti_righe`
prende `ubicazione_id_da`/`ubicazione_id_a` (obbligatorie o vietate secondo
`usa_ubicazioni` del rispettivo magazzino, D-L2-m); il CHECK
`chk_mag_trasferimenti_da_a_distinti` diventa «magazzini diversi **oppure**
ubicazioni diverse»; un guard pretende che `from` e `to` siano dello stesso
emittente (M-6: la primitiva non attraversa mai due emittenti, e qui sono due
chiamate nella stessa transazione); il posting è la coppia `TRASF_OUT`/
`TRASF_IN` con lo stesso `transfer_uid`, l'entrata al costo dell'uscita
(D-L2-c). Qui il ramo gemella della primitiva si prova in pgTAP chiamandola due
volte con lo stesso `transfer_uid`; il posting del DDT `TRASFERIMENTO` va col
Lotto 3 insieme allo scarico da DDT.

### D-L2-h — La porta `POSTED` si apre solo dall'operazione: GUC transazionale, matrice nel guard — ✅ confermata da Tid il 2026-09-17, **con una modifica: `COUNTING` esce**

✅ **Tid, 17-09: `COUNTING` non serve.** Verificato prima di toglierlo: sta
**solo** nel `CHECK` dello schema originario (`ck_mag_invetario_stato`) e in
una riga della doc manuale; nessuna analisi lo motiva, nessun pgTAP, backend,
seed o frontend lo nomina; `inventari` è a zero righe su dev e per costruzione
su `zeroerp_ci`. Sul modello non cambia niente di ciò che è permesso — le
righe si scrivono in `DRAFT` come in `COUNTING`, la fotografia del registro si
fissa alla **conferma** (D-L2-n), nessun attributo, nessun permesso diverso:
uno stato che non cambia le regole è un'etichetta, cioè la classe «esiste e
non è armata». Tolto, le tre famiglie (`inventari`, `rettifiche`,
`trasferimenti`) hanno la **stessa** matrice — `DRAFT → CONFIRM → POSTED`,
`DRAFT/CONFIRM → CANCEL`, `POSTED`/`CANCEL` terminali — e il guard di
transizione è davvero una matrice sola. Se un giorno servirà mostrare
«conteggio in corso», è un'informazione a video, non uno stato per il guard.
⇒ In **P-1** (`00_schema`) il `CHECK` si riscrive a quattro valori, e il nome
si corregge nello stesso gesto: `ck_mag_invetario_stato` (refuso + prefisso
`ck_`) → **`chk_mag_inventari_stato`**; nessuno pinna il nome vecchio
(`grep` su `db/pgtap`, `backend`, `80_data` a zero il 17-09).

Un inventario portato a `POSTED` con un `UPDATE` diretto sarebbe un documento
che dice «contato e registrato» **senza nessun movimento dietro**. La
transizione a `POSTED` deve passare **solo** dall'operazione. La forma è quella
già in servizio (memoria
`reference_guard_su_una_porta_censisce_le_madri_che_la_attraversano`, precedente
`fn_change_user_emittenti_scope` su `zeroerp.allow_user_emittente_delete_override`):

* `magazzino.trgfn_documento_interno_guard_transizione()` — **una** funzione
  per le famiglie `inventari`/`rettifiche` (`TG_ARGV`: nome della colonna di
  stato, nome della GUC), `BEFORE UPDATE OF <stato>`: la **matrice** degli
  stati ammessi — **la stessa per le due famiglie** dal 17-09 (`COUNTING`
  esce, vedi in testa): `DRAFT → CONFIRM → POSTED`, `DRAFT/CONFIRM → CANCEL`,
  `POSTED` e `CANCEL` terminali — e **`POSTED`
  ammesso solo se** `current_setting('zeroerp.magazzino_posting_<famiglia>', true)
  = NEW.id::text` — la GUC che l'operazione imposta con `set_config(…, true)`
  (transazionale) e azzera in coda. Altrimenti
  `E_MAG_DOCUMENTO_POSTED_SOLO_DA_OPERAZIONE` (`TECNICO`: nessuna interfaccia
  produce quell'`UPDATE`);
* `magazzino.trgfn_documento_interno_righe_guard_testata()` — sulle **righe**,
  `BEFORE INSERT OR UPDATE OR DELETE`: righe modificabili solo con testata in
  `DRAFT`; in `CONFIRM` scrive
  solo l'operazione (la stessa GUC: è lei a fissare `qta_sistema`); `POSTED`
  e `CANCEL` **immutabili** — `E_MAG_DOCUMENTO_RIGHE_CONGELATE`
  (`CONFLITTO_STATO`).

⚠️ **Matrice nel guard, non tabella**: gli stati sono un `CHECK` a valori
chiusi (`ck_mag_invetario_stato`, `chk_mag_rettifiche_stato`) senza attributi
— la forma che D-L1-b ha scelto per gli attesi (*«CHECK, non tabella: due
valori senza attributi»*). La forma di vendite (`config.stati_doc_*` con la
matrice a dato) esiste perché quegli stati portano attributi (`chiude_lotto`,
soglia dell'impegno, i18n). Qui sarebbe un motore senza consumatori — il
precedente di `pratiche` che c/s §7-septies cita. Se un giorno l'inventario
avrà bisogno di stati configurabili, la matrice esce dal guard e diventa un
seed: cambia **dove** sta, non chi la fa rispettare.

### D-L2-i — `causali.sorgente_tipo_id` 1:1 → **NON ora, e la forma proposta è già smentita** — ✅ rinvio confermato da Tid il 2026-09-17

Il Lotto 1 §9 la dava *«candidata al Lotto 2, quando la primitiva esiste»*. Ma
D-L2-f la smentisce prima di nascere: `RETT_POS` viene **da due sorgenti**
(`INVENTARIO_RIGA` e `RETTIFICA_RIGA`), quindi la regola «questa causale
accetta solo questa sorgente» non è 1:1 — è 1:N, cioè una tabella ponte. E
non ha ancora un caso che la chieda: le due operazioni di questo lotto
scelgono la causale **da sole**, non la ricevono da un operatore che possa
sbagliarla. ⇒ Si rinvia al primo scrittore che riceve la causale da fuori,
con la forma giusta (ponte), non con quella pensata a tavolino.

### D-L2-j — Le viste della disponibilità → **`vw_disponibilita` a due grane, solo le colonne che il lotto sa riempire** — ✅ confermata da Tid il 2026-09-17

Il nome «situazione merce» in vendite è **preso** (`vw_situazione_merce_ordine`
risponde a un'altra domanda: quanto è uscito, tornato, fatturato di un ordine).
Qui la domanda è *«quanto ce n'è, quanto è promesso, quanto se ne può ancora
usare»* ⇒ `magazzino.vw_disponibilita` (articolo × magazzino) e
`vw_disponibilita_articolo` (articolo, sommata sui magazzini **visibili** —
completa per l'emittente attivo, c/s §7-sexies 6). Colonne: `giacenza`,
`bloccata` (somma degli attesi `APERTA`, **firmata**, quindi negativa in
uscita), `disponibile = giacenza + bloccata` — la formula di M-3 in colonne —
e `n_blocchi`. ⛔ **Niente `impegnata`, `potenziale`, `in_arrivo`**: aspettano
il satellite D-17 dell'analisi acquisti, e una colonna a `NULL` che il nome
promette è *«un campo vuoto che il template afferma»* (memoria). Entreranno
con la vista che le sa riempire, e il nome della vista non cambierà.
⚠️ Il drill-down dei blocchi è **gratis**: sono le righe di `movimenti_attesi
APERTA` stesse, con `soggetto_ruolo_id` e `nota`.

### D-L2-k — Il presidio di prontezza ha cadenza **SETTIMANALE** — ✅ confermata da Tid il 2026-09-17

Il brief delle modifiche certe §7 ha fissato la forma (vista a una riga,
`ZERO`, `stato_atteso = MARCATI`) e c/s §8 il momento (*«col passo 2, o suona
per mesi a vuoto»*). Resta la cadenza. `GIORNALIERA` suonerebbe **ogni notte**
dal giorno dell'apply fino a quando qualcuno marca il primo articolo — una
condizione di **prontezza**, non un incidente, e un allarme quotidiano su una
cosa già saputa si spegne (è la lezione del digest). `SETTIMANALE` dice la
stessa cosa una volta a settimana, cioè quanto basta perché non venga
dimenticata.

### D-L2-l — `causali.is_installazione_asset` resta, e la sua scadenza si sposta — ✅ confermata da Tid il 2026-09-17

Il Lotto 1 §4.1 la teneva perché *«il consumatore nasce col Lotto 2 — se allora
non lo trova, esce»*. Il consumatore è l'operazione che posta un **evento
asset** (`ASSET_INSTALL` porta il pezzo fuori da ogni magazzino e cambia
`assets.stato_id`), e quella operazione **non è di questo lotto** (§9).
Toglierla qui sarebbe decidere sul lotto sbagliato; la scadenza si sposta con
il consumatore, ed è scritta lì.

### D-L2-m — Le ubicazioni: DECIDE IL MAGAZZINO (`magazzini.usa_ubicazioni`) — ✅ decisa da Tid il 2026-09-17, emersa dalla rilettura di D-L2-f

**Il difetto che la fa nascere.** Con la sola regola «alla grana della riga»
(D-L2-f), un magazzino con **10 pezzi di A senza ubicazione** a registro e un
inventario che conta **10 pezzi di A in U1** carica altri 10 in U1: a registro
diventano **20**, a scaffale sono 10. Un conteggio giusto raddoppia la
giacenza, e il rimedio scritto in D-L2-f («una riga senza ubicazione = 0»)
regge solo se l'operatore sa di doverla aggiungere. La causa è del **modello**:
nello stesso magazzino può convivere merce *con* e *senza* ubicazione, perché
`movimenti.ubicazione_id` è nullable e niente lega «questo magazzino usa le
ubicazioni» a «qui ogni movimento ne nomina una». Per lotti e seriali il
modello la domanda l'ha già chiusa — **decide l'articolo** (`requires_lotto`,
`requires_serial`: o sempre o mai). Per le ubicazioni mancava chi decide.

**La forma, sullo stesso stampo:** `magazzino.magazzini.usa_ubicazioni boolean
NOT NULL DEFAULT false` (terza colonna di DDL del lotto, P-1).

| `usa_ubicazioni` | ogni movimento (e ogni riga di inventario/rettifica) | se no |
| --- | --- | --- |
| `true` | **deve** nominare un'ubicazione, di quel magazzino e attiva | `E_MAG_UBICAZIONE_OBBLIGATORIA` (`DATO_ERRATO`, `campo = ubicazione_id`) |
| `false` | **non può** nominarne una | `E_MAG_UBICAZIONE_NON_AMMESSA` (idem) |

Lo fa rispettare la primitiva al **passo 8** (§4.2), che già verifica «l'ubicazione
è di questo magazzino»: i due codici sono i gemelli di
`E_MAG_LOTTO_OBBLIGATORIO`/`_NON_AMMESSO` ed entrano in §4.10.

⭐ **Il flag si cambia solo a giacenza zero**: un guard `BEFORE UPDATE OF
usa_ubicazioni` su `magazzini` rifiuta se esiste un movimento del magazzino
(`E_MAG_MAGAZZINO_CON_GIACENZA`, `CONFLITTO_STATO`) — si decide **alla
nascita**, prima del primo movimento. Un magazzino che «mette gli scaffali»
dopo, con merce dentro, ne crea uno nuovo con le ubicazioni e ci trasferisce
la merce: il documento di trasferimento fra magazzini **diversi** esiste già
(`chk_mag_trasferimenti_da_a_distinti` lo pretende), quindi la strada è sul
modello. ⚠️ Oggi il registro è vuoto: il vincolo non costa niente a nessuno.

⇒ La grana del registro e quella del conteggio **coincidono per costruzione**,
e l'angolo di D-L2-f sparisce invece di essere dichiarato. Un'area di
ricezione, in un magazzino a ubicazioni, **è** un'ubicazione (`RICEZIONE`): la
merce «da nessuna parte» non esiste più.

### D-L2-n — Contata in UY, a registro in UX: il PIANO dell'inventario si legge PRIMA di confermare — ✅ confermata da Tid il 2026-09-17

**Il caso di Tid** (17-09): l'articolo A sta in **UX** a registro, l'inventario
lo conta in **UY**. Con D-L2-f la riga (A, UY) trova sistema 0 e carica; UX
resta com'è. Può essere **giusto** (il pezzo è stato spostato senza documento, e
il conteggio lo dice), ma *qualcuno deve saperlo prima di confermare*.

**Proposta:** il numero lo dà il DB, in **una funzione sola** che l'operazione
di posting e la UI leggono entrambe (è §12.5.2 applicato all'inventario: ciò
che l'operatore vede è esattamente ciò che verrà scritto):

```
magazzino.fn_inventario_piano(p_inventario_id)
    RETURNS TABLE (riga_id, articolo_id, ubicazione_id, lotto_id, asset_id,
                   qta_contata, qta_sistema, delta, causale_codice_interno, esito)
```

`SECURITY INVOKER`, `STABLE`, sotto RLS come l'operatore. Una riga per
**ogni posizione** (articolo × ubicazione × lotto × asset) che il registro ha
**o** che il conteggio nomina, per gli articoli contati:

| `esito` | Che cosa è |
| --- | --- |
| `INV_INIZIALE` / `RETT_POS` / `RETT_NEG` | riga contata con differenza: verrà postata così |
| `INVARIATA` | riga contata, differenza zero: nessun movimento |
| **`NON_CONTATA`** | posizione **a registro con giacenza** che nessuna riga dell'inventario copre (`riga_id NULL`, `qta_contata NULL`): **resta com'è** |

`fn_posta_inventario` **legge il piano dalla stessa funzione** e posta le righe
con `delta <> 0`; le `NON_CONTATA` sono informazione, non blocco — l'operatore
può aggiungere una riga (UX = 0, o UX = 10) o lasciare. ⛔ Non un rifiuto:
«potrebbe essere giusta», e un inventario che non può registrare ciò che vede
mente. ⚠️ **E non un'altra sede del calcolo**: `qta_sistema` lo scrive il
posting **dal piano**, non con una seconda query.

🔵 **Per il BE/FE (brief loro):** il drawer dell'inventario, al passaggio a
`CONFIRM`, mostra il piano con le `NON_CONTATA` evidenziate. È lì che
«qualcuno lo sa prima di confermare».

---

## 4. Il disegno, oggetto per oggetto

> Letto dal **catalogo vivo** di dbdev il 2026-09-17 (`pg_proc`, `pg_policy`,
> `pg_constraint`, doc auto-gen), non dagli YAML. I nomi dei codici errore
> sono proposte: entrano a catalogo in P-3 con classe, messaggio, causa e
> soluzione.

### 4.1 La porta (D-L2-b)

| Cosa | Come | Fase |
| --- | --- | --- |
| `script.fn_resolve_emittente_fiscale_id` | `CREATE OR REPLACE` **dalla doc auto-gen** con l'`ELSIF p_modo = 'magazzino'`; ⛔ **si riscrive con la clausola `SET search_path TO 'pg_catalog', 'pg_temp'`** — un `CREATE OR REPLACE` che la dimentica azzera il pin in silenzio (memoria `reference_definer_search_path_stretto_accieca_la_invoker`). Il `COMMENT` elenca i modi. ⚠️ `grep -rl fn_resolve_emittente_fiscale_id db/pgtap/` prima: un test che pinna l'elenco dei modi va allargato nello stesso giro | `20_code/script` |
| guard di scrittura | `trg_movimenti_a10_guard_scope_ins_upd`, `trg_movimenti_attesi_a10_guard_scope_ins_upd`, `trg_valore_giacenza_a10_guard_scope_ins_upd` — `BEFORE INSERT OR UPDATE OF magazzino_id … EXECUTE FUNCTION script.trgfn_guard_emittente_scope('magazzino', 'magazzino_id')`, stampo `vendite.ordini`. ⭐ Alfabeticamente `guard_scope` < `guard_sorgente` < `guard_verso`: lo scope si valuta per primo (memoria «due guard BEFORE ROW: ordine alfabetico») | `20_code/magazzino` |
| loop dei grant | `90_end/ci_apply/20260205-41` **in place** (`runOnChange`): `v_tabelle_sola_lettura_app := ARRAY['magazzino.movimenti','magazzino.valore_giacenza']` → `GRANT SELECT` + `REVOKE INSERT, UPDATE, DELETE`; `v_tabelle_senza_delete := ARRAY['magazzino.movimenti_attesi']` → `GRANT SELECT, INSERT, UPDATE` + `REVOKE DELETE` (oggi la forma «senza DELETE» esiste solo per schemi: si aggiunge quella per tabella, stesso ramo). ⚠️ Il ramo va **prima** di quello generico, come `v_registri_append_only` | `90_end/ci_apply` |
| applicazione immediata | un `90_end` forward con gli stessi `REVOKE` (su dev `ci_apply` non gira da solo: `reference_su_dev_db_ci_apply_non_rilancia_le_automazioni`) | `90_end` |
| **terza sede** (§6-ter C2) | `scripts/sql/provision_db_roles.sql`, blocco «POSTURA DICHIARATA»: le due tabelle in sola lettura (`REVOKE INSERT, UPDATE, DELETE`) e `movimenti_attesi` senza `DELETE`, con lo stesso stampo idempotente (`to_regclass … \gexec`) di `audit_log`/`error_log` — è l'ultima parola in CI | `scripts/sql` |

### 4.2 La primitiva — `magazzino.fn_scrivi_movimento` (M-2, D-L2-a/b/c/d/e)

`SECURITY DEFINER`, `SET search_path TO 'pg_catalog', 'public', 'pg_temp'`
— il pin va scelto guardando **i chiamati**, non solo la funzione (memoria
`reference_definer_search_path_stretto_accieca_la_invoker`): la catena passa
da `script.fn_check_*` e da `fn_log_and_raise_error`, e `public` è nel path
reale dell'applicazione — `VOLATILE`, `%TYPE` ovunque, `RETURNS magazzino.movimenti.id%TYPE`.
**L'ordine dei controlli è il contratto**, ed è scritto nel corpo:

| # | Controllo | Se fallisce | Classe |
| --- | --- | --- | --- |
| 1 | parametri: `p_magazzino_id > 0`, `p_articolo_id` non nullo, `p_causale` non vuoto, `p_qta <> 0`, `p_sorgente_tipo_id > 0`, **esattamente una** chiave, `p_lotto_id`/`p_asset_id`/`p_ubicazione_id`/`p_storno_di_movimento_id` `> 0` se passati, `p_costo_unitario >= 0` se passato | `E_MAG_CHIAMATA_NON_VALIDA` (stampo `E_VENDITE_CHIAMATA_NON_VALIDA`: *«Chiamata non valida a %s: %s.»*, nel VARIADIC il nome della funzione e il valore ricevuto) | `TECNICO` |
| 2 | causale per `codice_interno`, `attivo` | `E_CONFIG_MANCANTE` (riuso: pezzo non configurato) | `TECNICO` |
| 3 | `sign(p_qta) = causali.segno` | `E_MAG_MOVIMENTO_VERSO_INCOERENTE` (riuso, stessa condizione del trigger: la madre dà la frase, il trigger resta la rete) | `TECNICO` |
| 4 | magazzino esiste e `attivo` (letto da DEFINER: esiste o no, non «lo vedo o no») | `E_MAG_CHIAMATA_NON_VALIDA` (id di un magazzino che non c'è: chiamante rotto) | `TECNICO` |
| 5 | articolo `attivo` e **`gestito_a_magazzino`** | `E_MAG_ARTICOLO_NON_GESTITO` — *«L'articolo %s non è gestito a magazzino: nessun movimento si può registrare.»*, `campo = articolo_id`; soluzione: marcare l'articolo | `DATO_ERRATO` |
| 6 | lotto: `requires_lotto` ⇒ `p_lotto_id` obbligatorio; `NOT requires_lotto` ⇒ deve essere NULL; il lotto è **dell'articolo** e `attivo` | `E_MAG_LOTTO_OBBLIGATORIO` · `E_MAG_LOTTO_NON_AMMESSO` · `E_MAG_LOTTO_DI_ALTRO_ARTICOLO`, `campo = lotto_id` | `DATO_ERRATO` |
| 7 | seriale: `requires_serial` ⇒ `p_asset_id` obbligatorio; altrimenti NULL; l'asset è dell'articolo, `attivo`, e **dello stesso emittente del magazzino** | `E_MAG_SERIALE_OBBLIGATORIO` · `E_MAG_SERIALE_NON_AMMESSO` · `E_MAG_ASSET_DI_ALTRO_ARTICOLO` · `E_MAG_ASSET_DI_ALTRO_EMITTENTE`, `campo = asset_id` | `DATO_ERRATO` |
| 8 | ubicazione — **decide il magazzino** (D-L2-m): `magazzini.usa_ubicazioni` ⇒ `p_ubicazione_id` obbligatorio; altrimenti deve essere NULL; se c'è, `ubicazioni.magazzino_id = p_magazzino_id` e `attivo` (il controllo cross-tabella che il Lotto 1 §4.4 rinvia qui) | `E_MAG_UBICAZIONE_OBBLIGATORIA` · `E_MAG_UBICAZIONE_NON_AMMESSA` · `E_MAG_UBICAZIONE_DI_ALTRO_MAGAZZINO`, `campo = ubicazione_id` | `DATO_ERRATO` |
| 9 | storno: `p_storno_di_movimento_id` ⇒ l'originale esiste, stesso articolo e magazzino, `sign(p_qta) = −sign(originale.qta)`, `\|p_qta\| = \|originale.qta\|`, la causale è `STORNO_POS`/`STORNO_NEG`, la sorgente è **quella dell'originale** | `E_MAG_STORNO_INCOERENTE` | `TECNICO` |
| 10 | identità: `SELECT id … WHERE (sorgente_tipo_id, sorgente_riga, sorgente_uid, causale_id, asset_id, lotto_id, ubicazione_id) IS NOT DISTINCT FROM (…)` | `E_MAG_MOVIMENTO_GIA_REGISTRATO` — *«Questa operazione ha già registrato il movimento %s.»*, `dettaglio.movimento_id`; il `UNIQUE` resta la rete | `CONFLITTO_STATO` |
| 11 | **solo se `segno = −1`**: lock `pg_advisory_xact_lock(hashtext('magazzino.fn_scrivi_movimento'), hashtext(p_magazzino_id::text \|\| ':' \|\| p_articolo_id::text))`, **poi** `script.fn_check_disponibilita_uscita(…)` (§4.3) e `script.fn_raise_primo_motivo_se_presente('magazzino', 'fn_scrivi_movimento', v_motivi, NULL, v_tx_id, jsonb_build_object('magazzino_id', …, 'articolo_id', …))` — ⭐ il codice lo **legge** dall'array, quindi l'helper e non la coda a mano (AGENTS.md §«Due funzioni per sollevare») | i codici della check | `CONFLITTO_STATO` |
| 12 | il costo, per struttura (D-L2-c) | `E_MAG_COSTO_NON_AMMESSO` · `E_MAG_GEMELLA_NON_TROVATA` | `TECNICO` |
| 13 | `INSERT INTO magazzino.movimenti … RETURNING id` — i trigger di Lotto 1 (scope, sorgente tipizzata, verso) restano la rete | — | — |
| 14 | `INSERT INTO valore_giacenza (articolo_id, magazzino_id, valore) VALUES (…, p_qta * costo) ON CONFLICT (articolo_id, magazzino_id) DO UPDATE SET valore = valore_giacenza.valore + EXCLUDED.valore` — con `costo NULL` il contributo è **zero** (`COALESCE`), per D-L2-c | — | — |

⚠️ **Il lock sta al passo 11 e non al passo 1**, e il TOCTOU è benigno
(memoria advisory lock): fra i controlli 1-10 e il lock nessuna lettura decide
una scrittura non idempotente — l'identità del passo 10 è ri-protetta dal
`UNIQUE`, i cataloghi non cambiano sotto. ⚠️ **La media corrente (passo 12) si
legge DENTRO il lock**, come la disponibilità: sotto READ COMMITTED la `SELECT`
dopo il lock prende uno snapshot nuovo.

⚠️ `E_MAG_ARTICOLO_NON_GESTITO` è `DATO_ERRATO` **per la primitiva** — chi
rimedia marca l'articolo. Ma le operazioni che leggeranno **righe di documento
di vendita** (Lotto 3) devono **saltare** gli articoli non gestiti (un servizio
in bolla non è un difetto), non farli rifiutare: la primitiva resta stretta,
il filtro è dell'operazione. Le due di questo lotto **non** filtrano: contare o
rettificare un articolo non gestito **è** un dato sbagliato.

`COMMENT ON FUNCTION`: i quattordici passi in una riga ciascuno, la regola del
lock (perimetro = controllo), i tre significati del costo, «DEFINER del
PROPRIETARIO, non di un superuser», la corsa benigna dei seriali (D-L2-e).

### 4.3 Il controllo di disponibilità — `script.fn_check_disponibilita_uscita` (M-3, D-L2-d)

```
script.fn_check_disponibilita_uscita(
    p_magazzino_id     bigint, p_articolo_id uuid,
    p_qta_uscita       numeric,                 -- POSITIVA: il «quanto» che vorrebbe uscire
    p_sorgente_tipo_id bigint DEFAULT NULL,     -- la sorgente di chi chiede: i SUOI blocchi si escludono
    p_sorgente_riga    bigint DEFAULT NULL, p_sorgente_uid uuid DEFAULT NULL,
    p_lotto_id         bigint DEFAULT NULL, p_asset_id bigint DEFAULT NULL,
    p_ignora_blocchi   boolean DEFAULT false    -- is_rettifica: lo passa la primitiva, letto dalla causale
) RETURNS jsonb   -- [] se ammessa; altrimenti array ORDINATO di {codice, reason, reason_key, dettaglio, valori}
```

`STABLE`, **`SECURITY INVOKER`**, in `script` come tutte le `fn_check_*`
(linee-guida-sql §12.5.1). **Pura**: non solleva (tranne la guard di parametro:
`E_MAG_CHIAMATA_NON_VALIDA`), non scrive. I motivi, **nell'ordine che è il
contratto**:

| # | `codice` | `reason` | `reason_key` | Condizione | `valori` |
| --- | --- | --- | --- | --- | --- |
| 1 | `E_MAG_GIACENZA_INSUFFICIENTE` | `GIACENZA_INSUFFICIENTE` | `magazzino.disponibilita.blocco.giacenza_insufficiente` | il fisico alla grana dichiarata (asset ⇒ posizione; lotto ⇒ `sum` del lotto; altrimenti `vw_giacenza`) `< p_qta_uscita` | articolo (codice), magazzino (codice), disponibile, richiesta |
| 2 | `E_MAG_MERCE_BLOCCATA` | `MERCE_BLOCCATA_PER_ALTRI` | `magazzino.disponibilita.blocco.merce_bloccata` | `NOT p_ignora_blocchi` e `giacenza(articolo) + sum(attesi APERTA altrui) < p_qta_uscita` | articolo, magazzino, disponibile, bloccata, richiesta |

⭐ **Chiamata da due posti e vera in entrambi**: dalla primitiva (DEFINER ⇒
legge tutto il magazzino, che è di un emittente) e dalla UI come operatore
(INVOKER sotto RLS ⇒ legge tutto il magazzino **se lo vede**, altrimenti
zero: e un magazzino che non vede è un magazzino su cui non scriverà). Il
numero non può divergere perché la funzione è una — è la proprietà di
§12.5.2. ⚠️ **Il `reason` non porta `E_`** (§12.5.1). 🔵 **Le due `reason_key`
sono un debito verso il FE**: `scripts/check_i18n_keys.py` (controllo 4) le
cerca nella doc auto-gen delle funzioni e **fallisce** se mancano da
`it.json`/`en.json` — vanno chieste **nello stesso giro** (§4.10).

⚠️ Alla **conferma dell'ordine** (Lotto 3+) il primo motivo è
**informazione**, non blocco (c/s §5-bis, «i due momenti»): lo decide il
**chiamante**, che legge l'array e non solleva. La funzione non lo sa e non
deve saperlo.

### 4.4 Il valore (M-4, D-L2-c)

| Cosa | Come |
| --- | --- |
| aggiornamento | nella primitiva, passo 14 (§4.2) |
| `magazzino.fn_ricalcola_valore_giacenza(p_magazzino_id, p_articolo_id DEFAULT NULL)` | `SECURITY DEFINER` del proprietario (scrive dove l'app non scrive), `p_magazzino_id` **obbligatorio** — *«un ricalcolo che serve N emittenti li itera, non li somma»* (c/s §7-sexies): il magazzino è di un emittente, quindi la grana è già quella giusta. `UPSERT` di `valore = sum(qta * coalesce(costo_unitario, 0))` dal registro; con `p_articolo_id` uno solo. **Ri-somma**, non ri-esecuzione: i `costo_unitario` scritti sono fatti |
| `dbops.vw_magazzino_valore_giacenza_divergente (C15)` | `security_invoker`: `(articolo, magazzino, valore_copia, valore_registro)` dove i due **differiscono** (`IS DISTINCT FROM`; una giacenza con movimenti e senza riga di valore è una divergenza) — deve restare **vuota**. Natura `ZERO`, perimetro `DEFINER` (legge tabelle sotto RLS: da un percorso senza contesto darebbe zero per cecità), cadenza `SETTIMANALE` |
| `dbops.vw_magazzino_movimenti_senza_costo (C15)` | `security_invoker`: le **entrate** con `costo_unitario IS NULL` (uscite a `NULL` sono la conseguenza, non la causa). Natura `LAVORAZIONE`, `SETTIMANALE`, `DEFINER` |

⭐ Il ricalcolo coincide con la copia **per costruzione**: l'accumulatore somma
gli stessi `qta × costo` che la primitiva ha scritto. La vista di divergenza
non prova l'aritmetica — prova che **nessuno ha scritto fuori dalla porta**.
È la sua vera funzione, e va nel suo `COMMENT`.

### 4.5 Le due operazioni — `fn_posta_inventario`, `fn_posta_rettifica` (D-L2-f/g/h)

Entrambe `SECURITY INVOKER`, `VOLATILE`, `RETURNS TABLE (movimento_id, riga_id, qta)`
(che cosa ha scritto, riga per riga: è ciò che il BE mostrerà e che il pgTAP
asserisce). Forma comune:

1. guard di parametro (`E_MAG_CHIAMATA_NON_VALIDA`);
2. `SELECT … FROM <testata> WHERE id = $1 FOR UPDATE` — sotto RLS: fuori
   perimetro non c'è ⇒ `E_MAG_DOCUMENTO_NON_TROVATO` (`NON_TROVATO`, 404
   identico a un id inesistente: convenzione no-leak); lo stato deve essere
   `CONFIRM` ⇒ altrimenti `E_MAG_DOCUMENTO_TRANSIZIONE_NON_AMMESSA`
   (`CONFLITTO_STATO`, `valori`: stato attuale, stato richiesto);
3. righe: almeno una ⇒ `E_MAG_DOCUMENTO_SENZA_RIGHE` (`NON_ESEGUIBILE`);
4. `set_config('zeroerp.magazzino_posting_<famiglia>', v_id::text, true)`;
5. per riga, in ordine di `id`: il delta (D-L2-f) o `qta_delta`, la causale,
   la primitiva; l'inventario **legge il piano da `fn_inventario_piano`**
   (D-L2-n: una sede sola per UI e posting), scrive `qta_sistema` sulla riga
   **prima** e posta le righe con `delta <> 0`; le posizioni `NON_CONTATA`
   restano com'erano;
6. `UPDATE <testata> SET <stato> = 'POSTED'` — passa il guard perché la GUC
   dice «sono io»;
7. `set_config(…, '', true)`.

⭐ **Sono una transazione sola per costruzione**: una `SELECT fn_posta_*()`.
Se la riga 7 di 10 fallisce (giacenza insufficiente), le prime sei si
annullano e il documento resta `CONFIRM` — è l'all-or-nothing di
linee-guida-sql §5b, e il pgTAP lo prova col caso costruito.

⚠️ **`FOR UPDATE` sulla testata e non un advisory lock**: la riga esiste ed è
il perimetro giusto (due posting dello stesso documento si serializzano sulla
riga; il secondo trova `POSTED` e rifiuta). Il lock advisory della primitiva
copre invece la corsa fra **documenti diversi** sulla stessa merce.

**Il piano dell'inventario** (D-L2-n): `magazzino.fn_inventario_piano(p_inventario_id)`
`RETURNS TABLE (riga_id, articolo_id, ubicazione_id, lotto_id, asset_id,
qta_contata, qta_sistema, delta, causale_codice_interno, esito)`, `SECURITY
INVOKER`, `STABLE`, sotto RLS. Una riga per ogni posizione (articolo ×
ubicazione × lotto × asset) che il registro **ha** o che il conteggio
**nomina**, per gli articoli contati: `INV_INIZIALE`/`RETT_POS`/`RETT_NEG`
(contata con differenza), `INVARIATA` (contata, delta zero), **`NON_CONTATA`**
(a registro con giacenza, nessuna riga la copre: `riga_id` e `qta_contata`
NULL). ⛔ Non solleva sulle `NON_CONTATA`: sono informazione. ⚠️ Testata
fuori perimetro ⇒ zero righe (è INVOKER): il 404 lo dà il BE sulla testata,
come per ogni satellite. Il guard di parametro (`E_MAG_CHIAMATA_NON_VALIDA`)
resta.

**I guard di famiglia** (D-L2-h): `trgfn_documento_interno_guard_transizione`
su `inventari` (`BEFORE UPDATE OF stato_mag_inventario`) e `rettifiche`
(`… OF stato_mag_rettifiche`), `trgfn_documento_interno_righe_guard_testata`
su `inventari_righe` e `rettifiche_righe` (`BEFORE INSERT OR UPDATE OR
DELETE`; legge la testata col `FK` passato in `TG_ARGV`). ⚠️ Prima di
montarli: `grep` della doc auto-gen delle funzioni e del backend per chi
scrive quelle tabelle (memoria «guard su una porta = censire le madri»): al
17-09 **nessuna funzione** scrive `inventari*`/`rettifiche*` e
`backend/apps/magazzino` è uno scheletro — il censimento è in P-0 e si
ripete al momento di scrivere.

### 4.6 Le viste della disponibilità (M-3, D-L2-j)

| Vista | Colonne | Note |
| --- | --- | --- |
| `magazzino.vw_disponibilita` | `articolo_id, magazzino_id, giacenza, bloccata, disponibile, n_blocchi` | `vw_giacenza` `LEFT JOIN` gli attesi `APERTA` aggregati; `bloccata` è la **somma firmata** (negativa), `disponibile = giacenza + bloccata` — **in colonne**, mai «meno» (c/s §7-bis, correzione del 04-09). ⚠️ Un articolo con blocchi e **senza** movimenti deve comparire (giacenza 0, disponibile negativo): `FULL JOIN`, o `UNION` delle chiavi — si prova in pgTAP |
| `magazzino.vw_disponibilita_articolo` | `articolo_id, giacenza, bloccata, disponibile, n_magazzini` | somma sui magazzini **visibili**: dentro l'emittente attivo è *tutto*; `COMMENT` come `vw_costo_medio_globale` |

Tutte `security_invoker = true` **ri-specificata** a ogni `CREATE OR REPLACE`.
⛔ Nessuna colonna «impegnata/potenziale/in arrivo» (D-L2-j).

### 4.7 La vista degli orfani (D-9)

`dbops.fn_sorgenti_orfane()` `RETURNS TABLE (tabella regclass, riga_id bigint,
sorgente_tipo_id bigint, sorgente_codice_interno varchar, sorgente_riga bigint,
sorgente_uid uuid, target_table regclass)` — `SECURITY DEFINER` del
proprietario (attraversa la RLS: un orfano in una tabella protetta va visto
comunque), `SET search_path TO 'pg_catalog', 'public', 'pg_temp'`, `STABLE`.
**Il perimetro si deriva dal vincolo, non da un elenco**: le tabelle con una
**FK verso `config.sorgenti`** su una colonna `sorgente_tipo_id` **e** le due
colonne `sorgente_riga`/`sorgente_uid` (il *modello A tipizzato*: è la forma
che il guard di Lotto 1 presidia). Per ciascuna, per ogni `sorgente_tipo_id`
presente, un anti-join dinamico (`format('%s', target_table)`, `%I` sulle
colonne) verso `target_table` sulla chiave che `key_selector` dichiara.
`dbops.vw_sorgenti_orfane AS SELECT * FROM dbops.fn_sorgenti_orfane()` — deve
restare **vuota**; natura `ZERO`, cadenza `SETTIMANALE`, perimetro `DEFINER`.

⭐ È lo stesso stampo di `vw_bersagli_non_dichiarati` e dei registri dei
codici errore (aggancio §8-bis), e si scrive **una volta** perché
`target_table` è un `regclass` e `key_selector` sta a catalogo. ⚠️ Il guard
tipizzato impedisce di **inserire** un orfano; questa vista trova quelli
creati **dopo**, cancellando il bersaglio — la FK non c'è, e non può esserci.
⚠️ **Il perimetro va reso visibile**: un secondo `RETURNS TABLE`,
`dbops.fn_sorgenti_orfane_perimetro()` (le tabelle esaminate), e il pgTAP
asserisce che le sei di `magazzino` ci sono — è il *«gemello "esiste" della
biforcazione»* (memoria `reference_presidio_ramo_scelto_da_presenza_colonna`):
un presidio che esamina zero tabelle è verde e muto.

🔴 **rev 18-09 (pomeriggio, `20260918-27`) — il ciclo interno legge TRE SCALARI
TIPIZZATI, non un `record`.** Dopo l'apply, il presidio dei riferimenti morti
(`dbops/test-riferimenti-morti-v1`, test 2) è diventato rosso su questa
funzione: `error:55000:29:RETURN QUERY: il record "v_s" non è stato ancora
assegnato` + `error:XX000:29: cached plan is not valid plan`, classificati
`REALE` (nessuna `FP_*` copre la forma: `FP_SQL_DINAMICO` prende solo il 42601
dentro un `EXECUTE`). La causa è la **forma**, e lo dice `plpgsql_check` stesso
alla riga 18: *«cannot determinate a result of dynamic SQL — Don't use dynamic
SQL and record type together»*. Un `record` riempito da `FOR … IN EXECUTE` ha
tupla indeterminata al momento del controllo, quindi ogni `v_s.campo` letto
dopo è «non ancora assegnato». ⇒ I tre campi sono colonne di `config.sorgenti`
e si dichiarano con `%TYPE` (`v_tipo_id`, `v_key_selector`, `v_target_table`);
il ciclo diventa `FOR v_tipo_id, v_key_selector, v_target_table IN EXECUTE …`,
che PL/pgSQL ammette. `v_t record` resta: viene da un `SELECT` statico. ⛔ Non
una riga nel registro delle esenzioni: quello è un **debito datato**, e qui c'è
una funzione nata oggi con una forma che il presidio non sa leggere — si cambia
la forma. Comportamento e firma invariati (6/6 nel suo pgTAP col corpo estratto
iniettato in transazione; 9/9 nel presidio dei riferimenti morti).

### 4.8 Il presidio di prontezza (brief modifiche certe §7, D-L2-k)

`dbops.vw_articoli_a_magazzino_prontezza`: **una riga**, `stato = CASE WHEN
EXISTS (SELECT 1 FROM catalogo.articoli WHERE gestito_a_magazzino AND attivo)
THEN 'MARCATI' ELSE 'NESSUNO_MARCATO' END`. `catalogo.articoli` non ha RLS ⇒
perimetro `LIBERO`. Riga in `presidi.csv`: natura `ZERO`, `colonna_stato =
stato`, `stato_atteso = MARCATI`, cadenza `SETTIMANALE`, `nota` con il perché
(*«al rilascio nessun articolo movimenta giacenza e nessun rosso lo dice»*).
⭐ `fn_conta_presidio` conta le righe `IS DISTINCT FROM 'MARCATI'`: lo zero
suona, il pieno tace — **non una natura nuova per un caso solo**.

### 4.9 `requires_lotto` in vista, BE e drawer (M-5, Lotto 1 §4.3) — 🔵 richiesta a BE/FE

| Lato | Che cosa |
| --- | --- |
| **DB** | `catalogo.vw_articoli_dettaglio`: `CREATE OR REPLACE` dalla doc auto-gen con `a.requires_lotto` **in coda** alla lista (PostgreSQL ammette solo colonne aggiunte alla fine in un `CREATE OR REPLACE VIEW`). ⛔ **Senza `security_invoker`**: la vista non ce l'ha e non deve averlo (`catalogo.articoli` non è in RLS — Lotto 1 §4.3, correzione del 15-09) |
| **BE** (`apps/catalogo`) | `requires_lotto` in `ARTICOLI_CREATE_COLUMNS`/`_UPDATE_COLUMNS` (`"bool"`), in `ARTICOLI_DETAIL_COLUMNS` (`a.requires_lotto` — la proiezione è **per nome**: una colonna nuova della vista non esce finché nessuno la nomina), nella whitelist del service, nell'`inline_serializer` di `@extend_schema`. ⛔ **NON in `dbops.lock_columns_conditional`** e non fra i `non_editable_fields`: è fuori dal lock BoM per decisione |
| **FE** (`ArticoloDrawer.vue`) | `ToggleSwitch` accanto a `requires_serial`, **senza `:disabled="isFieldLocked(…)"`** — chi copia `requires_serial` a occhi chiusi eredita il lucchetto; chiavi `catalogo.field_requires_lotto` (it/en) + hint (*«L'articolo si movimenta per partite: ogni movimento nomina un lotto»*). La colonna di lista (`ui.lista_colonna`, lista 26) **non è richiesta** da questo lotto: se la si vuole, è una riga di seed `attivo = f` fino al BE (memoria `reference_seed_lista_colonna_campo_sorgente_attivo_false`) |

### 4.10 I codici errore (AGENTS.md §«Sollevare un errore») — 🔵 richiesta al BE

Nuovi a catalogo (`codici_errore.csv` + `messaggi_errore.csv` `it`): **27**,
id **1075–1101** (P-3; i 25 qui sotto più i due nati in §6-ter, in coda alla
tabella). ✅ A catalogo su dbdev dal 18-09 12:23 (apply di Tid):

| Codice | Classe | Chi rimedia · `campo` |
| --- | --- | --- |
| `E_MAG_CHIAMATA_NON_VALIDA` | `TECNICO` | chiamante rotto; gemello di `E_VENDITE_CHIAMATA_NON_VALIDA` |
| `E_MAG_ARTICOLO_NON_GESTITO` | `DATO_ERRATO` | chi marca l'articolo · `articolo_id` |
| `E_MAG_LOTTO_OBBLIGATORIO` · `E_MAG_LOTTO_NON_AMMESSO` · `E_MAG_LOTTO_DI_ALTRO_ARTICOLO` | `DATO_ERRATO` | chi compila la riga · `lotto_id` |
| `E_MAG_SERIALE_OBBLIGATORIO` · `E_MAG_SERIALE_NON_AMMESSO` · `E_MAG_ASSET_DI_ALTRO_ARTICOLO` · `E_MAG_ASSET_DI_ALTRO_EMITTENTE` | `DATO_ERRATO` | idem · `asset_id` |
| `E_MAG_UBICAZIONE_OBBLIGATORIA` · `E_MAG_UBICAZIONE_NON_AMMESSA` · `E_MAG_UBICAZIONE_DI_ALTRO_MAGAZZINO` | `DATO_ERRATO` | idem · `ubicazione_id` (D-L2-m: gemelli dei lotti) |
| `E_MAG_MAGAZZINO_CON_GIACENZA` | `CONFLITTO_STATO` | `usa_ubicazioni` si cambia solo senza movimenti (D-L2-m): crearne uno nuovo e trasferire |
| `E_MAG_ASSET_POSIZIONE_INCOERENTE` | `CONFLITTO_STATO` | stato del registro: il pezzo è altrove / è già dentro |
| `E_MAG_GIACENZA_INSUFFICIENTE` · `E_MAG_MERCE_BLOCCATA` | `CONFLITTO_STATO` | stato del magazzino; i due della check |
| `E_MAG_MOVIMENTO_GIA_REGISTRATO` | `CONFLITTO_STATO` | doppio click / rilancio: la frase nomina il movimento esistente |
| `E_MAG_STORNO_INCOERENTE` · `E_MAG_COSTO_NON_AMMESSO` · `E_MAG_GEMELLA_NON_TROVATA` | `TECNICO` | chiamante rotto |
| `E_MAG_DOCUMENTO_NON_TROVATO` | `NON_TROVATO` | 404 no-leak (fuori scope = inesistente) |
| `E_MAG_DOCUMENTO_TRANSIZIONE_NON_AMMESSA` · `E_MAG_DOCUMENTO_RIGHE_CONGELATE` | `CONFLITTO_STATO` | rileggere lo stato |
| `E_MAG_DOCUMENTO_SENZA_RIGHE` | `NON_ESEGUIBILE` | aggiungere righe |
| `E_MAG_DOCUMENTO_POSTED_SOLO_DA_OPERAZIONE` | `TECNICO` | nessuna interfaccia produce quell'`UPDATE` |
| `E_MAG_MAGAZZINO_NON_VALIDO` (C4) | `TECNICO` | magazzino inesistente o non attivo al passo 4: codice suo, `E_MAG_CHIAMATA_NON_VALIDA` resta guard di parametro sola (B-7) |
| `E_MAG_DOCUMENTO_NON_ELIMINABILE` (C3) | `CONFLITTO_STATO` | si cancella solo una bozza: la frase porta lo stato |

Riusati: `E_CONFIG_MANCANTE`, `E_MAG_MOVIMENTO_VERSO_INCOERENTE`,
`E_SCOPE_EMITTENTE`/`E_SCOPE_SENZA_UTENTE` (li solleva il guard BB).
⛔ Nel `VARIADIC` **valori**, mai nomi di parametro: codici degli articoli e
dei magazzini, quantità, stati — la frase la legge una persona (eccezione: i
`TECNICO`, dove il lettore è chi sviluppa e il parametro **è** l'informazione).

🔵 **Al BE, nello stesso giro**: `./manage-env.sh genera_error_policies` (il
modulo generato) **e** una riga di ripiego senza segnaposto per ciascuno in
`error_messages_fallback.py` — `test_il_file_generato_e_allineato_al_catalogo`
e `test_ogni_codice_vivo_ha_un_messaggio_di_ripiego` sono rossi finché non
arrivano (è successo al Lotto 1 con due codici: §12 di quel brief, p.7).
🔵 **Al FE**: **tredici** `reason_key` in `it.json`/`en.json`, prima che la
doc auto-gen delle due check entri nel repo — le due di §4.3
(`magazzino.disponibilita.blocco.giacenza_insufficiente`, `….merce_bloccata`)
e le undici di `fn_check_riga_magazzino` (P-4-bis):
`magazzino.riga.blocco.articolo_non_gestito`, `.lotto_obbligatorio`,
`.lotto_non_ammesso`, `.lotto_di_altro_articolo`, `.seriale_obbligatorio`,
`.seriale_non_ammesso`, `.seriale_di_altro_articolo`,
`.seriale_di_altro_emittente`, `.ubicazione_obbligatoria`,
`.ubicazione_non_ammessa`, `.ubicazione_di_altro_magazzino`. Il testo è quello
del messaggio a catalogo, senza i valori.

---

## 5. Le trappole note, e dove morde ciascuna

> Le sei righe in coda alla §5 del Lotto 1 sono qui in testa, **riscritte per
> questo lotto**. Poi le nuove. Tutte già pagate almeno una volta.

| Trappola | Dove morde qui | Forma giusta |
| --- | --- | --- |
| **`MARK_RAN` autolesionista** — un oggetto nato sotto preCondition esiste solo su dev | nessun `DROP`/`RENAME` in questo lotto, ma **i `GRANT`**: il `REVOKE` forward di §4.1 non deve precondizionare su niente | `exectype` si legge su **`zeroerp_ci`**, mai su dev |
| **Montare/smontare una funzione = censire il registro che la dichiarava** | `fn_resolve_emittente_fiscale_id` cambia corpo; il guard di scope si monta su tre tabelle nuove | `grep` di ogni nome toccato nei CSV di `80_data/sql/dbops` (`riferimenti_morti_esenzioni`, `presidi`, `processi_bersagli`) e in `db/pgtap/` **prima** di scrivere |
| **Una fixture che CERCA un dato di macchina muore sul DB da zero** | ogni pgTAP di §7 | azienda e operatore da `dbops.fn_pgtap_crea_emittente_operatore()`, indirizzo da `fn_pgtap_crea_indirizzo_dettaglio(etichetta)`, **articolo costruito** (`INSERT` con `gestito_a_magazzino`, `requires_lotto`, `requires_serial` **scelti dal test**: pescare il primo `attivo` dal catalogo darebbe un articolo non gestito, cioè un `E_MAG_ARTICOLO_NON_GESTITO` che sembra un test rosso) |
| **Un indice del passato sopravvive sul DB da zero** | nessuna rinomina qui | — (resta scritto perché è la riga che il prossimo lotto con una rinomina dimenticherà) |
| **Cambiare una riga di CATALOGO = censire i pgTAP che la pinnano** | `presidi.csv` (+4 righe: `test-presidi-catalogo`, `test-presidi-debito-dichiarato` contano?), `codici_errore.csv` (+22), il loop dei grant | `grep -rl <nome> db/pgtap/` per ogni riga di seed toccata; un presidio che conta «quante righe» è una fotografia e si riscrive per nome |
| **Sette cose verdi in sessione per ragioni sbagliate** (bilancio del 15-09) | tutto | l'SQL estratto (`updateSQL`, offline) in `BEGIN … ROLLBACK` **su `zeroerp_ci`**, non solo su dev; i pgTAP col runner **come app**; `ci-local.sh --fresh --ci-apply` prima di dire «fatto» |
| **La porta rende rossi due pgTAP del Lotto 1** (D-L2-b, P-0 §6-ter C11) | `test-movimenti-vincoli-v2`, `test-valore-giacenza-forma-v1`; invariati `test-movimenti-attesi-forma-v1` (solo attesi) e `test-rls-magazzino-perimetro-v1` (già owner) | `vincoli-v2` → `pgtap-runner: owner` con motivo (forma 3 del criterio); `valore-giacenza-forma` → costruisce la giacenza **via primitiva**; ⛔ **nessuna riga in baseline** |
| **Un `REVOKE` in un changeSet normale non tiene** | i tre `REVOKE` di §4.1 | postura nel **loop** (`20260205-41`, in place) **e** forward `90_end`; asserzione con `has_table_privilege`, non `role_table_grants` |
| **`SECURITY DEFINER` = proprietario della FUNZIONE, che è chi migra** | primitiva, ricalcolo, orfani | pgTAP: `proowner` della funzione = `relowner` delle tabelle in RLS che legge (stampo `test-catalogo-presidi-v1` test 11); `COMMENT` «DEFINER del PROPRIETARIO, non di un superuser» |
| **Il `search_path` di una DEFINER vale per tutto ciò che chiama** | primitiva → `script.fn_check_*`, `fn_raise_primo_motivo_se_presente` (che ha il suo pin), `fn_log_and_raise_error` | pin **nella definizione** con `public` dentro (`pg_catalog, public, pg_temp`); riscrivendo `fn_resolve_emittente_fiscale_id` il **suo** pin (`pg_catalog, pg_temp`) si ricopia |
| **Il `WITH CHECK` scatta prima di `NOT NULL`/`CHECK`** | i pgTAP che provano un vincolo scrivendo come app sotto RLS | `col_not_null`/`has_check` sulla forma; il comportamento si prova **attraverso la primitiva** |
| **`SELECT INTO` a zero righe azzera senza errore** | la media corrente, la gemella, l'originale dello storno, il lotto/asset | `IF NOT FOUND` dopo ogni `SELECT INTO` che decide |
| **`PERFORM fn_log_and_raise_error` a cinque argomenti non risolve** | ogni sollevamento | il VARIADIC si passa **sempre**, anche vuoto; i codici dalla check passano da `fn_raise_primo_motivo_se_presente` |
| **`%TYPE` in firma è una fotografia** | la firma della primitiva | si accetta (è la convenzione), sapendo che un cambio di tipo sulla colonna vuole un `CREATE OR REPLACE` |
| **Un `BEFORE ROW` in `INSERT` oscura il `CHECK`** | il guard di scope e quello del verso stanno **prima** dei CHECK | i pgTAP asseriscono il codice del guard **e** l'esistenza del CHECK in `pg_constraint` (già nella forma di `vincoli-v2`) |
| **Il nome di un trigger a 63 caratteri viene hashato** | `trg_movimenti_attesi_a10_guard_scope_ins_upd` (44) — sotto; `trg_inventari_righe_a10_guard_testata_ins_upd_dlt` (49) — sotto | contare prima di salvare; `pg_trigger` dopo |
| **Un `CREATE OR REPLACE VIEW` può solo AGGIUNGERE colonne in coda** | `vw_articoli_dettaglio` + `requires_lotto` | in coda; il BE proietta per nome, quindi la posizione non gli importa |
| **Il numero libero scade nel minuto** | i file `20260917-NN` e seguenti | oggi l'ultimo è `-14`; si ricontrolla prima di salvare |
| **La `reason_key` è un debito verso il FE e il cancello è in CI** | §4.3 | le due chiavi nei locales **prima** che la doc auto-gen della check entri (P-9/P-10) |
| **Guard restrittivo: `grep` dei pgTAP e delle madri prima** | i due guard di famiglia (§4.5), i tre di scope | `grep -rl "inventari\|rettifiche" db/pgtap/` e la doc auto-gen delle funzioni per `UPDATE magazzino.inventari` |
| **Una vista `security_invoker` perde la marcatura a ogni `CREATE OR REPLACE`** | `vw_disponibilita*`, `dbops.vw_magazzino_valore_giacenza_divergente`, `vw_movimenti_senza_costo` — e le cinque del Lotto 1 se toccate | `WITH (security_invoker = true)` sempre; pgTAP su `reloptions` (già nel Lotto 1) |
| **Il presidio con `colonna_stato` conta «diverso dall'atteso», non «uguale a un allarme»** | `vw_articoli_a_magazzino_prontezza` | una riga sola, due valori: `MARCATI` tace, tutto il resto suona |
| **Un `record` riempito da SQL DINAMICO è `REALE` per il presidio dei riferimenti morti** (pagata il 18-09, dopo l'apply: `fn_sorgenti_orfane` → `55000 record "v_s" non ancora assegnato` + `XX000`, test 2 rosso) | ogni `FOR … IN EXECUTE` — qui il ciclo interno degli orfani | scalari con `%TYPE` come bersaglio del `FOR` (`FOR a, b, c IN EXECUTE …`); il `record` va bene solo su un `SELECT` statico. ⛔ Non nel registro delle esenzioni: non è un debito, è una forma. Rimedio: `20260918-27` |
| **Un conteggio ESATTO sul TESTO di `pg_proc` conta anche i commenti** (pagata il 18-09: `test-rubinetto-primo-motivo` test 5 a 20 invece di 19, perché `fn_check_disponibilita_uscita` NOMINA l'helper nel commento di testa) | ogni presidio che legge `prosrc` con una regex; qui il conteggio dei chiamanti di `fn_raise_primo_motivo_se_presente` | togliere i `--` e pretendere il nome seguito da `(` (la forma di `vw_punti_primo_motivo`); e ogni cantiere con funzioni plpgsql **nuove** rilancia i due presidi trasversali di §7 prima di dire «fatto» |

---

## 6. I passi

> Fase: `00_schema` → `20_code` → `80_data` → `90_end`; in CI tutta una fase
> prima della successiva, qualunque sia la data. ⛔ Negli YAML si cita il
> **nome** di questo brief (`brief-db-magazzino-lotto-2-motore`), mai il path
> `work-in-progress/`. ⛔ `runOnChange: false` in `00_schema` e `20_code`;
> `validCheckSums` al plurale. L'apply lo fa Tid; i pgTAP li lancia Tid col
> runner; qui si prova con l'SQL estratto in transazione annullata, **anche su
> `zeroerp_ci`**.

| # | Passo | Fase |
| --- | --- | --- |
| **P-0** | ✅ **Fatto il 2026-09-18** — **Censimenti**, prima di scrivere una riga: (a) chi scrive oggi `magazzino.movimenti`/`valore_giacenza`/`inventari*`/`rettifiche*` — `pg_proc` (doc auto-gen delle funzioni), `backend/apps`, `db/pgtap` (zero funzioni, BE scheletro, **due** pgTAP diretti sul ledger + uno sugli attesi); (b) i lettori di `fn_resolve_emittente_fiscale_id` e di `trgfn_guard_emittente_scope` in `db/pgtap` (nessuno pinna i modi); (c) le righe di `presidi.csv`, `codici_errore.csv`, `messaggi_errore.csv` (max id) e i pgTAP che ne contano le righe; (d) `pg_trigger` sulle otto tabelle toccate — nomi, lunghezze, ordine alfabetico dei `_a10_`; (e) `has_table_privilege('zeroerp_app', …)` **prima**, su dev e su `zeroerp_ci`, come fotografia datata. ⭐ Il risultato è il riquadro **§6-bis**; ciò che smentisce il brief è in **§6-ter** (dodici criticità, **C1 e C2 bloccano P-2**). ⛔ **Regole di scrittura per tutti i passi** (Tid, 18-09): `%TYPE` **in firma, in `DECLARE` e in `RETURNS TABLE`** — non solo nei parametri; numerazione dal primo libero **al momento del salvataggio** (`20260918-05` alle 10 del 18-09: `-01…-04` sono di `pagamenti`, non ancora committati) | — |
| **P-1** | ✅ **Scritto il 2026-09-18** — `20260918-06` (`costo_unitario` su `inventari_righe` e `rettifiche_righe`, `numeric(18,6)` nullable, `CHECK >= 0`, `COMMENT`: D-L2-c), `-07` (`magazzini.usa_ubicazioni boolean NOT NULL DEFAULT false`, `COMMENT`: D-L2-m), `-08` (il `CHECK` degli stati di `inventari` a quattro valori, `ck_mag_invetario_stato` → `chk_mag_inventari_stato`, preCondition «nessuna riga fuori dai quattro» a `expectedResult 0`), `-09` (`trgfn_magazzini_guard_usa_ubicazioni` + `trg_magazzini_a10_guard_usa_ubicazioni_upd`, `BEFORE UPDATE OF usa_ubicazioni`, `E_MAG_MAGAZZINO_CON_GIACENZA` con `campo`; conta i movimenti, non il saldo né gli attesi), `-10` (`catalogo.vw_articoli_dettaglio` + `requires_lotto` in coda, dalla doc auto-gen, senza `security_invoker`). **Provato**: cinque guardrail CI verdi; `liquibase validate` + `updateSQL` (i cinque resi nell'ordine `-06…-10`); SQL **estratto** in `BEGIN…ROLLBACK` su dev **e** `zeroerp_ci`; prova di comportamento in ROLLBACK (flag cambiato su un magazzino vuoto, stesso valore riscritto = ok, rifiutato con la frase su uno con movimento, costo negativo → `23514`, `COUNTING` → `23514` col nome nuovo, colonna 56 della vista = `requires_lotto`, nessuna reloption). ✅ Applicato da Tid il 18-09 alle 12:23 (con tutto il lotto) | `00_schema` + `20_code` |
| **P-2** | ✅ **Scritto il 2026-09-18** — **la porta**, in **sei** sedi: `20260918-12` `fn_resolve_emittente_fiscale_id` + modo `magazzino` (dalla doc auto-gen, pin `pg_catalog, pg_temp` ricopiato, frase dei **sette** modi); `-13` **C1**: `trgfn_guard_emittente_scope` — nel ramo «utente NULL», se `NOT row_security_active` **ma `current_user <> session_user`** (dentro una DEFINER) si risolve comunque l'emittente e, con un padrone, `E_SCOPE_SENZA_UTENTE`; senza padrone passa (le email di sistema); `-14` i tre trigger **con lo stampo** (`trg_<t>_a10_guard_emittente_scope_ins_upd`, `BEFORE INSERT OR UPDATE`, `('magazzino','magazzino_id')`; C5); `-15` il forward `90_end` (`GRANT SELECT` + `REVOKE INSERT, UPDATE, DELETE` su `movimenti`/`valore_giacenza`, `REVOKE DELETE` su `movimenti_attesi`); il loop `20260205-41` **in place** (liste `v_tabelle_sola_lettura_app`, `v_tabelle_senza_delete`, rami prima del generico); **`provision_db_roles.sql`** blocco «POSTURA DICHIARATA» (C2). **Provato** (SQL estratto dei quattro + il corpo del loop, in transazione annullata, su dev **e** `zeroerp_ci`): postura giusta **dopo** il loop (`movimenti`/`valore_giacenza` t/f/f/f, attesi t/t/t/f, `inventari` e `audit_log` invariati); i tre trigger montati e `guard_emittente_scope` primo fra i BEFORE ROW; il modo risolve l'emittente del magazzino e un id inesistente dà NULL; il guard nuovo: owner senza GUC passa, operatore di **un'altra** azienda → `E_SCOPE_EMITTENTE` sul ledger. ⚠️ Il ramo DEFINER di C1 si prova **come app** solo con la primitiva (P-9, `test-porta-ledger-v1`); la regressione «email di sistema senza sessione passa» va in `test-guard-emittente-senza-utente` | `20_code` + `90_end` + `scripts/sql` |
| **P-3** | ✅ **Scritto il 2026-09-18** — **27** righe in `codici_errore.csv` + `messaggi_errore.csv` (`it`, id **1075–1101**, causa e soluzione, `NULL` token): i 25 di §4.10 più `E_MAG_MAGAZZINO_NON_VALIDO` (TECNICO, §6-ter C4: il passo 4 non riusa `E_MAG_CHIAMATA_NON_VALIDA`, che resta guard di parametro sola) e `E_MAG_DOCUMENTO_NON_ELIMINABILE` (CONFLITTO_STATO, id 1101, C3 deciso). ⭐ **Il contratto dei `valori` è nel messaggio** (il numero e l'ordine dei `%s`): P-4/P-5/P-6 lo rispettano — `GIACENZA_INSUFFICIENTE` (articolo, magazzino, disponibili, richiesti), `MERCE_BLOCCATA` (articolo, magazzino, disponibili, bloccati, richiesti), `ASSET_POSIZIONE_INCOERENTE` (seriale, «dove risulta»), `STORNO_INCOERENTE` (id originale, condizione), `COSTO_NON_AMMESSO` (caso), i `*_OBBLIGATORIO` (codice articolo/magazzino), i `*_NON_AMMESSO` (codice articolo/magazzino, codice lotto/seriale/ubicazione), i `*_DI_ALTRO_*` (codice lotto/seriale/ubicazione, codice articolo/magazzino), `DOCUMENTO_TRANSIZIONE` (stato attuale, richiesto), `RIGHE_CONGELATE` (stato), `DOCUMENTO_*` (id). Loader `20260614-08` invariato (mirror `runOnChange`). **Provato**: upsert **completo** dei due CSV in una transazione sua (nessuna riga irriscrivibile), 27 nuovi in `vw_codici_errore_identita`, `format()` con i `%s` di ciascuno; ✅ **a catalogo su dbdev** (27 messaggi 1075–1101 dopo l'apply di Tid). **B-7 verde** sul catalogo vivo (`scripts/codici-errore-baseline.sh`: 149 presidiati, «nessun codice ha allargato»): nessun codice nuovo nasce con due famiglie — `E_MAG_CHIAMATA_NON_VALIDA` PARAMETRO (18 punti), `E_CONFIG_MANCANTE` resta NOT_FOUND (47 → 52 punti), i tre `*_OBBLIGATORI*` PARAMETRO, `STORNO_INCOERENTE`/`GEMELLA`/`MAGAZZINO_NON_VALIDO`/`DOCUMENTO_NON_TROVATO` NOT_FOUND, i due `DOCUMENTO_*` di stato VALORE_ATTESO, gli altri sedici `IGNOTO` (la misura non legge la loro guardia). 🔵 BE: `genera_error_policies` + 27 ripieghi (§4.10) | `80_data` |
| **P-4** | ✅ **Scritto il 2026-09-18** — `20260918-11` `script.fn_check_disponibilita_uscita` (§4.3): firma con `%TYPE` sulle colonne di `movimenti`, `STABLE SECURITY INVOKER`, pura; motivo 1 alla grana dichiarata (asset → posizione, lotto → somma del lotto, altrimenti `vw_giacenza`), motivo 2 = `giacenza + sum(attesi APERTA altrui)`; ⭐ **precisazione**: un blocco è un atteso in **uscita** (`qta < 0`) — un atteso in **entrata** («in arrivo») non entra nella somma, o farebbe uscire merce promessa da un arrivo non avvenuto (è la colonna che D-L2-j rinvia); `vw_disponibilita` (P-7) usa lo stesso filtro. `trim_scale()` sui numeri dei `valori` («11», non «11.000000»). Guard `E_MAG_CHIAMATA_NON_VALIDA` solo PARAMETRO. **Provato** in transazione annullata (owner con contesto operatore, seed P-3 dei soli nuovi): ammessa a 11 su giacenza 20 e blocchi altrui −9; `MERCE_BLOCCATA` a 12 con `valori` (art, mag, 11, 9, 12); la **propria** sorgente non è altrui; a 25 **entrambi** i motivi nell'ordine; grana lotto (20/3, esce 5 → fisico 3); `p_ignora_blocchi` passa a 12 e non a 25; qta 0 → `E_MAG_CHIAMATA_NON_VALIDA`; magazzino invisibile → zero con l'id nella frase. ⚠️ Come **app** sotto RLS la prova sta al runner (P-9): `titodb` non può `SET ROLE zeroerp_app` | `20_code/script` |
| **P-4-bis** | ✅ **Scritto il 2026-09-18** (C8) — `20260918-16` `script.fn_check_riga_magazzino(magazzino, articolo, lotto, asset, ubicazione)`: pura, `STABLE INVOKER`, i passi 5-8 in una sede — articolo gestito (e si ferma lì), lotto e seriale decisi dall'articolo, seriale dello stesso emittente del magazzino, ubicazione decisa dal magazzino (D-L2-m); ogni motivo porta `campo` nel `dettaglio`; **undici** `reason_key` `magazzino.riga.blocco.*` (🔵 FE, §4.10). Letta dalla primitiva (primo motivo) e dal piano (P-6, esito `NON_POSTABILE`) | `20_code/script` |
| **P-5** | ✅ **Scritto il 2026-09-18** — `20260918-17` **C6**: `vw_costo_medio`, `vw_giacenza_valorizzata`, `vw_costo_medio_globale` a «`NULL` se `qta <= 0`», `security_invoker` ri-specificata; `-18` **la primitiva** `magazzino.fn_scrivi_movimento` (§4.2: DEFINER del proprietario, pin `pg_catalog, public, pg_temp`, i quattordici passi — con `E_MAG_MAGAZZINO_NON_VALIDO` al passo 4 (C4), i passi 5-8 via `fn_check_riga_magazzino`, il passo 9-bis della posizione del seriale, lo storno che pretende anche la **posizione** dell'originale e non già stornato, la media da `vw_costo_medio` dentro il lock, `round(…, 6)` sul costo e sul contributo (C7)); `-19` `fn_ricalcola_valore_giacenza(p_magazzino_id, p_articolo_id DEFAULT NULL)` (DEFINER, `RETURNS TABLE` con `%TYPE`: prima/dopo per coppia; cancella le copie senza registro; `ON CONFLICT ON CONSTRAINT`, non l'elenco di colonne — ambiguo con le colonne di `RETURNS TABLE`), `dbops.vw_magazzino_valore_giacenza_divergente` (`FULL JOIN`, `IS DISTINCT FROM`), `dbops.vw_magazzino_movimenti_senza_costo` (entrate a costo NULL) — in `dbops`, C15. **Provato** in transazione annullata su dev (undici scenari): 5×10 € + 5×20 € → valore 150, media 15; uscita 4 → costo 15, valore 90; entrata senza costo **con** media → eredita 15 (`COALESCE`), 120; OUT 3 / IN 3 con lo stesso `transfer_uid` → la IN a 15, i valori si spostano (45/75); storno della OUT → costo dell'originale, secondo storno → `E_MAG_STORNO_INCOERENTE` «già stornato»; stessa identità → `GIA_REGISTRATO` con l'id; uscita 9 su 8 → `GIACENZA_INSUFFICIENTE` (8, 9); blocco altrui 4 → `SCARICO_VEN` 5 rifiutata, `RETT_NEG` 5 passa; verso, causale ignota, magazzino inesistente, articolo non gestito, costo su uscita → i cinque codici; divergenza 0 → 1 dopo una scrittura fuori porta → ricalcolo (46 → 45) → 0; seriale: entrata, seconda entrata altrove → «già presente nel magazzino MAGP5», uscita da dove non è → «assente dal magazzino MAGP5B». Compila anche su `zeroerp_ci` | `20_code/magazzino` |
| **P-6** | ✅ **Scritto il 2026-09-18** — `20260918-20` **C14**: `uq_mag_inventari_righe_posizione` UNIQUE NULLS NOT DISTINCT (inventario, articolo, ubicazione, lotto, asset); `-21` i due guard di famiglia + quattro trigger: `trgfn_documento_interno_guard_transizione` (`BEFORE UPDATE OF <stato> OR DELETE`; matrice unica: `DRAFT → CONFIRM|CANCEL`, `CONFIRM → POSTED|CANCEL|DRAFT` — **C13**: il ritorno in bozza è la conseguenza di D-L2-n, senza il piano non si corregge; `POSTED` solo con la GUC `zeroerp.magazzino_posting_<famiglia>` = id; `DELETE` solo in `DRAFT`, C3) e `trgfn_documento_interno_righe_guard_testata` (`BEFORE INSERT OR UPDATE OR DELETE`; `DRAFT` sì, `CONFIRM` solo con la GUC, `POSTED`/`CANCEL` congelate; testata assente = cascata già ammessa → passa; un solo punto di sollevamento per codice, B-7); `-22` `fn_inventario_piano` (`RETURNS TABLE` con `%TYPE`, esiti `INV_INIZIALE`/`RETT_POS`/`RETT_NEG`/`INVARIATA`/`NON_CONTATA`/**`NON_POSTABILE`** + `posting_blocco_reason`/`_reason_key` dal primo motivo di `fn_check_riga_magazzino`); `-23` `fn_posta_inventario` (dal piano: `qta_sistema` scritto prima, delta ≠ 0 postato, costo della riga solo in entrata, `data_mov` = data del documento) e `fn_posta_rettifica`, entrambe `INVOKER`, `FOR UPDATE` sulla testata, GUC aperta e richiusa, `RETURNS TABLE (movimento_id, riga_id, qta)`. **Provato** in transazione annullata (owner con contesto): primo conteggio 10 in UX → `INV_INIZIALE` a 7 €, `qta_sistema = 0`; secondo conteggio 12 in UY → piano `RETT_POS` + **`NON_CONTATA` per UX** (il caso di Tid); riapri, UX = 10 → `INVARIATA`, riga di articolo non gestito → `NON_POSTABILE ARTICOLO_NON_GESTITO` e il posting rifiuta **tutto** (stato `CONFIRM`, 1 movimento come prima); corretto e postato → giacenza 22, `qta_sistema` 10/0 sulle righe; posting su `POSTED` → transizione; `UPDATE` diretto a `POSTED` → `SOLO_DA_OPERAZIONE`; righe su `POSTED` e su `CONFIRM` (app) → congelate; `DELETE` di `POSTED` → non eliminabile, di `DRAFT` → passa; `POSTED → DRAFT` → transizione; `CONFIRM` senza righe → `SENZA_RIGHE`; riga senza ubicazione in magazzino a ubicazioni → `NON_POSTABILE UBICAZIONE_OBBLIGATORIA`; rettifica −5 → alla media 7, giacenza 17; −30 → fisico, testata resta `CONFIRM`; due righe stessa posizione → `23505`. Compila su `zeroerp_ci` | `00_schema` + `20_code/magazzino` |
| **P-7** | ✅ **Scritto il 2026-09-18** — `20260918-24` `vw_disponibilita` (`FULL JOIN` fra `vw_giacenza` e i blocchi: `bloccata` = somma firmata degli attesi `APERTA` **in uscita**, `disponibile = giacenza + bloccata`, `n_blocchi`) e `vw_disponibilita_articolo` (somma sui magazzini visibili, `n_magazzini`), `security_invoker`. **Provato**: giacenza 10, blocco −4 → −4 / 6 / 1; un `CHIUSA` −50 e un atteso in **entrata** +100 non contano; articolo con blocco e senza movimenti compare (0 / −3); per articolo somma e conta i magazzini | `20_code/magazzino` |
| **P-8** | ✅ **Scritto il 2026-09-18** — `20260918-25` `dbops.fn_sorgenti_orfane_perimetro()` (perimetro derivato da `pg_constraint` **+ `pg_trigger`**: FK verso `config.sorgenti`, le due colonne di chiave **e il guard tipizzato montato** — senza quest'ultimo le tabelle di `vendite` con la stessa forma ma un'altra semantica davano **112 falsi orfani** su dev; oggi le sei di magazzino), `fn_sorgenti_orfane()` (DEFINER del proprietario, anti-join dinamico per tabella e tipo sulla chiave di `key_selector`, confronto su `::text` perché nel perimetro convivono `uuid` e `text`), `vw_sorgenti_orfane`, `vw_articoli_a_magazzino_prontezza` (una riga, `n_marcati`); **quattro** righe in `presidi.csv` (le due spie di P-5 sono **`dbops.vw_magazzino_valore_giacenza_divergente`** e **`dbops.vw_magazzino_movimenti_senza_costo`**, non in `magazzino`: C15). **Provato**: perimetro 6/6 di magazzino, zero orfani; cancellato il bersaglio di un movimento come owner (trigger disabilitati) → **1** orfano (`movimenti#602 → INVENTARIO_RIGA:140`), `fn_conta_presidio` = 1; prontezza `MARCATI`/0 e `NESSUNO_MARCATO`/1; divergenza e senza costo a 0 via `fn_conta_presidio`; i test 2 e 3 del catalogo dei presidi verdi (ogni vista di `dbops` a catalogo, ogni riga con la sua vista). 🔴 **rev (pomeriggio)** — `20260918-27` `fn_sorgenti_orfane` col ciclo interno su **tre scalari `%TYPE`** invece del `record`: dopo l'apply il presidio dei riferimenti morti la riferiva `REALE` (§4.7, §5). **Provato**: SQL estratto dallo YAML in `BEGIN…ROLLBACK` (COMMENT compreso), `plpgsql_check` a zero `error:`, `test-sorgenti-orfane-v1` 6/6 e `test-riferimenti-morti-v1` 9/9 col corpo iniettato; cinque guardrail statici verdi. ✅ **Applicato da Tid il 18-09 pomeriggio, presidio verde** | `20_code/dbops` + `80_data` |
| **P-9** | ✅ **Scritto il 2026-09-18** — `20260918-26` due helper di fixture (`dbops.fn_pgtap_crea_articolo(codice, gestito, requires_lotto, requires_serial)`, `fn_pgtap_crea_magazzino(codice, usa_ubicazioni)`: regola del 2, dodici file avrebbero avuto la stessa copia); **dodici pgTAP** — `magazzino/test-fn-scrivi-movimento-controlli-v1` (25), `-disponibilita-v1` (9), `-seriali-v1` (5), `-valore-v1` (10), `test-valore-giacenza-divergenza-owner-v1` (5, owner: forma 3), `test-fn-posta-inventario-v1` (17), `test-fn-posta-rettifica-v1` (6), `test-documenti-interni-guard-v1` (15), `test-porta-ledger-v1` (16), `test-vw-disponibilita-v1` (7), `dbops/test-sorgenti-orfane-v1` (6, owner), `dbops/test-articoli-a-magazzino-prontezza-v1` (6); **ri-collocati**: `test-movimenti-vincoli-v2` → `pgtap-runner: owner` (forma 3, asserzioni invariate), `test-valore-giacenza-forma-v1` → la giacenza e la copia via primitiva (magazzino a ubicazioni, articolo costruito; test 10 e 12 riscritti: l'app non scrive più la copia); `script/test-guard-emittente-senza-utente` + 7-8 (email di sistema senza identità **passa**, la rev C1 è in servizio). **Provati** in un harness (SQL estratto dei 21 changeSet + seed dei soli nuovi + il pgTAP, in transazione annullata, **come owner**): tutti verdi tranne i **nove** che vogliono l'app — `porta-ledger` 4-7 e 13-14 (42501 e senza identità), `guard-senza-utente` 2, 4, 5 — che il runner esercita dopo l'apply. `guardrail_pgtap_preambolo` verde, debito `throws_ok` invariato (129). ✅ **Runner come app (Tid, 18-09 pomeriggio): due regressioni sui presidi TRASVERSALI**, non sui dodici del lotto — `dbops/test-riferimenti-morti-v1` test 2 (→ `20260918-27`, P-8 rev) e `script/test-rubinetto-primo-motivo-v1` test 5 (uguaglianza esatta 17 → **19**: `fn_scrivi_movimento` e `fn_posta_inventario` sono siti nuovi nati sull'helper; **e il predicato passa dal testo alla CHIAMATA** — commenti tolti, nome + `(` — perché `fn_check_disponibilita_uscita` lo nomina solo nel commento e il conteggio vecchio dava 20). Provato in transazione ritirata: 7/7. ✅ **Rilanciati da Tid dopo l'apply del `-27`: verdi** (18-09 pomeriggio) | `db/pgtap` |
| **P-10** | ✅ **Scritto il 2026-09-18** — **venti** pagine `manual/` nuove (magazzino ×10, script ×2, dbops ×8: §8), **diciassette** aggiornate (dieci tabelle e viste di magazzino, le tre `vw_costo_medio*` con la regola `qta > 0`, `fn_resolve_emittente_fiscale_id` con la tabella dei **sette** modi, `trgfn_guard_emittente_scope` con la rev C1 «dentro una DEFINER», `vw_articoli_dettaglio` e `articoli` con `requires_lotto`), `_dominio-magazzino.md` riscritto sullo stato «primitiva e prime due operazioni in esercizio, porta chiusa» (disegno con la PORTA, la famiglia dei documenti col ciclo, ciò che manca), la riga `magazzino` della mappa concentrica. La guida dei presidi **non** elenca le viste per nome (verificato: rimanda a `dbops.presidi`): niente da toccare. Le richieste BE/FE sono §4.9 e §4.10 (27 codici, 13 `reason_key`). ⛔ `index.md`/`index.ci.md` e la doc auto-gen non toccati a mano | `docs/` |

⚠️ **P-2 si prova con la porta chiusa**: dopo il `REVOKE`, in una sessione
come `zeroerp_app`, un `INSERT INTO magazzino.movimenti` deve dare `42501` — e
lo stesso `INSERT` attraverso la primitiva deve passare. È il collaudo che dice
che la porta è una porta.

### 6-bis — Riquadro P-0: i censimenti — ✅ eseguiti il 2026-09-18 (mattina)

> Letti da `pg_proc`/`pg_trigger`/`pg_constraint`/`pg_policy` su **dbdev** e,
> per proprietario e privilegi, anche su **`zeroerp_ci`**; i seed dai **CSV**
> (la sede), non dalle tabelle. Sono **struttura**, non popolazione — tranne
> dove è scritto «fatto datato». Ciò che smentisce il brief è in **§6-ter**.

| # | Censimento | Esito |
| --- | --- | --- |
| (a) | chi scrive `movimenti`/`valore_giacenza`/`inventari*`/`rettifiche*` | `pg_proc`: **zero** funzioni; `backend/apps`: zero; `db/pgtap`: **quattro** file scrivono direttamente — `test-movimenti-vincoli-v2` (14 `INSERT` sul ledger), `test-valore-giacenza-forma-v1` (1 ledger + 2 `valore_giacenza`), `test-movimenti-attesi-forma-v1` (8 sugli **attesi**, che restano scrivibili: **non diventa rosso**), `rls/test-rls-magazzino-perimetro-v1` (già `pgtap-runner: owner`: invariato). ⇒ i rossi per costruzione sono **due**, non tre (§5 corretta) |
| (b) | i lettori dei due BB | 23 pgTAP nominano `fn_resolve_emittente_fiscale_id`/`trgfn_guard_emittente_scope`; **nessuno pinna la frase dei modi** (`sono ammessi` → zero in `db/pgtap`); zero righe nei CSV di `80_data/sql/dbops`. Forma viva del resolver: `STABLE SECURITY DEFINER`, pin `pg_catalog, pg_temp`, **sei modi** — `fiscale`, `soggetto_ruolo`, `fattura`, `ente_incasso`, `contabile`, **`listino`** (dal 05-09; §4.1 ne elencava cinque) — e nel ramo `ELSE` una frase che **elenca i modi**: si riscrive con `magazzino` |
| (c) | presidi e codici | `presidi.csv`: 37 righe; vocabolari dal `CHECK`: natura ∈ {`ZERO`,`REGISTRO`,`LAVORAZIONE`,`CANCELLO`,`INVENTARIO`}, cadenza ∈ {`GIORNALIERA`,`SETTIMANALE`,`MAI`}, perimetro ∈ {`LIBERO`,`DEFINER`}, `chk_presidi_coppia_stato` (colonna e atteso insieme o nessuno); `fn_conta_presidio` con `colonna_stato` conta `IS DISTINCT FROM $1` ✓; `test-catalogo-presidi-v1` conta **`> 0`**, non una fotografia. `messaggi_errore.csv` max id **1074** ✓; `codici_errore.csv` = `(codice, classe, obsoleto_dal, note)`, senza id. `E_MAG_*` già a catalogo: **due** (`MOVIMENTO_VERSO_INCOERENTE` TECNICO, `TRASFERIMENTO_EMITTENTI_DIVERSI` DATO_ERRATO). Riusati: `E_CONFIG_MANCANTE` TECNICO (baseline B-7: **`NOT_FOUND`** sola), `E_SCOPE_EMITTENTE` NON_PERMESSO, `E_SCOPE_SENZA_UTENTE` TECNICO, `E_VENDITE_CHIAMATA_NON_VALIDA` TECNICO (B-7: `NOT_FOUND,PARAMETRO,VALORE_ATTESO`). ⚠️ Regola B-7 letta nello script: *«un codice NUOVO nasce con 2+ famiglie note → ROSSO»* (§6-ter C4) |
| (d) | `pg_trigger` e vincoli sulle otto tabelle | 74 trigger vivi. **Stampo del guard di scope** (24 tabelle): `trg_<t>_a10_guard_emittente_scope_ins_upd`, `BEFORE INSERT OR UPDATE`, argomenti `('fiscale','emittente_fiscale_id')` — `guard_scope_<qualifica>` solo dove ce ne sono **due** sulla stessa tabella (`sistemazioni`, `vendite_contabili_righe`). `magazzini` **ha già** il suo (`fiscale`). I tre nuovi: 47/54/53 caratteri. `valore_giacenza` non ha `tx_id` né storico (solo audit). CHECK vivi: `ck_mag_invetario_stato` a **cinque** valori, `chk_mag_rettifiche_stato` a quattro, `uq_mag_movimenti_identita` **`NULLS NOT DISTINCT`** sulle sette colonne del passo 10 ✓, `chk_mag_inventari_righe_asset_qta_unitaria` (`qta_contata ∈ {0,1}`), `qta_contata >= 0` ✓, `chk_mag_trasferimenti_da_a_distinti` ✓. Con lo **stesso refuso** del CHECK: l'indice `uq_mag_invetario_sorgente_fk`. FK righe → testata: **`ON DELETE CASCADE`** su entrambe le famiglie (§6-ter C3). Nessun `delete_block` generato su `magazzino`. `COUNTING`: nominato **solo** da `manual/inventari.md` |
| (e) | privilegi e postura (fatto datato 18-09) | `zeroerp_app`: `SELECT, INSERT, UPDATE, DELETE` su **tutte** le otto, su dev **e** su `zeroerp_ci`. Proprietario: `titodb` (dev) / `zeroerp` (CI). RLS `ENABLE` **senza `FORCE`** su tutte tranne `causali` e `lotti` (nessuna RLS); policy `FOR ALL` con `ruolo_applicativo = 'OPERATORE'` + `fn_scope_ef_whitelist_via_magazzino`. Il loop `20260205-41`: liste `v_registri_append_only`, `v_fn_riservate`, `v_schemi_senza_delete`, ramo prima del generico ✓ — **ma non è l'ultima parola** (§6-ter C2) |
| (+) | altro letto per strada | `vw_articoli_dettaglio`: **55** colonne (non 54), `requires_lotto` assente, **nessun** oggetto dipende dalla vista (il `CREATE OR REPLACE` è libero); `articoli.requires_lotto` `boolean NOT NULL` ✓. `consente_stock_negativo = false` su **tutte** le sedici causali (fatto datato): il pgTAP **costruisce** il caso. `fn_raise_primo_motivo_se_presente(p_area, p_funzione, p_motivi, p_campo, p_tx_id, p_context_extra)` ✓ come in §4.2. `fn_pgtap_crea_emittente_operatore()` → `(emittente_fiscale_id, emittente_codice, soggetto_ruolo_id, auth_user_id, identita_id)`. La shadow di storico salva uno **`snapshot` jsonb**: le tre colonne di P-1 non chiedono DDL sulla shadow. **Prova sotto il pin** (owner, `BEGIN…ROLLBACK`, 18-09): un `INSERT` sul ledger con `search_path = pg_catalog, public, pg_temp` attraversa tx_id, audit, storico, guard sorgente (dinamico) e `require_attivo` **senza cecità** — la catena regge il pin di §4.2. Numero libero al momento della scrittura: **`20260918-05`** (`-01…-04` sono di `pagamenti`, non committati; si ricontrolla) |

### 6-ter — ⚠️ Criticità emerse in P-0 — da decidere PRIMA di P-2

> Ognuna smentisce una riga del brief con un fatto di **struttura** (o con
> una prova in `ROLLBACK`), e propone un rimedio. Le prime due bloccano il
> lotto così com'è scritto; le altre lo correggono mentre si scrive.

**C1 🔴 D-L2-b — il guard BB è FAIL-OPEN dentro una DEFINER del proprietario.** ✅ **Deciso da Tid il 2026-09-18: rimedio nel BB (A′)**, P-2.
Il brief dice: *«il ramo «utente NULL» del guard passa solo chi
`row_security_active()` non filtrerebbe comunque … per la primitiva chiamata da
una sessione senza identità vale la stessa regola di `vendite.ordini`»*. **È
falso**, e non per un dettaglio: `row_security_active(TG_RELID)` risponde per
il **`current_user`**, che dentro una `SECURITY DEFINER` è il **proprietario**
— RLS `ENABLE` senza `FORCE` ⇒ **false** ⇒ `RETURN NEW`. ⭐ **Provato il 18-09
su dbdev con un precedente già in servizio**, stessa sessione `zeroerp_app`
**senza GUC**, in `ROLLBACK`: `INSERT` diretto su `config.email_log` →
`E_SCOPE_SENZA_UTENTE`; la stessa riga via `config.fn_accoda_email_sistema`
(DEFINER di `titodb`, tabella col guard `fiscale`) → **passa**. Per la
primitiva vuol dire: un management command, un job senza `processi_identita`,
qualunque sessione senza identità **scrive sul ledger** — cioè la porta si apre
proprio per chi la §5 dell'analisi voleva fermare; e `fn_ricalcola_valore_giacenza`
uguale. ⚠️ `fn_accoda_email_sistema` **conta** su questo passaggio (reset
password da endpoint non autenticato: *«nessuna sessione, nessuna GUC»*,
`email_repository.py:495`) — ma scrive `emittente_fiscale_id = NULL`, quindi il
ramo che la fa passare **non è quello dell'utente**: è il *«nessun padrone»*.
**Rimedio proposto — nel BB, una sede sola (A′)**: nel ramo «utente NULL»,
quando `NOT row_security_active(...)` **ma `current_user <> session_user`**
(si sta dentro una DEFINER), si risolve comunque l'emittente e, **se non è
NULL**, si solleva `E_SCOPE_SENZA_UTENTE`: una DEFINER che scrive una riga
*con* un padrone per conto di una sessione che non dice chi è non ha titolo;
una riga *senza* padrone (le email di sistema) passa come oggi. Censiti: le
DEFINER che scrivono su tabelle col guard sono **due** (`fn_accoda_email_sistema`,
`fn_chiudi_email_sistema`), entrambe a emittente NULL ⇒ nessun consumatore
cambia. pgTAP: caso nuovo in `script/test-guard-emittente-senza-utente.sql`
(«via DEFINER senza identità e con emittente → rifiuta; con emittente NULL →
passa») e il caso in `test-porta-ledger-v1` (§7). *Ripiego (B′)*: la primitiva
pretende la GUC salvo `session_user` esente (owner/superuser/BYPASSRLS) —
funziona, ma è la **seconda scrittura** della regola di esenzione che il guard
rifiuta di elencare. ⛔ Finché non è deciso, **P-2 non si scrive**: senza C1 la
porta è una porta a metà.

**C2 🔴 D-L2-b — la postura ha TRE sedi, non due.** Il loop `20260205-41`
**non è l'ultima parola** (è scritto nella sua intestazione, riga «🔴»):
`scripts/sql/provision_db_roles.sql` gira **dopo** `--contexts=ci_apply` in
`ci-validate.yaml` e in `ci-local.sh`, e fa `GRANT SELECT, INSERT, UPDATE,
DELETE ON ALL TABLES IN SCHEMA magazzino` all'app — riaprirebbe la porta **in
CI, nello stesso build**, in silenzio; su dev non si vede. Le eccezioni
esistenti (`audit_log`/`error_log`, `storico`) stanno **anche lì**
(`provision_db_roles.sql` righe 167-178). ⇒ P-2 = loop **+** forward `90_end`
**+** provisioning, e `test-porta-ledger-v1` è il presidio che le tiene
allineate (stampo: `test-registri-append-only-postura-v1`, che «l'ha detto il
giorno stesso in cui è nato, sul provisioning»).

**C3 🟠 D-L2-h — `ON DELETE CASCADE` righe → testata: una `POSTED` si cancella,
e lascia orfani.** ✅ **Deciso da Tid il 2026-09-18: eliminabile SOLO in `DRAFT`**, `BEFORE DELETE` nel guard di famiglia, codice `E_MAG_DOCUMENTO_NON_ELIMINABILE` (CONFLITTO_STATO, id 1101), P-6. `fk_mag_inventario_righe_testata` e
`fk_mag_rettifiche_righe_testata` sono `ON DELETE CASCADE`; il guard di
famiglia è `BEFORE UPDATE OF <stato>` sulla testata e `BEFORE INSERT OR UPDATE
OR DELETE` sulle righe. Un `DELETE FROM magazzino.inventari WHERE id = <POSTED>`
(l'app ha `DELETE`) cancella la testata, la cascata cancella le righe, e il
guard delle righe — che legge la testata dalla FK — **non la trova più**
(l'azione referenziale gira dopo il `DELETE` del padre): se «testata assente»
passa, i movimenti restano con `INVENTARIO_RIGA:{id}` verso righe sparite —
esattamente ciò che `vw_sorgenti_orfane` è nata per trovare **dopo**. Se
invece «assente» blocca, non si cancella più **nemmeno una `DRAFT`** con righe.
⇒ La porta è la **testata**: `trgfn_documento_interno_guard_transizione` prende
anche `BEFORE DELETE` (`TG_OP = 'DELETE'`): eliminabile solo in `DRAFT` — oppure
mai, se l'uscita è `CANCEL` come in vendite (**decisione**). Codice: riuso di
`E_MAG_DOCUMENTO_TRANSIZIONE_NON_AMMESSA` con `valori` (stato, «eliminazione»)
o un `E_MAG_DOCUMENTO_NON_ELIMINABILE` (CONFLITTO_STATO) — il secondo dice il
verbo. Nel guard delle righe, «testata assente» = cascata già decisa a monte ⇒
passa (sotto RLS un'app non arriva a una riga la cui testata non vede).

**C4 🟠 §4.10 — il cancello B-7 fa rosso un codice NUOVO nato con due
famiglie.** `scripts/codici-errore-baseline.sh`: *«un codice NUOVO nasce con 2+
famiglie note → ROSSO (nasce storto)»*. Così com'è scritto §4.2:
`E_MAG_CHIAMATA_NON_VALIDA` nasce `PARAMETRO` (passo 1, `p_* IS NULL OR <= 0`)
**e** `NOT_FOUND` (passo 4, `IF NOT FOUND` sul magazzino) ⇒ rosso. Idem il
rischio su `E_MAG_DOCUMENTO_TRANSIZIONE_NON_AMMESSA` (matrice nel guard +
`v_stato <> 'CONFIRM'` nell'operazione = `VALORE_ATTESO`) e
`E_MAG_DOCUMENTO_RIGHE_CONGELATE` (`IN ('POSTED','CANCEL')` = `ENUM` +
`= 'CONFIRM' AND GUC`). ⇒ Il passo 4 prende un codice suo,
**`E_MAG_MAGAZZINO_NON_VALIDO`** (TECNICO: un id che nessuna interfaccia
produce — le operazioni lo leggono dalla testata, FK-garantito) e
`E_MAG_CHIAMATA_NON_VALIDA` resta **solo** guard di parametro; `E_CONFIG_MANCANTE`
si solleva **solo** dietro un `IF NOT FOUND` (è la sua unica famiglia
dichiarata). ⭐ Regola operativa per P-5/P-6: **`scripts/codici-errore-baseline.sh`
su dbdev prima di dire «fatto»**, e le righe dei codici nuovi nella baseline
con la ragione nel commit — non dopo il primo rosso in CI.

**C5 🟠 §4.1 — i tre trigger di scope devono seguire lo STAMPO, non un nome
nuovo.** Lo stampo vivo (24 tabelle, `vendite.ordini` compreso) è
`trg_<t>_a10_guard_emittente_scope_ins_upd` su **`BEFORE INSERT OR UPDATE`**;
`guard_scope_<qualifica>` esiste solo dove una tabella ne monta **due**. Il
brief propone `guard_scope` + `UPDATE OF magazzino_id`: due deviazioni per
niente — il guard **salta da solo** se la colonna non cambia, e l'ordine
alfabetico regge uguale (`guard_e…` < `guard_so…` < `guard_v…`). ⇒ nomi
`trg_movimenti_a10_guard_emittente_scope_ins_upd` (47),
`trg_movimenti_attesi_a10_guard_emittente_scope_ins_upd` (54),
`trg_valore_giacenza_a10_guard_emittente_scope_ins_upd` (53), argomenti
`('magazzino', 'magazzino_id')`.

**C6 🟠 D-L2-c — la «media corrente» avrebbe due sedi.** ✅ **Deciso da Tid il 2026-09-18: una regola sola nella vista** — `vw_costo_medio` passa a «`NULL` se `qta <= 0`» e la primitiva la legge dentro il lock, P-5. `magazzino.vw_costo_medio`
esiste già (Lotto 1 §4.8): `valore / qta`, `NULL` a `qta = 0`. D-L2-c dice
`NULL` a giacenza **`≤ 0`** (con `consente_stock_negativo` la giacenza può
essere negativa e il rapporto non significa niente). Una regola sola: la
primitiva **legge `vw_costo_medio` dentro il lock** (è `security_invoker`, e
dentro la DEFINER legge tutto) e la vista passa a `qta > 0` — un `CREATE OR
REPLACE` con `security_invoker` **ri-specificato** e la stessa lettura in
`fn_inventario_piano`/`fn_posta_rettifica` per il costo di ripiego. Da confermare.

**C7 🟡 §4.4 — l'arrotondamento può far suonare la vista di divergenza per
1e-6.** `valore` e `costo_unitario` sono `numeric(18,6)`, `qta` idem: il
prodotto ha fino a dodici decimali, la copia lo **arrotonda a ogni passo**
(scrive `valore + qta × costo` su una colonna a sei decimali), la ri-somma
arrotonda **una volta sulla somma**. Non coincidono «per costruzione» finché
il prodotto non è arrotondato **prima** in entrambe le sedi:
`round(p_qta * v_costo, 6)` nel passo 14 e `sum(round(qta * costo_unitario, 6))`
nel ricalcolo. Un dettaglio da costruire, non una decisione.

**C8 🟡 D-L2-n contro §12.1 — il piano promette righe che la primitiva
rifiuterà.** ✅ **Deciso da Tid il 2026-09-18: check condivisa (b)** — `script.fn_check_riga_magazzino`, letta dalla primitiva e dal piano (esito `NON_POSTABILE`), P-4-bis. I passi 5-8 (`E_MAG_ARTICOLO_NON_GESTITO`, lotto/seriale/ubicazione
obbligatori o non ammessi) sono `DATO_ERRATO` con `campo`, cioè *«chi compila
la riga»* — ma la riga la si compila in `DRAFT`, il piano di `CONFIRM` la
mostra come `INV_INIZIALE`, e il rifiuto arriva **al posting**, all-or-nothing
su tutto il documento. È la «terza via» del §12.1 spostata di un passo.
Due strade, **decisione**: (a) v1 accetta, dichiarato nel `COMMENT` e nel brief
BE/FE (il rifiuto porta `campo` e l'operatore torna sulla riga); (b) i passi
5-8 escono in una `script.fn_check_riga_magazzino(p_magazzino_id, p_articolo_id,
p_lotto_id, p_asset_id, p_ubicazione_id)` pura (motivi ordinati, `campo`),
**chiamata dalla primitiva** (`fn_raise_primo_motivo_se_presente`) **e dal
piano** (esito `NON_POSTABILE` + `reason`) — §12.5.2 applicato: una sede.
Costa una funzione e un pgTAP in più; è la forma che il progetto chiede.

**C9 🟡 §4.1 — `fn_resolve_emittente_fiscale_id` ha sei modi, e la frase
d'errore li elenca.** Il modo `listino` (05-09) manca nell'elenco del brief;
copiando **dalla doc auto-gen** entra da solo, ma la frase del ramo `ELSE`
(*«sono ammessi fiscale, soggetto_ruolo, fattura, listino, ente_incasso e
contabile»*) va riscritta con `magazzino`. Nessun pgTAP la pinna (censito).

**C10 🟡 D-L2-h — il refuso `invetario` vive anche in un INDICE.** Accanto a
`ck_mag_invetario_stato` c'è `uq_mag_invetario_sorgente_fk` (parziale, su
`inventari`). **Non si rinomina qui**: un indice del passato sopravvive sul DB
da zero (memoria `indice_del_passato_sopravvive_alla_rinomina_sul_db_da_zero`)
e non è nel perimetro del lotto; si annota in `manual/inventari.md` come debito
di nome, con la strada (`DROP IF EXISTS` + ricrea, non `RENAME`).

**C11 🟡 §5/§7 — i pgTAP resi rossi dalla porta sono DUE, non tre.**
`test-movimenti-attesi-forma-v1` scrive **solo attesi** (8 `INSERT`), che
restano scrivibili: non cambia. Restano `vincoli-v2` (→ owner, forma 3) e
`valore-giacenza-forma-v1` (→ via primitiva).

**C13 🟡 D-L2-h contro D-L2-n — la matrice non aveva `CONFIRM → DRAFT`.** Il
piano si legge in `CONFIRM` e dice all'operatore «aggiungi una riga» o mostra
una riga `NON_POSTABILE`; le righe si scrivono solo in `DRAFT`. Senza il
ritorno in bozza l'unica uscita sarebbe `CANCEL` e rifare. ✅ **Incluso in
P-6 come conseguenza** (riaprire non scrive movimenti e non cancella niente),
da confermare da Tid.

**C14 🟡 D-L2-f — una posizione contata DUE volte nello stesso inventario
avrebbe postato due delta contro lo stesso `qta_sistema`.** Sorgenti diverse
(`INVENTARIO_RIGA:{id}`) ⇒ identità diverse sul ledger: nessuna rete. Sul
modello una posizione ha un conteggio per inventario: ✅ **`UNIQUE NULLS NOT
DISTINCT` su `inventari_righe` (`20260918-20`)**, non un caso nel piano. Le
rettifiche non lo prendono (due delta dati non sono due letture).

**C15 🟡 §4.4 — le due spie NON possono vivere in `magazzino`.** Il test 2 di
`dbops/test-catalogo-presidi-v1` pretende che **ogni vista degli schemi
presenti in `presidi.vista`** abbia una riga a catalogo: una spia in
`magazzino` avrebbe portato lo schema nel perimetro e reso rosse le sette
viste di dominio. Stampo di casa: `dbops.vw_af_senza_giro` (una spia di
vendite in `dbops`). ✅ Fatto: `dbops.vw_magazzino_valore_giacenza_divergente`,
`dbops.vw_magazzino_movimenti_senza_costo`.

**C16 🟡 §4.7 — il perimetro degli orfani «FK + due colonne» pescava anche
`vendite`.** `attivita_fatturabili`, `fatture_righe` hanno FK e colonne ma
un'altra semantica (`sorgente_riga` = riga del documento, `sorgente_uid` =
documento) e **non** il guard tipizzato: 112 falsi orfani su dev (fatto
datato). Il contratto del modello A è il **guard**: perimetro = FK + colonne
+ `trgfn_guard_sorgente_polimorfa_tipizzata` montato (`pg_trigger`). Le
tabelle di `vendite` entrano col roll-out D-3 (§9). ✅ Fatto.

**C12 🟡 D-L2-d — `consente_stock_negativo` è falso su tutte le causali.**
Fatto datato, non premessa: il ramo esiste sul modello e il pgTAP di §7 deve
**costruire** il caso (`UPDATE magazzino.causali SET consente_stock_negativo`
in transazione, come app se il privilegio c'è, altrimenti il file dichiara
perché gira owner) — pescare una causale dal catalogo darebbe un verde per
sottrazione.

---

## 7. I presidi

> Come l'applicazione, sotto RLS, fixture **costruite** (azienda, operatore,
> indirizzo, magazzino, **articolo con i flag scelti dal test**, lotto, asset,
> inventario/rettifica con righe). `throws_like` sulla frase dove la frase è la
> posta in gioco; mai `throws_ok(…, NULL, NULL)`. Preambolo a tre righe.

| Test | Che cosa prova |
| --- | --- |
| `magazzino/test-fn-scrivi-movimento-controlli-v1` | i quattordici passi di §4.2, **uno per test**, ciascuno col caso costruito: causale sconosciuta, verso incoerente (la frase della madre, non del trigger), articolo non gestito (`campo = articolo_id` nel context), lotto obbligatorio/non ammesso/di altro articolo, seriale idem + altro emittente, ubicazione obbligatoria/non ammessa (D-L2-m: due magazzini costruiti, uno per verso)/di altro magazzino; `usa_ubicazioni` non si cambia su un magazzino con un movimento (`E_MAG_MAGAZZINO_CON_GIACENZA`) e si cambia su uno vuoto, identità già registrata (la frase nomina l'id), costo non ammesso in uscita, gemella assente, storno incoerente; il caso buono torna un id e la riga è **come attesa** (qta firmata, costo, sorgente) |
| `magazzino/test-fn-scrivi-movimento-disponibilita-v1` | uscita oltre la giacenza → `E_MAG_GIACENZA_INSUFFICIENTE` con i valori nella frase; uscita dentro la giacenza ma oltre i **blocchi altrui** → `E_MAG_MERCE_BLOCCATA`; lo **stesso** blocco con la **stessa sorgente** del movimento non ferma; `consente_stock_negativo` passa sotto zero; `is_rettifica` (`RETT_NEG`) ignora i blocchi ma **non** il fisico; grana **lotto** (articolo 20, lotto 3, uscita 5 dal lotto → rifiuto); l'array della check e il codice sollevato **coincidono** (test che chiama la check da sola, come operatore, e la confronta col rifiuto) |
| `magazzino/test-fn-scrivi-movimento-seriali-v1` | asset: entrata quando è già dentro → posizione incoerente; uscita da dove non è → idem; entrata poi uscita poi entrata altrove → passa; `\|qta\| = 1` (CHECK) |
| `magazzino/test-fn-scrivi-movimento-valore-v1` | entrata a 10 € × 5 poi a 20 € × 5 ⇒ valore 150, media 15; uscita di 4 ⇒ `costo_unitario = 15` scritto sul movimento e valore 90; entrata **senza costo** ⇒ costo NULL, valore invariato, riga in `dbops.vw_magazzino_movimenti_senza_costo`; trasferimento OUT/IN con lo stesso `transfer_uid` ⇒ la IN porta il costo della OUT e i due valori si spostano; storno ⇒ costo dell'originale; `fn_ricalcola_valore_giacenza` **coincide** con la copia; una scrittura fuori porta (come owner, `pgtap-runner: owner` in un file **suo**: `test-valore-giacenza-divergenza-owner-v1`) fa comparire la riga in `dbops.vw_magazzino_valore_giacenza_divergente` e il ricalcolo la fa sparire |
| `magazzino/test-fn-posta-inventario-v1` | primo conteggio su merce mai movimentata ⇒ `INV_INIZIALE` con il costo della riga; conteggio su merce già a registro ⇒ `RETT_POS`/`RETT_NEG` per delta; delta zero ⇒ nessun movimento, `qta_sistema` scritto lo stesso; **grana**: riga con lotto confronta il lotto; **il piano** (D-L2-n): contata in UY con merce in UX ⇒ una riga `NON_CONTATA` per UX, il posting scrive UY e lascia UX, e `qta_sistema` sulla riga è quello del piano; un magazzino con `usa_ubicazioni` rifiuta la riga senza ubicazione (`E_MAG_UBICAZIONE_OBBLIGATORIA`) e uno senza la rifiuta con (`_NON_AMMESSA`) — D-L2-m; stato non `CONFIRM` ⇒ transizione non ammessa; senza righe ⇒ `NON_ESEGUIBILE`; **all-or-nothing**: la terza riga fallisce (articolo non gestito) e le prime due non sono a registro, testata ancora `CONFIRM`; posting due volte ⇒ la seconda rifiuta su `POSTED` |
| `magazzino/test-fn-posta-rettifica-v1` | stessa forma: delta dato, causale dal segno, costo dalla riga, `RETT_NEG` oltre la giacenza ⇒ rifiuto fisico, `RETT_NEG` sotto un blocco altrui ⇒ **passa** (il fatto vince) |
| `magazzino/test-documenti-interni-guard-v1` | la matrice (la stessa per le due famiglie, senza `COUNTING`): ogni transizione ammessa passa, ogni vietata dà `E_MAG_DOCUMENTO_TRANSIZIONE_NON_AMMESSA`; `UPDATE … SET stato = 'POSTED'` diretto ⇒ `E_MAG_DOCUMENTO_POSTED_SOLO_DA_OPERAZIONE`; righe su `POSTED`/`CANCEL` ⇒ congelate; righe in `CONFIRM` scritte dall'app ⇒ congelate, dall'operazione ⇒ passa; il `CHECK` di `inventari` ha **quattro** valori e si chiama `chk_mag_inventari_stato` |
| `magazzino/test-porta-ledger-v1` | `has_table_privilege('zeroerp_app', 'magazzino.movimenti', 'INSERT\|UPDATE\|DELETE')` **false**, `SELECT` true; idem `valore_giacenza`; `movimenti_attesi` senza `DELETE`; `INSERT` diretto come app ⇒ `42501`; **la primitiva è DEFINER del proprietario delle tabelle** (`proowner = relowner`, stampo `test-catalogo-presidi-v1` t.11), `proconfig` contiene il pin con `public`; le tre funzioni DEFINER del lotto hanno il pin; il guard di scope è montato sulle tre tabelle e **rifiuta** una scrittura via primitiva su un magazzino di un altro emittente (`E_SCOPE_EMITTENTE`) — due aziende costruite **come app, cambiando contesto operatore** (`fn_pgtap_set_contesto_operatore(auth_user_id)` dell'una e dell'altra: il magazzino B nasce nel contesto di B, il tentativo si fa nel contesto di A), non con l'owner: la DEFINER vede il magazzino B, il guard dice che A non può |
| `magazzino/test-vw-disponibilita-v1` | giacenza 10, blocco −4 ⇒ `bloccata = −4`, `disponibile = 6`; blocco `CHIUSA` non conta; articolo con blocco e **senza movimenti** compare (disponibile −4); la grana per articolo somma i magazzini; `security_invoker` su entrambe |
| `dbops/test-sorgenti-orfane-v1` | il perimetro contiene le **sei** tabelle di `magazzino` (gemello «esiste»); zero orfani sul mondo costruito; cancellato il bersaglio di un movimento **come owner** (file suo, `pgtap-runner: owner`: la FK non c'è per definizione, e l'app non cancella righe di inventario postate) ⇒ **una** riga con tabella, id e sorgente; `fn_conta_presidio('dbops.vw_sorgenti_orfane')` = 1 |
| `dbops/test-articoli-a-magazzino-prontezza-v1` | la vista ha **una** riga; con zero articoli marcati (`UPDATE` in transazione: il test costruisce lo stato) ⇒ `NESSUNO_MARCATO` e `fn_conta_presidio` = 1; con uno marcato ⇒ `MARCATI` e 0; la riga in `dbops.presidi` c'è con natura/coppia/cadenza attese |
| `magazzino/test-movimenti-vincoli-v2` (esistente) | **ri-collocato** `pgtap-runner: owner` con motivo (forma 3): il soggetto sono i vincoli, che dal Lotto 2 solo il proprietario può far scattare direttamente. Asserzioni **invariate** |
| `magazzino/test-valore-giacenza-forma-v1` (esistente) | la fixture costruisce la giacenza **attraverso `fn_scrivi_movimento`** invece dell'`INSERT` diretto; asserzioni invariate |
| `dbops/test-presidi-catalogo`, `test-presidi-debito-dichiarato`, `rls/test-rls-perimetro-scoperto`, `config/…` | ✅ riletti in P-0/P-8: `test-catalogo-presidi-v1` t.2 pretende che **ogni vista di uno schema presente in `presidi.vista`** sia a catalogo — è il motivo per cui le quattro spie vivono in `dbops` (C15); nessuno conta le righe di `presidi.csv`; t.2 e t.3 provati verdi con le quattro righe |
| `dbops/test-riferimenti-morti-v1`, `script/test-rubinetto-primo-motivo-v1` | 🔴 **I due presidi TRASVERSALI che ogni funzione plpgsql NUOVA attraversa**, e che questo lotto ha reso rossi dopo l'apply (18-09) senza che nessuna riga di questa tabella li nominasse: il primo compila **ogni** funzione con `plpgsql_check` (un `record` da SQL dinamico esce `REALE`), il secondo pinna con un'**uguaglianza esatta** quante funzioni chiamano `fn_raise_primo_motivo_se_presente` (ogni sito nuovo nato sull'helper la sposta, ed è voluto: «va guardato»). Si rilanciano **prima** di dire «fatto», in ogni cantiere che aggiunge funzioni. Esito 18-09: `20260918-27` e test 5 a 19 con predicato sulla CHIAMATA — ✅ **entrambi verdi col runner dopo l'apply** |

⚠️ La serializzazione del lock **non si prova in pgTAP** (mono-sessione): si
asserisce **strutturalmente** (`test-porta-ledger-v1` t.15: `pg_advisory_xact_lock`
a due argomenti col namespace `magazzino.fn_scrivi_movimento`, pattern
`vendite/test-ordini-lock-cliente.sql`) e si prova a mano a due sessioni
`psql` — ✅ **fatta il 2026-09-22, esito in §12.5.4**: B ha atteso 8,1 s il
rilascio di A e ha riletto la disponibilità **dopo** il lock.

---

## 8. Doc e cataloghi da toccare

✅ **Fatto il 2026-09-18** (P-10) — l'elenco com'era, con le correzioni di
nome di §6-ter (C15: le spie in `dbops`) e le pagine nate strada facendo
(`fn_check_riga_magazzino`, `fn_sorgenti_orfane_perimetro`, i due helper
pgTAP, il guard di `usa_ubicazioni`, la rev C1 del guard di scope):

- `docs/it/dbzero/magazzino/manual/`: **nuovi** `fn_scrivi_movimento.md`,
  `fn_ricalcola_valore_giacenza.md`, `fn_posta_inventario.md`,
  `fn_posta_rettifica.md`, `fn_inventario_piano.md`, `trgfn_documento_interno_guard_transizione.md`,
  `trgfn_documento_interno_righe_guard_testata.md`, `trgfn_magazzini_guard_usa_ubicazioni.md`,
  `vw_disponibilita.md`, `vw_disponibilita_articolo.md`; le due spie del valore
  stanno in **`dbops`** (C15): `vw_magazzino_valore_giacenza_divergente.md`,
  `vw_magazzino_movimenti_senza_costo.md`; **aggiornati** `vw_costo_medio.md`,
  `vw_costo_medio_globale.md`, `vw_giacenza_valorizzata.md` (C6: `NULL` a
  `qta <= 0`), `movimenti.md` (chi scrive:
  la primitiva; la porta), `valore_giacenza.md`, `movimenti_attesi.md` (chi
  legge i blocchi), `inventari.md`, `inventari_righe.md` (il costo, la grana),
  `rettifiche.md`, `rettifiche_righe.md`, `causali.md` (`is_rettifica` armata),
  `magazzini.md` (il modo di scope; `usa_ubicazioni`: decide il magazzino, si cambia solo a registro vuoto; `trasferimenti` = interno, il DDT `TRASFERIMENTO` = con trasporto), `trasferimenti.md` (la D di D-L2-g);
- `docs/it/dbzero/script/manual/`: **nuovi** `fn_check_disponibilita_uscita.md`,
  `fn_check_riga_magazzino.md`; **aggiornati** `fn_resolve_emittente_fiscale_id.md`
  («I sette modi»: la riga `magazzino`), `trgfn_guard_emittente_scope.md` (rev
  2026-09-18: dentro una DEFINER il criterio risponde per la persona sbagliata — C1);
- `docs/it/dbzero/dbops/manual/`: **nuovi** `fn_sorgenti_orfane.md`,
  `fn_sorgenti_orfane_perimetro.md`, `vw_sorgenti_orfane.md`,
  `vw_articoli_a_magazzino_prontezza.md`, `vw_magazzino_valore_giacenza_divergente.md`,
  `vw_magazzino_movimenti_senza_costo.md`, `fn_pgtap_crea_articolo.md`,
  `fn_pgtap_crea_magazzino.md`;
- `docs/it/dbzero/catalogo/manual/vw_articoli_dettaglio.md` e `articoli.md`
  (`requires_lotto`: chi lo legge);
- `docs/it/dbzero/magazzino/_dominio-magazzino.md`: il modello **col motore**;
- `docs/it/mappa-concentrica.md`, riga `magazzino`: da «forma decisa, perimetro
  armato, in attesa della primitiva» a «primitiva e prime due operazioni in
  esercizio; scarico da DDT al Lotto 3»;
- `docs/it/guide/presidi-e-registri-del-debito.md`: ✅ verificato, **non**
  elenca le viste per nome (rimanda a `dbops.presidi`): niente da toccare;
- questo brief: lo stato di ogni passo, il riquadro P-0, la data di ogni D-L2 ✅.

⛔ `index.md`/`index.ci.md` sono generati e non si toccano; la build della doc
non si lancia; l'autogen (`changelog-autogen.yaml`) non si rigenera a mano.

---

## 9. Che cosa NON entra, e dove sta

| Cosa | Dove | Perché non qui |
| --- | --- | --- |
| lo **scarico da DDT di vendita** (passo 3): l'aggancio a `EMESSO`, il filtro sugli articoli non gestiti, la conversione UoM | Lotto 3 | tocca `vendite.ddt`, che è in esercizio: il primo scrittore deve poter sbagliare da solo (§1). ⚠️ Eredita da qui: la primitiva rifiuta gli articoli non gestiti, quindi l'operazione **filtra** prima |
| la **utility di storno** (M-8) | Lotto 3 | è un'operazione; il **ramo** della primitiva è qui e provato |
| il **posting del DDT `TRASFERIMENTO`** (con trasporto) e quello di `magazzino.trasferimenti` (interno: stesso magazzino fra ubicazioni, o magazzini dello stesso emittente — D di Tid del 17-09, in D-L2-g) | Lotto 3: il DDT aspetta il `magazzino_id` sul DDT (lo stesso dello scarico da vendita); `trasferimenti` aspetta le ubicazioni sulle righe e il CHECK allargato | il ramo gemella della primitiva è qui e provato; i due documenti si armano con le loro colonne |
| aprire e **liberare un blocco manuale** (`movimenti_attesi`) | Lotto 3, col DDT (è alla spedizione che il blocco ferma) | qui gli attesi si **leggono** (disponibilità) e restano scrivibili dall'app sotto RLS + guard; il verbo «libera» con la traccia sul documento è di quel lotto |
| **eventi asset** (`ASSET_INSTALL`/`ASSET_RIENTRO`), `is_installazione_asset`, `assets.stato_id` | lotto suo (D-L2-l) | il pezzo lascia il magazzino e cambia stato: è un documento in più |
| le colonne **impegnata / potenziale / in arrivo** di `vw_disponibilita` | dopo il satellite **D-17** (analisi acquisti §7) e il Lotto 3 | la soglia dell'impegno è una riga sola per due cicli (c/s §7-bis) |
| `causali.sorgente_tipo_id` 1:1 | nessuno, per ora (D-L2-i) | la forma è smentita prima di nascere |
| il **BE/FE di magazzino** (endpoint di posting, drawer inventario, lista movimenti) | brief BE/FE suo, dopo questo | nasce quando la primitiva esiste; qui solo le due richieste minime (§4.9, §4.10) |
| il roll-out del guard di scope in scrittura sulle **testate** di magazzino (`inventari`, `rettifiche`, `trasferimenti`) e del guard tipizzato sulle nove tabelle fuori schema (D-3) | cantiere `dbops` | le testate sono scritte da INVOKER sotto `WITH CHECK`: già coperte; qui si monta dove la DEFINER le scavalca |
| `FORCE ROW LEVEL SECURITY` | nessuno | postura del progetto |
| l'apply, i pgTAP col runner, il commit | Tid | l'apply e il commit non sono autonomi |

---

## 10. Riferimenti

- Le decisioni: [analisi carico e scarico](../work-in-progress/analisi-db-magazzino-carico-e-scarico.md)
  (M-1 → M-9, §5-bis la primitiva, §7-bis la formula, §8 i lotti),
  [analisi aggancio §8-quater](../work-in-progress/analisi-db-magazzino-aggancio-documento-e-produzione.md)
  (D-1 → D-9), [Lotto 1](brief-db-magazzino-lotto-1-terreno-vuoto.md)
  (§3 D-L1-*, §5 le lezioni, §9 che cosa rinvia qui),
  [emittente di default](brief-db-emittente-di-default-un-bb-solo.md),
  [modifiche certe §7](brief-db-modifiche-certe-ciclo-vendita-e-articolo.md)
  (il presidio di prontezza).
- Le forme da copiare: `fn_check_*` pura → `script.fn_check_ordine_confermabile`;
  il sollevamento dal primo motivo → `script.fn_raise_primo_motivo_se_presente`;
  la guard di parametro `TECNICO` → `E_VENDITE_CHIAMATA_NON_VALIDA`; il guard
  di scope in scrittura → `vendite.ordini` + `script.trgfn_guard_emittente_scope`
  + `fn_resolve_emittente_fiscale_id`; la GUC-porta →
  `script.fn_change_user_emittenti_scope` / `zeroerp.allow_user_emittente_delete_override`;
  DEFINER del proprietario → `config.fn_accoda_email_sistema`, `dbops.fn_conta_presidio`;
  l'advisory lock a due argomenti → `vendite.fn_aggiungi_onere_commessa`; il
  loop dei grant → `90_end/ci_apply/20260205-41`; la vista di presidio
  dinamica → `dbops.vw_riferimenti_morti_da_sanare`; le fixture →
  `magazzino/test-movimenti-vincoli-v2` (Lotto 1).
- Regole: linee-guida-sql §5b (madre), §12.5 (azioni per riga, la madre chiama
  la check), §11.8 (postura nel loop); AGENTS.md §«Sollevare un errore»;
  `scripts/testpgtap.sh` intestazione (il criterio `owner`);
  `scripts/check_i18n_keys.py` controllo 4.
- Letto dal catalogo vivo il 2026-09-17: `pg_proc` (le tre funzioni di Lotto 1,
  `trgfn_guard_sorgente_polimorfa_tipizzata`, `trgfn_guard_emittente_scope`,
  `fn_resolve_emittente_fiscale_id`, `fn_check_user_emittente_scope`,
  `fn_raise_primo_motivo_se_presente`, `fn_conta_presidio`), `pg_policy` sul
  ledger, `pg_constraint` (25 CHECK del dominio), `config.sorgenti` (le dieci
  righe di riga/magazzino, tutte attive), `causali` (sedici), `dbops.presidi`
  (38 righe, struttura e CHECK), `catalogo.articoli` (i sei flag),
  `vw_articoli_dettaglio` (54 colonne, senza `requires_lotto`).

---

## 11. Registro delle revisioni

| Data | Cosa |
| --- | --- |
| 2026-09-24 (notte) | 📦 **ARCHIVIATO in `work-done/`** (decisione di Tid). Il lotto era consegnato dal 22-09; l'ultimo residuo — la porta chiusa a metà — è chiuso in `brief-db-magazzino-verbi-con-permesso` (`20260924-38` → `-42` applicati, pgTAP verdi). Link aggiornati nei documenti che lo citano per percorso |
| 2026-09-24 | ⚠️ **Nota in D-L2-b, lotto non riaperto.** La porta è chiusa a metà: l'app può chiamare la primitiva direttamente e nessuna funzione controlla `registra_magazzino`. Il completamento è un cantiere a sé, [brief-db-magazzino-verbi-con-permesso.md](../work-in-progress/brief-db-magazzino-verbi-con-permesso.md) (decisione D-4 di Tid, stesso giorno): questo brief resta la fotografia di ciò che è stato consegnato |
| 2026-09-22 | ✅ **Chiusi i quattro residui di §12.5, e il lotto è consegnato intero.** (1) **La prova del lock a due sessioni** è stata eseguita come app sul mondo committato di dbdev (magazzino `1109`, articolo `art-comp-001`, contesti operatore 5 e 6), con la sorgente tipizzata costruita **dentro ciascuna transazione** e tutte e due ritirate: `pg_locks` mostra la **stessa coppia di chiavi** con A `granted = t` e B `granted = f`, B ha impiegato **8 129 ms** (attesa, non rifiuto immediato) e al rilascio ha riletto sul saldo **committato** (`disponibili 0`) — la disponibilità si legge **dopo** il lock, e il ledger è rimasto vuoto. ⚠️ Il ramo «passa sul saldo aggiornato» resta **dichiarato non provato**: vorrebbe una scrittura permanente su dbdev. (2) **B-7 `--update`** era già fatto e committato (dieci codici nuovi + `E_CONFIG_MANCANTE` a 52). (3) **Commit** `787ab05ba`, mergiato con la PR #1605. (4) **La CI da zero è verde**: la corsa `35451924195` (19-09) contiene questo commit e ha fatto migrate da zero + `ci_apply` + provisioning + Django + **suite pgTAP**, con zero righe di magazzino in `baseline-rossi-ci.tsv` ⇒ `ci-local.sh --fresh --ci-apply` è ridondante. ⚠️ Due fatti datati **fuori dal lotto**: dal 21-09 sera la CI **non parte** (billing GitHub), e l'ultima corsa reale della suite aveva **una** regressione — `ui/test-lista-definizione-perimetro-emittente-v1`, già sanata il 22-09 (`559dbf351`). ⚠️ Il presidio di prontezza su dbdev è passato da `NESSUNO_MARCATO` a `MARCATI \| 3`: l'uso in-app ha marcato tre articoli. 🔵 **Decisione di Tid lo stesso giorno: il brief resta in `work-in-progress/`** — consegnato, non ancora archiviato |
| 2026-09-18 (pomeriggio, chiusura DB) | ✅ **`20260918-27` applicato da Tid e i due presidi trasversali rilanciati: verdi.** Con questo il lato DB del lotto è **chiuso**: 22 changeSet `EXECUTED`, quindici pgTAP del lotto verdi come app, i due trasversali verdi, B-7 verde sul catalogo vivo. Aggiornati la testa del brief (§Stato), §6 P-8/P-9, §7, §12.1, §12.2, §12.5. ⏳ A Tid restano B-7 `--update`, il lock a due sessioni, `ci-local.sh --fresh --ci-apply`, il commit; a BE/FE §4.9 e §4.10. Chiusura del brief in `work-done/` quando anche la CI da zero è verde |
| 2026-09-18 (pomeriggio, dopo l'apply) | 🔴 **Due regressioni dal runner come app, entrambe su presidi TRASVERSALI e non sui dodici pgTAP del lotto.** (1) `dbops/test-riferimenti-morti-v1` test 2: `fn_sorgenti_orfane` → `55000 record "v_s" non ancora assegnato` + `XX000 cached plan` sul `RETURN QUERY`, classe `REALE` — un `record` riempito da `FOR … IN EXECUTE` ha tupla indeterminata per `plpgsql_check` (lo dice il suo stesso hint alla riga 18). Rimedio sul modello, non nel registro: **`20260918-27`**, il ciclo interno su tre scalari `%TYPE` di `config.sorgenti`; comportamento e firma invariati, provato con l'SQL estratto in `ROLLBACK` (6/6 + 9/9), cinque guardrail statici verdi. (2) `script/test-rubinetto-primo-motivo-v1` test 5: 20 contro 17. Tre menzioni nuove, ma **due** chiamate (`fn_scrivi_movimento`, `fn_posta_inventario`: siti nati sull'helper) e **una** in un commento (`fn_check_disponibilita_uscita`, che nomina il consumatore): il predicato contava il TESTO. Riscritto sulla **chiamata** (commenti tolti, nome + `(`, la forma di `vw_punti_primo_motivo`) e portato a **19** con la nota datata; 7/7 in transazione ritirata. Registrati in §4.7, §5 (due trappole), §6 P-8/P-9, §7 (riga nuova: i due presidi trasversali si rilanciano in ogni cantiere che aggiunge funzioni). ⏳ Apply del `-27`, rilancio dei due file e baseline: Tid |
| 2026-09-18 (giornata) | ✅ **Sviluppato P-1 → P-10**, dopo le quattro decisioni di Tid (C1 «nel BB guard, A′», C3 «solo in DRAFT», C6 «la vista, a `qta > 0`», C8 «check condivisa»): **21 changeSet** `20260918-06 … -26` (`-01…-05` sono di `pagamenti`), tre sedi in place (loop `20260205-41`, `provision_db_roles.sql`, i tre CSV: 27 codici, 27 messaggi, 4 presidi), **dodici pgTAP nuovi** (127 asserzioni) e tre ri-collocati, venti pagine `manual/` nuove e diciassette aggiornate, il dominio e la mappa. Quattro criticità in più trovate scrivendo (C13 `CONFIRM → DRAFT`, C14 `UNIQUE` di posizione sulle righe d'inventario, C15 le spie in `dbops` per il test 2 del catalogo dei presidi, C16 il perimetro degli orfani pretende il guard tipizzato montato: 112 falsi orfani da `vendite` senza). Ogni passo provato con l'SQL **estratto** in transazione annullata su dev e `zeroerp_ci`, i pgTAP in un harness come owner (nove asserzioni sole vogliono l'app). ✅ **Applicato da Tid su dbdev alle 12:23** (21 `EXECUTED` in `databasechangelog`, postura t/f/f/f sul ledger, 27 messaggi, 4 presidi; B-7 verde sul catalogo vivo). Consegna in §12 |
| 2026-09-18 (mattina) | ✅ **P-0 eseguito** (§6-bis, letto dal catalogo vivo di dbdev e da `zeroerp_ci`, seed dai CSV). Ne escono **dodici criticità** in §6-ter, due delle quali **bloccano P-2**: **C1** — il guard BB di scope è **fail-open dentro una DEFINER** (`row_security_active` risponde per il proprietario; **provato in `ROLLBACK`** con `fn_accoda_email_sistema`: la stessa scrittura senza GUC è rifiutata diretta e passa via DEFINER), quindi la frase di D-L2-b «vale la stessa regola di `vendite.ordini`» è falsa — rimedio proposto nel BB (A′: dentro una DEFINER, riga *con* padrone e sessione senza identità → `E_SCOPE_SENZA_UTENTE`), ripiego nella primitiva (B′); **C2** — la postura ha **tre** sedi (loop + forward + `provision_db_roles.sql`, che gira dopo `ci_apply` e riaprirebbe la porta in CI). Poi: C3 `ON DELETE CASCADE` righe→testata (una `POSTED` si cancella con orfani: serve `BEFORE DELETE` sulla testata — decisione DRAFT-only o mai), C4 il cancello B-7 su un codice nuovo con due famiglie (`E_MAG_CHIAMATA_NON_VALIDA` al passo 4 → codice suo `E_MAG_MAGAZZINO_NON_VALIDO`), C5 lo stampo dei trigger di scope (`guard_emittente_scope`, `BEFORE INSERT OR UPDATE`), C6 la media corrente ha già una sede (`vw_costo_medio`, da portare a `qta > 0`), C7 arrotondamento a sei decimali in entrambe le sedi, C8 il piano promette righe che la primitiva rifiuta (§12.1: v1 dichiarato o `fn_check_riga_magazzino` condivisa — decisione), C9 sei modi del resolver e la frase da riscrivere, C10 il refuso anche nell'indice, C11 i rossi sono due non tre, C12 `consente_stock_negativo` falso ovunque (il test costruisce). Corretti §5 e D-L2-b sui «tre pgTAP». Regola di Tid registrata in P-0: `%TYPE` in firma, `DECLARE` e `RETURNS TABLE`; numero libero `20260918-05` da ricontrollare. 🔵 **Nessun changeSet**: si aspettano le decisioni su C1, C3, C6, C8 |
| 2026-09-17 (sera, poi) | ✅ **Quattordici decisioni prese da Tid, una alla volta** (in chat, esposte in linguaggio semplice). Dodici confermate; tre **modificate confermando**: D-L2-f — l'«angolo» delle ubicazioni era in realtà un **raddoppio della giacenza** da un conteggio giusto, chiuso sul modello da **D-L2-m** (`magazzini.usa_ubicazioni`: decide il magazzino, come `requires_lotto`/`requires_serial` decidono l'articolo; si cambia solo a registro vuoto); D-L2-g — la prima stesura diceva che lo spostamento «non ha un documento» ed era falso a metà: il trasferimento **con trasporto è il DDT `TRASFERIMENTO`** (`config.causali_trasporto`, letto da dieci oggetti di vendite; al DDT manca il `magazzino_id`, Lotto 3), e Tid ha deciso che **`magazzino.trasferimenti` è il trasferimento interno** (stesso magazzino fra ubicazioni, o magazzini dello stesso emittente); D-L2-h — **`COUNTING` esce** (solo nel CHECK, nessun consumatore, nessuna regola diversa): matrice unica per le due famiglie, CHECK rinominato `chk_mag_inventari_stato`. Una nuova da un dubbio di Tid: **D-L2-n**, «contata in UY, a registro in UX» → `fn_inventario_piano`, una funzione per UI e posting, con le posizioni `NON_CONTATA` segnalate e non bloccanti. Ricadute propagate in §4.2 (passo 8), §4.5, §4.10 (+4 codici), §6 (P-1, P-6), §7, §8, §9 |
| 2026-09-17 (sera) | **Nascita.** Con Lotto 1 e Lotto 1-bis chiusi, il motore: la primitiva coi quattordici passi, la check di disponibilità condivisa, il valore con ricalcolo e divergenza, le due operazioni senza documento commerciale, le viste, gli orfani, la prontezza, la porta. **Dodici decisioni piccole** emerse scrivendo (§3), fra cui tre che l'analisi non aveva visto: l'inventario iniziale **non ha un costo** (D-L2-c → colonna sulle righe), lo spostamento fra ubicazioni **non ha un documento** (D-L2-g → D aperta, trasferimento fuori), `is_rettifica` trova il suo **primo consumatore** (D-L2-d: una rettifica non si ferma su un blocco). Fatti di struttura letti dal catalogo e non presenti nelle analisi: `trgfn_guard_emittente_scope` ha già la forma per proteggere una DEFINER (basta un modo), `E_SCOPE_EMITTENTE`/`E_SCOPE_SENZA_UTENTE`/`E_CONFIG_MANCANTE` esistono e si riusano, tre pgTAP del Lotto 1 scrivono direttamente sul ledger e la porta li rende rossi per costruzione (dichiarato, non in baseline), `vw_articoli_dettaglio` non porta `requires_lotto`. ⛔ Nessun changeSet: le D-L2 si confermano prima |

---

## 12. Consegna — che cosa c'è e che cosa resta a Tid

### 12.1 I changeSet — 22 (`-06 … -27`; il `-27` dopo il primo giro del runner), tutti `runOnChange: false`, `failOnError: true`, con rollback — ✅ tutti `EXECUTED` su dbdev

| # | Fase | Che cosa | Stato dbdev (18-09) |
| --- | --- | --- | --- |
| `20260918-06` | `00_schema/magazzino` | `costo_unitario numeric(18,6)` su `inventari_righe` e `rettifiche_righe` + `CHECK >= 0` (D-L2-c) | ✅ `EXECUTED` 12:23 |
| `-07` | `00_schema/magazzino` | `magazzini.usa_ubicazioni boolean NOT NULL DEFAULT false` (D-L2-m) | ✅ |
| `-08` | `00_schema/magazzino` | `ck_mag_invetario_stato` → `chk_mag_inventari_stato` a quattro valori, `COUNTING` fuori (D-L2-h, C10) | ✅ |
| `-09` | `20_code/magazzino` | `trgfn_magazzini_guard_usa_ubicazioni` + trigger `BEFORE UPDATE OF usa_ubicazioni` | ✅ |
| `-10` | `20_code/catalogo` | `vw_articoli_dettaglio` + `requires_lotto` in coda (colonna 56), senza `security_invoker` | ✅ |
| `-11` | `20_code/script` | `fn_check_disponibilita_uscita` (pura, i due motivi, `trim_scale`) | ✅ |
| `-12` | `20_code/script` | `fn_resolve_emittente_fiscale_id`: modo `magazzino`, frase dei sette modi (C9) | ✅ |
| `-13` | `20_code/script` | `trgfn_guard_emittente_scope`: la rev C1 (`current_user <> session_user` dentro una DEFINER) | ✅ |
| `-14` | `20_code/magazzino` | i tre trigger di scope sul ledger, con lo stampo (C5) | ✅ |
| `-15` | `90_end` | il forward della postura: `REVOKE INSERT, UPDATE, DELETE` su `movimenti`/`valore_giacenza`, `REVOKE DELETE` su `movimenti_attesi` | ✅ `EXECUTED` 12:23:15, e il loop `20260205-41` `RERAN` nello stesso secondo (checksum nuovo): postura a fine corsa t/f/f/f · t/t/t/f |
| `-16` | `20_code/script` | `fn_check_riga_magazzino` (C8: articolo gestito, lotto, seriale, ubicazione; `campo` nel `dettaglio`) | ✅ |
| `-17` | `20_code/magazzino` | `vw_costo_medio`, `vw_giacenza_valorizzata`, `vw_costo_medio_globale`: `NULL` a `qta <= 0`, `security_invoker` ri-specificata (C6) | ✅ |
| `-18` | `20_code/magazzino` | **`fn_scrivi_movimento`** — la porta (DEFINER di chi migra, pin `pg_catalog, public, pg_temp`, quattordici passi) | ✅ proprietario `titodb` = proprietario di `movimenti` |
| `-19` | `20_code/magazzino` | `fn_ricalcola_valore_giacenza` + `dbops.vw_magazzino_valore_giacenza_divergente`, `dbops.vw_magazzino_movimenti_senza_costo` (C15) | ✅ |
| `-20` | `00_schema/magazzino` | `uq_mag_inventari_righe_posizione` UNIQUE NULLS NOT DISTINCT (C14) | ✅ |
| `-21` | `20_code/magazzino` | i due guard di famiglia (`…guard_transizione`, `…righe_guard_testata`) + quattro trigger (D-L2-h, C3, C13) | ✅ |
| `-22` | `20_code/magazzino` | `fn_inventario_piano` (D-L2-n, esito `NON_POSTABILE`) | ✅ |
| `-23` | `20_code/magazzino` | `fn_posta_inventario`, `fn_posta_rettifica` (INVOKER, GUC transazionale) | ✅ |
| `-24` | `20_code/magazzino` | `vw_disponibilita`, `vw_disponibilita_articolo` (D-L2-j) | ✅ |
| `-25` | `20_code/dbops` | `fn_sorgenti_orfane_perimetro`, `fn_sorgenti_orfane`, `vw_sorgenti_orfane`, `vw_articoli_a_magazzino_prontezza` (D-9, C16) | ✅ |
| `-26` | `20_code/dbops` | `fn_pgtap_crea_articolo`, `fn_pgtap_crea_magazzino` (regola del 2 per i pgTAP) | ✅ |
| **`-27`** | `20_code/dbops` | **rev** `fn_sorgenti_orfane`: il ciclo interno su tre scalari `%TYPE` invece del `record` da SQL dinamico (il presidio dei riferimenti morti lo riferiva `REALE`, §4.7) — stessa firma, stesso comportamento | ✅ `EXECUTED` (Tid, 18-09 pomeriggio, dopo il primo giro del runner) |

**In place** (non changeSet): `90_end/ci_apply/20260205-41` (le due liste
`v_tabelle_sola_lettura_app` / `v_tabelle_senza_delete` e i rami; C2),
`scripts/sql/provision_db_roles.sql` (blocco «POSTURA DICHIARATA», C2),
`80_data/sql/config/codici_errore.csv` + `messaggi_errore.csv` (27 + 27,
id 1075–1101), `80_data/sql/dbops/presidi.csv` (4 righe, tutte
`SETTIMANALE`). ✅ Tutti entrati su dbdev con l'apply delle 12:23 (letti dal
catalogo vivo: 27 messaggi, 4 presidi con natura/perimetro/cadenza attesi,
`EXECUTE` all'app su tutte le undici funzioni).

### 12.2 I pgTAP — dodici nuovi (127 asserzioni), tre ri-collocati — ✅ tutti verdi col runner come app

`magazzino/`: `test-fn-scrivi-movimento-controlli-v1` (25),
`-disponibilita-v1` (9), `-seriali-v1` (5), `-valore-v1` (10),
`test-valore-giacenza-divergenza-owner-v1` (5, `pgtap-runner: owner`),
`test-fn-posta-inventario-v1` (17), `test-fn-posta-rettifica-v1` (6),
`test-documenti-interni-guard-v1` (15), `test-porta-ledger-v1` (16),
`test-vw-disponibilita-v1` (7); `dbops/`: `test-sorgenti-orfane-v1` (6, owner),
`test-articoli-a-magazzino-prontezza-v1` (6). Ri-collocati:
`magazzino/test-movimenti-vincoli-v2` (→ owner, forma 3, asserzioni invariate),
`magazzino/test-valore-giacenza-forma-v1` (fixture via primitiva, t.10 e t.12
riscritti), `script/test-guard-emittente-senza-utente` (6 → 8: la rev C1).

**Come sono stati provati**: in un harness in transazione annullata — SQL
estratto dei 21 changeSet + seed dei soli nuovi + il file, **come owner** con
il contesto operatore (`titodb` non può `SET ROLE zeroerp_app`). Tutti verdi
tranne le **nove** asserzioni che vogliono l'app: `test-porta-ledger-v1`
**4-7** (`42501` sull'`INSERT` diretto) e **13-14** (la primitiva senza
identità si ferma su `E_SCOPE_SENZA_UTENTE`), `test-guard-emittente-senza-utente`
**2, 4, 5** (già così prima del lotto: sono le sue asserzioni da app). Sono
rosse nell'harness **per costruzione**, non per un difetto: le prova il runner.

🔴 **Il runner come app (Tid, 18-09 pomeriggio) ha trovato due rossi, e non
erano nei quindici**: `dbops/test-riferimenti-morti-v1` test 2 e
`script/test-rubinetto-primo-motivo-v1` test 5 — i due presidi **trasversali**
che ogni funzione plpgsql nuova attraversa (§7, riga nuova). Il primo è chiuso
dal `20260918-27`; il secondo dal test stesso, che ora conta le **chiamate**
(commenti tolti, nome + `(`) e pinna **19**: `fn_scrivi_movimento` e
`fn_posta_inventario` sono siti nuovi nati sull'helper, e
`fn_check_disponibilita_uscita` lo nomina solo in un commento (col predicato
vecchio erano 20). Provati in transazione ritirata: 9/9, 6/6, 7/7 —
✅ **e verdi col runner come app dopo l'apply del `-27` (Tid, 18-09
pomeriggio)**. Con questo i **quindici** file del lotto e i due trasversali
sono tutti verdi: nessuna riga in baseline.

### 12.3 La doc

Venti pagine `manual/` nuove, diciassette aggiornate, `_dominio-magazzino.md`,
la riga `magazzino` della mappa (§8, tutto ✅). `index.md`/`index.ci.md` e la
doc auto-gen delle funzioni **non** sono stati toccati a mano: li rigenera la
build.

### 12.4 Le richieste consegnate

- **BE/FE, `requires_lotto`** (§4.9): la colonna è in `vw_articoli_dettaglio`
  (colonna 56, su dbdev); mancano `ARTICOLI_*_COLUMNS`, whitelist, serializer,
  `ToggleSwitch` senza lucchetto, chiavi i18n.
- **BE, 27 codici** (§4.10): `genera_error_policies` + 27 ripieghi in
  `error_messages_fallback.py`; i due test del catalogo sono rossi finché non
  arrivano.
- **FE, 13 `reason_key`** (§4.10): `magazzino.disponibilita.blocco.*` (2) e
  `magazzino.riga.blocco.*` (11) in `it.json`/`en.json` — `check_i18n_keys.py`
  (controllo 4) le cerca nella doc auto-gen delle due check.

### 12.5 Che cosa resta a Tid — in ordine (✅ **tutto chiuso il 2026-09-22**, tranne il ramo dichiarato al punto 4)

1. ✅ **Apply su dbdev** — fatto alle 12:23 del 18-09 (letto da
   `databasechangelog`: 21 `EXECUTED`, il loop `20260205-41` e il mirror dei
   messaggi `20260614-08` `RERAN` alle 12:23:14-15; postura sul ledger
   t/f/f/f · t/t/t/f).
2. ✅ **pgTAP col runner come app**: fatto (18-09 pomeriggio) — verdi i 15 del lotto; il primo giro aveva reso rossi **due presidi trasversali** (§12.2), chiusi da `20260918-27` (applicato) e dal test 5 del rubinetto a 19: **rilanciati, verdi**. Nessuna riga in baseline. Attesi tutti verdi,
   comprese le nove asserzioni sole dell'harness (porta-ledger 4-7 e 13-14,
   guard-senza-utente 2, 4, 5). ⚠️ `test-articoli-a-magazzino-prontezza-v1`
   costruisce lo stato in transazione (`UPDATE` degli articoli): non dipende
   da come è dbdev.
3. ✅ **B-7 — fatto.** `db/baseline-codici-errore-famiglie.tsv` porta i **dieci**
   codici nuovi leggibili (`E_MAG_CHIAMATA_NON_VALIDA PARAMETRO 18`,
   `E_MAG_LOTTO_OBBLIGATORIO`/`_SERIALE_`/`_UBICAZIONE_ OBBLIGATORI* PARAMETRO 1`,
   `E_MAG_STORNO_INCOERENTE NOT_FOUND 3`, `_GEMELLA_NON_TROVATA 1`,
   `_MAGAZZINO_NON_VALIDO 1`, `_DOCUMENTO_NON_TROVATO 2`,
   `_DOCUMENTO_TRANSIZIONE_NON_AMMESSA VALORE_ATTESO 3`,
   `_DOCUMENTO_NON_ELIMINABILE 1`) e `E_CONFIG_MANCANTE` a **NOT_FOUND 52**,
   com'era previsto qui sotto; il file è dentro il commit `787ab05ba`.
   Il testo originale della consegna, per memoria:
   Con `--update` entrano in baseline i **dieci** codici nuovi che la misura
   legge (`E_MAG_CHIAMATA_NON_VALIDA` PARAMETRO 18 punti, i tre `*_OBBLIGATORI*`
   PARAMETRO, `STORNO`/`GEMELLA`/`MAGAZZINO_NON_VALIDO`/`DOCUMENTO_NON_TROVATO`
   NOT_FOUND, `DOCUMENTO_TRANSIZIONE`/`NON_ELIMINABILE` VALORE_ATTESO) e i punti
   di `E_CONFIG_MANCANTE` (NOT_FOUND, 47 → 52: stessa famiglia, non è un
   accumulo); gli altri sedici sono `IGNOTO` e restano fuori per costruzione.
   Senza l'update un secondo motivo su uno dei dieci domani conterebbe come
   «nasce generico» e non come «accumula» — stessa luce rossa, frase diversa.
4. ✅ **La prova a due sessioni del lock — FATTA il 2026-09-22** (§7). Due
   `psql` come `zeroerp_app` con contesto operatore (`auth_user` 5 e 6, tutti
   e due con scope sull'emittente `32`), sul mondo **già committato** di dbdev
   — magazzino `1109` «TEST» (`usa_ubicazioni = t`, ubicazione `413`),
   articolo `art-comp-001` (`gestito_a_magazzino`, né lotto né seriale).
   ⭐ La sorgente tipizzata ogni sessione se la costruisce **nella propria
   transazione** (un inventario `DRAFT` + una riga), quindi non serve niente
   di condiviso e **tutte e due le transazioni si ritirano**.

   | Momento | Sessione A | Sessione B (parte 4 s dopo) |
   | --- | --- | --- |
   | `t0` | entrata `INV_INIZIALE +10` a 1,50 € — **nessun lock** (segno `+1`) | — |
   | `t0 + 0,03 s` | uscita `RETT_NEG −1` ⇒ `pg_advisory_xact_lock` **preso** (1 riga in `pg_locks` per il suo backend), poi tiene 12 s | — |
   | `t0 + 4 s` | tiene | chiama la primitiva sulla **stessa coppia** e si ferma |
   | `t0 + 7 s` | `granted = t` | `granted = f` — **stessa coppia di chiavi**: `classid 3059323405` (= `hashtext('magazzino.fn_scrivi_movimento')` letto senza segno) e `objid 1764687745` (= `hashtext('1109:019e2234-…')`), cioè il perimetro `(magazzino, articolo)` di t.16 |
   | `t0 + 12 s` | `ROLLBACK`: il lock cade con la transazione | riparte e **rilegge**: `E_MAG_GIACENZA_INSUFFICIENTE` — *«Giacenza insufficiente per l'articolo art-comp-001 nel magazzino TEST: disponibili 0, richiesti 1»* |

   **Durata della chiamata di B: 8 129 ms** — cioè esattamente l'attesa, non
   un rifiuto immediato. ⭐ E il verdetto è il pezzo che conta: B rifiuta su
   **zero**, il saldo committato, non sui dieci che A vedeva nella propria
   transazione ⇒ la disponibilità si legge **dopo** che il lock è stato
   concesso, com'è scritto al passo 11 (§4.2).
   ⚠️ **Il ramo «…oppure passa sul saldo aggiornato» NON è provato**, ed è
   dichiarato: vorrebbe una prima sessione che **committa** un movimento su
   dbdev, cioè una scrittura permanente sul database di sviluppo. Resta a Tid
   decidere se pagarla; la metà che riguarda il **lock** è provata, e il
   ledger è rimasto vuoto (`movimenti` e `valore_giacenza` a zero a fine
   prova: le uniche righe di `inventari`/`inventari_righe` su dbdev sono le
   due scritte da `tid` alle 10:44 del 22-09, dall'applicazione).
5. ✅ **La CI da zero è verde, e non è la replica locale: è la CI vera.**
   Corsa **`35451924195`** (19-09 15:28, push su `Tito-dev`, commit
   `08542e6c2` che **contiene** `787ab05ba`): `Liquibase update (standard, no
   provision)` → `Liquibase admin (provision - post)` → `Liquibase CI apply` →
   `Django tests` → **`Suite pgTAP`**, tutti `success`. Nessun file di
   `magazzino` fra i rossi e **nessuna riga** di magazzino in
   `db/pgtap/baseline-rossi-ci.tsv` ⇒ la postura regge a fine corsa con
   `provision_db_roles.sql` per ultimo (era C2), e i quindici pgTAP del lotto
   passano su un database **ricostruito**. `ci-local.sh --fresh --ci-apply`
   resta non eseguito e ora è ridondante.
   ⚠️ **Fatto datato 22-09, e non riguarda questo lotto**: da
   `35659881035` (21-09 21:55) in poi le corse **non partono affatto**
   («The job was not started because recent account payments have failed»),
   quindi da quel momento la CI non è un metro disponibile. L'ultima corsa
   reale della suite — `35622075327` (21-09 15:54) — ha **una** regressione, e
   non è di magazzino: `ui/test-lista-definizione-perimetro-emittente-v1`
   (l'elenco delle liste globali), già sanata nel repo il 22-09 con
   `559dbf351` — CSV e elenco del test coincidono oggi a **nove** nomi,
   `magazzino.lotti` compreso.
6. ✅ **Commit — fatto**: `787ab05ba` (18-09 12:45), mergiato in `Tito-dev`
   con la **PR #1605** (`abec81197`, 12:46). Dentro: i 22 YAML (`-06…-27`), i
   tre file in place, i tre CSV, i 15 pgTAP, la doc, la baseline B-7 e questo
   brief.
7. ⚠️ **Il presidio di prontezza NON è più acceso.** Il 18-09 la vista diceva
   `NESSUNO_MARCATO` perché nessun articolo era marcato; al **22-09** dice
   `MARCATI | 3` — tre articoli sono stati marcati dall'uso in-app, e insieme
   a loro su dbdev ci sono ora un magazzino (`TEST`, con un'ubicazione) e un
   inventario in bozza. ⭐ È il presidio che fa il suo mestiere: era una spia
   sul **rilascio**, e si spegne quando il magazzino comincia a essere usato.
8. ✅ **BE/FE — consegnate** (§12.4), verificato il 22-09 sul repo:
   `requires_lotto` è in `catalogo_repository.py` (colonne e `SELECT`),
   `catalogo_service.py`, il serializer di `catalogo/api/views.py` e, lato FE,
   in `ArticoliView.vue` / `ArticoloDrawer.vue`; i codici `E_MAG_*` sono in
   `error_policies_generated.py` con i ripieghi in
   `error_messages_fallback.py`; le **13** `reason_key` ci sono in `it.json` e
   `en.json` (`magazzino.disponibilita.blocco.*` 2,
   `magazzino.riga.blocco.*` 11).
9. Al Lotto 3: lo scarico da DDT, lo storno come verbo, il trasferimento, la
   liberazione dei blocchi (§9).
