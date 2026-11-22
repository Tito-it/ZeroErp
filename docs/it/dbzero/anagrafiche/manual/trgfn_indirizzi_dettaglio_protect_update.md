## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_indirizzi_dettaglio_protect_update`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.indirizzi_dettaglio](/dbzero/anagrafiche/tabelle/indirizzi_dettaglio) — il civico di cui blocca la via
> * [config.stradario](/dbzero/config/tabelle/stradario) — la via
>
> Approfondimento funzioni:
>
> * [dbops.fn_admin_merge_stradario](/dbzero/dbops/funzioni/fn_admin_merge_stradario) — la fusione delle vie, che apre la porta
> * [maintenance.proc_bump_indirizzi_dettaglio](/dbzero/maintenance/funzioni/proc_bump_indirizzi_dettaglio) — la rinormalizzazione, che non ne ha bisogno

---

### 🎯 Scopo Principale

`anagrafiche.trgfn_indirizzi_dettaglio_protect_update` impedisce che un civico cambi via. Un civico su un'altra
via è un altro indirizzo fisico, e si crea; spostarlo cambierebbe in silenzio l'indirizzo di tutti quelli che lo
puntano.

---

### Solo il cambio di via, e una porta sola

Il trigger guarda soltanto `stradario_id`: numero, dettaglio, posizione e stato si modificano senza passare da
qui (la chiave la giudica `anagrafiche.trgfn_indirizzi_dettaglio_guard_chiave`).

L'unico che sposta i civici è la fusione delle vie, `dbops.fn_admin_merge_stradario`: quando due vie sono la
stessa, i civici della via che si sopprime passano su quella che resta. La fusione accende la porta, il
parametro di sessione `zeroerp.maintenance_indirizzi_dettaglio`, per il solo tempo del ripuntamento, e la
richiude al valore di prima; se il ripuntamento fallisce, l'annullamento la richiude da sé.

La rinormalizzazione dei civici di una via (`maintenance.proc_bump_indirizzi_dettaglio`) riscrive la stessa via,
non la cambia: non apre la porta.

---

### ⚠️ Che cosa oggi non copre

* **La porta è un parametro di sessione che chiunque scriva può accendere**: con la porta accesa il cambio di
  via passa senza giudizio, anche fuori dalla fusione.

---

### Codici errore

* `E_COLONNA_NON_MODIFICABILE` — un cambio di via a porta chiusa; il campo è `stradario_id`.

---

### Test

* `db/pgtap/dbops/test-fusioni-comune-stradario-v1.sql` — la fusione che sposta i civici sulla via che resta, la
  porta che resta chiusa dopo.
* `db/pgtap/maintenance/test-bump-toponomastica-v1.sql` — la rinormalizzazione che non lascia la porta accesa.

---

### Note di migrazione

* 2026-11-03 — la rinormalizzazione di una via smette di accendere la porta: le basta un aggiornamento che non
  cambia la via.
* 2026-11-07 — la fusione delle vie apre la porta per il ripuntamento: prima falliva appena la via aveva un
  civico.

---

{% include-markdown "signature-core.md" %}
