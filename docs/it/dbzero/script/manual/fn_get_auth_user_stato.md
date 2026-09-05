## ⚙️ Documentazione Concettuale – Funzione `script.fn_get_auth_user_stato`

> **Versione**: 2026-09-05 (brief-db-processi-automatici-identità-e-perimetro ·
> migration `20260905-30`, prima stesura nel `20260905-23`)

> **Vedi anche**
>
[dbops.vw_processi_roster](/dbzero/dbops/manual/vw_processi_roster) — il primo, e
> per ora unico, consumatore

---

### 🎯 Scopo Principale

Dire, per un utente dell'anagrafica di Django, **come si chiama** e **se è
attivo**. Nient'altro.

Preso un identificativo, restituisce una riga sola. Se quell'utente non c'è,
restituisce **zero righe**.

---

### ⭐ Perché esiste, ed è l'unica cosa importante da sapere

Il database non possiede le tabelle di Django: le crea Django stesso, al suo
avvio, **dopo** che le migrazioni del database sono passate.

Questo produce una differenza che si vede solo su una macchina ricostruita da
zero — cioè la build automatica, mai il database di sviluppo, dove quelle tabelle
esistono da mesi:

| Che cosa nomina `django.auth_user` | Quando viene controllato | Esito su un database nuovo |
| --- | --- | --- |
| Una **funzione** | alla prima esecuzione | ✅ si crea senza problemi |
| Una **vista** | alla creazione | ⛔ la creazione fallisce |

Il 5 settembre 2026 la migrazione si è fermata esattamente lì: una vista nuova
nominava `django.auth_user`, e in quel momento la tabella non esisteva ancora.

⇒ **La regola che ne esce:** il database può *chiedere* qualcosa a Django, ma non
può *appoggiarsi strutturalmente* alle sue tabelle — niente viste, chiavi esterne
o colonne calcolate che le nominino.

⇒ Chi ha bisogno di un dato di `auth_user` **dentro una vista** passa da qui.

⚠️ Non è una novità isolata: `anagrafiche.risorse_umane_auth_user` — una vista che
si chiama proprio così — legge le identità applicative e non tocca Django. Era già
la forma giusta, semplicemente non era scritta da nessuna parte.

---

### ⚠️ Zero righe non è un errore

Le funzioni del progetto che ricevono un identificativo di norma **si fermano** se
è vuoto o assurdo. Qui no, ed è una scelta.

Questa non è una funzione chiamata da una schermata: è la **chiave di un
collegamento** dentro una vista. Un utente cancellato deve far sparire la riga —
che è il comportamento prudente — non far fallire la lettura di tutto l'elenco per
colpa di una riga sola.

---

### Che cosa NON fa

* Non decide **se un'identità può lavorare**: quella è una domanda a cinque
  condizioni e la risponde
  [vw_processi_roster](/dbzero/dbops/manual/vw_processi_roster). Qui si legge una
  delle cinque.
* Non concede privilegi propri: chi la esegue legge `django.auth_user` **con i
  propri permessi**. Il backend ce li ha, il lavoro notturno gira come
  amministratore. Darle poteri suoi vorrebbe dire darli a chiunque possa
  eseguirla.
