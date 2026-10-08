## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_guard_istanza_ba_gestore_globale`

> 👀 **Vedi anche**
>
Approfondimenti funzioni:
>
[anagrafiche.fn_guard_istanza_ba_emittente](/dbzero/anagrafiche/manual/fn_guard_istanza_ba_emittente)
>
[anagrafiche.fn_guard_albero_ba_gestore_globale](/dbzero/anagrafiche/manual/fn_guard_albero_ba_gestore_globale) — il gemello sull'albero

---
### 🎯 Scopo Principale
(latest review 08-10-26)

Quando si sposta l'**azienda predefinita** del sistema, verifica che nessuna
istanza finisca con billing account di due aziende diverse.

---

### Perche' serve un controllo a parte

Un billing account senza un collegamento proprio a un'azienda appartiene
all'azienda predefinita. Spostare la predefinita cambia **in un colpo solo**
l'azienda di tutti quei billing account: una riga sola puo' mettere un'istanza
su due aziende, se ha un billing account collegato e uno no.

---

### Che cosa guarda

Solo i billing account **senza collegamento** che hanno un fratello nella
stessa istanza. Due fratelli entrambi senza collegamento si spostano insieme e
restano nella stessa azienda; due fratelli entrambi collegati non si spostano.
Conta la coppia **mista**, e la trova
[`fn_guard_istanza_ba_emittente`](/dbzero/anagrafiche/manual/fn_guard_istanza_ba_emittente).

Lo stesso movimento ha gia' un altro cancello — vietato se quei billing account
hanno gia' fatture o commesse
([`fn_guard_ba_gestore_globale_storia`](/dbzero/anagrafiche/manual/fn_guard_ba_gestore_globale_storia)):
questo chiede un'altra cosa, e i due si sommano.
