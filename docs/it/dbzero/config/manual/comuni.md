# 📘 Documentazione Concettuale – Tabella `config.comuni`

>  👀 **Vedi anche** 

> Approfondimento Tabelle:  
> - [config.stradario](../stradario)      
> - [config.stradario_generale](../stradario_generale)  


La tabella **`config.comuni`** censisce i comuni (italiani ed esteri) all’interno di uno stato, fornendo la base per la geolocalizzazione degli indirizzi e per l’associazione con lo stradario.

---

## 🎯 Scopo Principale

* **Censimento dei comuni**
  Elenco dei comuni presenti in ciascuno stato, identificati da nome e collegamento gerarchico a provincia e stato.
* **Attributi specifici per stato**
  La colonna `extra_country` (JSONB) permette di memorizzare dati aggiuntivi specifici per ogni paese (per l’Italia: codice catastale, codice ISTAT, fascia climatica, ecc.).
* **Integrazione con lo stradario**
  L’associazione tra `config.stradario_generale` (prefissi e nomi delle vie) e `config.comuni` genera la tabella `config.stradario`, che contiene l’indirizzo completo con la localizzazione geografica sul comune di appartenenza.
  Utilizzata per associare i record di **`config.stradario`** al comune di appartenenza, completa il percorso di indirizzamento.

---

## 💡 Vantaggi Operativi

* **Flessibilità**
  L’uso di un campo JSONB per attributi extra consente di adattare la struttura dei dati alle diverse normative nazionali senza modifiche allo schema.
* **Coerenza geografica**
  Collegamento a tabelle di stato e provincia garantisce una gerarchia amministrativa corretta e uniforme.
* **Facilità di manutenzione**
  Inserimenti e aggiornamenti automatici tramite trigger di auditing e storicizzazione (se abilitata) assicurano la tracciabilità delle modifiche.

---

> 🧠 **"Un catalogo flessibile e gerarchico dei comuni, arricchito da attributi nazionali personalizzabili per supportare indirizzamento e reporting geografico."**
