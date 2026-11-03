## 📘 Documentazione Concettuale – Tabella `dbops.rls_perimetro_debito`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.presidi](/dbzero/dbops/tabelle/presidi) — il catalogo dei presidi, dove questo registro è dichiarato
>
> Approfondimento viste:
>
> * [dbops.vw_rls_perimetro_scoperto](/dbzero/dbops/views/vw_rls_perimetro_scoperto) — la misura che questo registro fa tacere, riga per riga
>
> Guide:
>
> * [Presidi e registri del debito](/guide/presidi-e-registri-del-debito) — la forma comune di misura e registro
> * [Linee guida SQL — RLS](/linee-guida-sql#10-row-level-security-rls) — il perimetro per emittente

---

### 🎯 Scopo Principale

L'elenco delle tabelle che **dovrebbero filtrare i dati per azienda e oggi non lo fanno**, ognuna
con scritto accanto **perché**. È il registro del presidio `dbops.vw_rls_perimetro_scoperto`: una
riga lo fa tacere su quella tabella e per quel criterio soltanto.

Non è una lista di eccezioni concesse: è un elenco di lavori con un nome. Una riga dice «sappiamo
che questa tabella è aperta, sappiamo che cosa manca per chiuderla». Non dice «va bene che sia
aperta».

---

### ⭐ Perché un registro, invece di sistemare e basta

Chiudere una tabella non è quasi mai un gesto solo tecnico: prima c'è una domanda da risolvere —
*di chi è questa riga?* — e la risposta cambia il modo in cui il programma si comporta.

Un controllo che segnalasse come errori tutte le tabelle aperte dal primo giorno verrebbe spento, e
un controllo spento è peggio di uno che non c'è, perché nessuno lo sa. ⇒ Il patto è questo: **il
controllo si accende subito**, tace su ciò che è scritto qui e parla su tutto il resto. Una tabella
nuova che nasce aperta viene segnalata il giorno stesso.

---

### ⚠️ È un debito, quindi deve calare

Ogni riga ha una data (`data_registrazione`), e una riga ferma da mesi è un'informazione, non un
dettaglio.

⛔ Quando un lavoro è finito, **la riga va tolta**. Una riga rimasta dopo la riparazione
continuerebbe a far tacere il controllo su quella tabella, anche il giorno in cui tornasse aperta
per un'altra strada. Il controllo se ne accorge da solo: la riga diventa `DEBITO_ESTINTO`.

---

### Le due regole

| `criterio` | Che cosa dice |
| --- | --- |
| `FIGLIA_DI_TABELLA_PROTETTA` | la tabella ha una chiave esterna verso una tabella con la row level security accesa: le sue righe appartengono a righe protette, e dovrebbero seguire lo stesso perimetro |
| `POLICY_INERTE` | sulla tabella una policy **è scritta** e la row level security è spenta. È il caso peggiore: da fuori sembra protetta |

Il vocabolario è chiuso da un vincolo, ed è da quel vincolo che il test legge i criteri ammessi:
un criterio nuovo senza il suo ramo nella vista fa rosso. Il criterio entra nella chiave: una
tabella può essere scoperta per tutte e due le ragioni, e allora sono due righe e due lavori.

---

### ⛔ La ragione si legge, non si timbra

`ragione` dice che cosa manca perché la tabella si possa chiudere (un adattatore, una veste, una
decisione di modello) e dove vive quel lavoro. Non un'etichetta e non un rimando nudo: chi legge il
presidio deve capire da qui se ha davanti un allarme o un cantiere aperto.

Il vincolo sulla ragione ne misura solo la **lunghezza** minima: ferma «da fare» e «vedi brief», non
una frase vuota abbastanza lunga. È un cancello economico su un difetto frequente, non una garanzia:
la qualità la giudica una persona, in review.

---

### Che cosa c'è dentro, oggi

Le righe dichiarate sono di due specie:

* **legami di anagrafica** che puntano a righe protette: fra questi le due tabelle che **definiscono**
  il legame fra un'azienda e i clienti, cioè il dato da cui il perimetro stesso si ricava. Filtrarle
  con il perimetro vorrebbe dire appoggiarle a sé stesse: lì serve prima una decisione di modello,
  non un intervento. Accanto, legami con una chiave nullable, su cui una policy lascerebbe fuori le
  righe senza chiave;
* **documenti di acquisto** con una policy scritta per il solo portale del fornitore: accendere la
  row level security con quella sola veste chiuderebbe la tabella all'operatore, che ci scrive.

---

### Test

* `db/pgtap/rls/test-rls-perimetro-scoperto.sql` — nessuna riga del presidio fuori da
  `DEBITO_DICHIARATO`; ogni criterio del vincolo è un ramo vivo; una figlia nuova di una tabella
  protetta esce non dichiarata, e armata esce dal perimetro.
* `db/pgtap/rls/test-rls-magazzino-perimetro-v1.sql`, test 2 — per il magazzino il presidio è vuoto
  e il registro non ha più righe.

---

### Note di migrazione

* 2026-09-09 — nasce col presidio del perimetro (`brief-db-perimetro-emittente-righe-documento`), con
  i debiti dichiarati di allora: lotti di fatturazione, attività fatturabili, listini, pratiche,
  documenti generati, anagrafiche, magazzino, pagamenti, acquisti e shop. Le famiglie di vendita,
  pratiche, documenti e magazzino sono state chiuse da allora; al 2026-11-03 il seed dichiara sei
  righe, di anagrafiche, pagamenti e acquisti.

---

{% include-markdown "signature-core.md" %}
