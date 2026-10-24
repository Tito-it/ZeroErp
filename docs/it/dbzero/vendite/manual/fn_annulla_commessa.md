## 📘 Documentazione Concettuale – Funzione `vendite.fn_annulla_commessa`

> 👀 **Vedi anche**
>
**Approfondimento funzioni:**
>
• [vendite.fn_documento_legami](/dbzero/vendite/funzioni/fn_documento_legami) — che cosa si riapre  
> • [vendite.fn_documento_ritira_legami](/dbzero/vendite/funzioni/fn_documento_ritira_legami) — la conferma e il ritiro  
> • [vendite.trgfn_doc_guard_annullo_con_legami](/dbzero/vendite/funzioni/trgfn_doc_guard_annullo_con_legami) — l'avviso  
> • [script.fn_check_commessa_annullabile](/dbzero/script/funzioni/fn_check_commessa_annullabile) — ciò che vieta  

---

### 🎯 Scopo Principale
(2026-10-12, brief-db-annullo-a-valle-riapre-a-monte, D-1, D-2, D-3, D-7)

**Annullare una commessa riapre ciò che la riempiva**, e non in silenzio: chi
annulla vede che cosa si riapre e conferma. È la stessa forma dei verbi di
bolla, ordine, preventivo e contratto.

| La riga di commessa (non emessa) | Che cosa succede |
| --- | --- |
| di un preventivo, ordine, contratto, bolla | si ritira; il documento torna da mandare in commessa; un preventivo `EVASO` torna `ACCETTATO` |
| di un consumo | si ritira; il consumo torna da mandare |
| rettifica di un accredito di reso | l'accredito si annulla |
| onere | si annulla con la commessa |

L'ordine **non cambia stato** (D-6: lo stato dell'ordine lo dicono le bolle);
torna solo da mandare in commessa.

---

### Il percorso

1. La commessa, bloccata, nel perimetro di chi annulla (fuori:
   `E_COMMESSA_NON_TROVATA`).
2. **Prima ciò che vieta**: righe già emesse →
   `E_COMMESSA_ANNULLA_CON_RIGHE_EMESSE`, prima di chiedere conferma.
3. La conferma: chi conferma dichiara quanti legami ha visto; se non corrisponde,
   `E_DOC_ANNULLO_CON_LEGAMI`.
4. Il ritiro, ogni riga dal verbo del suo genere.
5. Lo stato passa ad `ANNULLATA` dal verbo di stato della commessa (matrice e
   controlli).

Una commessa senza legami si annulla senza conferma.

---

### Note operative

* `SECURITY DEFINER` con `search_path` bloccato; `EXECUTE` solo all'app.
* Ritorna i legami confermati.
* Una sorgente con righe in un'altra commessa: lì le righe restano.
* Test: `db/pgtap/vendite/test-annullo-commessa-v1.sql`,
  `db/pgtap/vendite/test-annullo-commessa-rettifica-v1.sql`.

---

{% include-markdown "signature-core.md" %}
