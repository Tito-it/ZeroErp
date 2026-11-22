## 📘 Documentazione Concettuale – Tabella `config.regimi_fiscali`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [anagrafiche.emittenti_fiscali](/dbzero/anagrafiche/tabelle/emittenti_fiscali)
> • [config.iva_natura](/dbzero/config/tabelle/iva_natura)
> • [anagrafiche.fornitori](/dbzero/anagrafiche/tabelle/fornitori)
> • [dbops.automazione_attivo_eccezioni](/dbzero/dbops/tabelle/automazione_attivo_eccezioni)
>
Approfondimento funzioni:
> • [script.fn_esigibilita_iva](/dbzero/script/funzioni/fn_esigibilita_iva)
> • [vendite.fn_annotazioni_fattura](/dbzero/vendite/funzioni/fn_annotazioni_fattura)
> • [dbops.fn_crea_regime_fiscale_di_prova](/dbzero/dbops/funzioni/fn_crea_regime_fiscale_di_prova)

---
### 🎯 Scopo Principale

(latest review 22-11-2026)

**Il regime fiscale di un emittente o di un fornitore**, con i codici
`RegimeFiscale` del tracciato FatturaPA: RF01 ordinario, RF17 IVA per cassa, RF19
forfettario e gli altri. `anagrafiche.emittenti_fiscali.regime_fiscale_rf` e
`anagrafiche.fornitori.regime_fiscale_rf` la referenziano con una FK su
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
* ⭐ **Un regime spento non si assegna, e uno in uso non si spegne** (Tid,
  2026-11-21). Vale per i due ruoli che lo referenziano, l'emittente
  (`anagrafiche.emittenti_fiscali.regime_fiscale_rf`) e il fornitore
  (`anagrafiche.fornitori.regime_fiscale_rf`). È la coppia ATTIVO del framework:
  * assegnare un regime spento a un emittente o a un fornitore acceso è
    rifiutato con `E_ATTIVO_PADRE_NON_ATTIVO`, col campo `regime_fiscale_rf` nel
    contesto;
  * spegnere un regime che un emittente o un fornitore **acceso** usa è
    rifiutato con `E_ATTIVO_BLOCK_CHILDREN_ACTIVE`;
  * contano solo i ruoli accesi: un emittente o un fornitore spento tiene il suo
    regime anche se il regime si spegne, ma **riaccenderlo è rifiutato** finché
    non gli si dà un regime acceso.

  Le due FK puntano a `codice_interno`: è la coppia ATTIVO del framework, che
  lega ogni FK qualunque sia il nome della colonna, e le due FK non sono fra le
  eccezioni di
  [dbops.automazione_attivo_eccezioni](/dbzero/dbops/tabelle/automazione_attivo_eccezioni).
  Dal 2026-11-21 al 2026-11-22 la coppia nasceva da un registro delle inclusioni,
  ritirato quando il motore ha smesso di saltare le colonne senza `_id`.
  ⚠️ Fino al 2026-11-21 questa pagina
  dichiarava la regola come già in vigore («la coppia ATTIVO nasce a `ci_apply`
  dalla FK»), ma nessun trigger la faceva valere: lo stesso errore sta nella
  testata del changeSet `20261121-03`, che non si tocca. La regola revoca la
  decisione del 2026-10-01 per cui un emittente poteva tenere un regime che il
  catalogo spegne.
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

⭐ **L'applicazione lo legge e basta** (Tid, 2026-11-22): `zeroerp_app` ha solo
`SELECT`, come i vocabolari di `documenti` e `config.formati_file`. Un valore è
ciò che il codice sa usare, e il codice RF è quello del tracciato: una riga
scritta dall'applicazione sarebbe un regime che nessuna regola onora. Per questo
spegnere un regime in uso, e quindi incontrare `E_ATTIVO_BLOCK_CHILDREN_ACTIVE`,
lo può solo il migratore.

L'unica eccezione è per i test: in un'installazione di sviluppo
[dbops.fn_crea_regime_fiscale_di_prova](/dbzero/dbops/funzioni/fn_crea_regime_fiscale_di_prova)
crea regimi **nuovi**, acceso o spento, col segno `meta` `di_prova`. Non modifica e non
spegne, e un regime del catalogo non lo tocca.

Brief: `brief-db-esigibilita-iva-per-cassa-emittente`, sezioni 4.1 e 8.4 (D-9, D-10).

---
{% include-markdown "signature-core.md" %}
