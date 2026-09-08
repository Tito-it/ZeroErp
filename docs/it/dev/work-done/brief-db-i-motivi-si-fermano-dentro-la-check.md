# Brief DB — i motivi si fermano dentro la check

> **Destinatario:** team DB (`dev/db-tid`). Aperto il 2026-09-08.
>
> **In una riga:** una `script.fn_check_*` sa **perché** si rifiuta, **con quale
> codice** e — a volte — **cosa scrivere nella frase**. Due di queste tre cose
> non escono da lì: non arrivano ai presidi del catalogo codici, e non arrivano
> al messaggio che l'operatore legge.
>
> **Origine.** Sono i due residui di
> [brief-db-coda-primo-motivo-in-un-posto-solo](brief-db-coda-primo-motivo-in-un-posto-solo.md)
> (§9.5).
>
> 🔴 **Riveduto il 2026-09-08 contro gli oggetti vivi, e §2.2, §3 e §5 dicevano
> il falso.** La prima stesura contava sei check con l'arità mista e prometteva
> un passo `V-1` che, come era scritto, **non avrebbe fatto entrare nessun
> codice sotto il rubinetto**. Le correzioni stanno nel corpo, ognuna col suo
> perché: un brief che cambia solo la conclusione insegna la stessa cosa
> sbagliata a chi lo rilegge.
>
> ⛔ **Nessuna misura decide niente qui.** I conteggi dicono **quanto è largo il
> perimetro**, non se il lavoro vada fatto. A decidere è la struttura — e la
> revisione qui sopra è la prova che serviva: tolte le due misure, la ragione
> del cantiere è rimasta in piedi identica.
>
> **Correlati:**
> [linee-guida-sql §12.5](../../linee-guida-sql.md) — le azioni per riga ·
> [linee-guida-sql §5](../../linee-guida-sql.md) — i canali di `fn_log_and_raise_error` ·
> [brief-db-segnaposti-messaggi-errore](brief-db-segnaposti-messaggi-errore.md) — il presidio statico dell'arità, che qui torna protagonista

---

## 1. ⭐ È una cosa sola, vista da due lati

Il pattern «la madre CHIAMA la check» ([linee-guida-sql §12.5.2](../../linee-guida-sql.md))
sposta la regola dentro la `fn_check_*`, e fa bene: rifiuto e tooltip non
«coincidono oggi», **non possono divergere**.

⚠️ Ma sposta anche **due cose che fuori servivano**:

| Cosa resta dentro la check | Chi la perde |
| --- | --- |
| il **codice**, che nella check è un letterale ma sulla riga di sollevamento non c'è | i presidi del catalogo codici, che il letterale lo cercano **accanto alla chiamata** |
| i **valori** della frase — quando la check non li emette | il messaggio: a comporlo resta il chiamante, con quello che ha in mano |

⇒ **Un cantiere solo, due passi.** Separarli sarebbe peggio: far emettere
`valori` alle check chiude il secondo lato **e** rende i loro siti estraibili
con l'helper — cioè l'`H-4` ritirato dall'altro brief.

---

## 2. Le due misure — fatti datati, 2026-09-08

### 2.1 🔴 Trentacinque codici fuori dal rubinetto degli accumulatori

`dbops.vw_codici_errore_forme_condizione` trova un punto di sollevamento così:
una riga con un **letterale `'E_...'`** e una `fn_log_and_raise_error` **entro
sei righe** (`chiamata_vicina`).

Nel pattern §12.5 il letterale sta **nella check**, dove nessuna chiamata gli sta
vicino. Misurato su `pg_proc`: **35 codici** nominati solo lì. ⚠️ La stessa cosa
contata sulla doc auto-gen dà **31** — sono due popolazioni diverse (il database
vivo ha funzioni che la doc non riporta), e nessuno dei due numero decide niente:
servono a dire che il perimetro è di quell'ordine.

| Presidio | Cosa perde |
| --- | --- |
| cancello del **terzo lato** («ha una policy?») | ✅ **niente** — e la ragione va scritta, perché non è quella che sembra: `dbops.vw_codici_errore_da_dichiarare` non passa dalla vista, ha un sensore suo ed è **volutamente larga** (§3) |
| ⭐ **rubinetto degli accumulatori** B-7 | 🔴 **tutti e 35** |
| lente `check_messaggio_vs_condizione` | 🔴 gli stessi 35 |
| 🔴 **test 4 e 5 di `test-catalogo-messaggi-errore-completo.sql`** — il presidio statico dell'arità | 🔴 **gli stessi 35, e non era stato notato**: si ferma su `CONTINUE WHEN v_code IS NULL — codice in variabile: non misurabile` |

⛔ **Il danno non è «un codice senza policy»** — quello non succede. È che
**trentacinque codici possono allargarsi a una condizione nuova senza che
nessuno se ne accorga**, ed è esattamente il modo in cui si forma un
accumulatore: *«nessuno crea un codice generico di proposito. Si prende quello
che c'è già e lo si usa anche per questo caso qui, una volta sola.»*

⚠️ **E non l'ha causato l'altro cantiere.** Anche prima quei siti sollevavano
`v_primo ->> 'codice'`, senza letterale: è una proprietà del pattern, non una
regressione.

