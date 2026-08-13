# Notes d'exploration - Superstore Dataset

## Métadonnées générales
- **Fichier source** : `data/raw/superstore_raw.csv`
- **Encodage** : latin-1 (échec en UTF-8, à noter pour le script ETL)
- **Dimensions** : 9 994 lignes x 21 colonnes
- **Date d'exploration** : [10/08/2026]

## Qualité des données
- Valeurs manquantes : 0 sur les 21 colonnes (dataset complet, pas d'imputation nécessaire)
- Lignes dupliquées : 0
- Cohérence Customer ID <-> Customer Name : validée (aucun ID ne correspond à plusieurs noms)

## Liste exacte des colonnes (21)
Row ID, Order ID, Order Date, Ship Date, Ship Mode, Customer ID, Customer Name,
Segment, Country, City, State, Postal Code, Region, Product ID, Category,
Sub-Category, Product Name, Sales, Quantity, Discount, Profit

## Écarts identifiés par rapport au guide de référence
- Aucun écart de nom de colonne : correspond exactement aux noms utilisés
  dans le DDL et le script ETL du guide (Section 4 et 5).
- Postal Code est en int64 : à surveiller, un code postal n'est pas une
  quantité numérique (perte possible d'un zéro initial si code sur 4 chiffres
  au lieu de 5).

## Anomalie confirmée : codes postaux tronqués
- 449 lignes sur 9 994 ont un Postal Code de 4 chiffres au lieu de 5.
- Cause : chargement en int64, qui supprime le zéro initial des codes
  postaux du Nord-Est des Etats-Unis (ex. Massachusetts, Rhode Island).
- Correction prévue au Jour 2 : conversion en texte avec zfill(5).

## Types de colonnes à corriger au Jour 2
- Order Date (object -> datetime)
- Ship Date (object -> datetime)
- Postal Code (int64 -> à vérifier, potentiellement string avec zero-padding)

## Décisions prises
- Pas de traitement de valeurs manquantes nécessaire (aucune trouvée).
- Pas de dédoublonnage nécessaire (aucun doublon).
- Le nettoyage du Jour 2 se concentrera uniquement sur : conversion des
  types de dates, vérification des codes postaux, et export du CSV
  intermédiaire nettoyé.

## Nettoyage effectué (Jour 2)
- Postal Code : converti en texte avec zéro initial restauré (zfill(5)) - OK
- Order Date / Ship Date : converties en datetime (format MM/JJ/AAAA) - OK
- Période couverte : 2014-01-03 à 2017-12-30 (4 années complètes)
- Cohérence Ship Date >= Order Date : validée (0 anomalie)
- Sales négatifs : 0
- Quantity <= 0 : 0
- Discount hors [0,1] : 0

## Fichier de sortie
- data/processed/superstore_clean.csv (9 994 lignes x 21 colonnes)
- Encodage : UTF-8 (converti depuis latin-1 source)

## Insight business identifié
- 1 871 lignes sur 9 994 (18.7%) ont un profit négatif.
- Ces lignes représentent 20.4% du chiffre d'affaires total.
- A investiguer en Jour 8-9 (requêtes SQL) : quelles catégories/segments
  sont les plus concernés ? Lien possible avec le taux de remise (Discount).