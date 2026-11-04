## 📘 Documentazione Concettuale – Funzione `dbops.fn_processo_acceso_su_valori`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.processi](/dbzero/dbops/tabelle/processi) — canale, ritiro, default per ambiente, spegnibile, accendibile
> * [dbops.processi_accensione](/dbzero/dbops/tabelle/processi_accensione) — la scelta a mano
> * [dbops.installazione](/dbzero/dbops/tabelle/installazione) — l'ambiente
>
> Approfondimento funzioni:
>
> * [dbops.fn_accensione_a_mano_ammessa_su_valori](/dbzero/dbops/funzioni/fn_accensione_a_mano_ammessa_su_valori) — il divieto di accensione in produzione, che la regola consulta
> * [dbops.fn_processo_acceso_dichiarato](/dbzero/dbops/funzioni/fn_processo_acceso_dichiarato) — legge i valori dal dato e chiede qui
> * [maintenance.fn_sveglia_accesa](/dbzero/maintenance/funzioni/fn_sveglia_accesa) — il cancello delle sveglie, attraverso la lettura

---

### 🎯 Scopo Principale

La regola dell'accensione della sveglia di un processo, pura sui valori: dati il catalogo, la
scelta a mano e l'ambiente, dice se la sveglia è accesa. È l'unico posto dove la regola è scritta.

---

### La regola, in ordine

| Caso | Risposta |
| --- | --- |
| il processo non ha sveglia (canale `CODA`, o `obsoleto_dal` valorizzato) | vuoto |
| il processo è **non spegnibile** | acceso, sempre: non legge né la scelta a mano né l'ambiente |
| c'è una scelta a mano e il divieto di produzione la ammette | la scelta a mano |
| l'ambiente è `SVILUPPO` | il default di sviluppo |
| l'ambiente è `PRODUZIONE` | il default di produzione |
| l'ambiente non è dichiarato | vuoto: non decidibile |

L'ordine dei rami è la regola:

* ⭐ **il non spegnibile viene prima di tutto**, così una riga che lo spegne, scritta prima che il
  catalogo lo dichiarasse tale, non lo spegne, e il suo stato non dipende da un ambiente mancante;
* ⭐ **la scelta a mano conta solo se il divieto la ammette**: una riga che accende in produzione un
  processo non accendibile si ignora, e vale il default di produzione; con l'ambiente non dichiarato
  il divieto non sa decidere, e la regola cade sul ramo dell'ambiente, cioè vuoto;
* una scelta a mano che spegne, o che accende un processo accendibile, decide anche senza ambiente.

⚠️ La regola non riceve `attivo`: un processo spento con `attivo` falso ma senza `obsoleto_dal`
risulta ancora con una sveglia.

---

### ⭐ Perché sui valori

L'ambiente di un'installazione non cambia e la CI è `SVILUPPO`: una regola che leggesse il dato
non si potrebbe provare in produzione senza riscrivere l'installazione. Sui valori, i test provano
ogni ramo passando il valore, senza costruire niente.

È immutabile e `LANGUAGE sql`, così si inlinea in chi la chiama; non è `STRICT`, perché i valori
vuoti sono casi normali (una scelta a mano assente, un processo senza sveglia).

Chi la legge: [fn_processo_acceso_dichiarato](/dbzero/dbops/funzioni/fn_processo_acceso_dichiarato)
la chiama coi valori del dato, e attraverso di lei la usano il cancello delle sveglie e il panorama
dei processi. Chi decide rende il vuoto un errore; chi descrive lo mostra.

---

### Test

* `db/pgtap/dbops/test-processi-accensione-v1.sql` — la forma (immutabile, `LANGUAGE sql`, senza
  `STRICT`), ogni ramo sui valori (senza sveglia, non spegnibile anche spento a mano o senza
  ambiente, scelta a mano nei due versi, i due default, ambiente mancante) e la scelta a mano che
  il divieto non ammette, in produzione, in sviluppo e senza ambiente.

---

### Note di migrazione

* 2026-10-16 — nasce col default di accensione per ambiente (`brief-db-processi-accensione-per-ambiente`).
* 2026-10-18 — riceve `accendibile_in_produzione` e ignora la scelta a mano che il divieto di
  produzione non ammette.

---

{% include-markdown "signature-core.md" %}
