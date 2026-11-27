## 📘 Documentazione Concettuale – Vista `anagrafiche.vw_accessi_altri`

> **Ultimo aggiornamento**: 27 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.identita_digitali](/dbzero/anagrafiche/tabelle/identita_digitali) — le vesti di ogni credenziale
> * [config.credenziali](/dbzero/config/tabelle/credenziali) — il blocco dell'amministratore
> * [anagrafiche.clienti](/dbzero/anagrafiche/tabelle/clienti) — i clienti collegati a una veste, sotto la visibilità per riga
>
> Approfondimento viste:
>
> * [anagrafiche.vw_accessi_sistema](/dbzero/anagrafiche/views/vw_accessi_sistema) — il tab gemello, le credenziali di sistema
> * [dbops.vw_credenziali_da_sanare](/dbzero/dbops/views/vw_credenziali_da_sanare) — il presidio che legge di qui le credenziali senza veste
>
> Approfondimento funzioni:
>
> * [script.fn_categoria_accesso](/dbzero/script/funzioni/fn_categoria_accesso) — la categoria che decide il tab
> * [script.fn_stato_veste](/dbzero/script/funzioni/fn_stato_veste) — lo stato di ogni veste
> * [script.fn_credenziale_ha_vesti](/dbzero/script/funzioni/fn_credenziale_ha_vesti) — se la credenziale ha almeno una veste
> * [script.fn_credenziali](/dbzero/script/funzioni/fn_credenziali) — tutte le credenziali, da cui la vista parte
>
> Guide:
>
> * [Risorse umane e accessi](/guide/risorse-umane-e-accessi) — la credenziale e le sue vesti
> * [Architettura multi-face auth](/guide/architettura-multi-face-auth) — le vesti e le categorie di accesso

---

### 🎯 Scopo Principale

`anagrafiche.vw_accessi_altri` alimenta il tab «Altri accessi» dell'area Accessi: una riga per credenziale di
categoria `ALTRO`, cioè le persone senza veste operatore (clienti e fornitori del portale, clienti dello shop) e le
credenziali senza nessuna veste.

---

### La categoria decide il tab

La vista non ha un criterio suo: tiene le credenziali che `script.fn_categoria_accesso` mette in `ALTRO`. Ogni
credenziale ha una sola categoria (`SISTEMA` prima, poi `OPERATORE`, altrimenti `ALTRO`), quindi i tre tab dell'area
Accessi si dividono le credenziali senza sovrapporsi e senza lasciarne fuori nessuna. Una credenziale senza vesti
cade in `ALTRO`: è qui che si vede, e qui la legge il presidio delle credenziali da sanare.

La lista configurabile di questo tab è `anagrafiche.accessi_altri`, un codice di `ui.lista_definizione`. È globale,
senza perimetro per azienda: una credenziale non appartiene a un'azienda.

---

### Le colonne che vanno capite

| Colonna | Significato |
| --- | --- |
| `nome_visualizzato` | nome e cognome della credenziale; se mancano, lo username. Non il soggetto della veste: per il cliente di un'azienda sarebbe l'azienda |
| `vesti` | una voce per veste, anche spenta, col suo stato, le sue date e il soggetto collegato |
| `vesti → cliente_ids` | un **elenco**: sullo stesso ruolo ci possono essere più clienti (uno per istanza utility), e sceglierne uno vorrebbe dire scegliere per id |
| `vesti → fornitore_id` | uno solo: il fornitore è unico sul suo ruolo |
| `vesti_elenco`, `soggetti_elenco` | i tipi di veste e i soggetti in un testo: le colonne su cui la lista filtra e cerca |
| `nessun_accesso` | la credenziale non ha nessuna veste, nemmeno spenta |
| `stato_accesso` | un **riassunto per il filtro**: il migliore stato fra le vesti (`ATTIVO`, poi `PENDING`, poi `NON_SPEDITO`, poi `DISATTIVO`, poi `REVOCATA`), `NESSUNO` senza vesti. `REVOCATA` vuol dire che tutte le vesti sono revocate: una sola veste spenta senza segno fa `DISATTIVO`. Lo stato vero sta su ogni veste |
| `secondo_fattore_stato` | solo lo stato del secondo fattore: il segreto non esce |
| `bloccata`, `bloccata_dal`, `motivo_blocco` | il blocco dell'amministratore sulla credenziale |

---

### La visibilità per riga dei clienti

La vista è `security_invoker`: legge le tabelle coi permessi di chi la interroga, e attraversa
`anagrafiche.clienti`, che ha la visibilità per riga. Le righe della vista non cambiano, ma gli elenchi
`cliente_ids` sì: un operatore vede solo i clienti delle aziende del suo perimetro, e una lettura senza contesto li
vede vuoti. Un elenco vuoto non vuol dire «nessun cliente».

---

### ⚠️ Che cosa oggi non copre

* **Lo stato non guarda le date.** Lo stato di una veste dice se è accesa, se ha un invito in corso e se l'email
  dell'invito è partita; non dice se la veste è dentro la sua finestra di date. Una veste accesa ma scaduta risulta
  `ATTIVO`, e così il riassunto della credenziale. Le date sono nella voce della veste, accanto allo stato.
* **I permessi.** Il ruolo applicativo `zeroerp_app` ha sulla vista anche inserimento, modifica e cancellazione,
  che su una vista non aggiornabile non servono.

---

### Test

* `db/pgtap/anagrafiche/test-area-accessi-v1.sql` — ogni credenziale sta in un tab solo, e i tre tab insieme le
  contano tutte; la credenziale senza vesti c'è, con `nessun_accesso`, stato `NESSUNO` e vesti vuote; la voce di una
  veste porta il suo stato e il riassunto, coi `cliente_ids` come elenco; operatori e utenti tecnici non ci sono; la
  vista è `security_invoker`.
* `db/pgtap/anagrafiche/test-veste-accensione-invito-fixture-v1.sql` — `REVOCATA` quando tutte le vesti sono
  revocate, `DISATTIVO` con una revocata e una spenta; ogni stato di `script.fn_stato_veste` è nominato
  nell'aggregato.

Nessun test prova gli elenchi dei clienti letti da un operatore col suo perimetro.

---

### Note di migrazione

* 2026-10-02 — nasce con l'area Accessi, insieme al tab «Di sistema».
* 2026-10-06 — «nessuna veste» si legge da `script.fn_credenziale_ha_vesti`, la stessa regola che rifiuta
  l'eliminazione di una credenziale che ha vesti.

---

{% include-markdown "signature-core.md" %}
