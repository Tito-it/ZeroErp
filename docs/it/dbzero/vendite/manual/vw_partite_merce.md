## 📘 Documentazione Concettuale – Vista `vendite.vw_partite_merce`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
>
[vendite.ddt_righe](/dbzero/vendite/tabelle/ddt_righe)
> [vendite.ordini_righe_fulfillment](/dbzero/vendite/tabelle/ordini_righe_fulfillment)
> [vendite.resi_righe](/dbzero/vendite/tabelle/resi_righe)
> [vendite.resi_righe_riconsegne](/dbzero/vendite/tabelle/resi_righe_riconsegne)
>
Viste collegate:
>
[vw_af_merce_per_riga](vw_af_merce_per_riga.md)
> [vw_contatore_merce](vw_contatore_merce.md)
> [vw_resi_righe_effettive](vw_resi_righe_effettive.md)
> [vw_resi_da_accreditare](vw_resi_da_accreditare.md)
> Brief autorevole: `docs/it/dev/work-done/brief-design-partita-merce-generalizzata.md`

---
### 🎯 Scopo Principale
(latest review 2026-08-17)

`vendite.vw_partite_merce` tiene **il conto della merce**: per ogni riga di merce uscita dal
magazzino dice quanta ne è andata al cliente, quanta è tornata indietro, quanta è stata
fatturata — e che cosa resta da fare.

**Una partita è una riga di documento di trasporto.** Una riga di DDT, una partita: sempre, che
dietro ci sia un ordine oppure no.

---

### Cosa cambia rispetto a prima, e perché conta

Fino al 2026-08-17 il conto della merce si teneva sulla **riga d'ordine**. Sembra un dettaglio
tecnico e non lo è: significa che **la merce senza ordine non veniva contata affatto**. Non
compariva a zero — non compariva.

Restavano fuori tre famiglie, tutte reali:

| Famiglia | Cosa succedeva |
|---|---|
| Righe aggiunte **a mano** su un DDT | uscivano dal magazzino, venivano fatturate, e nessuno ne teneva il conto |
| **DDT senza ordine** dietro | idem — e succede da sempre |
| Articoli **compositi** (i kit) | esclusi apposta, perché i loro numeri erano in un'unità di misura sbagliata |

⚠️ **La conseguenza pratica era una sola, e pesante**: se il cliente rendeva quella merce dopo
che gli era stata fatturata, **l'accredito non si poteva calcolare**. Il reso si registrava e
poi non produceva nulla.

