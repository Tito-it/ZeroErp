## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_famiglie_documento_guard_riferimenti`

> 👀 **Vedi anche**
>
Approfondimenti tabelle:
>
[vendite.famiglie_documento](/dbzero/vendite/manual/famiglie_documento)
>
Approfondimenti funzioni:
>
[anagrafiche.fn_ba_ha_storia_emittente](/dbzero/anagrafiche/manual/fn_ba_ha_storia_emittente)
> • [anagrafiche.fn_get_storia_emittente_ba](/dbzero/anagrafiche/manual/fn_get_storia_emittente_ba)

---
### 🎯 Scopo Principale
(latest review 31-08-2026)

Controlla che una riga **attiva** del catalogo delle famiglie di documento nomini
**cose che esistono davvero**: la tabella, la colonna del numero e la colonna del
cliente. Se una non c'è, la riga non si salva.

---

### Perché serve: è il prezzo di una scelta, e si paga qui

Il controllo che impedisce di spostare un cliente da un emittente all'altro non
ha più un elenco di tabelle scritto dentro di sé: lo **legge dal catalogo** e
costruisce le proprie interrogazioni al volo, con quei nomi.

È il modo giusto — toglie di mezzo l'elenco parallelo che prima o poi resta
indietro — ma sposta un rischio. Un nome sbagliato nel catalogo **non dà fastidio
a nessuno** finché qualcuno non prova a spostare un cliente. Lì l'errore uscirebbe
come *«tabella inesistente»*, nudo: dentro un controllo che parla di clienti ed
emittenti, in un'operazione che con le famiglie di documento non c'entra niente, e
senza nominare la propria causa.

⭐ Questo controllo sposta l'errore **dal momento in cui fa male al momento in cui
si capisce**: chi scrive la riga sbagliata lo scopre subito, e il messaggio dice
esattamente quale nome non esiste.

⭐ Non è un meccanismo inventato per l'occasione: la tabella gemella che dichiara
dove vive un codice automatico ha già lo stesso identico controllo.

---

### Le famiglie ritirate non si controllano, ed è deliberato

Una famiglia spenta può nominare una tabella che non c'è più. È **storia**, non
configurazione: quella riga serve a ricordare che quel tipo di documento è
esistito. Pretendere che resti valida costringerebbe a cancellarla, cioè a
perdere l'informazione.

⛔ **Ma riaccenderla ripassa dal controllo.** È la metà che si dimentica: senza,
una famiglia ritirata male tornerebbe in circolo rotta e in silenzio, e il difetto
ricomparirebbe al primo spostamento di un cliente — cioè dove nessuno lo sta
guardando.

---

### Perché non controlla a ogni modifica

Guarda solo quando cambia qualcosa che conta: la tabella, le due colonne, o
l'interruttore acceso/spento. Ritoccare una descrizione non rivalida niente —
altrimenti una riga ritirata male diventerebbe **impossibile da correggere**, con
un errore che parla di colonne che nessuno stava toccando.

---

### Impatto e Vantaggi

* un refuso nel catalogo si scopre **quando lo si scrive**, non mesi dopo in
  un'operazione scollegata;
* il messaggio nomina la famiglia e il riferimento mancante: si sa dove mettere
  le mani senza doverlo dedurre.
