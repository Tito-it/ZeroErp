## 📘 Documentazione Concettuale – Vista `dbops.vw_riferimenti_morti_rientrati`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [dbops.riferimenti_morti_esenzioni](/dbzero/dbops/tabelle/riferimenti_morti_esenzioni)
>
Approfondimento funzioni:
> • [dbops.fn_check_funzioni_riferimenti_morti](/dbzero/dbops/funzioni/fn_check_funzioni_riferimenti_morti)
>
Approfondimento viste:
> • [dbops.vw_riferimenti_morti_da_sanare](/dbzero/dbops/views/vw_riferimenti_morti_da_sanare)

---
### 🎯 Scopo Principale

(rev 2026-08-21)

Le voci del registro del debito che **non corrispondono più a nessun difetto**: righe da
**togliere**.

È il verso opposto della gemella `vw_riferimenti_morti_da_sanare`, e insieme fanno una cosa
che nessuna delle due fa da sola — **impedire al registro di gonfiarsi**.

Al 2026-08-21: **zero righe**.

---

### ⚠️ Perché senza questa vista il presidio si degrada da solo

Un registro di esenzioni ha una tendenza naturale: si riempie e non si svuota. Ogni difetto
giudicato accettabile aggiunge una riga; quando il difetto viene sanato, **nessuno torna
indietro a togliere l'esenzione**, perché niente lo segnala.

Il risultato, dopo un po', è un guardrail verde che non presidia quasi nulla: la maggior parte
del perimetro è esentata, e nessuno sa più quali esenzioni servano davvero.

Questa vista è ciò che rompe quel meccanismo: rende **visibile** l'esenzione diventata
inutile. È la ragione per cui il registro può essere chiamato «debito» e non «elenco di
eccezioni».

---

### Come funziona

`NOT EXISTS` rovesciato: per ogni riga di `riferimenti_morti_esenzioni`, verifica se esiste
ancora un difetto `REALE`/`ORFANA` che corrisponda a quello schema, quella funzione e quel
pattern `esito_like`. Se non esiste, la riga è **rientrata** e va rimossa.

Espone anche `motivo` e `data_registrazione`, così chi la toglie vede perché era stata messa e
da quanto tempo.

---

### ⚠️ Una riga qui non è sempre «difetto sanato»

Può anche voler dire che la **funzione è stata rinominata o eliminata**, o che l'`esito_like`
non corrisponde più perché il messaggio di `plpgsql_check` è cambiato — per esempio dopo un
aggiornamento dell'estensione, o dopo un ritocco che ha spostato i numeri di riga.

Prima di togliere una voce vale quindi la pena controllare che la funzione esista ancora e che
il difetto sia davvero sparito, non solo che il pattern non agganci più.

---

### ⚠️ Costa quanto la funzione che la alimenta

Come la gemella: fa girare `plpgsql_check_function` su tutto il database. Guardrail e test,
non percorsi frequenti.

Comporre le due viste in una query sola è **corretto** — verificato il 2026-08-21, lo stato
d'appoggio condiviso della funzione non crea interferenza — ma esegue il controllo **due
volte**.

---

### Scope

`WITH (security_invoker = on)`.

---

{% include-markdown "signature-core.md" %}
