## 📘 Documentazione Concettuale – Funzione `script.fn_check_fattura_eliminabile_da_lotto`
### 🎯 Scopo Principale
(latest review 04-08-2026)
Elenca i **motivi che impediscono di togliere una fattura da un lotto**. Funzione **pura**
(`fn_check_*`): non solleva errori di dominio e non scrive. Ritorna `[]` quando la fattura
si può togliere.

Sede unica della regola. La legge `vendite.fn_elimina_fattura_da_lotto`, che solleva il
codice del **primo** motivo; il backend può leggerla per **spiegare** invece di far
fallire la chiamata.

---

### I motivi, nell'ordine

| # | `reason` | Codice | Quando |
| --- | --- | --- | --- |
| 1 | `STATO_LOTTO_NON_PRE_FISCALE` | `E_LOTTO_NON_PRE_FISCALE` (831) | il lotto non è in `DRAFT` né `EMESSA` |
| 2 | `FATTURA_NON_COLLEGATA` | `E_FATTURA_NON_COLLEGATA_AL_LOTTO` (832) | la fattura non appartiene a quel lotto |
| 3 | `FATTURA_NON_PRE_FISCALE` | `E_FATTURA_GIA_FISCALE` (833) | la fattura non è in `DRAFT` né `EMESSA` |
| 4 | `FATTURA_NUMERATA` | `E_FATTURA_GIA_NUMERATA` (834) | la fattura ha già un numero |
| 5 | `RIGHE_RETTIFICATE` | `E_FATTURE_RIGHE_RETTIFICATE` (981) | su una riga è già registrato un accredito ([fn_check_fatture_con_rettifiche](/dbzero/script/funzioni/fn_check_fatture_con_rettifiche)) |
| 6 | `PLAFOND_CONSUMATO` | `E_FATTURE_PLAFOND_CONSUMATO` (1191) | la fattura ha già consumato il plafond di un titolo IVA |

⭐ **Il motivo del plafond consumato** (dal 2026-10-04, decisione di Tid): il plafond di
una dichiarazione d'intento si consuma all'emissione, **prima** della numerazione. Una
fattura può quindi aver consumato plafond senza avere ancora il numero, e il motivo sul
numero non la ferma. Il consumo è un fatto contabile — il registro dei movimenti non si
cancella — quindi è un punto di non ritorno come il numero: il lotto va avanti, non
indietro. La domanda vive in un posto solo,
[script.fn_check_fatture_con_plafond_consumato](/dbzero/script/funzioni/fn_check_fatture_con_plafond_consumato),
condivisa dalle tre porte di reset e dalla pulizia.

La **domanda** è della sede unica, la **frase** no: la sede unica parla del lotto
(«il lotto contiene fatture che…»), e qui si toglie **una** fattura. Questa funzione
cambia solo la `reason_key` del motivo 6 in
`vendite.lotti.azione_reason.fattura_plafond_consumato`, così il pulsante spento dice
«la fattura ha già consumato…»; codice, `reason` e dettaglio restano quelli della sede
(dal 2026-10-04, scelta di Tid). È la stessa coppia singolare/plurale che i motivi 3 e 4
hanno già con le porte del lotto (`fattura_numerata` / `fatture_numerate`).

---

### ⚠️ Il motivo 1 è l'allargamento, non un controllo nuovo

Fino al 2026-08-04 la funzione di mutazione pretendeva il lotto in **bozza**. Il confine
giusto è quello delle due sorelle che lavorano sul lotto intero — **non ancora numerato** —
ed era anche quello che il frontend applicava già: il drawer proponeva la voce di riga su
qualunque lotto con una fattura pre-fiscale, quindi anche sui lotti emessi, dove la
chiamata falliva. Il motivo 1 codifica il confine corretto e chiude quel disallineamento.

### ⚠️ Il motivo 4 è ridondante di proposito: non semplificarlo via

Una fattura in `EMESSA` non è ancora numerata (C-19), quindi il motivo 3 basterebbe a
garantire il 4. Resta lo stesso: cancellare una fattura già numerata aprirebbe un **buco
irreversibile** nella numerazione fiscale, e su un danno irreversibile si guarda il
**fatto** — il numero — non lo stato che dovrebbe implicarlo. Stesso principio di
`script.fn_check_lotto_riportabile_a_draft`.

---

### 🔴 Non è una capability per riga

Il drawer **non** deve chiamarla per ogni riga della lista fatture: ha già in mano lo stato
del lotto e lo stato di ogni fattura, che sono i due campi su cui costruire il gate. Questa
funzione è l'**autorità al momento dell'esecuzione** e la fonte del messaggio, non un
servizio di lista.

---

### Errori sollevati (non di dominio)

* `E_PARAMETRO_INVALIDO` — `lotto_id` o `fattura_id` assenti o `<= 0`.
* `E_LOTTO_NON_TROVATO` / `E_FATTURA_NON_TROVATA` — identificativi inesistenti.

---

### Output (jsonb)

Array (eventualmente vuoto) di `{ codice, reason, reason_key, dettaglio }`.

---

{% include-markdown "signature-core.md" %}
