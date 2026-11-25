## 📘 Documentazione Concettuale – Funzione `vendite.fn_guard_passaggio_lotto`

> **Ultimo aggiornamento**: 25 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [config.stati_doc_fiscale_transizioni](/dbzero/config/tabelle/stati_doc_fiscale_transizioni) — la matrice dei passaggi, e l'azione di ogni riga
>
> Approfondimento funzioni:
>
> * [script.fn_doc_passaggio](/dbzero/script/funzioni/fn_doc_passaggio) — la riga del passaggio e la sua azione
> * [script.fn_guard_azione](/dbzero/script/funzioni/fn_guard_azione) — il permesso quando la riga ha un'azione
> * [script.fn_guard_livello_area](/dbzero/script/funzioni/fn_guard_livello_area) — il permesso quando la riga non ce l'ha: il livello sull'area `vendite`
> * [script.fn_guard_passaggio](/dbzero/script/funzioni/fn_guard_passaggio) — il guard comune a tutti i documenti, che giudica la matrice
> * [vendite.fn_annulla_lotto_da_draft](/dbzero/vendite/funzioni/fn_annulla_lotto_da_draft) — chiamante: l'annullo del lotto
> * [vendite.fn_riporta_lotto_a_draft](/dbzero/vendite/funzioni/fn_riporta_lotto_a_draft) — chiamante: il ritorno in bozza
>
> Guide:
>
> * [Il modello del documento di vendita](/guide/modello-documento-di-vendita) — l'azione si dichiara sulla riga del passaggio
> * [Fatturazione](/guide/fatturazione) — chi può annullare e riportare in bozza un lotto

---

### 🎯 Scopo Principale

Il permesso di un passaggio di stato fiscale del **lotto di fatturazione**, con la stessa regola
dell'endpoint. La chiamano i due verbi del reset del lotto che cambiano il suo stato: l'annullo e il
ritorno in bozza.

---

### La regola

Il guard legge la riga del passaggio nella matrice
([`script.fn_doc_passaggio`](/dbzero/script/funzioni/fn_doc_passaggio)), dallo stato di oggi allo
stato d'arrivo:

| La riga del passaggio | Che cosa chiede |
| --- | --- |
| c'è, e dichiara un'azione | quell'azione ([`script.fn_guard_azione`](/dbzero/script/funzioni/fn_guard_azione)). Per il ritorno in bozza da `EMESSA` è `numera_fatture_lotti` |
| c'è, ma non ha azione | il livello `TUTTO` sull'area `vendite` ([`script.fn_guard_livello_area`](/dbzero/script/funzioni/fn_guard_livello_area)). È il caso dell'annullo della bozza |
| non c'è, perché il lotto è già nello stato d'arrivo | il livello `TUTTO` sull'area `vendite`. È il ritorno in bozza di un lotto già in bozza, che fa solo la pulizia |

Il rifiuto è sempre `E_PERMESSO_NEGATO`, lo stesso codice del backend.

---

### ⭐ Perché il lotto rifà il permesso sul documento

La regola comune dei documenti dice: una riga senza azione chiede solo il permesso sul documento, e
quel permesso lo controlla il backend.
[`script.fn_guard_passaggio`](/dbzero/script/funzioni/fn_guard_passaggio), comune a tutti i
documenti, in quel caso lascia passare.

I due verbi del lotto però girano come proprietario, e dietro di loro non c'è più la row security.
Per questo rifanno a DB il controllo che l'endpoint fa già: il livello `TUTTO` sull'area `vendite`.
Chi arriva dall'interfaccia non riceve un rifiuto nuovo. La ricaduta sull'area vale **solo per il
lotto**: gli altri documenti non cambiano.

---

### Che cosa non fa

* **Non giudica la matrice**: se il passaggio è ammesso, se è di processo, se il lotto è già nello
  stato. Lo fanno `script.fn_guard_passaggio`, dentro
  [`vendite.fn_cambia_stato_lotto`](/dbzero/vendite/funzioni/fn_cambia_stato_lotto), e il guard di
  transizione del lotto quando lo stato si scrive.
* **Non controlla il perimetro**: il verbo legge il lotto nel perimetro **prima** di chiamarlo,
  perché il permesso dipende dallo stato del lotto.

`SECURITY INVOKER`: decide sull'utente che il verbo gli passa, senza leggere niente da proprietario.

---

### Codici errore

* `E_PERMESSO_NEGATO` — manca l'azione della riga o, senza azione, il livello `TUTTO` sull'area
  `vendite`. Anche quando l'utente manca.

---

### Test

* `db/pgtap/vendite/test-porta-reset-lotto-e-fondo-v1.sql` — l'annullo con l'area a `LETTURA` e il
  ritorno in bozza di un lotto già in bozza con l'area a `LETTURA` rifiutano; il ritorno in bozza da
  `EMESSA` con l'area a `TUTTO` rifiuta senza `numera_fatture_lotti` e passa con l'azione.

---

### Note di migrazione

* 2026-11-25 — nasce con i verbi del reset del lotto `SECURITY DEFINER`. Prima il permesso del
  passaggio arrivava dopo la pulizia, da `fn_cambia_stato_lotto`, e senza la ricaduta sull'area
  (brief-db-porte-aperte-dalla-sola-guc, giro 1-7, D-X a).

---

{% include-markdown "signature-core.md" %}
