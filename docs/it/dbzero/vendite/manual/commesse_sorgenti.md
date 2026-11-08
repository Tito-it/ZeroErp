## 📘 Documentazione Concettuale – Tabella `vendite.commesse_sorgenti`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.commesse](/dbzero/vendite/tabelle/commesse) — la commessa a cui il documento è collegato
> * [vendite.commesse_attivita](/dbzero/vendite/tabelle/commesse_attivita) — le righe, che nascono insieme al link
> * [config.sorgenti](/dbzero/config/tabelle/sorgenti) — il catalogo dei tipi di documento, con la chiave di ognuno
>
> Approfondimento funzioni:
>
> * [vendite.fn_link_commessa_sorgente](/dbzero/vendite/funzioni/fn_link_commessa_sorgente) — la porta che scrive il link
> * [vendite.fn_commessa_viva_di_sorgente](/dbzero/vendite/funzioni/fn_commessa_viva_di_sorgente) — quale link conta, fra quelli di un documento
> * [script.fn_sorgente_chiave](/dbzero/script/funzioni/fn_sorgente_chiave) — il BB che dà la chiave da scrivere
> * [script.trgfn_guard_sorgente](/dbzero/script/funzioni/trgfn_guard_sorgente) — il guard unico della provenienza
>
> Guide:
>
> * [Sorgente polimorfa](/guide/sorgente-polimorfa) — il modello della provenienza

---

### 🎯 Scopo Principale

`vendite.commesse_sorgenti` registra i documenti collegati a una commessa: la sorgente ROOT, da cui la commessa nasce, e le sorgenti COLLEGATO che vi confluiscono.

---

### Il documento collegato: tipo, chiave, riga

Ogni link dice quale documento è collegato con le colonne del modello della provenienza:

* `sorgente_tipo_id` — il tipo del documento in `config.sorgenti` (preventivo, ordine,
  contratto, DDT), obbligatorio;
* `sorgente_id` *oppure* `sorgente_uid` — la chiave del documento: **una sola**, quella che
  il `key_selector` del tipo dichiara (uid per il preventivo, id per ordine, contratto e DDT).
  La forma la tiene `chk_commesse_sorgenti_sorgente_forma`;
* `sorgente_riga` — la riga del documento, quando il link è a grana di riga; vuota quando il
  link è al documento intero, come lo scrive oggi la porta.

La chiave la decide il BB che scrive, `script.fn_sorgente_chiave`, dentro la porta del link:
nessuno la compone a mano. Il guard unico `script.trgfn_guard_sorgente` verifica che il
documento (e la riga, se c'è) esista, e blocca la cancellazione del documento finché un link
lo cita.

---

### Regole principali

* **Una sola ROOT per commessa** (`uq_commesse_sorgenti_commessa_root`). La commessa è
  **multi-sorgente**: una ROOT e più COLLEGATO; il ruolo lo decide
  `vendite.fn_link_commessa_sorgente`.
* ⭐ **Un documento compare una volta per commessa**
  (`uq_commesse_sorgenti_sorgente_commessa`), e sta in **una sola commessa aperta** alla volta:
  questa regola la fa valere la porta, perché un indice non legge lo stato della commessa.
  Il link verso una commessa **chiusa o annullata resta come storia**: il documento si
  rimanda in una commessa nuova, e ha più link. Quale conta lo dice
  `vendite.fn_commessa_viva_di_sorgente`.
* **Il link nasce con la riga**: lo scrive la madre delle righe,
  `vendite.fn_upsert_commessa_attivita`, insieme alla riga di commessa.
* **Emittente omogeneo**: un guard dedicato tiene coerente l'emittente del documento collegato
  con quello della commessa.

---

### Utilizzo previsto

* tracciabilità della sorgente ROOT della commessa;
* protezione contro il doppio aggancio di un documento a commesse aperte;
* storia delle commesse in cui il documento è passato;
* base per recovery e audit dell'orchestratore del push.

---

### Note di migrazione

* 2026-06-09 — la commessa diventa multi-sorgente: una ROOT e più COLLEGATO.
* 2026-07-18 — la chiave testuale `sorgente_uid` viene normalizzata alla forma del
  `key_selector` e validata da un guard testuale (brief-db-guard-sorgente-polimorfa).
* 2026-10-12 — l'unicità da globale («una commessa per sempre», `uq_commesse_sorgenti_src_uid`)
  diventa per commessa, con la regola della commessa aperta nella porta
  (brief-db-annullo-a-valle-riapre-a-monte §10).
* 2026-11-07 — la chiave testuale `sorgente_uid` lascia il posto alla coppia tipizzata
  `sorgente_id` / `sorgente_uid` (uuid), e il guard testuale
  `script.trgfn_guard_sorgente_polimorfa_testuale` al guard unico `script.trgfn_guard_sorgente`;
  l'unicità per commessa diventa `uq_commesse_sorgenti_sorgente_commessa`
  (brief-db-sorgente-documento-e-riga).

---

{% include-markdown "signature-core.md" %}
