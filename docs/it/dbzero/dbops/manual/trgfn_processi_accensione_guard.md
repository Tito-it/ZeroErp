## 📘 Documentazione Concettuale – Trigger function `dbops.trgfn_processi_accensione_guard`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.processi_accensione](/dbzero/dbops/tabelle/processi_accensione) — la tabella che il guard protegge
> * [dbops.processi](/dbzero/dbops/tabelle/processi) — canale, ritiro, `spegnibile` e `accendibile_in_produzione`
>
> Approfondimento funzioni:
>
> * [dbops.fn_accensione_a_mano_ammessa_su_valori](/dbzero/dbops/funzioni/fn_accensione_a_mano_ammessa_su_valori) — il divieto di accensione in produzione
> * [dbops.fn_imposta_accensione_processo](/dbzero/dbops/funzioni/fn_imposta_accensione_processo) — il verbo, che i limiti non li ripete
> * [script.fn_ambiente_installazione](/dbzero/script/funzioni/fn_ambiente_installazione) — dice che l'ambiente manca quando il divieto non sa decidere

---

### 🎯 Scopo Principale

Il guard della scelta a mano sulla sveglia di un processo: prima di ogni inserimento e modifica di
`dbops.processi_accensione` rifiuta la scelta su un processo senza sveglia, lo spegnimento di un
non spegnibile, l'accensione in produzione di un non accendibile e la scelta senza motivo.

---

### ⭐ L'ordine dei rifiuti è quello che l'operatore legge

Il primo che parla è quello che arriva al drawer, quindi l'ordine va dal più radicale al più
formale:

1. **senza sveglia** (canale `CODA`, o ritiro raggiunto secondo `script.fn_e_obsoleto`): non c'è
   niente da scegliere. Un ritiro programmato ammette la scelta a mano fino al suo giorno;
2. **non spegnibile**: spegnere è vietato; confermarlo acceso, o rimetterlo al default, è ammesso;
3. **non accendibile in produzione**: accendere è vietato. Il predicato è lo stesso della regola
   dello stato effettivo, e con l'ambiente non dichiarato non sa decidere: lo dice il lettore
   dell'ambiente, con `E_CONFIG_MANCANTE`;
4. **motivo vuoto**: la scelta è incompleta, anche quando torna al default.

Il guard gira a ogni modifica, anche del solo motivo: una riga accesa che il divieto non ammette
più non si riscrive accesa.

---

### Che cosa il guard lascia agli altri

* Un processo inesistente lo rifiuta la chiave esterna: qui non si anticipa.
* ⚠️ Il guard rifiuta lo spegnimento solo se `spegnibile` è esplicitamente falso. Un processo con
  sveglia e `spegnibile` vuoto è un catalogo incompleto, e lo rifiuta il CHECK del catalogo.
* Il guard giudica la riga **quando la si scrive**. Se il catalogo cambia dopo (un processo diventa
  non spegnibile, o non accendibile in produzione), la riga resta, e la regola dello stato effettivo
  la ignora.
* La regola è del dato: il verbo [fn_imposta_accensione_processo](/dbzero/dbops/funzioni/fn_imposta_accensione_processo)
  non la ripete, e vale per chiunque scriva la tabella.

---

### Codici errore

* `E_PROCESSO_SENZA_SVEGLIA` — processo `CODA`, o con il ritiro raggiunto.
* `E_PROCESSO_NON_SPEGNIBILE` — spegnimento di un non spegnibile.
* `E_PROCESSO_NON_ACCENDIBILE_IN_PRODUZIONE` — accensione in produzione di un non accendibile.
* `E_CONFIG_MANCANTE` — la stessa accensione con l'ambiente non dichiarato.
* `E_PROCESSO_ACCENSIONE_MOTIVO_OBBLIGATORIO` — motivo vuoto.

---

### Test

* `db/pgtap/dbops/test-processi-accensione-v1.sql` — attraverso il verbo: spegnere un non
  spegnibile rifiutato e confermarlo acceso ammesso, il motivo vuoto anche per il default, il
  processo `CODA`.
* `db/pgtap/dbops/test-processi-accensione-produzione-v1.sql` — in una produzione costruita: il
  non accendibile non si riaccende, nemmeno ritoccando il solo motivo; spegnerlo e rimetterlo al
  default è ammesso; senza ambiente l'accensione dà `E_CONFIG_MANCANTE` e lo spegnimento passa.
* `db/pgtap/dbops/test-processo-vivo-v1.sql` — la scelta a mano su un ritiro programmato è
  ammessa, su un ritiro raggiunto dà `E_PROCESSO_SENZA_SVEGLIA`.

---

### Note di migrazione

* 2026-10-16 — nasce col default di accensione per ambiente (`brief-db-processi-accensione-per-ambiente`).
* 2026-10-18 — riceve il divieto di accensione in produzione.

---

{% include-markdown "signature-core.md" %}
