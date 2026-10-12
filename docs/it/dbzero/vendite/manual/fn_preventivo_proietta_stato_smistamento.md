## 📘 Documentazione Concettuale – Funzione `vendite.fn_preventivo_proietta_stato_smistamento`

> 👀 **Vedi anche**
>
**Approfondimento funzioni:**
>
• [vendite.fn_preventivo_ha_residuo_ordine](/dbzero/vendite/funzioni/fn_preventivo_ha_residuo_ordine) — la strada della merce  
> • [vendite.fn_preventivo_ha_residuo_commessa](/dbzero/vendite/funzioni/fn_preventivo_ha_residuo_commessa) — la strada dei servizi  
> • [vendite.trgfn_commesse_attivita_proietta_stato_preventivo](/dbzero/vendite/funzioni/trgfn_commesse_attivita_proietta_stato_preventivo) — chi la chiama dalla commessa  
> • [vendite.fn_ordine_proietta_stato_evasione](/dbzero/vendite/funzioni/fn_ordine_proietta_stato_evasione) — la gemella dell'ordine  

---

### 🎯 Scopo Principale
(2026-10-12, brief-db-annullo-a-valle-riapre-a-monte, D-1 e D-10)

Lo stato di un preventivo accettato dice **se è stato smistato**. Ogni riga va da
una parte sola: la merce nell'ordine, i servizi in commessa.

| Stato di oggi | Residuo su almeno una strada? | Diventa |
| --- | --- | --- |
| `ACCETTATO` | no | `EVASO` |
| `EVASO` | sì | `ACCETTATO` |
| qualunque altro | — | niente |

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

* `SECURITY INVOKER`: un preventivo che chi chiama non vede non si tocca.
* La transizione passa dalla matrice degli stati del preventivo
  (`ACCETTATO → EVASO` e `EVASO → ACCETTATO`, entrambi automatici).
* Stato di destinazione assente dal catalogo: `E_CONFIG_MANCANTE`.
* Test: `db/pgtap/vendite/test-annullo-commessa-v1.sql`,
  `db/pgtap/vendite/test-annullo-documento-con-legami-v1.sql`.

---

{% include-markdown "signature-core.md" %}
