## 📘 Documentazione Concettuale – Tabella `dbops.rls_perimetro_debito`

> 👀 **Vedi anche**
>
**Approfondimento viste:**
>
• [dbops.vw_rls_perimetro_scoperto](/dbzero/dbops/manual/vw_rls_perimetro_scoperto)
>

### 🎯 Scopo Principale
(latest review 09-09-2026)

L'elenco delle tabelle che **dovrebbero filtrare i dati per azienda e oggi non
lo fanno**, ognuna con scritto accanto **perché**.

Non è una lista di eccezioni concesse: è un elenco di lavori con un nome. Una
riga qui dice *«sappiamo che questa tabella è aperta, sappiamo cosa manca per
chiuderla, e chi lo farà»*. Non dice *«va bene che sia aperta»*.

---

### ⭐ A che cosa serve avere un elenco, invece di sistemare e basta

Perché sono tante, e chiudere una tabella non è mai un gesto solo tecnico: quasi
sempre c'è prima una domanda da risolvere — *di chi è questa riga?* — e la
risposta cambia il modo in cui il programma si comporta.

Se il controllo automatico segnalasse tutte e trenta le tabelle come errori dal
primo giorno, la prima cosa che succederebbe è che qualcuno lo spegnerebbe. E un
controllo spento è peggio di un controllo che non c'è, perché nessuno lo sa.

⇒ Il patto è questo: **il controllo si accende subito**, tace su ciò che è
scritto qui, e parla su tutto il resto. Una tabella nuova che nasce aperta viene
segnalata **il giorno stesso**.

---

### ⚠️ È un debito, quindi deve calare

L'elenco non è arredamento e non deve stabilizzarsi: ogni riga ha una data, e
una riga ferma da mesi è un'informazione, non un dettaglio.

⛔ E quando un lavoro è finito, **la riga va tolta**. Non è pignoleria: una riga
rimasta dopo la riparazione continuerebbe a far tacere il controllo su quella
tabella — anche il giorno in cui tornasse aperta per un'altra strada. Il
controllo se ne accorge da solo e lo segnala.

---

### Campi chiave

* `criterio`: **per quale regola** la tabella è finita nell'elenco. Sono due, e
  sono indipendenti — una tabella può esserci per tutte e due, e allora sono due
  righe e due lavori distinti;
* `schema_tabella` / `nome_tabella`: la tabella;
* `ragione`: che cosa manca perché si possa chiudere, e dove vive quel lavoro.
  ⛔ Non un rimando nudo e non un'etichetta: chi legge la segnalazione deve
  capire da qui se ha davanti un allarme o un cantiere già aperto;
* `data_registrazione`: da quando il debito è dichiarato.

---

### ⭐ Le due regole, dette in parole

| `criterio` | Che cosa dice |
| --- | --- |
| `FIGLIA_DI_TABELLA_PROTETTA` | questa tabella contiene righe che **appartengono** a righe già protette — le righe di un documento, gli allegati di una pratica — e quindi dovrebbe seguire lo stesso perimetro |
| `POLICY_INERTE` | su questa tabella una regola di filtro **è scritta**, e non viene applicata. È il caso peggiore: da fuori sembra protetta |

---

### Le famiglie di oggi, per capire di che ordine di lavoro si parla

I documenti di vendita sono stati chiusi. Restano fuori, ognuna con il suo
cantiere: i satelliti dei **lotti di fatturazione**, le **attività fatturabili**
e ciò che pende da loro, la catena dei **listini**, i sette satelliti delle
**pratiche**, gli eventi e il file dei **documenti generati**, e alcune tabelle
di **anagrafiche**, **magazzino**, **pagamenti**, **acquisti** e **shop**.

⚠️ Due di quelle tabelle sono un caso a parte, e la ragione lo dice: sono le
tabelle che **definiscono** il legame fra un'azienda e i suoi clienti, cioè il
dato da cui il perimetro stesso si ricava. Filtrarle con il perimetro
significherebbe appoggiarle a sé stesse: lì prima serve una decisione, non un
intervento.

Origine: `docs/it/dev/work-done/brief-db-perimetro-emittente-righe-documento.md` §8.

---

{% include-markdown "signature-core.md" %}
