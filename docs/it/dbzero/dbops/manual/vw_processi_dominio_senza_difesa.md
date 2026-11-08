## 📘 Documentazione Concettuale – Vista `dbops.vw_processi_dominio_senza_difesa`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.processi_bersagli](/dbzero/dbops/tabelle/processi_bersagli) — i bersagli col percorso dichiarato, la porta di scrittura e il flag del debito
> * [dbops.processi](/dbzero/dbops/tabelle/processi) — i processi dichiarati `DOMINIO`
> * [dbops.presidi](/dbzero/dbops/tabelle/presidi) — il catalogo in cui la vista è un presidio
>
> Approfondimento viste:
>
> * [dbops.vw_processi_dominio_senza_emittente](/dbzero/dbops/views/vw_processi_dominio_senza_emittente) — il livello 1: non si sa di chi è la riga
>
> Approfondimento funzioni:
>
> * [script.trgfn_guard_emittente_scope](/dbzero/script/funzioni/trgfn_guard_emittente_scope) — il guard di scrittura che la vista cerca
> * [script.fn_e_obsoleto](/dbzero/script/funzioni/fn_e_obsoleto) — la regola del processo vivo
>
> Guide:
>
> * [Linee guida SQL — sezione 10 RLS](/linee-guida-sql#10-row-level-security-rls) — la row level security e le sue policy
> * [Presidi e registri del debito](/guide/presidi-e-registri-del-debito) — debito dichiarato e allarme

---

### 🎯 Scopo Principale

Il livello 2 del presidio sui processi: le tabelle di dominio in cui si **sa** dove sta l'emittente,
ma nessuno lo usa per filtrare, perché manca la policy di row level security, manca la difesa di
scrittura (il guard o una porta dichiarata), o mancano tutte e due. L'invariante è «nessuna riga non dichiarata».

---

### ⭐ Due livelli, due lavori

| Vista | Che cosa manca |
| --- | --- |
| `vw_processi_dominio_senza_emittente` | **l'informazione**: non si sa di chi è la riga |
| questa | l'informazione c'è, **manca chi la applica** |

⛔ Fonderle sarebbe comodo e sbagliato: il primo lavoro si chiude dichiarando un percorso o
aggiungendo una colonna, il secondo scrivendo una policy o montando un guard, che sono decisioni di
sicurezza. Un elenco che mescola «da compilare» e «da proteggere» non dice quali righe siano urgenti.

Guarda i bersagli col percorso dichiarato dei processi `DOMINIO` vivi (ritiro non raggiunto,
`script.fn_e_obsoleto`: un ritiro programmato resta nel presidio fino al suo giorno), sulle tabelle
che esistono (una tabella mancante la dice il livello 1).

---

### ⛔ Una policy conta solo se la row level security è attiva

Il database conserva le policy di una tabella con la row level security disattivata, e non le
applica. Se bastasse **scrivere** una policy, una tabella aperta a tutti sparirebbe da qui con una
decorazione. Per questo la colonna `manca` distingue:

| `manca` | Che cosa vuol dire |
| --- | --- |
| policy e write-guard | niente filtra, né in lettura né in scrittura |
| la policy c'è ma la row level security non è attiva, e manca il write-guard | la policy non filtra, e la scrittura è scoperta |
| la policy c'è ma la row level security non è attiva | la policy non filtra niente |
| policy (lettura scoperta) | la scrittura è difesa, la lettura no |
| la porta di scrittura dichiarata non esiste o non è `SECURITY DEFINER`, e manca il write-guard | la porta dichiarata non vale come difesa |
| la porta di scrittura è dichiarata ma le policy non coprono `INSERT` e `UPDATE`, e manca il write-guard | la porta c'è, ma le scritture dell'applicazione sono scoperte |
| write-guard (scrittura scoperta) | la policy filtra, la scrittura no |

⚠️ `FORCE ROW LEVEL SECURITY` non entra nel criterio: il proprietario deve poter leggere fuori dalla
row security per le funzioni `SECURITY DEFINER` che derivano il perimetro.

---

### ⭐ Due modi di difendere la scrittura

La scrittura è difesa da **uno** di questi:

* **il guard** `script.trgfn_guard_emittente_scope`, riconosciuto per la funzione esatta (non
  un'omonima in un altro schema), montato su `INSERT` **e** su `UPDATE`, e non disattivato. Non
  guarda con quale via e su quale colonna è montato: quella coerenza la controlla il pgTAP del
  registro dei modi;
* **la porta dichiarata** in `dbops.processi_bersagli.porta_scrittura`: una funzione
  `SECURITY DEFINER` da cui passa ogni scrittura del processo, su una tabella con la row level
  security attiva e policy permissive che coprono `INSERT` e `UPDATE`. La policy difende le
  scritture dell'applicazione, la porta quelle del proprietario, che la row security non filtra.
  Serve dove il guard non si può montare, perché respinge le scritture senza utente che passano da
  una funzione `SECURITY DEFINER`.

---

### ⭐ Debito dichiarato contro allarme

Come la sorella di livello 1, ogni riga ha uno `stato` (da `dbops.processi_bersagli.debito_dichiarato`)
e una `nota`. `DEBITO_DICHIARATO` è un lavoro con un nome, `NON_DICHIARATO` un allarme; dichiarare
un debito dice «sappiamo perché è qui», non «va bene che ci sia».

⇒ «Senza difesa», in pratica, vuol dire che un utente collegato all'applicazione, anche di un'altra
azienda, può leggere o scrivere quelle righe con un'operazione normale.

---

### Chi la guarda

Nel catalogo dei presidi è un presidio a stato, guardato ogni giorno, che tocca allo sviluppo. La
vista gira coi privilegi del proprietario.

---

### Test

* `db/pgtap/dbops/test-processi-registro.sql` — un bersaglio col percorso ma senza difesa,
  costruito, compare.
* `db/pgtap/dbops/test-presidi-debito-dichiarato.sql` — un bersaglio scoperto e dichiarato si
  presenta come debito; una policy scritta con la row level security spenta non conta come difesa.
* `db/pgtap/rls/test-rls-fatture-stampa-coda-write-guard.sql`, `db/pgtap/rls/test-rls-listini-ef-whitelist-write.sql`
  — le tabelle protette non compaiono nel presidio.
* `db/pgtap/dbops/test-processo-vivo-v1.sql` — su una tabella di prova: senza guard compare;
  un'omonima del guard in un altro schema e il guard disattivato non difendono; il guard vero
  acceso su `INSERT` e `UPDATE` la toglie; la porta `DEFINER` con RLS e policy la toglie, la porta
  `INVOKER` o con la RLS spenta no; `dbops.coda_lavori` non compare; un processo a ritiro raggiunto
  non porta qui i suoi bersagli.

---

### Note di migrazione

* 2026-09-04 — nasce col registro dei processi automatici (`brief-db-processi-automatici-identita-e-perimetro`),
  come debito da far calare.
* 2026-09-05 — nascono `stato` e `nota` (`brief-db-processi-automatici-residui-be`, DB-2).
* 2026-09-05 — una policy conta solo con la row level security attiva (`brief-db-processi-automatici-identita-e-perimetro`,
  §12.15). Non nasce da una misura, nessun bersaglio era in quello stato, ma dalla scorciatoia che
  si stava per prendere sulla policy di una tabella delle email.
* 2026-11-08 — il guard si riconosce per la funzione esatta, acceso e montato su `INSERT` e
  `UPDATE` (prima bastava il nome della funzione in un trigger qualsiasi), e la porta dichiarata
  in `porta_scrittura` diventa una difesa di scrittura: `dbops.coda_lavori` esce dal debito.

---

{% include-markdown "signature-core.md" %}
