## 📘 Documentazione Concettuale – Funzione `vendite.fn_documento_listino_operativo`

> 👀 **Vedi anche**
>
> **La regola della versione in vigore:** [vendite.fn_listino_versione_in_vigore](/dbzero/vendite/funzioni/fn_listino_versione_in_vigore)
>
> **Chi la chiede:** [vendite.fn_documento_righe_preview](/dbzero/vendite/funzioni/fn_documento_righe_preview) ·
> [vendite.fn_offerta_righe_espanse](/dbzero/vendite/funzioni/fn_offerta_righe_espanse) ·
> [script.fn_check_esclusione_articolo_documento](/dbzero/script/funzioni/fn_check_esclusione_articolo_documento) ·
> [script.fn_check_articolo_riga](/dbzero/script/manual/fn_check_articolo_riga) (dal 2026-10-13, al posto del guard «aggiunta fuori listino»)
>
> **Verifica:** `db/pgtap/vendite/test-righe-esclusione-solo-non-si-vende-v1.sql` ·
> `db/pgtap/vendite/test-listino-versione-in-vigore-v1.sql` (test 13)

---

### 🎯 Scopo Principale

(funzione nata il 2026-10-04, `20261004-42`)

**Quale versione del listino vale per le righe di questo contratto, o di
questa offerta?** La risposta, in un posto solo:

1. se il documento ha già una versione fissata (il contratto all'attivazione,
   l'offerta all'emissione), è quella;
2. altrimenti, se ha un listino, la versione **in vigore oggi**, dalla sede
   unica [`fn_listino_versione_in_vigore`](/dbzero/vendite/funzioni/fn_listino_versione_in_vigore)
   (attiva o chiusa; la bozza non conta);
3. senza listino (solo un contratto può non averlo), nessuna versione.

Restituisce anche la variazione globale del documento (tipo e valore), che
serve alla lista delle righe per calcolare i prezzi del listino.

---

### Perché esiste

Fino al 2026-10-04 la stessa domanda era scritta in quattro funzioni: la lista
delle righe del contratto, il controllo dell'aggiunta fuori listino, il
controllo dell'esclusione del componente di un bundle, le righe espanse
dell'offerta. Portare le regole del contratto anche sull'offerta
(brief-db-righe-esclusione-solo-non-si-vende) le avrebbe raddoppiate: si è
estratta la risposta (regola del 2).

---

### Forma

- Primo argomento: il documento (`CONTRATTO`, `OFFERTA`); un altro valore è un
  errore di chi chiama (`E_DOC_TIPO_NON_GESTITO`).
- Documento che non c'è, o che chi chiede non vede: nessuna riga. Chi scrive
  passa comunque da policy e chiavi esterne.
- `SECURITY INVOKER`: la domanda si fa dentro il perimetro di chi scrive, come
  facevano le copie che sostituisce.

---

{% include-markdown "signature-core.md" %}
