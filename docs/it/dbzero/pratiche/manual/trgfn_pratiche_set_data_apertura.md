## 📘 Documentazione Concettuale – Trigger function `pratiche.trgfn_pratiche_set_data_apertura`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pratiche.pratiche](/dbzero/pratiche/tabelle/pratiche) — la pratica e la sua `data_apertura`
> * [config.stati_pratiche](/dbzero/config/tabelle/stati_pratiche) — gli stati `BOZZA` e `APERTA`, letti per codice interno
>
> Approfondimento funzioni:
>
> * [script.fn_data_operativa](/dbzero/script/funzioni/fn_data_operativa) — la data di oggi nel fuso dell'azienda

---

### 🎯 Scopo Principale

La trigger function `pratiche.trgfn_pratiche_set_data_apertura` valorizza `data_apertura` quando la
pratica entra in `APERTA`, sia quando nasce già aperta sia quando passa da `BOZZA` ad `APERTA`.

Una volta valorizzata, la data non cambia più con le transizioni successive.

---

### Le regole

* **Alla nascita**: se la pratica nasce in `APERTA` e la data non è stata fornita, prende la data di
  oggi. Una data fornita dal chiamante si conserva. In qualunque altro stato (per esempio `BOZZA`) la
  data resta vuota.
* **Al cambio di stato**: solo la transizione `BOZZA` → `APERTA` valorizza la data. Se la data è già
  valorizzata, si conserva quella di prima, qualunque sia la transizione.
* Gli stati si riconoscono per codice interno, mai per id.

⭐ La data è quella del giorno operativo dell'azienda (`script.fn_data_operativa`), non quella della
sessione: canali con fusi diversi danno lo stesso giorno.

⚠️ L'immutabilità vale sui cambi di stato: una modifica che tocca la sola `data_apertura`, senza
cambiare stato, non passa da questa funzione.

---

### Il significato della colonna

* `data_apertura` è una data, non un istante: per cruscotti e tempi conta il giorno. L'istante preciso
  sta nel giornale, nell'evento di cambio di stato.
* È vuota per le pratiche ancora in `BOZZA` e per quelle annullate senza essere mai state aperte.

---

{% include-markdown "signature-core.md" %}
