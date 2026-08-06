# Brief DB — La suite pgTAP non è confrontabile con la sua baseline (utente ≠ utente)

> **Tipo**: brief operativo per il **team DB** · **Target**: `dev/db-tid` ·
> **Data**: 2026-07-29 · **Owner**: Tid · **Stato**: 🟡 **IN CORSO** —
> il sintomo è rientrato per altra via (strada **(a)**), la decisione di passare
> a **(b)** è presa il 2026-08-05 e il piano è al **§8**.
> **Da leggere per primo: il §11** — stato al 2026-08-06, con la domanda aperta
> del §10.3 sciolta e l'elenco di ciò che resta al **§11.4** ·
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
