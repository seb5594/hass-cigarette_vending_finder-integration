# Zigarettenautomaten-Finder für Home Assistant

[🇬🇧 English](README.md) · **🇩🇪 Deutsch**

Die Integration sucht den nächsten **in OpenStreetMap erfassten** Zigarettenautomaten am Standort von Home Assistant oder einer Person. Über Overpass ist die Suche international und ohne API-Schlüssel möglich. Die Standorte sind nicht vollständig; Betrieb und Zugänglichkeit eines Automaten lassen sich daraus nicht garantieren.

## Installation

Dieses Repository im Home Assistant Marketplace (oder in älteren Versionen in HACS) als benutzerdefiniertes Repository vom Typ **Integration** hinzufügen, herunterladen und Home Assistant neu starten. Danach unter **Einstellungen → Geräte & Dienste** den **Zigarettenautomaten-Finder** einrichten. Getestet ab Home Assistant 2026.9.4.

Optional eine Standardperson auswählen sowie Suchradius (1–100 km, Standard 25) und Anzahl der Kartenmarkierungen (1–30, Standard 10) einstellen. Die Person benötigt Standortkoordinaten über einen Device Tracker. Gesucht wird beim Einrichten, etwa alle sechs Stunden und bei jedem Aufruf der Aktion.

## Aktive Suche

In **Entwicklerwerkzeuge → Aktionen** `cigarette_vending_finder.find_nearest` ausführen. `person: person.sebastian` nutzt den aktuellen Standort dieser Person. Alternativ gleichzeitig `latitude` und `longitude` angeben. Ohne beides gilt die konfigurierte Standardperson oder der Home Assistant Standort.

```yaml
# Beispiel für eine Automation mit auswertbarem Ergebnis.
action: cigarette_vending_finder.find_nearest
data:
  person: person.sebastian
  maximum_radius_km: 25
  limit: 5
response_variable: cigarette_machines
```

Die Antwort enthält `origin`, `count`, `nearest` und `machines`. Pro Automat werden die **Luftlinienentfernung**, OSM- und Navigationslink sowie vorhandene Standortdetails geliefert: etwa Beschreibung, genaue Lage, Stockwerk, Adresse, Betreiber, Zugang, Öffnungszeiten, Zahlarten und Erfassungsdatum. Ein `image_url` erscheint nur, wenn in OSM ein Bildlink oder eine Wikimedia-Commons-Datei hinterlegt ist. Ein vorhandener Mapillary-Verweis wird als Detail angezeigt, aber nicht als Bild geladen. Zusätzlich erscheinen ein Sensor für die Entfernung zum nächsten Automaten und temporäre Kartenmarkierungen. Fehlende Angaben werden nicht geschätzt.

Bei keinem Treffer ist `machines` leer und `nearest` gleich `null`. Ohne brauchbare Positionsdaten oder bei einer Störung von Overpass meldet die Aktion einen Fehler; der bisherige Sensorwert kann dann veraltet sein.

## Herkunft und Datenschutz

Gesucht werden OSM-Einträge mit `amenity=vending_machine` und `vending=cigarettes`, auch wenn ein Automat weitere Waren verkauft. Die Abfragen nutzen wachsende Radien und einen sechs Stunden gültigen Cache. Der öffentliche Overpass-Dienst ist begrenzt; für viele Installationen ist ein eigener Datendienst nötig. Die Suchkoordinaten werden an Overpass übertragen. Beim Anzeigen von Bildern kann Home Assistant externe Bildadressen abrufen. Fremde Standortlisten dürfen nur mit passenden Nutzungsrechten eingebunden werden.

Standortdaten: © [OpenStreetMap-Mitwirkende](https://www.openstreetmap.org/copyright), ODbL. Bilder haben eigene Lizenzen; bitte deren Bildseite beachten. Fehlende und falsche Automaten können direkt in OpenStreetMap korrigiert werden.