⭐ Adesso il rapporto è rovesciato: **la partita è la riga di merce, e la riga d'ordine è una
delle sue possibili origini** (l'altra è «nessuna»). Chi il conto lo aveva già, continua ad
averlo con gli stessi numeri; chi non ce l'aveva, ora ce l'ha.

---

### Le grandezze, una per volta

| Colonna | Cosa dice |
|---|---|
| `consegnato` | quanta merce è uscita con questa riga di documento |
| `reso` | quanta ne è tornata indietro |
| `in_riconsegna` | quanta di quella tornata è **già stata messa su un documento di rispedizione non ancora emesso** |
| `tenuti` | quanta ne ha in mano il cliente adesso — `consegnato − reso` |
| `fatturato_merce` | quanta ne è stata fatturata **come spedizione** |
| `fatturato_da_ordine` | quanta ne è stata fatturata **come ordine**, e attribuita a questa spedizione |
| `fatturato` | la somma dei due |
| `differenza` | `tenuti − fatturato` — il saldo |
| `stato` | il saldo tradotto in italiano: cosa c'è da fare |

---

### `stato`: la traduzione, fatta una volta sola

Un saldo negativo, mostrato com'è, sembra un guasto anche quando descrive correttamente il
mondo. Perciò la vista non si limita a esporre il numero: lo **traduce**, e lo fa qui, una volta
sola, per tutti quelli che la leggono.

| `stato` | Significa |
|---|---|
| `PAREGGIATA` | non c'è niente da fare |
| `DA_FATTURARE` | c'è merce consegnata e non ancora fatturata |
| `DA_ACCREDITARE` | è stato fatturato più di quanto il cliente tenga: gli si deve un accredito |
| `NON_FATTURABILE` | questa merce non si fattura, e non per dimenticanza |
| `NON_MISURABILE` | il conto non si riesce a fare |
| `RICONSEGNA` | questa merce ha un conto, ma non è qui: sta sulla partita da cui è tornata |

> ⚠️ **Chi consuma questa vista non deve ri-tradurre il segno.** Due traduzioni indipendenti —
> una nel pannello dell'ordine, una in quello del DDT — prima o poi divergono, e diventano due
> frasi diverse per lo stesso numero.

---

### ⚠️ `differenza` può essere vuota, e non è zero

Vuota (`NULL`) vuol dire **«il conto non si applica»**, ed è diverso da «il conto torna».

* **La causale di trasporto non è fatturabile** *e non c'è alcun fatturato*: conto visione,
  campionatura, trasferimento fra depositi, omaggio. Quella merce non verrà mai fatturata, e
  scrivere `0` farebbe dire allo schermo *«5 pezzi da fatturare»* su un conto visione.
* **Il conto non è misurabile**: un kit di cui non si riesce a ricostruire la quantità, o dati
  che chi legge non ha il permesso di vedere.

> ⭐ **Attenzione a una sottigliezza che è già capitata.** La causale non fatturabile **da sola**
> non spegne il conto. Esiste il caso reale di merce partita con causale «conto visione» il cui
> ordine è stato fatturato lo stesso: la causale dice cosa ci si aspetta **dal viaggio**, non se
> la merce è stata fatturata. Se un fatturato c'è, il conto si applica — è un fatto, non una
> previsione.

---

### ⚠️ La merce in bozza non è merce uscita

Una partita nasce quando il documento di trasporto **è stato emesso**. Finché è una bozza, la
merce è ancora in magazzino, e contarla direbbe che il cliente ce l'ha quando non è vero.

Il caso che lo rende evidente è il **giro della ri-consegna**: il cliente rende 3 pezzi,
qualcuno prepara il documento per rispedirglieli e non lo emette. Il cliente ne ha in mano 2 —
non 5.

⭐ **E quando la ri-consegna parte?** I pezzi tornano nel `consegnato` della
partita d'**origine** — non ne aprono una nuova. È la stessa cosa detta in due
momenti: finché il documento è fermo la merce è sul banco (`in_riconsegna`),
quando parte è di nuovo dal cliente (`consegnato`).

> 🔴 **Perché non può essere una partita nuova, ed è la trappola di tutto il
> cantiere.** Quei pezzi sono già stati consegnati e già contati una volta. Se
> la riga di ri-consegna avesse un conto proprio, risulterebbe `6 da fatturare`
> su merce già fatturata: **la si fatturerebbe due volte**. La riga resta
> visibile — con `e_riconsegna` acceso e lo stato `RICONSEGNA` — così il
> pannello del documento di ri-consegna non è vuoto, ma il conto sta altrove.

✅ **E quei 3 pezzi non spariscono**: si leggono in `in_riconsegna`. Non sono dal cliente, e non
sono nemmeno nell'elenco «da rispedire» — quello li considera già sistemati, perché il documento
qualcuno l'ha preparato. Senza questa colonna sarebbero merce invisibile.

```text
in mano al cliente .......  2
in ri-consegna ...........  3     ← tornati, già preparati, non ancora partiti
                           ---
                             5     ← e i conti tornano a occhio
```

---

### ⚠️ Come si conta la merce fatturata «sull'ordine»

Sul cliente standard si fattura **l'ordine alla conferma**, e la spedizione arriva dopo — a
volte molto dopo, a volte mai. Quel fatturato non appartiene a nessuna spedizione, perché
quando è nato di spedizioni non ce n'erano.

La regola è: **si versa nelle spedizioni di quella riga d'ordine, dalla più vecchia, fino a
capienza**. Ciò che avanza non appartiene a nessuna merce — è fatturato in anticipo, e si legge
nell'aggregato per riga d'ordine, non qui.

> ⚠️ **La capienza è il `consegnato`, non i `tenuti`.** Sembra una sfumatura e decide tutto: se
> fosse `tenuti`, un reso «libererebbe» capienza, l'accredito verrebbe riassorbito e la coda
> degli accrediti resterebbe **vuota** — cioè il difetto che tutto questo lavoro serve a evitare.

---

### 📑 Campi chiave esposti

* **Chiave**: `ddt_riga_id` — la partita
* **Contesto**: `ddt_id`, `ddt_uid`, `articolo_id`, `is_composito`
* **Origine**: `ordine_riga_id`, `ordine_id`, `origine` (`ORDINE` / `NESSUNA` / `MULTIPLA`)
* **Il conto**: `consegnato`, `reso`, `in_riconsegna`, `tenuti`, `fatturato_merce`,
  `fatturato_da_ordine`, `fatturato`, `differenza`
* **La lettura**: `stato`, `fatturabile`, `misurabile`, `e_riconsegna`,
  `sospetto_duplicato_ordine`

⭐ **`sospetto_duplicato_ordine` è un avviso, non un divieto.** Si accende su una
riga aggiunta a mano quando **tutte e tre**: la riga non ha ordine dietro, il
documento ne ha altre che ce l'hanno (spedizione mista), e l'articolo è già fra
quelli di quell'ordine. È la situazione che un operatore non distingue da una
svista — *«questa merce era già ordinata»* — e che prima non si vedeva affatto.

Non la si vieta perché il caso legittimo esiste, ed è comune: più pezzi dello
stesso codice spediti insieme, un ricambio, una sostituzione. Vietarla
significherebbe far viaggiare **due documenti di trasporto per una sola
spedizione**, che è un costo fisico, non informatico.

---

### Esempio d'uso

```sql
-- La situazione della merce di una spedizione, riga per riga.
SELECT ddt_riga_id, consegnato, reso, tenuti, fatturato, stato
FROM vendite.vw_partite_merce
WHERE ddt_id = 15854
ORDER BY ddt_riga_id;

-- Tutto ciò che è aperto su un ordine, comprese le righe aggiunte a mano.
SELECT ddt_riga_id, origine, stato, differenza
FROM vendite.vw_partite_merce
WHERE ordine_id = 18586 AND stato IN ('DA_FATTURARE', 'DA_ACCREDITARE');

-- Merce fatturata e poi resa: gli accrediti da emettere.
SELECT ddt_riga_id, -differenza AS accredito_dovuto
FROM vendite.vw_partite_merce
WHERE stato = 'DA_ACCREDITARE';
```

---

### Note operative

* **L'universo sono le righe di DDT attive**, su documenti non annullati e almeno emessi. Una
  riga di DDT c'è sempre quando la merce si muove: è il motivo per cui è stata scelta come
  chiave, e il motivo per cui non serviva inventarne una nuova.
* **I resi si agganciano alla riga di merce**, che è un dato obbligatorio, non alla riga
  d'ordine, che è facoltativa. È da lì che nasceva il buco: un reso senza riga d'ordine usciva
  dal conto **senza dare errore**.
* ⚠️ **La colonna avvisa solo se qualcuno la mostra.** Finché il frontend non la
  espone, il presidio è a metà.
* **`origine = MULTIPLA`**: il modello ammette che una riga di spedizione evada due righe
  d'ordine. La partita lo **dichiara** invece di duplicare la merce, ed esce sotto l'ordine
  della riga minima — il caso è **costruito** nel pgTAP della chiusura (test 13).
* **È read-time**: nessun conto memorizzato, nessun campo da tenere allineato. Ne discende che
  vale anche sui documenti vecchi, senza alcuna ricostruzione dello storico.
* `security_invoker=on`: la vista è letta con i permessi di chi interroga, quindi la RLS di
  scope resta attiva. ⚠️ Chi la modifica con `CREATE OR REPLACE` **deve ri-specificare la
  reloption**: non è visibile in `pg_get_viewdef` e verrebbe azzerata in silenzio.
* ⚠️ **Attenzione a un tranello di lettura**: il fatturato passa da un controllo di visibilità
  *diverso* da quello della merce. Chi vedesse la spedizione ma non la sua commessa leggerebbe
  «fatturato zero» — indistinguibile da «non ancora fatturato». È il motivo per cui esiste
  `misurabile`.
* Test: `db/pgtap/vendite/test-vw-partite-merce-v1.sql`; la chiusura per documento in
  `test-fn-partite-merce-chiusura-v1.sql`.

---


---

### 🔄 rev 2026-08-18 — la partita conosce la nota di credito

Brief: `brief-design-note-credito-resi` (slice **N6** e **N7**).

**Due colonne nuove**, entrambe in coda perché un `CREATE OR REPLACE VIEW` non
ne inserisce in mezzo — e da questa vista dipendono `vw_contatore_merce`,
`vw_resi_da_accreditare` e `vw_situazione_merce_ordine`.

| Colonna | Cosa dice |
|---|---|
| `rettificato` | quanto una nota di credito ha tolto al fatturato della partita. **Negativo o zero** |
| `riconsegna_quota_nuova` | i pezzi accreditati che hanno **cambiato casa** verso una spedizione di ri-consegna |

#### N6 — il `fatturato` somma le rettifiche

È la riga che chiude il **contratto del §2** del brief: *«una nota di credito che
non abbassa i fatturati della partita è invisibile al contatore → la coda
accrediti continuerebbe a chiedere l'accredito per sempre, anche a NC emessa»*.

⚠️ **La rettifica si legge SEMPRE sulla corsia DDT**, anche quando a fatturare è
stata la corsia ordine (decisione D-NC-1). Se entrasse nel serbatoio d'ordine, la
greedy oldest-first della CTE `alloc` scaricherebbe l'accredito sull'**ultima**
spedizione invece che su quella da cui la merce è tornata — con il totale
perfettamente giusto e la **ripartizione falsa**, cioè un difetto che nessun test
di parità vede. Per questo `alloc` non è stata toccata.

⭐ **È una somma, non una sottrazione**: la quantità della rettifica è già
negativa in catena (D-NC-2). Il segno vive nel numero, non in un'etichetta che
ogni consumatore dovrebbe saper tradurre.

#### N7 — «una ri-consegna è merce nuova SOLO per la parte accreditata»

> Quando si rispedisce, i pezzi che erano stati **accreditati** contano sulla
> spedizione **nuova**. Quelli non accreditati continuano a contare su quella
> vecchia.

| | consegnato | reso | in mano | fatturato | esito |
|---|---|---|---|---|---|
| DDT₁ *(resta ferma)* | 10 | 3 | 7 | 7 | 0 — a posto ✅ |
| DDT₂ *(prende i 3 accreditati)* | **3** | 0 | 3 | 0 | **3 da fatturare** ✅ |

DDT₂ è una spedizione **mai instradata**: `fn_get_stato_push_segment` la vede
`LIBERA`, il giro di fatturazione normale la prende in carico. ⭐ Nessun verbo
nuovo, nessuna seconda pipeline — e la cintura che impedisce di ri-spingere una
riga già fatturata **non si allenta**.

La quota si ripartisce fra più ri-consegne della stessa origine con la solita
**greedy oldest-first**, ed è cappata alla quantità ri-consegnata: un secondo
giro reso → NC → ri-consegna non conta due volte lo stesso accredito.

⚠️ **Senza nota di credito la regola è INERTE**: nessun pezzo è stato
accreditato, nessuno cambia casa, ogni numero resta quello di prima. È ciò che
tiene chiuso il buco di luglio e verde il **caso D** di
`test-fn-list-ddt-da-pushare-contatore-v1`.

#### ⚠️ `consegnato` è la base CONTABILE, non la quantità fisica

Su una riga di **ri-consegna** `consegnato` è ora la quota che ha cambiato casa —
cioè **0** finché non c'è una nota di credito. Prima era la quantità della riga
di DDT, contata **sia** sull'origine **sia** sulla riga nuova: la somma delle
partite superava la merce realmente uscita, e l'invariante *«i pezzi si spostano,
non si moltiplicano»* non era vero. Ora lo è.

La quantità fisica resta dov'è sempre stata: `vendite.ddt_righe.quantita`.

---

### 🔄 rev 2026-09-17 — `sospetto` si calcola una volta, non per partita (D14)

ChangeSet `20260917-01`. Registro: `migliorie-generali-da-test-valutazione.md`
§3 D14. **Niente cambia nel risultato**: stesse colonne, stesse righe, stesso
significato di `sospetto_duplicato_ordine`. Cambia **quante volte** la vista
paga le policy RLS per calcolarlo.

**Il difetto.** La CTE `sospetto` era un `EXISTS` correlato a quattro tabelle,
che il planner eseguiva **riga per riga**: per ogni partita ri-scandiva
`ddt_righe`, `ordini_righe_fulfillment` e `ordini_righe`, e ogni riga scandita
pagava la propria policy. Da owner non si vede (nessuna policy); come
applicazione sì — misura del 2026‑09‑17 su dbdev, 36 partite: la vista intera
**18 ms da owner, 396 ms da app**, di cui 322 nella sola `sospetto`.

⚠️ E chi la paga è la **capability del DDT** (`script.fn_available_actions_ddt`),
che legge la vista due volte per un documento solo — lister e diagnosi, entrambe
in `JOIN` con la vista, e il filtro sul documento non entra nelle CTE
materializzate: ogni chiamata ricalcola le partite di tutti i DDT. ~850 ms per
DDT come app, cioè il drawer a ogni apertura, e ogni pgTAP che itera i DDT vivi.

**La forma nuova.** L'`EXISTS` diceva «la coppia (DDT, articolo) di questa riga
sta nell'insieme delle coppie coperte da un ordine collegato al DDT». Quell'insieme
si costruisce **una volta** (`articoli_ordinati_per_ddt`, `DISTINCT`) e
`sospetto` diventa il `JOIN` delle righe senza fulfillment su quella coppia.
Le tre condizioni dell'avviso restano tutte e tre. Entrambe le CTE sono
`AS MATERIALIZED`: senza, il planner le inlina e torna al ciclo per riga.

**Misurato prima di scrivere** (solo `SELECT`, transazione ritirata): vista
intera come app **375 → 88 ms**, `EXCEPT ALL` nei due versi a zero righe.
⚠️ Il prezzo, dichiarato: la lettura di **una** riga (`WHERE ddt_riga_id = x`)
sale di ~12 ms, perché l'insieme si calcola intero anche quando serve una riga.
Chi legge una riga è il pgTAP della vista e la situazione merce di un documento;
chi la legge intera è la capability, cioè il drawer.

Presidio: `test-vw-partite-merce-v1.sql` test 11, che **costruisce** il caso
segnalato e quello legittimo — il dato vivo non ne contiene nessuno, e
un'equivalenza sulle righe di oggi non proverebbe il ramo.

---

### 🔄 rev 2026-09-21 — il contatore delle attività si legge una volta, non quattro (D14, terza leva)

ChangeSet `20260921-20`. Registro: `migliorie-generali-da-test-valutazione.md`
§3 D14. **Niente cambia nel risultato**: stesse colonne, stesse righe, stessi
numeri. Cambia quante volte la vista ricalcola `vw_af_merce_per_riga`.

**Il difetto.** La vista leggeva `vw_af_merce_per_riga` in **quattro** punti —
`acc_origine` (le rettifiche sull'origine), `alloc` (il serbatoio d'ordine),
`fd` e `fr` (fatturato e rettificato della partita). Quella vista è un
`GROUP BY` su `attivita_fatturabili ⋈ commesse_attivita`, cioè una scansione
intera che paga la policy di `commesse_attivita` per ogni riga; e il planner
non condivide un sottoalbero fra quattro `JOIN`: la ricalcolava quattro volte.
Fatto datato (dbdev, 2026‑09‑21, 51 DDT / 36 partite, come applicazione): le
quattro letture pesavano 16+15+20+17 ≈ 68 ms su ~130 della vista intera.

**La forma nuova.** Una CTE `af AS MATERIALIZED` in testa, proiezione **senza
filtro** della vista; i quattro `JOIN` restano identici nei predicati (corsia,
riga, tipo movimento) e cambiano solo la sorgente. Così l'equivalenza non ha
bisogno di argomenti: ogni `JOIN` vede esattamente le righe che vedeva.
`MATERIALIZED` per la stessa ragione di `sospetto`: senza, il planner la inlina
in ogni riferimento e torna a quattro scansioni.

**Misurato prima di scrivere** (solo `SELECT`, transazione ritirata, stessa
sessione): vista intera come applicazione **~90 → ~56 ms**, `EXCEPT ALL` nei
due versi a zero righe. La capability del DDT legge la vista due volte, quindi
risparmia il doppio.

⚠️ **Non è la chiusura di D14.** La vista resta senza parametro, e la lettura
di *un* documento continua a pagare le partite di *tutti*: quella è la quarta
leva — la partita per chiusura del documento — e ha il suo brief,
`work-in-progress/brief-db-partita-merce-per-documento.md`.

Presidi: gli stessi di sempre (`test-vw-partite-merce-v1`,
`test-vw-partite-merce-riconsegna-dopo-nc-v1` — dove `acc_origine` e `migra`
leggono le rettifiche —, `test-fn-list-ddt-da-pushare-contatore-v1`,
`test-vw-contatore-merce-v1`). Nessuna riga di test cambia.

---

### 🔄 rev 2026-09-21 — il conto sta nella funzione, la vista ne è la proiezione (D14, quarta leva)

ChangeSet `20260921-21` (la funzione) e `20260921-22` (la vista). Brief:
`work-in-progress/brief-db-partita-merce-per-documento.md`, decisioni D1 e D2
di Tid. **Niente cambia nel risultato**: stesse 23 colonne, stessi tipi, stesse
righe, stessi numeri. Cambia **dove sta il conto** e **chi lo paga**.

**Il conto sta in [`fn_partite_merce(p_ddt_ids, p_ordine_ids)`](fn_partite_merce.md)**,
e questa vista è `fn_partite_merce(NULL, NULL)`: un corpo solo. Chi legge
**per documento** — il lister e la diagnosi del push (cioè la capability del
DDT, a ogni apertura del drawer) e, ⏳ con la richiesta BE del brief, il pannello
«Situazione merce» — chiama la funzione con un seme e paga la **chiusura** del
documento: le sue righe, le spedizioni sorelle della stessa riga d'ordine, le
origini di ri-consegna. Non più le partite di tutti. Chi legge **tutto** — il
cockpit, `vw_contatore_merce` — continua a leggere la vista, che costa quanto
prima (le scansioni sono le stesse). ⭐ Dal **giro 2** (D3, 21-09) anche
`vw_situazione_merce_ordine` e `vw_resi_da_accreditare` sono proiezioni di due
funzioni con lo stesso seme — [`fn_situazione_merce_ordine`](fn_situazione_merce_ordine.md),
[`fn_resi_da_accreditare`](fn_resi_da_accreditare.md) — che chiamano questa;
i verbi dei resi leggono la coda per il DDT della riga resa.

⚠️ **La vista proietta le colonne per nome, con `consegnato::numeric(18,6)`.**
Non è pignoleria: un `RETURNS TABLE` perde la scala, e un `SELECT * FROM fn()`
sarebbe passato cambiando il contratto della vista in silenzio — senza
possibilità di tornare indietro con un `CREATE OR REPLACE`. Il pgTAP della
chiusura pinna i tipi.

⚠️ **La regola della chiusura vive nel COMMENT e nel manuale della funzione**:
chi aggiunge qui una finestra o un insieme con una chiave nuova deve allargare
la chiusura là, o la funzione sbaglia solo quando è chiamata con un seme — e
questa vista resterebbe giusta senza dirlo.

Presidi: `test-fn-partite-merce-chiusura-v1` (nuovo, 14 test a casi
costruiti) + `rls/test-rls-viste-security-invoker`, il cui criterio ora
attraversa le funzioni `BEGIN ATOMIC` (senza, questa vista — che dipende da una
funzione e non da tabelle — sarebbe uscita dal perimetro del presidio). I
cinque di sempre non cambiano.

---

{% include-markdown "signature-core.md" %}
