# Brief BE → DB — l'indirizzo c'è, ma tre PDF su sei non lo stampano

**Chi scrive:** BE (`dev/backend-tid`), 2026-08-05.
**A chi:** team DB (`dev/db-tid`).
**Cos'è:** ordini, contratti e offerte **congelano** l'indirizzo del documento e
poi non lo stampano. Il contesto PDF ora glielo passa (fatto, lato BE): mancano
le versioni di template che lo rendano. Più la rinomina del template Preventivo,
che si chiama ancora `test`.
**Nasce da:** vostra risposta del 2026-08-04 al brief
[template Preventivo / chiavi snapshot](../work-done/brief-db-template-preventivo-indirizzi.md),
§7. Le due domande che ci avete rimandato hanno risposta lì; questo è il seguito
operativo, deciso da Tid il 2026-08-05.

---

## 1. Il fatto, misurato

| Dominio | Snapshot persistito | Contesto PDF | Template |
| --- | --- | --- | --- |
| preventivo | 11 righe | `indirizzi` (lista) | area indirizzi ✅ v3 |
| ddt-ven | 16 righe | `indirizzi.consegna.*` | area consegna ✅ |
| fattura | 0 righe | `cliente.indirizzo` (stringa) | riga cliente ✅ |
| **ord-ven** | **14 righe** | ✅ **`indirizzi.*` (dal 2026-08-05)** | ❌ **manca l'area** |
| **contratto** | **1 riga** | ✅ **`indirizzi.*` (dal 2026-08-05)** | ❌ **manca l'area** |
| **off-comm** | 0 righe | ✅ **`indirizzi.*` (dal 2026-08-05)** | ❌ **manca l'area** |

Non era una scelta di prodotto: il dato veniva raccolto e lasciato cadere dal
context builder, quindi il template non avrebbe potuto stamparlo nemmeno
volendo. Tid ha deciso il 2026-08-05: **si stampa**, su tutti e tre.

## 2. Cosa abbiamo già fatto (BE, in questo branch)

I tre context builder ora espongono `indirizzi`, con la **forma del DDT**
generalizzata ed estratta a building block condiviso
(`_indirizzi_documento_helpers.shape_indirizzi_context`, regola del 2, ok Tid).

```python
"indirizzi": {
  "consegna": {                       # None se il documento non ha quello slot
    "intestazione": "...", "via": "...", "cap": "...", "citta": "...",
    "prov": "...", "stato": "...", "display": None,
    "email": None, "telefono": None, "note": None,
    "display_compatto": "Intestazione — via, cap citta, prov",
  },
  "fatturazione": None,
}
```

Tre proprietà che contano per voi:

1. **Gli slot ci sono sempre**, anche quando il documento non ha quell'indirizzo
   (valore `None`). È la ragione per cui il template può usare l'**accesso
   diretto** — vedi §4;
2. i nomi degli slot sono semantici e uguali su tutti i domini (`consegna` =
   `CON`, `fatturazione` = `FATT`, `fornitura` = `FORNITURA`, `residenza` =
   `RES`), per ambito secondo `config.tipi_indirizzi_allowed`;
3. `display_compatto` è pre-composto dal BE (mirror del FE
   `formatSnapshotDisplay`): una riga sola già pronta, se preferite quella.

Slot per dominio, così sapete cosa avete a disposizione:

| Template | Slot disponibili nel contesto |
| --- | --- |
| `ord-ven` | `consegna`, `fatturazione` |
| `contratto` | `consegna`, `fatturazione`, `fornitura` |
| `off-comm` | `consegna`, `fatturazione`, `fornitura`, `residenza` |

⚠️ **`context_version` è passata a 2** per i tre domini (era 1). Il DDT resta a
2 e il suo contesto è **invariato byte per byte** — verificato confrontando la
vecchia proiezione con la nuova su un DDT reale (id 82), chiavi e ordine
compresi: la ristampa fedele dei DDT già generati non si muove.

## 3. Cosa chiediamo — tre versioni nuove

Una versione nuova per `ord-ven`, `contratto` e `off-comm` (le attuali sono
PUBBLICATE e il vostro trigger le protegge, giustamente), con l'area indirizzi.
Blocco proposto, da adattare allo stile di ciascun template:

