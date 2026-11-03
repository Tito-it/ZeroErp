## 📘 Documentazione Concettuale – Vista `dbops.vw_rls_perimetro_scoperto`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.rls_perimetro_debito](/dbzero/dbops/tabelle/rls_perimetro_debito) — il registro del debito dichiarato, che decide lo stato di ogni riga
> * [dbops.presidi](/dbzero/dbops/tabelle/presidi) — il catalogo che porta la vista nel digest
>
> Approfondimento viste:
>
> * [dbops.vw_storico_scope_da_dichiarare](/dbzero/dbops/views/vw_storico_scope_da_dichiarare) — lo stesso disegno per lo scope delle shadow di storico
> * [dbops.vw_processi_dominio_senza_difesa](/dbzero/dbops/views/vw_processi_dominio_senza_difesa) — un altro presidio che ricava il perimetro dal catalogo
>
> Guide:
>
> * [Linee guida SQL — Row Level Security](/linee-guida-sql#10-row-level-security-rls) — il meccanismo di cui la vista controlla la copertura

---

### 🎯 Scopo Principale

Le tabelle che dovrebbero filtrare i dati per azienda e non lo fanno: ogni riga è una tabella in quella
condizione, con accanto che cosa le manca e se qualcuno se n'era già accorto.

Il difetto non fa rumore. Una tabella che non filtra non dà errori e non rompe nessuna schermata:
**mostra di più**. E una difesa parziale è peggio dell'assenza, perché sembra una difesa: righe
protette una per una si possono leggere tutte dalla porta accanto.

---

### ⛔ Il perimetro non è un elenco

La vista non parte da una lista di tabelle da controllare: se la ricava dal catalogo. Due criteri,
indipendenti:

| `criterio` | Quando una tabella vi entra |
| --- | --- |
| `FIGLIA_DI_TABELLA_PROTETTA` | ha una FK verso una tabella con la row level security accesa, e lei non ha sia la RLS accesa sia almeno una policy |
| `POLICY_INERTE` | porta almeno una policy e ha la row level security spenta: la regola è scritta e non si applica |

Ne discendono due cose:

* una tabella **nuova**, appesa a un documento protetto, compare qui da sola;
* il controllo **si estende**: chiusa una tabella, le sue figlie entrano nel perimetro al giro
  successivo.

Una tabella può entrare per tutti e due i criteri: sono due righe, e due lavori distinti. Per una figlia
la colonna `manca` dice che cosa le manca (la policy, l'accensione, o tutte e due) e `padri_in_rls`
elenca i padri protetti.

---

### Le tre risposte

| `stato` | Che cosa vuol dire | Che cosa fare |
| --- | --- | --- |
| `DEBITO_DICHIARATO` | la tabella è nel registro per quel criterio, con la ragione | niente, per ora: è un lavoro con un nome |
| `NON_DICHIARATO` | nessuno l'ha guardata | **allarme**: è nata scoperta e non se n'è accorto nessuno |
| `DEBITO_ESTINTO` | il registro nomina una tabella che per quel criterio non è più scoperta, o non esiste più | togliere la riga dal registro: finché resta, fa tacere il controllo su una tabella che potrebbe tornare aperta |

⛔ **La regola non è «la vista è vuota»**: è «niente fuori da `DEBITO_DICHIARATO`». Il catalogo dei
presidi la porta nel digest settimanale con natura `ZERO` e stato atteso `DEBITO_DICHIARATO`: sono le
righe negli altri due stati a doverci essere zero.

La corrispondenza con il registro è per criterio, schema e tabella: una riga del registro vale solo
per il criterio che dichiara.

---

### ⚠️ Che cosa la vista non dice

* Che le policy siano scritte **bene**: dice che esistono e che si applicano. Se lascino passare le righe
  giuste lo provano i pgTAP funzionali, uno per famiglia di documenti.
* `FORCE ROW LEVEL SECURITY` non entra nel criterio: l'applicazione non possiede le tabelle, e per lei
  conta solo che la RLS sia accesa.
* Una tabella con la RLS accesa e nessuna policy (che nega tutto) entra solo se è figlia di una tabella
  protetta.

La vista non è `security_invoker`: legge il catalogo e il registro coi privilegi del proprietario, e
la risposta non dipende da chi interroga.

---

### Test

* `db/pgtap/rls/test-rls-perimetro-scoperto.sql` — nessuna riga fuori da `DEBITO_DICHIARATO`; ogni
  criterio ammesso dal registro è un ramo vivo della vista; su casi costruiti, una figlia nuova di una
  tabella protetta esce `NON_DICHIARATO` e armata esce dal perimetro, una figlia di una tabella non
  protetta non entra, una policy con la RLS spenta esce `POLICY_INERTE`, una riga di registro senza più
  difetto esce `DEBITO_ESTINTO`.
* `db/pgtap/dbops/test-catalogo-presidi-v1.sql` — ogni vista di presidio, questa compresa, è a
  catalogo, e lo stato della colonna dichiarata esiste davvero sulla vista.
* `db/pgtap/rls/test-rls-magazzino-perimetro-v1.sql` e
  `db/pgtap/rls/test-rls-istanze-dati-precontrattuali-v1.sql` — le tabelle chiuse da quelle famiglie
  escono dalla vista.

---

### Note di migrazione

* 2026-09-09 — nasce con il registro del debito (`brief-db-perimetro-emittente-righe-documento`, §8 e
  §10). Lo stesso giorno le partizioni delle note dei documenti avevano ciascuna la sua policy, ed erano
  leggibili per intero dalla tabella padre.

---

{% include-markdown "signature-core.md" %}