🔴 **Correzione del 2026-09-08 — «la vista, sorgente dei tre presidi» è falso.**
La vista ne alimenta **uno**: lo snapshot B-7
(`scripts/sql/codici_errore_famiglie_snapshot.sql` → `db/baseline-codici-errore-famiglie.tsv`,
149 codici, **una** baseline e non tre). Gli altri due hanno **una copia propria**
dello stesso sensore a sei righe, scritta dentro di loro. ⇒ Insegnare la forma
nuova alla sola vista lascerebbe la lente cieca com'è: `V-1` da sola non basta,
e il piano lo dice adesso (`V-1b`).

### 2.2 🔴 L'arità — la misura era sbagliata, e il difetto vero è un altro

**Quello che questa sezione diceva:** *«sei check su tredici possono comporre una
frase con l'arità sbagliata; scatta il ripiego `W_MESSAGGIO_ARITA` e a video
escono i `%s` grezzi»*. Riletti i corpi vivi e il catalogo dei messaggi,
**quattro dei sei sono falsi positivi e nessuno dei tredici siti può produrre
quel ripiego oggi**.

**Il difetto della misura, che è istruttivo.** Contava *«i segnaposto dei codici
che la check nomina»* prendendo **tutti** i letterali `E_*` del corpo. Ma una
`fn_check_*` ne nomina **due specie**, e solo una arriva al chiamante:

| | Dove finisce | Chi compone la frase |
| --- | --- | --- |
| il codice di un **motivo** (`jsonb_build_object('codice', …)`) | nell'array, poi al chiamante | ⚠️ il chiamante — è il caso di cui parla questo brief |
| `E_PARAMETRO_INVALIDO` del **guard di parametro** in testa | da nessuna parte: la check **solleva lei**, col suo `VARIADIC` | la check stessa |

Il secondo ha **un** segnaposto. Contandolo, ogni check con un motivo a due
segnaposto risulta «1 / 2». Ricalcolato sui soli **codici-motivo**:

| Check | Arità dei codici-motivo | Prima stesura | Verificato |
| --- | --- | :---: | :---: |
| `fn_check_commessa_annullabile` | `{2}` — un motivo solo | 1/2 🔴 | ✅ uniforme |
| `fn_check_commessa_chiudibile` | `{2}` — un motivo solo | 1/2 🔴 | ✅ uniforme |
| `fn_check_ordine_confermabile` | `{2}` — un motivo solo | 1/2 🔴 | ✅ uniforme |
| `fn_check_preventivo_emettibile` | `{2}` — un motivo solo | 1/2 🔴 | ✅ uniforme |
| `fn_check_documento_escludibile_da_giro` | `{1,1,1,2}` | 1/2 🔴 | 🔴 **mista, vero** |
| `fn_check_rinuncia_reversibile` | `{0,1}` | 0/1 🔴 | 🔴 **mista, vero** |

⛔ **E il seguito non regge comunque.** `format()` alza `22023` solo con valori
**in meno**; quelli in più li ignora in silenzio. Sito per sito, i valori passati
sono sempre ≥ del massimo dei segnaposto — le quattro guard di transizione ne
passano due su un massimo di due, `fn_riapri_riconsegna_reso` uno su un massimo
di uno. ⇒ **`W_MESSAGGIO_ARITA` non può scattare in nessuno dei tredici**, e la
frase che lo prometteva descriveva un database che non esiste.

#### ⭐ Il controesempio VERO, che la misura non ha visto

C'è un difetto vivo, ed è **un sito**, di un'altra classe: non l'arità, il
**valore sbagliato**. `vendite.fn_escludi_documento_da_giro` compone la coda
così:

```sql
NULL::uuid,
p_gruppo_key,                                     -- 1º valore, SEMPRE il documento
COALESCE(v_motivi -> 0 ->> 'dettaglio', '-'));    -- 2º
```

Funziona per i motivi 2, 3 e 4, le cui frasi cominciano tutte con *«Il documento
%s…»*. **Non funziona per il motivo 1**, `E_LOTTO_NON_PRE_FISCALE`:

> `Il lotto e' oltre lo stato pre-fiscale (stato attuale: %s)` riceve
> **`p_gruppo_key`**, mentre lo stato del lotto sta nel `dettaglio` che nessuno
> legge.

⚠️ Ed è il motivo che sta **primo** nell'array, cioè quello che la madre solleva
sul percorso più comune. È l'incidente del 2026-09-01 di
`E_REGISTRO_SERIE_NON_AMMESSA` nella stessa identica forma — valori presenti,
posto sbagliato — e non lo vede nessuno: `throws_ok(…, 'P0001', NULL, …)` in
`db/pgtap/vendite/test-uscita-documento-dal-giro-v1.sql` non guarda la frase, e
il presidio statico dell'arità salta il sito (§2.1).

⭐ **La sorella lo fa giusto, ed è il modello.**
`vendite.fn_elimina_fattura_da_lotto` passa **solo** `v_motivi -> 0 ->> 'dettaglio'`:
un valore che appartiene al motivo, quindi scala con qualunque codice. È `C-1`
fatta a mano su un caso in cui bastava.

#### ⭐ La ragione, riscritta sulla struttura

Tolte le misure, resta questa — e regge su una check con un motivo solo tanto
quanto su una con quattro:

> **Il chiamante compone una frase POSIZIONALE dai propri dati, mentre il
> contratto della check ammette N codici con forme di frase indipendenti.**
> Niente lega le due cose, e il disallineamento non fa fallire niente.

⛔ Il ramo che oggi non esiste non è un motivo per non chiudere: *zero occorrenze
non significa che il caso non esiste, significa che non c'è ancora un
controesempio* — e uno, al §2.2, c'è.

---

## 3. ⭐ Perché `V-1` non poteva funzionare come era scritto

