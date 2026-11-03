## 📘 Documentazione Concettuale – Vista `dbops.vw_processi_dominio_senza_difesa`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.processi_bersagli](/dbzero/dbops/tabelle/processi_bersagli) — i bersagli col percorso dichiarato, e il flag del debito
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
>
> Guide:
>
> * [Linee guida SQL — sezione 10 RLS](/linee-guida-sql#10-row-level-security-rls) — la row level security e le sue policy
> * [Presidi e registri del debito](/guide/presidi-e-registri-del-debito) — debito dichiarato e allarme

---

### 🎯 Scopo Principale

Il livello 2 del presidio sui processi: le tabelle di dominio in cui si **sa** dove sta l'emittente,
ma nessuno lo usa per filtrare, perché manca la policy di row level security, manca il guard di
scrittura, o mancano tutti e due. L'invariante è «nessuna riga non dichiarata».

---

### ⭐ Due livelli, due lavori

| Vista | Che cosa manca |
| --- | --- |
| `vw_processi_dominio_senza_emittente` | **l'informazione**: non si sa di chi è la riga |
| questa | l'informazione c'è, **manca chi la applica** |

⛔ Fonderle sarebbe comodo e sbagliato: il primo lavoro si chiude dichiarando un percorso o
aggiungendo una colonna, il secondo scrivendo una policy o montando un guard, che sono decisioni di
sicurezza. Un elenco che mescola «da compilare» e «da proteggere» non dice quali righe siano urgenti.

Guarda i bersagli col percorso dichiarato dei processi `DOMINIO` attivi e non ritirati, sulle
tabelle che esistono (una tabella mancante la dice il livello 1).

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
| policy (lettura scoperta) | il guard c'è, la lettura no |
| write-guard (scrittura scoperta) | la policy filtra, la scrittura no |

⚠️ `FORCE ROW LEVEL SECURITY` non entra nel criterio: il proprietario deve poter leggere fuori dalla
row security per le funzioni `SECURITY DEFINER` che derivano il perimetro.

⚠️ Il guard si riconosce **dal nome della funzione**: conta qualunque trigger della tabella che
esegue `trgfn_guard_emittente_scope`, senza guardare con quale via e su quale colonna è montato.

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

---

### Note di migrazione

* 2026-09-04 — nasce col registro dei processi automatici (`brief-db-processi-automatici-identita-e-perimetro`),
  come debito da far calare.
* 2026-09-05 — nascono `stato` e `nota` (`brief-db-processi-automatici-residui-be`, DB-2).
* 2026-09-05 — una policy conta solo con la row level security attiva (`brief-db-processi-automatici-identita-e-perimetro`,
  §12.15). Non nasce da una misura, nessun bersaglio era in quello stato, ma dalla scorciatoia che
  si stava per prendere sulla policy di una tabella delle email.

---

{% include-markdown "signature-core.md" %}
