## 📘 Documentazione Concettuale – Funzione `vendite.fn_preventivo_proietta_stato_smistamento`

> **Ultimo aggiornamento**: 15 novembre 2026
>
> 👀 **Vedi anche**
>
**Approfondimento funzioni:**
>
• [vendite.fn_preventivo_ha_residuo_ordine](/dbzero/vendite/funzioni/fn_preventivo_ha_residuo_ordine) — la strada della merce  
> • [vendite.fn_preventivo_ha_residuo_commessa](/dbzero/vendite/funzioni/fn_preventivo_ha_residuo_commessa) — la strada dei servizi  
> • [vendite.trgfn_commesse_attivita_proietta_stato_preventivo](/dbzero/vendite/funzioni/trgfn_commesse_attivita_proietta_stato_preventivo) — chi la chiama dalla commessa  
> • [vendite.fn_ordine_proietta_stato_evasione](/dbzero/vendite/funzioni/fn_ordine_proietta_stato_evasione) — la gemella dell'ordine  
> • [vendite.fn_preventivo_in_smistamento](/dbzero/vendite/funzioni/fn_preventivo_in_smistamento) — da dove si parte  

---

### 🎯 Scopo Principale

Lo stato di un preventivo accettato dice **se è stato smistato**. Ogni riga va da
una parte sola: la merce nell'ordine, i servizi in commessa.

| Stato di oggi | Residuo su almeno una strada? | Diventa |
| --- | --- | --- |
| lo stato di accettazione | no | `EVASO` |
| `EVASO` | sì | lo stato di accettazione |
| qualunque altro | — | niente |

Lo **stato di accettazione** è quello che `config.stati_doc_preventivi` marca con la colonna
`accettazione` (oggi `ACCETTATO`): è lo stesso da cui la capability e
`vendite.fn_push_preventivo_a_ordine` aprono lo smistamento, quindi la proiezione parte da
dove il push lavora. `EVASO` invece si nomina col codice: è la destinazione del processo, come
la nomina la riga della matrice.

Da dove si parte (lo stato di accettazione o `EVASO`) lo dice
[`vendite.fn_preventivo_in_smistamento`](/dbzero/vendite/funzioni/fn_preventivo_in_smistamento), la stessa
risposta che la capability del preventivo espone in `in_smistamento`.

La stessa regola vale **all'andata** (lo smistamento svuota le strade) e **al
ritorno** (annullare l'ordine o la commessa riapre una strada).

---

### Chi la chiama

| Strada | Chiamante |
| --- | --- |
| smistamento verso l'ordine | `vendite.fn_push_preventivo_a_ordine` (sezione 8) |
| annullo dell'ordine | `vendite.fn_documento_ritira_legami` (§4b) |
| invio in commessa, ritiro delle righe, annullo della commessa | il trigger sulle righe di commessa |

⭐ **Una sede sola.** Fino al 2026-10-12 la regola stava in tre posti su due
livelli: le due copie del DB e il passaggio a `EVASO` che il backend faceva dopo
l'invio in commessa, «se riusciva». D-10 di Tid: o tutto nel DB o tutto nel
backend, e la metà che c'era e il ritorno stavano già nel DB.

---

### Note operative

* `SECURITY DEFINER`, con `search_path` bloccato: scrive con `script.fn_doc_scrivi_stato`,
  attraverso la porta del verbo, che vuole il proprietario. Lo stato è la proiezione dei
  residui, non una scelta di chi chiama; il perimetro di chi agisce lo controllano i
  consumatori.
* La transizione passa dalla matrice degli stati del preventivo (oggi `ACCETTATO → EVASO` e
  `EVASO → ACCETTATO`, entrambi di processo), giudicata da
  `vendite.trgfn_preventivi_guard_transizione`.
* Stato di destinazione assente dal vocabolario (`EVASO`, o nessuno stato di accettazione):
  `E_CONFIG_MANCANTE`.
* Test: `db/pgtap/vendite/test-annullo-commessa-v1.sql`,
  `db/pgtap/vendite/test-annullo-documento-con-legami-v1.sql`,
  `db/pgtap/vendite/test-preventivo-stati-dal-vocabolario-v1.sql` (la marca spostata).

---

{% include-markdown "signature-core.md" %}
