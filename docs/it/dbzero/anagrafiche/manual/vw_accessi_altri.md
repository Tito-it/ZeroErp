## 📘 Documentazione Concettuale – View `anagrafiche.vw_accessi_altri`

> 👀 **Vedi anche**
>
> [script.fn_categoria_accesso](/dbzero/script/funzioni/fn_categoria_accesso) ·
> [script.fn_stato_veste](/dbzero/script/funzioni/fn_stato_veste) ·
> [anagrafiche.vw_accessi_sistema](/dbzero/anagrafiche/views/vw_accessi_sistema)

### 🎯 Scopo

(02-10-2026 — brief `brief-db-be-fe-area-accessi`, R-DB-A2)

**Il tab «Altri accessi»**: una riga per credenziale di categoria `ALTRO` — le persone senza
veste operatore (clienti e fornitori del portale, clienti dello shop) e le credenziali
**senza alcuna veste**, che prima non mostrava nessuno. La vista non ha un predicato suo:
la categoria decide, e la partizione dei tre tab resta vera.

### Le colonne che vanno capite

| Colonna | Significato |
| --- | --- |
| `nome_visualizzato` | nome e cognome della credenziale; se Django non li ha, lo username. Non il soggetto della veste: per un cliente azienda sarebbe l'azienda |
| `vesti` | una voce per veste, anche spenta, col suo `stato` ([fn_stato_veste](/dbzero/script/funzioni/fn_stato_veste)) e il soggetto collegato |
| `vesti → cliente_ids` | ⚠️ un **elenco**: un soggetto può avere più clienti (uno per istanza utility), e sceglierne uno vorrebbe dire scegliere per id |
| `vesti → fornitore_id` | uno solo (unico sul soggetto_ruolo) |
| `vesti_elenco` | i tipi di veste in un testo: la colonna su cui la lista filtra e cerca |
| `nessun_accesso` | nessuna veste: il caso che il presidio conta |
| `stato_accesso` | **riassunto per il filtro**, il migliore stato fra le vesti (`ATTIVO > PENDING > NON_SPEDITO > DISATTIVO`), `NESSUNO` senza vesti. Lo stato vero sta su ogni veste |
| `secondo_fattore_stato` | solo lo stato del device: il segreto non esce |

### Forma

`security_invoker`: attraversa `anagrafiche.clienti`, che ha la RLS. Letta senza contesto,
gli elenchi `cliente_ids` escono vuoti (un vuoto non è un dato); le righe no. Le credenziali
vengono da [script.fn_credenziali](/dbzero/script/funzioni/fn_credenziali). Lista
configurabile: `anagrafiche.accessi_altri`, globale (`perimetro_emittente = false`: una
credenziale non appartiene a un'azienda).

### Test

`db/pgtap/anagrafiche/test-area-accessi-v1.sql` (casi 7, 11, 12, 16).
