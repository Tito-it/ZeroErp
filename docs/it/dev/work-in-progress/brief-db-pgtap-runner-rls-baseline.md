# Brief DB — La suite pgTAP non è confrontabile con la sua baseline (utente ≠ utente)

> **Tipo**: brief operativo per il **team DB** · **Target**: `dev/db-tid` ·
> **Data**: 2026-07-29 · **Owner**: Tid · **Stato**: 🟡 **IN CORSO** —
> il sintomo è rientrato per altra via (strada **(a)**), la decisione di passare
> a **(b)** è presa il 2026-08-05 e il piano è al **§8**.
> **Da leggere per primo: §23 → §24** — bilancio, divario misurato e priorità.
> I §11 → §22 sono la storia di come ci si è arrivati.
> In sintesi: la domanda aperta del §10.3 è sciolta (§11); la riga di contesto è
> in **426 file su 426** (§12, §18); il residuo sotto l'utente applicativo era
> **65 file, di cui 38 con una causa sola** (§13), quella causa è stata corretta
> (§15) e **oggi il divario è di 36 file** (§23.2), **23 dopo il marcatore**
> (§24). Tre difetti di prodotto trovati e chiusi: §13.3, §15.1, §18.2.
> La suite è ora **transazionale al completo**, 426 file su 426 (§16, §17, §18),
> le corse con utenti diversi non si contaminano più, e **tutti i file forzano i
> vincoli differiti** tranne **14** che portano dentro la ragione, più **3** in
> cui il vincolo differito È il soggetto del test (§19 → §22).
> ⚠️ Tre avvertenze prima di citare una cifra o di toccare un test: il **§14**
> corregge il metro dei §8.2, §9.2, §12.2 e della prima stesura del §13.1; il
> **§15.3** spiega perché due corse consecutive si sporcavano il database; il
> **§18.3** raccoglie le **tre trappole** della transazionalizzazione — la prima
> delle quali rende un test verde facendogli smettere di verificare.
> 🔴 **Il brief NON è chiuso**: il default del runner è ancora `owner`. Ma il
> **§24** ha chiuso la priorità 1 — il marcatore `-- pgtap-runner: owner` su 15
> file, `PGTAP_RUNNER` in `testpgtap.sh`, e una baseline che ora **registra con
> che utente è stata presa e rifiuta i confronti disomogenei** (il difetto del §1
> chiuso alla radice). Divario **da 36 a 23 file**.
> 👉 **Punto della situazione: §25** · **famiglia C CHIUSA: §26** · **cantiere `LIMIT 1`: §27** — ALTO su tabelle vere da 66 a 31 · **✅ il file intermittente è sciolto: §28** — 26/26, e non era `LIMIT 1`. Bilancio storico al §23 ·
> **Priorità**: 🔴 **ALTA** — non per un difetto di prodotto, ma perché
> **`scripts/pgtap-baseline.sh` oggi non può fare il suo mestiere**: distinguere
> un rosso nuovo da uno noto. Finché non è risolto, ogni «zero regressioni»
> dichiarato dalla suite vale poco.
>
> **Origine**: verifica del 2026-07-29 sul residuo **P6** del
> [brief-db-emissione-fattura-per-documento-sorgente](../work-done/brief-db-emissione-fattura-per-documento-sorgente.md).
> Controllando se i 9 rossi `E_SORG_FORMATO` fossero rientrati è emerso che il
> conto non torna: **105 rossi su 155 in `vendite`, di cui solo 38 in baseline**.
>
> **Contesto**: non siamo in produzione
> ([[project_no_produzione_solo_sviluppo]]).
>
> **Assorbe**: il residuo **P6** del brief sopra, che come voce a sé non ha più
> senso — va ricontato dopo aver sistemato quanto segue.

---

## 1. Il sintomo

```
$ scripts/pgtap-baseline.sh vendite
Rossi ora: 105 su 155   |   noti in baseline (perimetro): 38
❌ REGRESSIONI — rossi NUOVI, non erano in baseline:  (~60 file)
exit 1
```

La baseline è stata aggiornata il **2026-07-28 alle 23:42** (commit del brief di
ritiro). Se fosse stata registrata con lo stesso runner, i conti tornerebbero.
Non tornano.

## 2. La causa, verificata

**Il runner e la baseline non girano come lo stesso utente PostgreSQL.**

`scripts/testpgtap.sh` legge `backend/.env` e mappa `DB_USER` → `PGUSER`: si
connette come **`zeroerp_app`**. Ma:

| Ruolo | `BYPASSRLS` | È owner di `vendite` | Vede le tabelle RLS |
|---|---|---|---|
| `titodb` | ❌ no | ✅ **sì** | ✅ — perché `relforcerowsecurity` è `false`, e l'owner salta la RLS |
| `zeroerp_app` | ❌ no | ❌ no | ❌ **no**, senza le GUC operatore |
| `zeroerp_batch_fatturazione` | ✅ **sì** | ❌ no | ✅ |

Quindi lo stesso file `.sql` **passa o fallisce a seconda di chi lo lancia**, e
non c'è nulla nel test che lo dichiari.

### 2.1 Le due forme in cui si manifesta

Campionati sei test falliti, la causa è una sola in due vesti:

| Test | Errore |
|---|---|
| `test-fatture-righe-importo-e-kit-v1` | `la nuova riga viola la regola di sicurezza per riga per la tabella "fatture"` |
| `test-commesse-schema-v1` | idem su `"commesse"` |
| `test-ddt-read-side-v1` | idem su `"ordini"` |
| `test-emissione-mirata-gruppi-fatturabili-v1` | idem su `"preventivi"` |
| `test-annulla-commessa-attivita-v1` | `Parametro non valido: p_billing_account_id obbligatorio e > 0` |
| `test-fn-batch-upsert-commessa-attivita-v1` | idem |

- **Scrittura bloccata**: la policy `rls_fatture_ef_whitelist` (e sorelle) è
  `cmd=ALL` con un `WITH CHECK` che pretende
  `app.ruolo_applicativo='OPERATORE'` + `app.current_user_id`. Il fixture non le
  imposta → l'`INSERT` viene respinto.
- **Lettura vuota**: `anagrafiche.billing_account` è **anch'essa RLS** e senza
  GUC restituisce **0 righe** (verificato). Il fixture cerca un billing account,
  non lo trova, passa `NULL` alla funzione, e il guard di dominio solleva. Stesso
  difetto, sintomo diverso — e più insidioso, perché l'errore parla di un
  parametro e non di sicurezza.

Controprova coerente: i test che **passano** sono quelli che o impostano la GUC
(`test-porta-oneri-giro-completo-v1`, 1 occorrenza di `set_config`) o non
scrivono su tabelle RLS (`test-articolo-regole-fatturazione`). Il test nuovo che
fallisce ha **zero** `set_config`.

## 3. Perché è cresciuto adesso

Le tabelle con RLS in `vendite` + `anagrafiche` sono ormai **quattordici**:

```
anagrafiche.billing_account   vendite.fatture              vendite.offerte_commerciali
vendite.commesse              vendite.fatture_riepiloghi_iva   vendite.ordini
vendite.commesse_attivita     vendite.fatture_righe        vendite.preventivi
vendite.contratti             vendite.fatture_scadenze     vendite.resi
vendite.ddt                   vendite.fatturazione_lotti
```

⚠️ **`fatture_righe` e `fatture_riepiloghi_iva` sono state protette da poco** —
è l'applicazione di
[brief-db-rls-satelliti-fattura-portale](../work-done/brief-db-rls-satelliti-fattura-portale.md),
che risulta ancora `⬜ DA FARE` nella sua intestazione: **da allineare**. Ogni
tabella che entra nella RLS aggiunge fixture che smettono di funzionare, quindi
il fenomeno è destinato a peggiorare a ogni ondata.

> ✅ **Nessun impatto sui percorsi applicativi**, verificato: il worker di
> stampa gira dentro `system_process_context` come `zeroerp_batch_fatturazione`,
> che ha `BYPASSRLS`; il percorso web porta le GUC dal middleware; i due smoke
> di fatturazione (`smoke-fatturazione-aggregazione-righe`,
> `smoke-fatturazione-render-stampa`) sono **verdi** perché impostano il
> contesto operatore. Il problema è **solo** della suite pgTAP.

## 4. Cosa si chiede di decidere

Non propongo un'implementazione — è terreno del team DB — ma la scelta è fra
tre strade, e conviene farla esplicita perché condiziona ogni test futuro.

| | Strada | Conseguenze |
|---|---|---|
| **(a)** | Il runner si connette come **owner** (`titodb`) | Un cambio a `scripts/testpgtap.sh`. Ma i test **non esercitano mai la RLS**: continuerebbero a non accorgersi di una policy sbagliata, che è già un limite noto (cfr. `brief-db-emissione-fattura-per-documento-sorgente` §RLS) |
| **(b)** | Ogni fixture imposta le **GUC operatore** in testa | I test girano come l'applicazione e la RLS viene esercitata davvero. Costo: toccare ~60 file, o meglio estrarre un **helper di fixture** condiviso (`SELECT script.pgtap_set_contesto_operatore()`) e chiamarlo da ognuno |
| **(c)** | Il runner usa un ruolo **`BYPASSRLS`** dedicato ai test | Come (a) ma senza dipendere dall'ownership. Stesso limite: RLS non esercitata |

**Raccomandazione: (b)**, con l'helper condiviso. È l'unica che rende i test
rappresentativi di come gira l'applicazione, ed è coerente con la lezione di
questi giorni — un test che passa in una condizione che in esercizio non esiste
mai è verde senza dire nulla. (a) e (c) risolvono il conteggio nascondendo il
problema.

Se si sceglie (b), i test che devono verificare **il canale batch** useranno
esplicitamente il contesto di sistema: la differenza fra i due diventa parte di
ciò che si collauda, invece di un incidente.

## 5. Dopo la scelta

1. Applicare la strada scelta ai file del perimetro `vendite` (~60).
2. **Ricontare** e rigenerare la baseline: `scripts/pgtap-baseline.sh --update vendite`.
3. Solo allora ha senso riprendere **P6** (i 9 rossi `E_SORG_FORMATO`): oggi non
   sono nemmeno distinguibili dal rumore — la baseline non riporta più quella
   causa, ha solo `ERRORE_FIXTURE` (75) e `ASSERZIONE` (33).
4. Togliere dalla baseline i **5 rientrati** che il runner già segnala:
   `test-bozza-non-operativa-e-preview-contratto-v1`, `test-colonne-lineage-liste-v1`,
   `test-contratti-modalita-pricing-v1`, `test-contratti-schema-step21-v1`,
   `test-guard-esclusione-figlio-bundle-v1`.
5. Allineare l'intestazione di
   [brief-db-rls-satelliti-fattura-portale](../work-done/brief-db-rls-satelliti-fattura-portale.md),
   che si dichiara `DA FARE` mentre le due policy risultano applicate.

## 6. Fuori perimetro

- **`FORCE ROW LEVEL SECURITY`**: resta l'ondata coordinata futura. Nota però
  che il giorno in cui verrà attivata, la strada **(a)** smetterà di funzionare —
  l'owner non salterebbe più la RLS. È un argomento in più per **(b)**.
- **Il rosso di `test-contratti-overlap-draft-escluso-v1`**: fallisce per
  **asserzione**, non per fixture. È l'unico del campione con una causa diversa,
  e va guardato a parte.

- **`test-fn-init-componenti-jsonb-override-v1` — rosso intermittente, corretto
  il 2026-08-05.** Trovato lavorando a questo brief, ma **non è materia sua**: non
  c'entrano né il runner né la RLS. Il test sceglieva il proprio soggetto a caso.
  `fn_preventivo_riga_componenti_init` ha una guardia di idempotenza in testa
  («se la riga ha già componenti, `RETURN 0`»), quindi su quelle righe non arriva
  mai al guard che il test vuole provare: dei **44 candidati che accettava, 33
  uscivano subito** e solo 11 erano utilizzabili — tre probabilità su quattro di
  fallire. In più aveva **due `LIMIT 1` indipendenti e senza `ORDER BY`**, uno
  nell'`EXISTS` dello skip e uno nella `SELECT` del soggetto, che potevano pescare
  righe diverse: cambiando `enable_hashjoin` la stessa query restituiva la riga
  163 oppure la 128. Corretto scegliendo il soggetto una volta sola, con la
  condizione di idempotenza inclusa e un `ORDER BY` ripetibile; verificato con
  quattro piani diversi.

  > ⚠️ **Perché è comunque rilevante per questo brief.** Un rosso intermittente
  > è veleno per una baseline: se lo si registra quando è rosso, il giorno in cui
  > torna verde per fortuna la riga resta lì e copre un rosso vero; se lo si
  > registra quando è verde, il rosso successivo sembra una regressione. **Prima
  > di rigenerare la baseline (§9.3) conviene contare quanti altri test scelgono
  > il soggetto con `LIMIT 1` senza `ORDER BY`** — è un `grep` e una lettura, non
  > un cantiere — altrimenti si fotografa un pezzo di fortuna e lo si chiama
  > «noto».

---

## 7. Registro

| Data | Cosa | Esito |
|---|---|---|
| 2026-07-29 | Verifica del residuo P6 | Trovato lo scarto baseline/runner. Causa isolata su un campione di 6 test: RLS in scrittura (4) e `billing_account` invisibile in lettura (2). Confermato che i percorsi applicativi **non** sono coinvolti |


---

## 8. Il passaggio alla strada (b) — misura e piano (2026-08-05)

### 8.1 Dove siamo davvero

Il sintomo del §1 **è rientrato**, ma non con la strada raccomandata. Oggi
`scripts/testpgtap.sh` legge `db/internal.env` per primo, quindi runner e
baseline girano entrambi come `titodb`: è la strada **(a)**, l'owner. Il comando
del §1 risponde `36 su 175, noti in baseline 36 → nessuna regressione`, e la
baseline ha esattamente 36 voci. Lo strumento funziona di nuovo.

⚠️ Ma il limite che il §4 attribuiva ad (a) è quello che abbiamo: **nessuno dei
175 test tocca mai la RLS**. Una policy sbagliata passerebbe inosservata. E il
§6 lo dice già: il giorno in cui si attiva `FORCE ROW LEVEL SECURITY`, (a) smette
di funzionare tutta insieme, perché l'owner non salterà più la RLS.

### 8.2 Quanto costa (b), misurato

> ⚠️ **Valori assoluti sovrastimati: vedi §14** (misura senza `ON_ERROR_STOP`).
> I confronti fra le righe restano validi — stesso metro su tutte.

Non stimato: la suite `vendite` è stata eseguita **tre volte**, negli stessi
minuti, cambiando solo chi la lancia.

| | ok | ko | file rossi o muti |
| --- | --- | --- | --- |
| `titodb` (owner, com'è oggi) | 1643 | 30 | 24 su 175 |
| `zeroerp_app` **senza** contesto | 881 | 136 | **90** |
| `zeroerp_app` **+ 2 GUC** | **1678** | **26** | **16** |

Girare come l'applicazione, col contesto impostato, dà **più verdi e meno rossi
di adesso**. Non è un compromesso da pagare: è un miglioramento.

Tre cose che la misura ha corretto rispetto a quanto si credeva:

* **Bastano due GUC, non tre.** `app.ruolo_applicativo = 'OPERATORE'` e
  `app.current_user_id`. La terza che le policy citano
  (`app.current_identita_id`) non è servita in nessuno dei 175 file.
* **Non c'è lavoro di permessi.** `zeroerp_app` ha già i `GRANT`: legge
  `vendite.preventivi`, scrive `vendite.commesse`, usa lo schema `script`. I
  fallimenti non erano «permesso negato» ma RLS che restituiva zero righe, con le
  fixture che si rompevano a valle (tipico: «`p_billing_account_id` obbligatorio
  e > 0», perché il billing account era invisibile).
* **Il perimetro non è ~60 file ma 112** — tanti ne cambiano comportamento. Il
  numero del §4 veniva dal confronto rotto.

**Il lavoro residuo a mano è UN file**: `test-promo-articoli-guard-data-driven-v1.sql`,
l'unico che con (b) starebbe peggio di oggi (18 ok come owner, zero asserzioni
come operatore).

### 8.3 Il piano

1. **Helper** `script.pgtap_set_contesto_operatore()`: imposta le due GUC e
   **sceglie da sé un operatore valido** invece di inchiodare un id — un id
   scritto a mano è un test che si rompe il giorno in cui quel dato cambia.
2. **Una riga in testa ai file** del perimetro `vendite`. Non solo ai 112 che
   cambiano: a tutti. È una riga, ed è la prima cosa che chi legge il test deve
   sapere — *questo test gira come gira l'applicazione*. Decidere caso per caso
   costerebbe più della riga e lascerebbe un perimetro da spiegare.
3. **Runner**: `scripts/testpgtap.sh` passa all'utente applicativo.
4. **Ribaselinatura**: `scripts/pgtap-baseline.sh --update vendite`. La baseline
   attuale (36 voci) descrive il mondo dell'owner e non varrebbe più.
5. **Il file singolo**, guardato a mano.

### 8.4 ⚠️ Correzione al §5: il punto 4 oggi sarebbe un errore

