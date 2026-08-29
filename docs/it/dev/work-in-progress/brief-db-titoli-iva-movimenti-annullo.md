# Brief DB — l'annullo di una forzatura vuole una colonna, non un campo in `meta`

> **Destinatario:** team DB (`dev/db-tid`). **Voce unica**, e sblocca la slice
> `T3-b` del piano
> [brief-be-fe-titoli-iva-soggetto.md](brief-be-fe-titoli-iva-soggetto.md).
>
> **Origine.** Richiesta di Tid del 2026-08-29, sul piano BE/FE di `I7`:
> *«dovrebbe essere permesso l'annullamento di una riga forzata/manuale; solo
> annullamento, deve rimanere traccia ma no delete»*.
>
> **Stato.** 2026-08-29 — verificato sulla **struttura** (`pg_constraint`,
> corpo dell'accumulatore dalla doc auto-generata). Nessuna misura sui dati.
>
> **Correlati:**
> [soggetti_titoli_iva_movimenti](/dbzero/anagrafiche/tabelle/soggetti_titoli_iva_movimenti) ·
> [trgfn_soggetti_titoli_iva_movimenti_accumulatore](/dbzero/anagrafiche/funzioni/trgfn_soggetti_titoli_iva_movimenti_accumulatore) ·
> [brief-db-be-iva-risolutore-e-regime-cliente §8-ter](brief-db-be-iva-risolutore-e-regime-cliente.md)

---

## 1. Il meccanismo, e perché non è un flag

Una forzatura sbagliata si annulla registrando **una seconda riga `FORZATURA` di
segno opposto**. Non un `DELETE` (Tid: *«deve rimanere traccia»*) e non un flag
`annullato`.

⭐ **Le ragioni sono quattro, e la seconda riguarda direttamente il DB:**

1. il registro resta **append-only**, che è il punto di `D5`: *«una forzatura che
   sovrascrive non lascia traccia del perché; una forzatura che è una riga **è**
   la traccia»*. Un flag sarebbe di nuovo un valore sovrascritto sopra a un altro;
2. ⭐ **l'accumulatore non si tocca.**
   `trgfn_soggetti_titoli_iva_movimenti_accumulatore` fa
   `SELECT COALESCE(SUM(m.imponibile), 0) … WHERE m.titolo_iva_id = …` — **senza
   filtri**. Un contro-movimento riporta `imponibile_utilizzato` al valore giusto
   da solo. Un flag imporrebbe di aggiungere `WHERE NOT annullato`, cioè di
   mettere le mani **nel cuore di `I7`** per un caso di correzione;
3. la **data dell'annullo** è essa stessa un'informazione — quando qualcuno si è
   accorto dell'errore. Un flag la perde, una riga la porta in `data_movimento`;
4. la traccia è **più forte**: si vedono entrambe le righe, l'errore e la
   correzione, ognuna col suo motivo.

⚠️ **I `CHECK` esistenti lo ammettono già**, verificato: `chk_stiva_movimenti_segno`
vuole `imponibile <> 0` sulle forzature (quindi il segno opposto passa),
`chk_stiva_movimenti_documento` vuole `fattura_id IS NULL` sulle forzature, e
`chk_stiva_movimenti_motivo_forzatura` pretende il motivo — che sull'annullo è
proprio la cosa da scrivere. **Nessun vincolo va toccato.**

---

## 2. La richiesta

**Una colonna di collegamento su `anagrafiche.soggetti_titoli_iva_movimenti`**:

```text
annulla_movimento_id  bigint  NULL
    REFERENCES anagrafiche.soggetti_titoli_iva_movimenti(id)
```

⛔ **Perché non in `meta`**, ed è la ragione per cui questo brief esiste invece di
una riga di codice BE: un riferimento strutturale dentro un jsonb non ha FK, non
è interrogabile e non ha unicità — sarebbe una relazione dichiarata **a parole**
dentro un campo libero. Il frontend deve poter dire «questa riga è annullata» e
il backend deve poter rifiutare il doppio annullo: entrambe le cose vogliono una
colonna vera.

⭐ **Con, se il team DB concorda sul merito, due presidi che la rendono onesta:**

* un **UNIQUE parziale** su `annulla_movimento_id WHERE annulla_movimento_id IS NOT NULL`
  → una forzatura si annulla **una volta sola**. Senza, due contro-movimenti
  sulla stessa riga porterebbero `imponibile_utilizzato` dalla parte opposta, e
  il registro racconterebbe due annulli di un annullo solo;
* un **guard** che pretenda che il movimento annullato sia `tipo_movimento =
  'FORZATURA'` e che l'annullante lo sia a sua volta. ⚠️ Non è un `CHECK` di
  colonna: la regola legge **un'altra riga** della stessa tabella — la stessa
  ragione per cui `E_TITOLO_IVA_PLAFOND_MANCANTE` è un trigger e non un `CHECK`.
  📌 Un annullo di un movimento `FATTURA` non si corregge così: si corregge dal
  documento, con una nota di credito, ed è di `I4`.

📌 Serve anche una riga di `dbops.fk_index_policy` per la FK nuova, come per le
undici di `I7`. Se il «sì» o il «no» all'indice sia da rimandare lo decide il
team DB: la colonna si legge dal movimento annullato verso l'annullante, e oggi
quel verso non ha consumatori.

---

## 3. Presidio atteso

⭐ **Il test che conta non guarda il totale**: annullata una forzatura, il
registro deve avere **due righe** e `imponibile_utilizzato` deve essere tornato
al valore precedente.

⚠️ Un test che verificasse **solo** il totale passerebbe identico anche con un
`DELETE` della riga originale — cioè proprio con la cosa che Tid ha escluso, e
che è il motivo per cui questa voce esiste.

Più i due che negano: **doppio annullo** rifiutato (dall'UNIQUE parziale), e
**annullo di un `FATTURA`** rifiutato (dal guard).

---

## 4. Cosa succede lato BE/FE quando è applicato

Slice `T3-b` del piano: il verbo «Annulla» sulla sola riga `FORZATURA` non ancora
annullata, che scrive il contro-movimento; la riga annullata resa con il suo
segno barrato e il rimando alla riga che la annulla.

⚠️ Finché non c'è, `T3-a` va avanti lo stesso — registro in lettura e creazione
della forzatura non dipendono da questa colonna. È l'annullo, e solo l'annullo,
che aspetta.

---

## 5. Diario

| Data | Cosa |
| --- | --- |
| 2026-08-29 | Brief nato dalla richiesta di Tid sul piano BE/FE di `I7`. ⭐ Il meccanismo proposto (contro-movimento invece di flag) **non richiede modifiche all'accumulatore**, verificato sul corpo della funzione: la somma non ha filtri. Resta una sola cosa che il BE non può darsi da solo, ed è il **collegamento** fra la riga annullata e quella che la annulla |
