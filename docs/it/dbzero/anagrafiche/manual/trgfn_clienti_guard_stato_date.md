## 📘 Documentazione Concettuale – Funzione `anagrafiche.trgfn_clienti_guard_stato_date`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
>
[config.transizioni_stati_cliente](/dbzero/config/manual/transizioni_stati_cliente)
>
Guide:
>
[Gli stati del cliente e le loro date](/it/guide/gestione-delle-istanze-utility#gli-stati-del-cliente-e-le-loro-date)

---
### 🎯 Scopo Principale
(latest review 14-10-26)

Tiene in regola **lo stato del cliente e le date** che lo accompagnano, ogni volta che un cliente
si crea o si modifica.

---

### Le tre regole

| Regola | Errore |
| --- | --- |
| lo stato cambia solo lungo il percorso ammesso: da un chiuso si va solo a «Chiuso e fatturato», che è finale come l'annullato | `E_CLIENTE_STATO_TRANSIZIONE_INVALIDA` |
| un cliente chiuso non cambia più la data di chiusura, nemmeno quando diventa «Chiuso e fatturato» | `E_CLIENTE_DATA_CHIUSURA_IMMUTABILE` |
| ogni stato pretende la sua data | `E_CLIENTE_STATO_SENZA_DATA` |

E la chiusura non può precedere l'attivazione (`E_DATA_CHIUSURA`).

Le date che ogni stato pretende:

| Stato | Date |
| --- | --- |
| attivo, richiesta di sospensione | attivazione |
| sospeso (fatturabile o no) | attivazione, sospensione |
| chiuso (in ogni forma) | attivazione, chiusura |
| attivo dopo una sospensione | anche la riattivazione |
| pre-contrattuale, annullato, aggregante | nessuna |

Il percorso vale per i **cambi** di stato. Un cliente si può creare direttamente in qualunque
stato, purché abbia le date che lo stato pretende.

---

### Perché un cliente chiuso non si riapre

Decisione del 2026-10-13: chi torna dopo una chiusura apre una **catena nuova** (istanza, billing
account e cliente nuovi), collegata alla precedente. Il cliente chiuso resta com'è, perché la sua
data di chiusura dice fino a quando ha occupato la fornitura.

---

### Che cosa ha sostituito

Fino al 2026-10-14 due pezzi di queste regole stavano nella funzione che calcola il periodo del
cliente (l'attivo senza data di attivazione, il chiuso con la chiusura prima dell'attivazione), e
la disdetta accettava solo un cliente attivo. Ora la regola sta tutta qui, per tutti gli stati.