Il §5 chiede di togliere dalla baseline cinque test «rientrati». **Non vanno
tolti.** Eseguiti il 2026-08-05: tre falliscono ancora per asserzione (1, 2 e 2
rossi), due producono **zero asserzioni** per errore di fixture. Nessuno è verde.

Erano «rientrati» solo agli occhi del runner rotto, che li lanciava con un altro
utente: è lo stesso equivoco che il brief documenta, applicato a se stesso. Vale
la pena lasciarlo scritto invece di cancellare la riga — è la prova più chiara di
quanto costi un confronto fatto fra due mondi diversi.

Anche il punto 3 è decaduto: i 9 rossi `E_SORG_FORMATO` non sono più in baseline,
che oggi è 28 `ERRORE_FIXTURE` + 8 `ASSERZIONE`. Il punto 5 è fatto.


---

## 9. Cosa è stato fatto, e cosa manca (2026-08-05, sera)

### 9.1 Fatto

* **Helper** `script.fn_pgtap_set_contesto_operatore()` — changeSet `20260805-27`.
  Sceglie da sé un operatore con almeno un emittente in whitelist (nessun id
  scritto a mano) e fallisce parlando se non ne esiste nessuno.
* **Riga di contesto in 174 file su 175** di `vendite`.
* **Un file escluso, con la spiegazione dentro**: `test-vw-dash-aperto-v1` si
  costruisce il contesto da solo — fa perfino `ALTER TABLE … FORCE ROW LEVEL
  SECURITY` in transazione — perché ciò che verifica *è* lo scope RLS.
  Imporgliene uno lo portava da 14 asserzioni a 4.

**La baseline NON è stata toccata**: `db/pgtap/baseline-rossi.tsv` è invariato.
Va rigenerata solo quando il runner cambierà utente (§9.3), perché è allora che
descriverà un mondo diverso.

### 9.2 L'effetto, misurato col runner attuale (owner)

> ⚠️ **Valori assoluti sovrastimati: vedi §14** (misura senza `ON_ERROR_STOP`).
> I confronti fra le righe restano validi — stesso metro su tutte.

| | ok | ko | file rossi o muti |
| --- | --- | --- | --- |
| prima | 1643 | 30 | 24 |
| adesso | **1749** | **27** | **15** |
| peggioramenti | — | — | **0** |

Il guadagno non viene ancora dalla RLS — con l'owner non è esercitata — ma da un
effetto collaterale non previsto: **dodici file erano morti** perché le loro
fixture chiamavano `fn_resolve_emittente_for_user` con la GUC vuota. Col contesto
impostato tornano verdi (`test-contratti-schema-step22` da 0 a 17,
`test-contratti-righe-coerenza-fonte-erogazione` da 0 a 17, `test-contratti-step23`
da 0 a 13, e altri nove).

### 9.3 🔴 Il piano del §8.3 va corretto: il runner non si può ancora girare

**Il runner è globale, non solo `vendite`.** Misurato sugli altri 250 file:

| altri schemi | ok | ko | file rossi o muti |
| --- | --- | --- | --- |
| owner (oggi) | 2157 | 104 | 51 |
| app + contesto | 1758 | 130 | **67** |

**Diciannove file peggiorerebbero**, e la distribuzione dice cosa sono: **6 in
`rls/`** — la stessa famiglia del file escluso, test che si impostano il contesto
da soli — più 5 `pratiche`, 3 `dbops`, 2 `ui`, 2 `script`, 1 `maintenance`.

Quindi i passi **3 (cambio utente al runner)** e **4 (ribaselinatura)** del §8.3
restano da fare, ma **non oggi**: prima serve la stessa passata sugli altri
schemi — escludere la famiglia `rls/`, guardare i 13 restanti uno per uno.

Il lavoro fatto non è in attesa: migliora la suite già adesso, e rende il cambio
di utente una riga sola in `scripts/testpgtap.sh`.


---

## 10. Consolidamento del 2026-08-05 (sera) — stato, e da dove ripartire

> Scritto chiudendo la sessione. Il **runner non è stato cambiato**: tutto quanto
> segue è neutro o migliorativo con l'utente di oggi (`titodb`, owner).

### 10.1 Fatto e verificato

| Cosa | changeSet / file | Effetto misurato |
| --- | --- | --- |
| Helper del contesto `script.fn_pgtap_set_contesto_operatore()` | `20260805-27` | sceglie un operatore **normale** (un emittente), esclude i super admin |
| Riga di contesto in `vendite` | 174 file su 175 | owner: **1643 → 1749 ok**, 24 → 15 file rossi, **0 peggioramenti** |
| Un file escluso, con la ragione dentro | `test-vw-dash-aperto-v1` | si costruisce il contesto da sé (verifica lo scope): con la riga passava da 14 a 4 asserzioni |
| Helper dell'emittente `script.fn_pgtap_emittente_operatore()` | `20260805-38` | risponde «su quale emittente posso scrivere», dal contesto o in modo deterministico |
| Sostituzione del `LIMIT 1` sull'emittente | 33 file di `pratiche` | owner: **neutro** (457/6/1 invariato); owner **+ contesto**: 247 → **454 ok**, 5 → 1 file rossi |

### 10.2 🔴 Due lezioni pagate, che cambiano il piano del §8.3

**Non è solo RLS: una parte dei controlli è fatta da TRIGGER**, e i trigger
scattano per chiunque, owner compreso. Aggiungendo la riga di contesto ai 233
file fuori `vendite` si sono rotti **32 file (30 in `pratiche`)** *senza che il
runner fosse cambiato*: bastava dichiarare l'operatore per accendere
`trgfn_guard_emittente_scope`. **La riga è stata rimossa da quei 233 file** e
`pratiche` è tornato identico (457/6/1).

Conseguenza: **impostare il contesto non è una preparazione neutra da fare in
anticipo.** Cambia il comportamento subito. Ogni file va verificato sotto
l'utente di oggi *prima* che sotto quello di domani.

**La causa dei 30 rossi era una riga copiata:**
`SELECT id FROM anagrafiche.emittenti_fiscali WHERE attivo = true LIMIT 1` —
senza `ORDER BY`, restituiva l'emittente **44** (`EMI-TEST`), attivo, **senza un
solo documento** (i 163 preventivi e le 102 pratiche stanno tutti sul 32) e **non
assegnato a nessun operatore**. Risolto girando la domanda: non «dammi un
emittente» ma «dammi *il mio*», che è il verso dell'applicazione.

> ℹ️ **Perché NON si è assegnato un operatore al 44.** Le fixture avrebbero
> continuato a pescare a caso — a volte 32, a volte 44 — e il test sarebbe
> passato o no a seconda di chi agisce: il rosso intermittente, che è peggio del
> rosso fisso perché in baseline copre un rosso vero. Il 44 va **lasciato senza
> operatore**: è il soggetto naturale del giorno in cui si vorrà verificare che
> un operatore *non* veda i documenti dell'altro.

### 10.3 ⚠️ La domanda aperta, e le ipotesi per ripartire

**Sotto l'utente applicativo `pratiche` resta a 127 ok / 17 ko / 5 file rossi,
contro i 457 / 6 / 1 dell'owner.** La correzione dell'emittente **non ha toccato
questo divario** (127/17/5 identico prima e dopo): sono due problemi diversi, e
il secondo non è stato identificato.

Sull'intera suite il quadro è: owner **3699 ok / 142 ko / 71 file**, utente
applicativo **3380 / 155 / 88**, con **51 file che peggiorano** (17 `pratiche`,
14 `vendite`, 6 `script`, 6 `rls`, 4 `dbops`, 2 `ui`).

Ipotesi da verificare, in ordine di costo crescente:

1. **Una causa sola, come lo era l'emittente.** Il comportamento di `pratiche` —
   330 asserzioni perse in blocco — somiglia a un unico predicato che taglia,
   non a trenta problemi diversi. Primo controllo: prendere **un** file di
   `pratiche` che perde asserzioni, lanciarlo come utente applicativo e leggere
   il **primo** errore. È così che è venuto fuori l'emittente 44.
2. **GRANT mancanti su `pratiche`**, non RLS. Su `vendite` i permessi c'erano
   (verificato: `zeroerp_app` legge `preventivi`, scrive `commesse`, usa
   `script`); su `pratiche` **non è stato verificato**. Un `has_table_privilege`
   sulle tabelle di quello schema costa una query.
3. **Un secondo guard a trigger**, come `trgfn_guard_emittente_scope` ma su
   altro (contesto pratica, reparto, unità organizzativa). Il `pratiche` ha
   guard propri: vanno elencati e guardati.
4. **RLS su `pratiche.pratiche`**: la tabella è fra quelle con `relrowsecurity`.
   Le sue policy leggono `app.ruolo_applicativo` e `app.current_user_id`, ma
   potrebbero leggere anche altro (reparto, identità) che il contesto non
   imposta.

⚠️ **Da non rifare**: la strada «operatore senza restrizione» è già stata
provata e **misurata peggiore** (99 file rossi contro 88, 55 peggioramenti
contro 51). È anche meno fedele: un operatore senza emittente non è permissivo,
è una configurazione incompleta.

> ✅ **Risolta il 2026-08-06, al §11.1.** Erano l'ipotesi 4 e l'ipotesi 2, ma
> in forma più semplice di come sono scritte qui.

### 10.4 Un difetto trovato fuori perimetro, già corretto

`test-fn-init-componenti-jsonb-override-v1` falliva a intermittenza. Dettaglio e
lezione nel **§6**; in breve: sceglieva il proprio soggetto con `LIMIT 1` senza
`ORDER BY` fra 44 candidati di cui **33 non potevano far scattare il guard**
(guardia di idempotenza a monte). **Lo stesso schema — `LIMIT 1` senza
ordinamento — è comparso tre volte in un giorno**: nel test, nelle 33 fixture di
`pratiche`, e nella scelta dell'emittente. Vale la pena contarlo su tutta la
suite prima di rigenerare la baseline: è un `grep`, e ogni occorrenza è un test
che scommette invece di verificare.

---

## 11. Il divario di `pratiche`, sciolto (2026-08-06)

> Trovato **senza** l'utente applicativo: bastavano il catalogo dei privilegi e
> la lettura delle policy. Il runner resta invariato.

### 11.1 Non era una causa ignota: erano due, entrambe già nell'elenco

**Prima causa — 33 file su 37: manca il contesto, non le policy.** Nei 43 file di
`pratiche` la chiamata a `fn_pgtap_set_contesto_operatore()` compariva **zero
volte**, perché il §10.2 l'aveva tolta da tutti i 233 file fuori `vendite`. E
`pratiche.pratiche` ha `relrowsecurity = true` con una sola policy `cmd=*`:

```
rls_pratiche_ef_whitelist:
  current_setting('app.ruolo_applicativo', true) = 'OPERATORE'
  AND script.fn_scope_ef_whitelist(current_setting('app.current_user_id', true)::int,
                                   emittente_fiscale_id)
```

Senza GUC il primo membro è `NULL`, la policy è falsa, e la tabella risponde zero
righe in lettura respingendo ogni scrittura. Il conto torna riga per riga: dei
**37 file che perdevano asserzioni, 33 toccano `pratiche.pratiche`**. È la firma
che si legge anche nei numeri — quasi tutti scendevano a **1 o 2 asserzioni**,
cioè morivano subito dopo le precondizioni.

Quindi l'**ipotesi 4** del §10.3, ma non nella forma temuta («le policy leggono
anche reparto o identità»): le policy leggono esattamente le due GUC previste, e
il contesto semplicemente non c'era.

**Seconda causa — i 4 file restanti: privilegi, e non è un buco.** Tre scrivono
su `pratiche.workflow_definizioni`, che per `zeroerp_app` è **in sola lettura per
scelta**:

| tabella `pratiche` | SELECT | INSERT | UPDATE | DELETE |
|---|---|---|---|---|
| `workflow_definizioni` | ✅ | ❌ | ❌ | ❌ |
| `azioni_ui` | ✅ | ❌ | ❌ | ❌ |
| `template_flussi_avanzamento_proiezione` | ✅ | ❌ | ❌ | ❌ |

Il `GRANT SELECT` è deliberato (`20260703-15`, richiamato da `20260704-01`):
l'applicazione **non scrive mai direttamente** su `workflow_definizioni`, ci
passa da `fn_pubblica_definizione`, che è `SECURITY DEFINER` proprio per questo.
Sul resto degli schemi i privilegi sono completi — verificato tabella per tabella
con `has_table_privilege`, l'ipotesi 2 nella sua forma generale è **esclusa**.

⚠️ **Ne esce un difetto vero, di test e non di privilegi.** I tre file portano la
definizione in `RITIRATA` con un `UPDATE` diretto, ma **`RITIRATA` non è uno stato
che qualcuno possa impostare**: si raggiunge solo come effetto della
pubblicazione di una versione nuova, dentro `fn_pubblica_definizione`. Quei test
collaudano quindi una transizione che in esercizio non esiste — è la stessa
lezione del §4, un verde che non dice nulla. Vanno riscritti passando dalla
funzione. Fuori perimetro di questo brief: appartiene al cantiere delle
definizioni versionate.

### 11.2 La riga di contesto è tornata in `pratiche`, e adesso è neutra

Il §10.2 l'aveva rimossa perché rompeva 30 file. La causa era l'emittente 44, ed
è stata sanata: rimessa oggi in tutti i **43 file**, il confronto con l'owner
senza contesto è **identico file per file**.