**Quello che diceva:** *«dal punto che solleva risale alla `fn_check_*` chiamata
e ai codici che quella nomina»* — formulazione ereditata dal §7.3 dell'altro
brief. Non funziona, e la ragione sta in cosa la vista misura davvero.

`vw_codici_errore_forme_condizione` **non è un elenco di codici**: per ogni punto
che solleva guarda **la riga di `IF` appena sopra** e ne ricava che *tipo* di
controllo sia — `VALORE_ATTESO` per un confronto con un letterale, `PARAMETRO`
per un `IS NULL` su un `p_…`, `NOT_FOUND`, `ENUM`, oppure `IGNOTO`, che vuol dire
**«non so leggerla»**. Serve alla domanda del rubinetto B-7: *«questo codice ha
cominciato a coprire un tipo di situazione che prima non copriva?»*.

Nel pattern §12.5 il controllo vero sta **nella check**:

```sql
-- dentro script.fn_check_commessa_annullabile
IF v_emesse > 0 THEN                                  -- ← qui c'è il PERCHÉ
    ... 'codice', 'E_COMMESSA_ANNULLA_CON_RIGHE_EMESSE' ...
```

mentre sopra il punto che **solleva**, nella madre, c'è sempre e solo questa:

```sql
-- dentro vendite.trgfn_commesse_guard_transizione
IF jsonb_array_length(v_motivi) > 0 THEN              -- ← «c'è almeno un motivo?»
    PERFORM ... v_motivi -> 0 ->> 'codice' ...
```

Quella frase è **identica in tutti e 35 i punti** e non dice niente sul perché.
Per il classificatore è `IGNOTO`, sempre.

> **L'immagine:** il doganiere classifica il pacco leggendo l'etichetta al banco.
> Qui al banco arriva un corriere la cui etichetta dice sempre *«sto
> trasportando qualcosa»*. L'etichetta vera è sul pacco, scritta in magazzino.

