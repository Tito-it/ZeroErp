## 📘 Documentazione Concettuale – View `anagrafiche.vw_accessi_sistema`

> 👀 **Vedi anche**
>
> [script.fn_categoria_accesso](/dbzero/script/funzioni/fn_categoria_accesso) ·
> [dbops.processi_identita](/dbzero/dbops/tabelle/processi_identita) ·
> [anagrafiche.vw_accessi_altri](/dbzero/anagrafiche/views/vw_accessi_altri)

### 🎯 Scopo

(02-10-2026 — brief `brief-db-be-fe-area-accessi`, R-DB-A2-bis)

**Il tab «Di sistema»**, in sola lettura: una riga per credenziale di categoria `SISTEMA`,
cioè gli utenti tecnici dei processi automatici e le credenziali `API_CLIENT`. Il
proprietario di queste credenziali è il pannello dei processi: bloccarne una da qui
fermerebbe un automatismo a sua insaputa. Questa è la vista d'insieme; il drawer del
processo resta la vista di un processo.

* `tipo`: `PROCESSO` (una veste con `tecnica`) o `API_CLIENT`; con tutte e due vince
  `PROCESSO`, che ha un processo da aprire.
* Il processo (`dbops.processi_identita`) e l'emittente (`config.user_emittenti_fiscali`) sono
  al più uno ciascuno: entrambe le tabelle sono uniche sull'utente.
* Niente secondo fattore: su una macchina non ha senso.

Lista configurabile `anagrafiche.accessi_sistema`, con perimetro e multi-emittente come
`anagrafiche.operatori`: ogni utente tecnico lavora per un'azienda, e il super admin le vede
tutte (la colonna `emittente_codice` lo dice per ogni riga).

### Test

`db/pgtap/anagrafiche/test-area-accessi-v1.sql` (casi 13, 16).
