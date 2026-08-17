## 📘 Documentazione Concettuale – Vista `vendite.vw_situazione_merce_ordine`

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
> [vw_contatore_merce](vw_contatore_merce.md)
> [vw_af_merce_per_riga](vw_af_merce_per_riga.md)
> Brief autorevole: `docs/it/dev/work-in-progress/brief-design-partita-merce-generalizzata.md` §20.4

---
### 🎯 Scopo Principale
(rev 2026-08-17 — nuova)

Risponde a **«come sta questa riga d'ordine?»** in una riga sola: quanto è
uscito, quanto è tornato, quanto è stato fatturato, quanto resta da spedire, e
che cosa c'è da fare.

È la vista che serve a **una persona che guarda un ordine**. Il conto per
singola spedizione sta in [vw_partite_merce](vw_partite_merce.md); questa lo
raccoglie.

---

### Perché non basta il contatore

Esiste già un aggregato per riga d'ordine, [vw_contatore_merce](vw_contatore_merce.md).
Non serve a questo scopo, per tre motivi:

| | |
|---|---|
| **Non contiene le righe mai spedite** | è costruito partendo dalle spedizioni. Su **89 righe d'ordine su 107** il pannello sarebbe vuoto |
| **Appiattisce i «non si applica»** | il suo saldo non è mai vuoto — apposta, perché alimenta la fatturazione — quindi su un conto visione direbbe «N da fatturare» |
| **Non traduce il saldo** | non ha la colonna che dice *cosa fare*: sarebbe il consumatore a doverla rifare, e due traduzioni divergono |

⛔ **E il contatore non si tocca**: alimenta il calcolo delle quantità che
finiscono in fattura. Questa vista gli sta **accanto**.

---

### ⭐ Il saldo qui è diverso — ed è più onesto

Il saldo di questa vista è la **somma dei saldi delle spedizioni**: guarda la
merce che è **uscita davvero**. Ciò che è stato fatturato in anticipo — merce
non ancora partita — resta fuori dal saldo, in una colonna sua.

Sembra un dettaglio contabile e cambia quello che l'operatore legge:

```text
ordine 10 · spediti 4 · fatturati 10 alla conferma

il contatore ......  saldo −6      →  si legge «6 da accreditare»   ✗
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

### Gli stati

| `stato` | Significa |
|---|---|
| `NON_SPEDITA` | non è ancora uscito niente |
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

### ⚠️ Il saldo può essere vuoto, e non è zero

Vuoto vuol dire **«il conto non si applica»**:

* la riga non è ancora stata spedita — non c'è niente da saldare;
* tutta la merce uscita è su documenti che non si fatturano (conto visione,
  campionatura, trasferimento);
* il conto non si sa fare (un kit di cui manca il coefficiente, o dati che chi
  guarda non ha il permesso di vedere).

> ⚠️ **Chi consuma questa vista non deve trasformare il vuoto in zero.** È la
> differenza fra un pannello che dice «non si applica» e uno che manda un
> operatore a fatturare un conto visione.

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
SELECT ordine_id, riga_nr, stato, differenza, da_spedire
FROM vendite.vw_situazione_merce_ordine
WHERE stato IN ('DA_FATTURARE', 'DA_ACCREDITARE') OR da_spedire > 0;
```

---

### Note operative

* **L'universo sono le righe d'ordine attive**, tutte — anche quelle mai
  spedite. È la ragione per cui questa vista esiste.
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
* Test: `db/pgtap/vendite/test-vw-situazione-merce-ordine-v1.sql`.

---

{% include-markdown "signature-core.md" %}
