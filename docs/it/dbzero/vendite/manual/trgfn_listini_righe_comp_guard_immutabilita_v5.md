# trgfn_listini_righe_comp_guard_immutabilita_v5

> **Ultimo aggiornamento**: 15 novembre 2026
>
> **Vedi anche**
>
> - [script.fn_check_listino_riga_scrivibile](/dbzero/script/manual/fn_check_listino_riga_scrivibile) — la regola, comune a righe, componenti e kit
> - [catalogo.fn_chiudi_legame_distinta](/dbzero/catalogo/funzioni/fn_chiudi_legame_distinta) — l'unico verbo che apre la porta della fine
> - [vendite.listini_righe_componenti](/dbzero/vendite/manual/listini_righe_componenti) — tabella su cui il trigger opera
> - [vendite.vw_listini_versioni_azioni](/dbzero/vendite/manual/vw_listini_versioni_azioni) — la superficie (`prezzi_bundle_blocco_*`)
> - [vendite.trgfn_listini_righe_guard_stato](/dbzero/vendite/manual/trgfn_listini_righe_guard_stato) — il gemello sulle righe

## Scopo

I prezzi dei componenti di un kit (`vendite.listini_righe_componenti`) **si scrivono solo in
bozza**, come le righe: in una versione attiva o chiusa non si aggiungono, non si modificano e non
si eliminano, per nessuna colonna, `attivo` compreso. Disattivare un prezzo bundle cambierebbe il
prezzo che il resolver risolve per il kit, e nel listino in uso un prezzo non cambia: si clona la
versione, si corregge la bozza e la si attiva. Una bozza si elimina con tutto quello che contiene
([vendite.fn_elimina_versione_listino](/dbzero/vendite/funzioni/fn_elimina_versione_listino)).

La regola non sta qui: il guard solleva il primo motivo di
[`script.fn_check_listino_riga_scrivibile`](/dbzero/script/manual/fn_check_listino_riga_scrivibile),
la stessa che dice il pulsante (`prezzi_bundle_blocco_*` della superficie della versione).

> ⚠️ **Revoca (15-11-2026, brief `brief-db-stati-documento-dal-vocabolario` §6.28, Tid).** Dal
> 13-05-2026 (`brief-db-componenti-modello-unificato` §8.2) fuori dalla bozza restavano liberi i
> campi diversi da prezzo, IVA e validità, e il DELETE si sostituiva con `attivo = FALSE`: un
> prezzo bundle si toglieva da una versione attiva. Ora fuori dalla bozza non cambia niente.

## Contesto di esecuzione

| | |
|---|---|
| Nome trigger | `trg_listrighe_comp_a10_guard_immutabilita_v5_ins_upd_dlt` |
| Momento | `BEFORE INSERT OR UPDATE OR DELETE` |
| Fase | `_a10_` (guard) |
| Scope | `FOR EACH ROW` |

## ⭐ La porta della chiusura del legame

Un prezzo bundle sta dentro il periodo del suo legame di distinta (chiave esterna temporale). Se la
fine del prezzo non si potesse mai toccare, un kit prezzato in una versione già attiva non potrebbe
perdere un componente finché quella versione esiste. Per questo c'è una sola eccezione, stretta:

* si apre con la variabile di transazione `zeroerp.legame_distinta_chiudi` uguale all'id del legame
  della riga (`articolo_componente_id`), **e** solo per il proprietario della tabella
  (`script.fn_is_proprietario_tabella`): dall'applicazione non si apre, nemmeno impostandola;
* cambia **solo `valido_al`**, e solo per accorciarla (mai vuota, mai più avanti); ogni altra
  colonna resta uguale, altrimenti il rifiuto è quello di sempre.

La apre solo il verbo `catalogo.fn_chiudi_legame_distinta` (`SECURITY DEFINER`), che chiede il
permesso sul catalogo e sui listini e la conferma dell'operatore, e la richiude dopo aver scritto i
prezzi.

## Codici errore

| Codice | Quando |
|---|---|
| `E_RIGA_LISTINO_VERSIONE_CHIUSA` | una scrittura in una versione CHIUSA |
| `E_RIGA_LISTINO_VERSIONE_NON_IN_BOZZA` | una scrittura in una versione non in bozza e non chiusa (attiva) |

Una versione che non si legge non si giudica: parlano la chiave esterna e la policy della tabella.

## Il verbo nel registro

I prezzi bundle si scrivono direttamente (il backend li riscrive per kit, a tabula rasa): chi
rifiuta è questo guard. Per questo è il `verbo` dell'azione `PREZZI_BUNDLE_LISTINO` in
[`config.azioni_riga`](/dbzero/config/manual/azioni_riga).

---

{% include-markdown "signature-core.md" %}