⇒ **Prendere i codici dal magazzino e classificarli con l'etichetta del
corriere** significa archiviarli tutti e 35 sotto `IGNOTO`. E lo snapshot che
alimenta la baseline butta via `IGNOTO`, per una ragione sua giusta
(`WHERE NOT f.solo_ignoto`, più `EXCEPT 'IGNOTO'` sull'elenco):

* un codice che sta **solo** lì risulta «tutto ignoto» ⇒ **scartato**, come oggi;
* un codice che ha già una famiglia altrove guadagna solo un `IGNOTO`, che non
  entra nel confronto ⇒ **non cambia niente** (`n_punti` la baseline non lo
  confronta).

⇒ 🔴 La vista avrebbe mostrato 35 codici in più e il rubinetto non ne avrebbe
guadagnato **nemmeno uno**. Il §5 — *«la CI si fermerà su alcuni di loro»* —
descriveva un rischio che non poteva accadere, e `V-2` non avrebbe avuto niente
da ri-basare.

### ⭐ La forma che funziona, e il precedente è già in casa

**Non si segue il corriere: si legge l'etichetta dove viene scritta.** La vista
riconosce come punto anche la riga che **nomina** il codice dentro una
`fn_check_*`, e la guardia se la prende — come sempre — dall'`IF` che la precede
**nella check**. Lì c'è materia vera: `ELSIF v_esito = 'ESCLUSO'` è
`VALORE_ATTESO`, `IF v_emesse > 0` resta `IGNOTO` **e lo dichiara**, che è il
comportamento giusto di una misura.

⭐ **E la decisione ha un precedente motivato, a due schemi di distanza.**
`dbops.vw_codici_errore_da_dichiarare` è **volutamente larga** — raccoglie ogni
letterale, non solo quelli dentro una chiamata — e il perché è scritto nel suo
commento: *«restringere perderebbe i codici che arrivano da espressione (gruppo
C: `v_motivi -> 0 ->> 'codice'`) … fra i due errori possibili si sceglie quello
che si corregge guardando i falsi positivi, non quello che non si vede»*.
È lo stesso problema, già risolto allargando il sensore.

⚠️ **Cosa NON si fa, ed è la tentazione simmetrica:** risolvere la catena di
chiamate dentro la vista. Il grafo è ambiguo per costruzione —
`trgfn_commesse_guard_transizione` sceglie fra **tre** check con un `CASE`, e una
check è letta anche da `fn_available_actions_*`, che non solleva mai. La forma
della condizione non ha bisogno di sapere chi chiama chi.

---

## 4. Il piano

| Passo | Cosa | Dove |
| --- | --- | --- |
| **V-0** | ⭐ Promuovere a oggetto `dbops` la risalita **sito → check**, che esiste già: è la vista temporanea `punti_primo_motivo` di `test-rubinetto-primo-motivo-v1.sql`, scritta una volta e **provata per mutazione**. Consumatori: `P-0` e la lente. ⛔ Non serve a `V-1` (§3) | `20_code/dbops` |
| **V-1** | ⭐ La vista impara a classificare **dove il codice è NOMINATO** — dentro la `fn_check_*`, con la guardia di lì | `20_code/dbops` |
| **V-1b** | La stessa forma nella lente `check_messaggio_vs_condizione`, che ha un sensore suo | `scripts/sql/` |
| **V-2** | Ri-base **motivata** dell'unica baseline (`db/baseline-codici-errore-famiglie.tsv`): la prima corsa dirà quali codici hanno davvero più di una famiglia | `db/`, con la ragione nel commit |
| **P-0** | ⭐ Togliere il `CONTINUE WHEN v_code IS NULL` dal test 5 di `test-catalogo-messaggi-errore-completo.sql` usando `V-0`: l'arità diventa presidiata **staticamente su tutti i siti**, presenti e futuri — invece che con sei `throws_like` a mano | `db/pgtap/script` |
| **C-0** | Riparare `fn_escludi_documento_da_giro` / motivo 1 (§2.2), e **dichiararlo** | `20_code/vendite` |
| **C-1** | Far emettere **`valori`** alle **otto** check del §4.1 — non sei | `20_code/script` |
| **C-2** | Le **cinque** funzioni corrispondenti passano a `script.fn_raise_primo_motivo_se_presente` | `20_code/vendite` |
| **P-1** | Per ogni sito toccato, un `throws_like` sulla **frase resa** — con l'avvertenza del §4.2 | `db/pgtap/vendite` |
| **P-2** | In `test-rubinetto-primo-motivo-v1.sql`: soglia del **test 4** da 13 a **7**, **e** conteggio del **test 5** da 10 a **15** | `db/pgtap/script` |

### 4.1 🔴 Il perimetro di `C-1` è otto check, e non è una scelta

Il rubinetto calcola `in_perimetro` **per funzione** e in modo **pessimista**:
`bool_or(check.prosrc ~ 'valori')` su *tutte* le `fn_check_*` nominate nel corpo.
Da lì discende tutto:

| Funzione | Check che nomina | Conseguenza |
| --- | --- | --- |
| `trgfn_commesse_guard_transizione` | **tre**, scelte da un `CASE`, **un** solo punto che solleva | dare `valori` a una sola le fa entrare tutte in perimetro ⇒ serve anche **`fn_check_commessa_pronta_fatturazione`**, o il suo ramo perde i valori |
| `trgfn_ordini_guard_transizione` | **due**, su **due** rami | `fn_check_ordine_confermabile` trascina dentro **`fn_check_ordine_annullabile`** |

⇒ Le otto: `documento_escludibile_da_giro`, `rinuncia_reversibile`,
`commessa_annullabile`, `commessa_chiudibile`, **`commessa_pronta_fatturazione`**,
`ordine_confermabile`, **`ordine_annullabile`**, `preventivo_emettibile`.

⚠️ **E `C-1` e `C-2` non si separano fra due PR.** Fra i due il rubinetto è
**rosso per costruzione**: la funzione è in perimetro e solleva ancora a mano.
L'ordine «prima `C-1`» resta non negoziabile, ma stanno nella stessa consegna.

**I conti, che tornano esatti.** Oggi il debito del test 4 sono **12 funzioni**
(13 punti). `C-2` ne toglie cinque — `fn_escludi_documento_da_giro`,
`fn_riapri_riconsegna_reso`, `trgfn_commesse_guard_transizione`,
`trgfn_ordini_guard_transizione`, `trgfn_preventivi_guard_transizione` — e ne
restano **sette**: `fn_annulla_lotto_da_draft`, `fn_cambia_stato_preventivo`,
`fn_elimina_fattura_da_lotto`, `fn_riporta_attivita_da_emettere`,
`fn_riporta_lotto_a_draft`, `trgfn_doc_guard_chiusura_sorgente`,
`trgfn_preventivi_guard_annullamento`. ⇒ soglia **7**.

⚠️ **Per chi farà le altre sei check, dopo**: `fn_check_preventivo_annullabile` è
letta da **due** funzioni (`fn_cambia_stato_preventivo` e
`trgfn_preventivi_guard_annullamento`). Entrano in perimetro insieme.

### 4.2 ⛔ Il `throws_like` di `P-1` sul sito di `C-0` si spezza in due

`P-1` dice «un `throws_like` sulla frase resa, **prima** di toccarlo». Su quattro
siti è giusto: pinna l'equivalenza prima/dopo. Su
`fn_escludi_documento_da_giro`, no — **la frase di oggi è sbagliata** (§2.2), e
un test scritto prima diventerebbe rosso quando `C-0`/`C-1` la riparano.

⇒ Si spezza, ed è la regola già pagata in
`db/pgtap/dbops/test-vw-codici-errore-valore-atteso.sql`: *«un test che diventa
rosso quando il difetto viene sanato spinge a rimettere il difetto, o a
cancellare il test»*. Una asserzione di **equivalenza** sui siti sani, e per quel
motivo una asserzione sull'**invariante** — *la frase nomina lo stato del lotto*
— che nasce rossa e rientra con la riparazione.

---

## 5. ⛔ Cosa NON si fa

* ⛔ **Non si aggiunge `p_valori` all'helper.** Svuoterebbe la terza convenzione:
  il chiamante ricomporrebbe i valori a mano, e l'helper diventerebbe un
  involucro attorno a niente ([§4.2 dell'altro brief](brief-db-coda-primo-motivo-in-un-posto-solo.md));
* ⛔ **Non si allarga il marcatore del rubinetto** per prendere anche i siti
  fuori perimetro: lì il `-> 0` è **legittimo** finché la check non emette
  `valori`, e un cancello che boccia il caso giusto viene spento;
* ⛔ **Non si riscrivono i 1200 punti a codice letterale** per uniformare la
  forma: è l'alternativa già scartata, e si fa dal lato che **guarda** (una
  vista) non da quello che **scrive**;
* ⛔ **Non si insegna alla vista a risolvere il grafo delle chiamate** (§3): è
  ambiguo per costruzione e non serve a classificare una condizione;
* ⛔ **Nessun codice errore nuovo**: le check *nominano* codici già a catalogo.
  Se per scriverne una servisse un codice nuovo, il difetto è a monte.

---

## 6. ⚠️ Il rischio del passo `V-1`, e adesso è un rischio vero

La vista alimenta la baseline B-7. Insegnarle la forma nuova fa **entrare**
codici che oggi non vede: alcuni scopriranno di avere più di una famiglia di
condizione, e la CI si fermerà su di loro.

⭐ **È il comportamento giusto, non un incidente** — ed è già successo il
2026-09-07, quando una famiglia nuova (`VALORE_ATTESO`) fermò il rubinetto su
otto codici. Lì la lezione fu:

> Una famiglia nuova produce **due** effetti che si assomigliano e vanno
> separati uno per uno: cambia il metro su chi già usava quel codice, e **rende
> visibile** ciò che prima era illeggibile. ⛔ Il primo si ri-basa, il secondo
> **no**: è una segnalazione vera arrivata in ritardo. Il discriminante è il
> **conteggio dei punti**.

⚠️ Qui vale identico, ed è tutto il `V-2`: ⛔ **la baseline non si aggiorna per
far passare la CI.** Ogni codice che entra si guarda una volta, e la ragione va
nel messaggio di commit.

🔴 **E va detto che questo paragrafo, nella prima stesura, era una promessa a
vuoto**: con `V-1` scritta com'era nessun codice sarebbe entrato e la CI non si
sarebbe fermata su niente (§3). Vale adesso perché la forma è cambiata — *un
rischio dichiarato su un meccanismo che non lo produce è peggio di nessun
rischio dichiarato, perché fa sembrare presidiato ciò che non lo è.*

---

## 7. Cosa non si tocca

* **Le teste dei siti**: quale check chiamare, su cosa. Non è questo cantiere.
* **`script.fn_log_and_raise_error`** e **`script.fn_raise_primo_motivo_se_presente`**:
  le firme non cambiano.
* **L'ordine dell'array dei motivi**: è il contratto della check, e `C-1` non lo
  tocca — aggiunge `valori`, non riordina.
* **Il guard di parametro in testa alle check**: `E_PARAMETRO_INVALIDO` resta
  dov'è e come è. ⚠️ Non è un motivo, ed è la confusione che ha prodotto la
  misura sbagliata del §2.2.
* **Nessuna migrazione si applica** senza che Tid lo dica, per quel comando.

---

## 8. Stato — 2026-09-08

### 8.1 ✅ La corsia `V` è chiusa, applicata e verificata come applicazione

> ⭐ **I changeSet `-34` e `-35` sono stati applicati da Tid** il 2026-09-08 alle
> 23:31 (`databasechangelog`). Da lì in avanti i pgTAP sono stati girati per
> davvero con `scripts/testpgtap.sh`, cioè come `zeroerp_app` **con la RLS
> attiva** — non più solo in transazione da owner.

| Passo | Consegna | Verifica |
| --- | --- | --- |
| **V-0** | `20260908-34-create-vw-punti-primo-motivo` — `dbops.vw_punti_primo_motivo` | SQL **estratto dallo YAML**, `changes` e `rollback`, in transazione: 12 punti, 0 in perimetro, 0 rami ciechi — gli stessi numeri della vista temporanea che sostituisce |
| **V-0b** | `test-rubinetto-primo-motivo-v1.sql` **interroga** la vista invece di ridefinirla | 7/7 verde. ⭐ E la canarina è diventata un **testimone costruito**: ristretto il marcatore nella vista a `-> 0 ->> 'codice'`, il test 7 va **rosso** — con la formulazione vecchia restava verde, perché sorvegliava una copia del marcatore e non la sede |
| **V-1** | `20260908-35-update-vw-codici-errore-forme-condizione-motivo-nominato` | `changes` + `rollback` in transazione: 455 → **486** codici, 150 → **155** classificati; il rollback riporta a 455/150 esatti |
| **V-1 presidio** | `db/pgtap/dbops/test-vw-codici-errore-motivo-nominato.sql` (plan 6) | 6/6 verde. ⭐ **Provato per mutazione**: senza `V-1` cinque test su sei diventano rossi, e il 4 («il marcatore non è troppo largo») resta verde — che è il verso giusto |
| **V-1b** | La lente `check_messaggio_vs_condizione.sql` allargata allo stesso modo | 1204 → **1267** punti, 463 → **498** codici distinti: esattamente i 35 |
| **P-0** | Tolto il ramo cieco allo scanner dell'arità + **ramo B** di `_arita` che legge `V-0` | 6/6 verde. ⭐ **Provato per mutazione**: dato un segnaposto in più a `E_LOTTO_DOC_NON_IN_ERRORE`, il test 5 va **rosso** su un sito che prima non vedeva affatto |

⭐ **La misura dei 35 è confermata esatta** contro `pg_proc`: **50** codici-motivo, di cui **35** invisibili alla vista vecchia.

⚠️ **Quattro codici-motivo restano invisibili anche dopo `V-1`**, e non è un difetto
di questa consegna: cadono sulla regola **preesistente** «al massimo venticinque
righe fra la guardia e il punto» (distanze misurate: 51, 32, 53, 37 in
`fn_check_attivita_riportabile_da_emettere` e `fn_check_ba_cambio_emittente`).
È un debito **dichiarato** dal test 6 del presidio, a soglia che può solo calare.

⚠️ **`P-0` nasce verde, e va saputo**: nessuno dei diciannove punti a codice non
letterale passa oggi meno valori dei segnaposto. Prova che il cancello
**aggancia**, non che ci fosse un guasto — il guasto vivo è un altro ed è `C-0`.

### 8.2 ✅ `V-2` — deciso: si stringe la regola, la baseline non si tocca

Applicata `V-1`, i candidati passavano da 9 a 10 ed entrava **un solo codice**:
`E_DDT_CAUSALE_OBBLIGATORIA`, che acquistava `PARAMETRO` accanto a
`VALORE_ATTESO` perché la sua guardia è `IF p_ddt.causale_trasporto_id IS NULL`.

⛔ **Non si è ri-basato**, ed è la decisione di Tid del 2026-09-09. `p_ddt` è il
**documento** e `causale_trasporto_id` un suo **campo**: la condizione è «manca
la causale», un dato che una persona corregge. `PARAMETRO` significa l'opposto —
«chi ha chiamato è rotto», l'asse `TECNICO`/500 su cui non c'è nessun campo da
accendere. Il classificatore confondeva le due cose **proprio sull'asse per cui
esiste**, e ri-basare avrebbe scritto quel dato falso nel registro di un
cancello.

| Consegna | Verifica |
| --- | --- |
| `20260909-01-update-vw-codici-errore-forme-condizione-parametro-non-campo` | `changes` + `rollback` in transazione: il codice torna a `{IGNOTO, VALORE_ATTESO}`, i candidati tornano **9**, il rollback ripristina `{PARAMETRO, VALORE_ATTESO}` |
| Test **7-8** del presidio della vista | ⭐ Provati per mutazione: senza il restringimento il **7 resta verde** (un `p_x IS NULL` è ancora `PARAMETRO`) e l'**8 diventa rosso**. Vanno letti insieme: il 7 è il verso che impedisce di svuotare la regola |

⚠️ **Il perimetro è stato misurato prima**: in tutto il database c'è **una sola**
riga di guardia con un `p_qualcosa.campo` letto come parametro. Non è un criterio
cambiato al buio.

### 8.3 ✅ La corsia `C` è applicata — e ha trovato un secondo difetto vivo

🔴 **Il perimetro è cresciuto due volte, e non per scelta.** Le otto check
previste sono diventate **nove**, le cinque madri **sei**:

* `fn_check_ordine_annullabile` **compone** i motivi di
  `fn_check_sorgente_chiudibile` (`v_motivi := v_motivi || script.fn_check_…`):
  quei motivi arrivano già fatti, quindi senza `valori` metà dei motivi di quella
  funzione ne resterebbe priva ⇒ dentro anche `fn_check_sorgente_chiudibile`;
* e la sua altra madre, `trgfn_doc_guard_chiusura_sorgente`, entra allora nel
  perimetro pessimista del rubinetto ⇒ dentro anche lei.

⇒ **Il debito del rubinetto scende da 12 funzioni a 6**, non a 7.

#### 🔴 Il secondo difetto vivo, che solo la composizione fa vedere

`E_SORGENTE_CON_RIGHE_EMESSE` — *«Il documento ha **%s** righe di commessa già
emesse»* — ha **due** strade:

| Chiamante | Cosa passava | Esito |
| --- | --- | --- |
| `trgfn_doc_guard_chiusura_sorgente` | `dettaglio`, cioè il conteggio | ✅ corretto |
| `trgfn_ordini_guard_transizione`, via `fn_check_ordine_annullabile` | `NEW.numero` per primo, perché l'**altro** codice di quel ramo comincia con «Ordine %s» | 🔴 *«Il documento ha ORD-000123 righe di commessa già emesse»* |

⚠️ Arità giusta, nessun `W_`, nessun test rosso. È il gemello del difetto del
§2.2, e **nessuna delle due misure del brief lo aveva visto**: si vede solo
guardando chi *compone* i motivi di chi.

#### Cosa è stato scritto

| Passo | Consegna |
| --- | --- |
| **C-1** | `20260909-02 … -10` — le **nove** check emettono `valori`. Sei leggono la chiave visibile del documento; in tre casi è **una colonna in più** su una `SELECT` che c'era già |
| **C-0** | Non è un changeSet a sé: entrambi i difetti si chiudono **per costruzione** con `C-1`+`C-2`, e sono dichiarati nelle intestazioni di `-02`, `-04`, `-11` e `-14` |
| **C-2** | `20260909-11 … -16` — le **sei** madri passano a `script.fn_raise_primo_motivo_se_presente` |
| **P-1** | Due `throws_like` sulla **frase resa**, messi dove le fixture già vivono: `test-ritiro-commessa-attivita-da-sorgente-v1.sql` (il conteggio, non l'identificativo) e `test-uscita-documento-dal-giro-v1.sql` (lo stato del lotto, non il gruppo) |
| **P-2** | Rubinetto: soglia del test 4 **13 → 6**, conteggio del test 5 **10 → 16** |
| **P-0-bis** | ⭐ **Ramo C** dello scanner dell'arità + **test 7** a uguaglianza esatta (sotto) |

#### ⭐ Il cancello che prima non era possibile

⛔ **`C-2` avrebbe ridotto la copertura di un presidio**, ed è la cosa da non
lasciar succedere: i sei siti smettono di chiamare `fn_log_and_raise_error`,
quindi escono dallo scanner dell'arità (rami A e B) — e l'arità va a vivere
dentro la check, dove non guardava nessuno. Una bonifica che spegne un cancello è
«verde per sottrazione», la stessa classe di difetto per cui il cantiere esiste.

⇒ **Ramo C**: si misura `'valori', jsonb_build_array(…)` accanto al `'codice'`
del motivo. E lì il confronto diventa **più stretto** di quanto sia mai stato:
codice e valori stanno nello stesso oggetto, quindi si può pretendere
l'**uguaglianza** invece del «almeno quanti ne servono al peggiore».

⭐ **È l'unico cancello che prende i valori IN PIÙ** — `format()` li ignora in
silenzio, quindi l'arità resta «giusta» e la frase esce sbagliata. Sono
esattamente i due difetti vivi di questo cantiere: **nessuno dei due avrebbe
fatto scattare il test 5**.

⚠️ E va detto cosa **non** prova: che i valori siano quelli giusti e nell'ordine
giusto. Quello lo vede solo `P-1`, leggendo la frase resa.

#### Misure del 2026-09-09, tutte in transazione

| | Prima | Dopo |
| --- | ---: | ---: |
| funzioni che chiamano l'helper | 10 | **16** |
| punti con la coda a mano | 12 | **6** |
| …di cui in perimetro (test 2 del rubinetto) | 0 | **0** |
| motivi con `valori` misurati dal ramo C | — | **29**, con **0** disallineamenti |
| motivi ancora senza `valori` (debito) | — | **34** |

⚠️ **Due trappole trovate scrivendo i presidi**, e stanno nei commenti perché
sono ripetibili: un filtro `funzione LIKE '%fn_check_%'` sul test 7 pescava anche
i punti a **codice letterale** dentro una check (il guard di parametro), e un
`jsonb_typeof(x) <> 'array'` **non guarda niente** quando la chiave è assente —
`NULL <> 'array'` vale `NULL`, non vero, e il cancello cadeva dritto nel
`format()` che voleva evitare, abortendo il file.

### 8.4 Come è stato verificato

**Prima del migrate**: l'SQL **estratto dagli YAML** — `changes` *e* `rollback` —
eseguito su `dbdev` dentro `BEGIN … ROLLBACK`, coi pgTAP inseriti nella stessa
transazione. ⭐ La ricostruzione del corpo *senza* il marcatore nuovo è stata
verificata **equivalente alla vista viva** (`EXCEPT` nei due versi: 0 e 0) prima
di misurare qualunque delta — senza, il diff avrebbe misurato anche i propri
errori di trascrizione, e la prima stesura ne aveva uno.

**Dopo il migrate di Tid** (corsia `V`): `scripts/testpgtap.sh` sui tre file
(tutti **PASS** come `zeroerp_app`), `scripts/pgtap-baseline.sh dbops` → **0
rossi su 32**, `scripts/pgtap-baseline.sh script` → 1 rosso su 69, **già noto in
baseline**. Nessuna regressione.

**Corsie `V-2` e `C` — applicate da Tid il 2026-09-09** (`20260909-01 … -16`,
sedici changeSet). Prima del migrate erano state verificate applicando l'SQL
**estratto dagli YAML** — `changes` *e* `rollback` — in `BEGIN … ROLLBACK`, e
girando **nove** file pgTAP uno per uno: 8/8, 7/7, 7/7, 11/11, 18/18, 17/17, 8/8,
12/12, 15/15. Zero rossi, zero errori. In più `plpgsql_check` su tutte e quindici
le funzioni (i trigger con la loro tabella): **nessun errore**, e gli stessi 36
warning `STABLE/VOLATILE` che avevano già le funzioni vive.

**Dopo il migrate**, verificato da Tid: pgTAP e baseline rilanciate, **nessuna
regressione**. E il rubinetto B-7 è **verde senza che la baseline sia stata
toccata** — che era il punto di `(1b)`: 149 codici presidiati, zero accumuli
nuovi.

⭐ **Ogni cancello nuovo è stato visto diventare ROSSO**, non solo verde: il test
7 dei messaggi su un segnaposto tolto, i test 7-8 della vista senza il
restringimento, le due asserzioni `P-1` senza `C-1`, la canarina del rubinetto
col marcatore ristretto. *Un cancello che non si è visto rosso non è un cancello.*

---

Il brief è stato **riveduto contro gli oggetti vivi**
(doc auto-gen delle quattordici `fn_check_*` della forma B e delle loro madri,
`config.messaggi_errore`, i quattro presidi, la CI) e la forma di `V-1` è stata
decisa da Tid nella stessa conversazione: **si classifica dove il codice è
nominato**.

⚠️ Le tre cose da non riscoprire, se questo file si rilegge fra un mese:

1. `E_PARAMETRO_INVALIDO` dentro una check **non è un motivo** — chi lo conta
   ottiene sei check con l'arità mista invece di due;
2. la vista misura **la forma della guardia**, non l'elenco dei codici: il punto
   che solleva, nel pattern §12.5, non ne ha una che dica qualcosa;
3. il presidio dell'arità **esiste già ed è statico** — gli manca una riga, non
   sei `throws_like`.

---

## 9. Cosa resta aperto — 2026-09-09

Il piano del §4 è **finito**: `V-0`, `V-1`, `V-1b`, `V-2`, `P-0`, `C-0`, `C-1`,
`C-2`, `P-1`, `P-2` sono tutti applicati o dichiarati. Restano quattro cose, e
sono **debiti dichiarati e presidiati**, non residui di analisi.

| | Cosa | Dove è presidiato | Perché non si chiude qui |
| --- | --- | --- | --- |
| **R-1** | **Sei madri** sollevano ancora il primo motivo a mano, perché le loro check non emettono `valori`: `fn_annulla_lotto_da_draft`, `fn_cambia_stato_preventivo`, `fn_elimina_fattura_da_lotto`, `fn_riporta_attivita_da_emettere`, `fn_riporta_lotto_a_draft`, `trgfn_preventivi_guard_annullamento` | soglia **6** del test 4 del rubinetto, che può solo calare | ⛔ Lì il `-> 0` è **legittimo**: pretendere zero sarebbe un cancello che boccia il caso giusto. Si chiude una check alla volta, come si è fatto per queste nove |
| **R-2** | **34 motivi** non emettono `valori` e restano fuori dal ramo C (contro 29 misurati) | il numero da guardare è che il primo **cali**; nessuna soglia | è lo stesso perimetro di R-1, visto per motivo invece che per sito |
| **R-3** | **Quattro codici-motivo** non arrivano al classificatore: cadono sulla regola **preesistente** «al massimo 25 righe fra la guardia e il punto» (distanze 51, 32, 53, 37 in `fn_check_attivita_riportabile_da_emettere` e `fn_check_ba_cambio_emittente`) | test 6 di `test-vw-codici-errore-motivo-nominato.sql`, soglia 4 | non è un difetto di questo cantiere: vale identica sui punti a codice letterale. Si chiude avvicinando la guardia al motivo, o allargando la finestra — e la seconda è una decisione sul classificatore |
| **R-4** | ✅ **CHIUSO il 2026-09-09** — `P-1` copre tutti e sei i siti | le sei asserzioni sulla frase resa, nei file dove le fixture già vivono | — |

⚠️ **E una cosa che NON è un debito, ma va saputa**: con `C-1` una `fn_check_*`
legge la **chiave visibile** del documento per comporre la frase. Dentro un
trigger `BEFORE` quella lettura vede la riga **pre-modifica**. Sulle transizioni
di stato coincide — una transizione non rinomina un documento — ed è anzi il
valore che l'operatore ha davanti; ma se un giorno un guard `BEFORE` cambiasse
`codice`/`numero` nella stessa istruzione, la frase nominerebbe il valore
vecchio. Sta scritto nei commenti delle sei check che lo fanno.

### 9.1 ✅ R-4 chiuso — le sei frasi rese

| File | Cosa asserisce |
| --- | --- |
| `test-uscita-documento-dal-giro-v1.sql` (18) | la frase nomina lo **stato del lotto**, non il gruppo del documento |
| `test-ritiro-commessa-attivita-da-sorgente-v1.sql` (2-bis) | la frase nomina il **conteggio**, non l'identificativo del documento |
| `test-guard-uscita-commessa-v1.sql` (12-bis) | prima il **codice** della commessa, poi il conteggio |
| `test-ordini-guard-conferma-iva.sql` | prima il **numero** dell'ordine, poi la riga |
| `test-preventivi-guard-emissione-iva.sql` | prima il **numero** del preventivo, poi la descrizione |
| `test-rinuncia-gate-accredito-v1.sql` (3-bis, 3-ter) | la riga di reso · e il motivo a **zero segnaposto** rende il testo intero |

⭐ **Le quattro nuove si confrontano con la frase composta dai valori letti dalla
TABELLA**, non con un pezzo di stringa: se una check emettesse i valori
invertiti, le due frasi divergerebbero. Un `matches` su un frammento non lo
vedrebbe — ed è precisamente il difetto del 2026-09-01, dove arità e segnaposto
erano giusti.

✅ **Provate per mutazione**: rimesso in transazione il corpo pre-`C-1` di
ciascuna check, in ogni file diventa rossa **solo** l'asserzione nuova.

⚠️ E tutte usano lo stesso `CASE` difensivo, per due ragioni che sono costate
una correzione a testa: senza, una check che smettesse di emettere `valori`
farebbe alzare `22023` a `format()` **abortendo il file** e seppellendo le altre
asserzioni; e scritto con un `<>` nudo il guard non guarderebbe niente, perché
`jsonb_typeof(NULL) <> 'array'` vale `NULL`, non vero.

### 9.2 ✅ Chiuso il 2026-09-09

Il piano del §4 è **finito e applicato**. Ciò che resta — R-1, R-2, R-3 — non è
lavoro sospeso ma **debito dichiarato con la sua soglia**, nella forma che il
progetto usa per i registri che devono calare.

### 9.3 ⛔ Un difetto di questo cantiere: il PERCORSO di un brief negli YAML

Diciotto changeSet e due pgTAP citavano il brief come
`docs/it/dev/work-in-progress/…`. **La regola c'era già** — negli YAML si scrive
il **nome** del documento, mai il percorso — ed è stata infranta lo stesso.

⭐ **E il costo non è lo YAML.** Un percorso in un commento `#` si corregge
editando il file, e i commenti non entrano nemmeno nel checksum Liquibase. Ma lo
stesso testo dentro un `COMMENT ON` vive in `pg_description`, **riappare nella
doc auto-gen** e lì non si edita: bisogna ri-emettere il commento con un
changeSet nuovo (`20260909-17`). ⛔ E il `-34` non si tocca: è applicato, e
cambiarne l'SQL invaliderebbe il checksum.

⇒ Quando questo brief si è spostato in `work-done/`, i riferimenti da correggere
erano **ventuno**: diciotto commenti YAML, due pgTAP, un link nel brief padre —
più il commento nel database. Il nome nudo li avrebbe resi tutti inutili.

⚠️ **Perché è successo qui**: i changeSet sono stati generati da uno script, e il
percorso era scritto **una volta** nel modello. Un errore in un template si
moltiplica per il numero di file, e non lo si vede rileggendone uno.
