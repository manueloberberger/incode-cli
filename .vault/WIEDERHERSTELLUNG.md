# Projektweise Wiederherstellung mit Project Vault

In Vault dieses Projekt auswählen und „Zum Entwickeln wiederherstellen“ verwenden. Vault prüft Quellen, zugeordnete geschützte Bestandteile und die Entwicklungswerkzeuge getrennt. Das Projektpaket ist ein separates authentifiziert verschlüsseltes Release in einer privaten Ablage; es gehört nicht in ein App-ZIP. Das Sicherungspasswort und der erste GitHub-Zugang müssen unabhängig verfügbar sein.

Vorhandene Dateien werden nicht überschrieben. Fehlende gemeinsame Bestandteile können gezielt aus einer Notfallsicherung ergänzt werden. Erst eine erfolgreiche Projektprüfung bestätigt die Entwicklungsumgebung; ein vorhandener Klon allein reicht nicht. Anmeldungen, Lizenzen, Schlüsselbundimport und macOS-Freigaben können auf einem neuen Mac eigene Schritte erfordern.

`project.json` enthält keine Zugangsdaten. Es beschreibt die mit der zugehörigen Vault-Version geprüfte Zuordnung. Keine geheimen Werte ergänzen.

Für eine fertige App genügt in Vault „App installieren“ bzw. „App öffnen“; dafür sind weder Quellcode noch das Sicherungspasswort nötig. „Zusatzdaten verschlüsselt sichern“ legt ein eigenes privates Projektpaket an und pusht keine Codeänderungen. Quellcode und Zusatzpaket müssen beim Abschluss einer Weiterentwicklung gemeinsam geprüft und bei Änderungen aktualisiert werden.
