## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_guard_istanza_ba_emittente`

> 👀 **Vedi anche**
>
Approfondimenti funzioni:
>
[anagrafiche.fn_check_ba_coppia_emittente_omogenea](/dbzero/anagrafiche/manual/fn_check_ba_coppia_emittente_omogenea)
>
[anagrafiche.fn_guard_albero_ba_emittente](/dbzero/anagrafiche/manual/fn_guard_albero_ba_emittente) — il gemello sull'albero padre/figlio
>
[anagrafiche.fn_guard_istanza_ba_gestore_globale](/dbzero/anagrafiche/manual/fn_guard_istanza_ba_gestore_globale)

---
### 🎯 Scopo Principale
(latest review 08-10-26)

Verifica che un billing account appartenga alla **stessa azienda emittente**
di tutti gli altri billing account della sua istanza, e blocca l'operazione se
non e' cosi'.

---

### Perche' conta davvero

«Di chi e' questa istanza?» ha una risposta sola: dell'azienda del suo billing
account. E' la regola con cui l'applicazione decide chi puo' vedere
un'istanza. Un'istanza con due billing account di due aziende diverse sarebbe
di entrambe, e la risposta smetterebbe di esistere.

Decisione di Tid del 2026-10-08: un'istanza ha billing account di una sola
azienda.

---

### Lo stesso confronto dell'albero

Il controllo e' il gemello di quello sull'albero padre/figlio dei billing
account: cambia l'insieme guardato — qui i **fratelli di istanza**, la' padre e
figli — e il confronto e' lo stesso,
[`fn_check_ba_coppia_emittente_omogenea`](/dbzero/anagrafiche/manual/fn_check_ba_coppia_emittente_omogenea).
L'azienda confrontata e' quella **risolta** (collegamento proprio oppure azienda
predefinita), come la usa la fatturazione: due controlli che la calcolassero in
modo diverso potrebbero dire cose diverse sullo stesso billing account.

---

### Perche' e' privilegiata

Legge la tabella dei billing account, protetta da regole di visibilita' per
emittente: con i permessi di chi scrive, un fratello di un'altra azienda sarebbe
invisibile, e il controllo direbbe «a posto» proprio nel caso da bloccare.

---

### Errore

`E_ISTANZA_EMITTENTI_DIVERSI` — nomina i due billing account e l'istanza.
