# Brief DB — La suite pgTAP non è confrontabile con la sua baseline (utente ≠ utente)

> **Tipo**: brief operativo per il **team DB** · **Target**: `dev/db-tid` ·
> **Data**: 2026-07-29 · **Owner**: Tid · **Stato**: 🟡 **IN CORSO** —
> il sintomo è rientrato per altra via (strada **(a)**), la decisione di passare
> a **(b)** è presa il 2026-08-05 e il piano è al **§8**.
> **Da leggere per primo: §11 → §15** — stato al 2026-08-06. La domanda aperta
> del §10.3 è sciolta (§11); la riga di contesto è in **408 file su 426**, con 4
> esclusi motivati (§12); il residuo sotto l'utente applicativo era **65 file, di
> cui 38 con una causa sola** (§13), e quella causa è stata corretta: `pratiche`
> passa da 38 a **10 file rossi** (§15). Due difetti di prodotto trovati e
> chiusi: §13.3 e §15.1.
> ⚠️ Due avvertenze prima di citare una cifra: il **§14** corregge il metro dei
> §8.2, §9.2, §12.2 e della prima stesura del §13.1; il **§15.3** spiega perché
> due corse consecutive con utenti diversi si sporcano il database a vicenda.
> Cosa resta: **§13.4** più il §15.4 ·
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
