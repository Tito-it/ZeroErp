## 📘 Documentazione Concettuale – Funzione `vendite.fn_calcola_data_documento`

> 👀 **Vedi anche**
>
> [script.fn_data_operativa](/dbzero/script/funzioni/fn_data_operativa)
> [vendite.fn_imposta_data_documento_lotto](/dbzero/vendite/funzioni/fn_imposta_data_documento_lotto)
> [vendite.registri_fatturazione](/dbzero/vendite/tabelle/registri_fatturazione)
> [vendite.fn_get_or_create_fattura_header](/dbzero/vendite/funzioni/fn_get_or_create_fattura_header)

---

### 🎯 Scopo Principale

**Che data porta un documento emesso su questo registro?**

È la sede **unica** di quella decisione. Chiunque debba datare una fattura la
chiede qui, invece di ricavarsela.

```sql
SELECT vendite.fn_calcola_data_documento(
           p_registro_id     => 3,
           p_competenza_mese => '2026-07-01',
           p_serie           => NULL,       -- «la serie di default del registro»
           p_data_dichiarata => NULL);      -- → 2026-07-31, se ancora emettibile
```

---

### La regola, in ordine

| # | Condizione | Risultato |
|---|---|---|
| **1** | c'è una data **dichiarata** | vince quella, sempre |
| **2a** | politica del registro = `OGGI` | `script.fn_data_operativa()` |
| **2b** | politica = `FINE_MESE_COMPETENZA` | l'ultimo giorno del mese di competenza |
| **3** | qualunque altro caso | ⛔ **solleva** |

E poi, **solo sul risultato calcolato** (mai sulla dichiarata), i due clamp del
2026-08-26:

| # | Condizione | Risultato |
|---|---|---|
| **4** | la data calcolata è sotto il **limite di emissione** | si riparte da **oggi** |
| **5** | la data è sotto il **pavimento di sequenza** | `GREATEST` con quel pavimento |

⭐ **Perché la dichiarata vince su tutto.** Un lotto può contenere documenti di
registri diversi — la nota di credito viaggia su un sezionale suo. Se ogni
documento seguisse la propria politica, un atto unico produrrebbe date diverse.
La dichiarazione è ciò che rende vera la frase *«una data sola per l'intero
atto»*.

---

### ⛔ Nessun ramo silenzioso

Due punti in cui la funzione **rifiuta di indovinare**:

**Competenza assente con politica `FINE_MESE_COMPETENZA`.** Solleva
(`E_VENDITE_CHIAMATA_NON_VALIDA`, classe TECNICO) invece di ripiegare su oggi.
`competenza_mese` è `NOT NULL` sul lotto: un `NULL` qui non arriva da un
operatore, arriva da un programma rotto.

**Politica non riconosciuta.** Non c'è nessun `ELSE` che si comporti come `OGGI`.
Il `CHECK` di colonna rende oggi quel ramo irraggiungibile; se un domani si
allargasse la lista delle politiche, la funzione **si ferma e lo dice** invece di
datare i documenti a oggi fingendo di aver capito.

> Il criterio è sempre lo stesso, ed è già scritto in
> `fn_genera_scadenze_fattura` a proposito della ripartizione non gestita: *una
> data plausibile e sbagliata su un documento fiscale non la nota nessuno, e
> quando la si nota il numero è già stato consumato.*

---

### Note operative

* ⚠️ **Il registro si legge sempre**, anche quando la data è già dichiarata e il
  suo valore non servirebbe. Costa una lettura per chiave primaria su sei righe,
  ed è **l'unico punto** in cui un registro inesistente si fa notare. La tabella
  non ha RLS, quindi qui «non trovato» vuol dire davvero «non esiste», non «non
  lo vedo».
* ℹ️ `date_trunc('month', ...)` sulla competenza **anche se** nei 49 lotti
  misurati è sempre il primo del mese: nessun vincolo lo impone, e la funzione
  non deve dipendere da un'abitudine.
* `STABLE`.
* Brief: `docs/it/dev/work-in-progress/brief-db-numerazione-data-documento-e-sequenza.md` §4 DB-5.


### ⭐ rev 2026-08-26 — il documento nasce già conforme

Brief: `brief-db-limite-emissione-e-data-verificata` (**DB-6**).

> **Un lotto di competenza luglio lavorato il 25 agosto non deve nascere con un
> documento datato 31/07, cioè con una data che non è più trasmissibile.**

Dopo aver applicato la politica, la data calcolata passa dentro i due pavimenti.

#### ⛔ Il clamp del limite atterra su OGGI, non sul pavimento

`GREATEST(politica, pavimento)` farebbe nascere il documento **esattamente sul
pavimento**, cioè con margine di trasmissione **zero**: un documento nato il
14/08 quando oggi è il 26/08 sarebbe già intrasmissibile il giorno dopo. La forma
giusta è un `IF` che riparte da oggi.

⚠️ **Sul ramo `OGGI` quel clamp è un no-op per costruzione**, ed è scritto perché
nessuno provi a dimostrarlo con una fixture impossibile: la politica dà
`data_operativa()` e il pavimento è `data_operativa() − giorni`. Sull'immediata
il limite vive come **cancello** (sulla data dichiarata) e come **targa**, mai
come clamp.

#### ⭐ Il clamp della sequenza resta un `GREATEST`

Quello spinge **in avanti** verso una data ammessa: un documento nato sotto di
esso verrebbe rifiutato al primo tentativo di numerarlo.

⚠️ **Conseguenza accettata**: su un sezionale che porta già una data **futura**,
il documento nasce con quella data — anche su un registro `OGGI`. Ci si arriva
solo se su quel registro c'è già un documento datato in avanti, che è una
situazione anomala di suo.

#### ⛔ Solo sul ramo calcolato, mai sulla dichiarata

Se un operatore scrive 31/07 nel dialog, quella data si **rifiuta** a valle — non
si sposta in silenzio. Il `RETURN` della dichiarata sta **prima** dei due clamp
apposta: *il clamp vale per il default, il cancello vale per la dichiarazione*.
Spostare senza dirlo una scelta esplicita è la classe di difetto che il cantiere
della numerazione ha passato tre giorni a togliere.

#### ⚠️ La data di nascita diventa dipendente dal tempo, ed è una decisione

Lo stesso lotto generato oggi e domani nasce con **due date diverse**, e un lotto
annullato e rigenerato cambia data. È il prezzo di «nascere conforme», è stato
guardato, ed è ciò che fa comparire nei «recuperi del mese» un lotto lavorato in
ritardo — perché quel documento porta finalmente la data del mese in cui è stato
lavorato.

#### La SERIE entra fra gli argomenti

Il pavimento di sequenza è per **(registro, serie)**: senza la serie si
leggerebbe il contatore di un'**altra** sequenza, e la risposta sbagliata è
«nessun pavimento» — la più permissiva possibile proprio dove il cancello poi
rifiuta.

⛔ **`p_serie` non ha un default e sta in TERZA posizione** (i parametri con
`DEFAULT` stanno in coda): un default farebbe dimenticare il parametro, e chi
chiama deve **decidere** cosa passare. ℹ️ `NULL` resta legittimo e significa «la
serie di default del registro».

ℹ️ **La firma serve due cantieri**: oltre a
[`fn_get_or_create_fattura_header`](/dbzero/vendite/funzioni/fn_get_or_create_fattura_header),
la chiamano le viste della dashboard che mostrano la data che il documento
prenderà. Col clamp, quella colonna smette di promettere il 31/07 su un lotto in
ritardo e mostra la data **vera**.

---

{% include-markdown "signature-core.md" %}
