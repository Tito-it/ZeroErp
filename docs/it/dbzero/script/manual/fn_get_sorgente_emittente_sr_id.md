## 📘 Documentazione Concettuale – Funzione `script.fn_get_sorgente_emittente_sr_id`

> 👀 **Vedi anche**
>
Approfondimenti funzioni:
>
[script.trgfn_guard_sorgente_polimorfa_testuale](/dbzero/script/manual/trgfn_guard_sorgente_polimorfa_testuale)
>
[vendite.trgfn_commesse_sorgenti_guard_emittente](/dbzero/vendite/manual/trgfn_commesse_sorgenti_guard_emittente)
>
Guide:
>
[Sorgente polimorfa](/guide/sorgente-polimorfa)

---
### 🎯 Scopo Principale
(latest review 26-08-26)

Dato un documento indicato «alla maniera universale» — un tipo e una chiave —
risponde alla domanda **«chi lo emette?»**.

---

### Il pezzo che mancava

Il meccanismo con cui in Zero ERP ci si aggancia a un documento qualsiasi sapeva
già rispondere a due domande:

* **esiste?** — lo verifica il controllo della sorgente polimorfa;
* **in che stato è?** — lo traduce la vista dello stato sorgente.

Non sapeva rispondere alla terza, **chi lo emette** — ed è quella che serve per
dire se due documenti appartengono allo stesso emittente. Da qui la funzione:
una sola, scritta una volta, invece della stessa lettura ricopiata in ogni punto
che ne avrà bisogno.

---

### ⛔ La strada sbagliata, e perché è istruttiva

La prima versione chiedeva l'emittente **al cliente** del documento: sembrava la
strada generica. Non lo è.

| tabella | il cliente | l'emittente |
| --- | --- | --- |
| ordini, preventivi, DDT, resi | **può mancare** | c'è sempre |
| contratti, offerte | c'è sempre | c'è sempre |

Su **quattro tabelle su sei** il cliente può non esserci — ed è uno stato
**legittimo**, non un errore. Il risolutore si fermava su documenti
perfettamente validi.

⇒ La regola che ne esce vale ben oltre questa funzione: **un controllo che
rifiuta una situazione che il modello ammette non è severo, è rotto.**

L'ha scoperto un test, non un ragionamento: un file di prova che crea ordini
senza cliente **di proposito**.

---

### Le tre strade, in ordine di direttezza

1. **La colonna dell'emittente in convenzione interna** — commesse, fatture,
   lotti: è già la risposta, si copia;
2. **L'emittente del documento**, tradotto — i sei documenti di vendita: è la
   strada normale, e quella colonna non è mai vuota;
3. **Il cliente** — le due tabelle di attività, che un emittente proprio non ce
   l'hanno.

Nessuna delle tre disponibile ⇒ errore.

---

### Perché è privilegiata

I documenti sono protetti da regole di visibilità per emittente. Se questa
funzione girasse con i permessi di chi la chiama, **il documento di un altro
emittente sarebbe invisibile**, e chi la interroga concluderebbe «non esiste»
invece di «è di un altro».

Sono due risposte diverse: la prima è un errore da segnalare, la seconda è
esattamente il caso che i controlli a valle devono bloccare.

---

### Perché non risponde mai «non lo so»

Ogni strada che non porta a un risultato certo si ferma con un errore parlante.
Non è rigidità: un risolutore che rispondesse «non lo so» lascerebbe passare il
confronto a valle e trasformerebbe il controllo che lo usa in **un controllo che
non controlla niente**. Silenziosamente.

---

### La trappola della chiave

La chiave da passare è quella **canonica**, cioè quella che il sistema
memorizza — per alcuni tipi l'identificativo numerico, per altri il codice
universale. **Non** quella che il processo di push passa in giro, che è sempre
la seconda forma.

Dedurla da chi chiama, invece che dal catalogo, produce una funzione che non
trova mai niente. In silenzio.

«Canonica» vuol dire anche **scritta come la scrive il database** (dal 2026-10-05): una
chiave con maiuscole, zeri davanti o spazi riceve `E_SORG_FORMATO`. La regola è quella dei
building block [script.fn_sorgente_chiave_id](/dbzero/script/funzioni/fn_sorgente_chiave_id) /
[script.fn_sorgente_chiave_uuid](/dbzero/script/funzioni/fn_sorgente_chiave_uuid), la stessa del
guard della sorgente polimorfa.

---

### Impatto e Vantaggi

* una definizione sola di «chi emette questo documento», riusabile da chiunque;
* nessuna scorciatoia sui permessi: la funzione vede tutto **per rispondere
  correttamente**, non per aggirare il perimetro di chi la chiama — il filtro di
  visibilità resta di chi la usa.
