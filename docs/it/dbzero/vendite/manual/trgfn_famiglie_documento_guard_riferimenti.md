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

---

### 🔄 rev 2026-09-01 — ora guarda anche la **serie**, e non le basta che esista

`colonna_serie` è arrivata il 2026-09-01, il controllo era stato scritto il 30
agosto: la serie non la conosceva.

⚠️ **E questa pagina lo affermava già** — *«col nome, il controllo automatico
verifica che la colonna esista davvero e che stia nel vincolo di unicità del
numero»*. Nel database quel controllo **non c'era**: l'unico presidio era un test,
che gira quando qualcuno lo lancia, non quando qualcuno salva una riga. Da oggi
la frase è vera.

**Sulla serie i controlli sono due, e sono difetti diversi:**

| Che cosa non va | Che tipo di difetto è |
| --- | --- |
| la colonna dichiarata **non esiste** | un refuso, come per le altre tre: stesso messaggio |
| la colonna esiste ma **non distingue il numero** — non compare in nessun vincolo di unicità insieme a lui | ⭐ il caso insidioso: il nome è giusto e si legge. Ha un messaggio suo |

⛔ **Perché il secondo conta.** La serie entra nella chiave del contatore, quindi
apre un contenitore nuovo che riparte da 1. Se il documento non la porta anche
nel proprio vincolo di unicità, quel numero va a sbattere contro uno già emesso:
il documento non si numera più. È la regola generale — *tutto ciò che distingue
il contatore deve poter distinguere anche il documento*.

#### 🔴 E il trigger non nominava la colonna

Fino a oggi la lista delle colonne che risvegliano il controllo era: tabella,
colonna del numero, colonna del cliente, interruttore. **`colonna_serie` non
c'era.**

⇒ Aggiornare la sola funzione avrebbe prodotto un controllo che verifica una
colonna su cui **non viene mai chiamato**: verde in ogni prova che passi dalle
altre colonne, muto proprio sul caso per cui è stato scritto. ⚠️ E il seed che
scrive la serie tocca **esattamente e solo** quella colonna.

⭐ Trovato eseguendo l'aggiornamento vero, non leggendo il codice: il trigger è
stato ricreato con la colonna dentro.

#### ⚠️ Un dettaglio che sembra tecnico e decide il comportamento

Il controllo «la serie sta nel vincolo del numero» guarda il **testo** della
definizione dell'indice, non l'elenco delle sue colonne.

Sembra meno preciso ed è l'unico corretto: sulle fatture la serie entra
nell'unicità **dentro una funzione** — `COALESCE(serie, '')` — e per l'elenco
delle colonne quella non è una colonna. La versione «precisa» avrebbe **rifiutato
la fattura**, cioè fatto fallire la migrazione sul seed delle famiglie.
