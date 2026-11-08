## 📘 Documentazione Concettuale – Vista `vendite.vw_situazione_merce_ordine`

> **Ultimo aggiornamento**: 3 novembre 2026

> 👀 **Vedi anche**
>
Approfondimento tabelle:
>
[vendite.ordini_righe](/dbzero/vendite/tabelle/ordini_righe)
> [vendite.ordini_righe_fulfillment](/dbzero/vendite/tabelle/ordini_righe_fulfillment)
>
Viste collegate:
>
[vw_partite_merce](vw_partite_merce.md)
> [vw_af_merce_per_riga](vw_af_merce_per_riga.md)
> Brief autorevole: `docs/it/dev/work-done/brief-design-partita-merce-generalizzata.md` §20.4

---
### 🎯 Scopo Principale
(rev 2026-11-03 — solo righe merce, gli oneri no · rev 2026-09-21 — la vista è la proiezione di `fn_situazione_merce_ordine` · rev 2026-09-13 — le date e il ritardo · rev 2026-08-18 — soglia dell'impegno · rev 2026-08-17 — nuova)

Risponde a **«come sta questa riga d'ordine?»** in una riga sola: quanto è
uscito, quanto è tornato, quanto è stato fatturato, quanto resta da spedire, e
che cosa c'è da fare. Una riga per riga d'ordine attiva **di merce**: le
righe-onere non hanno situazione merce e la funzione le esclude
(`20261103-24`, brief-db-addebito-trasporto-ordine §8.1).

È la vista che serve a **una persona che guarda un ordine**. Il conto per
singola spedizione sta in [vw_partite_merce](vw_partite_merce.md); questa lo
raccoglie.

---

### Perché non bastava il contatore — e perché ora è questa l'unica lettura

Fino al 22 settembre 2026 esisteva un secondo aggregato per riga d'ordine,
`vw_contatore_merce`: il **contatore grezzo** — `tenuti − fatturati`, mai vuoto —
che dosava il push dei DDT alla fatturazione. **È stato ritirato** (decisione D6
del brief D14): dal giro 1 della partita per documento il lister dosa dalla
partita stessa ([`fn_partite_merce`](/dbzero/vendite/funzioni/fn_partite_merce),
col DDT come seme), nessuna macchina lo leggeva più, e ogni colonna nuova della
partita gli costava un `DROP` a cascata. Questa vista è quindi **l'unica
lettura per riga d'ordine**, per una persona come per una macchina. I tre
motivi per cui il contatore non serviva a *questo* scopo restano scritti,
perché dicono cosa questa vista deve continuare a fare:

| | |
|---|---|
| **Non contiene le righe mai spedite** | è costruito partendo dalle spedizioni. Su **89 righe d'ordine su 107** il pannello sarebbe vuoto |
| **Appiattisce i «non si applica»** | il suo saldo non è mai vuoto — apposta, perché alimenta la fatturazione — quindi su un conto visione direbbe «N da fatturare» |
| **Non traduce il saldo** | non ha la colonna che dice *cosa fare*: sarebbe il consumatore a doverla rifare, e due traduzioni divergono |

⭐ Le quantità che finiscono in fattura le dosa la **partita**
([`vw_partite_merce`](vw_partite_merce.md), grana = riga di DDT), letta dal
lister per documento: questa vista **non** è sul percorso della fatturazione,
e può restare parlante senza rischiare di cambiare un numero in fattura.

---

### ⭐ Il saldo qui è diverso — ed è più onesto

Il saldo di questa vista è la **somma dei saldi delle spedizioni**: guarda la
merce che è **uscita davvero**. Ciò che è stato fatturato in anticipo — merce
non ancora partita — resta fuori dal saldo, in una colonna sua.

Sembra un dettaglio contabile e cambia quello che l'operatore legge:

```text
ordine 10 · spediti 4 · fatturati 10 alla conferma

il contatore (ritirato)  saldo −6  →  si leggeva «6 da accreditare»  ✗
questa vista .....  saldo  0      →  «tutto in pari»
                    fatturato in anticipo 6 · da spedire 6
```

**«Di quello che è uscito non c'è nulla in sospeso; ne restano 6 da spedire, già
fatturati.»** È la lettura giusta, e il contatore non poteva darla senza
cambiare i numeri su cui si fattura.

---

### ⚠️ «Da spedire» non si ricalcola: viene da dove è sempre venuto

Il residuo di spedizione ha già una sua formula nel sistema, quella che decide
se un ordine è evaso. Questa vista **usa quella**, e non ne inventa una seconda.

La differenza non è teorica:

```text
ordine da 21 · spediti tutti e 21 · 3 tornati indietro da rispedire

«ordinato − consegnato» ......  0   →  «niente da spedire»   ✗
il residuo di sistema ........  3   →  l'ordine deve ancora 3
```

⭐ La causa è che il *consegnato* di una spedizione **comprende le
ri-consegne** — la stessa merce che esce due volte — e quindi non è confrontabile
con la quantità ordinata. Su una riga reale vale 17 contro 9 ordinati.

---

### ⭐ Un ordine in bozza non impegna nessuno

Una bozza d'ordine è una proposta: si può ancora cambiare, e nessuno in
magazzino sta preparando niente. Un ordine annullato è una proposta che è
morta. In tutti e due i casi la domanda **«quanto resta da spedire?»** non ha
risposta — non perché la risposta sia zero, ma perché nessuno aspetta quella
merce.

Fino al 18 agosto 2026 la vista rispondeva lo stesso, con la quantità ordinata:

```text
ordine ancora in BOZZA da 10 pezzi

prima ....  «10 da spedire»   →  un'intenzione presentata come un arretrato   ✗
adesso ...  «—»               →  non si applica: l'ordine non è stato confermato
```

Non era un caso di coda: su 107 righe, **60 erano su ordini in bozza**. E su un
ordine annullato e mai spedito il numero sarebbe rimasto lì **per sempre**,
perché nessuna azione avrebbe potuto azzerarlo.

**La regola**: l'impegno esiste da quando l'ordine esce dalla bozza e finché non
viene annullato. Sotto quella soglia «da spedire» resta vuoto e lo stato dice
`NON_IMPEGNATA`.

> ⭐ **La riga però resta**, con la sua quantità ordinata. È voluto: il pannello
> si apre **dentro un ordine**, e far sparire le righe renderebbe vuoto il
> pannello di ogni bozza — cioè si tornerebbe a non poter distinguere «qui non
> c'è niente da fare» da «qui non sto vedendo niente».

> ⚠️ **La merce uscita davvero vince sempre.** Se su una riga c'è anche una sola
> spedizione, lo stato torna a essere quello del saldo — anche se l'ordine è
> stato annullato dopo. Merce uscita è merce uscita: il conto è reale, e un
> eventuale accredito pure. Oggi la combinazione non si può verificare (un
> ordine con una spedizione viva non è annullabile), ma se un domani cambiasse,
> il pannello **lo mostra** invece di nasconderlo.

---

### Gli stati

| `stato` | Significa |
|---|---|
| `NON_IMPEGNATA` | l'ordine è ancora in bozza, o è stato annullato: non c'è un impegno a spedire |
| `NON_SPEDITA` | l'ordine è confermato, ma non è ancora uscito niente |
| `PAREGGIATA` | di ciò che è uscito, non c'è nulla in sospeso |
| `DA_FATTURARE` | c'è merce consegnata e non ancora fatturata |
| `DA_ACCREDITARE` | è stato fatturato più di quanto il cliente tenga |
| `NON_FATTURABILE` | quella merce non si fattura, e non per dimenticanza |
| `NON_MISURABILE` | il conto non si riesce a fare |

> ⭐ **`NON_SPEDITA` e non `DA_SPEDIRE`, e la differenza conta.** `stato` dice
> cosa c'è da fare **sul saldo**: fatturare, accreditare, niente. «Da spedire» è
> un'altra cosa — un arretrato di spedizione — e sta nella sua colonna, che vale
> anche per le righe spedite a metà. Mescolarle rimetterebbe insieme due domande
> che il sistema ha appena finito di separare.

---

### ⚠️ Vuoto non è zero — e vale per due colonne

**Zero** è un'affermazione: «ho guardato, e non c'è niente da fare».
**Vuoto** è un'astensione: «la domanda non si applica». Sono due cose diverse, e
qui succedono in due punti.

**Il saldo (`differenza`) è vuoto** quando:

* la riga non è ancora stata spedita — non c'è niente da saldare;
* tutta la merce uscita è su documenti che non si fatturano (conto visione,
  campionatura, trasferimento);
* il conto non si sa fare (un kit di cui manca il coefficiente, o dati che chi
  guarda non ha il permesso di vedere).

**«Da spedire» (`da_spedire`) è vuoto** quando l'ordine non impegna: è ancora in
bozza, oppure è stato annullato. Nessuno aspetta quella merce.

> ⚠️ **Chi consuma questa vista non deve trasformare il vuoto in zero.** È la
> differenza fra un pannello che dice «non si applica» e uno che manda un
> operatore a fatturare un conto visione — o che gli mette in coda una
> spedizione che nessuno ha chiesto.

---

### 📑 Campi chiave esposti

* **Chiave**: `ordine_riga_id` · **contesto**: `ordine_id`, `riga_nr`, `articolo_id`
* **La merce**: `ordinato`, `consegnato`, `reso`, `in_riconsegna`, `tenuti`
* **La fatturazione**: `fatturato_merce`, `fatturato_da_ordine`, `fatturato`,
  `fatturato_anticipato`
* **Cosa resta**: `da_spedire`, `differenza`, `stato`
* **Attendibilità**: `misurabile`, `partite_merce`

---

### Esempio d'uso

```sql
-- La situazione di un ordine, riga per riga.
SELECT riga_nr, ordinato, consegnato, tenuti, fatturato, da_spedire, stato
FROM vendite.vw_situazione_merce_ordine
WHERE ordine_id = 18586
ORDER BY riga_nr;

-- Cosa è aperto, senza confondere il vuoto con lo zero.
-- ⭐ `da_spedire > 0` esclude da sé le righe non impegnate: un confronto con un
--    valore vuoto non è mai vero. Le bozze non entrano, senza filtri in più.
SELECT ordine_id, riga_nr, stato, differenza, da_spedire
FROM vendite.vw_situazione_merce_ordine
WHERE stato IN ('DA_FATTURARE', 'DA_ACCREDITARE') OR da_spedire > 0;

-- Le righe di un ordine che non impegna ancora (o non impegna più).
SELECT ordine_id, riga_nr, ordinato, stato
FROM vendite.vw_situazione_merce_ordine
WHERE stato = 'NON_IMPEGNATA';
```

---

### Note operative

* **L'universo sono le righe d'ordine attive**, tutte — anche quelle mai
  spedite, anche quelle di un ordine in bozza o annullato. È la ragione per cui
  questa vista esiste, e la soglia dell'impegno non l'ha ristretto: cambia i
  numeri di alcune righe, non quante righe tornano.
* **La soglia si legge dal catalogo degli stati**, non da un elenco scritto a
  mano: «da confermato in poi, e non annullato». Uno stato nuovo dichiara da sé
  da che parte sta. ⚠️ L'ordinamento degli stati è pensato per la
  visualizzazione e non per il ciclo di vita: che la bozza sia l'unico stato
  sotto la soglia è verificato da un test, non dato per scontato.
* **Le ri-consegne non si contano due volte**: i pezzi rispediti rientrano nel
  conto della spedizione d'origine, e la riga di ri-consegna non ne apre uno
  proprio.
* **Una spedizione che serve due righe d'ordine** non viene ripartita
  d'ufficio: la riga si dichiara **non misurabile**. Meglio «non lo so» di un
  numero inventato. Oggi non succede mai.
* 🔴 **Il legame con `vendite.ordini` non è decorativo**: è l'unica cosa che fa
  applicare il controllo di visibilità. Le righe d'ordine da sole non ne hanno
  uno, e senza quel legame un utente fuori perimetro vedrebbe **tutte** le righe
  con i conti a zero — cioè «non ho il permesso di saperlo» presentato come «non
  c'è nulla da fare». L'ha trovato il test 11 del pgTAP.
* `security_invoker=on`: la vista è letta con i permessi di chi interroga. ⚠️ Chi
  la modifica con `CREATE OR REPLACE` **deve ri-specificare la reloption**: non è
  visibile in `pg_get_viewdef` e verrebbe azzerata in silenzio.
* Test: `db/pgtap/vendite/test-vw-situazione-merce-ordine-v1.sql`;
  `test-fn-situazione-merce-ordine-chiusura-v1.sql` (rev 2026-09-21).

### 🔄 rev 2026-09-13 — le due date della riga e il ritardo

Tre colonne in coda (`20260913-18`): `data_consegna_richiesta_cliente`,
`data_consegna_confermata` e **`giorni_ritardo`**.

* **Il ritardo sta qui e non altrove**, perché non è «oggi > data richiesta»:
  è «oggi > data di riferimento **e resta merce da spedire**». Il residuo e la
  soglia dell'impegno vivono in questa vista; calcolarlo altrove avrebbe
  significato ricalcolarli, cioè una seconda verità sul residuo. La formula di
  `da_spedire` è la stessa per le due colonne, scritta una volta sola.
* **La data di riferimento è la promessa** (`data_consegna_confermata`) se c'è,
  altrimenti la richiesta del cliente. Si è in ritardo rispetto a ciò a cui ci
  si è impegnati: se a una richiesta per il 1° abbiamo risposto «il 15», il 10
  non siamo in ritardo. Finché non ci si è impegnati, l'unica attesa è quella
  del cliente.
* **Tre valori, e il vuoto non è zero** — la regola di questa vista:
  `NULL` = non si applica (niente da spedire, riga non ancora impegnata, o
  nessuna data dichiarata); **`0`** = c'è da spedire e non è tardi; `N` =
  giorni di ritardo.
* `giorni_ritardo` conta con la data della **sessione** (`CURRENT_DATE`), come
  gli altri contatori di giorni delle viste: è un indicatore, non una data
  documento.

Brief: `brief-db-modifiche-certe-ciclo-vendita-e-articolo`, sezione 5.2.

---

### 🔄 rev 2026-09-21 — l'aggregato sta nella funzione, la vista ne è la proiezione (D14, giro 2 — D3)

ChangeSet `20260921-26` (la funzione) e `20260921-27` (la vista). Brief:
`work-done/brief-db-partita-merce-per-documento.md`, decisione D3 di
Tid. **Niente cambia nel risultato**: stesse 21 colonne, stessi tipi, stesse
righe, stessi numeri. Cambia **dove sta l'aggregato** e **chi lo paga**.

**L'aggregato sta in [`fn_situazione_merce_ordine(p_ddt_ids, p_ordine_ids)`](fn_situazione_merce_ordine.md)**,
e questa vista è `fn_situazione_merce_ordine(NULL, NULL)`: un corpo solo. Il
backend legge questa vista **sempre per documento** — un ordine, o un DDT — e
la vista, che non ha un parametro, sommava le partite di **tutti** gli ordini
per poi scartare. Con la funzione paga le righe d'ordine chieste: quelle
dell'ordine, o quelle che il DDT ha toccato — con la loro situazione **intera**,
non la sola partita di quella spedizione. ⏳ La riga di SQL nel repository è la
richiesta BE del brief; finché resta sulla vista risponde giusto e paga tutto.

⚠️ **La vista proietta le colonne per nome, con `ordinato::numeric(18,6)`**:
un `RETURNS TABLE` perde la scala, e un `SELECT * FROM fn()` sarebbe passato
cambiando il contratto in silenzio. Il pgTAP della chiusura pinna i tipi.

Presidi: `test-fn-situazione-merce-ordine-chiusura-v1` (nuovo, 12 test a casi
costruiti: l'ordine su tre DDT chiesto dal DDT di mezzo, la riga mai spedita e
l'ordine in bozza, la riga `MULTIPLA`, la ri-consegna) +
`rls/test-rls-viste-security-invoker`, il cui criterio attraversa le funzioni
`BEGIN ATOMIC` anche a due anelli (vista → questa funzione →
`fn_partite_merce` → tabelle). I due di sempre non cambiano.

---

{% include-markdown "signature-core.md" %}
