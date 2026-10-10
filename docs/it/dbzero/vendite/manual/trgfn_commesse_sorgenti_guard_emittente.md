## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_commesse_sorgenti_guard_emittente`

> 👀 **Vedi anche**
>
Approfondimenti funzioni:
>
[script.fn_get_sorgente_emittente_sr_id](/dbzero/script/manual/fn_get_sorgente_emittente_sr_id)
>
[script.trgfn_doc_guard_emittente_ba](/dbzero/script/manual/trgfn_doc_guard_emittente_ba)
>
Approfondimenti tabelle:
>
[vendite.commesse_sorgenti](/dbzero/vendite/tabelle/commesse_sorgenti)

---
### 🎯 Scopo Principale
(latest review 26-08-26)

Impedisce che a una commessa vengano collegati documenti **di emittenti
diversi**.

---

### Perche' conta davvero

Una commessa raccoglie il lavoro che verra' fatturato insieme, e porta con se'
**un** emittente: e' quello a decidere su quale registro la fattura verra'
numerata.

Se dentro la stessa commessa finiscono documenti di due emittenti, quella scelta
smette di essere vera per una parte delle righe: il documento esce da un
emittente che con quel lavoro non c'entra, con una numerazione che non e' la sua.
E' la regola detta in una riga: **una commessa non puo' aggregare diversi
emittenti insieme**.

---

### Il criterio e' l'emittente, non il cliente

Il controllo confronta gli **emittenti**, non i clienti. Sembra una sfumatura e
non lo e'.

Piu' clienti possono stare sotto lo stesso emittente — e' esattamente a questo
che serve l'albero dei clienti — quindi vietare che un documento di un cliente
«figlio» contribuisca alla commessa di un cliente «padre» sarebbe una regola piu'
severa di quella che si e' deciso di dare, e nessuno l'ha mai decisa. Il
controllo dice quello che la regola dice: **stesso emittente**.

---

### Perche' non sta dentro la funzione che collega

Perche' quella funzione e' **uno** dei modi di scrivere su questa tabella, e ce
ne sono altri. Un controllo che vive dentro una funzione protegge da chi ci
passa; messo sulla tabella, vale per chiunque scriva — compresi i percorsi che
verranno aggiunti domani da qualcuno che non sapra' che questa regola esiste.

---

### L'ordine, che e' una decisione

Sulla stessa tabella c'e' gia' un controllo che verifica **che il documento
esista davvero**. Deve parlare per primo: e' piu' preciso, e questo controllo —
che del documento deve leggere l'emittente — su un documento inesistente non
avrebbe niente da leggere.

L'ordine fra due controlli dello stesso tipo lo decide il **nome**, in ordine
alfabetico. Non e' un dettaglio estetico: e' il motivo per cui questo si chiama
cosi', e c'e' un test che lo sorveglia.

---

### Impatto e Vantaggi

* la regola vale per ogni scrittore, non solo per il percorso previsto oggi;
* il messaggio nomina **la commessa, il documento e i due emittenti**: chi lo
  legge sa cosa sistemare senza andarlo a cercare;
* la decisione vive in **una** funzione di verifica riusabile: qui c'e' solo il
  blocco e la frase, non una seconda copia della regola.
