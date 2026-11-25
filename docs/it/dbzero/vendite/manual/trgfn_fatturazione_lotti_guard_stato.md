## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_fatturazione_lotti_guard_stato`

> **Ultimo aggiornamento**: 25 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.fatturazione_lotti](/dbzero/vendite/tabelle/fatturazione_lotti) — la tabella che protegge
> * [config.stati_doc_fiscale_transizioni](/dbzero/config/tabelle/stati_doc_fiscale_transizioni) — la matrice dei passaggi
>
> Approfondimento funzioni:
>
> * [vendite.fn_set_fatturazione_lotto_stato](/dbzero/vendite/funzioni/fn_set_fatturazione_lotto_stato)
> * [vendite.fn_cambia_stato_lotto](/dbzero/vendite/funzioni/fn_cambia_stato_lotto) — il verbo dei passaggi manuali del lotto
> * [vendite.fn_porta_reset_lotto_aperta](/dbzero/vendite/funzioni/fn_porta_reset_lotto_aperta) — la porta del reset del lotto: la GUC e il proprietario

---

### 🎯 Scopo Principale

La funzione **`vendite.trgfn_fatturazione_lotti_guard_stato()`** controlla le
transizioni tra stati documento sui lotti di fatturazione.

---

### Regola applicata

* Trigger `BEFORE UPDATE OF stato_doc_fiscale_id` su `vendite.fatturazione_lotti`.
* Verifica la transizione in `config.stati_doc_fiscale_transizioni`.
* Se `config.stati_doc_fiscale_transizioni.meta.tipo_lotto` e` valorizzato,
  la transizione e` ammessa solo per lotti con lo stesso `tipo_lotto`.
* Se lo stato non e` applicabile o la transizione non e` ammessa → errore.

---

### La porta del reset del lotto

Il guard lascia passare la scrittura quando la **porta del reset del lotto** è aperta. La legge
[`vendite.fn_porta_reset_lotto_aperta`](/dbzero/vendite/funzioni/fn_porta_reset_lotto_aperta), che
risponde sì solo se la GUC `zeroerp.maintenance_reset_lotto_draft` è accesa **e** chi scrive è il
proprietario della tabella.

La GUC la accende solo la pulizia del lotto,
[`vendite.fn_cleanup_fatture_by_ids`](/dbzero/vendite/funzioni/fn_cleanup_fatture_by_ids), riservata
al proprietario, e la spegne prima di uscire: la porta è aperta solo mentre la pulizia lavora. ⛔ Per
l'applicazione la porta è sempre chiusa: accendere la GUC da sé e scrivere diretta non apre niente.

⭐ **Lo stato che i verbi del reset scrivono lo giudica questo guard.** L'annullo e il ritorno in
bozza scrivono lo stato del lotto dopo la pulizia, con `vendite.fn_cambia_stato_lotto`: a quel punto
la pulizia ha già richiuso la porta, quindi il passaggio passa dai controlli di questa pagina come
ogni altro. I due passaggi del reset (`DRAFT → ANNULLATA`, `EMESSA → DRAFT`) sono righe ammesse
della matrice, e il fermo non li riguarda: l'annullo è uno stato abortito, la bozza non congela.

---

### Un lotto fermo non diventa definitivo

(rev 2026-10-24, `brief-modello-documento-vendita` R-1)

La regola di Tid: *se un documento del lotto è in errore, gli altri non possono passare a
uno stato definitivo; prima i documenti non conformi si tolgono dal lotto (o si correggono e
si rilancia lo step).*

* Quando il lotto sta per entrare in uno stato **congelato e non abortito** (dal vocabolario:
  `congela_fiscale = true`, `is_abortito = false`; oggi Definitiva, Inviata, Registrata), il
  controllo legge se il lotto è **fermo** dalla sede unica
  [vendite.vw_lotti_segnalazioni_summary](/dbzero/vendite/views/vw_lotti_segnalazioni_summary):
  segnalazioni critiche, fatture in errore, documenti in errore.
* Se è fermo, rifiuta con `E_PIPELINE_LOTTO_CRITICAL`: lo **stesso codice** del runner della
  pipeline. La regola è una, i punti in cui si applica due: il runner si ferma prima, il
  database decide anche per chi scrive senza passare dal runner.
* Un passaggio **non** congelato (per esempio a Emessa) resta ammesso, e così l'**annullo**.

L'altra metà della regola sta nell'invariante lotto ↔ fatture
([vendite.fn_guard_lotto_fatture_stato_coerente](/dbzero/vendite/manual/fn_guard_lotto_fatture_stato_coerente)).
Presidio: `db/pgtap/vendite/test-lotto-fermo-non-diventa-definitivo-v1.sql`.

---

### Test

* `db/pgtap/vendite/test-lotto-fermo-non-diventa-definitivo-v1.sql` — il lotto fermo non diventa
  definitivo.
* `db/pgtap/vendite/test-porta-reset-lotto-e-fondo-v1.sql` — con la GUC accesa dall'applicazione
  la porta resta chiusa; col permesso l'annullo riesce, e lo stato d'annullo passa da questo guard.

---

### Note di migrazione

* 2026-10-24 — il lotto fermo non entra in uno stato definitivo (brief-modello-documento-vendita
  R-1).
* 2026-11-25 — la porta del reset si legge da `vendite.fn_porta_reset_lotto_aperta` e chiede anche
  il proprietario; prima bastava la GUC, che l'applicazione poteva accendere da sé
  (brief-db-porte-aperte-dalla-sola-guc, giro 1-7). La pulizia la lasciava
  accesa fino a fine transazione, e lo stato scritto dai verbi del reset passava senza questo guard.

---

{% include-markdown "signature-core.md" %}
