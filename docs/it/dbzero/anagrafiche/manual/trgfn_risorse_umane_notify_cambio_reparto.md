## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_risorse_umane_notify_cambio_reparto`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.risorse_umane](/dbzero/anagrafiche/tabelle/risorse_umane) — il rapporto di lavoro, che porta il reparto
> * [config.unita_organizzative](/dbzero/config/tabelle/unita_organizzative) — i reparti
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_notify_cambio_reparto](/dbzero/anagrafiche/funzioni/fn_notify_cambio_reparto) — la funzione che costruisce e invia l'avviso
>
> Guide:
>
> * [Risorse umane e accessi](/guide/risorse-umane-e-accessi) — il rapporto di lavoro e la veste operatore

---

### 🎯 Scopo Principale

`anagrafiche.trgfn_risorse_umane_notify_cambio_reparto` avvisa il backend quando una risorsa umana cambia reparto
(`unita_organizzativa_id`), perché ricalcoli i permessi di quella persona.

---

### Perché il backend va avvisato

Un profilo di accesso si può dare a un reparto invece che a una persona: vale per chi ci lavora. Il backend tiene i
permessi di ogni utente in una memoria temporanea, e uno spostamento di reparto la rende vecchia. Il database non
chiama il backend: lascia un avviso sul canale `cambio_reparto`, e il processo del backend che ascolta quel canale
toglie dalla memoria i permessi della persona spostata.

---

### Quando scatta

Dopo una modifica di `unita_organizzativa_id` in cui il valore cambia davvero, anche da vuoto a valorizzato e
viceversa. Una modifica che riscrive lo stesso reparto non scatta. Il trigger passa alla funzione il rapporto, il
reparto di prima e quello nuovo, e non cambia la riga.

L'avviso parte solo se la transazione si conferma: una modifica annullata non avvisa nessuno.

---

### Test

* `db/pgtap/anagrafiche/test-notify-cambio-reparto.sql` — il trigger è montato; un cambio di reparto lo attraversa
  senza errori, e una modifica che non cambia il reparto non lo fa scattare.

Nessun test verifica che l'avviso arrivi, né che cosa porta: l'avviso parte alla conferma della transazione, e il
test si chiude annullandola.

---

{% include-markdown "signature-core.md" %}
