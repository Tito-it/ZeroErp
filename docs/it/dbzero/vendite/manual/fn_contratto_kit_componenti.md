## 📘 Documentazione Concettuale – Funzione `vendite.fn_contratto_kit_componenti(p_contratto_id, p_articolo_padre_id, p_data)`

> **Ultimo aggiornamento**: 1 novembre 2026

> 👀 **Vedi anche**
>
> [vendite.fn_contratti_addebiti_maturati](/dbzero/vendite/manual/fn_contratti_addebiti_maturati) ·
> [vendite.fn_resolve_prezzo_listino_v2](/dbzero/vendite/funzioni/fn_resolve_prezzo_listino_v2) ·
> [vendite.listini_righe_componenti](/dbzero/vendite/manual/listini_righe_componenti) ·
> [Guida dei contratti §4-bis.3](/guide/gestione-contratti#4-bis3-il-canone)

### 🎯 Scopo
(31-10-2026 — brief `brief-db-contratto-righe-periodiche-in-commessa` §7.2, D-2, decisione c di Tid)

**I componenti di un kit che il contratto non negozia, dal listino del contratto.** Un kit
negoziato porta i suoi componenti sulla riga (`contratti_righe_componenti`). Due kit non li hanno:

* la **quota fissa** di un kit del listino: non c'è una riga del contratto;
* l'**ADESIONE** su un kit: la riga c'è, ma non ha prezzo né componenti suoi.

Per questi la funzione dà i componenti della versione di listino del contratto
([`fn_documento_listino_operativo`](/dbzero/vendite/funzioni/fn_documento_listino_operativo)),
validi alla data, **nella stessa forma** che l'espansore del backend legge dalle
`*_righe_componenti`: componente, unità operativa (quella del componente), coefficiente della
distinta, prezzo unitario, esposizione in fattura, origine del prezzo.

### Chi la usa

| Chi | Per che cosa |
| --- | --- |
| [`vendite.fn_contratti_addebiti_maturati`](/dbzero/vendite/manual/fn_contratti_addebiti_maturati) | il prezzo del kit: la somma prezzo × coefficiente, alla data del pezzo (la una tantum a `valido_dal`) |
| l'espansore dei kit del backend (`BoMComponentExpander`, push dei contratti) | i componenti in commessa, alla `data_attivita` del pezzo: la stessa data a cui il kit è prezzato |

### Regole

* **Il prezzo lo dice il resolver**
  ([`fn_resolve_prezzo_listino_v2_esito`](/dbzero/vendite/funzioni/fn_resolve_prezzo_listino_v2_esito))
  sul componente nel contesto del padre: oggi il prezzo del listino **senza** variazione globale
  (`LISTINO_BUNDLE`), come l'anteprima del listino. La funzione non ricopia la regola: se la
  variazione sul kit deve cambiare, cambia nel resolver.
* Un componente senza prezzo alla data esce con prezzo `NULL`: chi somma non dà un prezzo al kit
  (il lister lo scarta `SENZA_PREZZO`).
* Contratto fuori perimetro, o senza listino: nessuna riga. `STABLE`, `SECURITY INVOKER`.

### 🧪 Il presidio

`db/pgtap/vendite/test-listino-kit-e-periodicita-v1.sql` (componenti dal listino, quota fissa del
kit, ADESIONE sul kit).

---

{% include-markdown "signature-core.md" %}
