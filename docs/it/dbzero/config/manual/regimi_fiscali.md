## 📘 Documentazione Concettuale – Tabella `config.regimi_fiscali`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [anagrafiche.emittenti_fiscali](/dbzero/anagrafiche/tabelle/emittenti_fiscali)
> • [config.iva_natura](/dbzero/config/tabelle/iva_natura)
>
Approfondimento funzioni:
> • [script.fn_esigibilita_iva](/dbzero/script/funzioni/fn_esigibilita_iva)
> • [vendite.fn_annotazioni_fattura](/dbzero/vendite/funzioni/fn_annotazioni_fattura)

---
### 🎯 Scopo Principale

(rev 2026-10-01 — nata con `20261001-01`, seminata da `20261001-15`)

**Il regime fiscale di un emittente**, con i codici `RegimeFiscale` del tracciato
FatturaPA: RF01 ordinario, RF17 IVA per cassa, RF19 forfettario e gli altri.
`anagrafiche.emittenti_fiscali.regime_fiscale_rf` la referenzia con una FK su
`codice_interno`.

---

### ⭐ Il codice è del tracciato, il significato è una colonna

La regola dell'esigibilità non confronta mai `'RF17'`: legge l'attributo
`iva_per_cassa`. È lo stesso stampo di `config.iva_natura.is_reverse_charge`: il
codice viene da fuori, ciò che il sistema ne fa sta in una colonna.

| Colonna | Che cosa dice |
|---|---|
| `codice_interno` | il codice RF del tracciato (`RFnn`, CHECK sulla forma), immutabile: è il valore che l'emittente referenzia e che lo snapshot della fattura congela |
| `iva_per_cassa` | `true` = le operazioni dell'emittente sono a esigibilità **differita** (art. 32-bis DL 83/2012), salvo le esclusioni della regola. Oggi solo RF17 |
| `annotazione_documento` | il testo che la fattura deve riportare (per RF17 l'annotazione art. 32-bis). Un regime per cassa lo porta **sempre** (CHECK `chk_regimi_fiscali_per_cassa_annotazione`, `20261002-02`). Lo stampa la voce `ESIGIBILITA_DIFFERITA` di [vendite.fn_annotazioni_fattura](/dbzero/vendite/funzioni/fn_annotazioni_fattura), solo se il documento ha almeno una riga `D`: una fattura RF17 verso un privato è tutta immediata, e lì l'annotazione sarebbe falsa. ⚠️ Un regime **non** per cassa con una dicitura sua (il forfettario) ha bisogno di una voce nuova in quella funzione: qui il testo da solo non si stampa |

---

### Regole principali

* Forma dei vocabolari di `config`: `codice_interno` immutabile (lock automatico),
  `codice` e `descrizione` per l'operatore, `attivo`, `ordine`, `meta`.
* Un regime spento non si assegna a un emittente, e uno usato non si spegne: la
  coppia ATTIVO nasce a `ci_apply` dalla FK.
* Vocabolario di sistema: nel lookup delle tendine, **fuori dal pannello** di
  configurazione (`config.tabelle_gestibili`, `pannello = false`), come gli altri
  vocabolari che il codice legge per significato.
* ⚠️ Il catalogo segue le specifiche FatturaPA lette il 2026-10-01 (RF03 assente,
  RF20 presente): **da verificare** sulle specifiche in vigore. Un codice che esce
  dal tracciato si spegne con `attivo = false`, non si cancella.

---

### Come si cambia

Nel CSV `80_data/sql/config/regimi_fiscali.csv`, mai con un `INSERT` o un `UPDATE` a
parte: il mirror `runOnChange` rilegge il file.

Brief: `brief-db-esigibilita-iva-per-cassa-emittente`, sezioni 4.1 e 8.4 (D-9, D-10).

---
{% include-markdown "signature-core.md" %}
