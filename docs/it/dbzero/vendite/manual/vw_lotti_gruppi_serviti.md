## 📘 Documentazione Concettuale – Vista `vendite.vw_lotti_gruppi_serviti`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.fatturazione_lotti_gruppi](/dbzero/vendite/tabelle/fatturazione_lotti_gruppi) — registra il **permesso**, non il servito
> * [vendite.attivita_fatturabili](/dbzero/vendite/tabelle/attivita_fatturabili) — il perno fra fattura e riga di commessa
>
> Approfondimento funzioni:
>
> * [vendite.fn_esito_gruppi_giro](/dbzero/vendite/funzioni/fn_esito_gruppi_giro) — il verdetto di un giro, che confronta questo **fatto** con il perimetro richiesto
> * [vendite.fn_list_emittibili_lane](/dbzero/vendite/funzioni/fn_list_emittibili_lane) — il suo `gruppi_coperti` è una **previsione**, questa è la **misura**
> * [vendite.fn_gruppo_fatturabile_key_di_attivita](/dbzero/vendite/funzioni/fn_gruppo_fatturabile_key_di_attivita) — la chiave di gruppo di una riga di commessa
> * [vendite.fn_build_gruppo_fatturabile_key](/dbzero/vendite/funzioni/fn_build_gruppo_fatturabile_key) — unica fonte della forma della chiave

---

### 🎯 Scopo Principale

**Quali gruppi fatturabili un lotto ha davvero servito.** Una riga per ogni combinazione (lotto, gruppo, commessa) per cui esiste almeno un'attività finita su una riga di fattura di quel lotto, con quante attività e quante fatture.

---

### ⭐ Perché esiste: la differenza fra prevedere e misurare

Quando un operatore chiede di fatturare tre gruppi, il motore prima **scopre** che cosa può fare
(`fn_list_emittibili_lane`, che dichiara anche `gruppi_coperti`) e poi **esegue**. Fra i due momenti
passa del tempo, e in quel tempo le righe di un gruppo possono essere prese da un altro giro.

Il risultato è la forma di difetto peggiore, perché è muta: nessun fallito, nessun gruppo scoperto,
e un gruppo non è stato fatturato. L'esito legge «pieno successo» mentre del lavoro è rimasto
fermo, e nessuno lo va a cercare. Questa vista è la misura fatta **dopo**, l'unica che può
contraddire la previsione.

---

### 🧭 Come si legge la catena

La domanda «questa attività è stata fatturata, e da quale lotto?» si risolve in quattro salti, tutti
già esistenti:

```text
fatturazione_lotti_fatture → fatture → fatture_righe
                                     → attivita_fatturabili (fattura_riga_id valorizzato)
                                     → commesse_attivita    (la riga di origine)
```

Il perno è `attivita_fatturabili.commessa_attivita_id`, che è **unico**: ogni riga di commessa ha al
più una controparte fatturabile, quindi il conteggio non può gonfiarsi. `fattura_riga_id`
valorizzato è ciò che significa «fatturata»: più attività possono condividere la stessa riga di
fattura, ed è il motivo per cui si contano le **attività**, non le righe.

---

### ⚠️ Tre cose da sapere prima di usarla

**1. La chiave viene dalla riga di commessa.** La chiave del gruppo la calcola
`vendite.fn_gruppo_fatturabile_key_di_attivita` sul tipo del documento, sul `segment_key` e sulla
commessa della **riga di commessa**: è la stessa funzione che usano la lane, l'elenco dei gruppi e i
filtri dell'emissione mirata. L'attività fatturabile non ha una provenienza sua (la sua provenienza
è la riga di commessa), quindi non c'è una seconda copia della chiave da cui partire: servito e
richiesto restano confrontabili per costruzione.

**2. È una misura viva, non un registro storico.** Se un lotto torna in bozza e le sue fatture
spariscono, il gruppo smette di risultare servito. È corretto — la fattura non c'è più — ma non è la
cronaca di che cosa fece quel giro quel giorno: è la risposta **di oggi** alla domanda «di questo
perimetro, che cosa risulta fatturato».

**3. Non c'è l'importo, ed è una scelta.** Il valore pro-quota di un'attività (N attività possono
stare su una riga di fattura sola) è una formula che vive già in
`vw_dash_competenza_attivita.valore_fatturato`. Riportarla qui sarebbe la terza copia di una regola
di calcolo, per una colonna che nessuno ha chiesto: la domanda era *quali* gruppi, non *per
quanto*.

---

### 🔍 Perché la commessa è nella grana

La chiave di un gruppo con documento vale `<codice_interno>:<uid>` e **non contiene la commessa**.
Lo stesso documento può alimentare righe su due commesse: la regola è «un documento in una sola
commessa **aperta**», e un documento la cui commessa è stata chiusa o annullata torna da mandare e
può finire in una commessa nuova. `vw_dash_competenza_gruppi` la commessa la tiene già nel proprio
raggruppamento: tenerla anche qui costa una colonna e toglie di mezzo un collasso silenzioso.

---

### 🔒 Scope

`security_invoker = on`. Il cancello non è decorativo: `fatturazione_lotti_fatture` e
`attivita_fatturabili` **non** hanno RLS, mentre `fatture`, `fatture_righe` e `commesse_attivita`
sì — quindi il `JOIN` su quelle è ciò che limita la vista al perimetro dell'operatore.

⚠️ Chi confronta questa vista con `fatturazione_lotti_gruppi` deve sapere che quella tabella RLS
**non ne ha**: senza un cancello anche sul richiesto, un lotto invisibile produrrebbe falsi «non
servito». Il cancello è dentro `fn_esito_gruppi_giro`, che è la sede dove il confronto avviene.

---

### Note di migrazione

* 2026-08-15 — nasce per dare al verdetto del giro una misura del servito (brief-db-emittibilita-visibile-e-sbloccabile §8.2, §9).
* 2026-10-12 — un documento sta in una sola commessa **aperta**, non più in una sola commessa per
  sempre (brief-db-annullo-a-valle-riapre-a-monte).
* 2026-11-07 — la chiave del gruppo si calcola con `fn_gruppo_fatturabile_key_di_attivita`, dall'uid
  del documento nel `segment_key`; l'attività fatturabile perde le sue colonne di provenienza
  (brief-db-sorgente-documento-e-riga).

---

{% include-markdown "signature-core.md" %}
