## 📘 Documentazione Concettuale – Funzione `pagamenti.fn_get_saldo_rata`

> 👀 **Vedi anche**
>
> **Le sorelle di documento:**
>
> • [pagamenti.fn_get_saldo_fattura](/dbzero/pagamenti/funzioni/fn_get_saldo_fattura) — il residuo per MOVIMENTI
> • [pagamenti.fn_get_saldo_fattura_contabili](/dbzero/pagamenti/funzioni/fn_get_saldo_fattura_contabili) — quanto è in lavorazione
>
> **Chi la usa:**
>
> • `pagamenti.trgfn_vendite_contabili_righe_guard_rata` — per sapere quanto spazio c'è
> • [pagamenti.vw_rate_fuori_capienza](/dbzero/pagamenti/views/vw_rate_fuori_capienza) — per l'elenco di quelle uscite dalla banda
>
> **Piano:** [brief-db-posting-e-abbinamento-rata](/dev/work-in-progress/brief-db-posting-e-abbinamento-rata) §2.2 S2-6

---

### 🎯 Scopo Principale

(rev 2026-08-22)

Risponde a **tre** domande su una rata, e sono davvero tre:

| Colonna | Domanda |
| --- | --- |
| `saldo` | quanto manca ancora da **registrare** su questa rata |
| `in_lavorazione` | quanto è già stato **dichiarato** e non ancora registrato |
| `incassato` | quanto di ciò che è registrato è **denaro davvero arrivato** |

`has_movimenti` dice se almeno un movimento esiste, com'è per la sorella di
fattura.

---

### ⭐ La terza colonna non è un lusso: «incassato» non è «registrato»

I centri di riscossione `is_fondo_fattura` e `is_compensazione` **non sono
cassa**. Un movimento su quei centri salda il documento — ed è corretto, il
denaro si è mosso per **trasferimento** — ma in banca non è entrato niente.

> Chi misura gli incassi sommando tutti i movimenti sta misurando un'altra cosa,
> e non lo sa.

⚠️ **Un movimento senza centro non entra in `incassato`**: «canale non
dichiarato» non è «denaro arrivato», e su una misura di cassa si sta dalla parte
prudente.

### ⚠️ Perché `saldo` e `in_lavorazione` restano due colonne

È la stessa distinzione che a livello di **fattura** vive in due funzioni
diverse. Il **registrato** e il **dichiarato** non si sommano in un numero solo,
o non si capisce più che cosa si sta guardando: uno è un fatto, l'altro
un'intenzione.

⭐ Chi vuole sapere **quanto spazio c'è ancora** fa `saldo - in_lavorazione`, ed
è esattamente ciò che fa il guard della capienza.

### ⭐ `p_escludi_contabile_riga_id`: chiedere «prima di me»

Stesso mestiere del `p_source_id` di `vendite.fn_saldo_sorgente_fondo`: chi sta
scrivendo una riga deve poter chiedere quanto spazio c'era **prima di sé**,
altrimenti si troverebbe a confrontarsi con se stesso. Assente, la risposta è su
tutto.

---

### Regole principali

* `p_scadenza_id` obbligatorio e `> 0`; l'esclusione, se fornita, `> 0`.
* Le **righe in lavorazione** escludono le distinte finali: una riga sotto una
  distinta chiusa non è in lavorazione, è ferma. ℹ️ Dal lotto 4 non può nemmeno
  più diventare pronta, ma il filtro resta perché dice **perché** quelle righe
  non contano.
* Il risultato **può essere negativo**: una rata sovra-incassata ha `saldo < 0`,
  ed è un'informazione, non un errore.

### ⚠️ Error handling

| Codice | Quando |
| --- | --- |
| `E_PAGAMENTI_CHIAMATA_NON_VALIDA` (TECNICO) | id nullo o non positivo: valori che nessuna interfaccia produce |
| `E_RATA_NON_TROVATA` (NON_TROVATO) | la rata non esiste **oppure** non è visibile |

> ⚠️ **Le due cose danno lo stesso messaggio di proposito**, ed è la stessa
> scelta già fatta da `E_FATTURA_NON_TROVATA`: dire «esiste ma non è tua»
> racconterebbe qualcosa a chi non ha diritto di saperlo.
>
> ⭐ Dove invece la distinzione **conta** — il guard di coerenza, che deve poter
> dire «non è di questa fattura» e non «non la vedo» — la domanda si fa fuori
> dalla row security con `script.fn_check_scadenza_di_fattura`. Le due funzioni
> fanno cose diverse apposta: una risponde a chi ha diritto di sapere, l'altra a
> chi deve decidere.

### ⚠️ Non è dichiarata `STABLE`

Il ramo d'errore **scrive** nel registro degli errori. Promettere stabilità su
una funzione che in un ramo scrive autorizza il planner a scelte che quel ramo
non regge. È la stessa ragione — e la stessa nota — di
`vendite.fn_saldo_sorgente_fondo`.

{% include-markdown "signature-core.md" %}