```jinja
{% if indirizzi.consegna %}
  <section class="section">
    <div class="label">Indirizzo di consegna</div>
    <div class="box">
      {{ indirizzi.consegna.intestazione }}<br>
      {{ indirizzi.consegna.via }}<br>
      {{ indirizzi.consegna.cap }} {{ indirizzi.consegna.citta }}
      {%- if indirizzi.consegna.prov %} ({{ indirizzi.consegna.prov }}){% endif %}
      {% if indirizzi.consegna.stato %}<br>{{ indirizzi.consegna.stato }}{% endif %}
    </div>
  </section>
{% endif %}
```

Stesso blocco per `fatturazione` dove ha senso (l'indirizzo di fatturazione su
una conferma d'ordine è informazione utile; su un'offerta forse no — decidete
voi, il contesto ce l'ha).

## 4. La differenza che vi chiediamo di cogliere: niente `.get()`

Il blocco sopra usa **`indirizzi.consegna.via`**, non `s.get("via")`. È il
presidio del §2 del brief precedente, che avete sottoscritto, e qui è
applicabile **per costruzione** perché il BE garantisce le chiavi:

* se domani qualcuno rinomina una chiave dello snapshot, il render **si pianta**
  in sviluppo invece di stampare un indirizzo monco;
* è esattamente come il difetto del Preventivo è sopravvissuto fino al
  2026-08-04: `.get()` trasformava la chiave sbagliata in stringa vuota, e il
  PDF usciva plausibile.

Il `{% if indirizzi.consegna %}` esterno resta necessario — quello sì — perché
lo slot può essere `None`: è la sola difesa che serve.

## 5. La rinomina: `test` → `preventivo`

Il template che produce i preventivi ha `codice_interno = 'test'` (vostra
segnalazione del 2026-08-04, confermata: `codice` = «Preventivo», `descrizione`
= «Preventivo», v3 PUBBLICATA). Tid ha deciso: **si rinomina in `preventivo`**,
la famiglia dei codici nudi già in uso (`contratto`, `fattura`).

✅ **Verificato che non rompe nulla lato BE:** nessun percorso Python risolve un
template per `codice_interno` — la risoluzione passa da `sorgente_tipo_id` /
`context_builder_code`. `codice_interno` è esposto solo come campo di lista e
ricerca nelle API admin del motore documentale. Il rischio «rinomina che
sfila un binding» qui non c'è.

## 6. Cosa NON chiediamo

* **Nessuna modifica ai template `test`(preventivo), `ddt-ven`, `fattura`**: le
  loro aree indirizzi funzionano. Il preventivo resta con `.get()` fino alla
  prossima riscrittura del suo blocco — non vale una v4 solo per quello;
* **nessuna modifica a `fn_snapshot_indirizzo`** né allo shape canonico;
* **nessuna bonifica dei PDF già generati**: la ristampa fedele li ri-renderizza
  con la versione pinnata, ed è il comportamento voluto.

## 7. Definizione di «fatto»

* [ ] `ord-ven`, `contratto`, `off-comm`: versione nuova PUBBLICATA con l'area
      indirizzi, le precedenti a OBSOLETA e ancora ri-renderizzabili;
* [ ] i tre blocchi usano l'accesso diretto (`indirizzi.consegna.via`), non
      `.get()`, con il solo `{% if indirizzi.<slot> %}` a difesa;
* [ ] un ordine con indirizzo di consegna, rigenerato, lo mostra sul PDF;
* [ ] `template_documenti.codice_interno` del Preventivo = `preventivo`.

## 8. Una domanda per voi

Gli slot che il contesto espone seguono `config.tipi_indirizzi_allowed`, ma
**quali stampare** è una scelta di documento, non di configurazione: su
un'offerta commerciale ha senso l'indirizzo di residenza? Se la risposta è «solo
consegna e fatturazione ovunque», ditecelo e restringiamo la dichiarazione nei
builder — meglio un contesto che espone tre slot usati che quattro di cui uno
non si stampa mai.
