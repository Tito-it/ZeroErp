## 📘 Documentazione Concettuale – Funzione Trigger `anagrafiche.trgfn_efba_guard_albero_emittente`

> 👀 **Vedi anche**
>
Approfondimenti funzioni:
>
[anagrafiche.fn_guard_albero_ba_emittente](/dbzero/anagrafiche/manual/fn_guard_albero_ba_emittente)
>
[anagrafiche.fn_guard_albero_ba_gestore_globale](/dbzero/anagrafiche/manual/fn_guard_albero_ba_gestore_globale)

---
### 🎯 Scopo Principale
(latest review 18-08-26)

Fa scattare il controllo dell'albero omogeneo quando cambia **l'emittente** di
un billing account.

---

### Sono TRE movimenti, non uno

E' la parte che si sottovaluta: l'emittente di un billing account puo' cambiare
in tre modi diversi, e solo il primo e' ovvio.

| # | Cosa succede | Effetto |
| --- | --- | --- |
| 1 | si **modifica** l'assegnazione | il billing account cambia emittente |
| 2 | si **cancella** l'assegnazione | ricade sul gestore globale: cambia emittente **senza che nessuno abbia scritto un emittente** |
| 3 | si sposta il **gestore globale** | cambiano insieme tutti quelli non assegnati: **raggio ampio** |

Il secondo e' quello che sfugge leggendo il codice; il terzo e' quello che con
una riga sola puo' spaccare un numero arbitrario di alberi.

---

### Contesto di Esecuzione

* **Tipo**: trigger `AFTER` su inserimento, modifica e cancellazione
* Deve girare **dopo** la scrittura, perche' il controllo rilegge l'assegnazione
  per risolvere l'emittente: prima, leggerebbe lo stato vecchio.

---

### Una differenza da conoscere

La tabella delle assegnazioni **non** ha le regole di visibilita' per emittente,
a differenza dei billing account. I due trigger di questo controllo lavorano
quindi con due visibilita' diverse — ed e' una delle ragioni per cui la lettura
dei billing account e' incapsulata in una funzione privilegiata invece che
scritta qui.
---

### ⚠️ Una nota del 2026-08-26: i tre movimenti sono ora condizionati

I tre movimenti che questo controllo presidia — creare, cambiare e cancellare
l'aggancio — **non sono più operazioni ordinarie**. Dal 2026-08-26 sono ammessi
solo finché il cliente non ha storia: nessuna fattura, nessuna commessa.

⛔ Non è un divieto, è una **condizione**. Un cliente nasce già agganciato
all'emittente di chi lo crea, quindi può nascere sbagliato: la correzione deve
restare possibile finché su quel cliente non è passato del lavoro.

Il fratello che lo impone è
[`trgfn_efba_guard_storia_emittente`](/dbzero/anagrafiche/manual/trgfn_efba_guard_storia_emittente):
uno dice *«l'albero non può diventare misto»*, l'altro *«la storia non si
sposta»*.
