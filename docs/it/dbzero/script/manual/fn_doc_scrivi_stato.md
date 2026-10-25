## 📘 Documentazione Concettuale – Funzione `script.fn_doc_scrivi_stato(regclass, bigint, bigint)`

> 👀 **Vedi anche**
>
> [script.fn_guard_passaggio](/dbzero/script/funzioni/fn_guard_passaggio) ·
> [script.trgfn_doc_stato_solo_dal_verbo](/dbzero/script/funzioni/trgfn_doc_stato_solo_dal_verbo) ·
> guida [Il modello del documento di vendita](/guide/modello-documento-di-vendita) §5

### 🎯 Scopo
(25-10-2026 — brief `brief-modello-documento-vendita` §7, decisioni S-1, S-2)

**La seconda metà del verbo di stato: la scrittura attraverso la porta.** Apre la
porta per **quel** documento (la variabile di transazione
`zeroerp.doc_cambio_stato` vale `'<oid della testata>:<id>'`), scrive lo stato con
un `UPDATE` che passa da tutti i guard di sempre (la matrice, le condizioni
d'uscita dalla bozza, il numero, i legami) e rimette la porta com'era.

### Regole

* **Non è riservata, e non serve che lo sia.** La porta chiede anche che chi scrive
  sia il proprietario della tabella: chiamata da un verbo `SECURITY DEFINER` passa,
  chiamata dall'applicazione si ferma alla porta.
* La porta si rimette com'era, non si chiude: un verbo che cambia due documenti (il
  reso e poi la sua bolla) non lascia aperta quella del primo, e una scrittura
  annidata non chiude quella di chi l'ha chiamata.
* Il permesso lo controlla prima la prima metà, `script.fn_guard_passaggio`. I
  passaggi **di processo** li scrive con questa sola il verbo che ne è la causa
  (la conferma e l'annullo del reso per la bolla `CONSEGNATO ↔ RESO`).
* Testata fuori mappa, id o stato mancanti, nessuna riga toccata:
  `E_SCRIPT_CHIAMATA_NON_VALIDA`.
