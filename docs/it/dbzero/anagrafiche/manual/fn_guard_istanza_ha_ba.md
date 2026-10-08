## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_guard_istanza_ha_ba`

> 👀 **Vedi anche**
>
Approfondimenti funzioni:
>
[anagrafiche.trgfn_istanze_utilities_require_utility_dichiarata](/dbzero/anagrafiche/manual/trgfn_istanze_utilities_require_utility_dichiarata)
>
[anagrafiche.trgfn_billing_account_require_istanza_ha_ba](/dbzero/anagrafiche/manual/trgfn_billing_account_require_istanza_ha_ba)
>
Guide:
>
[Ogni istanza nasce col suo billing account](/it/guide/gestione-delle-istanze-utility#ogni-istanza-nasce-col-suo-billing-account)

---
### 🎯 Scopo Principale
(latest review 08-10-26)

Verifica che un'istanza utility **abbia il suo billing account**, e blocca
l'operazione se non ce l'ha.

---

### La regola

Decisione di Tid del 2026-10-08: istanza e billing account nascono **insieme**,
nella stessa operazione, sempre. Un'istanza senza billing account non e' una
fase del ciclo di vita — non c'e' una «fase prospect» con la sola istanza — ma
un dato fuori regola.

---

### Due modi di rompere la regola, un solo controllo

La regola si rompe in due momenti, e questa funzione e' il controllo di
entrambi:

| Momento | Chi la chiama |
| --- | --- |
| nasce un'istanza senza billing account | il controllo sulla nascita dell'istanza |
| si cancella l'ultimo billing account di un'istanza che resta | il controllo sulla cancellazione del billing account |

Un terzo modo — spostare il billing account su un'altra istanza — non passa da
qui: lo impedisce il blocco della colonna (`E_BA_ISTANZA_IMMUTABILE`).

Il controllo avviene **alla conferma dell'operazione**: dentro la stessa
operazione l'istanza puo' essere scritta prima del suo billing account, e
un'istanza puo' essere cancellata insieme ai suoi billing account.

---

### Perche' e' privilegiata

La funzione legge la tabella dei billing account, protetta da regole di
visibilita' per emittente. Con i permessi di chi scrive, un billing account fuori
dal suo perimetro sarebbe invisibile, e il controllo rifiuterebbe un'istanza che
il suo billing account ce l'ha. Gira quindi con i privilegi del proprietario.

---

### Errore

`E_ISTANZA_SENZA_BA` — *«L'istanza %s resterebbe senza billing account»*, col
codice dell'istanza.
