## 📘 Documentazione Concettuale – View `dbops.vw_operatori_senza_emittente`

> 👀 **Vedi anche**
>
Approfondimenti tabelle:
>
[config.user_emittenti_fiscali](/dbzero/config/tabelle/user_emittenti_fiscali)
>
Approfondimenti funzioni:
>
[script.fn_change_user_emittenti_scope](/dbzero/script/manual/fn_change_user_emittenti_scope)

---
### 🎯 Scopo Principale
(latest review 18-08-26)

Elenca gli operatori **configurati a meta'**: hanno un'identita' attiva, non sono
amministratori di sistema, e non hanno l'emittente fiscale assegnato.

> ⚠️ **Deve restare a zero righe.** Una riga qui e' una persona che apre
> l'applicazione e non trova niente.

---

### Perche' esiste

Da quando l'assegnazione dell'emittente e' obbligatoria, chi non ce l'ha **non
vede piu' nulla**. E' il comportamento corretto — prima vedeva gli emittenti di
chiunque, ed era indistinguibile da un amministratore — ma ha una proprieta'
sgradevole: **non si annuncia**.

Non c'e' un errore, non c'e' un messaggio. C'e' una schermata vuota. A differenza
di un controllo che blocca e spiega, questo difetto e' silenzioso per
costruzione: lo scopre l'interessato, e lo segnala come un guasto.

Questa vista lo trasforma in una cosa che **si guarda** invece che in una cosa
che si subisce.

---

### Chi e' escluso, e perche'

L'**amministratore di sistema** e' legittimamente senza assegnazione: il suo
perimetro passa da un'altra strada. Comparirebbe come falso allarme, e un
cruscotto con dentro un falso allarme fisso e' un cruscotto che si smette di
guardare.

---

### Come si sistema una riga

Con la funzione di dominio che assegna l'emittente a un utente, **non** con una
scrittura diretta: e' quella la sede unica del modello «un operatore, un
emittente», ed e' li' che stanno i controlli.
