## 📘 Documentazione Concettuale – Vista `anagrafiche.vw_accessi_sistema`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.identita_digitali](/dbzero/anagrafiche/tabelle/identita_digitali) — le vesti di ogni credenziale
> * [dbops.processi_identita](/dbzero/dbops/tabelle/processi_identita) — il processo automatico a cui appartiene un utente tecnico
> * [config.user_emittenti_fiscali](/dbzero/config/tabelle/user_emittenti_fiscali) — l'azienda per cui l'utente lavora
> * [config.credenziali](/dbzero/config/tabelle/credenziali) — il blocco dell'amministratore
>
> Approfondimento viste:
>
> * [anagrafiche.vw_accessi_altri](/dbzero/anagrafiche/views/vw_accessi_altri) — il tab gemello, gli altri accessi
>
> Approfondimento funzioni:
>
> * [script.fn_categoria_accesso](/dbzero/script/funzioni/fn_categoria_accesso) — la categoria che decide il tab
> * [script.fn_credenziali](/dbzero/script/funzioni/fn_credenziali) — tutte le credenziali, da cui la vista parte
>
> Guide:
>
> * [Risorse umane e accessi](/guide/risorse-umane-e-accessi) — la credenziale e le sue vesti
> * [Architettura multi-face auth](/guide/architettura-multi-face-auth) — le vesti e le categorie di accesso

---

### 🎯 Scopo Principale

`anagrafiche.vw_accessi_sistema` alimenta il tab «Di sistema» dell'area Accessi, in sola lettura: una riga per
credenziale di categoria `SISTEMA`, cioè gli utenti tecnici dei processi automatici e le credenziali `API_CLIENT`.

---

### Un tab in sola lettura

Queste credenziali le governa il pannello dei processi: bloccarne una da qui fermerebbe un automatismo a sua
insaputa. Il tab è la vista d'insieme; il drawer del processo, che il frontend apre da `processo_id`, resta il posto
in cui si interviene su un processo.

La vista tiene le credenziali che `script.fn_categoria_accesso` mette in `SISTEMA`: quelle con almeno una veste
tecnica o una veste `API_CLIENT`. La categoria è una sola per credenziale, e `SISTEMA` vince sulle altre: una
credenziale che fosse insieme di una persona e di sistema starebbe qui, e la segnala il presidio delle credenziali
da sanare.

La lista configurabile di questo tab è `anagrafiche.accessi_sistema`, un codice di `ui.lista_definizione`, con
perimetro e più aziende come la lista degli operatori: ogni utente tecnico lavora per un'azienda, e il super admin le
vede tutte.

---

### Le colonne che vanno capite

| Colonna | Significato |
| --- | --- |
| `tipo` | `PROCESSO` se la credenziale ha una veste tecnica, altrimenti `API_CLIENT`; con tutte e due vince `PROCESSO`, che ha un processo da aprire |
| `identita_attiva` | almeno una veste della credenziale è accesa |
| `processo_…`, `legame_processo_attivo` | il processo collegato e lo stato del legame; al più uno, perché il legame è unico sulla credenziale |
| `emittente_…` | l'azienda per cui l'utente lavora; al più una, per la stessa ragione |
| `bloccata`, `bloccata_dal`, `motivo_blocco` | il blocco dell'amministratore sulla credenziale |

Niente secondo fattore: su una macchina non ha senso.

---

### ⚠️ Che cosa oggi non copre

* **I permessi.** Il ruolo applicativo `zeroerp_app` ha sulla vista anche inserimento, modifica e cancellazione,
  che su una vista non aggiornabile, pensata per la sola lettura, non servono.

---

### Test

* `db/pgtap/anagrafiche/test-area-accessi-v1.sql` — un utente tecnico è `PROCESSO` col suo processo e la sua
  azienda; una credenziale `API_CLIENT` è senza processo; un operatore non c'è; ogni credenziale sta in un tab
  solo; la vista è `security_invoker`.

---

### Note di migrazione

* 2026-10-02 — nasce con l'area Accessi, insieme al tab «Altri accessi».

---

{% include-markdown "signature-core.md" %}
