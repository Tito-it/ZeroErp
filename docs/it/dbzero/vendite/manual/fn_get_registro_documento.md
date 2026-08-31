## 📘 Documentazione Concettuale – Funzione `vendite.fn_get_registro_documento`

> 👀 **Vedi anche**
>
Approfondimenti funzioni:
>
[vendite.fn_lookup_registro_documento](/dbzero/vendite/manual/fn_lookup_registro_documento)
> • [vendite.fn_get_next_progressivo](/dbzero/vendite/manual/fn_get_next_progressivo)
>
Approfondimenti tabelle:
>
[vendite.registri_fatturazione](/dbzero/vendite/tabelle/registri_fatturazione)
> • [vendite.famiglie_documento](/dbzero/vendite/manual/famiglie_documento)

---
### 🎯 Scopo Principale
(latest review 31-08-2026)

Dà il **registro su cui un documento deve prendere il numero**, dato il tipo di
documento e l'emittente che lo emette. Se quel registro non c'è, **ferma**.

---

### Perché esistono due funzioni e non una

C'è una funzione che **cerca** e questa, che **pretende**.

* chi deve solo *sapere* se un registro esiste — una lista, un controllo, una
  maschera che mostra cosa succederebbe — usa quella che cerca, e accetta un
  «non c'è» come risposta legittima;
* chi sta **scrivendo un documento** usa questa. Lì «non c'è» non è
  un'informazione: è un documento che sta per nascere senza numero, o con un
  numero preso da una serie che non gli appartiene.

⭐ Tenerle separate evita l'errore classico: una funzione sola che a volte tace e
a volte blocca, e nessuno che si ricordi quale delle due cose fa nel punto in cui
la sta usando.

---

### Perché fermare è il verso giusto

Un emittente senza registro per quel tipo di documento è una **configurazione
incompleta**, non un caso d'uso. Se si lasciasse passare, il documento nascerebbe
senza numero e il problema comparirebbe molto più tardi — magari in stampa, o in
un controllo di sequenza — quando ricostruire cosa è successo costa dieci volte
tanto.

⚠️ È un comportamento **nuovo** rispetto a prima del 31 agosto 2026, e va nel
collaudo: un emittente configurato a metà oggi ferma la creazione dei suoi
documenti invece di lasciarla passare in silenzio. È il motivo per cui i registri
di ogni emittente vengono creati **prima** di accendere i generatori nuovi, e per
cui un emittente nuovo se li prende da sé.

---

### La fattura non passa da qui

Questa funzione **rifiuta** la famiglia «fattura», e non per dimenticanza: il
registro di una fattura dipende dal **tipo di documento fiscale** e dalla natura
dell'operazione, e lo sceglie una funzione sua.

⛔ Rispondere anche qui non darebbe un errore: darebbe il **primo registro di
fatturazione** dell'emittente — plausibile, e per una nota di credito il
sezionale **sbagliato**, in silenzio. Un rifiuto secco è meglio di una risposta
che sembra giusta.

---

### Impatto e Vantaggi

* un documento non fiscale prende il numero **dal registro del proprio
  emittente**, e due emittenti possono ripartire entrambi da 1 senza pestarsi i
  piedi;
* una configurazione incompleta si scopre **al primo documento**, con una frase
  che la nomina, invece che mesi dopo in mezzo a una sequenza di numeri.
