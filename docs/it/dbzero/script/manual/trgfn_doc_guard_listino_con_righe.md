## 📘 Documentazione Concettuale – Funzione `script.trgfn_doc_guard_listino_con_righe()`

> 👀 **Vedi anche**
>
> • [script.fn_check_listino_cambiabile](/dbzero/script/funzioni/fn_check_listino_cambiabile) — la regola, scritta una volta

---

### 🎯 Scopo Principale

(nato il 2026-10-11, brief `brief-db-testata-dopo-emissione`, §11, R-DB-4)

Il guard che impedisce di cambiare il listino di un contratto o di un'offerta sotto righe già
caricate, e di toglierlo sotto eccezioni che ne dipendono. Solleva il primo motivo di
`script.fn_check_listino_cambiabile`, col campo `listino_id`: la regola non è scritta qui.

### Dove parla

È montato su `vendite.contratti` e `vendite.offerte_commerciali`, prima della scrittura,
solo quando il listino cambia. L'ordine dei rifiuti è voluto:

1. fuori bozza parla prima il lock di testata (`E_DOC_CONDIZIONI_FUORI_BOZZA`): il listino non
   si cambia comunque;
2. poi questo guard: il listino non si cambia sotto le righe;
3. infine `guard_listino_documento`: il listino nuovo è della utility e dell'azienda giuste?

Prima si dice che una cosa non si può cambiare, poi se il valore nuovo era buono.