| `pratiche`, lanciato da owner | ok | ko | file rossi o muti |
| --- | --- | --- | --- |
| senza contesto (com'era) | 457 | 6 | 1 |
| con contesto, prima del fix sotto | 454 | 6 | 1 |
| **con contesto, dopo il fix** | **457** | **6** | **1** |

`scripts/pgtap-baseline.sh pratiche` → **nessuna regressione**. E la verifica che
conta di più: **la baseline è stata poi eseguita su tutta la suite, e nemmeno lì
c'è una regressione**. Vale la pena dirlo perché la riga di contesto non è un
intervento locale — accende trigger e policy — e il perimetro `pratiche` da solo
non avrebbe dimostrato che gli altri schemi non ne risentono.

**Il file che regrediva era la 34ª occorrenza dello stesso difetto.**
`test-coda-esclude-pratiche-terminali.sql` era rimasto fuori dalla passata sui 33
e conservava la riga
`SELECT id FROM anagrafiche.emittenti_fiscali WHERE attivo = true LIMIT 1`.
Appena dichiarato un contesto, l'errore è stato quello di sempre, alla lettera:

```
Accesso negato per scope emittente fiscale:
Utente 5 non autorizzato per emittente fiscale 44 su pratiche.pratiche
```

Sostituito con `script.fn_pgtap_emittente_operatore()` → **5/5 verde**. E ora le
sue 5 asserzioni lavorano su una pratica dell'emittente di chi agisce, non su una
dell'emittente 44 che non è di nessuno: stesso numero, significato diverso.

Cercato in tutta la suite: **non ne restano altre**. Le due occorrenze superstiti
di `emittenti_fiscali … LIMIT 1` sono dentro `EXISTS(...)`, dove il `LIMIT` non
sceglie niente.

### 11.3 Il censimento del §10.4, fatto

Analizzate tutte le occorrenze di `LIMIT 1` mascherando commenti, stringhe e
dollar-quote, e risalendo all'inizio della query bilanciando le parentesi, così
che `ORDER BY` sia cercato **allo stesso livello di annidamento** e non altrove
nel file.

| schema | `LIMIT 1` senza `ORDER BY` | di cui rischio ALTO | file |
| --- | --- | --- | --- |
| `vendite` | 385 | 79 | 98 |
| `pratiche` | 91 | 33 | 28 |
| `script` | 45 | 6 | 19 |
| `anagrafiche` | 44 | 7 | 15 |
| `rls` | 8 | 6 | 7 |
| `config` + `ui` | 4 | 2 | 3 |
| **totale** | **577** | **133** | **170 su 440** |

«ALTO» = nessun `WHERE`, oppure un `WHERE` che filtra un insieme senza
individuare una riga (`attivo = true`, `IS NOT NULL`). La tabella più pescata a
caso è **`anagrafiche.soggetti`, 24 volte**: la forma esatta dell'emittente 44.
E **82 file** hanno più di un `LIMIT 1` sulla stessa tabella — i candidati al
difetto del test intermittente, due estrazioni indipendenti che possono dare
soggetti diversi fra lo `skip` e l'asserzione.

Il numero che il §10.4 chiedeva prima di ribaselinare adesso c'è. Non è una
giornata di lavoro: è un cantiere a sé, e va aperto **prima** di
`pgtap-baseline.sh --update`, altrimenti si registra come «noto» un pezzo di
fortuna.

### 11.4 Cosa resta

1. **Misurare `pratiche` sotto `zeroerp_app`** con la riga rimessa: è la verifica
   della diagnosi del §11.1, e serve la credenziale del ruolo applicativo (né
   `titodb` né chi lancia i test la ha oggi — non è superuser, non è membro del
   ruolo, non ha `CREATEROLE`).
2. **La stessa passata sugli altri schemi** (`script`, `dbops`, `ui`,
   `maintenance`), escludendo la famiglia `rls/` che il contesto se lo costruisce
   da sé. Metodo confermato oggi: **rimettere la riga, misurare da owner, e
   pretendere zero differenze** prima di guardare all'utente applicativo.
3. **I 3 test su `workflow_definizioni`** (§11.1), da riscrivere passando da
   `fn_pubblica_definizione`.
4. **Il cantiere `LIMIT 1`** (§11.3), 133 siti a rischio ALTO.
5. Solo dopo: **passi 3 e 4 del §8.3** — cambio utente al runner e
   ribaselinatura.

---

## 12. La passata è completa: tutti gli schemi, 408 file su 426 (2026-08-06)

> Chiude il punto **2 del §11.4**. Il runner **non è ancora cambiato**: anche
> questo è tutto neutro o migliorativo con l'owner di oggi.

### 12.1 Copertura

| | file |
| --- | --- |
| con la riga di contesto | **408** |
| esclusi, con la ragione scritta dentro | **4** |
| famiglia `rls/`, fuori perimetro per definizione | 14 |
| **totale suite** | **426** |

Non resta un solo file del perimetro senza una riga o una spiegazione. Chi apre
un test adesso sa in che condizione gira, e se non ci gira sa perché.

### 12.2 L'effetto, misurato schema per schema da owner

> ⚠️ **I valori assoluti qui sotto sono sovrastimati** — vedi §14. **La
> conclusione regge**: «prima» e «dopo» sono stati misurati con lo stesso metro,
> quindi «invariato» significa davvero invariato.

Metodo del §11.2: aggiungere, rimisurare, **pretendere zero differenze**.

| schema | file | prima (ok/ko/rossi) | dopo |
| --- | --- | --- | --- |
| `script` | 58 | 449 / 17 / 10 | **invariato** |
| `anagrafiche` | 54 | 360 / 47 / 22 | **invariato** |
| `config` | 26 | 229 / 13 / 5 | **invariato** |
| `dbops` | 16 | 154 / 1 / 2 | **160 / 1 / 1** ⬆ |
| `catalogo` | 15 | 114 / 8 / 3 | **invariato** |
| `documenti` | 11 | 106 / 0 / 0 | **invariato** |
| `ui` | 8 | 96 / 8 / 4 | **invariato** |
| `pagamenti` · `maintenance` · `shop` | 6 | 52 / 0 / 0 | **invariato** |

`scripts/pgtap-baseline.sh` sull'**intera suite**: **nessuna regressione**, e un
solo **rientrato**.

**Il rientrato è vero, e si è verificato perché.** Il §8.4 aveva già scambiato per
«rientrati» cinque test che erano solo lanciati da un altro utente, quindi
l'etichetta non basta. `dbops/test-fn-apply-chiusura-scadenze-v1.sql` era **muto**
(0 asserzioni) e ora ne fa **6 verdi**; lanciato senza la riga risponde ancora,
alla lettera:

```
Nessun emittente fiscale attivo … GUC vuota, numero=PGTAP_FW_CONTR_SCAD
```

È lo stesso meccanismo dei dodici file di `vendite` del §9.2: la fixture chiamava
`fn_resolve_emittente_for_user` senza contesto. Tolto dalla baseline con
`--update dbops` (aggiornamento parziale, così le altre classificazioni restano
quelle curate a mano): **89 → 88 righe**, ed è l'unica differenza nel file. Il
registro del debito è calato di uno.

### 12.3 I tre file esclusi oggi, e il difetto che ne esce

Solo tre file peggioravano, e nessuno per un difetto proprio: in tutti e tre il
contesto **non è lo sfondo, è il soggetto**.

**`script/test-fn-current-identita-context.sql`** (7 → 6+1) — verifica cosa
`fn_current_identita_context` legge in ogni combinazione di GUC, impostandole e
azzerandole da sé. La sua prima asserzione è «nessuna GUC settata → tutte le
colonne NULL»: una riga in testa ne distrugge la premessa prima di cominciare.
Caso limpido, come `test-vw-dash-aperto-v1`.

**`ui/test-fn-resolve-dashboard-config.sql`** (12 → 10+2) e
**`ui/test-fn-resolve-lista-config.sql`** (13 → 10+3) — qui la ragione è scomoda e
va detta per intero. Entrambi costruiscono un'identità **`CLIENTE_PORTALE`** e su
quella verificano le precedenze fra preset. Ma la funzione filtra i profili per la
veste corrente:

```
v_ruolo_guc := current_setting('app.ruolo_applicativo', true)   -- NULL = tutte le vesti
… script.fn_get_profili_accesso_applicabili(p_auth_user_id, v_ruolo_guc)
```

Dichiarare `OPERATORE` esclude — **correttamente** — il profilo di un'identità
portale. La funzione fa il suo mestiere; è l'accoppiata «identità portale + veste
operatore» a non esistere.

⚠️ **Ma il rovescio è peggiore, e non va lasciato implicito.** Senza GUC la veste
è `NULL`, cioè *tutte* — e questa è una condizione che **l'applicazione non
produce mai**, perché il middleware la valorizza sempre. Quelle asserzioni sono
verdi in un mondo che non esiste: la stessa cosa che il §4 rimprovera alla strada
(a). La correzione vera non è imporre una veste operatore, è far dichiarare al
test **la veste coerente con la propria fixture** (`CLIENTE_PORTALE`) e
riverificare le precedenze lì dentro. È una decisione del cantiere `ui`, non di
questo brief: qui resta scritta, con la ragione, dentro i due file.

C'è un indizio che lo conferma: `test-fn-resolve-lista-config` **conosce già** la
GUC — la sua asserzione 12 la manipola apposta per verificare che la veste filtri.
Sceglie di tenerla vuota per tutte le altre.

### 12.4 Cosa resta adesso

Dei cinque punti del §11.4 restano:

1. **Misurare sotto `zeroerp_app`** — unico passo bloccato, serve la credenziale
   del ruolo. Sta in `backend/.env` del server backend (`DB_USER=zeroerp_app` +
   `DB_PASSWORD`); va messa in `~/.pgpass` (`localhost:5432:zeroerp:zeroerp_app:…`,
   `chmod 600`) e **non** in un file dentro il repo: `.gitignore` filtra
   `internal.env` esatto, non altri nomi.
   ⚠️ **Non resettare la password del ruolo**: la si cambierebbe sotto i piedi al
   backend.
2. **I 3 test su `workflow_definizioni`** (§11.1) e **i 2 di `ui`** (§12.3) —
   entrambi difetti di test, entrambi da evadere nel cantiere proprietario.
3. **Il cantiere `LIMIT 1`** (§11.3): 133 siti a rischio ALTO.
4. **Passi 3 e 4 del §8.3**: cambio utente al runner e ribaselinatura. Ora sono
   davvero una riga in `scripts/testpgtap.sh` più una rigenerazione — tutto il
   resto è pronto.

---

## 13. La prima misura sotto `zeroerp_app` — e il primo difetto vero (2026-08-06)

> Chiude il punto **1 del §12.4**. La credenziale del ruolo applicativo è stata
> messa in `~/.pgpass`; il runner **non è ancora cambiato**.

### 13.1 Il quadro

> ⚠️ **Questo paragrafo è stato riscritto: la prima stesura riportava numeri
> presi con un metro sbagliato.** Cosa non andava, cosa resta valido e come si
> riconosce: **§14**. Sotto ci sono i numeri verificati, misurati riproducendo
> `pg_prove` (`ON_ERROR_STOP=1`) e allineati alla baseline **file per file**.

| suite intera, 426 file | ok | ko | file rossi |
| --- | --- | --- | --- |
| owner (com'è oggi) | 3853 | 74 | **88** |
| **utente applicativo** | **3318** | **69** | **152** |

Gli 88 dell'owner coincidono **esattamente** con la baseline, nome per nome:
zero divergenze in entrambe le direzioni. È la prova che il metro è quello giusto.

Il numero che conta non è però 152 — dentro ci sono anche i rossi già noti. È il
**delta**: i file che l'owner vede verdi e l'utente applicativo no, cioè ciò che
davvero blocca il cambio di runner.

**Sessantacinque file.** E la loro distribuzione è la notizia buona:

| causa | file | che cos'è |
| --- | --- | --- |
| `permesso negato per la tabella workflow_definizioni` | **38** | **una sola causa, e vale il 58% del delta**: 37 dei 43 file di `pratiche` più uno di `dbops`. Vedi §13.2 |
| `bisogna essere proprietari della tabella …` | 9 | i test fanno `ALTER TABLE … FORCE ROW LEVEL SECURITY`: richiedono l'**owner per natura**. 6 sono la famiglia `rls/`, uno è `vendite/test-promo-articoli-guard-data-driven-v1` — quello che il §8.2 aveva già isolato come «il lavoro residuo a mano è UN file» |
| `la nuova riga viola la regola di sicurezza per riga` | 7 | RLS **davvero esercitata**, su `commesse` (5) e `fatture_righe` (2). Non è un incidente: è il motivo per cui esiste questo brief |
| `permesso negato per lo schema dbops` | 3 | i test fanno `CREATE TABLE dbops.…`: strumenti DBA, stessa famiglia «owner» |
| GRANT mancanti mirati | 4 | `preventivi`, `pratiche_sorgenti`, `indirizzi_dettaglio`, `dashboard_definizione` |
| non-ok o piano non rispettato | 3 | da guardare uno per uno |
| `Profilo N (tipo AD_HOC): binding non coerente` | 1 | il `ui` del §12.3 — ora leggibile grazie al §13.3 |
| `Nessun emittente fiscale attivo … GUC vuota` | 1 | `test-vw-dash-aperto-v1`, già escluso e documentato |

Due letture, e sono entrambe utili:

* **Il grosso è UNA correzione.** 38 file su 65 si fermano tutti sulla stessa
  riga. Non sono 38 problemi: è un `SECURITY DEFINER` mancante (§13.2).
* **Dodici file sono la famiglia «richiede owner»** (9 + 3): non sono difetti e
  non lo diventeranno. Vanno riconosciuti come categoria, e il runner dovrà
  saperli lanciare da owner. È quella, non i permessi, la vera precondizione al
  passo 3 del §8.3.

### 13.2 `pratiche` sotto l'utente applicativo: un trigger, non un permesso

Il primo errore, letto come insegna il §10.3:

```
ERRORE: permesso negato per la tabella workflow_definizioni
CONTESTO: funzione PL/pgSQL pratiche.trgfn_tipi_prestazione_bootstrap_definizione() riga 7
          INSERT INTO pratiche.workflow_definizioni …
```

Un **trigger** `z90` su `pratiche.tipi_prestazione` scrive la definizione «v1 —
preset iniziale», ed è `SECURITY INVOKER`. Ma `workflow_definizioni` è SELECT-only
per il ruolo applicativo **per scelta** (`20260703-15`, §11.1). Quindi:
**`zeroerp_app` non può creare un tipo di prestazione**, mai, per nessuna via.

⚠️ **È il singolo blocco più grosso di tutto il cantiere**: **37 dei 43 file di
`pratiche`, più uno di `dbops`**, si fermano su questa riga — 38 dei 65 file del
delta. Ogni fixture che crea un tipo di prestazione muore lì, alla prima
istruzione utile. Non sono 38 problemi da istruire: è una parola mancante.

Oggi non si vede perché il backend non ci scrive — verificato, nessun
`INSERT/UPDATE/DELETE` su `pratiche.tipi_prestazione` in `backend/`. È un buco
**latente**: il giorno in cui nasce la schermata «nuovo tipo prestazione», si
rompe.

La correzione ha un precedente diretto nello stesso schema: `20260703-16` e
`-17` hanno reso `SECURITY DEFINER` `fn_fork_nuova_versione` e
`fn_pubblica_definizione` per la stessa ragione. Il bootstrap non è una scrittura
che l'utente sceglie, è il dominio che si prepara da sé — il caso da manuale per
il `DEFINER`. **Non fatto qui**: appartiene al cantiere delle definizioni
versionate, e va deciso lì insieme ai 3 test del §11.1.

### 13.3 ⚠️ Un guard che non ha mai detto la sua ragione — corretto

Questo **non è un difetto di test**: è il primo difetto di prodotto che la strada
(b) restituisce, e da solo ripaga il cantiere.

Il messaggio registrato per `E_PROFILO_ACCESSO_BINDING_INCOERENTE` ha **due**
segnaposto:

```
Profilo %s (tipo %s): binding non coerente col tipo del profilo.
```

ma tutti e quattro i punti di `config.trgfn_profili_accesso_bindings_guard_coerenza`
che lo sollevavano passavano **un solo** valore variadico. `fn_log_and_raise_error`
compone con `format(messaggio, VARIADIC valori)`, quindi ogni volta che il guard
scattava esplodeva prima di parlare:

```
ERRORE: numero di argomenti non sufficiente per format()   (SQLSTATE 22023)
```

Chi lo incontrava vedeva un errore interno di PostgreSQL al posto della ragione, e
nel log non finiva nessun codice di dominio. **Riprodotto anche da owner**: non
c'entra l'utente applicativo, che ha solo avuto il merito di passare da lì.

**Corretto** — changeSet `20260806-12`, `v_tipo_profilo::text` come secondo valore
nei quattro punti. Ora il guard dice:

```
P0001 | Profilo 1 (tipo REPARTO): binding non coerente col tipo del profilo.
```

**Perché nessuno se n'era accorto, ed è la parte che vale.** Il test esiste —
`config/test-profili-accesso-bindings-guard-coerenza.sql` — e passava.
Usava `throws_ok(sql, NULL, NULL, descrizione)`: verifica **che** sollevi, non
**che cosa**. Il crash di `format()` lo soddisfaceva esattamente come lo avrebbe
soddisfatto il guard funzionante. Verde per la ragione sbagliata, con la
descrizione che nominava il codice atteso senza mai controllarlo.

Le asserzioni ora pretendono lo SQLSTATE. E tirando quel filo ne è uscita una
seconda:

⚠️ **L'asserzione 4 non collaudava il `CHECK`, e non lo ha mai fatto.** Si
chiamava «CHECK xor: 0 colonne valorizzate», ma in PostgreSQL **i trigger BEFORE
ROW girano prima che i vincoli CHECK siano valutati**: con zero colonne su un
profilo REPARTO è il guard a intercettare, e `chk_profili_accesso_bindings_xor`
non viene mai raggiunto. Misurato: `P0001`, non `23514`. L'unica asserzione che
tocca davvero il CHECK è la **5**, e per un motivo preciso — con
`unita_organizzativa_id` valorizzato il guard è soddisfatto e lascia passare,
così l'xor può finalmente scattare.

Lo stesso equivoco stava scritto **dentro la funzione**, nel commento
«Pre-condizioni: il CHECK garantisce … prima che il trigger venga eseguito».
È il contrario, ed è corretto nel changeSet: un commento sbagliato che aveva già
ingannato un test non è un dettaglio di forma.

Test **9/9 verde**, `pgtap-baseline.sh config` senza regressioni.

### 13.4 Cosa resta, in ordine di resa

1. **`trgfn_tipi_prestazione_bootstrap_definizione` → `SECURITY DEFINER`**
   (§13.2). **Sblocca 38 dei 65 file del delta** — è la mossa con il rapporto
   resa/costo più alto di tutto il cantiere, e ha già due precedenti nello stesso
   schema (`20260703-16`, `-17`). Va evasa insieme ai 3 test su
   `workflow_definizioni` del §11.1: cantiere definizioni versionate.
2. **La famiglia «richiede owner»** (12 file: 9 `ALTER TABLE … FORCE ROW LEVEL
   SECURITY` + 3 `CREATE TABLE dbops.…`). Non è un difetto, è una **categoria**:
   serve una marcatura nel file e un runner che sappia lanciarli da owner. È la
   vera precondizione al passo 3 del §8.3, ed è l'unico punto che richiede una
   decisione di design, non una correzione.
3. **I 7 file con RLS in scrittura** su `commesse` e `fatture_righe`: qui la
   policy viene esercitata sul serio, ed è il motivo per cui esiste il brief.
   Vanno guardati uno per uno — è lì che si scopre se una policy è giusta.
4. **I 4 GRANT mirati** (`preventivi`, `pratiche_sorgenti`,
   `indirizzi_dettaglio`, `dashboard_definizione`) e **i 2 test `ui`** del §12.3.
   Nota: dopo il fix del §13.3 il loro errore è finalmente leggibile —
   «Profilo 9469 (tipo AD_HOC): binding non coerente col tipo del profilo» — e
   conferma la diagnosi del §12.3.
5. **I 3 file con non-ok o piano non rispettato**, da guardare uno per uno.
6. **Il cantiere `LIMIT 1`** (§11.3): 133 siti a rischio ALTO.
7. Poi, e solo poi, **cambio utente al runner e ribaselinatura**.

---

## 14. ⚠️ Il metro era sbagliato — cosa cade e cosa regge (2026-08-06)

> Trovato consolidando il brief: i conteggi non tornavano con
> `scripts/pgtap-baseline.sh`, e non tornavano per un motivo preciso.

### 14.1 Il difetto della misura

Le misure di questo cantiere sono state prese lanciando i file con
`psql -f`. Ma `pg_prove` — il runner vero, quello che sta dentro
`scripts/testpgtap.sh` e `pgtap-baseline.sh` — li lancia con **`ON_ERROR_STOP=1`**.

La differenza non è di forma. Senza quell'opzione **psql tira dritto dopo un
errore**: continua a eseguire il file, continua a stampare `ok`, ed esce con
codice **0**. Con l'opzione si ferma alla prima istruzione che fallisce.

Esempio misurato, stesso file, stesso istante:

```
senza ON_ERROR_STOP : 6 ok su 6, exit 0                  -> sembra VERDE
con  ON_ERROR_STOP  : 3 ok, exit 3                       -> e' ROSSO
pg_prove            : Tests: 3, Bad plan. You planned 6 tests but ran 3.  FAIL
```

Conseguenza: **gli `ok` erano gonfiati e i file rossi sottostimati**. Il conto
tornava a 3920/131/**86** contro gli **88** della baseline, e le due righe di
scarto sembravano «rientrati» — non lo erano.

Riprodotto `pg_prove` (piano + `not ok` + exit code, con `ON_ERROR_STOP=1`), gli
88 file rossi da owner combaciano con la baseline **nome per nome, zero
divergenze in entrambe le direzioni**.

### 14.2 Cosa cade

I **valori assoluti** dei §8.2, §9.2, §12.2 e della prima stesura del §13.1.
Sono sovrastimati sugli `ok` e sottostimati sui rossi. In particolare:

* il delta sotto l'utente applicativo non è 20 file: è **65**;
* `pratiche` sotto l'utente applicativo non ha 5 file rossi ma **38 su 43** —
  perché quasi tutti muoiono alla prima istruzione utile (§13.2), e senza
  `ON_ERROR_STOP` proseguivano a produrre asserzioni verdi che il runner non
  avrebbe mai visto.

### 14.3 Cosa regge — e non è poco

**Tutti i confronti prima/dopo restano validi**, perché i due lati sono stati
misurati con lo stesso metro. Quindi restano vere, e non vanno rifatte:

* §12.2 — la riga di contesto è **neutra da owner** su ogni schema: «prima» e
  «dopo» sono stati misurati identicamente, e la differenza era zero;
* §11.2 — `pratiche` con la riga di contesto è **identico file per file** a
  `pratiche` senza;
* il rientrato di `dbops` (§12.2) e la baseline scesa da 89 a 88: verificati con
  `pgtap-baseline.sh`, cioè col metro giusto fin dall'inizio;
* il difetto del §13.3 e la sua correzione: verificati con esecuzioni dirette e
  `pgtap-baseline.sh config`, non con conteggi.

La lezione è la stessa che questo brief ripete da tre settimane, applicata
un'ultima volta a se stesso: **una misura vale quanto vale il modo in cui è
presa**, e due numeri sono confrontabili solo se prodotti dallo stesso strumento.
Era esattamente il §2 — «lo stesso file passa o fallisce a seconda di chi lo
lancia» — con «come» al posto di «chi».

### 14.4 Regola operativa

Per misurare la suite fuori da `pgtap-baseline.sh` serve **`ON_ERROR_STOP=1`**, e
un file va contato rosso se: exit ≠ 0, **oppure** c'è un `not ok`, **oppure** il
piano `1..N` non coincide con le asserzioni eseguite. Le tre condizioni servono
tutte: da sole nessuna riproduce `pg_prove`.

Nel dubbio, non contare a mano: lanciare `scripts/pgtap-baseline.sh <schema>`.

---

## 15. Il `SECURITY DEFINER` del §13.2, applicato — e un ostacolo nuovo (2026-08-06)

> Chiude il punto **1 del §13.4**, il primo per resa. E ne apre uno che il piano
> non prevedeva: **i test si sporcano il database a vicenda**.

### 15.1 Il risultato

ChangeSet **`20260806-16`**: `pratiche.trgfn_tipi_prestazione_bootstrap_definizione`
passa a `SECURITY DEFINER` con `search_path` fisso, sulla strada già battuta da
`20260703-16` e `-17` nello stesso schema. Corpo e firma invariati.

| `pratiche` (43 file) | ok | file rossi |
| --- | --- | --- |
| utente applicativo, prima | 93 | **38** |
| utente applicativo, dopo | **353** | **10** |
| owner, prima e dopo | 457 | 1 |

**Ventotto file sbloccati con una parola**, e da owner non cambia niente.

**Perché `DEFINER` e non un `GRANT`**: dare DML su `workflow_definizioni` al ruolo
applicativo riaprirebbe ciò che `20260703-15` ha chiuso apposta — quella tabella
si scrive solo attraverso le funzioni del dominio, che sanno mantenere
l'invariante di versionamento. Il bootstrap non è una scrittura che l'utente
sceglie: è il dominio che si prepara da sé, a partire da `NEW` e da nient'altro.

### 15.2 I 10 che restano, e sono tutti la stessa cosa

| causa | file |
| --- | --- |
| scrive direttamente su `pratiche.workflow_definizioni` | **7** |
| scrive su `pratiche.template_flussi_avanzamento_proiezione` | **2** |
| `bisogna essere proprietari della tabella sospensioni` | 1 |

Le prime due righe sono **la stessa famiglia del §11.1, cresciuta da 3 a 9**:
test che scrivono dove l'applicazione non scrive mai. Entrambe le tabelle sono
`SELECT`-only per il ruolo applicativo **per scelta**. Non è un buco di permessi:
è che quei test costruiscono stati che il dominio non permette di costruire —
`test-workflow-definizioni-fase0` per esempio fa
`DELETE FROM pratiche.workflow_definizioni` per fabbricare un «tipo senza preset»
e verificare che il guard 507 scatti.

⚠️ **E quella è un'intenzione legittima.** Un guard si prova solo mettendolo nella
condizione che deve respingere, e se quella condizione è irraggiungibile per
l'applicazione, il test ha bisogno di privilegi che l'applicazione non ha. Sono
quindi **candidati alla categoria «richiede owner»** del §13.4 punto 2, non a una
riscrittura. La decisione è del cantiere definizioni versionate.

### 15.3 ⚠️ L'ostacolo nuovo: le corse si contaminano

Applicato il changeSet, la misura da owner è passata da **457/6/1** a
**448/6/2**. Non era il changeSet:

```
un valore chiave duplicato viola il vincolo univoco "uq_template_flussi_definizione_codice"
La chiave (definizione_id, codice)=(5411, WDF_STEP) esiste già.
```

Le righe `TEST_WDF` e `TEST_WDF2` erano state inserite da **`zeroerp_app`**, cioè
dalla misura sotto l'utente applicativo lanciata pochi minuti prima. Quel file
muore alla 5ª asserzione su 11 — e il suo cleanup sta alla **sezione 10, in
fondo**. Non ci arriva mai.

**Il meccanismo, ed è generale.** Solo **10 dei 43 file di `pratiche`** aprono una
transazione: gli altri 33 puliscono con `DELETE` in coda al file. Col runner vero,
che gira con `ON_ERROR_STOP`, **un file che fallisce non raggiunge mai il proprio
cleanup**. Finché ci sono rossi, ogni corsa lascia detriti, e il rosso successivo
può essere causato dalla corsa precedente invece che dal codice.

È il «verde per la ragione sbagliata» rovesciato: un **rosso** per la ragione
sbagliata. E peggiora proprio adesso, perché la migrazione alla strada (b)
comporta di lanciare la suite con due utenti diversi sullo stesso database.

**Correzione applicata a `test-workflow-definizioni-fase0`**, e il pattern vale
per tutti:

1. **Pulizia d'ingresso FUORI dalla transazione**, in testa al file. In
   autocommit, quindi rimuove davvero i detriti di una corsa morta a metà —
   dentro la transazione verrebbe annullata insieme al resto e non servirebbe a
   niente. È questa a sanare il database *una volta*.
2. **`BEGIN;` … `ROLLBACK;`** attorno al corpo. Da lì in poi il file non lascia
   traccia comunque vada, e se muore a metà la transazione viene abbandonata alla
   chiusura della sessione.
3. Le `DELETE` del cleanup finale **restano**: lì sono un'asserzione (verificano
   la cascata), non una pulizia.

Verificato: 11/11 verde da owner, residuo azzerato dal test stesso, e owner resta
**457/6/1 anche dopo** una corsa completa sotto l'utente applicativo — la
contaminazione è chiusa per quel file.

### 15.4 Cosa si aggiunge al §13.4

**Rendere transazionali i file che non lo sono.** Contati su tutta la suite:
**77 file su 426** non aprono una transazione.

| schema | file | transazionali | **NON** transazionali |
| --- | --- | --- | --- |
| `pratiche` | 43 | 11 | **32** |
| `anagrafiche` | 54 | 34 | **20** |
| `catalogo` | 15 | 8 | 7 |
| `config` | 26 | 21 | 5 |
| `dbops` | 16 | 11 | 5 |
| `script` | 58 | 54 | 4 |
| `vendite` | 175 | 171 | 4 |
| `documenti` · `rls` · `ui` · `pagamenti` · `maintenance` · `shop` | 39 | 39 | 0 |
| **totale** | **426** | **349** | **77** |

La concentrazione dice dove intervenire: **`pratiche` e `anagrafiche` da soli
sono 52 dei 77**, e `vendite` — il perimetro più grande e più lavorato — ne ha
solo 4. Non è un abbellimento: senza, ogni misura sporca la successiva, e **la
ribaselinatura finale registrerebbe rossi che sono detriti**, non debito. Va
fatto *prima* del passo 3 del §8.3, insieme alla categoria «richiede owner».

Il pattern da applicare è quello del §15.3: pulizia d'ingresso fuori dalla
transazione, `BEGIN`/`ROLLBACK` attorno al corpo, e le `DELETE` che sono
asserzioni lasciate dove sono.

### 15.5 Verifica finale

`scripts/pgtap-baseline.sh` sull'intera suite dopo tutte le modifiche di oggi:
**88 rossi su 426, tutti già noti — nessuna regressione.**

---

## 16. `pratiche` reso transazionale — 43 file su 43 (2026-08-06)

> Primo lotto del §15.4, scelto perché è la concentrazione peggiore: 32 dei 77
> file non transazionali della suite stavano qui. `pratiche` e `anagrafiche` sono
> nati presto, quando il pattern non era ancora la norma.

### 16.1 Cosa è stato fatto

**32 file** hanno ricevuto `BEGIN;` in testa — prima della riga di contesto, cioè
prima di qualunque scrittura — e `ROLLBACK;` in coda, dopo `finish()`. Le `DELETE`
del cleanup esistente **sono rimaste dove sono**: dove sono un'asserzione (la
cascata di `test-workflow-definizioni-fase0`) devono continuare a girare, e il
`ROLLBACK` le annulla comunque.

Tolta anche la riga di commento «⚠️ Questo file non apre una transazione propria»
dove c'era: da adesso sarebbe falsa, e un commento sbagliato inganna chi legge —
lezione già pagata al §13.3.

Prima di toccarli, verificato che nessuno dipenda da un commit: nessun `COMMIT`,
nessun `pg_advisory_lock` non transazionale, nessun `VACUUM`, nessun
`CREATE INDEX CONCURRENTLY`.

### 16.2 L'unico che ha resistito, e insegna qualcosa

`test-sospensioni-tempi.sql` è passato da 22/0 a 12/3. Causa:

```
chk_sospensioni_data_fine:  CHECK (data_fine IS NULL OR data_fine > data_inizio)
```

⚠️ **Dentro una transazione `now()` è congelato all'apertura.** La sospensione
veniva aperta e chiusa nella stessa transazione, quindi `data_fine` risultava
**identica** a `data_inizio` e il `CHECK`, che è stretto, la respingeva.

In esercizio non può succedere: una sospensione si apre in una richiesta e si
chiude in un'altra, quindi i due `now()` sono diversi. È il **test** a comprimere
in una transazione due momenti che la realtà separa da minuti o giorni.

Corretto con **`clock_timestamp()`**, che legge l'orologio adesso invece che
all'apertura della transazione — l'unico modo di dire «un istante dopo» dentro
una transazione sola. Il vincolo resta esercitato: `data_fine > data_inizio` deve
comunque valere.

**Quattro occorrenze**, e le ultime due sono la parte istruttiva: la chiusura dei
flussi alimenta `pratiche.calcoli_tempo` **via trigger**, e anche
`chk_calcoli_tempo_data_fine` è stretto. Lì il problema non passava più dal test
ma dal codice di produzione che il test attraversa — lo stesso `now()` congelato,
due tabelle più in là.

> ℹ️ **Regola che ne esce**: rendendo transazionale un test che misura *tempi*,
> ogni `now()` usato come «istante successivo» va guardato. Non è un dettaglio di
> stile: `now()` e `clock_timestamp()` sono la stessa cosa fuori da una
> transazione e cose diverse dentro.

### 16.3 Verifica

| `pratiche` (43 file) | ok | ko | file rossi |
| --- | --- | --- | --- |
| owner, prima | 457 | 6 | 1 |
| **owner, dopo** | **457** | **6** | **1** |

**Zero differenze, file per file.** `scripts/pgtap-baseline.sh pratiche`: nessuna
regressione.

**La prova che conta — la contaminazione è chiusa:**

```
1) corsa sotto zeroerp_app   -> 353 ok, 10 file rossi
2) subito dopo, da owner     -> 457 ok,  1 file rosso   (invariato)
3) di nuovo sotto zeroerp_app-> 353 ok, 10 file rossi   (identica alla 1)
```

Prima la corsa (1) lasciava `TEST_WDF`/`TEST_WDF2` e la (2) crollava a 448/6/2.
Adesso le due corse convivono, e la corsa applicativa è **riproducibile**: stesso
numero due volte di fila. Residuo lasciato nel database dalle tre corse: **zero**.

### 16.4 Cosa resta del §15.4

**45 file non transazionali** su altri schemi: `anagrafiche` **20**, `catalogo` 7,
`config` 5, `dbops` 5, `script` 4, `vendite` 4. `anagrafiche` è il prossimo lotto
naturale — stessa età, stessa origine.

---

## 17. `anagrafiche` transazionale, e una trappola che stava per costarci cara (2026-08-06)

> Secondo lotto del §15.4. Ma la parte che conta non è `anagrafiche`: è il
> difetto che la sua misura ha rivelato, e che riguarda **anche il lotto
> `pratiche` già chiuso al §16** — dove non si vedeva nei numeri.

### 17.1 ⚠️ `BEGIN … ROLLBACK` spegne i vincoli DIFFERITI

Transazionalizzati i 20 file di `anagrafiche`, uno risultava **rientrato**:
`test-create-istanza-from-pdp` passava da 3 asserzioni su 9 a **9 su 9 verdi**,
stabile su tre esecuzioni. Sembrava un guadagno.

Non lo era. La versione precedente falliva in modo **riproducibile** con:

```
Istanza utility senza utility dichiarata: serve almeno un riferimento
(billing_account, dati precontrattuali, cliente). istanza_utility_id=1277
```

Il guard che solleva è
`trg_istanze_utilities_z90_require_utility_dichiarata_ins`, ed è un
**constraint trigger `DEFERRABLE INITIALLY DEFERRED`**: scatta al `COMMIT`. Un
file avvolto in `BEGIN … ROLLBACK` al `COMMIT` **non ci arriva mai**, quindi quel
controllo non scatta più. Il test era diventato verde **per sottrazione**: aveva
smesso di verificare, senza dirlo.

**Quanto è grande il buco**, contato nel DB:

| schema | trigger differiti | tabelle |
| --- | --- | --- |
| `vendite` | 150 | 57 |
| `config` | 53 | 33 |
| `pratiche` | 39 | 17 |
| `anagrafiche` | 36 | 20 |
| `magazzino` | 33 | 17 |
| altri (`acquisti`, `catalogo`, `documenti`, `pagamenti`) | 54 | 20 |
| **totale** | **365** | **164** |

Più **375 vincoli FK/UNIQUE dichiarati `DEFERRABLE INITIALLY DEFERRED`**.

⚠️ **Ed è la stessa lezione del §8.4 e del §13.3, in una veste nuova**: un test
che diventa verde va spiegato prima di essere creduto. Qui l'etichetta diceva
«rientrato» e la realtà era «ha smesso di guardare».

### 17.2 La correzione, e perché la posizione conta

`SET CONSTRAINTS ALL IMMEDIATE;` — ma **subito dopo `BEGIN;`**, non prima di
`finish()`.

Provate entrambe, e la differenza è netta:

| posizione | esito |
| --- | --- |
| in coda, prima di `finish()` | **31 file di `pratiche` diventano rossi** pur avendo tutte le asserzioni verdi |
| **in testa, dopo `BEGIN;`** | **zero differenze** rispetto a prima della transazionalizzazione |

In coda i differiti si accumulano per tutta la transazione e scattano **tutti
insieme dopo il cleanup**, su righe ormai cancellate: falliscono
(`dbops.trgfn_child_requires_active_parent`, «Padre non attivo») per una ragione
che non riguarda ciò che il test verifica.

In testa invece li riporta a scattare **a fine di ogni istruzione** — che è
esattamente come si comportavano prima, quando il file girava in autocommit e
ogni istruzione era una transazione a sé. Non è un compromesso: è la
riproduzione fedele del comportamento precedente.

### 17.3 Verifica

| schema, da owner | ok | ko | file rossi |
| --- | --- | --- | --- |
| `pratiche` prima → dopo | 457 → **457** | 6 → **6** | 1 → **1** |
| `anagrafiche` prima → dopo | 300 → **306** | 16 → **16** | 28 → **28** |

**Zero peggioramenti.** L'unico cambiamento in `anagrafiche` è
`test-istanza-cliente-chain`, che passa da **muto (0 asserzioni)** a 6 prima di
morire: resta rosso, ma adesso dice qualcosa.

`scripts/pgtap-baseline.sh anagrafiche pratiche`: **29 rossi su 97, nessuna
regressione**.

**Contaminazione chiusa anche qui:**

```
1) anagrafiche sotto zeroerp_app -> 304 ok, 29 file rossi
2) subito dopo, da owner         -> 306 ok, 28 file rossi   (invariato)
3) di nuovo sotto zeroerp_app    -> 304 ok, 29 file rossi   (identica alla 1)
```

### 17.4 Il debito che resta scoperto

⚠️ **I 349 file che erano GIÀ transazionali non hanno mai avuto questa riga.**
Il difetto del §17.1 non l'ho introdotto io: c'era da sempre in ogni file con
`BEGIN … ROLLBACK`, e i 53 che ho toccato oggi sono gli unici presidiati.

Vuol dire che una parte della suite **non esercita i 365 trigger differiti né i
375 vincoli differiti** — e non si sa quanta, perché aggiungere la riga potrebbe
far emergere rossi veri. È una passata da fare con la stessa cautela usata qui:
aggiungere, misurare, e leggere ogni differenza invece di accoglierla.

Non è un lavoro da chiudere di corsa prima della ribaselinatura: è materia sua,
e va deciso quanto scoperchiare in una volta.

### 17.5 Cosa resta del §15.4

**25 file non transazionali**: `catalogo` 7, `config` 5, `dbops` 5, `script` 4,
`vendite` 4. Più il debito del §17.4, che è di natura diversa e più grande.

---

## 18. La suite è transazionale al completo — 426 file su 426 (2026-08-06)

> Chiude il §15.4. Ultimo lotto: i 25 file rimasti su `catalogo` (7), `config`
> (5), `dbops` (5), `script` (4), `vendite` (4), in una passata sola con misura
> per schema, così ogni differenza resta attribuibile.

### 18.1 Il risultato

| schema, da owner | prima | dopo |
| --- | --- | --- |
| `catalogo` | 107 / 2 / 5 | **invariato** |
| `dbops` | 160 / 1 / 1 | **invariato** |
| `script` | 443 / 9 / 12 | **invariato** |
| `vendite` | 1749 / 16 / 24 | **invariato** |
| `config` | 229 / 12 / 6 | **invariato** (dopo il §18.2) |

`scripts/pgtap-baseline.sh` sui quattro schemi puliti: **42 rossi su 264, nessuna
regressione**. Contaminazione verificata su tutti: corsa applicativa → owner
invariato → corsa applicativa **identica**.

Due cose che il censimento ha corretto in corsa:

* **Dodici file non hanno `finish()`.** È legittimo — dichiarano solo `plan(N)`
  e pg_prove legge il flusso TAP. Il `ROLLBACK` va quindi ancorato alla fine del
  file, non a `finish()`.
* Nessun file dipendeva da un `COMMIT`: verificato prima di toccarli
  (`COMMIT`, advisory lock non transazionali, `VACUUM`,
  `CREATE INDEX CONCURRENTLY`).

### 18.2 ⚠️ Terza classe di trappola: stato di sessione a vita transazionale

Un solo file ha resistito, e aveva ragione lui.
`config/test-stradario-riclassificazione-unico` perdeva l'asserzione 11 —
«Guard attivo: cambio stradario_id senza manutenzione bloccato» — con:

```
caught: no exception, wanted: an exception
```

Il guard `trgfn_indirizzi_dettaglio_protect_update` lascia passare se è alzato il
flag `zeroerp.maintenance_indirizzi_dettaglio`. Quel flag lo alza
`maintenance.proc_bump_indirizzi_dettaglio` — e **non lo riabbassava mai**. Il
commento nel corpo diceva «solo per la sessione corrente», ma
`set_config(..., true)` vale per la **transazione**:

> **Ogni transazione che chiama quella procedura resta senza quella protezione
> per tutto ciò che segue.**

Non faceva danni per un motivo fragile: nessuno la chiama dentro una transazione
più grande — verificato, né `backend/` né altre funzioni del DB. Finché è una
`CALL` isolata in autocommit, la transazione muore subito e il flag con lei. Il
giorno in cui finisce dentro un'unità di lavoro più ampia — che è **esattamente
ciò che la regola dell'atomicità incoraggia** — il bypass resta acceso in
silenzio.

**Corretto**: changeSet **`20260806-20`** spegne il flag prima di uscire, con un
blocco `EXCEPTION` perché torni `off` anche se l'`UPDATE` fallisce — una porta
che si richiude solo quando tutto va bene non è una porta chiusa. Applicato:
`config` torna a **229/12/6, zero differenze**.

### 18.3 Le tre trappole della transazionalizzazione, in un posto solo

Chi affronterà il debito del §17.4 le incontrerà tutte e tre. In ordine di
insidiosità:

| | trappola | sintomo | rimedio |
| --- | --- | --- | --- |
| 1 | **Vincoli DIFFERITI** (§17.1) | il test diventa **verde**: ha smesso di verificare | `SET CONSTRAINTS ALL IMMEDIATE;` subito dopo `BEGIN;` |
| 2 | **`now()` congelato** (§16.2) | `CHECK` stretti su `data_fine > data_inizio` falliscono | `clock_timestamp()` dove serve «un istante dopo» |
| 3 | **Stato di sessione transazionale** (§18.2) | un guard smette di scattare | il codice che alza un flag deve riabbassarlo |

La prima è la peggiore perché **premia**: dà un verde in più e sembra un
progresso. Le altre due almeno rompono rumorosamente.

⚠️ E la 2 e la 3 non si vedono guardando il file: arrivano dai **trigger e dalle
procedure che il test attraversa**. Nel caso 2 il secondo colpo è arrivato da
`calcoli_tempo`, due tabelle più in là; nel caso 3 da una procedura di
manutenzione che il test chiama una volta sola.

### 18.4 Stato del §15.4

**Chiuso**: 426 file su 426 sono transazionali. Resta il debito del **§17.4** —
i 349 file che erano già transazionali non hanno mai avuto
`SET CONSTRAINTS ALL IMMEDIATE`, quindi non esercitano i 365 trigger differiti né
i 375 vincoli differiti. È materia a sé, e va deciso quanto scoperchiare in una
volta.

---

## 19. Il debito del §17.4: provato su un file, poi su uno schema intero (2026-08-06)

> Domanda posta: prima di aprire una passata su ~350 file, uno solo funziona? E
> lo stesso schema di intervento regge?

### 19.1 Un file, scelto perché dicesse qualcosa

Un file a caso non misura niente: serviva uno **verde oggi** e che scrivesse su
tabelle con trigger differiti, altrimenti la riga passa inosservata per
costruzione. Incrociando i file verdi con le **164 tabelle** che hanno trigger
`DEFERRABLE INITIALLY DEFERRED`, il candidato migliore è
`vendite/test-vw-dash-backlog-v1.sql`: verde, scrive su **nove** di quelle
tabelle, e `vendite` è lo schema con più differiti (150).

Aggiunta la riga: **14/14, exit 0, stabile su due giri**. Nessun costo, e da
adesso quei nove insiemi di controlli vengono davvero attraversati.

### 19.2 Poi uno schema intero, per avere un tasso

Un file solo non dice quanti diventeranno rossi. `config` è la prova giusta:
**53 trigger differiti** (il secondo schema dopo `vendite`) su appena 26 file.

Aggiunta a tutti quelli che ne erano privi — **19 file**:

| `config`, da owner | ok | ko | file rossi |
| --- | --- | --- | --- |
| prima | 229 | 12 | 6 |
| **dopo** | **229** | **12** | **6** |

**Zero differenze.** Il tasso di rossi nuovi, su un campione con alta densità di
differiti, è **zero su 19**.

### 19.3 ⚠️ Una correzione al §18: «426 su 426» era gonfiato

Il conteggio dei file transazionali usava `grep '^\s*BEGIN;'`, che accetta
l'indentazione. Ma `BEGIN;` compare anche **dentro le stringhe** passate a
`throws_ok`, indentato — e un file veniva contato come transazionale senza
esserlo:
`config/test-trgfn-prevent-deactivate-if-children-toponomastica.sql`.
Sistemato; ora i file con un `BEGIN;` a colonna 1 sono **426 su 426** davvero.

Il ricontrollo stretto ha anche mostrato **nove file con `BEGIN;` e senza
`ROLLBACK` esplicito**. Non è un difetto: la chiusura della sessione annulla la
transazione aperta, e diversi di essi lo dichiarano in testa («rollback implicito
a fine file»). Restano meno espliciti degli altri, e basta saperlo.

> ℹ️ È la stessa lezione del §14 su scala minore: **un conteggio vale quanto il
> criterio con cui è fatto**, e un `grep` permissivo risponde sempre di sì.

### 19.4 Il verdetto, e cosa resta

Il pattern regge: **stessa riga, stessa posizione, zero costo** su 20 file di
due schemi diversi, uno dei quali ad alta densità di vincoli differiti.

Restano **308 file**: `vendite` 167, `script` 54, `anagrafiche` 22, `documenti`
11, `rls` 11, `dbops` 11, `pratiche` 10, `ui` 8, `catalogo` 8, `pagamenti` 4,
`maintenance` 1, `shop` 1.

⚠️ **Zero su 19 non garantisce zero su 308.** Il campione è piccolo e `vendite` —
da solo più della metà del residuo — ha 150 trigger differiti su 57 tabelle, cioè
molte più occasioni di trovarne uno che oggi non viene esercitato. La passata va
fatta **schema per schema, misurando ogni volta**, e ogni rosso nuovo va letto:
sarà un difetto vero che la suite non stava vedendo, non un incidente da
aggirare. Ed è esattamente ciò che si vuole da questo cantiere.

---

## 20. `script`: la passata trova il primo vero limite del pattern (2026-08-06)

> Secondo schema del §19. `script` è stato scelto apposta come rodaggio — e ha
> restituito più di quanto ci si aspettasse.

### 20.1 Cosa è successo

54 file trattati (4 li avevano già). Dei 54, **30 scrivono su tabelle con trigger
differiti**: l'esposizione non viene dallo schema — `script` non ha tabelle
proprie con differiti — ma da **dove i suoi test scrivono**.

| `script`, da owner | ok | ko | file rossi |
| --- | --- | --- | --- |
| prima | 443 | 9 | 12 |
| dopo, tutti e 54 | 425 | 9 | **14** |
| **dopo, con 3 esclusi** | **443** | **9** | **12** |

**Tre file diventavano rossi**, due dei quali erano verdi:

```
test-fn-guard-soggetto-pf-pura   7/0 -> 1/0   Indirizzo obbligatorio mancante per soggetto …
test-fn-scope-ef-whitelist      10/0 -> 1/0   idem
test-fn-is-super-admin           7/1 -> 4/1   Padre non attivo: figlio attivo non consentito
```

### 20.2 ⚠️ Il limite: `IMMEDIATE` in testa vieta una deferralità VOLUTA

> ⚠️ **Diagnosi corretta al §22.1**: non e' che `IMMEDIATE` scatti «troppo
> presto». Misurato mettendo il controllo dove starebbe il `COMMIT`, quei file
> falliscono **lo stesso**: le fixture lasciano davvero dati non committabili.

`anagrafiche.soggetti` ha **tre guard `DEFERRABLE INITIALLY DEFERRED`** —
indirizzi, contatti, dati societari. Lì la deferralità non è un dettaglio
tecnico: è il **contratto del dominio**. Si crea il soggetto, poi il suo
indirizzo, e la completezza si verifica al `COMMIT`. È esattamente per questo che
`anagrafiche.fn_crea_soggetto_pf` può restituire un soggetto ancora incompleto:
il chiamante completa l'unità di lavoro prima di committare — ed è così che lo
usa il backend (`soggetti_repository.py`).

`SET CONSTRAINTS ALL IMMEDIATE` in testa pretende l'indirizzo **nell'istante
stesso dell'INSERT del soggetto**: vieta il pattern che il dominio ha scelto. Il
test non è sbagliato nel modo in cui costruisce — è sbagliato nel non finire.

⚠️ **Quindi nessuna delle due posizioni è universalmente giusta**, e conviene
dirlo chiaro prima di aprire il resto della passata:

| posizione | cosa rompe | perché |
| --- | --- | --- |
| **in testa** (§17.2) | test che sfruttano la deferralità per costruire in più passi | i controlli scattano prima che l'unità di lavoro sia completa |
| **in coda** (§17.2) | test che smontano i propri dati alla fine | i differiti scattano dopo il cleanup, su righe ormai cancellate |

La posizione in testa resta quella giusta per i file **resi** transazionali
(§16-§18): lì riproduce fedelmente il comportamento in autocommit, che era il
metro da conservare. Per i file **già** transazionali (§19) il metro non esiste —
non li ha mai esercitati nessuno — e la scelta va fatta guardando il file.

### 20.3 Cosa è rimasto e cosa no

**51 file su 54 tengono la riga a costo zero.** I tre esclusi la portano scritta
dentro, con la ragione e con il debito dichiarato:

> Senza la riga quei tre guard non vengono esercitati, e la fixture lascia un
> soggetto che l'applicazione non potrebbe committare. **La correzione vera è
> completare la fixture** (indirizzo + contatti): allora la riga si può
> rimettere, e il test verifica sul serio.

`script` torna a **443/9/12, zero differenze**.
`scripts/pgtap-baseline.sh script config`: **18 rossi su 84, nessuna
regressione**.

### 20.4 Il metodo per i 254 che restano

Il tasso non è più zero: su 54 file, **3 hanno reagito** (5,5%), e tutti e tre
per la stessa ragione — fixture che non completano l'unità di lavoro. Quindi:

1. **Applicare schema per schema**, mai in blocco.
2. **Ogni rosso nuovo va letto**, e la domanda è sempre la stessa: *il test sta
   costruendo qualcosa che l'applicazione potrebbe committare?* Se no, il difetto
   è nella fixture e va completata. Se sì, la riga in quel file va tolta o
   spostata.
3. **Non accogliere mai un verde**: è la lezione del §17.1, e vale al contrario
   anche qui — un file che resta verde con la riga ha davvero guadagnato
   copertura, ma solo se scriveva su tabelle con differiti. Trenta su 54, in
   `script`.

Restano **254 file**: `vendite` 167, `anagrafiche` 22, `documenti` 11, `rls` 11,
`dbops` 11, `pratiche` 10, `ui` 8, `catalogo` 8, `pagamenti` 4, `maintenance` 1,
`shop` 1. ⚠️ `vendite` è due terzi del residuo e ha 150 trigger differiti su 57
tabelle: è lì che ci si aspetta il grosso delle reazioni, e va tenuto per ultimo.

---

## 21. Tutti gli schemi tranne `vendite` — 87 file, e il limite si conferma (2026-08-06)

> Terza tappa del §19, su richiesta: `anagrafiche`, `documenti`, `rls`, `dbops`,
> `pratiche`, `ui`, `catalogo`, `pagamenti`, `maintenance`, `shop`. `vendite`
> tenuto per ultimo perché da solo è due terzi del residuo.

### 21.1 Il risultato

| schema | file trattati | esito |
| --- | --- | --- |
| `documenti` · `dbops` · `pratiche` · `ui` · `catalogo` · `pagamenti` · `maintenance` · `shop` | 47 | **zero differenze** |
| `anagrafiche` | 22 | **7 esclusi**, 15 tengono la riga |
| `rls` | 11 | **3 esclusi**, 8 tengono la riga |

**77 file su 87 tengono la riga a costo zero.** Le misure per schema tornano tutte
identiche al prima, e `scripts/pgtap-baseline.sh` sui dieci schemi: **46 rossi su
167, nessuna regressione**.

### 21.2 I dieci esclusi sono una causa sola

> ⚠️ **Diagnosi corretta al §22.1**: non e' che `IMMEDIATE` scatti «troppo
> presto». Misurato mettendo il controllo dove starebbe il `COMMIT`, quei file
> falliscono **lo stesso**: le fixture lasciano davvero dati non committabili.

Nove su dieci falliscono per i **guard differiti di completezza** su
`anagrafiche.soggetti` (indirizzi, contatti, dati societari) e su
`anagrafiche.istanze_utilities` (almeno un riferimento fra billing account, dati
precontrattuali, cliente).

Il caso più limpido è `test-fn-crea-soggetto-pf`, la cui **prima asserzione** si
chiama letteralmente *«fn_crea_soggetto_pf eseguita senza errori»* — e con
`IMMEDIATE` fallisce. Non c'è dimostrazione migliore che lì la deferralità sia
**di progetto**: la funzione del dominio restituisce un soggetto incompleto, e il
chiamante lo completa prima di committare.

Conferma il §20.2: **`IMMEDIATE` in testa vieta una deferralità voluta.** Non è
un difetto del pattern, è il suo perimetro.

Tutti e dieci portano dentro la ragione e il debito dichiarato: *senza la riga
quei guard non vengono esercitati, e la fixture lascia un soggetto (o un'istanza)
che l'applicazione non potrebbe committare; la correzione vera è completare la
fixture, e allora la riga si rimette.*

### 21.3 Un file instabile, segnalato

`anagrafiche/test-istanza-cliente-chain.sql` oscilla fra **6 e 0 asserzioni** fra
esecuzioni consecutive, a parità di codice. È rosso in baseline sia prima sia
dopo, quindi non cambia il verdetto dello schema — ma è **un rosso intermittente**,
cioè la cosa che il §6 indica come veleno per una baseline. Il file è
regolarmente transazionale (`BEGIN` + `ROLLBACK`, non lascia residuo) e contiene
**cinque `LIMIT 1`**: il sospetto è quello del §11.3, e va guardato quando si
aprirà quel cantiere.

### 21.4 Il tasso, aggiornato

| tappa | file | reagiti | tasso |
| --- | --- | --- | --- |
| §19 `config` + 1 file `vendite` | 20 | 0 | 0% |
| §20 `script` | 54 | 3 | 5,6% |
| §21 dieci schemi | 87 | 10 | 11,5% |
| **totale** | **161** | **13** | **8,1%** |

E le 13 reazioni sono **tutte la stessa cosa**: guard differiti di completezza
sui soggetti e sulle istanze. Nessuna ha rivelato un difetto di prodotto nuovo —
il che, dopo il §13.3 e il §18.2, è di per sé un'informazione.

### 21.5 Cosa resta

**`vendite`, 167 file.** È l'ultimo, ed è quello con più esposizione: 150 trigger
differiti su 57 tabelle. Il tasso dell'8% suggerirebbe una dozzina di reazioni,
ma la densità di `vendite` è più alta di tutte le altre e le sue fixture creano
soggetti e documenti in catena: è ragionevole aspettarsene di più.

⚠️ E resta il debito vero, che non è la riga ma ciò che la riga rivela: **13
fixture costruiscono dati che l'applicazione non potrebbe committare**. Completarle
è il lavoro che rende quei guard finalmente esercitati — e appartiene ai cantieri
di dominio, non a questo.

---

## 22. `vendite`: il tasso più basso di tutti — e la diagnosi va corretta (2026-08-06)

> Ultimo schema. Era anche il più esposto: **133 file su 167 scrivono su tabelle
> con trigger differiti**, e `vendite` ne ha 150 su 57 tabelle.

### 22.1 ⚠️ Prima la correzione, perché cambia ciò che è scritto ai §20.2 e §21.2

Lì avevo concluso che `SET CONSTRAINTS ALL IMMEDIATE` **in testa** fosse troppo
severo: scattando a ogni istruzione, vieterebbe la costruzione in più passi che
il dominio consente (crea il soggetto, poi il suo indirizzo). Vero sul *quando*,
ma **sbagliato sul merito**.

Misurato spostando il controllo **in coda**, cioè esattamente dove starebbe il
`COMMIT`:

```
test-fn-crea-soggetto-pf         1..9   ok=9  ko=0   exit=3   Indirizzo obbligatorio mancante…
test-genera-scadenze-lotto-v1    1..11  ok=11 ko=0   exit=3   Lotto 106: 2 fattura/e con stato…
test-snapshot-indirizzi-lotto-v1 1..12  ok=12 ko=0   exit=3   Lotto 2900: 1 fattura/e…
```

Eseguono **tutto il piano** e poi falliscono lo stesso. Quindi non è una
questione di anticipo: **quelle fixture lasciano dati che un `COMMIT` vero
rifiuterebbe**. La deferralità serviva solo a non farlo vedere.

Conseguenza pratica: i **14 file esclusi** (§20, §21, §22) non aspettano un
aggiustamento del pattern. Aspettano che qualcuno **completi l'unità di lavoro**
che hanno lasciato a metà — l'indirizzo del soggetto, il riferimento
dell'istanza, l'allineamento fra lotto e fatture.

### 22.2 Il risultato su `vendite`

| `vendite`, da owner | ok | ko | file rossi |
| --- | --- | --- | --- |
| prima | 1749 | 16 | 24 |
| dopo, tutti e 167 | 1727 | 16 | 26 |
| **dopo, con 2 esclusi** | **1749** | **16** | **24** |

**165 file su 167 tengono la riga a costo zero: il tasso più basso di tutta la
passata (1,2%)**, con l'esposizione più alta. L'ipotesi era giusta: `vendite` è
più recente, e le sue fixture completano quasi sempre ciò che iniziano.

`scripts/pgtap-baseline.sh vendite`: **24 rossi su 175, nessuna regressione**.

I due esclusi introducono un'invariante nuova, diversa dalla completezza dei
soggetti: **coerenza fra lo stato fiscale del lotto e quello delle sue fatture**
(`E_LOTTO_FATTURE_STATO_INCOERENTE`, guard
`trg_fatturazione_lotti_def_guard_stato_fatture_coerente_upd` e
`trg_fatture_def_guard_stato_lotto_coerente_ins_upd`).

### 22.3 Il quadro completo della passata

| tappa | file | reagiti | tasso |
| --- | --- | --- | --- |
| §19 `config` + 1 di `vendite` | 20 | 0 | 0 % |
| §20 `script` | 54 | 3 | 5,6 % |
| §21 dieci schemi | 87 | 10 | 11,5 % |
| §22 `vendite` | 167 | 2 | **1,2 %** |
| **totale** | **328** | **14** | **4,3 %** |

**Il debito del §17.4 è chiuso**: tutti i file transazionali della suite ora
forzano i vincoli differiti, tranne ~~15~~ **14** che portano dentro la ragione e
il debito.

> ⚠️ **Correzione (2026-08-07): erano 14, non 15.** Ricontato sul repo:
> `426 = 409` file con la riga a colonna zero `+ 14` esclusi con nota `+ 3` in
> cui il vincolo differito è il soggetto del test (§22.5). Il «15» nasceva dal
> contare uno dei tre del §22.5 fra gli esclusi.

Le 14 reazioni sono di **tre invarianti**, tutte di completezza o coerenza:

| invariante | file |
| --- | --- |
| `anagrafiche.soggetti`: indirizzi, contatti, dati societari | 10 |
| `anagrafiche.istanze_utilities`: almeno un riferimento | 2 |
| `vendite`: stato lotto ↔ stato fatture | 2 |

### 22.4 Cosa resta

**Completare le 14 fixture.** Non è lavoro di questo brief: ogni file appartiene
al dominio che collauda, e il difetto è sempre lo stesso — *il test costruisce
qualcosa che l'applicazione non potrebbe salvare*. Quando una viene completata,
si toglie la nota e si rimette la riga: da quel momento il guard è esercitato.

⚠️ **E questi 14 sono un campione, non l'inventario.** Dicono quante fixture
*incontrano* un vincolo differito lasciandolo insoddisfatto; non dicono quante
altre costruiscono dati incompleti su invarianti non presidiate da un differito.

### 22.5 ✅ Le tre invarianti hanno già test dedicati — il debito è più piccolo di così

Chiudendo il conto della copertura, **tre file non rientravano né fra i 409 con
la riga né fra i 14 esclusi**:

```
anagrafiche/test-soggetti-indirizzi-required.sql
anagrafiche/test-soggetti-ruoli-indirizzi-required.sql
anagrafiche/test-trgfn-istanze-utilities-require-utility-dichiarata.sql
```

Contengono **quattro `SET CONSTRAINTS ALL IMMEDIATE` ciascuno**, ma dentro le
stringhe di `throws_ok`: sono i test **il cui soggetto È il vincolo differito**.
Lo fanno scattare nel punto scelto e asseriscono che respinga — che è la tecnica
giusta, ed era già lì.

| test dedicato | esito |
| --- | --- |
| `test-soggetti-ruoli-indirizzi-required` | **6/6 verde** |
| `test-trgfn-istanze-utilities-require-utility-dichiarata` | 3/4 (1 rosso, in baseline) |
| `test-soggetti-indirizzi-required` | muto (in baseline, `ERRORE_FIXTURE`) |

Quindi **le invarianti non erano scoperte**: quello che mancava era che le
*altre* fixture, quelle che le incontrano di passaggio, le rispettassero. È una
distinzione che cambia la priorità del §22.4 — il debito è di igiene delle
fixture, non un buco di collaudo su un vincolo di dominio.

> ℹ️ E suggerisce la tecnica per completare i 14: non serve la riga in testa.
> Basta un `SET CONSTRAINTS ALL IMMEDIATE` **nel punto in cui l'unità di lavoro
> è completa**, come fanno già questi tre.

---

## 23. Il brief NON è chiuso: cosa manca, e cosa vale la pena (2026-08-07)

> Bilancio richiesto a fine cantiere. Verificato, non ricordato.

### 23.1 L'obiettivo del brief non è ancora raggiunto

`scripts/testpgtap.sh` legge tuttora `db/internal.env` e si connette come
**`titodb`, l'owner**. Quindi la frase del §1 è ancora vera: *nessuno dei 426
test esercita una policy RLS*, e il giorno in cui si attiva `FORCE ROW LEVEL
SECURITY` la suite si rompe tutta insieme.

Tutto ciò che è stato fatto dal §11 al §22 è **preparazione**: la riga di
contesto ovunque, la transazionalità, i vincoli differiti forzati, tre difetti di
prodotto trovati e corretti. Ma i **passi 3 e 4 del §8.3** — cambio utente al
runner e ribaselinatura — sono ancora da fare, ed è lì che il brief si chiude.

### 23.2 Il divario, misurato oggi

| | ok | ko | file rossi |
| --- | --- | --- | --- |
| owner (com'è il runner) | 3853 | 74 | 88 |
| utente applicativo | 3584 | 69 | 123 |

**Delta = 36 file** rossi solo sotto l'utente applicativo — erano **51** al §10.3
e **65** al §13.1. Ripartiti: `vendite` 12, `pratiche` 9, `rls` 7, `dbops` 3,
`ui` 2, `anagrafiche`/`script`/`maintenance` 1.

### 23.3 I 36, in quattro famiglie

**A — Richiedono l'owner per natura: 12 file.** `ALTER TABLE … FORCE ROW LEVEL
SECURITY` ~~(6 in `rls/`, più `commesse`, `preventivi`, `promo_articoli`,
`sospensioni`)~~ e `CREATE TABLE dbops.…` (3, strumenti DBA). **Non sono difetti
e non lo diventeranno.**

> ⚠️ **Correzione (2026-08-07): la composizione qui sopra è sbagliata**, il
> totale 12 era giusto per caso. `commesse` e `preventivi` erano **già** dentro i
> 6 di `rls/`, e mancava `vendite/test-annulla-commessa-attivita-v1`.
> L'inventario verificato, con la causa misurata file per file, è al **§24.2**.

**B — Il test scrive dove l'applicazione non scrive: 8 file.** Sei su
`pratiche.workflow_definizioni`, due su
`pratiche.template_flussi_avanzamento_proiezione`, entrambe `SELECT`-only per
scelta. Cantiere definizioni versionate.

**C — RLS in scrittura, finalmente esercitata: 7 file.** Cinque su
`vendite.commesse`, due su `vendite.fatture_righe`. **Sono i più interessanti di
tutti**: è l'unico posto dove una policy viene messa alla prova, cioè il motivo
per cui questo brief esiste.

**D — Permessi mirati e casi singoli: 9 file.** GRANT su `indirizzi_dettaglio`,
`pratiche_sorgenti`, `dashboard_definizione`, `preventivi`; i 2 `ui` del §12.3;
`test-vw-dash-aperto-v1` (già escluso e documentato); 3 che falliscono per
asserzione o piano.

### 23.4 Cosa vale la pena, in ordine

1. **La famiglia A — la decisione di design.** È l'unico vero blocco al cambio di
   runner: dodici file che devono girare da owner. Serve una **marcatura nel
   file** e un runner che sappia leggerla. Piccolo, e sblocca tutto il resto.
2. **La famiglia C — i 7 file con RLS in scrittura.** Massimo valore
   informativo: è lì che si scopre se una policy è scritta bene. Ogni rosso lì è
   una domanda vera, non un incidente di fixture.
3. **Il cantiere `LIMIT 1`** (§11.3): **133 siti a rischio ALTO su 170 file**.
   Va aperto **prima** della ribaselinatura, altrimenti si registra come «noto»
   un pezzo di fortuna. È il debito più grande rimasto in assoluto.
4. **Le 14 fixture incomplete** (§22.4) e le famiglie **B** e **D**: lavoro dei
   cantieri di dominio, non di questo.
5. **Poi, e solo poi**, i passi 3-4 del §8.3: una riga in
   `scripts/testpgtap.sh` e `pgtap-baseline.sh --update`.

⚠️ **Un rosso intermittente da guardare prima di ribaselinare**:
`anagrafiche/test-istanza-cliente-chain.sql` oscilla fra 6 e 0 asserzioni a
parità di codice (§21.3). Registrarlo com'è significherebbe fotografare un pezzo
di fortuna.

### 23.5 Cosa questo cantiere ha già restituito

Vale la pena metterlo nero su bianco, perché non era l'obiettivo dichiarato:

* **tre difetti di prodotto**, trovati e corretti — il guard che non diceva mai
  la sua ragione (§13.3), il bootstrap che impediva al ruolo applicativo di
  creare un tipo di prestazione (§15.1), la manutenzione che lasciava il bypass
  acceso per tutta la transazione (§18.2);
* **tre trappole documentate** (§18.3) e una quarta (§22.1);
* **due errori di misura** riconosciuti e corretti (§14, §19.3), che è la ragione
  per cui i numeri di adesso valgono qualcosa.

---

## 24. Riapertura: la famiglia A non era un ostacolo, era una tecnica (2026-08-07)

> Cantiere riaperto sulla priorità 1 del §23.4. Tutto quello che segue è
> **misurato oggi contro il DB**, non ripreso dal testo.

### 24.1 Il divario si riconcilia esattamente

I 36 file del §23.2 rieseguiti uno per uno come `zeroerp_app`, con
`ON_ERROR_STOP=1`, catturando l'errore vero di ciascuno. Le quattro famiglie
tornano al file: **12 + 7 + 8 + 9 = 36**, senza residui.

| famiglia | messaggio che la identifica | file |
| --- | --- | --- |
| **A** richiede l'owner | `bisogna essere proprietari della tabella` (9) · `permesso negato per lo schema dbops` (3) | 12 |
| **C** RLS in scrittura | `la nuova riga viola la regola di sicurezza per riga` | 7 |
| **B** GRANT mancante di dominio | `permesso negato per la tabella` (`workflow_definizioni` 6, `template_flussi_avanzamento_proiezione` 2) | 8 |
| **D** singoli | 4 GRANT mirati, 3 asserzioni, 1 GUC emittente, 1 binding AD_HOC | 9 |

La famiglia **C** conferma il §23.3 alla lettera: 5 su `vendite.commesse`, 2 su
`vendite.fatture_righe`.

### 24.2 ⚠️ La composizione della famiglia A al §23.3 era sbagliata

Il totale (12) era giusto; l'elenco no. `commesse` e `preventivi` erano **già**
dentro i sei di `rls/`, e mancava `vendite/test-annulla-commessa-attivita-v1`.
L'inventario verificato:

| file | DDL che richiede l'owner |
| --- | --- |
| `rls/test-rls-commesse-ef-whitelist-write` | `ALTER TABLE vendite.commesse` + `commesse_attivita` |
| `rls/test-rls-ddt-ef-whitelist-write` | `ALTER TABLE vendite.ddt` |
| `rls/test-rls-resi-ef-whitelist-write` | `ALTER TABLE vendite.resi` |
| `rls/test-rls-preventivi-ef-whitelist-write` | `ALTER TABLE vendite.preventivi` |
| `rls/test-rls-fatture-satelliti-functional` | `ALTER TABLE` sui due satelliti |
| `rls/test-rls-viste-fattura-invarianza` | `ALTER TABLE` sui due satelliti |
| `pratiche/test-sospensioni-anti-overlap-data-futura` | `DROP CONSTRAINT` + `dbops.fn_apply_automazione_overlap()` |
| `vendite/test-annulla-commessa-attivita-v1` | `ADD/DROP CONSTRAINT` temporaneo su `commesse_attivita_log` |
| `vendite/test-promo-articoli-guard-data-driven-v1` | `DISABLE TRIGGER` del guard sotto test |
| `dbops/test-cleanup-framework` | `CREATE TABLE dbops.tst_cleanup_framework` |
| `dbops/…overlap-key-expressions-v1` | `CREATE TABLE dbops._test_overlap_kx` |
| `dbops/…overlap-where-predicate-v1` | `CREATE TABLE dbops._test_overlap_wp` / `_tot` |

### 24.3 E soprattutto: quei test **devono** girare da owner

Non è una limitazione da aggirare, è la tecnica con cui sono scritti. Lo dice
l'intestazione di `rls/test-rls-preventivi-ef-whitelist-write.sql`, da prima di
questo cantiere:

> *ENABLE + FORCE locale alla tx (owner titodb non-superuser → soggetto).*

**È il `FORCE` a rendere l'owner soggetto alle policy**, e l'identità la simulano
le GUC `app.ruolo_applicativo` / `app.current_user_id`, non il ruolo di
connessione. Girarli come `zeroerp_app` non li renderebbe più severi: li
romperebbe all'`ALTER TABLE`, prima della prima asserzione.

Stesso ragionamento per gli altri: la fault injection di
`test-annulla-commessa-attivita-v1` aggiunge un CHECK temporaneo per dimostrare
che l'INSERT del log fallisce davvero — senza DDL quel ramo non è raggiungibile;
i tre `dbops` registrano una tabella finta nel registry e l'automazione ci applica
sopra un EXCLUDE **vero**, quindi una TEMP non è un'alternativa.

⚠️ **Uno solo dei dodici è discutibile**:
`vendite/test-promo-articoli-guard-data-driven-v1` fa `DISABLE TRIGGER` del guard
che sta collaudando, per piantare le fixture nei tre stati che il guard vieta. Lì
il DDL è una scorciatoia di fixture, non lo strumento del collaudo: si toglierebbe
riscrivendo le fixture. È scritto nel marcatore del file, così non si perde.

### 24.4 La decisione: marcatore nel file, e il runner che lo legge

Fra marcatore nel file, manifesto centrale e convenzione di nome/cartella, si è
scelto il **marcatore nel file**: la verità sta accanto al test, lo segue nelle
rinomine, si legge dove serve e si vede in diff. Un manifesto separato diverge
dai test; rinominare i file avrebbe fatto churn su baseline e storia, e rotto il
perimetro per schema di `pgtap-baseline.sh`.

```sql
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgtap-runner: owner
-- pgtap-runner-motivo: ALTER TABLE vendite.ddt ENABLE + FORCE ROW LEVEL SECURITY,
--   locale alla transazione: e' il FORCE a rendere l'owner soggetto alle policy.
```

**Il motivo è obbligatorio**: senza, il runner esce con codice 4 invece di
concedere l'eccezione. È il presidio contro l'uso che ci si deve aspettare —
mettere il marcatore per far sparire un permesso mancante.

### 24.5 Cosa è stato applicato

**`scripts/testpgtap.sh`** — nuova variabile `PGTAP_RUNNER`:

* `owner` (**default, invariato**) — l'utente dell'env file, com'è sempre stato;
* `app` — `PGTAP_APP_USER` (default `zeroerp_app`), password da `~/.pgpass`.
  ⚠️ La `PGPASSWORD` dell'env file viene **tolta apposta**: senza l'`unset` si
  tenterebbe la password dell'owner sull'utente applicativo.

Un file marcato resta sull'owner anche con `PGTAP_RUNNER=app`, e il runner lo
dichiara su `stderr` con la sua ragione — l'eccezione si vede a ogni corsa,
non si dimentica.

**`scripts/pgtap-baseline.sh`** — la baseline adesso **registra con che utente è
stata presa**, prima riga `# pgtap-runner: <owner|app>`, e **rifiuta** sia il
confronto sia l'aggiornamento parziale se la corsa gira con un utente diverso.

> Vale la pena dirlo esplicitamente: **questo è il difetto del §1 chiuso alla
> radice.** Il brief nasce perché runner e baseline giravano come utenti diversi
> e nessuno se ne accorgeva. Da adesso non è più possibile: o i due metri
> coincidono, o lo script si ferma e lo dice.

Le baseline esistenti non hanno l'intestazione e vengono lette come `owner`, che
era l'unico modo di girare la suite: nessuna rottura.

**I 15 file marcati** — i 12 della famiglia A più tre che oggi non compaiono nel
divario ma si romperebbero comunque alla commutazione:
`rls/test-rls-ordini-multipolicy` e `rls/test-rls-fatture-ef-whitelist-functional`
(rossi da entrambi gli utenti, quindi invisibili nel delta) e
`vendite/test-vw-dash-aperto-v1` (rosso sotto app per la GUC emittente, che si
ferma prima di arrivare al suo `ALTER TABLE`).

> Il censimento è **esaustivo, non aneddotico**: cercati su tutti i 426 file
> `ALTER TABLE`, `CREATE TABLE`, `CREATE/DROP INDEX`, `GRANT`, `REVOKE`,
> `COMMENT ON`, `TRUNCATE`, `SET ROLE`, `SET SESSION AUTHORIZATION`,
> `ALTER SYSTEM`, `CREATE EXTENSION`. I 40 candidati si riducono a 15: tutti i
> `CREATE OR REPLACE FUNCTION` sono `pg_temp.*`, e gli `ALTER TABLE`/`TRUNCATE`
> restanti sono su tabelle temporanee. Il ruolo applicativo li fa senza problemi.

### 24.6 La verifica, col metodo di sempre

Suite intera due volte, **passando dal runner ufficiale** perché il marcatore
venisse onorato come in una corsa vera.

| corsa | file rossi | atteso |
| --- | --- | --- |
| owner (default, com'è il runner oggi) | **92** | 88 + 4 (v. sotto) |
| `PGTAP_RUNNER=app` | **114** | 123 − 13 marcati + 4 |

**Divario: da 36 a 23 file.** I 13 che escono sono i 12 della famiglia A più
`vendite/test-vw-dash-aperto-v1`. I 15 marcati danno **esito identico** con
entrambi i runner, file per file: il marcatore funziona e non ha spostato nulla.

I 23 che restano sono esattamente le famiglie **B (8) + C (7) + D (8)**: nessun
residuo, nessuna sorpresa.

> ⚠️ **I 4 rossi in più da owner NON sono di questo cantiere.** Sono
> `vendite/test-{preventivi,ordini,ddt,contratti}-righe-componenti-v1`, e vengono
> dal commit `75fd25ed8` («Quarto lato»): i tre codici nuovi hanno cambiato il
> **testo** del messaggio, e quei test asseriscono sul testo con
> `throws_like('%riga preventivo non trovata%')`. Il messaggio ora è
> `Riga preventivo 2147483647 non trovata.` — non combacia né per la maiuscola né
> perché l'id si infila in mezzo alla frase. Il nome del test cita ancora
> `E_PARAMETRO_INVALIDO`, che non è più il codice sollevato.
> Annotato qui perché senza questa riga i 92 di oggi contro gli 88 di ieri
> sembrerebbero una regressione nostra.
>
> ✅ **Sanati il 2026-08-07 sera** — `scripts/pgtap-baseline.sh vendite`: 24
> rossi su 175, tutti noti, nessuna regressione.
>
> ⚠️ **E qui va corretta un'ipotesi sbagliata fatta poche ore prima**: «la
> riparazione giusta è asserire su SQLSTATE + codice». **In questo progetto non
> funziona.** Tutti i raise di `script.fn_log_and_raise_error` condividono
> `SQLSTATE P0001`, quindi il codice **non discrimina**: `throws_ok` con `P0001`
> accetterebbe qualunque errore di dominio, compreso quello sbagliato. La
> convenzione del repo — scritta in
> `catalogo/test-guard-iva-reactivation-v1.sql:150` da giugno — è `throws_like`
> sulla **frase stabile** del messaggio.
>
> La riparazione applicata è quindi il pattern nuovo, **con l'accortezza che
> mancava**: saltare l'id interpolato. `'%Riga DDT %non trovata%'`, non
> `'%riga DDT non trovata%'`. Il messaggio è `Riga DDT %s non trovata.`: il
> pattern vecchio si spezzava sia sulla maiuscola sia sull'id in mezzo alla
> frase. Ogni blocco porta ora la ragione scritta, così non si ripete.
>
> ✅ **Difetto adiacente, corretto**: le righe 899/900/901 di
> `messaggi_errore.csv` descrivevano il guard come
> `vendite.fn_fn_ddt_riga_componenti_init` — **`fn_fn_`**, una funzione che non
> esiste (solo la 897 era scritta bene). Corretto nel CSV, che è la sede: il
> mirror `20260614-08` è `runOnChange` + `validCheckSums: ANY`.
>
> ✅ **Chiusi anche gli altri due rilievi sullo stesso testo (2026-08-07 sera)**,
> registrati al **§23.3 del brief terzo lato**, che è il loro cantiere.
>
> 1. **Tre codici dicevano tutti «Sesto e ultimo dei punti trovati dalla
>    lente»** — 899, 900, 901: una riga copiata su tre. La deduzione tentata qui
>    (`899 = quarto`, `900 = quinto`) **era sbagliata**: leggendo il §23 del brief
>    terzo lato, i tre non stanno in fila — sono **le gemelle trovate insieme
>    nella seconda passata**, e «la prima passata ne aveva vista una» (§23.1).
>    Il testo ora lo dice, e separa il rimando: §19.4 il difetto, §23 le gemelle.
> 2. **Il rimando «Brief terzo lato §19.4» non era rotto: la mia copia era
>    indietro.** La sezione è stata scritta dal BE con `e83d44412`, dopo i commit
>    che avevano introdotto i codici — un rimando in avanti, non un errore.
>    ⚠️ Vale come promemoria: prima di dichiarare morto un riferimento, guardare
>    se il repo locale è aggiornato.

### 24.7 Cosa resta, aggiornato

Il §23.4 resta valido, meno il punto 1 che è chiuso:

1. ~~Famiglia A — la decisione di design~~ ✅ **fatta** (§24.4, §24.5).
2. **Famiglia C — i 7 file con RLS in scrittura.** Sono il motivo per cui il
   brief esiste: l'unico posto dove una policy viene messa alla prova. Cinque si
   fermano su `vendite.commesse`, due su `vendite.fatture_righe`, tutti con
   `la nuova riga viola la regola di sicurezza per riga`. Ogni rosso lì è una
   domanda vera: *la policy è scritta male, o la fixture scrive dove
   l'applicazione non scriverebbe?*
3. **Il cantiere `LIMIT 1`** (§11.3): 133 siti a rischio ALTO su 170 file.
   Sempre **prima** della ribaselinatura.
4. **Famiglia B (8)** e **D (8)**, più le **14 fixture** del §22.4: lavoro dei
   cantieri di dominio.
5. **Poi, e solo poi**, la commutazione: il default di `PGTAP_RUNNER` da `owner`
   ad `app` — **una riga sola, adesso** — e
   `PGTAP_RUNNER=app scripts/pgtap-baseline.sh --update` sull'intera suite.

⚠️ Restano in piedi le due avvertenze del §23.4: il rosso intermittente di
`anagrafiche/test-istanza-cliente-chain.sql` (§21.3) e il fatto che ribaselinare
prima del cantiere `LIMIT 1` fotografa un pezzo di fortuna.

---

## 25. Punto della situazione (2026-08-07, sera)

> Verificato, non ricordato. Da qui riparte chi apre il brief domani.

### 25.1 I numeri, corretti dopo la sanatoria dei 4

I 4 `vendite/*-righe-componenti-v1` erano rossi con **entrambi** i runner
(§24.6): sanandoli calano tutti e due i lati della stessa quantità, e il divario
non si muove.

| | alla misura del §24.6 | ora |
| --- | --- | --- |
| owner (default) | 92 | **88** |
| `PGTAP_RUNNER=app` | 114 | **110** |
| **divario** | **23** | **23** |

Verificato file per file: i 4 sono verdi da owner **e** da utente applicativo.
Gli 88 sono lo stesso numero da cui il cantiere era partito il 2026-08-06.

### 25.2 Cosa c'è, e funziona

* **Marcatore `-- pgtap-runner: owner` su 15 file**, con `-- pgtap-runner-motivo:`
  obbligatorio (senza, il runner esce 4).
* **`PGTAP_RUNNER=owner|app`** in `scripts/testpgtap.sh`. **Default ancora
  `owner`**: nessun cambio di comportamento per chi lancia i test oggi.
* **`scripts/pgtap-baseline.sh` registra l'utente** nella prima riga della
  baseline e **rifiuta confronto e update parziale** se la corsa gira con un
  altro utente — *prima* di eseguire, in 8 ms invece che dopo 7 minuti.
* Tutto committato in `b3948da09`.

ℹ️ `db/pgtap/baseline-rossi.tsv` **non ha ancora la riga `# pgtap-runner:`**, e
va bene: si legge come `owner`, che è ciò che era. La scriverà il primo
`--update`.

### 25.3 Il residuo, in una riga ciascuno

| # | cosa | dimensione | perché in quest'ordine |
| --- | --- | --- | --- |
| 1 | **Famiglia C — RLS in scrittura** | 7 file | è il motivo per cui il brief esiste: l'unico posto dove una policy viene messa alla prova |
| 2 | **Cantiere `LIMIT 1`** | 133 siti ALTO su 170 file | va **prima** della ribaselinatura, o si registra come «noto» un pezzo di fortuna |
| 3 | **Famiglia B (8) + D (8)** e le 14 fixture del §22.4 | 16 + 14 | lavoro dei cantieri di dominio, non di questo |
| 4 | **La commutazione** | una riga | default `app` + `PGTAP_RUNNER=app pgtap-baseline.sh --update` sull'intera suite |

⚠️ Prima del punto 4, guardare `anagrafiche/test-istanza-cliente-chain.sql`:
oscilla fra 6 e 0 asserzioni a parità di codice (§21.3).

### 25.4 La prossima mossa, concreta

**Famiglia C, i 7 file.** Tutti si fermano su
`la nuova riga viola la regola di sicurezza per riga`, cinque su
`vendite.commesse` e due su `vendite.fatture_righe`:

```
vendite/test-drop-uq-commesse-attivita-src-uid-partial-v1.sql   commesse
vendite/test-fn-list-preventivi-da-pushare-righe-ids-v1.sql     commesse
vendite/test-guard-uscita-commessa-v1.sql                       commesse
vendite/test-vw-dash-fatturazione-v1.sql                        commesse
vendite/test-vw-preventivi-smistamento-v1.sql                   commesse
vendite/test-lista-commessa-attivita-fatturata-v1.sql           fatture_righe
vendite/test-numerazione-guard-coerenza-v1.sql                  fatture_righe
```

La domanda da farsi su ognuno è **una sola, e ha due risposte opposte**: *la
policy è scritta male* (difetto di prodotto, come i tre già trovati) *oppure la
fixture scrive dove l'applicazione non scriverebbe* (difetto di test)? Le due si
distinguono guardando **chi** scrive quella riga nel percorso reale — non
costruendo una fixture che confermi il ramo, che è la trappola di
[[feedback_verifica_dal_percorso_reale]].

Si aprono con:

```bash
PGTAP_RUNNER=app scripts/testpgtap.sh db/vendite/test-guard-uscita-commessa-v1.sql
```

---

## 26. Famiglia C — la RLS in scrittura, finalmente esercitata (2026-08-07)

> È il motivo per cui il brief esiste: i sette file dove una policy viene messa
> alla prova. **Non erano una cosa sola: sono quattro cause distinte**, e solo
> misurandole una per una si vede quali sono difetti di test e quali no.

### 26.1 Il metodo, prima del risultato

La domanda su ogni rosso era sempre la stessa e con due risposte opposte: *la
policy è scritta male, oppure la fixture scrive dove l'applicazione non
scriverebbe?* Si risponde **dal percorso reale**, mai dalla fixture
([[feedback_verifica_dal_percorso_reale]]): chi scrive davvero quella riga, e con
quali valori. Tre misure hanno deciso tutto:

* **`vendite.commesse`: 58 righe in essere, ZERO senza emittente.** La colonna è
  l'unica nullable fra tutti i documenti (preventivi, ordini, ddt, resi, fatture
  la hanno `NOT NULL`), ma nessuna riga vive in quello stato.
  ⚠️ Conteggio fatto **da owner**: su tabella con RLS lo zero da utente
  applicativo sarebbe fail-closed, non un dato ([[feedback_conteggi_rls_zero_non_errore]]).
* **L'unico scrittore reale è `vendite.fn_get_or_create_commessa`**, e l'emittente
  lo risolve **sempre**: `COALESCE(p_emittente_soggetto_ruolo_id,
  anagrafiche.fn_get_emittente_fiscale_id(p_billing_account_id))`. Non è
  `SECURITY DEFINER`, quindi gira soggetta alla RLS come chiunque.
* **Il BE non scrive mai testata e righe fattura insieme**: in
  `pipeline_repository.py` ci sono 2 `INSERT INTO vendite.fatture_righe` e
  **zero** `INSERT INTO vendite.fatture` — la fattura nasce in uno step della
  pipeline, le righe in quello dopo.

### 26.2 ⭐ Il rilievo che vale più di tutti: la CTE che non può passare

Due file (`test-lista-commessa-attivita-fatturata-v1`,
`test-numerazione-guard-coerenza-v1`) creavano fattura **e** righe dentro **una
sola CTE**. Esperimento controllato, stessi dati e stesso operatore:

| | esito |
| --- | --- |
| fattura, poi righe — **due statement** | ✅ passa |
| fattura + righe — **una CTE** | ❌ `viola la regola di sicurezza per riga` |

**La causa**: le CTE che scrivono condividono tutte la **stessa snapshot**.
`script.fn_scope_ef_whitelist_via_fattura` è `STABLE` e cerca la fattura in
`vendite.fatture`, dove la riga appena inserita **non è ancora visibile**: l'SR
risolve a `NULL` e il `WITH CHECK` nega fail-closed.

> ⚠️ **È una mina, non un difetto — ma va saputa.** La policy fa la cosa giusta
> in ogni percorso che l'applicazione usa davvero. Ma chiunque scriva un giorno
> un `INSERT` genitore+figlio in una CTE sola — pattern SQL del tutto
> legittimo — otterrà una violazione RLS che **non parla della causa vera**.
> Non si corregge la policy: la si documenta, e la si trova qui.

Riparate spezzando in due statement, che è anche la forma più fedele al BE. Il
secondo file è passato da `LANGUAGE sql` (una CTE) a `LANGUAGE plpgsql` (due
`INSERT`), perché in SQL puro le due scritture non si possono separare.

### 26.3 Le quattro cause, e cosa si è fatto

| # | causa | file | verdetto |
| --- | --- | --- | --- |
| **C1** | la fixture **omette** l'emittente | 3 | **difetto di fixture** — l'applicazione lo valorizza sempre |
| **C2** | la fixture **azzera** l'emittente di proposito | 1 | marcatore, e una domanda di prodotto (§26.4) |
| **C3** | la fixture scrive su un **secondo emittente** di proposito | 1 | la policy fa il suo mestiere: marcatore |
| **C4** | testata e righe nella **stessa CTE** | 2 | **difetto di fixture**, con la mina del §26.2 sotto |

**C1** — nuovo helper `script.fn_pgtap_emittente_sr_operatore()`
(`20260807-10`), terzo della famiglia dopo `20260805-27` e `-38`. Le tabelle
documento usano **due convenzioni** per l'emittente (`emittente_fiscale_id` per
preventivi/ordini/ddt/resi, `emittente_soggetto_ruolo_id` per
commesse/fatture/lotti): la compagna risponde alla prima, questa alla seconda, e
le fixture smettono di ripetere la sotto-select di traduzione.

**C2 e C3** — marcatore `-- pgtap-runner: owner`, e con esso una **seconda
categoria ammessa**, scritta nell'intestazione di `scripts/testpgtap.sh`:

> 1. il test **fa DDL** che il ruolo applicativo non può e non deve fare;
> 2. **la fixture costruisce un mondo che l'operatore non deve vedere.**

Sono la stessa natura: il test allestisce la scena e poi la osserva sotto
restrizione. ⚠️ Quello che **non** è un'eccezione resta scritto accanto: un
permesso negato che l'applicazione non incontrerebbe mai è un difetto di fixture
o di policy, e il marcatore lo nasconderebbe invece di risolverlo.

I marcati passano da 15 a **17**.

### 26.4 ⚠️ Una domanda di prodotto che resta aperta

`vendite.commesse.emittente_soggetto_ruolo_id` è nullable, ma:

* nessuna delle 58 righe in essere è `NULL`;
* l'unico scrittore lo risolve sempre;
* **con la RLS attiva nessun operatore può portarlo a `NULL`** né creare una riga
  che ce l'abbia — la policy nega, e non ha un ramo per l'assenza.

Quindi il ramo «emittente mancante» di
`vendite.fn_check_commessa_pronta_fatturazione` è raggiungibile **solo da un
ruolo `BYPASSRLS`** (batch, automazioni) o dall'owner, mai da un operatore. Non è
un ramo morto — è un ramo che appartiene a un altro attore.

Le due domande, per quando si aprirà il cantiere giusto:

1. la colonna dovrebbe essere `NOT NULL`, come lo è su tutti gli altri documenti?
   Attenzione: `fn_get_or_create_commessa` può ancora produrre `NULL` se il
   billing account non risolve un emittente;
2. se resta nullable, la policy dovrebbe avere un ramo esplicito per l'assenza —
   e quale? Oggi una commessa senza emittente sarebbe **invisibile a tutti gli
   operatori**, il che è coerente col fail-closed ma va deciso, non subìto.

### 26.5 ✅ Il migrate del 2026-08-07 ha sciolto anche il dubbio del §28.1 dell'altro brief

`make db-migrate` ha applicato l'helper, l'azzeramento del registro codici errore
e il testo corretto dei tre messaggi. In particolare: **il `loadData` su un CSV di
sole intestazioni ha funzionato** — `dbops.codici_errore_senza_policy` è a **0
righe**. Il rischio segnalato (nessun precedente nel repo) non si è materializzato.

### 26.6 La verifica, col metodo di sempre

Suite intera due volte, dal runner ufficiale.

| | prima della famiglia C | dopo |
| --- | --- | --- |
| owner (default) | 88 | **88** |
| `PGTAP_RUNNER=app` | 110 | **103** |
| **divario** | **23** | **16** |

**Zero differenze da owner**: gli 88 sono identici, file per file — la famiglia C
non ha spostato niente su chi la suite la lancia oggi. Sotto utente applicativo
calano esattamente **7**, cioè i sette della famiglia. **Nessun file della
famiglia C compare più nel divario.**

I 16 che restano sono esattamente le famiglie **B (8) + D (8)**: nessun residuo.

### 26.7 Cosa resta

1. **Cantiere `LIMIT 1`** (§11.3): 133 siti a rischio ALTO su 170 file. Sempre
   **prima** della ribaselinatura.
2. **Famiglia B (8)** — `pratiche.workflow_definizioni` (6) e
   `template_flussi_avanzamento_proiezione` (2): `SELECT`-only per scelta,
   cantiere definizioni versionate.
   **Famiglia D (8)** — 4 GRANT mirati (`indirizzi_dettaglio`,
   `pratiche_sorgenti`, `dashboard_definizione`, `preventivi`), 3 asserzioni,
   1 binding AD_HOC. Più le **14 fixture** del §22.4.
3. **La commutazione**: default `PGTAP_RUNNER` da `owner` ad `app` — una riga —
   e `PGTAP_RUNNER=app scripts/pgtap-baseline.sh --update` sull'intera suite.

⚠️ Prima del punto 3, `anagrafiche/test-istanza-cliente-chain.sql`: oscilla fra
6 e 0 asserzioni a parità di codice (§21.3).

---

## 27. Cantiere `LIMIT 1` — aperto, e la prima metà è fatta (2026-08-07)

> Il debito più grande rimasto, e l'unico che deve stare **prima** della
> ribaselinatura: registrare come «noto» un rosso intermittente significa coprire
> un rosso vero il giorno in cui torna verde per caso.

### 27.1 L'analizzatore, ricostruito

La passata di censimento del §11.3 era stata fatta in un'altra sessione e lo
strumento non c'era più. Ricostruito, e va ricostruito bene perché il punto
delicato è uno solo: **`ORDER BY` va cercato allo stesso livello di
annidamento** del `LIMIT`. Un `ORDER BY` in una sottoquery, o nella query che
contiene quella col `LIMIT`, non ordina la scelta che interessa.

Come funziona: maschera commenti, stringhe e dollar-quote preservando gli
offset; risale dal `LIMIT` bilanciando le parentesi fino alla `(` aperta più
vicina o al `;`; cerca `ORDER BY` a profondità 0 in quel perimetro. Esclude i
`LIMIT` dentro `EXISTS(...)`, dove non scelgono niente.

Il controllo che dice che è sano: `anagrafiche.soggetti` esce **24 volte**,
esattamente il numero misurato allora.

### 27.2 ⚠️ Prima di tagliare: 116 «ALTO» non sono 116 problemi

Il censimento grezzo dava **550 occorrenze / 116 ALTO / 163 file** (era
577/133/170 su 440 file: nel frattempo la suite è passata a 426, e l'euristica
non è la stessa). Ma separando il rumore dal segnale:

| | |
| --- | --- |
| ALTO su **tabelle temporanee create dal test stesso** | 50 — il `LIMIT` non sceglie niente di rischioso |
| ALTO su **tabelle vere del dominio** | **66** — il bersaglio |

Tagliare a tappeto sui 116 avrebbe speso metà del lavoro su siti innocui.

### 27.3 Le due tranche fatte

**Tranche 1 — `anagrafiche.soggetti`, 24 siti.** Forma omogenea, e con
un'ironia dentro:

```sql
CREATE TEMP TABLE tmp_xx_refs AS
SELECT
  script.fn_pgtap_emittente_operatore() AS emittente_id,   -- dal contesto ✅
  (SELECT id FROM anagrafiche.soggetti LIMIT 1) AS soggetto_id,  -- a caso ❌
```

La riga sopra deriva l'emittente **dal contesto** (regola 4 di
[[feedback_pgtap_limit1_senza_orderby]]); quella sotto pesca il soggetto a caso.
È la forma esatta del difetto dell'emittente 44. Sistemati tutti con `ORDER BY`
sulla PK. Il ventiquattresimo era diverso — un `JOIN` a tre tabelle — e ha avuto
`ORDER BY s.id, sr.id, iu.id`: ordinare il solo soggetto avrebbe lasciato al
planner la scelta di ruolo e istanza.

**Tranche 2 — `catalogo.unita_misura` (6) e `config.iva` (6).**

⭐ **E qui è saltato fuori un difetto vero, non stilistico.** In
`test-fn-ricalcola-totali-preventivo` c'erano **due estrazioni indipendenti dallo
stesso insieme**:

```sql
(SELECT i.id           FROM config.iva i WHERE attivo AND aliquota_iva > 0 LIMIT 1) AS iva_id,
(SELECT i.aliquota_iva FROM config.iva i WHERE attivo AND aliquota_iva > 0 LIMIT 1) AS iva_aliquota;
```

Niente garantiva che pescassero la stessa riga: il test avrebbe calcolato i
totali attesi con l'aliquota di un'IVA **diversa** da quella messa in riga.
**Non è teorico: in catalogo ci sono 7 IVA attive con aliquota positiva.** E la
riga appena sopra aveva già `ORDER BY ef.id` — qualcuno aveva sistemato
l'emittente e lasciato l'IVA, che è il modo in cui questi difetti sopravvivono.

Riparato con una **CTE che sceglie una volta sola** e proietta id e aliquota
dalla stessa riga — la regola 3 della memoria, che l'`ORDER BY` da solo non
avrebbe soddisfatto altrettanto bene.

### 27.4 Il risultato, e la verifica

| | inizio | dopo tranche 1 | dopo tranche 2 |
| --- | --- | --- | --- |
| occorrenze senza `ORDER BY` | 550 | 526 | **515** |
| di cui ALTO | 116 | 92 | **81** |
| **ALTO su tabelle vere** | **66** | 42 | **31** |
| `anagrafiche.soggetti` ALTO | 24 | **0** | **0** |

**Verificato dopo ogni tranche: 88 rossi da owner, zero differenze file per
file.** Nessun test è cambiato di esito — il che è il punto: si è tolta la
fortuna, non si è spostato il risultato.

### 27.5 Cosa resta, e perché cambia natura

I 31 ALTO rimasti su tabelle vere non si tagliano più a tappeto. In testa non ci
sono più tabelle ma **funzioni**:

| | |
| --- | --- |
| `pratiche.fn_check_prerequisiti_flusso` | 6 |
| `vendite.fn_list_ddt_da_pushare` | 3 |
| `vendite.fn_ricalcola_totali_fattura` | 2 |
| `anagrafiche.pdp`, `config.unita_organizzative` | 2 + 2 |
| altri, uno o due ciascuno | 16 |

Un `LIMIT 1` su una funzione che ritorna un insieme è legittimo se la funzione
ritorna una riga sola, ed è una scommessa se ne ritorna molte: **si decide
leggendo la funzione**, non con una regex. Sono lavoro a giudizio, non una
passata.

⚠️ **E la passata va chiusa sul pattern, non sull'elenco dei file toccati** —
la lezione del 34° file di [[feedback_pgtap_limit1_senza_orderby]]. Lo
strumento per rifarla in ogni momento è
`censimento_limit1.py`, il cui metodo è descritto al §27.1.

### 27.6 ℹ️ Il file intermittente NON è un caso di `LIMIT 1`

`anagrafiche/test-istanza-cliente-chain.sql` (§21.3), quello che oscilla fra 6 e
0 asserzioni, ha due `LIMIT 1` su `anagrafiche.soggetti` — ma sono
`WHERE partita_iva = '...'`, cioè **deterministici**. L'analizzatore li classifica
correttamente «medio». **La causa dell'oscillazione è un'altra e resta da
trovare**: va cercata prima della ribaselinatura, ma non in questo cantiere.

---

## 28. ✅ Il file intermittente, sciolto — e non era `LIMIT 1` (2026-08-07)

`anagrafiche/test-istanza-cliente-chain.sql` oscillava fra **6 e 0 asserzioni a
parità di codice** dal §21.3, ed era l'ultima cosa da capire prima della
ribaselinatura. **Adesso è verde: 26 su 26.**

### 28.1 ⚠️ Prima di tutto: «6 o 0» non era verde-o-rosso

Venticinque corse consecutive. Il file **non passava mai**: la differenza era
solo *quanto lontano arrivava*.

| esito | dove moriva | perché |
| --- | --- | --- |
| **6 asserzioni** | riga 255 | vincolo differito `require_utility_dichiarata`: fixture incompleta |
| **0 asserzioni** | riga 146 | `uq_pdp_codice` — chiave duplicata |

Chi leggeva «oscilla fra 6 e 0» poteva credere che a volte funzionasse. Non è
mai successo. **Erano due difetti diversi in fila**, e il secondo nascondeva il
primo una volta su quattro.

### 28.2 ⭐ La causa dell'oscillazione è aritmetica

```sql
SELECT ('G-PDP-CH-' || substring(k.suffix, 1, 2))   -- ← DUE caratteri esadecimali
```

**Due cifre esadecimali = 256 codici possibili**, su una colonna `UNIQUE`. E in
`anagrafiche.pdp` ci sono **64 righe residue** con quel prefisso, la più vecchia
del **2026-02-15**, la più recente del **2026-08-06**: sei mesi di corse
*non transazionali* — fino al giorno in cui questo cantiere ha reso il file
transazionale (§17).

**64 su 256 = 25% di collisione per corsa.** È esattamente la frequenza
osservata. Non c'era niente di misterioso: era un compleanno con un calendario
da 256 giorni.

⚠️ **Il troncamento non serviva a niente**: `pdp` è `varchar(30)` e la chiave
intera sarebbe lunga 17. E **tutte le altre chiavi dello stesso
`tmp_test_keys` usano già il suffisso intero** — solo il PDP era stato tagliato.
Corretto: suffisso intero, 8 cifre esadecimali. Quindici corse consecutive, tutte
allo stesso punto: l'oscillazione è sparita.

> È la coda di [[feedback_pgtap_test_non_transazionali_contaminano]]: la
> transazionalità ha fermato l'accumulo, ma **i residui di prima sono ancora
> lì**, e continuano a far danno finché una chiave è abbastanza stretta da
> incontrarli.

### 28.3 Poi i due difetti veri, in fila

**1. Il vincolo differito scattava troppo presto.** Il file ha
`SET CONSTRAINTS ALL IMMEDIATE` **in testa** (§17), ma qui istanza e satellite
nascono in **due istruzioni separate**, per quattro coppie: a fine della prima
`INSERT` il `billing_account` non esiste ancora, e il guard respinge.

È il caso esatto del §22.5 — la riga va **dove l'unità di lavoro è completa**.
Spostata dopo la **quarta** coppia: dopo la prima non basterebbe, perché da lì in
poi ogni istruzione è immediata e le tre istanze successive fallirebbero uguale.
E comunque prima del cleanup, altrimenti scatterebbe su righe già cancellate.

**2. `billing_account.categoria_cliente_id` è `NOT NULL`**, e la fixture era
rimasta indietro rispetto alla colonna: tutte e quattro le `INSERT` la
ignoravano. Aggiunta, scegliendo la categoria **una volta sola e con `ORDER BY`**
— le regole del §27, applicate mentre si ripara.

### 28.4 Il risultato

| | |
| --- | --- |
| esito | **26/26 PASS**, 20 corse consecutive tutte a 26 |
| da utente applicativo | **PASS** |
| suite da owner | **88 → 87**, un rientrato e nessun rosso nuovo |
| baseline | aggiornata: il file è uscito dal registro del debito |

ℹ️ La baseline ha ora la sua prima riga `# pgtap-runner: owner` (§24.5): è il
primo `--update` da quando il meccanismo esiste.

### 28.5 ⚠️ Restano 64 righe di spazzatura in `anagrafiche.pdp`

Le residue `G-PDP-CH-xx` **non fanno più danno** — la chiave nuova è lunga 8 e
non può più incontrarle — ma restano lì, e sono dati di test in una tabella di
dominio. Vanno cancellate a mano
([[project_no_produzione_solo_sviluppo]]: dati sporchi si correggono a mano, non
con codice):

```sql
DELETE FROM anagrafiche.pdp WHERE pdp LIKE 'G-PDP-CH-__';   -- 64 righe, esattamente 2 caratteri
```

⚠️ Il predicato con `__` e non `%` **apposta**: le chiavi nuove sono
`G-PDP-CH-` + 8 caratteri, e un `%` cancellerebbe anche quelle di una corsa in
volo. **Non eseguito**: è una cancellazione su una tabella di dominio, la decide
Tid.

E vale la domanda più larga, che non è di questo cantiere: **quanti altri
residui di corse non transazionali ci sono in giro?** Sei mesi di accumulo non
hanno lasciato solo dei PDP.
