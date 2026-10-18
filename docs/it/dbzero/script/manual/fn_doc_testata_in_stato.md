## 📘 Documentazione Concettuale – Funzione `script.fn_doc_testata_in_stato()`

> 👀 **Vedi anche**
>
> • [script.fn_doc_lock_montaggi](/dbzero/script/funzioni/fn_doc_lock_montaggi) — il lettore del montaggio, dove sta il quadro intero
> • [vendite.trgfn_doc_testata_lock_fuori_bozza](/dbzero/vendite/funzioni/trgfn_doc_testata_lock_fuori_bozza) — il lock che legge

---

### 🎯 Scopo Principale

(nata il 2026-10-10, brief `brief-db-testata-dopo-emissione`, fase 2)

**La testata di un documento in uno stato, vista dal form.** Le capability di ordine,
bolla, reso, preventivo, offerta e contratto dicono al form quali campi spegnere
(`non_editable_fields`) e se la testata si modifica (`can_edit_testata`). Fino al
10 ottobre 2026 lo dicevano con liste e stati scritti a mano nella funzione: una terza copia
della regola, accanto al lock e al backend. Ora lo leggono da qui, cioè dal montaggio del lock.

Restituisce:

| Chiave | Che cosa |
| --- | --- |
| `non_modificabili` | le colonne che la capability dichiara ferme **sempre** (campi di sistema, lock assoluti come il cliente dell'ordine), seguite da quelle che il lock ferma in questo stato, senza doppioni. Dal 2026-10-18 il lock stesso può dire una colonna ferma sempre, bozza compresa (utility ed emittente di preventivo, offerta e contratto): esce in ogni stato, e la capability non la ripete |
| `modificabile` | vero se in questo stato almeno una colonna nominata dal lock si cambia: in bozza tutte, dopo l'emissione quelle aperte (le note, i dati di trasporto della bolla, la fine validità del contratto attivo), a documento chiuso nessuna |

Le colonne che il lock non nomina non compaiono: le scrive il database, o il form non le
mostra.
